"""Shared helpers for the e2e and integration tests.

Assumes the stacks are already running: a data node (see
.github/scripts/setup-data-node.sh) with MII testdata loaded (see
data-node/get-mii-testdata.sh and data-node/upload-testdata.sh), and for the
api/ and ui/ suites also a data portal (see .github/scripts/setup-data-portal.sh
and .github/scripts/create-portal-test-user.sh). These tests only cover what
happens on top of that base setup.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_NODE_DIR = REPO_ROOT / "data-node"
DATA_PORTAL_DIR = REPO_ROOT / "data-portal"

# Data portal in its default context path setup (see data-portal/proxy/context-paths.nginx.conf).
PORTAL_URL = os.environ.get("PORTAL_URL", "https://localhost")
PORTAL_BACKEND_URL = f"{PORTAL_URL}/backend"
PORTAL_AUTH_URL = f"{PORTAL_URL}/auth"
PORTAL_REALM = "dataportal"
PORTAL_CLIENT_ID = "dataportal"
PORTAL_CA_CERT = DATA_PORTAL_DIR / "auth" / "ca-cert.pem"

# Created by .github/scripts/create-portal-test-user.sh
PORTAL_TEST_USER = os.environ.get("PORTAL_TEST_USER", "testuser")
PORTAL_TEST_PASSWORD = os.environ.get("PORTAL_TEST_PASSWORD", "testpassword")
PORTAL_TEST_ROLES = ("DataportalUser", "DataportalPowerUser", "DataportalAdmin")

_JOB_ID_RE = re.compile(r"Job ID: (\S+)")


def wait_for_url(url: str, expect_status: int | None = 200, timeout: float = 120) -> None:
    """Polls a URL until it responds - by default until it returns `expect_status`,
    or, if expect_status is None, until it responds with any status at all (for
    services with no dedicated health endpoint)."""
    deadline = time.monotonic() + timeout
    last_error: object = "no attempt made"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except urllib.error.URLError as error:
            last_error = error
            time.sleep(2)
            continue

        if expect_status is None or status == expect_status:
            return
        last_error = f"got HTTP {status}, expected {expect_status}"
        time.sleep(2)

    raise TimeoutError(f"{url} was not ready after {timeout}s ({last_error})")


def get_fhir_access_token() -> str:
    """Fetches an OAuth access token for the FHIR server (see
    data-node/get-fhir-server-access-token.sh)."""
    result = subprocess.run(
        ["bash", str(DATA_NODE_DIR / "get-fhir-server-access-token.sh")],
        capture_output=True,
        text=True,
    )
    print(result.stderr)
    result.check_returncode()
    return result.stdout.strip()


def run_aether_pipeline(project_dir: pathlib.Path, pipeline_config: str, crtdl: str) -> str:
    """Runs `aether pipeline start` in project_dir and returns the resulting job id."""
    result = subprocess.run(
        ["aether", "pipeline", "start", pipeline_config, crtdl],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print(result.stderr)
    result.check_returncode()

    match = _JOB_ID_RE.search(result.stdout + result.stderr)
    if not match:
        raise RuntimeError("could not find a 'Job ID: ...' line in aether's output")
    return match.group(1)


def portal_ssl_context() -> ssl.SSLContext:
    """TLS context that trusts the CA of the data portal's self-signed certificate
    (see data-portal/setup-base-auth.sh)."""
    return ssl.create_default_context(cafile=str(PORTAL_CA_CERT))


def get_portal_access_token(
    username: str = PORTAL_TEST_USER, password: str = PORTAL_TEST_PASSWORD
) -> dict:
    """Fetches a token for the data portal test user with a password grant. The
    realm's public `dataportal` client has direct access grants enabled (see
    data-portal/keycloak/init/dataportal-realm.json). Returns the token response."""
    data = urllib.parse.urlencode(
        {
            "grant_type": "password",
            "client_id": PORTAL_CLIENT_ID,
            "username": username,
            "password": password,
            "scope": "openid",
        }
    ).encode()
    request = urllib.request.Request(
        f"{PORTAL_AUTH_URL}/realms/{PORTAL_REALM}/protocol/openid-connect/token", data=data
    )
    with urllib.request.urlopen(request, context=portal_ssl_context(), timeout=30) as response:
        return json.load(response)


def portal_request(
    path: str, token: str | None = None, method: str = "GET", body: object | None = None
) -> tuple[int, object]:
    """Calls the data portal backend (path relative to PORTAL_BACKEND_URL, e.g.
    /api/v6/terminology/systems). Returns (status, parsed JSON body or raw text)."""
    headers = {"Accept": "application/json"}
    data = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    request = urllib.request.Request(
        f"{PORTAL_BACKEND_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, context=portal_ssl_context(), timeout=60) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as error:
        status, raw = error.code, error.read()
    text = raw.decode(errors="replace")
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text
