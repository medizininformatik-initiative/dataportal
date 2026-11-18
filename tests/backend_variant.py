"""A second dataportal-backend container with config overrides, next to the regular one.

It runs the pinned image with the portal's backend/.env plus overrides on the compose
network, so it shares Postgres, Elasticsearch and Keycloak with the regular backend and
accepts the same tokens. It is reached directly on its own port, not through the proxy.
"""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import urllib.error
import urllib.request

from helpers import COMPOSE_PROJECT, DATA_PORTAL_DIR, wait_for_url
from torch_client import env_file


# A portal user without DataportalPowerUser, so the hard quota applies too.
QUOTA_USER = ("s6-quota-user", "s6-quota-password")
SIMPLE_CCDL = {
    "version": "http://json-schema.org/to-be-done/schema#",
    "display": "S6 quota",
    "inclusionCriteria": [[{
        "termCodes": [{"code": "263495000", "system": "http://snomed.info/sct", "display": "Geschlecht"}],
        "context": {"code": "Patient", "system": "fdpg.mii.cds", "version": "1.0.0", "display": "Patient"},
        "valueFilter": {"type": "concept", "selectedConcepts": [{"code": "male", "system": "http://hl7.org/fhir/administrative-gender", "display": "Male"}]},
    }]],
}


def backend_image() -> str:
    compose = (DATA_PORTAL_DIR / "backend" / "docker-compose.yml").read_text()
    return re.search(r"image:\s*(ghcr.io/medizininformatik-initiative/dataportal-backend:\S+)", compose).group(1)


class Backend:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url

    def request(self, path: str, token: str | None = None, method: str = "GET", body: object | None = None):
        headers = {"Content-Type": "application/json"} | ({"Authorization": f"Bearer {token}"} if token else {})
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{self.url}{path}", data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def logs(self) -> str:
        result = subprocess.run(["docker", "logs", self.name], capture_output=True, text=True)
        return result.stdout + result.stderr


@contextlib.contextmanager
def backend_variant(env: dict[str, str], port: int, label: str):
    name = f"{COMPOSE_PROJECT}-backend-{label}"
    environment = env_file(DATA_PORTAL_DIR / "backend" / ".env") | {
        # set in backend/docker-compose.yml, not in .env
        "QUERYRESULT_DISABLE_LOG_FILE_ENCRYPTION": "true",
    } | env
    command = [
        "docker", "run", "-d", "--name", name, "--network", f"{COMPOSE_PROJECT}_default",
        "--add-host", "auth.localhost:host-gateway", "-p", f"127.0.0.1:{port}:8090",
        "-v", f"{DATA_PORTAL_DIR / 'auth'}:/opt/dataportal-backend/certs",
    ]
    for key, value in environment.items():
        command += ["-e", f"{key}={value}"]
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(command + [backend_image()], check=True, capture_output=True)
    backend = Backend(name, f"http://localhost:{port}")
    try:
        wait_for_url(f"{backend.url}/api/v6/actuator/health", timeout=300)
        yield backend
    except BaseException:
        print(f"backend variant {label}:\n{backend.logs()[-4000:]}")
        raise
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
