#!/usr/bin/bash
# This script must be run from root directory of repository.
set -euo pipefail

SPARQL_PORT=3033
export SPARQL=http://localhost:$SPARQL_PORT/n4o

echo "### Start temporary triple store"
SPARQL_CONTAINER=$(docker run -d --rm -p $SPARQL_PORT:3030 ghcr.io/nfdi4objects/n4o-fuseki:main)
cleanup() {
    echo "### Stop temporary triple store"
    docker stop $SPARQL_CONTAINER
    exit ${1:-0}
}
trap 'cleanup 1' ERR

count=5
until ./tests/sparql-update "INSERT DATA {}" || (( count-- == 0 )); do
  echo "Waiting for SPARQL endpoint $SPARQL ..."
  sleep 1
done

coverage run -m pytest -v -s

cleanup
