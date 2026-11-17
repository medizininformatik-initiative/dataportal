"""C2/UI-3: filter dropdowns of the cohort search: order, search field, dependent options."""

from __future__ import annotations

import time

import pytest
from playwright.sync_api import Page, expect

from ui.pages.feasibility import open_search
from ui.pages.portal import login
from ui.pages.search_filters import (
    choose_option,
    close_filter,
    filter_labels,
    open_filter,
    option_names,
    search_in_open_filter,
)

pytestmark = pytest.mark.smoke


@pytest.fixture
def search_page(page: Page) -> Page:
    login(page)
    open_search(page)
    page.wait_for_load_state("networkidle")
    return page


def test_filters_are_ordered_module_context_terminology(search_page: Page):
    assert filter_labels(search_page) == ["CDS Modules", "Context", "Terminology"]


def test_dropdown_search_narrows_the_options(search_page: Page):
    open_filter(search_page, "CDS Modules")
    assert len(option_names(search_page)) > 1
    search_in_open_filter(search_page, "Onko")
    expect(search_page.locator(".mat-mdc-select-panel mat-option")).to_have_count(2)  # search field + 1
    assert option_names(search_page) == ["Onkologie"]


def _context_options_after_filtering(page: Page, before: int, timeout: float = 15) -> list[str]:
    """The app debounces the filter request, so the context options change shortly after
    the module dropdown closes. Polls until they differ from the unfiltered options."""
    deadline = time.monotonic() + timeout
    while True:
        open_filter(page, "Context")
        contexts = option_names(page)
        close_filter(page)
        if len(contexts) != before or time.monotonic() > deadline:
            return contexts
        page.wait_for_timeout(500)


def test_choosing_a_module_narrows_contexts_and_results(search_page: Page):
    open_filter(search_page, "Context")
    all_contexts = option_names(search_page)
    close_filter(search_page)

    open_filter(search_page, "CDS Modules")
    choose_option(search_page, "Onkologie")
    close_filter(search_page)
    # A dropdown with a selection shows the selection instead of its label.
    assert filter_labels(search_page) == ["Onkologie", "Context", "Terminology"]

    oncology_contexts = _context_options_after_filtering(search_page, len(all_contexts))
    assert 0 < len(oncology_contexts) < len(all_contexts)
    assert all(context.startswith("MII_Onkologie") for context in oncology_contexts), oncology_contexts

    # The result table follows the module filter; its last column is the context.
    rows = search_page.locator("num-table tbody tr")
    expect(rows.first).to_be_visible()
    contexts = [row.locator("td").last.inner_text().strip() for row in rows.all()[:10]]
    assert all(context.startswith("MII_Onkologie") for context in contexts), contexts
