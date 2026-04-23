#!/usr/bin/env bash

ONTOLOGY_VERSION=${ONTOLOGY_VERSION:-4.0.0}
echo "\$0 = $0"
echo "dirname \$0 = $(dirname "$0")"

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit 1 ; pwd -P )"
echo "BASE_DIR = $BASE_DIR"

# Create measure directory if it doesn't exist
MEASURE_DIR="${BASE_DIR}/measure"
echo "MEASURE_DIR = $MEASURE_DIR"
mkdir -vp "${BASE_DIR}/${MEASURE_DIR}"

COMPOSE_PROJECT=${DATA_PORTAL_COMPOSE_PROJECT:-dataportal}
echo "COMPOSE_PROJECT = $COMPOSE_PROJECT"
DOWNLOAD_URL="https://github.com/medizininformatik-initiative/fhir-ontology-generator/releases/download/v${ONTOLOGY_VERSION}/availability.zip"

FDE_REPORT_TYPE=${FDE_REPORT_TYPE:-cdsCodingAvailability}

if [[ $FDE_REPORT_TYPE == "cdsCodingAvailability" ]]; then
    MEASURE_FILE="Measure-CdsCodingAvailability.fhir"
    PROJECT_IDENTIFIER_VALUE=fdpg-data-availability-report
    PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT=fdpg-data-availability-report-obfuscated

elif [[ "$FDE_REPORT_TYPE" == "DseElementAvailability" ]]; then
    MEASURE_FILE="Measure-DseElementAvailability.fhir"
    PROJECT_IDENTIFIER_VALUE="fdpg-data-element-availability-report"
    PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT=fdpg-data-element-availability-report-obfuscated

else
    echo "Unknown FDE_REPORT_TYPE: $FDE_REPORT_TYPE"
    exit 1
fi

# Check if measure file exists
if [ ! -f "${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json" ]; then
    echo -n "Downloading measure resource v${ONTOLOGY_VERSION} ... "
    # Download and extract measure resource
    curl -Ls -o "${BASE_DIR}/availability.zip" "$DOWNLOAD_URL"
    unzip -pj "${BASE_DIR}/availability.zip" "${MEASURE_FILE}.json" > "${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json"
    #rm "${BASE_DIR}/availability.zip"
    mv -v "${BASE_DIR}/availability.zip" "${BASE_DIR}/availability."$(date +%Y-%m-%dT%H.%M.%S)".zip"
    echo "done."
fi

touch .env-temp

export OVERRIDE_ENV=".env-temp"

# ensure cleanup on exit/crash
trap 'rm -f $OVERRIDE_ENV' EXIT

cp .env "$OVERRIDE_ENV"

override_env_var() {
  local key=$1
  local value=$2
  if grep -q "^${key}=" "$OVERRIDE_ENV"; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
      sed -i '' "s|^${key}=.*|${key}=${value}|" "$OVERRIDE_ENV"
    else
      sed -i "s|^${key}=.*|${key}=${value}|" "$OVERRIDE_ENV"
    fi
  else
    echo "${key}=${value}" >> "$OVERRIDE_ENV"
  fi
}

override_env_var "PROJECT_IDENTIFIER_VALUE" "$PROJECT_IDENTIFIER_VALUE"
override_env_var "PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT" "$PROJECT_IDENTIFIER_VALUE_OBFUSCATED_REPORT"


echo "Starting FHIR data evaluator ..."
COMPOSE_IGNORE_ORPHANS=True FDE_INPUT_MEASURE="${MEASURE_DIR}/${MEASURE_FILE}_v${ONTOLOGY_VERSION}.json" docker compose -p "$COMPOSE_PROJECT" -f "$BASE_DIR/docker-compose.yml" up -d

#mv -v "${MEASURE_DIR}/${MEASURE_FILE}" "${MEASURE_DIR}/${MEASURE_FILE}."$(date +%Y-%m-%dT%H.%M.%S)




