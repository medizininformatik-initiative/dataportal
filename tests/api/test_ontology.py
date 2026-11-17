"""S4: the ontology as served by the backend, for every UI profile and every data
selection profile, not only for the golden cases.

B1  every filter of a UI profile offers concepts (value sets) or criteria (criteria sets)
B2  every UI profile has a criterion that runs over CQL, also with its filters (ON-2)
B4  every data selection profile resolves, and its code filters offer concepts (ON-10)
ON-5  criteria sets contain only criteria of their own context
ON-8  search treats umlauts and their transcription alike
ON-9  ICD-10-GM and SNOMED CT criteria have an English display
ON-13 data selection offers no profiles of non-DomainResource types
"""

from __future__ import annotations

import json
import pathlib
import urllib.parse
from functools import lru_cache

import pytest

from feasibility import CCDL_VERSION, run_feasibility
from helpers import get_portal_access_token, portal_request

pytestmark = pytest.mark.smoke

# Resource types that do not derive from DomainResource and that TORCH cannot extract.
NON_DOMAIN_RESOURCES = {"Bundle", "Binary", "Parameters"}

KNOWN_ISSUES_FILE = pathlib.Path(__file__).resolve().parents[1] / "golden" / "known-issues.json"


def assert_only_known_issues(check: str, problems: list[str]) -> None:
    """Fails on problems that are not in golden/known-issues.json, and on known issues
    that no longer occur, so the baseline stays current."""
    known = set(json.loads(KNOWN_ISSUES_FILE.read_text()).get(check, {}).get("items", []))
    new, fixed = sorted(set(problems) - known), sorted(known - set(problems))
    message = []
    if new:
        message.append(f"new problems ({len(new)}):\n  " + "\n  ".join(new))
    if fixed:
        message.append(f"fixed, remove from {KNOWN_ISSUES_FILE.name} [{check}] ({len(fixed)}):\n  " + "\n  ".join(fixed))
    assert not message, "\n".join(message)


@lru_cache(maxsize=None)
def _token() -> str:
    return get_portal_access_token()["access_token"]


def _get(path: str, **params) -> object:
    query = urllib.parse.urlencode(params, doseq=True)
    status, body = portal_request(f"{path}?{query}" if query else path, token=_token())
    assert status == 200, f"GET {path} {params} -> {status}: {str(body)[:300]}"
    return body


def _english(display: dict | None) -> str:
    translations = (display or {}).get("translations") or []
    return next((t.get("value") or "" for t in translations if t.get("language") == "en-US"), "")


@lru_cache(maxsize=None)
def ui_profiles() -> dict[str, dict]:
    return {p["name"]: p for p in _get("/api/v6/terminology/ui-profile")}


@lru_cache(maxsize=None)
def value_set_concepts(value_set: str) -> tuple:
    hits = _get("/api/v6/codeable-concept/entry/search", searchterm="", **{"value-sets": value_set, "page-size": 5})
    return tuple(h["termCode"] for h in hits["results"])


@lru_cache(maxsize=None)
def criteria_set(url: str) -> tuple:
    hits = _get("/api/v6/terminology/entry/search", searchterm="", **{"criteria-sets": url, "page-size": 100})
    return tuple(hits["results"])


@lru_cache(maxsize=None)
def contexts() -> tuple:
    filters = _get("/api/v6/terminology/search/filter")
    values = next(f["values"] for f in filters if f["name"] == "context")
    return tuple(v.get("label") if isinstance(v, dict) else v for v in values)


@lru_cache(maxsize=None)
def sample_criteria() -> dict[str, dict]:
    """One selectable criterion per UI profile. Large contexts (e.g. Diagnose) use a
    different UI profile per terminology, so the first page of each context and
    terminology pair is sampled."""
    samples: dict[str, dict] = {}
    for context in contexts():
        filters = _get("/api/v6/terminology/search/filter", **{"target-filter": "terminology", "contexts": context})
        terminologies = [v["label"] for f in filters if f["name"] == "terminology" for v in f["values"]] or [None]
        for terminology in terminologies:
            params = {"searchterm": "", "contexts": context, "page-size": 50}
            if terminology:
                params["terminologies"] = terminology
            hits = _get("/api/v6/terminology/entry/search", **params)
            entries = {h["id"]: h for h in hits["results"] if h["selectable"]}
            if not entries:
                continue
            for data in _get("/api/v6/terminology/criteria-profile-data", ids=",".join(entries)):
                samples.setdefault(data["uiProfileId"], {**data, "search": entries[data["id"]]})
    return samples


def _filter_definitions(profile: dict) -> list[dict]:
    definitions = list(profile["attributeDefinitions"])
    if profile["valueDefinition"]:
        definitions.append(profile["valueDefinition"])
    return definitions


# --- B1: filters of UI profiles --------------------------------------------------------


def test_ui_profile_filters_offer_concepts_or_criteria():
    problems = []
    for name, profile in sorted(ui_profiles().items()):
        for definition in _filter_definitions(profile):
            label = f"{name}: " + ((definition.get("attributeCode") or {}).get("code") or "value")
            if definition["type"] == "concept" and not definition.get("selectableConcepts"):
                if not definition.get("referencedValueSet"):
                    problems.append(f"{label}: concept filter without value set or concepts")
                for value_set in definition.get("referencedValueSet") or []:
                    if not value_set_concepts(value_set):
                        problems.append(f"{label}: value set {value_set} returns no concepts")
            if definition["type"] == "reference":
                for url in definition.get("referencedCriteriaSet") or []:
                    if not criteria_set(url):
                        problems.append(f"{label}: criteria set {url} is empty")
    assert_only_known_issues("ui-profile-filters", problems)


def test_criteria_sets_contain_only_their_own_context():
    """ON-5: e.g. the specimen attribute 'festgestellteDiagnose' references
    CriteriaSet/Diagnose/icd-10-gm and must offer diagnoses only."""
    problems = []
    urls = {
        url
        for profile in ui_profiles().values()
        for definition in _filter_definitions(profile)
        for url in definition.get("referencedCriteriaSet") or []
    }
    assert urls, "no UI profile references a criteria set"
    for url in sorted(urls):
        context = url.split("/CriteriaSet/")[1].split("/")[0]
        wrong = {h["context"] for h in criteria_set(url)} - {context}
        if wrong:
            problems.append(f"{url} contains criteria of {sorted(wrong)}")
    assert not problems, "\n".join(problems)


# --- B2: every UI profile runs -----------------------------------------------------------


# UI profiles the ontology ships without criteria on purpose (confirmed 2026-11-17).
UI_PROFILES_WITHOUT_CRITERIA = {"MII_PR_Onko_Strahlentherapie_Bestrahlung_Nuklearmedizin"}


def test_every_ui_profile_is_used_by_a_criterion():
    unused = set(ui_profiles()) - set(sample_criteria()) - UI_PROFILES_WITHOUT_CRITERIA
    assert not unused, f"no criterion found for UI profiles {sorted(unused)}"


def _filters_for(profile: dict) -> dict:
    """Builds one filter of each kind the profile offers, with its first concept or unit."""
    criterion: dict = {}
    value = profile["valueDefinition"]
    if value and value["type"] == "concept":
        concepts = value.get("selectableConcepts") or [
            c for vs in value.get("referencedValueSet") or [] for c in value_set_concepts(vs)
        ]
        if concepts:
            criterion["valueFilter"] = {"type": "concept", "selectedConcepts": [concepts[0]]}
    if value and value["type"] == "quantity":
        units = value.get("allowedUnits") or []
        criterion["valueFilter"] = {
            "type": "quantity-comparator",
            "comparator": "gt",
            "value": 0,
            # The CCDL schema accepts code and display of a unit, not its system.
            **({"unit": {"code": units[0]["code"], "display": units[0].get("display", units[0]["code"])}} if units else {}),
        }
    attributes = []
    for attribute in profile["attributeDefinitions"]:
        if attribute["type"] != "concept":
            continue
        concepts = attribute.get("selectableConcepts") or [
            c for vs in attribute.get("referencedValueSet") or [] for c in value_set_concepts(vs)
        ]
        if concepts:
            attributes.append(
                {"type": "concept", "attributeCode": attribute["attributeCode"], "selectedConcepts": [concepts[0]]}
            )
    if attributes:
        criterion["attributeFilters"] = attributes[:1]
    return criterion


@pytest.mark.parametrize("name", sorted(ui_profiles()))
def test_criterion_of_ui_profile_runs_with_and_without_filter(name: str):
    sample = sample_criteria().get(name)
    if sample is None:
        pytest.skip("UI profile without criteria (see UI_PROFILES_WITHOUT_CRITERIA)")
    profile = ui_profiles()[name]
    filters = _filters_for(profile)
    base = {"termCodes": sample["termCodes"], "context": sample["context"]}
    value = profile["valueDefinition"]
    if value and not value.get("optional", True):
        # A mandatory value filter belongs to the criterion itself.
        assert "valueFilter" in filters, f"no value filter could be built for mandatory {value['type']} value"
        base["valueFilter"] = filters.pop("valueFilter")

    ccdl = {"version": CCDL_VERSION, "display": f"S4 {name}", "inclusionCriteria": [[base]]}
    count = run_feasibility(ccdl, _token())
    assert count >= 0

    if filters:
        filtered = {"version": CCDL_VERSION, "display": f"S4 {name} filtered", "inclusionCriteria": [[{**base, **filters}]]}
        assert run_feasibility(filtered, _token()) <= count


def test_molgen_module_has_a_runnable_criterion():
    """ON-2: the MolGen 2026 criteria are searchable and run."""
    hits = _get("/api/v6/terminology/entry/search", searchterm="", **{"kds-modules": "Molgen", "page-size": 50})
    selectable = [h for h in hits["results"] if h["selectable"]]
    assert selectable, "module Molgen has no selectable criterion"
    data = _get("/api/v6/terminology/criteria-profile-data", ids=selectable[0]["id"])[0]
    ccdl = {"version": CCDL_VERSION, "display": "S4 Molgen", "inclusionCriteria": [[{"termCodes": data["termCodes"], "context": data["context"]}]]}
    assert run_feasibility(ccdl, _token()) >= 0


# --- ON-9: English display ---------------------------------------------------------------

# Not every concept has an English translation. Criteria of these terminologies must have one.
TRANSLATED_TERMINOLOGIES = ("http://fhir.de/CodeSystem/bfarm/icd-10-gm", "http://snomed.info/sct")


@pytest.mark.parametrize("terminology", TRANSLATED_TERMINOLOGIES)
def test_icd10_and_snomed_criteria_have_english_display(terminology: str):
    """Checks the first page of criteria of the terminology in every context."""
    checked, missing = 0, []
    for context in contexts():
        hits = _get(
            "/api/v6/terminology/entry/search",
            searchterm="", contexts=context, terminologies=terminology, **{"page-size": 50},
        )
        for hit in hits["results"]:
            checked += 1
            if not _english(hit["display"]):
                missing.append(f"{context}: {hit['termcode']} {hit['display']['original']}")
    assert checked, f"no criteria of {terminology} found"
    assert not missing, f"{len(missing)} of {checked} criteria without English display:\n" + "\n".join(missing)


# --- ON-8: umlauts in search -------------------------------------------------------------


def test_profile_search_handles_umlauts():
    def names(term: str) -> set:
        hits = _get("/api/v6/profile/entry/search", searchterm=term, **{"page-size": 20})
        return {h["name"] for h in hits["results"]}

    umlaut, transcribed = names("Größe"), names("Groesse")
    assert umlaut, "no profile found for 'Größe'"
    assert umlaut == transcribed


# --- B4: data selection profiles ---------------------------------------------------------


@lru_cache(maxsize=None)
def dse_profiles() -> tuple:
    hits = _get("/api/v6/profile/entry/search", searchterm="", **{"page-size": 1000})
    assert hits["totalHits"] == len(hits["results"]), "profile search is paged, raise page-size"
    return tuple(hits["results"])


@lru_cache(maxsize=None)
def dse_profile_data() -> dict[str, dict]:
    urls = [p["url"] for p in dse_profiles()]
    data: dict[str, dict] = {}
    for i in range(0, len(urls), 25):
        for profile in _get("/api/v6/dse/profile-data", ids=",".join(urls[i : i + 25])):
            data[profile["url"]] = profile
    return data


def test_data_selection_profiles_resolve():
    broken = [f"{url}: {d['errorCode']} {d['errorCause']}" for url, d in dse_profile_data().items() if d.get("errorCode")]
    assert not broken, "\n".join(broken)


def test_data_selection_code_filters_offer_concepts():
    """ON-10: e.g. the code filter of Diagnose offers ICD-10-GM, Alpha-ID, SNOMED CT and
    Orphanet codes."""
    problems = []
    for url, profile in dse_profile_data().items():
        for f in profile["filters"]:
            if f["type"] != "token":
                continue
            if not f["valueSetUrls"]:
                problems.append(f"{url} filter {f['name']}: no value set")
            problems += [
                f"{url} filter {f['name']}: value set {vs} returns no concepts"
                for vs in f["valueSetUrls"]
                if not value_set_concepts(vs)
            ]
    assert_only_known_issues("data-selection-code-filters", problems)


def test_data_selection_offers_only_domain_resources():
    """ON-13: TORCH extracts DomainResources only."""
    wrong = [
        f"{p['name']} ({p['resourceType']['display']['original']})"
        for p in dse_profiles()
        if (p.get("resourceType") or {}).get("display", {}).get("original") in NON_DOMAIN_RESOURCES
    ]
    assert not wrong, f"profiles of non-DomainResource types: {wrong}"
