"""Verifies that the example DUP project's DIMP config never empties a required
(min cardinality 1) Reference.

The pseudonymizer prunes any element whose children were all redacted. For a
1..1 Reference such as Encounter.diagnosis.condition or Provenance.entity.what
that yields invalid FHIR, e.g. "Element 'condition' with minimum cardinality 1
cannot be null". Instead, the content has to be replaced by a data-absent-reason
'masked' extension.

Calls $de-identify directly with hand-built resources, so the cases do not
depend on what the MII test data happens to contain.
"""

from __future__ import annotations

import base64
import json
import urllib.request

import pytest

from helpers import DATA_NODE_DIR, wait_for_url

DUP_YAML = DATA_NODE_DIR / "example-dup-project" / "example-project_dimp_dup_base.yaml"
DE_IDENTIFY_URL = "http://localhost:8083/fhir/$de-identify"

DATA_ABSENT_REASON_URL = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
DATA_ABSENT_REASON_MASKED = [{"url": DATA_ABSENT_REASON_URL, "valueCode": "masked"}]
RAW_VALUE = "RAW-SITE-VALUE-123"

REFERENCE_SHAPES = {
    "identifier-only": {"identifier": {"system": "https://example.org/sid/unlisted", "value": RAW_VALUE}},
    "identifier-and-display": {
        "identifier": {"system": "https://example.org/sid/unlisted", "value": RAW_VALUE},
        "display": RAW_VALUE,
    },
    "display-only": {"display": RAW_VALUE},
    "reference-data-absent-reason": {"_reference": {"extension": DATA_ABSENT_REASON_MASKED}},
}


def _encounter_with_diagnosis_condition(reference: dict) -> dict:
    return {
        "resourceType": "Encounter",
        "id": "enc-1",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"},
        "diagnosis": [{"condition": reference, "rank": 1}],
    }


def _encounter_with_location(reference: dict) -> dict:
    return {
        "resourceType": "Encounter",
        "id": "enc-1",
        "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP"},
        "location": [{"location": reference, "status": "active"}],
    }


def _provenance_with_entity_what(reference: dict) -> dict:
    return {
        "resourceType": "Provenance",
        "id": "prov-1",
        "target": [{"reference": "Patient/pat-1"}],
        "recorded": "2024-01-01T00:00:00Z",
        "agent": [{"who": {"reference": "Device/dev-1"}}],
        "entity": [{"role": "source", "what": reference}],
    }


REQUIRED_REFERENCE_PATHS = {
    "Encounter.diagnosis.condition": (
        _encounter_with_diagnosis_condition,
        lambda resource: resource.get("diagnosis", [{}])[0].get("condition"),
    ),
    "Encounter.location.location": (
        _encounter_with_location,
        lambda resource: resource.get("location", [{}])[0].get("location"),
    ),
    "Provenance.entity.what": (
        _provenance_with_entity_what,
        lambda resource: resource.get("entity", [{}])[0].get("what"),
    ),
}


@pytest.fixture(scope="module", autouse=True)
def _wait_for_dimp():
    wait_for_url("http://localhost:8083/fhir/metadata")


def _de_identify(resource: dict) -> dict:
    body = {
        "resourceType": "Parameters",
        "parameter": [
            {
                "name": "config",
                "valueAttachment": {
                    "contentType": "application/yaml",
                    "data": base64.b64encode(DUP_YAML.read_bytes()).decode(),
                },
            },
            {"name": "resource", "resource": resource},
        ],
    }
    request = urllib.request.Request(
        DE_IDENTIFY_URL,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _data_absent_reasons(element: dict) -> list[dict]:
    """Collects data-absent-reason extensions on the Reference itself, on its
    reference primitive (_reference) and on its identifier."""
    extensions = element.get("extension", []) + element.get("_reference", {}).get("extension", [])
    extensions += element.get("identifier", {}).get("extension", [])
    return [extension for extension in extensions if extension.get("url") == DATA_ABSENT_REASON_URL]


@pytest.mark.parametrize("shape", REFERENCE_SHAPES)
@pytest.mark.parametrize("path", REQUIRED_REFERENCE_PATHS)
def test_required_reference_is_masked_not_pruned(path: str, shape: str):
    build, extract = REQUIRED_REFERENCE_PATHS[path]
    result = _de_identify(build(REFERENCE_SHAPES[shape]))
    element = extract(result)

    assert element, (
        f"{path} (min cardinality 1) was pruned for a '{shape}' Reference - "
        f"the output is invalid FHIR: {json.dumps(result)}"
    )
    assert RAW_VALUE not in json.dumps(element), f"raw value leaked in {path}: {json.dumps(element)}"
    assert _data_absent_reasons(element) == DATA_ABSENT_REASON_MASKED, (
        f"expected {path} to carry exactly one data-absent-reason 'masked' extension, "
        f"found {json.dumps(element)}"
    )
