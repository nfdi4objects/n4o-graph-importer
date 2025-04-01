#!/usr/bin/bash
set -euo pipefail
cd $(dirname "$0")/..   # run from repository root directory

SPARQL_PORT=3033
SPARQL=http://localhost:$SPARQL_PORT/n4o
export SPARQL

# start configured triple store (in-memory)
SPARQL_CONTAINER=$(docker run -d --rm -p $SPARQL_PORT:3030 ghcr.io/nfdi4objects/n4o-fuseki:main)
echo "Started triple store at $SPARQL"
echo "If something fails run: docker stop $SPARQL_CONTAINER"

count=5
until ./sparql-update "INSERT DATA {}" || (( count-- == 0 )); do
  echo "Waiting for SPARQL endpoint $SPARQL ..."
  sleep 1
done

# TODO: test loading terminology

# test importing a collection

# TODO: receive data

id=0
stage=stage/collection/0

# mock receive => filtered.nt and collection.nt
mkdir -p $stage 

jq 'select(.id)|.uri="https://graph.nfdi4objects.net/collection/\(.id)"' test/collection.json > $stage/collection.json
npm run --silent -- jsonld2rdf -c collection-context.json $stage/collection.json > $stage/collection.nt
rapper -q -i turtle test/data.ttl > $stage/filtered.nt

# Import collection
./load-collection 0

echo "Stopping container"
docker stop $SPARQL_CONTAINER
exit


