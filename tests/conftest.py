"""Fixtures shared by all suites. Plain helpers live in helpers.py."""

from __future__ import annotations

import pytest

from helpers import get_portal_access_token


@pytest.fixture(scope="session")
def portal_token() -> dict:
    """Token response for the data portal test user (all three dataportal roles)."""
    return get_portal_access_token()


@pytest.fixture(scope="session")
def portal_access_token(portal_token: dict) -> str:
    return portal_token["access_token"]
