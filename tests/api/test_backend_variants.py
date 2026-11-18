"""S6: backend config variants, each in its own container (tests/backend_variant.py).

BE-5   QUERYRESULT_EXPIRY reaches the UI through /.settings
UI-18  the soft quota answers 429 with Retry-After and FEAS-10002 (the UI part is in
       tests/ui/test_rate_limit.py)
BE-7   with the FHIR server unreachable, the direct broker logs the failed dispatch
"""

from __future__ import annotations

import json
import re
import time

import pytest

from backend_variant import SIMPLE_CCDL, backend_variant
from helpers import DATA_PORTAL_DIR, portal_request, portal_token
from torch_client import env_file

pytestmark = pytest.mark.smoke


def test_result_expiry_is_published_in_settings(quota_backend):
    status, _, body = quota_backend.request("/.settings")
    assert status == 200
    assert json.loads(body)["queryResultExpiry"] == "PT2M"
    status, settings = portal_request("/.settings")
    assert settings["queryResultExpiry"] == env_file(DATA_PORTAL_DIR / "backend" / ".env")["QUERYRESULT_EXPIRY"]


def test_soft_quota_answers_429(quota_exceeded):
    status, headers, body = quota_exceeded
    assert status == 429, body
    retry_after = {k.lower(): v for k, v in headers.items()}["retry-after"]
    assert 0 < int(retry_after) <= 60
    assert [i["code"] for i in json.loads(body)["issues"]] == ["FEAS-10002"]


@pytest.fixture(scope="module")
def broken_backend():
    with backend_variant({"CQL_SERVER_BASE_URL": "http://s6-fhir-server-down:8080/fhir"}, port=8093, label="broken") as backend:
        yield backend


@pytest.fixture(scope="module")
def failed_dispatch(broken_backend) -> tuple[str, str]:
    """Posts a query to the backend without FHIR server and returns (query id, log)."""
    status, headers, body = broken_backend.request("/api/v6/query/feasibility", portal_token(), "POST", SIMPLE_CCDL)
    assert status == 201, body
    query_id = {k.lower(): v for k, v in headers.items()}["location"].rstrip("/").rsplit("/", 1)[1]
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        log = broken_backend.logs()
        if f"Failed to dispatch query '{query_id}'" in log:
            return query_id, log
        time.sleep(1)
    pytest.fail(f"no dispatch error for query {query_id} in the backend log")


def test_dispatch_failure_is_logged(failed_dispatch):
    query_id, log = failed_dispatch
    assert re.search(rf"ERROR .*Failed to dispatch query '{query_id}' with broker type 'DIRECT'", log)


@pytest.mark.xfail(strict=True, reason="D21: backend 9.5.0 logs 'An error occurred while trying to create "
                   "measure and library' and 'Dispatch failed for all brokers', but not the cause (host, connection error)")
def test_dispatch_failure_log_names_the_cause(failed_dispatch):
    _, log = failed_dispatch
    assert "s6-fhir-server-down" in log
