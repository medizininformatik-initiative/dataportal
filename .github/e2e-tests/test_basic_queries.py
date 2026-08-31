"""Basic FHIR search query checks against the shared MII testdata release that's
already uploaded onto the data node as part of the e2e job setup (see
data-node/get-mii-testdata.sh and data-node/upload-testdata.sh) - the same
dataset the rest of the e2e tests (e.g. test_dup_pipeline.py) run against.

Ported from the old dedicated `test-data-node-fhir-server` CI job so these
checks share the data node setup with the rest of the e2e tests instead of
standing up a second one.
"""

from __future__ import annotations

import json
import ssl
import urllib.request

import pytest

from conftest import DATA_NODE_DIR, get_fhir_access_token

FHIR_BASE_URL = "https://fhir.localhost:444/fhir"
CACERT = DATA_NODE_DIR / "auth" / "cert.pem"

CONSENT_PERMIT_URI = (
    f"{FHIR_BASE_URL}/Consent?mii-provision-provision-code-type="
    "2.16.840.1.113883.3.1937.777.24.5.3.6$permit"
)
CONDITION_B05_3_URI = f"{FHIR_BASE_URL}/Condition?code=http://fhir.de/CodeSystem/bfarm/icd-10-gm|B05.3"


@pytest.fixture(scope="module")
def access_token() -> str:
    return get_fhir_access_token()


def _search_total(access_token: str, url: str) -> int:
    request = urllib.request.Request(
        url,
        headers={
            "Prefer": "handling=strict",
            "Accept": "application/fhir+json",
            "Authorization": f"Bearer {access_token}",
        },
    )
    context = ssl.create_default_context(cafile=str(CACERT))
    with urllib.request.urlopen(request, context=context, timeout=30) as response:
        body = json.load(response)

    if body.get("resourceType") == "OperationOutcome":
        diagnostics = [issue.get("diagnostics") for issue in body.get("issue", [])]
        pytest.fail(f"search against {url} failed: {diagnostics}")
    return body["total"]


def test_consent_permit_count(access_token: str):
    assert _search_total(access_token, CONSENT_PERMIT_URI) == 10


def test_condition_count_b05_3(access_token: str):
    assert _search_total(access_token, CONDITION_B05_3_URI) == 1
