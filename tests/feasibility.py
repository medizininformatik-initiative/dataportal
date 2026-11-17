"""Feasibility queries against the data portal backend, built from the golden cases in
golden/feasibility.json, and an independent FHIR search oracle for the same cases.

A criterion in a golden case names a term code, its ontology context and optional filter
values. It is resolved through the backend terminology API (entry search, criteria
profile data, UI profile, value set search), so a case also fails if the ontology no
longer offers the criterion, the filter or the concept.

CCDL semantics: inclusionCriteria is an AND of OR groups, exclusionCriteria is an OR of
AND groups.
"""

from __future__ import annotations

import json
import pathlib
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache

from helpers import (
    DATA_NODE_DIR,
    PORTAL_BACKEND_URL,
    get_fhir_access_token,
    portal_request,
    portal_ssl_context,
)

GOLDEN_FILE = pathlib.Path(__file__).resolve().parent / "golden" / "feasibility.json"
CCDL_VERSION = "http://to_be_decided.com/draft-1/schema#"
FHIR_BASE_URL = "https://fhir.localhost:444/fhir"
FHIR_CA_CERT = DATA_NODE_DIR / "auth" / "cert.pem"


def load_golden_cases() -> list[dict]:
    return json.loads(GOLDEN_FILE.read_text())["cases"]


# --- Resolving criteria through the backend ------------------------------------------


class Terminology:
    """Looks up criteria, UI profiles and value set concepts with one portal token."""

    def __init__(self, token: str):
        self.token = token
        self._ui_profiles: dict[str, dict] | None = None

    def _get(self, path: str, params: dict) -> object:
        status, body = portal_request(f"{path}?{urllib.parse.urlencode(params)}", token=self.token)
        assert status == 200, f"GET {path} {params} -> {status}: {body}"
        return body

    def ui_profile(self, name: str) -> dict:
        if self._ui_profiles is None:
            profiles = self._get("/api/v6/terminology/ui-profile", {})
            self._ui_profiles = {p["name"]: p for p in profiles}
        return self._ui_profiles[name]

    def criterion(self, spec: dict) -> dict:
        """Builds a CCDL criterion from a golden spec: code, context and optional
        valueConcepts or attribute {code, concepts}."""
        hits = self._get("/api/v6/terminology/entry/search", {"searchterm": spec["code"], "page-size": 50})
        matches = [
            r for r in hits["results"] if r["termcode"] == spec["code"] and r["context"] == spec["context"]
        ]
        assert matches, f"ontology has no criterion {spec['code']} in context {spec['context']}"
        entry = self._get("/api/v6/terminology/criteria-profile-data", {"ids": matches[0]["id"]})[0]
        criterion = {"termCodes": entry["termCodes"], "context": entry["context"]}
        profile = self.ui_profile(entry["uiProfileId"])

        if "valueConcepts" in spec:
            definition = profile["valueDefinition"]
            assert definition and definition["type"] == "concept", (
                f"{entry['uiProfileId']} has no concept value filter"
            )
            criterion["valueFilter"] = {
                "type": "concept",
                "selectedConcepts": self._concepts(definition, spec["valueConcepts"]),
            }

        if "attribute" in spec:
            wanted = spec["attribute"]
            definitions = [
                a for a in profile["attributeDefinitions"] if a["attributeCode"]["code"] == wanted["code"]
            ]
            assert definitions, f"{entry['uiProfileId']} has no attribute {wanted['code']}"
            definition = definitions[0]
            criterion["attributeFilters"] = [
                {
                    "type": "concept",
                    "attributeCode": definition["attributeCode"],
                    "selectedConcepts": self._concepts(definition, wanted["concepts"]),
                }
            ]
        return criterion

    def _concepts(self, definition: dict, codes: list[str]) -> list[dict]:
        """Resolves codes to term codes: from selectableConcepts, else by searching the
        referenced value sets."""
        found = {c["code"]: c for c in definition.get("selectableConcepts") or []}
        for value_set in definition.get("referencedValueSet") or []:
            for code in codes:
                if code in found:
                    continue
                hits = self._get(
                    "/api/v6/codeable-concept/entry/search",
                    {"searchterm": code, "value-sets": value_set, "page-size": 50},
                )
                for hit in hits["results"]:
                    if hit["termCode"]["code"] == code:
                        found[code] = hit["termCode"]
        missing = [c for c in codes if c not in found]
        assert not missing, f"value set of the filter does not offer {missing}"
        return [found[c] for c in codes]


def build_ccdl(case: dict, terminology: Terminology) -> dict:
    ccdl = {
        "version": CCDL_VERSION,
        "display": f"golden case {case['id']}",
        "inclusionCriteria": [[terminology.criterion(c) for c in group] for group in case["inclusion"]],
    }
    if case.get("exclusion"):
        ccdl["exclusionCriteria"] = [[terminology.criterion(c) for c in group] for group in case["exclusion"]]
    return ccdl


# --- Running a query -----------------------------------------------------------------


def run_feasibility(ccdl: dict, token: str, timeout: float = 120) -> int:
    """Posts the CCDL and waits until the site result arrives. The summary result shows 0
    until then, so the detailed result (one line per site) marks completion."""
    request = urllib.request.Request(
        f"{PORTAL_BACKEND_URL}/api/v6/query/feasibility",
        data=json.dumps(ccdl).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, context=portal_ssl_context(), timeout=60) as response:
            location = response.headers["Location"]
    except urllib.error.HTTPError as error:
        raise AssertionError(f"POST feasibility query -> {error.code}: {error.read().decode()}") from None

    query_id = location.rstrip("/").split("/")[-1]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status, body = portal_request(f"/api/v6/query/feasibility/{query_id}/detailed-result", token=token)
        if status == 200 and body.get("resultLines"):
            return body["totalNumberOfPatients"]
        time.sleep(1)
    raise TimeoutError(f"feasibility query {query_id} had no site result after {timeout}s")


# --- FHIR search oracle --------------------------------------------------------------


@lru_cache(maxsize=1)
def _fhir_token() -> str:
    return get_fhir_access_token()


def _fhir_search(query: str) -> list[dict]:
    """Returns all resources of a FHIR search, following the next links."""
    context = ssl.create_default_context(cafile=str(FHIR_CA_CERT))
    url = f"{FHIR_BASE_URL}/{query}"
    resources: list[dict] = []
    while url:
        request = urllib.request.Request(
            url, headers={"Accept": "application/fhir+json", "Authorization": f"Bearer {_fhir_token()}"}
        )
        with urllib.request.urlopen(request, context=context, timeout=60) as response:
            bundle = json.load(response)
        resources += [e["resource"] for e in bundle.get("entry", []) if "resource" in e]
        url = next((link["url"] for link in bundle.get("link", []) if link["relation"] == "next"), None)
    return resources


def _patient_id(resource: dict) -> str:
    if resource["resourceType"] == "Patient":
        return resource["id"]
    reference = (resource.get("subject") or resource.get("patient") or {}).get("reference", "")
    return reference.split("/")[-1]


def _has_coding(resource: dict, element: str, code: str) -> bool:
    value = resource.get(element)
    concepts = value if isinstance(value, list) else [value] if value else []
    return any(c.get("code") == code for concept in concepts for c in concept.get("coding", []))


def oracle_patients(spec: dict) -> set[str]:
    """Patients matching one criterion by plain FHIR search, without the portal."""
    oracle = spec["oracle"]
    resources = _fhir_search(oracle["search"])
    for element, code in (oracle.get("where") or {}).items():
        resources = [r for r in resources if _has_coding(r, element, code)]
    return {_patient_id(r) for r in resources}


def oracle_count(case: dict) -> int:
    included = None
    for group in case["inclusion"]:
        matching = set().union(*(oracle_patients(c) for c in group))
        included = matching if included is None else included & matching
    for group in case.get("exclusion") or []:
        excluded = set.intersection(*(oracle_patients(c) for c in group))
        included -= excluded
    return len(included)
