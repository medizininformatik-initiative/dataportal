"""Page actions for downloading and uploading a data definition (CRTDL)."""

from __future__ import annotations

import pathlib

from playwright.sync_api import Page, expect

from helpers import PORTAL_URL

DATA_DEFINITION_PATH = "/data-query/cohort-definition"
FORMATS = {"crtdl": "download-format-crtdl", "csv": "download-format-csv"}


def download_data_definition(page: Page, title: str, fmt: str, directory: pathlib.Path) -> pathlib.Path:
    """Downloads the current data definition from the action bar as CRTDL (JSON) or as
    project summary (CSV files in a ZIP)."""
    page.locator("[data-cy=download-crtdl-button]").first.click()
    modal = page.locator("[data-cy=download-modal]")
    modal.get_by_placeholder("Title").fill(title)
    modal.locator(f"[data-cy={FORMATS[fmt]}]").check()
    with page.expect_download() as download:
        modal.locator("[data-cy=save-file-button] button").click()
    path = directory / download.value.suggested_filename
    download.value.save_as(path)
    return path


def upload_crtdl(page: Page, path: pathlib.Path) -> None:
    """Opens the data definition page and uploads a CRTDL file."""
    page.goto(f"{PORTAL_URL}{DATA_DEFINITION_PATH}")
    page.locator("[data-cy=upload-crtdl]").set_input_files(str(path))


def run_feasibility_of_data_definition(page: Page) -> None:
    feasibility = page.get_by_role("button", name="Feasibility Query")
    expect(feasibility).to_be_enabled()
    feasibility.click()
    page.wait_for_url("**/feasibility-query/result")
