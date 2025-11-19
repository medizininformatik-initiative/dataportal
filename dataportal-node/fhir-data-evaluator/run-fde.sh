#!/usr/bin/env bash

ONTOLOGY_VERSION="3.9.2"

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit 1 ; pwd -P )"


COMPOSE_PROJECT=${FEASIBILITY_COMPOSE_PROJECT:-feasibility-deploy}
DOWNLOAD_URL="https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v${ONTOLOGY_VERSION}/availability.zip"
MEASURE_DIR="${BASE_DIR}/measure"
FDE_REPORT_TYPE=${FDE_REPORT_TYPE:-cdsCodingAvailability}


if [[ $FDE_REPORT_TYPE == "cdsCodingAvailability" ]]; then
    MEASURE_FILE="Measure-CdsCodingAvailability.fhir"
    FDE_PROJECT_IDENTIFIER_VALUE=fdpg-data-availability-report
    FDE_PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT=fdpg-data-availability-report-obfuscated
else
    MEASURE_FILE="Measure-DseElementAvailability.fhir"
    FDE_PROJECT_IDENTIFIER_VALUE=fdpg-data-broad-availability-report
    FDE_PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT=fdpg-data-broad-availability-report-obfuscated
fi

# Create measure directory if it doesn't exist
mkdir -p "${BASE_DIR}/${MEASURE_DIR}"

# Check if measure file exists
if [ ! -f "${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json" ]; then
    echo -n "Downloading measure resource v${ONTOLOGY_VERSION} ... "
    # Download and extract measure resource
    curl -Ls -o "${BASE_DIR}/availability.zip" "$DOWNLOAD_URL"
    unzip -pj "${BASE_DIR}/availability.zip" "${MEASURE_FILE}.json" > "${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json"
    rm "${BASE_DIR}/availability.zip"
    echo "done."
fi

echo "Starting FHIR data evaluator ..."
FDE_PROJECT_IDENTIFIER_VALUE=$FDE_PROJECT_IDENTIFIER_VALUE FDE_PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT=$FDE_PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT COMPOSE_IGNORE_ORPHANS=True FDE_INPUT_MEASURE="${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json" docker compose -p "$COMPOSE_PROJECT" -f "$BASE_DIR/docker-compose.yml" up -d






