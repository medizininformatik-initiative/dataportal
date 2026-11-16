#!/usr/bin/env python3
"""Run every CRTDL in a folder through aether with the example DUP pipeline.

Each CRTDL runs in the modes given with --modes (default: both):
  as-is            the CRTDL unchanged
  cohort-replaced  cohortDefinition replaced by replacement-cohort.json

A run passes if aether exits 0, state.json reports "completed" for the job and
every step, and the flattening step wrote at least one CSV.

Layout of results/<timestamp>/:
  summary.md, summary.json
  failures.md                        failed runs only
  <crtdl-name>/<mode>/crtdl.json     CRTDL that was submitted
  <crtdl-name>/<mode>/pipeline.yml   generated aether config (jobs_dir points here)
  <crtdl-name>/<mode>/aether.log     aether stdout + stderr
  <crtdl-name>/<mode>/job/           symlink to the aether job dir
                                     (import/, dimp/, csv/, state.json, job.log)

Usage:
  ./run-dup-pipeline-tests.py [--crtdl-dir DIR] [--results-dir DIR] [--modes as-is cohort-replaced]
                              [--parallel N] [--torch-poll-interval SECONDS]
"""
import argparse
import concurrent.futures
import csv
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODES = ("as-is", "cohort-replaced")


def parse_args():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--crtdl-dir", type=Path, default=HERE / "input-crtdls")
    p.add_argument("--example-dir", type=Path, default=HERE.parent / "example-dup-project",
                   help="example DUP project; aether runs with this as cwd so its relative paths resolve")
    p.add_argument("--pipeline", default="example-project-pipeline.yml",
                   help="pipeline config file name inside --example-dir")
    p.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES),
                   help="modes to run (default: both), e.g. --modes as-is")
    p.add_argument("--cohort", type=Path, default=HERE / "replacement-cohort.json")
    p.add_argument("--results-dir", type=Path, default=HERE / "results")
    p.add_argument("--aether", default="aether")
    p.add_argument("--timeout", type=int, default=3600, help="seconds per aether run")
    p.add_argument("--parallel", type=int, default=4, help="number of aether runs at the same time")
    p.add_argument("--torch-poll-interval", type=int, default=1,
                   help="seconds between TORCH status polls (minimum 1)")
    return p.parse_args()


def override(text: str, pattern: str, replacement: str) -> str:
    text, n = re.subn(pattern, replacement, text)
    if n != 1:
        sys.exit(f"expected exactly one match of {pattern!r} in pipeline config, found {n}")
    return text


def write_pipeline_config(template: str, jobs_dir: Path, poll_interval: int, dest: Path):
    text = override(template, r"(?m)^jobs_dir:.*$", f'jobs_dir: "{jobs_dir}"')
    # aether reads torch.polling_interval (a duration). The example config's polling_interval_seconds is ignored.
    text = override(text, r"(?m)^(\s+)polling_interval_seconds:.*$", rf'\g<1>polling_interval: "{poll_interval}s"')
    dest.write_text(text)


def csv_rows(path: Path) -> int:
    with path.open(newline="") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


def evaluate(run_dir: Path, exit_code: int, log: str) -> dict:
    jobs = [d for d in (run_dir / "jobs").glob("*") if d.is_dir()] if (run_dir / "jobs").exists() else []
    result = {"exit_code": exit_code, "job_id": None, "job_status": None, "steps": {}, "csv": {}, "error": None}

    if jobs:
        job = max(jobs, key=lambda d: d.stat().st_mtime)
        result["job_id"] = job.name
        (run_dir / "job").symlink_to(Path("jobs") / job.name)
        state_file = job / "state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            result["job_status"] = state.get("status")
            result["steps"] = {s["name"]: s["status"] for s in state.get("steps", [])}
        for c in sorted((job / "csv").glob("*.csv")):
            result["csv"][c.name] = csv_rows(c)

    errors = [l for l in log.splitlines() if l.startswith("Error:")]
    if errors:
        result["error"] = errors[-1][len("Error:"):].strip()

    checks = {
        f"exit code {exit_code}": exit_code == 0,
        f"job status {result['job_status']}": result["job_status"] == "completed",
        "not all steps completed": bool(result["steps"]) and all(s == "completed" for s in result["steps"].values()),
        "no csv written": bool(result["csv"]),
    }
    result["failed_checks"] = [k for k, ok in checks.items() if not ok]
    result["passed"] = not result["failed_checks"]
    return result


def run_one(args, template: str, crtdl: dict, run_dir: Path) -> dict:
    run_dir.mkdir(parents=True)
    crtdl_path = run_dir / "crtdl.json"
    crtdl_path.write_text(json.dumps(crtdl, indent=4, ensure_ascii=False))
    config_path = run_dir / "pipeline.yml"
    write_pipeline_config(template, run_dir / "jobs", args.torch_poll_interval, config_path)

    cmd = [args.aether, "pipeline", "start", str(config_path), str(crtdl_path), "--no-progress"]
    start = datetime.datetime.now()
    try:
        proc = subprocess.run(cmd, cwd=args.example_dir, capture_output=True, text=True, timeout=args.timeout)
        exit_code, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        exit_code = -1
        log = (e.stdout or b"").decode(errors="replace") + (e.stderr or b"").decode(errors="replace")
        log += f"\nError: timeout after {args.timeout}s\n"
    (run_dir / "aether.log").write_text(log)

    result = evaluate(run_dir, exit_code, log)
    result["duration_s"] = round((datetime.datetime.now() - start).total_seconds(), 1)
    return result


def write_summary(out: Path, results: list):
    (out / "summary.json").write_text(json.dumps(results, indent=2))
    write_table(out / "summary.md", "DUP pipeline test results",
                f"Passed {sum(r['passed'] for r in results)} of {len(results)} runs.", results)
    failures = [r for r in results if not r["passed"]]
    write_table(out / "failures.md", "DUP pipeline test failures",
                f"Failed {len(failures)} of {len(results)} runs.", failures)


def write_table(path: Path, title: str, intro: str, results: list):
    lines = [f"# {title}", "", intro, "",
             "| CRTDL | Mode | Result | Steps | CSV rows | Error | Output |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in results:
        steps = ", ".join(f"{k}={v}" for k, v in r["steps"].items()) or "-"
        rows = ", ".join(f"{Path(k).stem}={v}" for k, v in r["csv"].items()) or "-"
        verdict = "PASS" if r["passed"] else "FAIL (" + "; ".join(r["failed_checks"]) + ")"
        error = (r["error"] or "-").replace("|", "\\|")
        lines.append(f"| {r['crtdl']} | {r['mode']} | {verdict} | {steps} | {rows} | {error} | "
                     f"[{r['crtdl']}/{r['mode']}]({r['crtdl']}/{r['mode']}) |")
    path.write_text("\n".join(lines) + "\n")


def main():
    args = parse_args()
    args.example_dir = args.example_dir.resolve()
    template = (args.example_dir / args.pipeline).read_text()
    cohort = json.loads(args.cohort.read_text())
    crtdls = sorted(args.crtdl_dir.glob("*.json"))
    if not crtdls:
        sys.exit(f"no CRTDL files in {args.crtdl_dir}")

    out = args.results_dir.resolve() / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True)
    print(f"results: {out}")

    tasks = []
    for path in crtdls:
        original = json.loads(path.read_text())
        for mode in args.modes:
            crtdl = dict(original)
            if mode == "cohort-replaced":
                crtdl["cohortDefinition"] = cohort
            tasks.append((path.stem, mode, crtdl))
    print(f"{len(crtdls)} CRTDLs x {len(args.modes)} modes = {len(tasks)} runs, {args.parallel} in parallel")

    def run(task):
        name, mode, crtdl = task
        r = run_one(args, template, crtdl, out / name / mode)
        r.update(crtdl=name, mode=mode)
        return r

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for done, r in enumerate(concurrent.futures.as_completed([pool.submit(run, t) for t in tasks]), 1):
            r = r.result()
            results.append(r)
            verdict = "PASS" if r["passed"] else f"FAIL ({'; '.join(r['failed_checks'])}) {r['error'] or ''}"
            print(f"[{done}/{len(tasks)}] {r['crtdl']} [{r['mode']}] {r['duration_s']}s ... {verdict}", flush=True)

    order = {(name, mode): i for i, (name, mode, _) in enumerate(tasks)}
    results.sort(key=lambda r: order[(r["crtdl"], r["mode"])])
    write_summary(out, results)
    print(f"\n{sum(r['passed'] for r in results)}/{len(results)} passed. Summary: {out / 'summary.md'}, failures: {out / 'failures.md'}")
    sys.exit(0 if all(r["passed"] for r in results) else 1)


if __name__ == "__main__":
    main()
