"""Shared helpers for the e2e and integration tests.

Assumes the stacks are already running: a data node (see
.github/scripts/setup-data-node.sh) with MII testdata loaded (see
data-node/get-mii-testdata.sh and data-node/upload-testdata.sh), and for the
api/ and ui/ suites also a data portal (see .github/scripts/setup-data-portal.sh
and .github/scripts/create-portal-test-user.sh). These tests only cover what
happens on top of that base setup.
"""

from __future__ import annotations

import http.client
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

KNOWN_ISSUES_FILE = REPO_ROOT / "tests" / "golden" / "known-issues.json"


def assert_only_known_issues(check: str, problems: list[str]) -> None:
    """Fails on problems that are not in golden/known-issues.json, and on known issues
    that no longer occur, so the baseline stays current."""
    known = set(json.loads(KNOWN_ISSUES_FILE.read_text()).get(check, {}).get("items", []))
    new, fixed = sorted(set(problems) - known), sorted(known - set(problems))
    message = []
    if new:
        message.append(f"new problems ({len(new)}):\n  " + "\n  ".join(new))
    if fixed:
        message.append(f"fixed, remove from {KNOWN_ISSUES_FILE.name} [{check}] ({len(fixed)}):\n  " + "\n  ".join(fixed))
    assert not message, "\n".join(message)


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
        except (urllib.error.URLError, ConnectionError, http.client.HTTPException) as error:
            last_error = error
            time.sleep(2)
            continue

        if expect_status is None or status == expect_status:
            return
        last_error = f"got HTTP {status}, expected {expect_status}"
        time.sleep(2)

    raise TimeoutError(f"{url} was not ready after {timeout}s ({last_error})")


def wait_for_validator(url: str, profiles: dict[str, str], timeout: float = 600) -> None:
    """Waits until the validator at `url` (its /validateResource endpoint) resolves every
    profile of `profiles` (profile URL -> resource type). The validator answers HTTP
    requests before it has loaded its IGs, so any HTTP status is no sign of readiness:
    until then it reports the profile of a resource as not found."""
    deadline = time.monotonic() + timeout
    pending = list(profiles)
    last_error: object = "no attempt made"
    while time.monotonic() < deadline:
        try:
            for profile in list(pending):
                probe = json.dumps({"resourceType": profiles[profile], "meta": {"profile": [profile]}}).encode()
                request = urllib.request.Request(
                    url, data=probe, headers={"Content-Type": "application/fhir+json", "Accept": "application/fhir+json"}
                )
                try:
                    with urllib.request.urlopen(request, timeout=60) as response:
                        issues = json.load(response)["issue"]
                except urllib.error.HTTPError as error:
                    issues = json.load(error)["issue"]
                texts = [i.get("details", {}).get("text") or i.get("diagnostics", "") for i in issues]
                unresolved = [t for t in texts if "could not be found" in t and profile in t]
                if unresolved:
                    last_error = unresolved[0]
                    break
                pending.remove(profile)
            if not pending:
                return
        except (urllib.error.URLError, ConnectionError, http.client.HTTPException, ValueError, KeyError) as error:
            last_error = error
        time.sleep(5)
    raise TimeoutError(f"validator {url} did not resolve {pending} after {timeout}s ({last_error})")


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


def create_portal_user(username: str, password: str, roles: tuple[str, ...]) -> None:
    """Creates a user in the portal Keycloak with exactly `roles`, like
    .github/scripts/create-portal-test-user.sh does for the main test user."""
    env = {}
    for line in (DATA_PORTAL_DIR / "keycloak" / ".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip().strip('"')

    def kcadm(*args: str) -> str:
        result = subprocess.run(
            ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(DATA_PORTAL_DIR / "keycloak" / "docker-compose.yml"),
             "exec", "-T", "auth", "/opt/keycloak/bin/kcadm.sh", *args, "--config", "/tmp/kcadm.config"],
            capture_output=True, text=True,
        )
        result.check_returncode()
        return result.stdout

    kcadm("config", "credentials", "--server", "http://localhost:8080/auth", "--realm", "master",
          "--user", env["KC_BOOTSTRAP_ADMIN_USERNAME"], "--password", env["KC_BOOTSTRAP_ADMIN_PASSWORD"])
    if not kcadm("get", "users", "-r", PORTAL_REALM, "-q", "exact=true", "-q", f"username={username}", "--fields", "id").strip(" []\n"):
        kcadm("create", "users", "-r", PORTAL_REALM, "-s", f"username={username}", "-s", "enabled=true",
              "-s", "firstName=Test", "-s", "lastName=User", "-s", f"email={username}@example.com", "-s", "emailVerified=true")
    kcadm("set-password", "-r", PORTAL_REALM, "--username", username, "--new-password", password)
    for role in roles:
        kcadm("add-roles", "-r", PORTAL_REALM, "--uusername", username, "--rolename", role)


_PORTAL_TOKEN: dict = {}


def portal_token() -> str:
    """Access token of the portal test user, renewed a minute before it expires. Keycloak
    issues tokens for 5 minutes by default, shorter than a full test run."""
    now = time.time()
    if not _PORTAL_TOKEN or _PORTAL_TOKEN["expires"] - now < 60:
        response = get_portal_access_token()
        _PORTAL_TOKEN.update(token=response["access_token"], expires=now + response.get("expires_in", 300))
    return _PORTAL_TOKEN["token"]


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


# Backend Elasticsearch, published on the host by data-portal/backend/docker-compose.yml.
PORTAL_ES_URL = os.environ.get("PORTAL_ES_URL", "http://localhost:9200")
COMPOSE_PROJECT = os.environ.get("DATA_PORTAL_COMPOSE_PROJECT", "dataportal")


def container_logs(service: str) -> str:
    """Returns the logs of a service container of the compose project."""
    result = subprocess.run(
        ["docker", "logs", f"{COMPOSE_PROJECT}-{service}-1"], capture_output=True, text=True
    )
    result.check_returncode()
    return result.stdout + result.stderr


def pinned_ontology_tag() -> str:
    """The ontology tag the backend Elasticsearch is loaded with (ONTO_GIT_TAG of the
    es-init service in data-portal/backend/docker-compose.yml)."""
    compose = (DATA_PORTAL_DIR / "backend" / "docker-compose.yml").read_text()
    match = re.search(r"ONTO_GIT_TAG:\s*(\S+)", compose)
    assert match, "ONTO_GIT_TAG not found in data-portal/backend/docker-compose.yml"
    return match.group(1)
