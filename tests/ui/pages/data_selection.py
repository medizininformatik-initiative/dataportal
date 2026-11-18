"""Page actions for the feature (data) selection. Selectors follow the dataportal-ui
Cypress suite (dataSelectionSearch.cy.ts, dataSelectionOnlyIfReferenced.cy.ts)."""

from __future__ import annotations

import re
import time

from playwright.sync_api import Locator, Page, expect

from helpers import PORTAL_URL

SEARCH_PATH = "/data-selection/search"


def open_search(page: Page) -> None:
    """Opens the feature search. page.goto reloads the app and drops the current data
    definition, so use it before building one only."""
    page.goto(f"{PORTAL_URL}{SEARCH_PATH}")
    page.wait_for_load_state("networkidle")


def search(page: Page, term: str, timeout: float = 10) -> None:
    """Searches features. The search request is debounced, so this waits until the
    result table differs from before (or the timeout passes, e.g. for the same results)."""
    before = result_names(page)
    page.get_by_placeholder("Search for term or fields").fill(term)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        page.wait_for_timeout(300)
        page.wait_for_load_state("networkidle")
        if result_names(page) != before:
            return


def result_names(page: Page) -> list[str]:
    """Feature names in the result table (second cell; the first holds the checkbox). Read
    in one call, because the table is rebuilt while a search runs."""
    return page.locator("tbody tr").evaluate_all(
        "rows => rows.map(r => r.cells.length > 1 ? r.cells[1].innerText.trim() : '')"
    )


def add_all_results(page: Page) -> None:
    page.locator("thead [data-cy=checkbox]").first.click()
    page.get_by_role("button", name="Add to Selection").click()


def move_down(page: Page, name: str) -> None:
    feature_box(page, name).first.get_by_role("button", name="Move down").click()


def _row(page: Page, name: str) -> Locator:
    return page.locator("tbody tr").filter(has=page.locator("td", has_text=re.compile(rf"^\s*{re.escape(name)}\s*$")))


def add_feature(page: Page, name: str) -> None:
    """Searches the feature by name, ticks its row and adds it to the selection."""
    search(page, name)
    row = _row(page, name).first
    expect(row).to_be_visible()
    row.locator("[data-cy=checkbox]").click()
    page.get_by_role("button", name="Add to Selection").click()


def show_selection(page: Page) -> None:
    page.get_by_role("button", name="Show Selection").click()
    page.wait_for_url("**/data-selection/overview")
    page.wait_for_load_state("networkidle")


def feature_titles(page: Page) -> list[str]:
    """Displayed feature titles. Features with the same name are numbered ('Diagnosis (1)')
    in the title only; their data-cy keeps the plain name."""
    return page.locator("div.selection-box").evaluate_all("els => els.map(e => e.innerText.split('\\n')[0].trim())")


def feature_box(page: Page, name: str) -> Locator:
    return page.locator(f'div.selection-box[data-cy="{name}"]')


def feature_names(page: Page) -> list[str]:
    return page.locator("div.selection-box").evaluate_all("els => els.map(e => e.getAttribute('data-cy'))")


def feature_menu(page: Page, name: str, item: str) -> None:
    feature_box(page, name).first.get_by_role("button", name="Options").click()
    page.locator(".mat-mdc-menu-item", has_text=item).click()


def configure_feature(page: Page, name: str) -> None:
    feature_menu(page, name, "Configure")
    page.wait_for_url("**/query-editor/feature/**")
    page.wait_for_load_state("networkidle")


def open_tab(page: Page, label: str) -> None:
    page.locator(".tabs-container .tab, .mdc-tab__text-label").filter(
        has_text=re.compile(rf"^\s*{re.escape(label)}\s*$", re.I)
    ).first.click()


def add_reference(page: Page, target: str) -> None:
    """References tab: links the feature being edited to the feature named target."""
    page.locator("num-button button", has_text="Add new reference").click()
    modal = page.locator("num-modal-window")
    expect(modal).to_be_visible()
    modal.locator(f'.divider[data-cy="{target}"] [data-cy=checkbox]').click()
    modal.locator("num-button button").first.click()
    expect(modal).to_be_hidden()


def close_editor(page: Page) -> None:
    page.get_by_role("button", name="Close").click()
    page.wait_for_url("**/data-selection/overview")
    page.wait_for_load_state("networkidle")


def only_if_referenced(page: Page, name: str) -> Locator:
    """The 'Only if referenced' checkbox of a feature box; only referenced features have one."""
    return feature_box(page, name).locator("num-reference-col [data-cy=checkbox]")


def unresolved_references(page: Page) -> Locator:
    """Reference tiles that show the 'unresolved reference' warning."""
    return page.locator("num-profile-reference-tile").filter(has=page.locator("num-missing-filter"))


def follow_unresolved_reference_shortcut(page: Page) -> None:
    """Clicks the warning text of the first unresolved reference. The click handler sits
    on the inner message span."""
    unresolved_references(page).first.locator("num-missing-filter .warning-message > span").first.click()
    page.wait_for_url("**/query-editor/feature/**")


def remove_unresolved_references(page: Page) -> None:
    while unresolved_references(page).count():
        unresolved_references(page).first.locator("fa-icon[icon=trash]").first.click()
        page.wait_for_timeout(300)


def open_from_navigation(page: Page) -> None:
    """Opens the feature selection through the side navigation, which keeps the current
    data definition (page.goto would reload the app)."""
    page.locator("[data-cy=nav-data-selection]").click()
    page.wait_for_load_state("networkidle")


def download_enabled(page: Page) -> bool:
    return page.locator("[data-cy=download-crtdl-button]").first.is_enabled()


def select_code(page: Page, code: str, system: str) -> Locator:
    """Feature editor, code filter tab: searches the code and ticks the row of the given
    terminology (display name, e.g. 'ICD-10-GM'). Returns the row locator factory input."""
    page.get_by_placeholder("Enter concept or term code").filter(visible=True).fill(code)
    row = code_row(page, code, system)
    expect(row).to_be_visible()
    row.locator("[data-cy=checkbox]").click()
    return row


def code_row(page: Page, code: str, system: str) -> Locator:
    exact = lambda text: re.compile(rf"^\s*{re.escape(text)}\s*$")
    return (
        page.locator("tbody tr").filter(visible=True)
        .filter(has=page.locator("td", has_text=exact(code)))
        .filter(has=page.locator("td", has_text=exact(system)))
        .first
    )
