#!/bin/sh
# Usage: ./update-aether.sh [version|newest]
#   no argument   install the default version (see compatibility matrix)
#   <version>     install that version, e.g. 1.6.0 or v1.6.0
#   newest        install the latest GitHub release

set -e

DEFAULT_VERSION="1.6.0"
INSTALL_URL="https://raw.githubusercontent.com/medizininformatik-initiative/aether/main/install.sh"

version="${1:-$DEFAULT_VERSION}"

case "$version" in
  newest|latest)
    curl -sSfL "$INSTALL_URL" | sh
    ;;
  *)
    curl -sSfL "$INSTALL_URL" | sh -s -- "${version#v}"
    ;;
esac

sudo mv aether /usr/local/bin/
