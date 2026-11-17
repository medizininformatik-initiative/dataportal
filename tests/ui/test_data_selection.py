"""C7/C8: feature (data) selection in the browser (UI-4, UI-6, UI-8, UI-9, UI-10)."""

from __future__ import annotations

import json
import pathlib
import re

import pytest
from playwright.sync_api import Page, expect

from feasibility import load_golden_cases
from ui.pages import data_selection as ds
from ui.pages.data_definition import download_data_definition, open_feature_selection_step, upload_crtdl
from ui.pages.feasibility import build_query
from ui.pages.portal import login

pytestmark = pytest.mark.smoke

GOLDEN = {case["id"]: case for case in load_golden_cases()}
FEATURE = "Medication administration"
REFERENCED = "Procedure"


def _groups_by_profile(crtdl: dict) -> dict[str, dict]:
    """Attribute groups by profile (last segment of groupReference). A feature created
    through a reference is named after its profile, e.g. 'MII PR Prozedur Procedure'."""
    return {g["groupReference"].rsplit("/", 1)[-1]: g for g in crtdl["dataExtraction"]["attributeGroups"]}


@pytest.fixture
def cohort(page: Page) -> Page:
    """Logged in with a cohort (leukocytes). The download needs a cohort criterion."""
    login(page)
    build_query(page, GOLDEN["leukocytes"])
    ds.open_from_navigation(page)
    return page


def test_only_if_referenced_is_offered_toggled_and_kept_in_the_crtdl(cohort: Page, tmp_path: pathlib.Path):
    """UI-4: a referenced feature offers 'Only if referenced' (on by default), the option
    can be switched, ends up as includeReferenceOnly in the CRTDL and survives an upload."""
    page = cohort
    ds.add_feature(page, FEATURE)
    ds.show_selection(page)

    ds.configure_feature(page, FEATURE)
    ds.open_tab(page, "References")
    ds.open_tab(page, "Part of")
    ds.add_reference(page, REFERENCED)
    ds.close_editor(page)
    # Medication administration also requires a medication reference; remove it so the
    # data definition can be downloaded (see test_download_is_blocked_...).
    ds.remove_unresolved_references(page)

    option = ds.only_if_referenced(page, REFERENCED)
    expect(option).to_have_attribute("aria-checked", "true")
    expect(ds.only_if_referenced(page, FEATURE)).to_have_count(0)
    option.click()
    expect(option).to_have_attribute("aria-checked", "false")
    option.click()
    expect(option).to_have_attribute("aria-checked", "true")

    path = download_data_definition(page, "s5-only-if-referenced", "crtdl", tmp_path)
    groups = _groups_by_profile(json.loads(path.read_text()))
    assert groups["Procedure"]["includeReferenceOnly"] is True
    assert groups["MedicationAdministration"].get("includeReferenceOnly") is not True
    linked = [g for a in groups["MedicationAdministration"]["attributes"] for g in a.get("linkedGroups", [])]
    assert groups["Procedure"]["id"] in linked

    upload_crtdl(page, path)
    open_feature_selection_step(page)
    # After the upload the feature carries the name from the CRTDL (its profile name).
    expect(ds.only_if_referenced(page, groups["Procedure"]["name"])).to_have_attribute("aria-checked", "true")


def test_unlinked_required_reference_shows_a_shortcut_to_the_field(page: Page):
    """UI-6: the warning on an unlinked reference opens the feature editor at that field."""
    login(page)
    ds.open_search(page)
    ds.add_feature(page, FEATURE)
    ds.show_selection(page)
    expect(ds.unresolved_references(page)).to_have_count(1)
    ds.follow_unresolved_reference_shortcut(page)
    active = page.locator(".tabs-container .tab.active, .mdc-tab--active")
    expect(active.filter(has_text=re.compile(r"^\s*references\s*$", re.I))).to_have_count(1)
    expect(active.filter(has_text="Medication")).to_have_count(1)


def test_download_is_blocked_while_a_required_reference_is_unresolved(cohort: Page):
    """UI-10: a feature with an unresolved required reference blocks the download."""
    page = cohort
    assert ds.download_enabled(page)
    ds.add_feature(page, FEATURE)
    ds.show_selection(page)
    assert not ds.download_enabled(page)
    ds.remove_unresolved_references(page)
    assert ds.download_enabled(page)


def test_empty_search_starts_with_pinned_profiles(page: Page):
    """UI-8: without a search term the core profiles come first."""
    login(page)
    ds.open_search(page)
    assert ds.result_names(page)[:3] == ["Diagnosis", "Procedure", "Laboratory test"]


def test_search_finds_profiles_by_field_description(page: Page):
    """UI-8: 'remission' occurs only in the description of Condition.abatement[x]."""
    login(page)
    ds.open_search(page)
    ds.search(page, "remission")
    assert "Diagnosis" in ds.result_names(page)


def test_add_all_results_and_numbered_duplicates(page: Page):
    """UI-9: all found profiles can be added at once; the same profile added twice gets a
    numbered name."""
    login(page)
    ds.open_search(page)
    ds.search(page, "Laboratory")
    found = ds.result_names(page)
    # The search also matches profiles whose field descriptions mention laboratories.
    assert {"Laboratory test", "Laboratory report", "Laboratory order"} <= set(found), found
    ds.add_all_results(page)
    ds.add_feature(page, "Diagnosis")
    ds.add_feature(page, "Diagnosis")
    ds.show_selection(page)
    assert set(found) <= set(ds.feature_names(page))
    titles = ds.feature_titles(page)
    assert titles.count("Diagnosis") == 1 and titles.count("Diagnosis (1)") == 1, titles


def test_new_feature_order_is_kept_in_the_crtdl(cohort: Page, tmp_path: pathlib.Path):
    """UI-9: features moved with the arrows keep their order in the downloaded CRTDL."""
    page = cohort
    ds.add_feature(page, "Diagnosis")
    ds.add_feature(page, "Procedure")
    ds.show_selection(page)
    ds.remove_unresolved_references(page)
    assert ds.feature_names(page)[1:] == ["Diagnosis", "Procedure"]
    ds.move_down(page, "Diagnosis")
    expect(page.locator("div.selection-box").nth(1)).to_have_attribute("data-cy", "Procedure")

    crtdl = json.loads(download_data_definition(page, "s5-order", "crtdl", tmp_path).read_text())
    profiles = [g["groupReference"].rsplit("/", 1)[-1] for g in crtdl["dataExtraction"]["attributeGroups"]]
    assert profiles.index("Procedure") < profiles.index("Diagnose"), profiles
