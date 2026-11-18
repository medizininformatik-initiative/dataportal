"""A TORCH stand-in whose extraction never finishes, for aether's job control.

It serves the CapabilityStatement of the real TORCH (aether checks it at start), accepts
$extract-data with 202, answers every status poll with 202 and records each request.
"""

from __future__ import annotations

import contextlib
import http.server
import json
import threading
import urllib.request

from torch_client import TORCH_URL

JOB = "s7-stub-job"


class Stub:
    def __init__(self, port: int):
        self.url = f"http://localhost:{port}"
        self.requests: list[tuple[str, str, dict]] = []

    def calls(self, method: str, path_part: str) -> list[dict]:
        return [headers for m, path, headers in self.requests if m == method and path_part in path]


@contextlib.contextmanager
def torch_stub(port: int = 8097):
    with urllib.request.urlopen(f"{TORCH_URL}/fhir/metadata", timeout=30) as response:
        metadata = response.read()
    stub = Stub(port)

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _answer(self, status: int, body: bytes = b"", headers: dict | None = None):
            self.send_response(status)
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _record(self):
            stub.requests.append((self.command, self.path, dict(self.headers)))
            length = int(self.headers.get("Content-Length") or 0)
            if length:
                self.rfile.read(length)

        def do_GET(self):
            self._record()
            if self.path.startswith("/fhir/metadata"):
                self._answer(200, metadata, {"Content-Type": "application/fhir+json"})
            elif self.path.startswith(f"/fhir/__status/{JOB}"):
                self._answer(202, b"", {"X-Progress": "in progress", "Retry-After": "1"})
            else:
                self._answer(404)

        def do_POST(self):
            self._record()
            if self.path.startswith("/fhir/$extract-data"):
                self._answer(202, b"", {"Content-Location": f"{stub.url}/fhir/__status/{JOB}"})
            elif self.path.startswith(f"/fhir/Task/{JOB}/$cancel"):
                self._answer(200, json.dumps({"resourceType": "Task", "id": JOB, "status": "cancelled"}).encode(),
                             {"Content-Type": "application/fhir+json"})
            else:
                self._answer(404)

        def do_DELETE(self):
            self._record()
            self._answer(202)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield stub
    finally:
        server.shutdown()
        server.server_close()
