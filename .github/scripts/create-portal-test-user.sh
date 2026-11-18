#!/bin/bash -e

# Creates the data portal test user in the portal Keycloak with all dataportal roles.
# The realm import (data-portal/keycloak/init/dataportal-realm.json) contains no users.
# Running it again resets the password and roles of an existing user.

BASE_DIR="$( cd -- "$(dirname "$0")/../.." >/dev/null 2>&1 || exit 1 ; pwd -P )"
KEYCLOAK_DIR="$BASE_DIR/data-portal/keycloak"
COMPOSE_PROJECT="${DATA_PORTAL_COMPOSE_PROJECT:-dataportal}"
REALM="dataportal"
TEST_USER="${PORTAL_TEST_USER:-testuser}"
TEST_PASSWORD="${PORTAL_TEST_PASSWORD:-testpassword}"
ROLES=(DataportalUser DataportalPowerUser DataportalAdmin)

env_value() {
  grep -E "^$1=" "$KEYCLOAK_DIR/.env" | head -1 | cut -d= -f2- | tr -d '"'
}
ADMIN_USER="$(env_value KC_BOOTSTRAP_ADMIN_USERNAME)"
ADMIN_PASSWORD="$(env_value KC_BOOTSTRAP_ADMIN_PASSWORD)"

kcadm() {
  docker compose -p "$COMPOSE_PROJECT" -f "$KEYCLOAK_DIR/docker-compose.yml" exec -T auth \
    /opt/keycloak/bin/kcadm.sh "$@" --config /tmp/kcadm.config
}

kcadm config credentials --server http://localhost:8080/auth --realm master \
  --user "$ADMIN_USER" --password "$ADMIN_PASSWORD"

if [ -z "$(kcadm get users -r "$REALM" -q exact=true -q "username=$TEST_USER" --fields id --format csv --noquotes)" ]; then
  # First name, last name and a verified email avoid the "update account" step at first login.
  kcadm create users -r "$REALM" -s "username=$TEST_USER" -s enabled=true \
    -s firstName=Test -s lastName=User -s "email=$TEST_USER@example.com" -s emailVerified=true
  echo "Created user $TEST_USER"
fi

kcadm set-password -r "$REALM" --username "$TEST_USER" --new-password "$TEST_PASSWORD"
for role in "${ROLES[@]}"; do
  kcadm add-roles -r "$REALM" --uusername "$TEST_USER" --rolename "$role"
done
echo "User $TEST_USER has roles: ${ROLES[*]}"
