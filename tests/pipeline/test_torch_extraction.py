"""S7: TORCH extraction of the MII test data, validated with mii-fhir-validator.

TO-9   extracted resources (slices, partial copies, polymorphic references) are valid
ON-11  the Medikation profiles of the data selection validate (Medication, MedicationAdministration)
PS-4   DIMP (fhir-pseudonymizer 3, FHIR.NET 6) adds no validation errors
TO-14  every NDJSON link of the manifest resolves to the documented bundles: one core.ndjson
       with one Bundle without Patient, and one transaction Bundle per patient with exactly
       one Patient (https://medizininformatik-initiative.github.io/torch/api/api.html)
BL-4   paging: TORCH with 2 resources per page and 3 patients per batch extracts the same

Terminology errors are ignored because the CI node has no terminology loaded. The other
errors are compared with baselines in tests/golden/known-issues.json.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.request

import pytest

from helpers import DATA_NODE_DIR, assert_only_known_issues, wait_for_url, wait_for_validator
from torch_client import PATIENT_PROFILE, extract, torch_variant

VALIDATOR_URL = "http://localhost:8080/validateResource"
DE_IDENTIFY_URL = "http://localhost:8083/fhir/$de-identify"
DUP_YAML = DATA_NODE_DIR / "example-dup-project" / "example-project_dimp_dup_base.yaml"

OBSERVATION_LAB = "https://www.medizininformatik-initiative.de/fhir/core/modul-labor/StructureDefinition/ObservationLab"
# Profiles the validator has to resolve before the tests start (Person, Labor and Medikation IGs)
PROBE_PROFILES = {
    PATIENT_PROFILE: "Patient",
    OBSERVATION_LAB: "Observation",
    "https://www.medizininformatik-initiative.de/fhir/core/modul-medikation/StructureDefinition/Medication": "Medication",
}


def slices_crtdl() -> dict:
    """data-node/aether/queries/example-crtdl.json (an address slice as must-have) plus a
    laboratory group with the category slice and a linked encounter."""
    crtdl = json.loads((DATA_NODE_DIR / "aether" / "queries" / "example-crtdl.json").read_text())
    crtdl["dataExtraction"]["attributeGroups"].append({
        "id": "lab",
        "name": "Laboratory",
        "groupReference": OBSERVATION_LAB,
        "attributes": [
            {"attributeRef": ref, "mustHave": False}
            for ref in ("Observation.code", "Observation.value[x]", "Observation.effective[x]",
                        "Observation.category.coding:observation-category")
        ] + [{"attributeRef": "Observation.encounter", "mustHave": False, "linkedGroups": ["enc"]}],
    })
    return crtdl


# Slices, linked groups and must-have attributes / Medication, MedicationAdministration
CRTDLS = {
    "slices": slices_crtdl,
    "dup-project": lambda: json.loads((DATA_NODE_DIR / "example-dup-project" / "example-project-crtdl.json").read_text()),
}

TERMINOLOGY = re.compile(
    r"terminology-server|code ?system|value ?set|Wrong Display|Invalid display|Unknown code|not found in|could not be validated",
    re.IGNORECASE,
)


@pytest.fixture(scope="module", autouse=True)
def _wait_for_services():
    wait_for_url("http://localhost:8086/actuator/health")
    wait_for_validator(VALIDATOR_URL, PROBE_PROFILES)
    wait_for_url("http://localhost:8083/fhir/metadata")


@pytest.fixture(scope="module")
def extractions() -> dict:
    return {name: extract(crtdl()) for name, crtdl in CRTDLS.items()}


def validation_errors(resource: dict) -> set[str]:
    """Non-terminology errors as '<type> <profile>: <message>' without element indices."""
    request = urllib.request.Request(
        VALIDATOR_URL, data=json.dumps(resource).encode(),
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            issues = json.load(response)["issue"]
    except urllib.error.HTTPError as error:
        issues = json.load(error)["issue"]
    profile = (resource.get("meta", {}).get("profile") or ["-"])[0].rsplit("/", 1)[-1]
    errors = set()
    for issue in issues:
        text = issue.get("details", {}).get("text") or issue.get("diagnostics", "")
        if issue["severity"] in ("error", "fatal") and not TERMINOLOGY.search(text):
            text = re.sub(r"\[\d+\]", "", re.sub(r"\s*\(from https?://\S+\)", "", text))
            text = re.sub(r"[0-9a-f]{32}", "<hash>", text)
            errors.add(f"{resource['resourceType']} {profile}: {text}")
    return errors


def errors_of(resources: list[dict]) -> set[str]:
    return set().union(*(validation_errors(r) for r in resources))


def de_identify(bundle: dict) -> dict:
    body = {
        "resourceType": "Parameters",
        "parameter": [
            {"name": "config", "valueAttachment": {"contentType": "application/yaml", "data": base64.b64encode(DUP_YAML.read_bytes()).decode()}},
            {"name": "resource", "resource": bundle},
        ],
    }
    request = urllib.request.Request(DE_IDENTIFY_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def test_extraction_covers_the_crtdl_groups(extractions):
    types = {r["resourceType"] for result in extractions.values() for r in result.resources()}
    assert {"Patient", "Condition", "Encounter", "Observation", "Medication", "MedicationAdministration"} <= types


def test_extracted_resources_validate(extractions):
    """TO-9, ON-11."""
    errors = set().union(*(errors_of(result.resources()) for result in extractions.values()))
    assert_only_known_issues("torch-output-validation", sorted(errors))


def test_dimp_adds_no_validation_errors(extractions):
    """PS-4: validates the TORCH output before and after $de-identify with the DUP config."""
    bundles = extractions["dup-project"].bundles()
    before = errors_of([e["resource"] for b in bundles for e in b.get("entry", [])])
    after = errors_of([e["resource"] for b in bundles for e in de_identify(b).get("entry", [])])
    assert_only_known_issues("dimp-output-validation", sorted(after - before))


def test_every_ndjson_link_resolves(extractions):
    """TO-14."""
    for name, result in extractions.items():
        outputs = [o["url"] for o in result.manifest["output"]]
        core = [url for url in outputs if url.endswith("/core.ndjson")]
        assert len(core) == 1, f"{name}: expected one core.ndjson in {outputs}"
        assert len(outputs) > 1, f"{name}: no patient batch file in {outputs}"
        for url in outputs:
            bundles = [json.loads(line) for line in result.read(url).splitlines() if line.strip()]
            assert bundles, f"{name}: empty NDJSON {url}"
            assert all(b["resourceType"] == "Bundle" and b["type"] == "transaction" for b in bundles), url
            patients = [sum(e["resource"]["resourceType"] == "Patient" for e in b.get("entry", [])) for b in bundles]
            if url in core:
                assert patients == [0], f"{name}: core.ndjson must hold one Bundle without Patient, got {patients}"
            else:
                assert set(patients) == {1}, f"{name}: every patient Bundle must hold exactly one Patient in {url}"


def resource_keys(result) -> set[tuple[str, str]]:
    """Resources without Provenance, whose ids TORCH generates per run."""
    return {(r["resourceType"], r["id"]) for r in result.resources() if r["resourceType"] != "Provenance"}


def test_small_pages_and_batches_extract_the_same(extractions):
    """BL-4: Blaze paging links are followed over many pages and batches."""
    with torch_variant({"TORCH_FHIR_PAGE_COUNT": "2", "TORCH_BATCHSIZE": "3"}) as torch:
        paged = extract(CRTDLS["dup-project"](), torch=torch)
    assert len(paged.job["batches"]) > 1
    assert resource_keys(paged) == resource_keys(extractions["dup-project"])
