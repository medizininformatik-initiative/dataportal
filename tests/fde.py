"""Runs fhir-data-evaluator (FDE) once against the data node's FHIR server.

The data node's fhir-data-evaluator/.env points at http://localhost:8080/fhir (D11), so
the runs here override the source and report server with the fhir-server service.
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
import urllib.request
import zipfile

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR
from torch_client import FHIR_URL, env_file, fhir_token

FDE_DIR = DATA_NODE_DIR / "fhir-data-evaluator"
REPORT_IDENT = "fdpg-data-availability-report"


def fhir_get(path: str) -> dict:
    request = urllib.request.Request(f"{FHIR_URL}/{path}", headers={"Authorization": f"Bearer {fhir_token()}"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def fde_measure() -> pathlib.Path:
    """The measure file run-fde.sh uses, downloaded the same way if missing."""
    script = (FDE_DIR / "run-fde.sh").read_text()
    version = re.search(r"ONTOLOGY_VERSION=\$\{ONTOLOGY_VERSION:-(\S+)\}", script).group(1)
    measure = FDE_DIR / "measure" / f"Measure-CdsCodingAvailability.fhir_v{version}.json"
    if not measure.exists():
        url = f"https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v{version}/availability.zip"
        with urllib.request.urlopen(url, timeout=120) as response:
            archive = zipfile.ZipFile(io.BytesIO(response.read()))
        measure.parent.mkdir(exist_ok=True)
        measure.write_bytes(archive.read("Measure-CdsCodingAvailability.fhir.json"))
    return measure


def run_fde(**overrides: str) -> tuple[dict, dict]:
    """Runs FDE with the data node's .env plus `overrides`, uploads the report to the FHIR
    server and returns its (DocumentReference, MeasureReport)."""
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = env_file(FDE_DIR / ".env") | {
        "FHIR_SOURCE_SERVER": "http://fhir-server:8080/fhir",
        "FHIR_REPORT_SERVER": "http://fhir-server:8080/fhir",
        "SEND_REPORT_TO_SERVER": "true",
        "CREATE_OBFUSCATED_REPORT": "false",
        "PROJECT_IDENTIFIER_VALUE": REPORT_IDENT,
    } | overrides
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
    reports = [d["resource"] for d in documents if d["resource"].get("masterIdentifier", {}).get("value") == REPORT_IDENT]
    assert len(reports) == 1, f"expected one DocumentReference of the FDE run, found {len(reports)}"
    document = reports[0]
    return document, fhir_get(document["content"][0]["attachment"]["url"])
