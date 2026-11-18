"""UI-7, UI-13, UI-14: upload replaces the query, English labels, profile details and
highlighting, and a code that exists in two terminologies."""

from __future__ import annotations

import json
import pathlib
import re

import pytest
from playwright.sync_api import Page, expect

from feasibility import Terminology, build_ccdl, load_golden_cases
from helpers import DATA_NODE_DIR
from ui.pages import data_selection as ds
from ui.pages.data_definition import download_data_definition, upload_crtdl_from_action_bar
from ui.pages.feasibility import build_query, open_search
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}
AVAILABILITY_EN = {"Unknown", "Very low", "Low", "Medium", "High", "Very high"}
ICD10GM = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"


def test_upload_replaces_the_query_being_built(page: Page, portal_access_token: str, tmp_path: pathlib.Path):
    """UI-7 (#528): uploading a CRTDL replaces the current query instead of merging."""
    crtdl = json.loads((DATA_NODE_DIR / "torch" / "queries" / "example-crtdl.json").read_text())
    crtdl["cohortDefinition"] = build_ccdl(GOLDEN["gender-male"], Terminology(portal_access_token))
    path = tmp_path / "gender-male.json"
    path.write_text(json.dumps(crtdl))

    login(page)
    build_query(page, GOLDEN["leukocytes"])
    upload_crtdl_from_action_bar(page, path)
    expect(page.get_by_text("Inclusion criteria (1)").first).to_be_visible()
    expect(page.get_by_text("Leukocytes [#/volume] in Blood")).to_have_count(0)


def test_availability_labels_are_english(page: Page):
    """UI-7 (#584): the availability column of the criteria search is translated."""
    login(page)
    open_search(page)
    page.locator("num-searchbar input").first.fill("Leukocytes")
    rows = page.locator("num-table tbody tr")
    expect(rows.first).to_be_visible()
    labels = set(rows.evaluate_all("rows => rows.map(r => r.cells[2] ? r.cells[2].innerText.trim() : '')"))
    assert labels and labels <= AVAILABILITY_EN, labels


def test_profile_details_show_description_and_fields(page: Page):
    """UI-13 (#618): the details panel of a search hit shows its description and fields."""
    login(page)
    ds.open_search(page)
    ds.search(page, "remission")
    page.locator("tbody tr").filter(has_text="Diagnosis").first.locator("td").nth(1).click()
    panel = page.locator("text=Description").locator("xpath=ancestor::*[contains(., 'Fields')][1]")
    expect(panel).to_contain_text("A clinical diagnosis of a patient.")
    expect(panel).to_contain_text("abatement")


def test_feature_search_highlights_matches(page: Page):
    """UI-13 (#620): the search of the selected features filters them and marks the match."""
    login(page)
    ds.open_search(page)
    ds.add_feature(page, "Diagnosis")
    ds.add_feature(page, "Procedure")
    ds.show_selection(page)
    page.get_by_placeholder("Enter search text").fill("Diag")
    expect(page.locator("div.selection-box")).to_have_count(1)
    assert ds.feature_names(page) == ["Diagnosis"]
    marks = page.locator("div.selection-box mark")
    expect(marks.first).to_have_text(re.compile("^Diag$", re.I))


def test_same_code_in_two_terminologies_selects_only_one(page: Page, tmp_path: pathlib.Path):
    """UI-14 (#626): I26 exists in ICD-10-GM and Alpha-ID; selecting it in ICD-10-GM must
    not select the Alpha-ID code, and the CRTDL contains the ICD-10-GM code only."""
    login(page)
    build_query(page, GOLDEN["leukocytes"])
    ds.open_from_navigation(page)
    ds.add_feature(page, "Diagnosis")
    ds.show_selection(page)
    ds.remove_unresolved_references(page)
    ds.configure_feature(page, "Diagnosis")
    ds.open_tab(page, "Code Filter")
    ds.select_code(page, "I26", "ICD-10-GM")
    expect(page.get_by_role("tab", name="Selected code filter (1)")).to_be_visible()
    expect(ds.code_row(page, "I26", "ICD-10-GM").locator("[data-cy=checkbox]")).to_have_attribute("aria-checked", "true")
    expect(ds.code_row(page, "I26", "Alpha-ID").locator("[data-cy=checkbox]")).to_have_attribute("aria-checked", "false")
    ds.close_editor(page)

    crtdl = json.loads(download_data_definition(page, "s5-i26", "crtdl", tmp_path).read_text())
    diagnoses = next(g for g in crtdl["dataExtraction"]["attributeGroups"] if g["groupReference"].endswith("/Diagnose"))
    codes = [(c["system"], c["code"]) for f in diagnoses.get("filter", []) for c in f.get("codes", f.get("selectedConcepts", []))]
    assert codes == [(ICD10GM, "I26")], diagnoses.get("filter")
