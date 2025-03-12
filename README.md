# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

This component imports arbitrary RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of two steps:

1. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report is generated.
2. **load**: on success the processed data is loaded into the triple store

## Usage

Internal scripts (don't call directly!):

- `load-collection`
- `load-collection-metadata`
- `load-rdf-graph`
- `sparql-update`
- `collection-context.json`

Two Docker volumes (or local directories) are used:

- `./import` a directory read RDF data from
- `./stage` the stage directory with subdirectories
  - `./stage/collection/$ID` for collections with collection id `$ID`
  - `./stage/terminology/$ID` for terminologies with BARTOC id `$ID`

## Configuration

Environment variables:

- `SPARQL`
- `SPARQL_UPDATE` (default: same as `SPARQL`)

## Development

Locally build Docker image for testing:

~~~sh
docker compose create
~~~


