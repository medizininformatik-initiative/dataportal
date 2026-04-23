#!/bin/bash

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit 1 ; pwd -P )"

curl -L https://packages.fhir.org/de.medizininformatikinitiative.kerndatensatz.base/2026.0.0 -o "$BASE_DIR/igs/de.medizininformatikinitiative.kerndatensatz.base-2026.0.0.tgz"
