#!/bin/bash -e

# The version of docs/compatibility-matrix.md. tests/pipeline/test_aether_cli.py needs
# >= 1.6.0 (aether send, aether job stop).
VERSION="1.6.0"

curl -sLO "https://github.com/medizininformatik-initiative/aether/releases/download/v$VERSION/aether-$VERSION-linux-amd64.tar.gz"
tar xzf "aether-$VERSION-linux-amd64.tar.gz"
rm "aether-$VERSION-linux-amd64.tar.gz"
chmod +x ./aether-linux-amd64
sudo mv ./aether-linux-amd64 /usr/local/bin/aether
