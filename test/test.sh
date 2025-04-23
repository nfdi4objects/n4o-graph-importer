#!/usr/bin/bash
set -euo pipefail
cd $(dirname "$0")/..   # run from repository root directory

SPARQL_PORT=3033
export SPARQL=http://localhost:$SPARQL_PORT/n4o
export STAGE=test/stage

XXXXXXXX() { echo; echo "### $@"; echo; }

XXXXXXXX "Start temporary triple store"

SPARQL_CONTAINER=$(docker run -d --rm -p $SPARQL_PORT:3030 ghcr.io/nfdi4objects/n4o-fuseki:main)
echo "Started triple store at $SPARQL"
cleanup() {
    XXXXXXXX "Stopping triple store"
    docker stop $SPARQL_CONTAINER
    exit ${1:-0}
}
trap 'cleanup 1' ERR

count=5
until ./sparql-update "INSERT DATA {}" || (( count-- == 0 )); do
  echo "Waiting for SPARQL endpoint $SPARQL ..."
  sleep 1
done

XXXXXXXX "Test updating terminologies and loading terminology metadata"

./update-terminologies  # TODO: avoid external dependency on BARTOC

./load-terminologies-metadata

XXXXXXXX "Test importing terminology"

./import-terminology 18274 test/skos.rdf

XXXXXXXX "Test importing a collection"

# TODO: use proper import script  (needs cleanup)
# ./receive-collection 0

stage=$STAGE/collection/0

# mock receive => filtered.nt and collection.nt
mkdir -p $stage 

jq 'select(.id)|.uri="https://graph.nfdi4objects.net/collection/\(.id)"' test/collection.json > $stage/collection.json
npm run --silent -- jsonld2rdf -c collection-context.json $stage/collection.json > $stage/collection.nt
rapper -q -i turtle test/data.ttl > $stage/filtered.nt

# Import collection
./load-collection 0

cleanup
