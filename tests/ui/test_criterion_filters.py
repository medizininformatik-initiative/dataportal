"""C3/UI-2: configure filters in the criterion editor, run the query in the browser and
compare the count with the golden value of golden/feasibility.json.

Covers an attribute filter (interpretation, encounter status), a value filter (gender),
an AND of two criteria and an exclusion with a filter.
"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from feasibility import Terminology, load_golden_cases
from ui.pages.feasibility import build_query, result_count, send_query
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}
CASES = [
    "leukocytes-interpretation-high",
    "inpatient-encounter-finished",
    "gender-male",
    "and-male-with-leukocytes",
    "exclusion-leukocytes-not-high",
]


@pytest.fixture(scope="module")
def terminology(portal_access_token: str) -> Terminology:
    return Terminology(portal_access_token)


@pytest.mark.parametrize("case_id", CASES)
def test_filtered_query_in_browser_shows_golden_count(page: Page, terminology: Terminology, case_id: str):
    case = GOLDEN[case_id]
    login(page)
    build_query(page, case, terminology)
    send_query(page)
    assert result_count(page) == case["expected"]
