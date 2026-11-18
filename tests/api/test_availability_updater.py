"""S6: availability updater 0.4.2 with FDE reports from the node FHIR server.

AU-3   reads the elastic/content layout of ontology 5.x, loads the nodes and updates the counts
AU-4   a second run uses the new report only (input directory cleared), counts go down
ON-12  data selection availability (profile index)

Twelve crafted patients with a SNOMED CT procedure that the MII test data lacks give that
criterion a count of 10 (the updater rounds down to 0, 10, 100, ...). After the patients
are deleted, the next FDE and updater run must set it back to 0. The updater runs with
`compose up`, so the second run reuses the container of the first (tests/availability.py).
"""

from __future__ import annotations

import re

import pytest

from availability import UPDATER_DIR, Updater
from fde import run_fde
from helpers import portal_request, portal_token
from torch_client import delete_resources, env_file, put_resources

pytestmark = pytest.mark.smoke

PROCEDURE_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-prozedur/StructureDefinition/Procedure"
CODE = "410620009"  # Well child visit, not in the MII test data
PATIENTS = 12


def crafted() -> list[dict]:
    resources = []
    for i in range(PATIENTS):
        resources.append({"resourceType": "Patient", "id": f"s6-availability-{i}", "gender": "female"})
        resources.append({
            "resourceType": "Procedure", "id": f"s6-availability-procedure-{i}",
            "meta": {"profile": [PROCEDURE_PROFILE]}, "status": "completed",
            "category": {"coding": [{"system": "http://snomed.info/sct", "code": "387713003"}]},
            "code": {"coding": [{"system": "http://snomed.info/sct", "code": CODE}]},
            "subject": {"reference": f"Patient/s6-availability-{i}"}, "performedDateTime": "2024-01-01",
        })
    return resources


def availability() -> int:
    status, body = portal_request(f"/api/v6/terminology/entry/search?searchterm={CODE}&contexts=Procedure", token=portal_token())
    assert status == 200
    return next(r["availability"] for r in body["results"] if r["termcode"] == CODE)


@pytest.fixture(scope="module")
def runs():
    """Availability and updater log after a run with the crafted data and after a run
    without it."""
    updater = Updater()
    reports: dict[str, dict] = {}
    resources = crafted()
    try:
        put_resources(resources)
        for resource in run_fde():
            reports[f"{resource['resourceType']}/{resource['id']}"] = resource
        first_log = updater.run()
        first = availability()
        delete_resources(resources)
        resources = []
        for resource in run_fde():
            reports[f"{resource['resourceType']}/{resource['id']}"] = resource
        second_log = updater.run()
        yield {"first": (first, first_log), "second": (availability(), second_log)}
    finally:
        if resources:
            delete_resources(resources)
        delete_resources(list(reports.values()))
        updater.remove()


def test_updater_loads_the_ontology_and_updates_elasticsearch(runs):
    _, log = runs["first"]
    loaded = re.search(r"Loaded (\d+) ontology nodes", log)
    assert loaded and int(loaded.group(1)) > 0, log[-2000:]
    assert "Elasticsearch update complete" in log


def test_count_appears_with_data_and_goes_away_without(runs):
    assert runs["first"][0] == 10
    assert runs["second"][0] == 0


def test_default_report_server_is_the_fhir_server():
    assert env_file(UPDATER_DIR / ".env.default")["AVAILABILITY_REPORT_SERVER_BASE_URL"] == "http://fhir-server:8080/fhir"


@pytest.mark.xfail(strict=True, reason="D19: no component writes data selection availability; updater 0.4.2 "
                   "updates only the ontology index, so every profile shows availability 0")
def test_data_selection_shows_availability_for_profiles_with_data(runs):
    status, body = portal_request("/api/v6/profile/entry/search?searchterm=Prozedur&page-size=20", token=portal_token())
    assert status == 200
    procedure = next(r for r in body["results"] if r["url"] == PROCEDURE_PROFILE)
    assert procedure["availability"] > 0
