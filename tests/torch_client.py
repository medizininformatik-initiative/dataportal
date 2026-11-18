"""TORCH $extract-data client and FHIR server access for the node and pipeline suites.

TORCH writes its results to the file server of the data node (torch-nginx, see
data-node/torch/docker-compose.yml). The manifest links to the NDJSON bundles and to
the CSV reports, see https://medizininformatik-initiative.github.io/torch/api/api.html
"""

from __future__ import annotations

import base64
import contextlib
import csv
import io
import json
import pathlib
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, get_fhir_access_token, wait_for_url

TORCH_URL = "http://localhost:8086"
FHIR_URL = "http://localhost:8081/fhir"

CONSENT_CODE_PREFIX = "2.16.840.1.113883.3.1937.777.24.5.3"
CONSENT_SYSTEM = f"urn:oid:{CONSENT_CODE_PREFIX}"
CONSENT_CONTEXT = {"code": "Einwilligung", "display": "Einwilligung", "system": "fdpg.mii.cds", "version": "1.0.0"}
DIAGNOSE_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-diagnose/StructureDefinition/Diagnose"
PATIENT_PROFILE = "https://www.medizininformatik-initiative.de/fhir/core/modul-person/StructureDefinition/Patient"
CONSENT_PROFILE = "https://www.medizininformatik-initiative.de/fhir/modul-consent/StructureDefinition/mii-pr-consent-einwilligung"


class TorchError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"TORCH answered {status}: {body[:500]}")
        self.status = status
        self.body = body


def _request(url: str, data: bytes | None = None, headers: dict | None = None, method: str | None = None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    return urllib.request.urlopen(request, timeout=60)


# --- CRTDL -----------------------------------------------------------------------------


def consent_criterion(code_suffix: str) -> dict:
    """An Einwilligung criterion for the MII consent provision code ending in .<suffix>."""
    return {
        "termCodes": [{"code": f"{CONSENT_CODE_PREFIX}.{code_suffix}", "system": CONSENT_SYSTEM, "version": "1.0.7", "display": code_suffix}],
        "context": CONSENT_CONTEXT,
    }


def consent_inclusion(*suffixes: str) -> list[list[dict]]:
    """Inclusion criteria with one group per consent code, the shape the portal exports."""
    return [[consent_criterion(s)] for s in suffixes]


def condition_crtdl(inclusion: list[list[dict]] | None) -> dict:
    """A CRTDL that extracts Patient and Diagnose Condition. Without inclusion criteria
    TORCH enforces no consent."""
    cohort = {"version": "http://to_be_decided.com/draft-1/schema#", "display": "S7", "inclusionCriteria": inclusion or []}
    return {
        "version": "http://json-schema.org/to-be-done/schema#",
        "display": "S7 consent",
        "cohortDefinition": cohort,
        "dataExtraction": {
            "attributeGroups": [
                {
                    "id": "patient",
                    "name": "Patient",
                    "groupReference": PATIENT_PROFILE,
                    "attributes": [{"attributeRef": "Patient.gender", "mustHave": False}],
                },
                {
                    "id": "condition",
                    "name": "Diagnose",
                    "groupReference": DIAGNOSE_PROFILE,
                    "attributes": [
                        {"attributeRef": "Condition.code", "mustHave": False},
                        {"attributeRef": "Condition.recordedDate", "mustHave": False},
                    ],
                },
            ]
        },
    }


# --- $extract-data -----------------------------------------------------------------------


def submit(crtdl: dict, patients: list[str] | None = None, diagnostics: bool = False, torch_url: str = TORCH_URL) -> str:
    """Starts an extraction and returns the status URL."""
    parameters = [{"name": "crtdl", "valueBase64Binary": base64.b64encode(json.dumps(crtdl).encode()).decode()}]
    parameters += [{"name": "patient", "valueString": p} for p in patients or []]
    if diagnostics:
        parameters.append({"name": "consentDiagnostics", "valueBoolean": True})
    body = json.dumps({"resourceType": "Parameters", "parameter": parameters}).encode()
    try:
        with _request(f"{torch_url}/fhir/$extract-data", body, {"Content-Type": "application/fhir+json"}) as response:
            return response.headers["Content-Location"]
    except urllib.error.HTTPError as error:
        raise TorchError(error.code, error.read().decode(errors="replace")) from None


def wait(status_url: str, timeout: float = 600) -> dict:
    """Polls the status URL until the job completes and returns the manifest. Raises
    TorchError when the job fails."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with _request(status_url) as response:
                if response.status == 200:
                    return json.load(response)
        except urllib.error.HTTPError as error:
            raise TorchError(error.code, error.read().decode(errors="replace")) from None
        time.sleep(1)
    raise TimeoutError(f"TORCH job {status_url} not finished after {timeout}s")


def extract(
    crtdl: dict, patients: list[str] | None = None, diagnostics: bool = False, torch: "Variant | None" = None
) -> "Result":
    torch_url = torch.url if torch else TORCH_URL
    return Result(wait(submit(crtdl, patients, diagnostics, torch_url)), torch.output if torch else None)


def env_file(path: pathlib.Path) -> dict[str, str]:
    """KEY=VALUE lines of a compose .env file, with quotes removed as compose does
    (docker run --env-file would keep them)."""
    values = {}
    for line in path.read_text().splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", line.strip())
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


class Variant:
    """A second TORCH container with extra environment, see torch_variant()."""

    def __init__(self, url: str, output: pathlib.Path):
        self.url = url
        self.output = output


@contextlib.contextmanager
def torch_variant(env: dict[str, str], port: int = 8096):
    """Runs the pinned TORCH image with the data node's torch/.env plus `env`, next to
    the regular TORCH. Its results go to a host directory instead of the file server."""
    compose = (DATA_NODE_DIR / "torch" / "docker-compose.yml").read_text()
    image = re.search(r"image:\s*(ghcr.io/medizininformatik-initiative/torch:\S+)", compose).group(1)
    name = f"{COMPOSE_PROJECT}-torch-variant"
    output = pathlib.Path(tempfile.mkdtemp(prefix="torch-variant-"))
    output.chmod(0o777)
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    command = [
        "docker", "run", "-d", "--name", name, "--network", f"{COMPOSE_PROJECT}_default",
        "--add-host", "auth.localhost:host-gateway", "--add-host", "host.docker.internal:host-gateway",
        "-p", f"127.0.0.1:{port}:8080",
        "-v", f"{DATA_NODE_DIR / 'auth'}:/app/certs", "-v", f"{output}:/app/output",
    ]
    environment = env_file(DATA_NODE_DIR / "torch" / ".env") | {
        "TORCH_BASE_URL": f"http://localhost:{port}",
        "TORCH_OUTPUT_FILE_SERVER_URL": "http://torch-variant",
        # torch/.env asks for 8 GB, next to the regular TORCH and the validator
        "JAVA_TOOL_OPTIONS": "-Xmx3g",
    } | env
    for key, value in environment.items():
        command += ["-e", f"{key}={value}"]
    subprocess.run(command + [image], check=True, capture_output=True)
    try:
        wait_for_url(f"http://localhost:{port}/actuator/health", timeout=180)
        wait_for_url(f"http://localhost:{port}/fhir/metadata", timeout=60)
        yield Variant(f"http://localhost:{port}", output)
    except BaseException:
        logs = subprocess.run(["docker", "logs", "--tail", "40", name], capture_output=True, text=True)
        state = subprocess.run(["docker", "inspect", "-f", "{{json .State}}", name], capture_output=True, text=True)
        print(f"TORCH variant state: {state.stdout}\n{logs.stdout}{logs.stderr}")
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


class Result:
    """A completed TORCH job: its bundles and reports."""

    def __init__(self, manifest: dict, output: pathlib.Path | None = None):
        self.manifest = manifest
        self.output = output
        self.extensions = {e["url"]: e for e in manifest.get("extension", [])}

    @property
    def job(self) -> dict:
        return self.extensions["https://torch.mii.de/fhir/StructureDefinition/torch-job"]["valueObject"]

    @property
    def summary(self) -> dict:
        return self.extensions.get("torch-job-diagnostics-summary", {}).get("valueObject", {})

    def read(self, url: str) -> str:
        """Content of a result file, from the file server or from the variant's directory."""
        if self.output:
            return (self.output / urllib.parse.urlparse(url).path.lstrip("/")).read_text()
        with _request(url) as response:
            return response.read().decode()

    def bundles(self) -> list[dict]:
        return [
            json.loads(line)
            for output in self.manifest["output"]
            for line in self.read(output["url"]).splitlines()
            if line.strip()
        ]

    def resources(self, resource_type: str | None = None) -> list[dict]:
        resources = [e["resource"] for b in self.bundles() for e in b.get("entry", [])]
        return [r for r in resources if resource_type in (None, r["resourceType"])]

    def report(self, name: str) -> list[dict] | None:
        """Rows of the CSV report of the extension torch-<name>, None if TORCH wrote none."""
        extension = self.extensions.get(f"torch-{name}")
        if not extension:
            return None
        return list(csv.DictReader(io.StringIO(self.read(extension["valueUrl"]))))


# --- FHIR server -------------------------------------------------------------------------

_token: tuple[float, str] | None = None


def fhir_token() -> str:
    """Access token for the FHIR server, reused for a minute (fetching one starts a container)."""
    global _token
    if _token is None or time.monotonic() - _token[0] > 60:
        _token = (time.monotonic(), get_fhir_access_token())
    return _token[1]



def fhir_transaction(entries: list[dict]) -> dict:
    """Sends a transaction bundle to the FHIR server of the data node."""
    body = json.dumps({"resourceType": "Bundle", "type": "transaction", "entry": entries}).encode()
    headers = {"Content-Type": "application/fhir+json", "Authorization": f"Bearer {fhir_token()}"}
    try:
        with _request(FHIR_URL, body, headers) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise AssertionError(f"FHIR transaction failed {error.code}: {error.read()[:500]}") from None


def put_resources(resources: list[dict]) -> None:
    fhir_transaction([
        {"resource": r, "request": {"method": "PUT", "url": f"{r['resourceType']}/{r['id']}"}} for r in resources
    ])


def delete_resources(resources: list[dict]) -> None:
    fhir_transaction([
        {"request": {"method": "DELETE", "url": f"{r['resourceType']}/{r['id']}"}} for r in resources
    ])
