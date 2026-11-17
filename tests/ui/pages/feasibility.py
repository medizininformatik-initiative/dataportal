"""Page actions for building and running a feasibility query in the UI. Paths follow
src/app/app-paths.ts of dataportal-ui, selectors its Cypress suite where one exists."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from helpers import PORTAL_URL

SEARCH_PATH = "/feasibility-query/search"
RESULT_PATH = "/feasibility-query/result"
LISTS = ("Inclusion", "Exclusion")


def open_search(page: Page) -> None:
    """Opens the feasibility search page. page.goto reloads the app and the query being
    built lives only in memory, so call this before adding the first criterion only."""
    page.goto(f"{PORTAL_URL}{SEARCH_PATH}")


def add_criterion(page: Page, code: str, context: str) -> None:
    """Searches the code on the feasibility search page, selects the row of the given
    context and adds it to the cohort selection."""
    search = page.locator("num-searchbar input").first
    search.fill(code)
    exact = re.compile(rf"^\s*{re.escape(context)}\s*$")
    row = page.locator("num-table tbody tr").filter(has_text=code).filter(
        has=page.locator("td", has_text=exact)
    )
    expect(row).to_have_count(1)
    row.locator("[data-cy=checkbox]").click()
    page.locator("num-action-bar button", has_text="Add to cohort selection").click()


def show_editor(page: Page) -> None:
    page.locator("num-action-bar button", has_text="Show cohort selection").click()
    expect(page.locator("#Stage")).to_be_visible()
    # The criteria boxes animate in. A drag that starts during the animation is lost.
    page.wait_for_timeout(1000)


def move_staged_criterion(page: Page, target: str) -> None:
    """Drags the first criterion from the staging area into the Inclusion or Exclusion
    list. Angular CDK starts a drag only after the pointer moved a few pixels, so the
    move is done in small steps."""
    assert target in LISTS
    handle = page.locator("#Stage .drag-handle").first
    box = handle.bounding_box()
    drop = page.locator(f"#{target}").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(x, y)
    page.mouse.down()
    for step in range(1, 11):
        page.mouse.move(x - step * 3, y + step * 3)
    page.mouse.move(drop["x"] + drop["width"] / 2, drop["y"] + drop["height"] / 2, steps=30)
    page.mouse.up()


def build_query(page: Page, case: dict) -> None:
    """Builds a golden case (one criterion per group, no filters) in the criteria editor:
    adds all criteria on the search page, then drags them from the staging area to their
    lists in the order they were added."""
    placements = []
    for target, groups in (("Inclusion", case["inclusion"]), ("Exclusion", case.get("exclusion") or [])):
        for group in groups:
            assert len(group) == 1, "OR groups are not supported by this helper yet"
            criterion = group[0]
            assert not {"valueConcepts", "attribute"} & criterion.keys(), "filters are not supported yet"
            placements.append((target, criterion))

    open_search(page)
    for _, criterion in placements:
        add_criterion(page, criterion["code"], criterion["context"])
    show_editor(page)
    for target, criterion in placements:
        move_staged_criterion(page, target)
        expect(page.locator(f"#{target}")).to_contain_text(criterion["code"])
    expect(page.locator("#Stage .cdk-drag")).to_have_count(0)


def send_query(page: Page) -> None:
    send = page.locator("button", has_text="Send Feasibility query")
    expect(send).to_be_enabled()
    send.click()
    page.wait_for_url(f"**{RESULT_PATH}")


def result_count(page: Page) -> int:
    """Waits until the query is completed and reads the patient counter digits."""
    expect(page.get_by_text("Query completed")).to_be_visible(timeout=90_000)
    digits = "".join(page.locator("num-patient-count .digit").all_inner_texts())
    return int(re.sub(r"\s", "", digits))


def detail_rows(page: Page) -> dict[str, int]:
    """Opens the result details dialog and returns patients per location."""
    page.locator("num-button.button-dialog-result-details button").click()
    dialog = page.locator("mat-dialog-container")
    expect(dialog.locator("num-table tbody tr").first).to_be_visible()
    rows = {}
    for row in dialog.locator("num-table tbody tr").all():
        cells = [c.strip() for c in row.locator("td").all_inner_texts() if c.strip()]
        rows[cells[0]] = int(cells[-1])
    return rows
