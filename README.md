# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

[![Docker image](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml/badge.svg)](https://github.com/orgs/nfdi4objects/packages/container/package/n4o-graph-importer)
[![Test](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml)

This component imports RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of three steps:

1. **register**: metadata is retrieved and written to the triple store
2. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report log is generated
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
    - [POST /terminology/:id/remove](#post-terminologyidremove)
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

Unregister a terminology and remove it from stage area and triple store. This implies [DELETE /terminology/:id/remove](#delete-terminologyidremove).

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

Receive terminology data. The location of the data is going to be extracted from terminology metadata from BARTOC but this has not been implemented yet. For now pass query parameter `from` instead to locate an URL or the name of a file in the data directory. Format must be RDF/Turtle for file extension `.ttl` or `.nt`, otherwise RDF/XML.

#### GET /terminology/:id/receive

Get latest receive log of a terminology.

#### POST /terminology/:id/load

Load received terminology data into the triple store.

#### GET /terminology/:id/load

Get latest load log of a terminology. 

#### POST /terminology/:id/remove

Remove terminology data from the triple store and from staging area. The terminology will still be registered and its metadata is not removed from the triple store.

#### GET /terminology/namespaces.json

Return registered URI namespaces forbidden to be used in RDF subjects. The result is a JSON object with terminology URIs as keys and namespaces as values. For instance the SKOS (<http://bartoc.org/en/node/18274>) namespace is <http://www.w3.org/2004/02/skos/core#> so RDF triples with subjects in this namespace can only be added to the knowledge graph via `/terminology/18274`.

### Collections

Collections are described in a custom JSON format described by JSON Schema [collection-schema.json](collection-schema.json). This JSON data is enriched with field `id` and internally converted to RDF for import into the knowledge graph. In its simplest form, a collection should contain a name, an URL, and a license:

~~~json
{
  "name": "test collection",
  "url": "https://example.org/",
  "license": "https://creativecommons.org/publicdomain/zero/1.0/"
}
~~~

When registered, the collection is assigned an id, and a corresponding URI.

#### GET /collection/

Return the list of registered collections (metadata only).

#### GET /collection/schema.json

Return the JSON Schema used to validation collection metadata. See file [collection-schema.json](collection-schema.json). Collection field `id` is required by the schema but it gets assigned automatically in most cases.

#### PUT /collection/

Register a list of collections. This is only allowed if the current list is empty.

#### POST /collection/

Register a new collection or update metadata of a registered collection.

#### GET /collection/:id

Return metadata of a specific registered collection.

#### PUT /collection/:id

Update metadata of a specific registered collection or register a new collection.

#### DELETE /collection/:id 

Unregister a collection and remove it from the triple store and staging area. This implies [DELETE /collection/:id/remove](#delete-collectionidremove).

#### POST /collection/:id/receive

Receive and process collection data. The location of the data is taken from collection metadata field `access` if existing. The location can be overridden with optional query parameter `from` with an URL or a file name from local data directory.

#### GET /collection/:id/receive

Get latest receive log of a collection.

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
