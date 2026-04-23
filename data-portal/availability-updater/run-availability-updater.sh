#! /bin/bash

COMPOSE_PROJECT=${DATA_PORTAL_COMPOSE_PROJECT:-dataportal}

docker compose -p "$COMPOSE_PROJECT" up -d