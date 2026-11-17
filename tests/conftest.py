"""Fixtures shared by all suites. Plain helpers live in helpers.py."""

from __future__ import annotations

import pytest

from helpers import get_portal_access_token, portal_token


@pytest.fixture(scope="session")
def portal_token_response() -> dict:
    """Token response for the data portal test user (all three dataportal roles)."""
    return get_portal_access_token()


@pytest.fixture
def portal_access_token() -> str:
    """A valid access token for the portal test user (renewed before it expires)."""
    return portal_token()
