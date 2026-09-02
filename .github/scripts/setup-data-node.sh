#!/bin/bash -e

# Brings up a data node with its base/default service configuration, wired for a CI
# runner (localhost domains + self-signed cert instead of a real reverse-proxy setup).
# Used as shared setup for e2e test jobs - it does not enable/disable individual
# services, tests are expected to wait for whatever services they specifically need.

BASE_DIR="$( cd -- "$(dirname "$0")/../.." >/dev/null 2>&1 || exit 1 ; pwd -P )"
DATA_NODE_DIR="$BASE_DIR/data-node"

"$DATA_NODE_DIR/initialise-node-env-files.sh"

sed -i -r -e 's#^(OPENID_PROVIDER_URL)=.*$#\1="https://auth.localhost:444/realms/blaze"#' \
          -e 's#^(KC_HOSTNAME)=.*$#\1="https://auth.localhost:444/"#' \
          -e 's#^(KC_HTTP_RELATIVE_PATH)=.*$#\1=/#' \
    "$DATA_NODE_DIR/fhir-server/.env"
sed -i -r -e 's#^(FHIR_SERVER_HOSTNAME)=.*$#\1="fhir.localhost"#' \
          -e 's#^(FLARE_HOSTNAME)=.*$#\1="flare.localhost"#' \
          -e 's#^(KEYCLOAK_HOSTNAME)=.*$#\1="auth.localhost"#' \
          -e 's#^(DATA_NODE_REV_PROXY_NGINX_CONFIG)=.*$#\1="./subdomains.nginx.conf"#' \
    "$DATA_NODE_DIR/rev-proxy/.env"

CERT_DOMAINS="localhost, fhir.localhost, auth.localhost, flare.localhost, torch.localhost, terminology.localhost, dimp.localhost, flattener.localhost, validator.localhost" \
  "$DATA_NODE_DIR/generate-cert.sh"

# fhir-flattener needs a flatteningLookup.json - not checked into git, has to be fetched
(cd "$DATA_NODE_DIR/aether" && ./get_flattening_lookup.sh)

"$DATA_NODE_DIR/start-node.sh"
