#!/bin/bash -e

# Brings up a data node with its base/default service configuration, wired for a CI
# runner (localhost domains + self-signed cert instead of a real reverse-proxy setup).
# Used as shared setup for e2e test jobs - tests are expected to wait for whatever
# services they specifically need.
#
# DATA_NODE_PROFILE selects the services:
#   full (default) - every data node service
#   core           - FHIR server with its Keycloak, reverse proxy and TORCH only, for the
#                    data portal integration tests. Feasibility runs over CQL against the
#                    FHIR server, so flare is not needed; TORCH also uses CQL by default.

BASE_DIR="$( cd -- "$(dirname "$0")/../.." >/dev/null 2>&1 || exit 1 ; pwd -P )"
DATA_NODE_DIR="$BASE_DIR/data-node"
DATA_NODE_PROFILE="${DATA_NODE_PROFILE:-full}"

# Sets KEY to VALUE in an env file. Portable across GNU and BSD sed.
set_env_var() {
  local file="$1" key="$2" value="$3"
  if ! grep -qE "^${key}=" "$file"; then
    echo "Error: $key not found in $file" >&2
    exit 1
  fi
  sed -i.bak -E "s|^${key}=.*|${key}=\"${value}\"|" "$file" && rm "$file.bak"
}

"$DATA_NODE_DIR/initialise-node-env-files.sh"

case "$DATA_NODE_PROFILE" in
  full) ;;
  core)
    set_env_var "$DATA_NODE_DIR/flare/.env" FLARE_ENABLED false
    set_env_var "$DATA_NODE_DIR/terminology-server/.env" TERMINOLOGY_SERVER_ENABLED false
    set_env_var "$DATA_NODE_DIR/fhir-pseudonymizer/.env" DIMP_ENABLED false
    set_env_var "$DATA_NODE_DIR/fhir-flattener/.env" FLATTENING_ENABLED false
    set_env_var "$DATA_NODE_DIR/fhir-validator/.env" VALIDATION_ENABLED false
    ;;
  *)
    echo "Error: unknown DATA_NODE_PROFILE '$DATA_NODE_PROFILE' (expected full or core)" >&2
    exit 1
    ;;
esac

# rev-proxy/docker-compose.yml reads these through ${VAR:-default} interpolation, and
# compose gives the shell environment precedence over rev-proxy/.env - so exporting them
# is enough and no edit of the generated .env is needed. This does not work for
# fhir-server, whose compose files use env_file:.
export FHIR_SERVER_HOSTNAME="fhir.localhost"
export FLARE_HOSTNAME="flare.localhost"
export KEYCLOAK_HOSTNAME="auth.localhost"
export DATA_NODE_REV_PROXY_NGINX_CONFIG="./subdomains.nginx.conf"

CERT_DOMAINS="localhost, fhir.localhost, auth.localhost, flare.localhost, torch.localhost, terminology.localhost, dimp.localhost, flattener.localhost, validator.localhost" \
  "$DATA_NODE_DIR/generate-cert.sh"

if [ "$DATA_NODE_PROFILE" = "full" ]; then
  # fhir-flattener needs a flatteningLookup.json - not checked into git, has to be fetched
  (cd "$DATA_NODE_DIR/aether" && ./get_flattening_lookup.sh)
fi

"$DATA_NODE_DIR/start-node.sh"
