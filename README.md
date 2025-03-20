# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

[![Docker image](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml/badge.svg)](https://github.com/orgs/nfdi4objects/packages/container/package/n4o-graph-importer)
[![Test](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml)

This component imports RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of two steps:

1. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report is generated.
2. **load**: on success the processed data is loaded into the triple store

## Data flow

```mermaid
graph TD
    terminologies(terminologies) --> receive
    collections(collections) --> receive
    data(research data) --> receive

    subgraph n4o-graph-import
        receive[**receive**]
        receive -- validate, transform, report --> stage
        stage --> load
        load[**load**]
    end
    subgraph n4o-fuseki
        kg(triple store)
    end
    subgraph n4o-graph-apis
        ui[**web application**]
    end
    subgraph lido-rdf-converter
        lido2rdf[**lido2rdf**]
        web-app[**web-app**]
    end

    stage --> ui
    kg -- SPARQL --> ui
    ui -- SPARQL --> apps(applications)

    receive <--> lido2rdf
    load -- SPARQL update & graph store --> kg

    web-app <--> ui

    ui <--web browser--> users(users)
```

## Usage

This component can be used both as Docker image (recommended) and from sources (for development and testing). In both cases the importer is executed via individual command line scripts.

Two Docker volumes (or local directories) are used:

- `./stage` the stage directory with subdirectories
  - `./stage/collection/$ID` for collections with collection id `$ID`
  - `./stage/terminology/$ID` for terminologies with BARTOC id `$ID`
- `./data` a directory read RDF data from (not required if running from sources)

Related components:

- [n4o-graph-apis](https://github.com/nfdi4objects/n4o-graph-apis): web interface and public SPARQL endpoint
- [n4o-fuseki](https://github.com/nfdi4objects/n4o-fuseki): RDF triple store
- [lido-rdf-converter](https://github.com/nfdi4objects/lido-rdf-converter): convert LIDO format to RDF

With Docker:

~~~
docker compose -f docker-compose-graph.yml up --force-recreate -V
docker compose run importer
~~~

### Receive

*not fully implemented yet*

### Load

Load collection data and metadata from stage directory into triple store:

~~~sh
load-collection 0     # change to another collection id except for testing
~~~

Load terminology data into triple store:

*not fully implemented yet*

## Configuration

Environment variables:

- `SPARQL`: API endpoint of SPARQL Update protocol. Default: <http://localhost:3030/n4o>.
- `SPARQL_UPDATE`: API endpoint of SPARQL Graph store protocol. Default: same as `SPARQL`

## Development

See `test/test.sh` for a test script, also run via GitHub action.

Locally build Docker image for testing:

~~~sh
docker compose create
~~~

To run with related components there is a docker-compose file currently being developed:

~~~sh
docker compose -f docker-compose-graph.yml up --remove-orphans
docker compose -f docker-compose-graph.yml run importer
~~~

## License

Licensed under [Apache License](http://www.apache.org/licenses/) 2.0.
