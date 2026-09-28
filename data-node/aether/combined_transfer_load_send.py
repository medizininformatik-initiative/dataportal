#!/usr/bin/env python3
"""Send CSV and NDJSON files to a transfer FHIR server, like aether's transfer_load.

Each file becomes one zipped FHIR Binary. One DocumentReference links all Binaries.
Only the Python standard library is used.

Example:
  transfer_load_send.py ./out https://dsf.example.org \
      --project-identifier My-DUP --organization-identifier my-org.de \
      --username user --password secret
"""

import argparse
import base64
import io
import json
import ssl
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

EXTENSIONS = (".csv", ".ndjson")


def find_files(folder):
    return sorted(p for p in Path(folder).rglob("*") if p.is_file() and p.name.endswith(EXTENSIONS))


def zip_base64(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=path.name)
    with buf.getbuffer() as view:
        data = base64.b64encode(view)
    buf.close()
    return data


def build_binary(path):
    """Return the Binary id and its JSON body as chunks, so the body is never joined in memory."""
    binary_id = str(uuid.uuid4())
    prefix = (f'{{"resourceType":"Binary","id":"{binary_id}",'
              f'"contentType":"application/zip","data":"').encode("ascii")
    return binary_id, [prefix, zip_base64(path), b'"}']


def build_document_reference(binary_ids, project_id, org_id):
    return {
        "resourceType": "DocumentReference",
        "id": str(uuid.uuid4()),
        "masterIdentifier": {
            "system": "http://medizininformatik-initiative.de/sid/project-identifier",
            "value": project_id,
        },
        "status": "current",
        "docStatus": "final",
        "author": [{
            "type": "Organization",
            "identifier": {"system": "http://dsf.dev/sid/organization-identifier", "value": org_id},
        }],
        "date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "content": [
            {"attachment": {"contentType": "application/zip", "url": f"Binary/{binary_id}"}}
            for binary_id in binary_ids
        ],
    }


def put(base_url, resource_type, resource_id, chunks, headers, ssl_ctx, timeout):
    url = f"{base_url.rstrip('/')}/fhir/{resource_type}/{resource_id}"
    req = urllib.request.Request(url, data=chunks, method="PUT",
                                 headers={"Content-Type": "application/fhir+json",
                                          "Content-Length": str(sum(len(c) for c in chunks)),
                                          **headers})
    try:
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"PUT {url} failed: HTTP {e.code}: {body}")


def auth_headers(args):
    if args.token:
        return {"Authorization": f"Bearer {args.token}"}
    if args.username:
        creds = base64.b64encode(f"{args.username}:{args.password or ''}".encode()).decode()
        return {"Authorization": f"Basic {creds}"}
    return {}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("folder", help="folder with .csv and .ndjson files (searched recursively)")
    p.add_argument("url", help="base URL of the transfer server; resources go to <url>/fhir/<Type>/<id>")
    p.add_argument("--project-identifier", required=True)
    p.add_argument("--organization-identifier", required=True)
    p.add_argument("--username")
    p.add_argument("--password")
    p.add_argument("--token", help="bearer token, used instead of basic auth")
    p.add_argument("--ca-cert", help="CA bundle to verify the server certificate")
    p.add_argument("--timeout", type=float, default=300, help="seconds per request (default: 300)")
    args = p.parse_args()

    files = find_files(args.folder)
    if not files:
        sys.exit(f"no .csv or .ndjson files found in {args.folder}")

    ssl_ctx = ssl.create_default_context(cafile=args.ca_cert)
    headers = auth_headers(args)

    print(f"Sending {len(files)} file(s) to {args.url}")
    binary_ids = []
    for i, path in enumerate(files, 1):
        binary_id, chunks = build_binary(path)
        status = put(args.url, "Binary", binary_id, chunks, headers, ssl_ctx, args.timeout)
        del chunks
        print(f"  {i}/{len(files)} {path.name} -> Binary/{binary_id} (HTTP {status})")
        binary_ids.append(binary_id)

    doc_ref = build_document_reference(binary_ids, args.project_identifier, args.organization_identifier)
    status = put(args.url, "DocumentReference", doc_ref["id"],
                 [json.dumps(doc_ref).encode("utf-8")], headers, ssl_ctx, args.timeout)
    print(f"DocumentReference/{doc_ref['id']} (HTTP {status})")


if __name__ == "__main__":
    main()
