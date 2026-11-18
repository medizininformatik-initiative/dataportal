"""S4 (B6): backend contracts the UI and the data node rely on.

BE-3  profile search: pinned profiles first, field descriptions are searched
BE-4  bulk search: duplicates are found, unknown codes are reported
BE-8  Elasticsearch queries are not logged at INFO
BE-10 Elasticsearch holds the ontology the backend expects
BE-11 CRTDL upgrade replaces onset-date with recorded-date
UI-11 the CSV export of a CRTDL matches the CRTDL
"""

from __future__ import annotations

import copy
import csv
import io
import json
import re
import urllib.parse
import urllib.request
import zipfile

import pytest

from feasibility import CCDL_VERSION
from helpers import (
    DATA_NODE_DIR,
    PORTAL_BACKEND_URL,
    PORTAL_ES_URL,
    container_logs,
    pinned_ontology_tag,
    portal_request,
    portal_ssl_context,
)

pytestmark = pytest.mark.smoke

EXAMPLE_CRTDL = DATA_NODE_DIR / "torch" / "queries" / "example-crtdl.json"
ICD10GM = "http://fhir.de/CodeSystem/bfarm/icd-10-gm"
ONTOLOGY_INDICES = ("ontology", "codeable_concept", "profile")


def _example_crtdl() -> dict:
    return json.loads(EXAMPLE_CRTDL.read_text())


def _profile_names(token: str, term: str) -> list[str]:
    query = urllib.parse.urlencode({"searchterm": term, "page-size": 10})
    status, body = portal_request(f"/api/v6/profile/entry/search?{query}", token=token)
    assert status == 200, body
    return [hit["name"] for hit in body["results"]]


# --- BE-3: profile search ----------------------------------------------------------------


def test_empty_profile_search_starts_with_pinned_profiles(portal_access_token: str):
    assert _profile_names(portal_access_token, "")[0] == "MII_PR_Diagnose_Condition"


def test_profile_search_finds_terms_in_field_descriptions(portal_access_token: str):
    # 'remission' occurs only in the description of Condition.abatement[x].
    assert "MII_PR_Diagnose_Condition" in _profile_names(portal_access_token, "remission")


# --- BE-4: bulk search -------------------------------------------------------------------


def test_bulk_search_finds_duplicates_and_reports_unknown_codes(portal_access_token: str):
    status, body = portal_request(
        "/api/v6/terminology/entry/bulk-search",
        token=portal_access_token,
        method="POST",
        body={"terminology": ICD10GM, "context": "Diagnose", "searchterms": ["C34.1", "B05.3", "C34.1", "XXX.9"]},
    )
    assert status == 200, body
    assert body["notFound"] == ["XXX.9"]
    found = {code for hit in body["found"] for code in (t["code"] for t in hit["termcodes"])}
    assert found == {"C34.1", "B05.3"}


# --- CCDL and CRTDL validation and upgrade -----------------------------------------------


def test_example_crtdl_is_valid(portal_access_token: str):
    status, body = portal_request(
        "/api/v6/validation/crtdl", token=portal_access_token, method="POST", body=_example_crtdl()
    )
    assert status == 200, body


def _crtdl_with_onset_date_filter() -> dict:
    crtdl = _example_crtdl()
    diagnoses = next(g for g in crtdl["dataExtraction"]["attributeGroups"] if g["groupReference"].endswith("/Diagnose"))
    diagnoses["filter"] = [{"type": "date", "name": "onset-date", "start": "2020-01-01", "end": "2025-12-31"}]
    return crtdl


def test_unknown_filter_name_is_rejected(portal_access_token: str):
    status, body = portal_request(
        "/api/v6/validation/crtdl", token=portal_access_token, method="POST", body=_crtdl_with_onset_date_filter()
    )
    assert status == 400
    assert [issue["value"]["code"] for issue in body] == ["VALIDATION-2000008"]


def test_upgrade_replaces_onset_date_with_recorded_date(portal_access_token: str):
    """BE-11: CRTDLs saved before ontology 5 used onset-date for diagnoses."""
    status, body = portal_request(
        "/api/v6/upgrade/crtdl", token=portal_access_token, method="POST", body=_crtdl_with_onset_date_filter()
    )
    assert status == 200, body
    filters = [f for g in body["crtdl"]["dataExtraction"]["attributeGroups"] for f in g.get("filter", [])]
    assert [f["name"] for f in filters] == ["recorded-date"]
    assert [a["value"]["code"] for a in body["annotations"]] == ["UPGRADE-1000001"]


def test_upgraded_crtdl_is_valid(portal_access_token: str):
    status, body = portal_request(
        "/api/v6/upgrade/crtdl", token=portal_access_token, method="POST", body=_crtdl_with_onset_date_filter()
    )
    assert status == 200, body
    status, issues = portal_request(
        "/api/v6/validation/crtdl", token=portal_access_token, method="POST", body=body["crtdl"]
    )
    assert status == 200, issues


def test_missing_mandatory_value_filter_is_rejected(portal_access_token: str):
    # 'Current chronological age' (Patient) requires a quantity value filter.
    query = urllib.parse.urlencode({"searchterm": "424144002", "contexts": "Patient"})
    status, hits = portal_request(f"/api/v6/terminology/entry/search?{query}", token=portal_access_token)
    assert status == 200 and hits["results"], hits
    status, data = portal_request(
        f"/api/v6/terminology/criteria-profile-data?ids={hits['results'][0]['id']}", token=portal_access_token
    )
    criterion = {"termCodes": data[0]["termCodes"], "context": data[0]["context"]}
    ccdl = {"version": CCDL_VERSION, "display": "missing value filter", "inclusionCriteria": [[criterion]]}
    status, body = portal_request("/api/v6/validation/ccdl", token=portal_access_token, method="POST", body=ccdl)
    assert status == 400, f"{status}: {body}"


# --- UI-11: CSV export -------------------------------------------------------------------


def _csv_export(crtdl: dict, token: str) -> zipfile.ZipFile:
    request = urllib.request.Request(
        f"{PORTAL_BACKEND_URL}/api/v6/query/data/convert/crtdl",
        data=json.dumps(crtdl).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/zip"},
        method="POST",
    )
    with urllib.request.urlopen(request, context=portal_ssl_context(), timeout=60) as response:
        return zipfile.ZipFile(io.BytesIO(response.read()))


def _without_empty(value: object) -> object:
    """Drops empty strings, lists, objects and nulls. The backend leaves them out when it
    writes a CRTDL back."""
    if isinstance(value, dict):
        cleaned = {k: _without_empty(v) for k, v in value.items()}
        return {k: v for k, v in cleaned.items() if v not in ("", [], {}, None)}
    if isinstance(value, list):
        return [_without_empty(v) for v in value]
    return value


def _rows(archive: zipfile.ZipFile, name: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8-sig")), delimiter=";"))


def test_csv_export_matches_crtdl(portal_access_token: str):
    crtdl = _example_crtdl()
    archive = _csv_export(crtdl, portal_access_token)

    assert set(archive.namelist()) == {
        "Datendefinition.json",
        "EN_Inclusioncriteria.csv", "EN_Exclusioncriteria.csv", "EN_Featureselection.csv",
        "DE_Einschlusskriterien.csv", "DE_Ausschlusskriterien.csv", "DE_Merkmalselektion.csv",
    }
    assert _without_empty(json.loads(archive.read("Datendefinition.json"))) == _without_empty(crtdl)

    groups = crtdl["dataExtraction"]["attributeGroups"]
    assert [r["Featurename"] for r in _rows(archive, "EN_Featureselection.csv")] == [g["name"] for g in groups]
    assert [r["Merkmalname"] for r in _rows(archive, "DE_Merkmalselektion.csv")] == [g["name"] for g in groups]

    criteria = [c for group in crtdl["cohortDefinition"]["inclusionCriteria"] for c in group]
    inclusion = _rows(archive, "EN_Inclusioncriteria.csv")
    assert [r["Code"] for r in inclusion] == [c["termCodes"][0]["code"] for c in criteria]
    assert _rows(archive, "EN_Exclusioncriteria.csv") == []


# --- BE-8, BE-10: logs and ontology version ----------------------------------------------


def test_backend_does_not_log_terminology_searches_at_info(portal_access_token: str):
    _profile_names(portal_access_token, "Diagnose")
    request_logs = re.findall(r"\[http-nio-[^\]]+\] INFO\s+(d\.m\.d\.b\.t\.\S+)", container_logs("dataportal-backend"))
    assert not request_logs, f"terminology loggers at INFO: {sorted(set(request_logs))}"


ONTOLOGY_VERSION_REASON = (
    "Ontology releases v5.2.1 and v5.2.2 stamp their Elasticsearch indices as v5.2.0 "
    "(elastic/index/*.json), while the stack pins v5.2.2 and dataportal-backend 9.5.0 expects "
    "v5.2.2. Remove this marker once the ontology release stamps its own version."
)


@pytest.mark.xfail(strict=True, reason=ONTOLOGY_VERSION_REASON)
def test_elasticsearch_holds_the_pinned_ontology_version():
    expected = pinned_ontology_tag()
    versions = {}
    for index in ONTOLOGY_INDICES:
        with urllib.request.urlopen(f"{PORTAL_ES_URL}/{index}/_mapping", timeout=30) as response:
            mapping = json.load(response)
        versions[index] = next(iter(mapping.values()))["mappings"].get("_meta", {}).get("version")
    assert versions == {index: expected for index in ONTOLOGY_INDICES}


@pytest.mark.xfail(strict=True, reason=ONTOLOGY_VERSION_REASON)
def test_backend_reports_no_ontology_version_mismatch():
    mismatch = [line for line in container_logs("dataportal-backend").splitlines() if "Ontology version mismatch" in line]
    assert not mismatch, mismatch[0]
