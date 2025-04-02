#!/bin/bash
set -euo pipefail
function error() { echo $@ >&2; exit 1; }

usage() {
  echo "Please use one of the following commands (not all implemented yet):"
  echo
  # echo "import-collection ID"
  echo "receive-collection ID"
  echo "load-collection ID"
  echo
  echo "npm run update-terminologies"
  # echo "import-terminology ID"
  echo "receive-terminology ID"
  echo "load-terminology ID"
}


usage

# show configuration

. sparql-env

echo "SPARQL         $SPARQL"
echo "SPARQL_UPDATE  $SPARQL_UPDATE"
echo "SPARQL_STORE   $SPARQL_STORE"
# TODO: check for existence of ./stage

