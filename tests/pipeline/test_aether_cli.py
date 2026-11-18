"""S7: aether CLI against the data node.

ON-6   TORCH + flattening of example-crtdl.json: one CSV per attribute group
AE-3   service URLs are server roots; the TORCH CapabilityStatement is checked at start
AE-4   the CRTDL is checked at start (duplicate attributeGroup names)
AE-5   the auth block and the deprecated flat TORCH fields both send credentials; both together are refused
AE-7   Ctrl+C once warns, twice stops (exit 130); continue re-attaches; job stop cancels the TORCH job;
       a finished step needs --force
AE-8   pipeline status from a second process during the extraction
AE-9   flattening pairs code and strength of each ingredient
AE-10  decimals stay exact in DIMP (1.50)
AE-11  local_import reads the top level only and skips TORCH consent files
AE-12  aether send: transfer_load with OAuth, source.json with SHA-256, resume refused after a change
AE-13  DIMP splits bundles above the threshold and passes empty bundles
AE-14  AETHER_* overrides, ${VAR} expansion, ISO 8601 durations

Each test writes its own aether.yaml (JSON is valid YAML) into a temporary project.
"""

from __future__ import annotations

import csv
import json
import os
import pathlib
import re
import signal
import subprocess
import time

import pytest

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, wait_for_url
from torch_client import TORCH_URL, delete_resources
from torch_stub import JOB, torch_stub

EXAMPLE_CRTDL = DATA_NODE_DIR / "aether" / "queries" / "example-crtdl.json"
LOOKUP = DATA_NODE_DIR / "aether" / "flatteningLookup.json"
DUP_YAML = DATA_NODE_DIR / "example-dup-project" / "example-project_dimp_dup_base.yaml"
PIPELINE_CONFIGS = [DATA_NODE_DIR / "aether" / "base-pipeline-config.yml", DATA_NODE_DIR / "example-dup-project" / "example-project-pipeline.yml"]
PATIENT_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
MEDICATION_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-medikation/StructureDefinition/Medication"
NAMING_SYSTEM = "https://www.medizininformatik-initiative.de/fhir/fdpg/NamingSystem"


@pytest.fixture(scope="module", autouse=True)
def _wait_for_services():
    wait_for_url(f"{TORCH_URL}/actuator/health")
    wait_for_url("http://localhost:8083/fhir/metadata")
    wait_for_url("http://localhost:8088/", expect_status=None)


class Project:
    def __init__(self, path: pathlib.Path):
        self.path = path
        (path / "crtdl.json").write_text(EXAMPLE_CRTDL.read_text())

    def config(self, services: dict, steps: list[str], **extra) -> None:
        config = {"services": services, "pipeline": {"enabled_steps": steps}, "compression": {"enabled": False}, "jobs_dir": "./jobs"} | extra
        (self.path / "aether.yaml").write_text(json.dumps(config, indent=1))

    def command(self, *args: str) -> list[str]:
        return ["aether", *args]

    def run(self, *args: str, env: dict | None = None, timeout: float = 600) -> subprocess.CompletedProcess:
        result = subprocess.run(self.command(*args), cwd=self.path, capture_output=True, text=True,
                                env=os.environ | (env or {}), timeout=timeout)
        print(result.stdout[-4000:], result.stderr[-4000:])
        return result

    def popen(self, *args: str) -> subprocess.Popen:
        return subprocess.Popen(self.command(*args), cwd=self.path, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def start(self, crtdl: str = "crtdl.json", env: dict | None = None) -> subprocess.CompletedProcess:
        return self.run("pipeline", "start", "aether.yaml", crtdl, "--no-progress", env=env)

    def jobs(self) -> list[pathlib.Path]:
        jobs = self.path / "jobs"
        return sorted(p for p in jobs.iterdir() if p.is_dir()) if jobs.exists() else []

    def job(self) -> pathlib.Path:
        [job] = self.jobs()
        return job


@pytest.fixture
def project(tmp_path) -> Project:
    return Project(tmp_path)


def torch_services(url: str = TORCH_URL, **torch) -> dict:
    return {"torch": {"base_url": url, "polling_interval": "PT1S", "request_timeout": "PT1M"} | torch}


def output(result: subprocess.CompletedProcess) -> str:
    return result.stdout + result.stderr


def read_csv(path: pathlib.Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


# --- ON-6, AE-3, AE-4, AE-14 ---------------------------------------------------------------


def test_flattening_writes_one_csv_per_attribute_group(project):
    project.config(torch_services() | {"flattening": {"service_url": "http://localhost:8088", "lookup_path": str(LOOKUP), "formats": ["csv"]}},
                   ["torch", "flattening"])
    result = project.start()
    assert result.returncode == 0, output(result)
    groups = {g["name"] for g in json.loads(EXAMPLE_CRTDL.read_text())["dataExtraction"]["attributeGroups"]}
    csvs = {p.stem: p for p in (project.job() / "csv").glob("*.csv")}
    assert set(csvs) == groups
    diagnoses = read_csv(next(p for name, p in csvs.items() if "Diagnos" in name))
    icd10 = [c for c in diagnoses[0] if re.search(r"icd.?10", c, re.IGNORECASE) and c.endswith("_code")]
    assert icd10, f"no ICD-10 slice column in {list(diagnoses[0])}"
    assert any(row[icd10[0]] for row in diagnoses)


def test_torch_url_with_fhir_suffix_fails_before_a_job(project):
    project.config(torch_services(f"{TORCH_URL}/fhir"), ["torch"])
    result = project.start()
    assert result.returncode != 0
    assert "metadata check failed" in output(result)
    assert project.jobs() == []


def test_duplicate_group_names_stop_before_the_first_step(project):
    crtdl = json.loads(EXAMPLE_CRTDL.read_text())
    groups = crtdl["dataExtraction"]["attributeGroups"]
    groups[1]["name"] = groups[0]["name"]
    (project.path / "duplicate.json").write_text(json.dumps(crtdl))
    project.config(torch_services(), ["torch"])
    result = project.start("duplicate.json")
    assert result.returncode != 0
    assert "duplicate-csv-filename" in output(result)
    assert project.jobs() == []


def test_aether_env_override_is_applied(project):
    project.config(torch_services(), ["torch"])
    result = project.start(env={"AETHER_SERVICES_TORCH_BASE_URL": f"{TORCH_URL}/fhir"})
    assert result.returncode != 0
    assert f"{TORCH_URL}/fhir/fhir/metadata" in output(result)


def test_variables_and_iso_durations_in_the_config(project):
    project.config(torch_services("${S7_TORCH_URL}", extraction_timeout="PT10M"), ["torch"])
    result = project.start(env={"S7_TORCH_URL": TORCH_URL})
    assert result.returncode == 0, output(result)
    assert list((project.job() / "import").glob("*.ndjson"))


# --- AE-5, AE-7, AE-8 (stub TORCH) ---------------------------------------------------------


def wait_until(condition, timeout: float = 60, message: str = "condition"):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.5)
    raise TimeoutError(message)


def interrupt_twice(process: subprocess.Popen) -> str:
    process.send_signal(signal.SIGINT)
    time.sleep(1)
    assert process.poll() is None, "aether stopped on the first Ctrl+C"
    process.send_signal(signal.SIGINT)
    out, _ = process.communicate(timeout=60)
    return out


@pytest.mark.parametrize("shape", ["auth-block", "flat-fields"])
def test_torch_credentials_are_sent(project, shape):
    credentials = {"username": "s7", "password": "secret"}
    torch = {"auth": credentials} if shape == "auth-block" else credentials
    with torch_stub() as stub:
        project.config(torch_services(stub.url, **torch), ["torch"])
        process = project.popen("pipeline", "start", "aether.yaml", "crtdl.json", "--no-progress")
        try:
            wait_until(lambda: stub.calls("POST", "$extract-data"), message="no $extract-data")
        finally:
            interrupt_twice(process)
    assert stub.calls("POST", "$extract-data")[0]["Authorization"] == "Basic czc6c2VjcmV0"


def test_auth_block_and_flat_fields_together_are_refused(project):
    project.config(torch_services(username="s7", password="secret", auth={"username": "s7", "password": "secret"}), ["torch"])
    result = project.start()
    assert result.returncode != 0
    assert "not both" in output(result)


def test_interrupt_continue_and_stop(project):
    with torch_stub() as stub:
        project.config(torch_services(stub.url), ["torch"])
        start = project.popen("pipeline", "start", "aether.yaml", "crtdl.json", "--no-progress")
        try:
            wait_until(lambda: stub.calls("GET", f"__status/{JOB}"), message="aether does not poll")
            job_id = project.job().name
            status = project.run("pipeline", "status", "aether.yaml", job_id)
            assert status.returncode == 0 and "torch" in output(status).lower()  # AE-8
        finally:
            out = interrupt_twice(start)
        assert "Press Ctrl+C again" in out
        assert start.returncode == 130

        polls = len(stub.calls("GET", f"__status/{JOB}"))
        resumed = project.popen("pipeline", "continue", "aether.yaml", job_id, "--no-progress")
        try:
            wait_until(lambda: len(stub.calls("GET", f"__status/{JOB}")) > polls, message="continue does not poll")
            assert len(stub.calls("POST", "$extract-data")) == 1, "continue submitted the CRTDL again"
            stop = project.run("job", "stop", "aether.yaml", job_id, timeout=90)
            assert stop.returncode == 0, output(stop)
            assert stub.calls("POST", f"Task/{JOB}/$cancel")
            resumed.wait(timeout=60)
        finally:
            if resumed.poll() is None:
                resumed.kill()
    listing = project.run("job", "list", "aether.yaml")
    assert re.search(rf"{job_id}\s+\S*\s*stopped", output(listing)), output(listing)


# --- AE-9, AE-10, AE-11, AE-13, job run --force --------------------------------------------


def provenance(resource: dict, group: str) -> dict:
    pid = f"prov-{resource['id']}"
    return {
        "resourceType": "Provenance", "id": pid,
        "target": [{"reference": f"{resource['resourceType']}/{resource['id']}"}],
        "recorded": "2026-01-01T00:00:00+00:00",
        "agent": [{"who": {"identifier": {"system": f"{NAMING_SYSTEM}/program", "value": "torch"}}}],
        "entity": [{"role": "source", "what": {"identifier": {"system": f"{NAMING_SYSTEM}/attribute_group", "value": group}}}],
    }


def torch_bundle(bundle_id: str, grouped: list[tuple[str, dict]]) -> dict:
    """A patient bundle as TORCH writes it: transaction PUTs plus one Provenance per resource
    that names its attribute group (aether routes resources to groups by it)."""
    resources = [r for _, r in grouped] + [provenance(r, g) for g, r in grouped]
    return {
        "resourceType": "Bundle", "id": bundle_id, "type": "transaction",
        "entry": [{"resource": r, "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}} for r in resources],
    }


def ingredient(code: str, strength: str) -> dict:
    return {
        "itemCodeableConcept": {"coding": [{"system": "http://fhir.de/CodeSystem/ask", "code": code}]},
        "strength": {
            "numerator": {"value": "__DECIMAL_" + strength, "unit": "mg", "system": "http://unitsofmeasure.org", "code": "mg"},
            "denominator": {"value": 1, "unit": "mL", "system": "http://unitsofmeasure.org", "code": "mL"},
        },
    }


def ndjson(*bundles: dict) -> str:
    """NDJSON with decimals written exactly as given (json would turn 1.50 into 1.5)."""
    text = "\n".join(json.dumps(b) for b in bundles) + "\n"
    return re.sub(r'"__DECIMAL_([0-9.]+)"', r"\1", text)


LOCAL_CRTDL = {
    "groups": [
        {"id": "pat", "name": "Patient", "groupReference": PATIENT_PROFILE, "attributes": [{"attributeRef": "Patient.gender", "mustHave": False}]},
        {"id": "med", "name": "Medication", "groupReference": MEDICATION_PROFILE, "attributes": [{"attributeRef": "Medication.ingredient", "mustHave": False}]},
    ]
}


@pytest.fixture
def local_project(project) -> Project:
    data = project.path / "data"
    (data / "nested").mkdir(parents=True)
    patient = {"resourceType": "Patient", "id": "ae-p1", "meta": {"profile": [PATIENT_PROFILE]}, "gender": "female"}
    medication = {"resourceType": "Medication", "id": "ae-m1", "meta": {"profile": [MEDICATION_PROFILE]},
                  "ingredient": [ingredient("10001", "1.50"), ingredient("10002", "20")]}
    (data / "batch.ndjson").write_text(ndjson(torch_bundle("batch", [("pat", patient), ("med", medication)])))
    (data / "batch_consent.ndjson").write_text(ndjson({"resourceType": "Bundle", "id": "consent", "type": "collection"}))
    (data / "nested" / "other.ndjson").write_text(ndjson(torch_bundle("other", [("pat", patient | {"id": "ae-p2"})])))
    crtdl = json.loads(EXAMPLE_CRTDL.read_text())
    crtdl["dataExtraction"]["attributeGroups"] = LOCAL_CRTDL["groups"]
    (project.path / "crtdl.json").write_text(json.dumps(crtdl))
    project.config({
        "local_import": {"dir": str(data)},
        "dimp": {"url": "http://localhost:8083", "anonymization_config": str(DUP_YAML)},
        "flattening": {"service_url": "http://localhost:8088", "lookup_path": str(LOOKUP), "formats": ["csv"]},
    }, ["local_import", "dimp", "flattening"])
    return project


def test_local_import_dimp_and_flattening(local_project):
    result = local_project.start()
    assert result.returncode == 0, output(result)
    job = local_project.job()
    assert sorted(p.name for p in (job / "import").iterdir()) == ["batch.ndjson"]  # AE-11
    assert '"value":1.50' in (job / "dimp" / "dimped_batch.ndjson").read_text().replace(" ", "")  # AE-10
    rows = read_csv(job / "csv" / "Medication.csv")  # AE-9
    code = next(c for c in rows[0] if c.endswith("codingAsk_code"))
    strength = next(c for c in rows[0] if c.endswith("strength_numerator_value"))
    assert sorted((r[code], float(r[strength])) for r in rows) == [("10001", 1.5), ("10002", 20.0)]


def test_finished_step_needs_force(local_project):
    assert local_project.start().returncode == 0
    job_id = local_project.job().name
    again = local_project.run("job", "run", "aether.yaml", job_id, "--step", "dimp")
    assert again.returncode != 0 and "--force" in output(again)
    forced = local_project.run("job", "run", "aether.yaml", job_id, "--step", "dimp", "--force")
    assert forced.returncode == 0, output(forced)


def test_dimp_splits_large_bundles_and_passes_empty_ones(project):
    data = project.path / "data"
    data.mkdir()
    observations = [{"resourceType": "Observation", "id": f"o{i}", "status": "final", "code": {"text": "x" * 1000},
                     "subject": {"reference": "Patient/p1"}} for i in range(3000)]
    big = {"resourceType": "Bundle", "id": "big", "type": "transaction",
           "entry": [{"resource": o, "request": {"method": "PUT", "url": f"Observation/{o['id']}"}} for o in observations]}
    (data / "big.ndjson").write_text(ndjson(big))
    (data / "empty.ndjson").write_text(ndjson({"resourceType": "Bundle", "id": "empty", "type": "transaction"}))
    project.config({"local_import": {"dir": str(data)},
                    "dimp": {"url": "http://localhost:8083", "anonymization_config": str(DUP_YAML), "bundle_split_threshold_mb": 1}},
                   ["local_import", "dimp"])
    result = project.start()
    assert result.returncode == 0, output(result)
    chunks = re.search(r"Split Bundle into chunks \| \[bundle_id big chunks (\d+)\]", output(result))
    assert chunks and int(chunks.group(1)) >= 4
    dimp = project.job() / "dimp"
    [big_out] = [json.loads(line) for line in (dimp / "dimped_big.ndjson").read_text().splitlines() if line.strip()]
    assert len(big_out["entry"]) == len(observations)
    [empty_out] = [json.loads(line) for line in (dimp / "dimped_empty.ndjson").read_text().splitlines() if line.strip()]
    assert empty_out["resourceType"] == "Bundle" and "entry" not in empty_out


# --- AE-12 -----------------------------------------------------------------------------------


def frontend_client() -> dict:
    """OAuth client of the Blaze frontend, as data-node/get-fhir-server-access-token.sh uses it."""
    result = subprocess.run(["docker", "inspect", "--format", "{{json .Config.Env}}", f"{COMPOSE_PROJECT}-fhir-server-frontend-1"],
                            capture_output=True, text=True, check=True)
    env = dict(e.split("=", 1) for e in json.loads(result.stdout))
    return {"oauth_issuer_uri": env["AUTH_ISSUER"], "oauth_client_id": env["AUTH_CLIENT_ID"], "oauth_client_secret": env["AUTH_CLIENT_SECRET"]}


def send_config(project: Project, url: str) -> None:
    project.config({"send": {"send_as": "transfer_load", "url": url, "auth": frontend_client(),
                             "transfer": {"project_identifier": "S7-PROJECT", "organization_identifier": "s7.example.de"}}},
                   ["local_import"], tls={"ca_cert_path": str(DATA_NODE_DIR / "auth" / "cert.pem")})


def test_send_transfer_load_and_resume(project):
    """A first run against .../fhir fails (D17), a resume with changed files is refused,
    a resume with the original files and the server root completes."""
    files = project.path / "csv"
    files.mkdir()
    (files / "one.csv").write_text('a,b\n1,"x,y"\n')
    (files / "two.CSV").write_text("c\n2\n")
    (files / "notes.txt").write_text("not sent")
    send_config(project, "http://localhost:8081/fhir")
    failed = project.run("send", "aether.yaml", str(files))
    assert failed.returncode != 0
    job = project.job()
    source = json.loads((job / "source.json").read_text())
    assert source["completed"] is False
    assert sorted(f["name"] for f in source["files"]) == ["one.csv", "two.CSV"]
    assert all(re.fullmatch(r"[0-9a-f]{64}", f["sha256"]) for f in source["files"])

    (files / "one.csv").write_text("changed\n")
    refused = project.run("send", "aether.yaml", str(files), "--job", job.name)
    assert refused.returncode != 0 and "source directory changed" in output(refused)

    (files / "one.csv").write_text('a,b\n1,"x,y"\n')
    send_config(project, "http://localhost:8081")
    resumed = project.run("send", "aether.yaml", str(files), "--job", job.name)
    log = (job / "job.log").read_text()
    uploaded = [{"resourceType": t, "id": i} for t, i in sorted(set(re.findall(r"\b(DocumentReference|Binary)/([0-9a-f-]{36})\b", log)))]
    try:
        assert resumed.returncode == 0, output(resumed)
        assert json.loads((job / "source.json").read_text())["completed"] is True
        assert any(r["resourceType"] == "DocumentReference" for r in uploaded)
    finally:
        if uploaded:
            delete_resources(uploaded)


@pytest.mark.xfail(strict=True, reason="D17: services.send.url in the example pipeline configs ends in /fhir; "
                   "aether expects the server root and sends to .../fhir/fhir (404)")
@pytest.mark.parametrize("config", PIPELINE_CONFIGS, ids=lambda p: p.name)
def test_example_send_url_is_a_server_root(config):
    url = re.search(r"^\s*send:.*?^\s*url:\s*\"([^\"]+)\"", config.read_text(), re.MULTILINE | re.DOTALL).group(1)
    assert not url.rstrip("/").endswith("/fhir"), url
