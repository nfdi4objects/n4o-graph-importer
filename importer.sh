#!/usr/bin/bash
. utils.sh

echo "Please use one of the following commands (not all implemented yet):"
echo
# echo "import-collection ID"
echo "  receive-collection ID"
echo "  load-collection ID"
echo
echo "  update-terminologies"
echo "  load-terminologies-metadata"
echo
echo " import-terminology ID"
echo "  receive-terminology ID"
echo "  load-terminology ID"

# show configuration

echo
echo "SPARQL         $SPARQL"
echo "SPARQL_UPDATE  $SPARQL_UPDATE"
echo "SPARQL_STORE   $SPARQL_STORE"

# TODO: check for existence of ./stage
