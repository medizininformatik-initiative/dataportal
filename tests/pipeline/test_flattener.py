"""S7: fhir-flattener called directly with ViewDefinition/$run.

FF-1  CSV output follows RFC 4180: quotes, commas and line breaks in values survive
FF-2  no data leaks from one run into the next, and the index page loads
"""

from __future__ import annotations

import csv
import io
import json
import urllib.request

import pytest

from helpers import wait_for_url

FLATTENER_URL = "http://localhost:8088"

VIEW = {
    "resourceType": "ViewDefinition",
    "name": "conditions",
    "resource": "Condition",
    "status": "active",
    "select": [{"column": [{"path": "id", "name": "id"}, {"path": "note.text.first()", "name": "note"}]}],
}

NASTY = 'He said "no", then left,\nnext line\r\nand a ; too'


@pytest.fixture(scope="module", autouse=True)
def _wait_for_flattener():
    wait_for_url(f"{FLATTENER_URL}/", expect_status=None)


def condition(cid: str, note: str) -> dict:
    return {"resourceType": "Condition", "id": cid, "subject": {"reference": "Patient/p1"}, "note": [{"text": note}]}


def run_raw(resources: list[dict], extra: list[dict] | None = None) -> str:
    body = {
        "resourceType": "Parameters",
        "parameter": (extra or []) + [{"name": "viewDefinition", "resource": VIEW}]
        + [{"name": "resources", "resource": r} for r in resources],
    }
    request = urllib.request.Request(
        f"{FLATTENER_URL}/fhir/ViewDefinition/$run", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/fhir+json", "Accept": "text/csv"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read().decode()


def run_csv(resources: list[dict]) -> list[dict]:
    """Rows by the column names of VIEW, because the CSV has no header (D16)."""
    columns = [c["name"] for c in VIEW["select"][0]["column"]]
    return list(csv.DictReader(io.StringIO(run_raw(resources), newline=""), fieldnames=columns))


def test_csv_quotes_commas_and_line_breaks():
    rows = run_csv([condition("c1", NASTY), condition("c2", "plain")])
    assert {r["id"]: r["note"] for r in rows} == {"c1": NASTY, "c2": "plain"}


def test_runs_do_not_leak_into_each_other():
    first = run_csv([condition("first-1", "a"), condition("first-2", "b")])
    second = run_csv([condition("second-1", "c")])
    assert sorted(r["id"] for r in first) == ["first-1", "first-2"]
    assert [r["id"] for r in second] == ["second-1"]


@pytest.mark.xfail(strict=True, reason="D16 (low): fhir-flattener 0.1.0-alpha.10 writes CSV without a header "
                   "row and rejects the SQL-on-FHIR $run parameter header")
def test_csv_has_a_header_row():
    text = run_raw([condition("c1", "a")], [{"name": "header", "valueBoolean": True}])
    assert text.splitlines()[0] == "id,note"


def test_index_page_loads():
    with urllib.request.urlopen(f"{FLATTENER_URL}/", timeout=30) as response:
        assert response.status == 200
        assert "<html" in response.read().decode(errors="replace").lower()
