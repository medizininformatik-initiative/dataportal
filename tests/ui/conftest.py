"""Playwright setup for the UI suite (pytest-playwright provides `page`)."""

from __future__ import annotations

import pytest
from playwright.sync_api import ConsoleMessage, Error, Page


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        # The portal runs with a self-signed certificate (data-portal/setup-base-auth.sh).
        "ignore_https_errors": True,
        "locale": "en-US",
        "viewport": {"width": 1440, "height": 900},
    }


@pytest.fixture
def console_errors(page: Page) -> list[str]:
    """Collects browser console errors and uncaught page errors of the test."""
    errors: list[str] = []

    def on_console(message: ConsoleMessage) -> None:
        if message.type == "error":
            errors.append(f"console: {message.text} ({message.location.get('url')})")

    def on_page_error(error: Error) -> None:
        errors.append(f"page error: {error.message}")

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    return errors
