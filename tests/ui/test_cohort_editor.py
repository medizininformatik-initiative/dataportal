"""UI-12: time period for all criteria at once, and codes in the reference selection."""

from __future__ import annotations

import json
import re
import pathlib
import urllib.parse

import pytest
from playwright.sync_api import Page, expect

from feasibility import load_golden_cases
from helpers import portal_request
from ui.pages.data_definition import download_data_definition
from ui.pages.feasibility import (
    add_criterion,
    apply_time_period_to_all,
    build_query,
    open_criterion_tab,
    open_search,
    open_staged_criterion_editor,
    show_editor,
)
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}


def test_time_period_is_applied_to_all_criteria(page: Page, tmp_path: pathlib.Path):
    login(page)
    build_query(page, GOLDEN["exclusion-leukocytes-without-lung-cancer"])
    apply_time_period_to_all(page, "1/1/2020", "12/31/2025", criteria=2)

    boxes = page.locator("#Inclusion .cdk-drag, #Exclusion .cdk-drag")
    expect(boxes).to_have_count(2)
    for box in boxes.all():
        expect(box).to_contain_text("From 01.01.2020 to 31.12.2025")

    crtdl = json.loads(download_data_definition(page, "s5-time", "crtdl", tmp_path).read_text())
    cohort = crtdl["cohortDefinition"]
    criteria = [c for group in cohort["inclusionCriteria"] + cohort.get("exclusionCriteria", []) for c in group]
    assert [c.get("timeRestriction") for c in criteria] == [{"afterDate": "2020-01-01", "beforeDate": "2025-12-31"}] * 2


def test_reference_selection_shows_codes(page: Page, portal_access_token: str):
    """A specimen criterion references diagnoses (criteria set Diagnose/icd-10-gm); the
    selection lists them with terminology and code."""
    query = urllib.parse.urlencode({"searchterm": "", "contexts": "Specimen", "page-size": 1})
    status, hits = portal_request(f"/api/v6/terminology/entry/search?{query}", token=portal_access_token)
    assert status == 200 and hits["results"], hits
    login(page)
    open_search(page)
    add_criterion(page, hits["results"][0]["termcode"], "Specimen")
    show_editor(page)
    open_staged_criterion_editor(page)
    open_criterion_tab(page, "References")

    expect(page.locator("thead th").filter(has_text="Terminology code")).to_have_count(1)
    first = page.locator("tbody tr").first.locator("td")
    expect(first.nth(2)).to_have_text("ICD-10-GM")
    expect(first.last).to_have_text(re.compile(r"^\s*[A-Z]\d\d(\.\d+)?\s*$"))
