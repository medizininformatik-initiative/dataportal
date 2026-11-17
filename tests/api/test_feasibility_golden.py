"""B3: feasibility counts on the MII test data, end to end through the portal backend,
CQL and the node's FHIR server (golden/feasibility.json).

Two checks per case. If only the portal check fails, the portal path is broken (ontology,
CCDL translation, CQL, broker). If both fail, the test data changed and the golden value
has to be reviewed.
"""

from __future__ import annotations

import pytest

from feasibility import Terminology, build_ccdl, load_golden_cases, oracle_count, run_feasibility

pytestmark = pytest.mark.smoke

CASES = load_golden_cases()
CASE_IDS = [case["id"] for case in CASES]


@pytest.fixture(scope="module")
def terminology(portal_access_token: str) -> Terminology:
    return Terminology(portal_access_token)


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_portal_count_matches_golden(case: dict, terminology: Terminology, portal_access_token: str):
    ccdl = build_ccdl(case, terminology)
    assert run_feasibility(ccdl, portal_access_token) == case["expected"]


@pytest.mark.parametrize("case", CASES, ids=CASE_IDS)
def test_fhir_oracle_matches_golden(case: dict):
    assert oracle_count(case) == case["expected"]
