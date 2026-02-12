#!/bin/bash -e

# Function to display usage
usage() {
  echo "Usage: $0 {install|update}"
  echo "  install  - Run npm clean-install"
  echo "  update   - Run npm update"
  exit 1
}

# Check if command is provided
if [[ $# -eq 0 ]]; then
  usage
fi

# Parse command
case "$1" in
  install)
    echo "Running npm clean-install..."
    npm clean-install
    ;;
  update)
    echo "Running npm update..."
    npm update
    ;;
  *)
    echo "Error: Unknown command '$1'"
    usage
    ;;
esac