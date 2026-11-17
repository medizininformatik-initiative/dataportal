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


@pytest.mark.xfail(
    strict=True,
    reason=(
        "dataportal-ui 7.3.4-rc4 requests /backend/.settings with 'Authorization: Bearer null' "
        "before the token exists, the backend answers 401 and the UI logs 'CoreInitService "
        "failed'. It retries with the token and continues. Remove this marker once fixed."
    ),
)
def test_app_loads_without_console_errors(page: Page, console_errors: list[str]):
    login(page)
    page.wait_for_load_state("networkidle")
    assert console_errors == [], "\n".join(console_errors)
