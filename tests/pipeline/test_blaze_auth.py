"""S6, BL-3: Blaze 1.7.0+ can enforce the iss and aud claims of tokens.

The data node sets neither OPENID_PROVIDER_ISSUER nor OPENID_AUDIENCE, so Blaze logs a
warning and skips both checks. Each case starts a Blaze with in-memory storage next to the
regular one and sends a token of the node Keycloak, which has no aud claim.
"""

from __future__ import annotations

import contextlib
import re
import subprocess
import urllib.error
import urllib.request

import pytest

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, wait_for_url
from torch_client import env_file, fhir_token

PORT = 8098


def blaze_image() -> str:
    compose = (DATA_NODE_DIR / "fhir-server" / "docker-compose.yml").read_text()
    return re.search(r"image:\s*(samply/blaze:\S+)", compose).group(1)


@contextlib.contextmanager
def blaze_variant(env: dict[str, str]):
    name = f"{COMPOSE_PROJECT}-blaze-variant"
    node = env_file(DATA_NODE_DIR / "fhir-server" / ".env")
    environment = {
        "STORAGE": "in-memory",
        "JAVA_TOOL_OPTIONS": "-Xmx1g",
        "BASE_URL": f"http://localhost:{PORT}",
        "OPENID_PROVIDER_URL": node["OPENID_PROVIDER_URL"],
        "OPENID_CLIENT_TRUST_STORE": "/app/trust-store.p12",
        "OPENID_CLIENT_TRUST_STORE_PASS": node["OPENID_CLIENT_TRUST_STORE_PASS"],
    } | env
    command = ["docker", "run", "-d", "--name", name, "--network", f"{COMPOSE_PROJECT}_default",
               "--add-host", "auth.localhost:host-gateway", "-p", f"127.0.0.1:{PORT}:8080",
               "-v", f"{DATA_NODE_DIR / 'auth' / 'trust-store.p12'}:/app/trust-store.p12:ro"]
    for key, value in environment.items():
        command += ["-e", f"{key}={value}"]
    subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(command + [blaze_image()], check=True, capture_output=True)
    try:
        wait_for_url(f"http://localhost:{PORT}/health", timeout=180)
        yield f"http://localhost:{PORT}/fhir"
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def status(url: str, token: str | None) -> int:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


ISSUER = env_file(DATA_NODE_DIR / "fhir-server" / ".env")["OPENID_PROVIDER_URL"]

CASES = {
    "matching-issuer": ({"OPENID_PROVIDER_ISSUER": ISSUER}, 200),
    "other-issuer": ({"OPENID_PROVIDER_ISSUER": "https://other.example/realms/blaze"}, 401),
    # The blaze realm adds no audience mapper, so a required audience locks every client out.
    "required-audience": ({"OPENID_AUDIENCE": "blaze"}, 401),
}


@pytest.mark.parametrize("case", CASES)
def test_token_claims_are_enforced(case):
    env, expected = CASES[case]
    with blaze_variant(env) as fhir:
        assert status(f"{fhir}/Patient", None) == 401
        assert status(f"{fhir}/Patient", fhir_token()) == expected
