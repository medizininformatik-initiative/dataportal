"""S6, BL-2: the Blaze frontend 1.13.0 behind the data node reverse proxy.

Sign-in goes through the node Keycloak (realm blaze) with Better Auth, whose session
cookies are about 6 KB. The realm import has no users, so the test creates one.
"""

from __future__ import annotations

import subprocess

import pytest
from playwright.sync_api import Page, Response, expect

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR
from torch_client import env_file

pytestmark = pytest.mark.smoke

FRONTEND_URL = "https://fhir.localhost:444/fhir/"
BLAZE_USER = ("s6-blaze-user", "s6-blaze-password")


@pytest.fixture(scope="module")
def blaze_user() -> tuple[str, str]:
    env = env_file(DATA_NODE_DIR / "fhir-server" / ".env")

    def kcadm(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "exec", f"{COMPOSE_PROJECT}-fhir-server-frontend-keycloak-1", "/opt/keycloak/bin/kcadm.sh",
             *args, "--config", "/tmp/kcadm.config"], capture_output=True, text=True,
        )

    kcadm("config", "credentials", "--server", "http://localhost:8080", "--realm", "master",
          "--user", env["KC_BOOTSTRAP_ADMIN_USERNAME"], "--password", env["KC_BOOTSTRAP_ADMIN_PASSWORD"]).check_returncode()
    username, password = BLAZE_USER
    # fails when the user exists already, which is fine
    kcadm("create", "users", "-r", "blaze", "-s", f"username={username}", "-s", "enabled=true", "-s", "firstName=S6",
          "-s", "lastName=Blaze", "-s", f"email={username}@example.com", "-s", "emailVerified=true")
    kcadm("set-password", "-r", "blaze", "--username", username, "--new-password", password).check_returncode()
    return BLAZE_USER


def test_sign_in_browse_and_sign_out(page: Page, blaze_user):
    failed: list[str] = []

    def on_response(response: Response) -> None:
        if response.status >= 400:
            failed.append(f"{response.status} {response.url}")

    page.on("response", on_response)
    page.goto(FRONTEND_URL)
    page.get_by_role("button", name="Sign in with Keycloak").click()
    page.wait_for_url("**/realms/blaze/**")
    page.fill("#username", blaze_user[0])
    page.fill("#password", blaze_user[1])
    page.click("#kc-login")
    page.wait_for_url(FRONTEND_URL)
    expect(page.get_by_role("link", name="Patient", exact=True)).to_be_visible()

    page.goto(f"{FRONTEND_URL}Patient")
    expect(page.get_by_text("mii-exa-test-data-patient-1").first).to_be_visible()

    page.get_by_role("button", name="Open user menu").click()
    page.get_by_role("menuitem", name="Sign out").click()
    page.wait_for_url("**/__sign-in**")
    page.goto(f"{FRONTEND_URL}Patient")
    page.wait_for_url("**/__sign-in**")
    assert not failed, failed
