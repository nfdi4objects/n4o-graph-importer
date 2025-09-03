# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

[![Docker image](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml/badge.svg)](https://github.com/orgs/nfdi4objects/packages/container/package/n4o-graph-importer)
[![Test](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml)

This component imports RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of two steps:

1. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report is generated.
2. **load**: on success the processed data is loaded into the triple store

See [n4o-graph](https://github.com/nfdi4objects/n4o-graph) for full documentation of system architecture with all components.

## Table of Contents

- [Usage](#usage)
- [API](#api)
  - [Terminologies](#terminologies)
    - [GET /terminology](#get-terminology)
    - [GET /terminology/:id](#get-terminologyid)
    - [PUT /terminology/:id](#put-terminologyid)
    - [DELETE /terminology/:id](#delete-terminologyid)
    - [PUT /terminology/](#put-terminology)
    - [POST /terminology/:id/receive](#post-terminologyidreceive)
    - [GET /terminology/:id/receive](#get-terminologyidreceive)
    - [POST /terminology/:id/load](#post-terminologyidload)
    - [GET /terminology/:id/load](#get-terminologyidload)
    - [GET /terminology/namespaces.json](#get-terminologynamespacesjson)
  - [Collections](#collections)
    - [GET /collection/](#get-collection)
    - [GET /collection/schema.json](#get-collectionschemajson)
    - [PUT /collection/](#put-collection)
    - [POST /collection/](#post-collection)
    - [GET /collection/:id](#get-collectionid)
    - [PUT /collection/:id](#put-collectionid)
    - [DELETE /collection/:id](#delete-collectionid)
    - [POST /collection/:id/receive](#post-collectionidreceive)
    - [GET /collection/:id/receive](#get-collectionidreceive)
    - [POST /collection/:id/load](#post-collectionidload)
    - [GET /collection/:id/load](#get-collectionidload)
    - [POST /collection/:id/remove](#post-collectionidremove)
- [Configuration](#configuration)
- [Development](#development)
- [License](#license)

## Usage

This component can be used both [as Docker image](https://github.com/nfdi4objects/n4o-graph-importer) (recommended) and from sources (for development and testing). In both cases the importer is executed via individual command line scripts. A REST API is being implemented.

Two Docker volumes (or local directories) are used to store files:

- `./stage` the stage directory with subdirectories
  - `./stage/collection/$ID` for collections with collection id `$ID`
  - `./stage/terminology/$ID` for terminologies with BARTOC id `$ID`
- `./data` a directory read RDF data from (not required if running from sources)

Import is three steps:

1. register
2. receive
3. load

## API

### Terminologies

Terminologies are identified by their BARTOC identifier. Terminology data should be imported before collection data, to detect use of terminologies in collections. 

#### GET /terminology

Return the list of registered terminologies.

#### GET /terminology/:id

Return metadata of a registered terminology.

#### PUT /terminology/:id

Register a terminology or update its metadata from BARTOC. The metadata is directly added to the triple store. Updates may lead to errors in description of terminologies because removal of statements is limited to simple triples with terminology URI as subject!

#### DELETE /terminology/:id

Unregister a terminology and remove it from stage area and triple store.

#### PUT /terminology/

Register a list of terminologies. This is only allowed as long as the current list is empty. The response body is expected to be a JSON array with objects having key `uri` with the BARTOC URI like this:

~~~json
[
 { "uri": "http://bartoc.org/en/node/18274" },
 { "uri": "http://bartoc.org/en/node/20533" }
]
~~~

Other fields are ignored so the return value of [GET /terminology/](#get-terminology) can be used as payload.

#### POST /terminology/:id/receive

Receive terminology data. Arguments passed as query parameters:

- `from` with an URL or with the name of a file in data directory. Format must be RDF/Turtle for file extension `.ttl` or `.nt`, otherwise RDF/XML.

#### GET /terminology/:id/receive

Get latest receive log of a terminology. *Not implemented yet!*

#### POST /terminology/:id/load

Load received terminology data into the triple store.

#### GET /terminology/:id/load

Get latest load log of a terminology. *Not implemented yet!*

#### GET /terminology/namespaces.json

Return registered URI namespaces forbidden to be used in RDF subjects. The result is a JSON object with terminology URIs as keys and namespaces as values. For instance the SKOS (<http://bartoc.org/en/node/18274>) namespace is <http://www.w3.org/2004/02/skos/core#> so RDF triples with subjects in this namespace can only be added to the knowledge graph via `/terminology/18274`.

### Collections

Collections are described in a custom JSON format described by JSON Schema [collection-schema.json](collection-schema.json). This JSON data is internally converted to RDF for import into the knowledge graph.

#### GET /collection/

Return the list of registered collections (metadata only).

#### GET /collection/schema.json

Return the JSON Schema used to validation collection metadata. See file [collection-schema.json](collection-schema.json).

#### PUT /collection/

Initially register a list of collections. Only allowed if the current list is empty. Collections metadata must conform to the Collection JSON Schema.

*The metadata is not imported into the triple store!*

#### POST /collection/

Register a new collection or update metadata of a registered collection. Collection metadata must conform to the Collection JSON Schema.

*The metadata is not imported into the triple store!*

#### GET /collection/:id

Return metadata of a specific registered collection.

#### PUT /collection/:id

Update metadata of a specific registered collection or register a new collection.

*The metadata is not imported into the triple store!*

#### DELETE /collection/:id 

Unregister a collection and remove it from the triple store and staging area. This implies [DELETE /collection/:id/remove](#delete-collectionidremove).

#### POST /collection/:id/receive

Receive and process collection data. Optional query parameters:

- from (URL or local file in data directory)
- format

#### GET /collection/:id/receive

Get latest receive log of a collection. *Not implemented yet!*

#### POST /collection/:id/load

Load received and processed collection data into the triple store.

#### GET /collection/:id/load

Get latest load log of a collection. *Not implemented yet!*

#### POST /collection/:id/remove

Remove collection data from the triple store and from staging area. The collection will still be registered and collection metadata is not removed from the triple store.

## Configuration

Environment variables:

- `TITLE`: title of the application. Default `N4O Graph Importer`
- `SPARQL`: API endpoint of SPARQL Query protocol, SPARQL Update protocol and SPARQL Graph store protocol. Default: <http://localhost:3030/n4o>.
- `STAGE`: stage directory. Default `stage`
- `BASE`: base URI of collections. Default: `https://graph.nfdi4objects.net/collection/`
- `DATA`: local data directory for file import

## Commands

**This will be removed in favour or the API**

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

This generates files `terminologies.json`, `namespaces.json`, and `terminologies.ttl` in directory `stage/terminology/`, required for importing collections and terminologies.

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

Requires basic development toolchain (`sudo apt install build-essential`) and Python 3 with module venv to be installed.

- `make deps` installs Python dependencies in a virtual environment in directory `.venv`
- `make test` runs a test instance of the service with a temporary triple store
- `make start` runs the service without restarting
- `make api` runs the service with automatic restarting (requires install Node module `nodemon` with `npm install`)

Best use the Docker image [n4o-fuseki](https://github.com/nfdi4objects/n4o-fuseki#readme) to start a triple store configured to be used with the importer:

~~~sh
docker run -rm -p 3030:3030 ghcr.io/nfdi4objects/n4o-fuseki:main
~~~

Locally build Docker image for testing:

~~~sh
docker compose create
~~~

## License

Licensed under [Apache License](http://www.apache.org/licenses/) 2.0.
