#!/usr/bin/env sh

COMPOSE_PROJECT=${DATA_PORTAL_COMPOSE_PROJECT:-dataportal}

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit 1 ; pwd -P )"

docker compose -p "$COMPOSE_PROJECT" -f "$BASE_DIR"/flare/docker-compose.yml \
                                     -f "$BASE_DIR"/torch/docker-compose.yml \
                                     -f "$BASE_DIR"/fhir-flattener/docker-compose.yml \
                                     -f "$BASE_DIR"/fhir-pseudonymizer/docker-compose.yml \
                                     -f "$BASE_DIR"/fhir-pseudonymizer/docker-compose.vfps.yml \
                                     -f "$BASE_DIR"/fhir-validator/docker-compose.yml \
                                     -f "$BASE_DIR"/terminology-server/docker-compose.yml \
                                     -f "$BASE_DIR"/fhir-server/docker-compose.yml \
                                     -f "$BASE_DIR"/fhir-server/keycloak.docker-compose.yml \
                                     -f "$BASE_DIR"/rev-proxy/docker-compose.yml stop
