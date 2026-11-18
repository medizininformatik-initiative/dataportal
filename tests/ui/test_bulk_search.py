"""UI-17: bulk search keeps the order of the entered codes, reports a duplicate once and
lists unknown codes as not found."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from helpers import PORTAL_URL
from ui.pages.portal import login
from ui.pages.search_filters import choose_option, close_filter

pytestmark = pytest.mark.smoke

BULK_SEARCH_PATH = "/feasibility-query/bulk-search"


def _choose(page: Page, label: str, option: str) -> None:
    page.locator("num-bulk-search-input mat-select").filter(has_text=label).click()
    page.locator(".mat-mdc-select-panel").wait_for()
    choose_option(page, option)
    if page.locator(".mat-mdc-select-panel").count():
        close_filter(page)


def test_bulk_search_keeps_input_order_and_reports_unknown_codes(page: Page):
    login(page)
    page.goto(f"{PORTAL_URL}{BULK_SEARCH_PATH}")
    page.wait_for_load_state("networkidle")
    form = page.locator("num-bulk-search-input")
    form.locator("textarea").fill("B05.3\nC34.1\nA15.0\nC34.1\nXXX.9")
    _choose(page, "Terminology", "ICD-10-GM")
    _choose(page, "Context", "Diagnose")
    form.locator("button", has_text="Search").click()

    expect(page.get_by_role("tab", name="Found (3)")).to_be_visible()
    expect(page.get_by_role("tab", name="Not found (1)")).to_be_visible()
    codes = [row.locator("td").last.inner_text().strip() for row in page.locator("num-table tbody tr").all()]
    assert codes == ["B05.3", "C34.1", "A15.0"]

    page.get_by_role("tab", name="Not found (1)").click()
    expect(page.get_by_text("XXX.9").first).to_be_visible()
