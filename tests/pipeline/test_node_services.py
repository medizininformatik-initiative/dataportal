"""S7: data node services on their own.

BL-1  Blaze images without curl: the healthchecks of fhir-server and terminology-server use wget
FD-1  fhir-data-evaluator 1.3.3 against Blaze 1.13.0 creates a MeasureReport (also BL-5,
      $evaluate-measure, and BL-4, paging with a page size below the patient count)
VA-1  the validator loads every IG of IG_PARAMS and resolves ICU and Mikrobiologie profiles
VA-2  the terminology package range reaches the BOM the validator expects
VA-3  R5 cross-version extensions validate without errors

The CI node has no terminology loaded (SNOMED CT needs a licence), so terminology errors
of the validator are not checked here.
"""

from __future__ import annotations

import datetime
import io
import json
import os
import pathlib
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile

import pytest

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, wait_for_url
from torch_client import FHIR_URL, delete_resources, env_file, fhir_token

VALIDATOR_URL = "http://localhost:8080/validateResource"
PACKAGES = "/root/.fhir/packages"
FDE_DIR = DATA_NODE_DIR / "fhir-data-evaluator"


def container(service: str) -> str:
    return f"{COMPOSE_PROJECT}-{service}-1"


def inspect(service: str) -> dict:
    result = subprocess.run(["docker", "inspect", container(service)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)[0]


def fhir_get(path: str) -> dict:
    request = urllib.request.Request(f"{FHIR_URL}/{path}", headers={"Authorization": f"Bearer {fhir_token()}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


# --- BL-1 --------------------------------------------------------------------------------


@pytest.mark.parametrize("service", ["fhir-server", "terminology-server"])
def test_blaze_healthcheck_uses_wget_and_is_healthy(service):
    state = inspect(service)
    assert "wget" in " ".join(state["Config"]["Healthcheck"]["Test"])
    assert state["State"]["Health"]["Status"] == "healthy"


# --- FD-1, BL-4, BL-5 ----------------------------------------------------------------------


def fde_measure() -> pathlib.Path:
    """The measure file run-fde.sh uses, downloaded the same way if missing."""
    script = (FDE_DIR / "run-fde.sh").read_text()
    version = re.search(r"ONTOLOGY_VERSION=\$\{ONTOLOGY_VERSION:-(\S+)\}", script).group(1)
    measure = FDE_DIR / "measure" / f"Measure-CdsCodingAvailability.fhir_v{version}.json"
    if not measure.exists():
        url = f"https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v{version}/availability.zip"
        with urllib.request.urlopen(url, timeout=120) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        measure.write_bytes(archive.read("Measure-CdsCodingAvailability.fhir.json"))
    return measure


@pytest.fixture(scope="module")
def fde_report():
    """Runs FDE once with the data node's .env, pointed at the fhir-server service (see
    test_fde_default_points_at_the_fhir_server) and with 5 resources per page, and returns
    the MeasureReport it uploaded."""
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = env_file(FDE_DIR / ".env") | {
        "FHIR_SOURCE_SERVER": "http://fhir-server:8080/fhir",
        "FHIR_REPORT_SERVER": "http://fhir-server:8080/fhir",
        "FHIR_SOURCE_PAGE_COUNT": "5",
        "SEND_REPORT_TO_SERVER": "true",
        "CREATE_OBFUSCATED_REPORT": "false",
        "PROJECT_IDENTIFIER_VALUE": "fdpg-data-availability-report",
    }
    with tempfile.TemporaryDirectory() as tmp:
        env_path = pathlib.Path(tmp) / "fde.env"
        env_path.write_text("".join(f"{k}={v}\n" for k, v in env.items()))
        output = pathlib.Path(tmp) / "output"
        output.mkdir(mode=0o777)
        result = subprocess.run(
            ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(FDE_DIR / "docker-compose.yml"),
             "run", "--rm", "fhir-data-evaluator"],
            env=os.environ | {"OVERRIDE_ENV": str(env_path), "FDE_INPUT_MEASURE": str(fde_measure()),
                              "FDE_OUTPUT_DIR": str(output), "COMPOSE_IGNORE_ORPHANS": "True"},
            capture_output=True, text=True, timeout=600,
        )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    documents = fhir_get(f"DocumentReference?_lastUpdated=gt{started}&_count=50").get("entry", [])
    reports = [
        d["resource"] for d in documents
        if d["resource"].get("masterIdentifier", {}).get("value") == "fdpg-data-availability-report"
    ]
    assert len(reports) == 1, f"expected one DocumentReference of the FDE run, found {len(reports)}"
    document = reports[0]
    report = fhir_get(document["content"][0]["attachment"]["url"])
    yield report
    delete_resources([document, report])


def test_fde_creates_a_measure_report(fde_report):
    assert fde_report["resourceType"] == "MeasureReport"
    assert len(fde_report["group"]) > 1


@pytest.mark.xfail(strict=True, reason="D12 (low): fhir-data-evaluator 1.3.3 uploads MeasureReports without "
                   "the R4 mandatory elements status, type, measure and period")
def test_fde_measure_report_has_the_mandatory_elements(fde_report):
    missing = [e for e in ("status", "type", "measure", "period") if e not in fde_report]
    assert not missing, missing


def test_fde_pages_through_all_patients(fde_report):
    """The first group counts patients. With 5 resources per page FDE must read every page."""
    patients = fhir_get("Patient?_summary=count")["total"]
    assert patients > 5
    populations = {p["code"]["coding"][0]["code"]: p["count"] for p in fde_report["group"][0]["population"]}
    assert populations["initial-population"] == patients


@pytest.mark.xfail(strict=True, reason="D11: FHIR_SOURCE_SERVER and FHIR_REPORT_SERVER default to "
                   "http://localhost:8080/fhir, which is the validator on a full data node (Blaze is on 8081)")
def test_fde_default_points_at_the_fhir_server():
    defaults = env_file(FDE_DIR / ".env.default")
    assert defaults["FHIR_SOURCE_SERVER"] == "http://fhir-server:8080/fhir"
    assert defaults["FHIR_REPORT_SERVER"] == "http://fhir-server:8080/fhir"


# --- VA-1, VA-2, VA-3 ----------------------------------------------------------------------


def validator_sh(command: str) -> str:
    result = subprocess.run(["docker", "exec", container("fhir-validator"), "sh", "-c", command],
                            capture_output=True, text=True, check=True)
    return result.stdout


def validate(resource: dict) -> list[dict]:
    request = urllib.request.Request(
        VALIDATOR_URL, data=json.dumps(resource).encode(),
        headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.load(response)["issue"]
    except urllib.error.HTTPError as error:
        return json.load(error)["issue"]


def message(issue: dict) -> str:
    return issue.get("details", {}).get("text") or issue.get("diagnostics", "")


def ig_params() -> list[str]:
    return re.findall(r"-ig (\S+)", env_file(DATA_NODE_DIR / "fhir-validator" / ".env")["IG_PARAMS"])


@pytest.fixture(scope="module", autouse=True)
def _wait_for_validator():
    wait_for_url(VALIDATOR_URL, expect_status=None, timeout=600)


def test_validator_loads_every_ig_of_ig_params():
    log = subprocess.run(["docker", "logs", container("fhir-validator")], capture_output=True, text=True).stdout
    loaded = set(re.findall(r"Load (\S+#\S+) - \d+ resources", log))
    missing = [ig for ig in ig_params() if ig not in loaded]
    assert not missing, f"IGs of IG_PARAMS not loaded: {missing}"


@pytest.mark.parametrize("ig", ["de.medizininformatikinitiative.kerndatensatz.icu", "de.medizininformatikinitiative.kerndatensatz.mikrobiologie"])
def test_validator_resolves_the_profiles_of_the_2026_baseline(ig):
    """VA-1: validates the first example of the pinned IG. Its profile must be found."""
    pinned = next(p for p in ig_params() if p.startswith(f"{ig}#"))
    example_path = validator_sh(f"ls '{PACKAGES}/{pinned}/package/examples/'*.json | head -1").strip()
    example = json.loads(validator_sh(f"cat '{example_path}'"))
    not_found = [message(i) for i in validate(example) if "could not be found" in message(i) and "StructureDefinition" in message(i)]
    assert example["meta"]["profile"], example_path
    assert not not_found, not_found


def test_r5_cross_version_extensions_validate():
    """VA-3: the MII base Encounter examples that use hl7.org/fhir/5.0 extensions."""
    base = next(p for p in ig_params() if p.startswith("de.medizininformatikinitiative.kerndatensatz.base#"))
    paths = validator_sh(f"grep -l 'hl7.org/fhir/5.0/StructureDefinition' '{PACKAGES}/{base}/package/example/'*.json").split()
    assert paths, f"no example with an R5 extension in {base}"
    for path in paths:
        errors = [message(i) for i in validate(json.loads(validator_sh(f"cat '{path}'"))) if i["severity"] in ("error", "fatal")]
        assert not errors, f"{path}: {errors}"


@pytest.mark.xfail(strict=True, reason="D10: terminology-data/package.json allows ^2025.8.29, so "
                   "get-mii-terminology.sh update cannot reach the BOM 2026.8.25 of mii-fhir-validator alpha.9")
def test_terminology_package_range_reaches_the_2026_bom():
    package = json.loads((DATA_NODE_DIR / "terminology-server" / "terminology-data" / "package.json").read_text())
    wanted = package["dependencies"]["@mii-termserv/de.medizininformatikinitiative.kerndatensatz.terminology.bill-of-materials"]
    assert re.match(r"^\^?2026\.", wanted), wanted
