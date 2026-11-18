"""C1: the test user signs in through the portal Keycloak, the app loads without browser
errors, and logging out returns to the Keycloak sign-in page."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from ui.pages.portal import login, logout

pytestmark = pytest.mark.smoke


def test_login_and_logout(page: Page):
    login(page)
    logout(page)


def test_app_loads_without_console_errors(page: Page, console_errors: list[str]):
    login(page)
    page.wait_for_load_state("networkidle")
    assert console_errors == [], "\n".join(console_errors)
