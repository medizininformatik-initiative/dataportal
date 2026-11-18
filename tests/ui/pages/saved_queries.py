"""Page actions for saving data definitions and the 'Saved data definitions' page.
Selectors follow the dataportal-ui Cypress suite (savedQueries.cy.ts, cohortResult.cy.ts)."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from helpers import PORTAL_URL

SAVED_PATH = "/saved-queries"


def save_data_definition(page: Page, title: str, comment: str) -> None:
    page.locator("[data-cy=save-cohort-button]").first.click()
    modal = page.locator("num-save-dataquery-modal")
    expect(modal).to_be_visible()
    modal.locator("[data-cy=dialog-title-input]").fill(title)
    modal.locator("[data-cy=dialog-comment-input]").fill(comment)
    modal.locator("button", has_text="Save").click()
    expect(modal).to_be_hidden()


def open_saved(page: Page) -> None:
    page.goto(f"{PORTAL_URL}{SAVED_PATH}")
    page.wait_for_load_state("networkidle")


def tile(page: Page, title: str) -> Locator:
    return page.locator(".saved-query-tile").filter(has_text=title)


def load(page: Page, title: str) -> None:
    tile(page, title).locator("button", has_text="Load Data Definition").click()
    page.wait_for_url("**/data-query/**")
    page.wait_for_load_state("networkidle")


def delete(page: Page, title: str) -> None:
    tile(page, title).locator("[data-cy=saved-query-delete-icon]").click()
    page.locator("button", has_text="Delete").last.click()
    expect(tile(page, title)).to_have_count(0)
