"""Smoke checks that the data portal backend is up and accepts tokens of the portal
Keycloak. Runs against the stack started by .github/scripts/setup-data-portal.sh."""

from __future__ import annotations

import base64
import json

import pytest

from helpers import PORTAL_TEST_ROLES, portal_request

pytestmark = pytest.mark.smoke

TERMINOLOGY_SYSTEMS = "/api/v6/terminology/systems"


def _jwt_claims(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


def test_backend_health_is_up():
    status, body = portal_request("/api/v6/actuator/health")
    assert status == 200
    assert body["status"] == "UP"


def test_test_user_has_all_dataportal_roles(portal_access_token: str):
    roles = _jwt_claims(portal_access_token).get("realm_access", {}).get("roles", [])
    assert set(PORTAL_TEST_ROLES) <= set(roles)


def test_terminology_rejects_requests_without_token():
    status, _ = portal_request(TERMINOLOGY_SYSTEMS)
    assert status == 401


def test_terminology_accepts_portal_token(portal_access_token: str):
    status, body = portal_request(TERMINOLOGY_SYSTEMS, token=portal_access_token)
    assert status == 200, body
    assert body, "backend returned no terminology systems - is the ontology loaded?"
