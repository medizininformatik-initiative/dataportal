"""Shared helpers for data node e2e tests.

Assumes a data node is already running (see .github/scripts/setup-data-node.sh)
with MII testdata already loaded (see data-node/get-mii-testdata.sh and
data-node/upload-testdata.sh) - these tests only cover what happens on top of
that base setup.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_NODE_DIR = REPO_ROOT / "data-node"

_JOB_ID_RE = re.compile(r"Job ID: (\S+)")


def wait_for_url(url: str, expect_status: int | None = 200, timeout: float = 120) -> None:
    """Polls a URL until it responds - by default until it returns `expect_status`,
    or, if expect_status is None, until it responds with any status at all (for
    services with no dedicated health endpoint)."""
    deadline = time.monotonic() + timeout
    last_error: object = "no attempt made"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        except urllib.error.URLError as error:
            last_error = error
            time.sleep(2)
            continue

        if expect_status is None or status == expect_status:
            return
        last_error = f"got HTTP {status}, expected {expect_status}"
        time.sleep(2)

    raise TimeoutError(f"{url} was not ready after {timeout}s ({last_error})")


def get_fhir_access_token() -> str:
    """Fetches an OAuth access token for the FHIR server (see
    data-node/get-fhir-server-access-token.sh)."""
    result = subprocess.run(
        ["bash", str(DATA_NODE_DIR / "get-fhir-server-access-token.sh")],
        capture_output=True,
        text=True,
    )
    print(result.stderr)
    result.check_returncode()
    return result.stdout.strip()


def run_aether_pipeline(project_dir: pathlib.Path, pipeline_config: str, crtdl: str) -> str:
    """Runs `aether pipeline start` in project_dir and returns the resulting job id."""
    result = subprocess.run(
        ["aether", "pipeline", "start", pipeline_config, crtdl],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    print(result.stderr)
    result.check_returncode()

    match = _JOB_ID_RE.search(result.stdout + result.stderr)
    if not match:
        raise RuntimeError("could not find a 'Job ID: ...' line in aether's output")
    return match.group(1)
