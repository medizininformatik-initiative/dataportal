"""Page actions shared by the UI tests. Selectors follow the dataportal-ui Cypress suite
(cypress/support/commands.ts and component-objects/NumUserMenu.ts)."""

from __future__ import annotations

import re

from playwright.sync_api import Page, expect

from helpers import PORTAL_AUTH_URL, PORTAL_TEST_PASSWORD, PORTAL_TEST_USER, PORTAL_URL

USER_MENU = "num-header-user-menu mat-select"
LOGOUT_LABEL = re.compile(r"^\s*(Log Out|Abmelden)\s*$")


def expect_keycloak_login_form(page: Page) -> None:
    expect(page).to_have_url(re.compile(f"^{re.escape(PORTAL_AUTH_URL)}/"))
    expect(page.locator("input[name=username]")).to_be_visible()


def login(page: Page, username: str = PORTAL_TEST_USER, password: str = PORTAL_TEST_PASSWORD) -> None:
    """Opens the portal, signs in on the Keycloak page and waits for the app header."""
    page.goto(f"{PORTAL_URL}/")
    expect_keycloak_login_form(page)
    page.locator("input[name=username]").fill(username)
    page.locator("input[name=password]").fill(password)
    page.locator("#kc-login").click()
    expect(page.locator(USER_MENU)).to_be_visible(timeout=60_000)
    expect(page).not_to_have_url(re.compile(f"^{re.escape(PORTAL_AUTH_URL)}/"))


def logout(page: Page) -> None:
    """Logs out through the header user menu."""
    page.locator(USER_MENU).click()
    page.locator(".mat-mdc-option").filter(has_text=LOGOUT_LABEL).click()
    expect_keycloak_login_form(page)
