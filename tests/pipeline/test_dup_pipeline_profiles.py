"""Runs one CRTDL per DSE profile of the pinned ontology release through the example DUP
pipeline (data-node/example-dup-project/example-project-pipeline.yml: TORCH, DIMP,
fhir-flattener).

ontology_testdata.py generates the CRTDLs and a bundle with test data for every profile and
field. The bundle is loaded into the FHIR server for this module and deleted afterwards. Each
CRTDL runs unchanged, PARALLEL runs at a time. A run passes if aether exits 0, state.json
reports "completed" for the job and every step, and the flattening step wrote a CSV. Failed
runs are retried once alone. test_parallel_runs_fail_only_like_single_runs reports the runs
that failed only under load.

The run directories (CRTDL, generated aether config, aether log, job directory) and
summary.md are under the pytest base temp directory, printed at the start of the run.
"""

from __future__ import annotations

import concurrent.futures
import csv
import json
import pathlib
import re
import subprocess
import time

import pytest

import ontology_testdata
from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, assert_only_known_issues, pinned_ontology_tag, wait_for_url
from torch_client import delete_resources, fhir_search, put_resources

PROJECT_DIR = DATA_NODE_DIR / "example-dup-project"
PIPELINE_CONFIG = PROJECT_DIR / "example-project-pipeline.yml"
PARALLEL = 4
RUN_TIMEOUT = 1800
TORCH_POLL_INTERVAL = 1


@pytest.fixture(scope="module")
def generated(request, tmp_path_factory) -> pathlib.Path:
    wait_for_url("http://localhost:8086/actuator/health")  # torch
    wait_for_url("http://localhost:8083/fhir/metadata")  # dimp
    wait_for_url("http://localhost:8089/v1/namespaces")  # vfps
    wait_for_url("http://localhost:8088/", expect_status=None)  # fhir-flattener has no health route
    subprocess.run(["bash", "example-project-create-namespaces-vfps.sh"], cwd=PROJECT_DIR, check=True)

    out = tmp_path_factory.mktemp("dup-pipeline-profiles")
    print(f"ontology tests: {out}")
    cache = pathlib.Path(request.config.cache.mkdir("ontology-release"))
    resources = ontology_testdata.generate(pinned_ontology_tag(), cache, out)
    put_resources(resources)
    yield out
    # TORCH leaves the cohort of every extraction as a List in the FHIR server. Lists that
    # reference the generated patients block their deletion (referential integrity).
    patients = ",".join(f"Patient/{r['id']}" for r in resources if r["resourceType"] == "Patient")
    delete_resources(resources + fhir_search(f"List?item={patients}&_elements=id&_count=1000"))


def _pipeline_config(jobs_dir: pathlib.Path) -> str:
    """The example pipeline config with jobs_dir in the run directory, so nothing is written to
    example-dup-project/jobs, and a short TORCH poll interval."""
    text = PIPELINE_CONFIG.read_text()
    for pattern, replacement in [
        (r"(?m)^jobs_dir:.*$", f'jobs_dir: "{jobs_dir}"'),
        # aether reads torch.polling_interval (a duration) and ignores the example's polling_interval_seconds.
        (r"(?m)^(\s+)polling_interval_seconds:.*$", rf'\g<1>polling_interval: "{TORCH_POLL_INTERVAL}s"'),
    ]:
        text, n = re.subn(pattern, replacement, text)
        assert n == 1, f"expected one match of {pattern!r} in {PIPELINE_CONFIG}, found {n}"
    return text


def _csv_rows(path: pathlib.Path) -> int:
    with path.open(newline="") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


def _run(crtdl: pathlib.Path, run_dir: pathlib.Path) -> dict:
    run_dir.mkdir(parents=True)
    (run_dir / "crtdl.json").write_text(crtdl.read_text())
    (run_dir / "pipeline.yml").write_text(_pipeline_config(run_dir / "jobs"))
    start = time.monotonic()
    cmd = ["aether", "pipeline", "start", str(run_dir / "pipeline.yml"), str(run_dir / "crtdl.json"), "--no-progress"]
    try:
        proc = subprocess.run(cmd, cwd=PROJECT_DIR, capture_output=True, text=True, timeout=RUN_TIMEOUT)
        exit_code, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        exit_code = -1
        log = (e.stdout or b"").decode(errors="replace") + (e.stderr or b"").decode(errors="replace")
        log += f"\nError: timeout after {RUN_TIMEOUT}s\n"
    (run_dir / "aether.log").write_text(log)

    result = {"crtdl": crtdl.stem, "exit_code": exit_code, "job_status": None, "steps": {}, "csv": {}, "error": None,
              "duration_s": round(time.monotonic() - start)}
    jobs = [d for d in (run_dir / "jobs").glob("*") if d.is_dir()]
    if jobs:
        job = max(jobs, key=lambda d: d.stat().st_mtime)
        state_file = job / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            result["job_status"] = state.get("status")
            result["steps"] = {s["name"]: s["status"] for s in state.get("steps", [])}
        result["csv"] = {c.stem: _csv_rows(c) for c in sorted((job / "csv").glob("*.csv"))}
    if errors := [line for line in log.splitlines() if line.startswith("Error:")]:
        result["error"] = errors[-1].removeprefix("Error:").strip()

    checks = {
        f"exit code {exit_code}": exit_code == 0,
        f"job status {result['job_status']}": result["job_status"] == "completed",
        "not all steps completed": bool(result["steps"]) and all(s == "completed" for s in result["steps"].values()),
        "no csv written": bool(result["csv"]),
    }
    result["failed_checks"] = [k for k, ok in checks.items() if not ok]
    return result


def _write_summary(path: pathlib.Path, results: list[dict]) -> None:
    lines = ["# DUP pipeline profile runs", "", f"Passed {sum(not r['failed_checks'] for r in results)} of {len(results)}.", "",
             "| CRTDL | Result | Steps | CSV rows | Error |", "| --- | --- | --- | --- | --- |"]
    for r in results:
        verdict = "FAIL (" + "; ".join(r["failed_checks"]) + ")" if r["failed_checks"] else "PASS"
        steps = ", ".join(f"{k}={v}" for k, v in r["steps"].items()) or "-"
        rows = ", ".join(f"{k}={v}" for k, v in r["csv"].items()) or "-"
        lines.append(f"| {r['crtdl']} | {verdict} | {steps} | {rows} | {(r['error'] or '-').replace('|', '/')} |")
    path.write_text("\n".join(lines) + "\n")


def _flattener_restarts() -> int:
    result = subprocess.run(["docker", "inspect", f"{COMPOSE_PROJECT}-fhir-flattener-1", "--format", "{{.RestartCount}}"],
                            capture_output=True, text=True, check=True)
    return int(result.stdout)


@pytest.fixture(scope="module")
def results(generated: pathlib.Path) -> dict:
    """Runs every CRTDL, PARALLEL at a time. Failed runs are retried once alone, so a profile
    result does not depend on load. The parallel failures are kept in "parallel_failures"."""
    crtdls = sorted((generated / "crtdls").glob("*.json"))
    assert crtdls, f"no CRTDLs generated in {generated / 'crtdls'}"
    restarts = _flattener_restarts()
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        results = list(pool.map(lambda c: _run(c, generated / "runs" / c.stem), crtdls))
    restarts = _flattener_restarts() - restarts
    parallel_failures = [r for r in results if r["failed_checks"]]
    results = [_run(generated / "crtdls" / f"{r['crtdl']}.json", generated / "runs" / f"{r['crtdl']}-retry")
               if r["failed_checks"] else r for r in results]
    _write_summary(generated / "summary.md", results)
    (generated / "summary.json").write_text(json.dumps(results, indent=2))
    return {"results": results, "parallel_failures": parallel_failures, "flattener_restarts": restarts}


def test_testdata_covers_every_dse_field(generated: pathlib.Path):
    coverage = json.loads((generated / "coverage.json").read_text())["profiles"]
    uncovered = [f"{c['crtdl']}: {f}" for c in coverage
                 for f in c["uncovered_fields"] + c["uncovered_references"] + c["unlinked_references"]]
    assert not uncovered, f"DSE fields without test data, see {generated / 'coverage.md'}:\n  " + "\n  ".join(uncovered)


def test_every_profile_runs_through_the_pipeline(generated: pathlib.Path, results: dict):
    failed = [r for r in results["results"] if r["failed_checks"]]
    for r in failed:
        print(f"{r['crtdl']}: {'; '.join(r['failed_checks'])}: {r['error']}")
    print(f"summary: {generated / 'summary.md'}")
    assert_only_known_issues("dup-pipeline-profiles", [r["crtdl"] for r in failed])


@pytest.mark.xfail(strict=False, reason="D26: fhir-flattener 0.1.0-alpha.10 exits (code 0, no log) under sustained load and "
                   "restarts, about 13 times in 268 runs with 4 in parallel, once in 268 sequential runs. aether's retries "
                   "hide most restarts. Not deterministic, so not strict.")
def test_parallel_runs_fail_only_like_single_runs(results: dict):
    failed_alone = {r["crtdl"] for r in results["results"] if r["failed_checks"]}
    load_failures = [f"{r['crtdl']}: {r['error']}" for r in results["parallel_failures"] if r["crtdl"] not in failed_alone]
    assert not load_failures and not results["flattener_restarts"], (
        f"fhir-flattener restarted {results['flattener_restarts']} times during {PARALLEL} parallel runs. "
        f"Runs that failed in parallel but passed alone:\n  " + "\n  ".join(load_failures)
    )
