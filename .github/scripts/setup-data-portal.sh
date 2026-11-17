#!/bin/bash -e

# Brings up the data portal in its default context path setup (https://localhost) next to
# a data node started with setup-data-node.sh. Both use the compose project
# $DATA_PORTAL_COMPOSE_PROJECT, so they share one Docker network and the backend reaches
# the node services by name.
#
# The backend runs feasibility queries with the direct broker over CQL against the node's
# FHIR server. It authenticates at the node Keycloak (https://auth.localhost:444), so it
# has to trust the node certificate.

BASE_DIR="$( cd -- "$(dirname "$0")/../.." >/dev/null 2>&1 || exit 1 ; pwd -P )"
DATA_PORTAL_DIR="$BASE_DIR/data-portal"
DATA_NODE_DIR="$BASE_DIR/data-node"
PORTAL_URL="${PORTAL_URL:-https://localhost}"

# Sets KEY to VALUE in an env file. Portable across GNU and BSD sed.
set_env_var() {
  local file="$1" key="$2" value="$3"
  if ! grep -qE "^${key}=" "$file"; then
    echo "Error: $key not found in $file" >&2
    exit 1
  fi
  sed -i.bak -E "s|^${key}=.*|${key}=\"${value}\"|" "$file" && rm "$file.bak"
}

# Waits until URL returns HTTP 200, trusting the portal CA. Fails after TIMEOUT seconds.
wait_for_url() {
  local url="$1" timeout="$2" start status
  start="$(date +%s)"
  echo "Waiting for $url (max ${timeout}s)"
  while true; do
    status="$(curl -s -o /dev/null -w '%{http_code}' --cacert "$DATA_PORTAL_DIR/auth/ca-cert.pem" "$url" || true)"
    [ "$status" = "200" ] && { echo "  ready after $(( $(date +%s) - start ))s"; return 0; }
    if [ $(( $(date +%s) - start )) -ge "$timeout" ]; then
      echo "Error: $url not ready after ${timeout}s (last HTTP status: $status)" >&2
      return 1
    fi
    sleep 5
  done
}

"$DATA_PORTAL_DIR/initialise-portal-env-files.sh"

if [ ! -f "$DATA_PORTAL_DIR/auth/ca-cert.pem" ] || [ ! -f "$DATA_PORTAL_DIR/auth/cert.pem" ]; then
  "$DATA_PORTAL_DIR/setup-base-auth.sh"
fi

if [ ! -f "$DATA_NODE_DIR/auth/cert.pem" ]; then
  echo "Error: data node certificate missing - run setup-data-node.sh first" >&2
  exit 1
fi
# The backend imports every *.pem in data-portal/auth into its trust store.
cp "$DATA_NODE_DIR/auth/cert.pem" "$DATA_PORTAL_DIR/auth/data-node-cert.pem"

BACKEND_ENV="$DATA_PORTAL_DIR/backend/.env"
set_env_var "$BACKEND_ENV" BROKER_CLIENT_MOCK_ENABLED false
set_env_var "$BACKEND_ENV" BROKER_CLIENT_DIRECT_ENABLED true
set_env_var "$BACKEND_ENV" BROKER_CLIENT_DIRECT_USE_CQL true
set_env_var "$BACKEND_ENV" CQL_SERVER_BASE_URL "http://fhir-server:8080/fhir"
# The golden counts on the MII test data are small, so no result thresholds.
set_env_var "$BACKEND_ENV" PRIVACY_THRESHOLD_RESULTS 0
set_env_var "$BACKEND_ENV" PRIVACY_THRESHOLD_SITES_RESULT 0
# The soft quota (default 3 queries per minute) also applies to power users and the
# tests send more queries than that. Rate-limit tests use their own setting.
set_env_var "$BACKEND_ENV" PRIVACY_QUOTA_SOFT_CREATE_AMOUNT 1000
# The UI polls a result for this long before it shows "Query completed" (default PT1M).
# The direct broker answers within seconds, so a shorter time keeps the UI tests fast.
set_env_var "$BACKEND_ENV" PT_POLLING_TIME_UI PT20S

"$DATA_PORTAL_DIR/start-portal.sh"

wait_for_url "$PORTAL_URL/auth/realms/dataportal/.well-known/openid-configuration" 300
# The backend starts after the Elasticsearch init has loaded the ontology.
wait_for_url "$PORTAL_URL/backend/api/v6/actuator/health" 900
wait_for_url "$PORTAL_URL/" 120
