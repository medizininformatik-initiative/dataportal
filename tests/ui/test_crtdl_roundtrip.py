"""C6: download a data definition, upload it again and run it (UI-11, UI-19)."""

from __future__ import annotations

import copy
import json
import pathlib
import zipfile

import pytest
from playwright.sync_api import Page, expect

from feasibility import Terminology, load_golden_cases
from ui.pages.data_definition import download_data_definition, run_feasibility_of_data_definition, upload_crtdl
from ui.pages.feasibility import build_query, result_count
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}


@pytest.fixture(scope="module")
def terminology(portal_access_token: str) -> Terminology:
    return Terminology(portal_access_token)


@pytest.fixture
def leukocytes_high_crtdl(page: Page, terminology: Terminology, tmp_path: pathlib.Path) -> pathlib.Path:
    """CRTDL downloaded after building 'leukocytes with interpretation H' in the browser."""
    login(page)
    build_query(page, GOLDEN["leukocytes-interpretation-high"], terminology)
    return download_data_definition(page, "s5-roundtrip", "crtdl", tmp_path)


def test_downloaded_crtdl_contains_the_query_and_runs_again(page: Page, leukocytes_high_crtdl: pathlib.Path):
    crtdl = json.loads(leukocytes_high_crtdl.read_text())
    [[criterion]] = crtdl["cohortDefinition"]["inclusionCriteria"]
    assert [t["code"] for t in criterion["termCodes"]] == ["26464-8"]
    assert [c["code"] for f in criterion["attributeFilters"] for c in f["selectedConcepts"]] == ["H"]

    # page.goto reloads the app, so the upload starts from an empty query.
    upload_crtdl(page, leukocytes_high_crtdl)
    expect(page.get_by_text("Leukocytes [#/volume] in Blood").first).to_be_visible()
    run_feasibility_of_data_definition(page)
    assert result_count(page) == GOLDEN["leukocytes-interpretation-high"]["expected"]


def test_project_summary_zip_matches_the_query(page: Page, terminology: Terminology, tmp_path: pathlib.Path):
    """UI-11: the CSV download contains the cohort criteria of the query."""
    login(page)
    build_query(page, GOLDEN["leukocytes"], terminology)
    archive = zipfile.ZipFile(download_data_definition(page, "s5-summary", "csv", tmp_path))
    assert {"Datendefinition.json", "EN_Inclusioncriteria.csv", "EN_Featureselection.csv"} <= set(archive.namelist())
    assert "26464-8" in archive.read("EN_Inclusioncriteria.csv").decode("utf-8-sig")


def test_old_crtdl_is_upgraded_on_upload(page: Page, leukocytes_high_crtdl: pathlib.Path, tmp_path: pathlib.Path):
    """UI-19: a CRTDL with the onset-date filter of ontology 4 is upgraded to recorded-date
    on upload, the user is told about the change, and the query still runs."""
    old = copy.deepcopy(json.loads(leukocytes_high_crtdl.read_text()))
    old["dataExtraction"]["attributeGroups"].append({
        "id": "diagnoses",
        "name": "Diagnoses",
        "groupReference": "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose",
        "attributes": [{"attributeRef": "Condition.code", "mustHave": False}],
        "filter": [{"type": "date", "name": "onset-date", "start": "2020-01-01", "end": "2025-12-31"}],
    })
    path = tmp_path / "old-onset-date.json"
    path.write_text(json.dumps(old))

    upload_crtdl(page, path)
    dialog = page.locator("mat-dialog-container")
    expect(dialog).to_contain_text("UPGRADE-1000001")
    expect(dialog).not_to_contain_text("VALIDATION-")
    page.keyboard.press("Escape")
    run_feasibility_of_data_definition(page)
    assert result_count(page) == GOLDEN["leukocytes-interpretation-high"]["expected"]
