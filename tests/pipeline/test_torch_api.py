"""S6: TORCH API beyond $extract-data.

TO-1   Task API: a running job can be paused, resumed, reprioritised and cancelled; unknown ids give 404
TO-7   Patient.identifier only when the CRTDL asks for it; Patient.meta.profile from groupReference
TO-8   cohort size = extracted patients + excluded patients, with an exclusion list
TO-11  Task progress and Prometheus metrics agree with the job summary
TO-12  $evaluate-cohort and $translate-cql
TO-15  405 for a wrong HTTP method
ON-7   the data selection date filter (recorded-date of Diagnose) limits the extracted resources

TO-1 needs a job that stays running: a TORCH variant reads from a FHIR server that holds
every search (tests/pipeline/torch_stub.py slow_fhir_server). The TO-1 tests share that job
and run in file order: the cancel test ends the job, so it has to stay the last of them.

Spec: https://medizininformatik-initiative.github.io/torch/api/task-api.html
"""

from __future__ import annotations

import copy
import json
import time
import urllib.error
import urllib.request

import pytest

from helpers import DATA_NODE_DIR, wait_for_url
from torch_client import TORCH_URL, Result, condition_crtdl, extract, fhir_search, submit, torch_variant, wait
from torch_stub import slow_fhir_server

EXAMPLE_CRTDL = DATA_NODE_DIR / "aether" / "queries" / "example-crtdl.json"
CONSENT_CRTDL = DATA_NODE_DIR / "aether" / "queries" / "example-crtdl-consent.json"
PATIENT_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/PatientPseudonymisiert"
BUSINESS_STATUS = "https://medizininformatik-initiative.de/torch/job-status"


@pytest.fixture(scope="module", autouse=True)
def _wait_for_torch():
    wait_for_url(f"{TORCH_URL}/actuator/health")


def call(method: str, url: str, body: object | None = None, headers: dict | None = None,
         content_type: str = "application/fhir+json") -> tuple[int, object]:
    data = json.dumps(body).encode() if body is not None else (b"" if method in ("POST", "PUT") else None)
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": content_type} | (headers or {}))
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            text = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as error:
        text, status = error.read().decode(), error.code
    try:
        return status, json.loads(text) if text else None
    except ValueError:
        return status, text


def business_status(task: dict) -> str:
    return next(c["code"] for c in task["businessStatus"]["coding"] if c["system"] == BUSINESS_STATUS)


def progress(task: dict) -> dict:
    extension = next(e for e in task.get("extension", []) if e["url"] == "https://torch.mii.de/fhir/torch-job-progress")
    return {e["url"]: e.get("valueInteger") for e in extension["extension"]}


# --- TO-1 ----------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def running_job():
    """A job of a TORCH variant that waits for its FHIR server: (task URL, job id, TORCH URL,
    the RUNNING_* state it reached)."""
    with slow_fhir_server() as fhir, torch_variant({"TORCH_FHIR_URL": fhir}) as torch:
        status_url = submit(condition_crtdl(None), ["s6-patient"], torch_url=torch.url)
        job = status_url.rstrip("/").rsplit("/", 1)[1]
        task_url = f"{torch.url}/fhir/Task/{job}"
        deadline = time.monotonic() + 60
        while not (state := business_status(call("GET", task_url)[1])).startswith("RUNNING_PROCESS"):
            assert time.monotonic() < deadline, f"the job does not reach RUNNING_PROCESS_*, it is {state}"
            time.sleep(0.5)
        yield task_url, job, torch.url, state


def test_running_job_can_be_paused_and_resumed(running_job):
    """$resume returns the job to the state it was paused from."""
    task_url, _, _, state = running_job
    status, task = call("POST", f"{task_url}/$pause")
    assert (status, task["status"], business_status(task)) == (200, "on-hold", "PAUSED")
    status, task = call("POST", f"{task_url}/$resume")
    assert (status, task["status"], business_status(task)) == (200, "in-progress", state)


def test_priority_update_needs_the_current_version(running_job):
    task_url, job, _, _ = running_job
    body = {"resourceType": "Task", "id": job, "status": "in-progress", "intent": "order", "priority": "asap"}
    assert call("PUT", task_url, body)[0] == 428
    # A failed If-Match is 412 Precondition Failed (RFC 9110 13.1.1), which TORCH 1.1.0
    # answers. The TORCH Task API docs name 409 Conflict, which is a mistake of the docs.
    assert call("PUT", task_url, body, {"If-Match": 'W/"0"'})[0] == 412
    version = call("GET", task_url)[1]["meta"]["versionId"]
    status, task = call("PUT", task_url, body, {"If-Match": f'W/"{version}"'})
    assert (status, task["priority"]) == (200, "asap")


def search_ids(torch_url: str, query: str) -> list[str]:
    """Task ids of a search. With handling=strict TORCH rejects parameters it does not
    understand instead of ignoring them, so the filter is really applied."""
    status, bundle = call("GET", f"{torch_url}/fhir/Task?{query}", headers={"Prefer": "handling=strict"})
    assert status == 200, bundle
    return [e["resource"]["id"] for e in bundle.get("entry", [])]


def test_task_search_by_status_and_id(running_job):
    _, job, torch_url, state = running_job
    assert search_ids(torch_url, f"_id={job}&status={state},PAUSED") == [job]
    assert search_ids(torch_url, f"_id={job}&status=COMPLETED,FAILED") == []
    assert job in search_ids(torch_url, f"status={state}")


def test_running_job_can_be_cancelled(running_job):
    task_url, _, _, _ = running_job
    status, task = call("POST", f"{task_url}/$cancel")
    assert (status, task["status"], business_status(task)) == (200, "cancelled", "CANCELLED")
    assert business_status(call("GET", task_url)[1]) == "CANCELLED"
    # CANCELLED is final: the job cannot be paused or resumed any more. A second $cancel is
    # a no-op in TORCH 1.1.0 (200), although the docs name 409 for it.
    assert [call("POST", f"{task_url}/{op}")[0] for op in ("$pause", "$resume")] == [409, 409]


def test_unknown_job_is_404():
    status, outcome = call("GET", f"{TORCH_URL}/fhir/Task/s6-no-such-job")
    assert status == 404
    assert outcome["resourceType"] == "OperationOutcome"


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="D20, torch#1391: TORCH 1.1.0 answers DELETE /fhir/Task/{id} with 204, but the Task stays "
                   "readable and the result files stay on disk and on the file server. TORCH only marks the job "
                   "DELETED and removes its directory in a GC sweep (torch.gc.job-deletion-delay-ms, default 24 h)")
def test_deleted_job_and_its_results_are_gone():
    status_url = submit(json.loads(EXAMPLE_CRTDL.read_text()))
    result = Result(wait(status_url))
    task_url = f"{TORCH_URL}/fhir/Task/{result.job['id']}"
    assert call("DELETE", task_url)[0] == 204
    time.sleep(2)
    assert call("GET", task_url)[0] == 404
    assert call("GET", result.manifest["output"][0]["url"])[0] == 404


# --- TO-8, TO-11 ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def consent_job() -> Result:
    return extract(json.loads(CONSENT_CRTDL.read_text()))


def test_cohort_is_extracted_plus_excluded_patients(consent_job):
    summary = consent_job.summary
    excluded = sum(summary["Patient-Exclusions"].values())
    assert excluded > 0, "the consent example excludes no patient, so the check is empty"
    assert summary["Num-Cohort-Patients"] == summary["Num-Final-Patients"] + excluded
    assert len(consent_job.report("patient-exclusions")) == excluded
    assert len(consent_job.resources("Patient")) == summary["Num-Final-Patients"]


def test_task_progress_matches_the_job(consent_job):
    status, task = call("GET", f"{TORCH_URL}/fhir/Task/{consent_job.job['id']}")
    assert status == 200 and task["status"] == "completed"
    numbers = progress(task)
    assert numbers["cohortSize"] == consent_job.summary["Num-Cohort-Patients"]
    assert numbers["batchesCompleted"] == numbers["batchesTotal"] == len(consent_job.job["batches"])


def extract_data_requests() -> float:
    """Count of the Spring Boot http.server.requests metric for $extract-data, all statuses."""
    status, text = call("GET", f"{TORCH_URL}/actuator/prometheus")
    assert status == 200
    return sum(
        float(line.rsplit(" ", 1)[1]) for line in text.splitlines()
        if line.startswith("http_server_requests_seconds_count{") and 'uri="/fhir/$extract-data"' in line
    )


def test_prometheus_metrics_count_extractions():
    before = extract_data_requests()
    wait(submit(json.loads(EXAMPLE_CRTDL.read_text())))
    assert extract_data_requests() >= before + 1


# --- TO-7 ----------------------------------------------------------------------------------


def patient_crtdl(with_identifier: bool) -> dict:
    crtdl = json.loads(EXAMPLE_CRTDL.read_text())
    attributes = [{"attributeRef": "Patient.gender", "mustHave": False}]
    if with_identifier:
        attributes.append({"attributeRef": "Patient.identifier", "mustHave": False})
    crtdl["dataExtraction"]["attributeGroups"] = [
        {"id": "pat", "name": "Patient", "groupReference": PATIENT_PROFILE, "attributes": attributes}
    ]
    return crtdl


MASKED = [{"extension": [{"url": "http://hl7.org/fhir/StructureDefinition/data-absent-reason", "valueCode": "masked"}]}]


def test_patient_identifier_only_when_selected():
    """PatientPseudonymisiert requires an identifier (1..*), so without selection TORCH writes
    a masked one (data-absent-reason) instead of the values (TORCH docs, Redaction)."""
    without = extract(patient_crtdl(False)).resources("Patient")
    with_identifier = extract(patient_crtdl(True)).resources("Patient")
    assert without and all(p.get("identifier") == MASKED for p in without)
    assert any(i.get("value") for p in with_identifier for i in p.get("identifier", []))
    assert all(PATIENT_PROFILE in p["meta"]["profile"] for p in without + with_identifier)


# --- TO-12, TO-15 --------------------------------------------------------------------------


def test_evaluate_cohort_matches_the_extraction_cohort():
    crtdl = json.loads(EXAMPLE_CRTDL.read_text())
    status, cohort = call("POST", f"{TORCH_URL}/fhir/$evaluate-cohort", crtdl, content_type="application/json")
    assert status == 200 and cohort["resourceType"] == "List"
    assert len(cohort["entry"]) == extract(crtdl).summary["Num-Cohort-Patients"]
    # independent oracle: the example cohort is every male patient
    assert len(cohort["entry"]) == len(fhir_search("Patient?gender=male&_elements=id&_count=1000"))


def test_translate_cql():
    cohort = json.loads(EXAMPLE_CRTDL.read_text())["cohortDefinition"]
    status, cql = call("POST", f"{TORCH_URL}/fhir/$translate-cql", cohort, content_type="application/json")
    assert status == 200
    assert "define InInitialPopulation" in cql
    assert "'male'" in cql, "the CQL does not contain the gender criterion of the cohort"


def test_wrong_method_is_405():
    assert call("GET", f"{TORCH_URL}/fhir/$extract-data")[0] == 405


# --- ON-7 ----------------------------------------------------------------------------------


def test_date_filter_limits_extracted_diagnoses():
    """The filter name is the one the portal exports for the Diagnose profile (ontology DSE data)."""
    crtdl = json.loads(EXAMPLE_CRTDL.read_text())
    unfiltered = sorted(c["recordedDate"] for c in extract(crtdl).resources("Condition"))
    filtered_crtdl = copy.deepcopy(crtdl)
    diagnoses = next(g for g in filtered_crtdl["dataExtraction"]["attributeGroups"] if g["id"] == "diags")
    diagnoses["filter"] = [{"type": "date", "name": "recorded-date", "start": "2022-01-01", "end": "2023-12-31"}]
    filtered = sorted(c["recordedDate"] for c in extract(filtered_crtdl).resources("Condition"))
    assert filtered == [d for d in unfiltered if "2022-01-01" <= d[:10] <= "2023-12-31"]
    assert 0 < len(filtered) < len(unfiltered)
