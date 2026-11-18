"""S7: fhir-pseudonymizer (DIMP) features since v2.23.0, called directly.

PS-5  request decompression, the remove method for nested resources, and the request
      size limit (Kestrel__MaxRequestBodySize) against the bundle size aether sends
PS-4  FHIR.NET 6: cryptoHash of a Reference keeps its data-absent-reason extension (D14)
"""

from __future__ import annotations

import base64
import gzip
import http.client
import json
import re
import urllib.error
import urllib.request

import pytest

from helpers import DATA_NODE_DIR, wait_for_url
from torch_client import env_file

DE_IDENTIFY_URL = "http://localhost:8083/fhir/$de-identify"
DUP_YAML = DATA_NODE_DIR / "example-dup-project" / "example-project_dimp_dup_base.yaml"
DUP_PIPELINE = DATA_NODE_DIR / "example-dup-project" / "example-project-pipeline.yml"
DATA_ABSENT_REASON = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
# fhir-pseudonymizer appsettings.json, Kestrel.MaxRequestBodySize
DEFAULT_MAX_REQUEST_BODY = 30_000_000

REMOVE_LOCATIONS = """\
fhirVersion: R4
fhirPathRules:
  - path: Bundle.entry.where(resource is Location)
    method: remove
"""


@pytest.fixture(scope="module", autouse=True)
def _wait_for_dimp():
    wait_for_url("http://localhost:8083/fhir/metadata")


def parameters(resource: dict, config: bytes | None = None) -> dict:
    parameter = [{"name": "resource", "resource": resource}]
    if config is not None:
        parameter.insert(0, {"name": "config", "valueAttachment": {"contentType": "application/yaml", "data": base64.b64encode(config).decode()}})
    return {"resourceType": "Parameters", "parameter": parameter}


def post(body: bytes, headers: dict | None = None) -> tuple[int, dict | str]:
    request = urllib.request.Request(DE_IDENTIFY_URL, data=body, headers={"Content-Type": "application/json"} | (headers or {}))
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, error.read().decode(errors="replace")


def bundle(*resources: dict) -> dict:
    return {"resourceType": "Bundle", "type": "collection", "entry": [{"resource": r} for r in resources]}


PATIENT = {"resourceType": "Patient", "id": "p1", "gender": "female"}
LOCATION = {"resourceType": "Location", "id": "l1", "name": "Station 1"}


def test_gzip_request_is_decompressed():
    body = gzip.compress(json.dumps(parameters(PATIENT, DUP_YAML.read_bytes())).encode())
    status, result = post(body, {"Content-Encoding": "gzip"})
    assert status == 200, result
    assert result["resourceType"] == "Patient"
    assert result["id"] != "p1"


def test_remove_method_drops_nested_resources():
    status, result = post(json.dumps(parameters(bundle(PATIENT, LOCATION), REMOVE_LOCATIONS.encode())).encode())
    assert status == 200, result
    assert [e["resource"]["resourceType"] for e in result["entry"]] == ["Patient"]


def max_request_body() -> int:
    configured = env_file(DATA_NODE_DIR / "fhir-pseudonymizer" / ".env").get("Kestrel__MaxRequestBodySize")
    return int(configured) if configured else DEFAULT_MAX_REQUEST_BODY


def patients_body(size: int) -> bytes:
    """A valid $de-identify request with a Bundle of Patients of at least `size` bytes."""
    entry = {"resource": {"resourceType": "Patient", "gender": "female", "name": [{"family": "x" * 1000}]}}
    count = size // len(json.dumps(entry)) + 1
    return json.dumps(parameters(bundle(*[entry["resource"]] * count))).encode()


def test_request_size_limit_is_in_effect():
    """A bundle above the limit is rejected: with 413, or Kestrel closes the connection
    while the body is still being sent."""
    connection = http.client.HTTPConnection("localhost", 8083, timeout=300)
    try:
        connection.request("POST", "/fhir/$de-identify", body=patients_body(max_request_body() + 1_000_000),
                           headers={"Content-Type": "application/json"})
        status = connection.getresponse().status
    except (BrokenPipeError, ConnectionResetError):
        status = 413
    assert status == 413


@pytest.mark.xfail(strict=True, reason="D15: the example DUP project sends bundles up to "
                   "bundle_split_threshold_mb: 100 to DIMP, which rejects bodies above 30 MB with 413 "
                   "(Kestrel__MaxRequestBodySize is not set in fhir-pseudonymizer/.env)")
def test_dup_project_bundle_threshold_fits_the_dimp_limit():
    threshold = int(re.search(r"bundle_split_threshold_mb:\s*(\d+)", DUP_PIPELINE.read_text()).group(1))
    assert threshold * 1_000_000 <= max_request_body()


@pytest.mark.xfail(strict=True, reason="D14: fhir-pseudonymizer 3.1.2 cryptoHash on Reference.reference "
                   "also hashes url and valueCode of the extension on _reference")
def test_crypto_hash_of_a_reference_keeps_its_extension():
    medication = {
        "resourceType": "Medication",
        "id": "m1",
        "ingredient": [{
            "itemReference": {
                "reference": "Medication/m2",
                "_reference": {"extension": [{"url": DATA_ABSENT_REASON, "valueCode": "masked"}]},
            },
        }],
    }
    status, result = post(json.dumps(parameters(medication, DUP_YAML.read_bytes())).encode())
    assert status == 200, result
    reference = result["ingredient"][0]["itemReference"]
    assert reference["_reference"]["extension"] == [{"url": DATA_ABSENT_REASON, "valueCode": "masked"}]
