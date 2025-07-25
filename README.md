# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

[![Docker image](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml/badge.svg)](https://github.com/orgs/nfdi4objects/packages/container/package/n4o-graph-importer)
[![Test](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml)

This component imports RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of two steps:

1. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report is generated.
2. **load**: on success the processed data is loaded into the triple store

See [n4o-graph](https://github.com/nfdi4objects/n4o-graph) for full documentation of system architecture with all components.

## Usage

This component can be used both [as Docker image](https://github.com/nfdi4objects/n4o-graph-importer) (recommended) and from sources (for development and testing). In both cases the importer is executed via individual command line scripts. A REST API is being implemented.

Two Docker volumes (or local directories) are used to store files:

- `./stage` the stage directory with subdirectories
  - `./stage/collection/$ID` for collections with collection id `$ID`
  - `./stage/terminology/$ID` for terminologies with BARTOC id `$ID`
- `./data` a directory read RDF data from (not required if running from sources)

## Configuration

Environment variables:

- `SPARQL`: API endpoint of SPARQL Query protocol. Default: <http://localhost:3030/n4o>.
- `SPARQL_UPDATE`: API endpoint of SPARQL Update protocol. Default: same as `SPARQL`
- `SPARQL_STORE`: API endpoint of SPARQL Graph store protocol. Default: same as `SPARQL`
- `STAGE`: stage directory. Default `stage`

## Collection metadata

Collections are specified in a JSON format described by JSON Schema [collection-schema.json](collection-schema.json).

## Commands

Main entry script `./importer.sh` lists all available commands.

### Import terminologies

The list of terminologies to be loaded is managed in BARTOC. Download URLs for selected terminologies are hard-coded in file [`terminology-data.csv`](terminology-data.csv) (until a better way has been established to manage this information). The following data formats are supported:

- [rdf/turtle](http://format.gbv.de/rdf/turtle) (subsumes N-Triples) (`.ttl` or `.nt`)
- [rdf/xml](http://format.gbv.de/rdf/xml) (`.rdf`)
- [jskos](http://format.gbv.de/jskos) (`.ndjson`)

To update the list of terminologies from BARTOC run:

~~~sh
./update-terminologies
~~~

This generates files `terminologies.json`, `namespaces.json`, and `terminologies.ttl` in directory `stage/terminology/`, required for importing collections and terminologies. This metadata about terminologies is loaded into the triple store with:

~~~sh
./load-terminologies-metadata
~~~

To receive and load individual terminology data (here exemplified with SKOS terminology, <http://bartoc.org/en/node/18274>:

~~~sh
./receive-terminology http://bartoc.org/en/node/18274
./load-terminology http://bartoc.org/en/node/18274
~~~

Or both in one command:

~~~sh
./import-terminology http://bartoc.org/en/node/18274
~~~

Data and reports are stored in `stage/terminology/18274`.

A local terminology file can be imported for testing:

~~~sh
./import-terminology http://bartoc.org/en/node/18274 skos.rdf
~~~

Terminology data is *not checked* before import except basic RDF syntax checks!

### Import collections

Collections are currently managed [in a CSV file](https://github.com/nfdi4objects/n4o-databases/blob/main/n4o-collections.csv) until there is a better solution. To get the current list of collections and transform it to RDF run:

~~~sh
./update-collections
~~~

Optionally pass a local `.json` file or an URL to load list of collections from (see [Collection metadata](#collections-metadata).

This creates `stage/collection/collections.ttl`. To load its content into the Knowledge Graph run:

~~~sh
./load-collections-metadata
~~~

Note this overrides the `issued` date of imported collection data (this may be fixed later).

To receive collection data from where it has been published, do quality analysis and convert it to RDF run:

~~~sh
./receive-collection 0
~~~

*Receiving data has not been fully implemented yet!*

Load collection data and metadata from stage directory into triple store:

~~~sh
./load-collection 0     # change to another collection id except for testing
~~~

## Development

See `test/test.sh` for a test script, also run via GitHub action.

Locally build Docker image for testing:

~~~sh
docker compose create
~~~

## License

Licensed under [Apache License](http://www.apache.org/licenses/) 2.0.
