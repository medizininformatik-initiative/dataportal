"""Runs the availability updater the way data-portal/availability-updater does it: one
compose service, started with `up` so a second run reuses the container.

An override compose file mounts the node certificate (the node Keycloak uses a
self-signed one) without touching the files of the checkout.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile

from helpers import COMPOSE_PROJECT, DATA_NODE_DIR, DATA_PORTAL_DIR

UPDATER_DIR = DATA_PORTAL_DIR / "availability-updater"
SERVICE = "availability-updater"


class Updater:
    def __init__(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="availability-updater-"))
        (self.tmp / "auth").mkdir()
        shutil.copy(DATA_NODE_DIR / "auth" / "cert.pem", self.tmp / "auth" / "cert.pem")
        override = {"services": {SERVICE: {"volumes": [f"{self.tmp / 'auth'}:/opt/availability-updater/auth"]}}}
        (self.tmp / "override.yml").write_text(json.dumps(override))
        self.compose = ["docker", "compose", "-p", COMPOSE_PROJECT, "-f", str(UPDATER_DIR / "docker-compose.yml"),
                        "-f", str(self.tmp / "override.yml")]

    def run(self) -> str:
        """Starts the service, waits for it to exit and returns the log of this run."""
        env = os.environ | {"COMPOSE_IGNORE_ORPHANS": "True"}
        container = f"{COMPOSE_PROJECT}-{SERVICE}-1"
        since = subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"], capture_output=True, text=True).stdout.strip()
        subprocess.run(self.compose + ["up", "-d", SERVICE], cwd=UPDATER_DIR, env=env, check=True, capture_output=True)
        code = subprocess.run(["docker", "wait", container], capture_output=True, text=True, timeout=900).stdout.strip()
        logs = subprocess.run(["docker", "logs", "--since", since, container], capture_output=True, text=True)
        log = logs.stdout + logs.stderr
        assert code == "0", f"availability updater exited with {code}:\n{log[-3000:]}"
        return log

    def remove(self) -> None:
        subprocess.run(self.compose + ["rm", "-f", "-s", SERVICE], cwd=UPDATER_DIR, capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)
