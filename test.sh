#!/usr/bin/bash
set -euo pipefail

# mock receive

mkdir -p stage/collection/0
cp test/collection.json stage/collection/0

rapper -q -i turtle test/data.ttl > stage/collection/0/filtered.nt
