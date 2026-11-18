"""Fixtures shared by all suites. Plain helpers live in helpers.py."""

from __future__ import annotations

import time

import pytest

from backend_variant import QUOTA_USER, SIMPLE_CCDL, backend_variant
from helpers import create_portal_user, get_portal_access_token, portal_token

@pytest.fixture(scope="session")
def portal_token_response() -> dict:
    """Token response for the data portal test user (all three dataportal roles)."""
    return get_portal_access_token()


@pytest.fixture
def portal_access_token() -> str:
    """A valid access token for the portal test user (renewed before it expires)."""
    return portal_token()


@pytest.fixture(scope="session")
def quota_backend():
    """Backend with a soft quota of 1 query per minute (UI-18) and a result expiry of 2
    minutes (BE-5). Intervals below one minute count no queries (D22)."""
    with backend_variant({
        "PRIVACY_QUOTA_SOFT_CREATE_AMOUNT": "1",
        "PRIVACY_QUOTA_SOFT_CREATE_INTERVAL": "PT1M",
        "QUERYRESULT_EXPIRY": "PT2M",
    }, port=8092, label="quota") as backend:
        yield backend


@pytest.fixture(scope="session")
def quota_exceeded(quota_backend) -> tuple[int, dict, bytes]:
    """The response of the quota backend once the quota user has hit the soft quota."""
    create_portal_user(*QUOTA_USER, roles=("DataportalUser",))
    token = get_portal_access_token(*QUOTA_USER)["access_token"]
    for _ in range(3):
        response = quota_backend.request("/api/v6/query/feasibility", token, "POST", SIMPLE_CCDL)
        if response[0] != 201:
            return response
        time.sleep(1)
    return response
