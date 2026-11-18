"""C4: build a feasibility query in the browser, run it and read the count (UI-1, UI-5).
The expected counts are the golden values of golden/feasibility.json, which
tests/api/test_feasibility_golden.py checks against the API and a FHIR search oracle."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from feasibility import load_golden_cases
from ui.pages.feasibility import build_query, detail_rows, result_count, send_query
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}
UI_CASES = ["leukocytes", "exclusion-leukocytes-without-lung-cancer"]


@pytest.mark.parametrize("case_id", UI_CASES)
def test_query_in_browser_shows_golden_count(page: Page, case_id: str):
    case = GOLDEN[case_id]
    login(page)
    build_query(page, case)
    send_query(page)
    assert result_count(page) == case["expected"]


def test_result_details_show_count_per_location(page: Page):
    case = GOLDEN["leukocytes"]
    login(page)
    build_query(page, case)
    send_query(page)
    assert result_count(page) == case["expected"]
    # The direct broker reports one location.
    assert list(detail_rows(page).values()) == [case["expected"]]
