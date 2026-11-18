"""Page actions for the filter dropdowns of the cohort search ("Refine Your Search")."""

from __future__ import annotations

import re

from playwright.sync_api import Locator, Page

OPTION_LABEL = re.compile(r"^(?P<name>.+?) \((?P<count>\d+)\)$")


def filter_select(page: Page, label: str) -> Locator:
    return page.locator("div.filter-container mat-select").filter(has_text=label)


def filter_labels(page: Page) -> list[str]:
    return [t.strip() for t in page.locator("div.filter-container mat-select").all_inner_texts()]


def open_filter(page: Page, label: str) -> None:
    filter_select(page, label).click()
    page.locator(".mat-mdc-select-panel").wait_for()


def close_filter(page: Page) -> None:
    """Closes the open dropdown and waits until the other filters and the results are
    updated (one backend request each)."""
    page.keyboard.press("Escape")
    page.locator(".mat-mdc-select-panel").wait_for(state="detached")
    page.wait_for_load_state("networkidle")


def option_names(page: Page) -> list[str]:
    """Names of the options of the open dropdown, without their counts. The first option
    holds the search field and has no name."""
    names = []
    for text in page.locator(".mat-mdc-select-panel mat-option").all_inner_texts():
        match = OPTION_LABEL.match(text.strip())
        if match:
            names.append(match["name"].strip())
    return names


def search_in_open_filter(page: Page, text: str) -> None:
    """Types into the search field of the open dropdown. The field sits in a disabled
    option, so Playwright's enabled check is skipped; a user clicks into it the same way."""
    field = page.locator(".mat-mdc-select-panel input").first
    field.click(force=True)
    page.keyboard.type(text)


def choose_option(page: Page, name: str) -> None:
    for option in page.locator(".mat-mdc-select-panel mat-option").all():
        match = OPTION_LABEL.match(option.inner_text().strip())
        if match and match["name"].strip() == name:
            option.click()
            return
    raise AssertionError(f"no option {name!r} in {option_names(page)}")
