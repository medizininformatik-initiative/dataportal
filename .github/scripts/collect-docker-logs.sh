#!/bin/bash

# Writes the state and the logs of all containers to the directory given as first
# argument, for upload as a CI artifact after a failed run.

OUT_DIR="${1:-docker-logs}"
mkdir -p "$OUT_DIR"

docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' > "$OUT_DIR/containers.txt"
for container in $(docker ps -a --format '{{.Names}}'); do
  docker logs "$container" > "$OUT_DIR/$container.log" 2>&1
done
echo "Wrote logs of $(docker ps -a -q | wc -l | tr -d ' ') containers to $OUT_DIR"
