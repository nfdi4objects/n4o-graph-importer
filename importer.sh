#!/usr/bin/bash
. utils.sh

echo "Please use one of the following commands (not all implemented yet):"
echo
echo " import-metadata                update and load terminology metada with one command"
echo "   update-terminologies         update the list of terminologies from BARTOC"
echo "   load-terminologies-metadata  load metadata about terminologies into the triple store"
echo
echo " import-terminology ID          receive and load a terminology with one command"
echo "  receive-terminology ID        receive terminology data"
echo "  load-terminology ID           load terminology data into the triple store"
echo
echo "  update-collections            get the current list of collections"
echo "  load-collections-metadata     load collections metadata into the triple store"
echo
echo " import-collection ID           receive and load collection data in one command"
echo "  receive-collection ID         receive published collection data and transform it"
echo "  load-collection ID            load collection data and metadata from into the triple store"
echo 
echo "Configuration:"
echo
echo " SPARQL         $SPARQL"
echo " SPARQL_UPDATE  $SPARQL_UPDATE"
echo " SPARQL_STORE   $SPARQL_STORE"
echo " STAGE          $STAGE"
