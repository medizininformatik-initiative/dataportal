"""C5: save a data definition, load it again after a reload, run it and delete it."""

from __future__ import annotations

import uuid

import pytest
from playwright.sync_api import Page, expect

from feasibility import Terminology, load_golden_cases
from ui.pages import saved_queries
from ui.pages.data_definition import run_feasibility_of_data_definition
from ui.pages.feasibility import build_query, result_count
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

CASE = {case["id"]: case for case in load_golden_cases()}["leukocytes-interpretation-high"]


@pytest.fixture
def terminology(portal_access_token: str) -> Terminology:
    return Terminology(portal_access_token)


def test_saved_data_definition_loads_runs_and_deletes(page: Page, terminology: Terminology):
    title = f"s5-saved-{uuid.uuid4().hex[:8]}"
    login(page)
    build_query(page, CASE, terminology)
    saved_queries.save_data_definition(page, title, "integration test")

    # page.goto reloads the app, so the loaded definition comes from the backend.
    saved_queries.open_saved(page)
    expect(saved_queries.tile(page, title)).to_have_count(1)
    saved_queries.load(page, title)
    expect(page.get_by_text("Leukocytes [#/volume] in Blood").first).to_be_visible()
    run_feasibility_of_data_definition(page)
    assert result_count(page) == CASE["expected"]

    saved_queries.open_saved(page)
    saved_queries.delete(page, title)
