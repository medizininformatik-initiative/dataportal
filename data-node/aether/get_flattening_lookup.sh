#!/usr/bin/env bash
set -eo pipefail

usage() {
  echo "Usage: $(basename "$0") [VERSION]"
  echo "  VERSION  Release tag, e.g. v4.1.0 (default: v4.1.0)"
  echo "           Can also be set via the FLATTENING_VERSION env var."
  echo ""
  echo "Examples:"
  echo "  $(basename "$0")            # uses default v4.1.0"
  echo "  $(basename "$0") v4.2.0    # specific version"
  echo "  FLATTENING_VERSION=v4.2.0 $(basename "$0")"
}

if [[ "${1-}" == "--help" || "${1-}" == "-h" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  echo "Error: too many arguments ($# given, expected at most 1)." >&2
  usage >&2
  exit 1
fi

VERSION="${1-${FLATTENING_VERSION:-v4.2.0}}"

# Basic sanity check: must look like vX.Y.Z
if [[ ! "$VERSION" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Error: invalid version '${VERSION}' — expected format vX.Y.Z (e.g. v4.1.0)." >&2
  exit 1
fi

URL="https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/${VERSION}/flattening.zip"

echo "Downloading flattening.zip (${VERSION})..."
if ! curl -fL --progress-bar -o flattening.zip "$URL"; then
  echo "Error: download failed. Check that version '${VERSION}' exists." >&2
  rm -f flattening.zip
  exit 1
fi

echo "Unpacking..."
if ! unzip -q flattening.zip; then
  echo "Error: failed to unpack flattening.zip." >&2
  rm -f flattening.zip
  exit 1
fi

rm flattening.zip
echo "Done."