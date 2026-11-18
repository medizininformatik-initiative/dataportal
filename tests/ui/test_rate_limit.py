"""S6, UI-18: the UI shows the soft quota error of the backend.

The browser talks to the regular backend through the proxy. The test answers the query
POST with the 429 the quota backend variant returned for a real request
(tests/conftest.py quota_exceeded), so status, headers and body are the backend's own.
"""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, Route, expect

from feasibility import load_golden_cases
from ui.pages.feasibility import build_query
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}


@pytest.mark.xfail(strict=True, reason="D23: dataportal-ui 7.3.4-rc4 ignores the 429 of the query POST and "
                   "shows 'Feasibility query is being processed' with 0 patients without end")
def test_quota_error_is_shown(page: Page, quota_exceeded):
    status, headers, body = quota_exceeded
    assert status == 429

    def answer(route: Route) -> None:
        if route.request.method == "POST":
            route.fulfill(status=status, headers=headers, body=body)
        else:
            route.continue_()

    login(page)
    build_query(page, GOLDEN["leukocytes"])
    page.route(re.compile(r".*/api/v6/query/feasibility/?$"), answer)
    page.locator("button", has_text="Send Feasibility query").click()
    expect(page.get_by_text(re.compile(r"quota|too many requests|FEAS-10002", re.IGNORECASE)).first).to_be_visible(timeout=30_000)
