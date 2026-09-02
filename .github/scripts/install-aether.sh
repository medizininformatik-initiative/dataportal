#!/bin/bash -e

VERSION="1.3.0"

curl -sLO "https://github.com/medizininformatik-initiative/aether/releases/download/v$VERSION/aether-$VERSION-linux-amd64.tar.gz"
tar xzf "aether-$VERSION-linux-amd64.tar.gz"
rm "aether-$VERSION-linux-amd64.tar.gz"
chmod +x ./aether-linux-amd64
sudo mv ./aether-linux-amd64 /usr/local/bin/aether
