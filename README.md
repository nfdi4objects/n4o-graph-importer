# n4o-graph-importer

> Import RDF data into the NFDI4Objects Knowledge Graph

[![Docker image](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/docker.yml)
[![Test](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml/badge.svg)](https://github.com/nfdi4objects/n4o-graph-importer/actions/workflows/test.yml)

This component imports RDF data of a collection or a terminology into the triple store of NFDI4Objects Knowledge Graph. The import consists of two steps:

1. **receive**: data is copied into a **stage** directory where it is validated, filtered, and a report is generated.
2. **load**: on success the processed data is loaded into the triple store

```mermaid
graph TD
    collections(collections)
    data(published data)    
    apps(applications)

    data --> receive
    collections --> receive

    subgraph n4o-graph-import
        receive[**receive**]
        receive --> stage
        stage --> import
        import[**import**]
    end
    subgraph n4o-fuseki
        kg(triple store)
    end
    subgraph n4o-graph-apis
        ui[**web application**]
    end
    stage --> ui
    kg -- SPARQL --> ui
    ui -- SPARQL --> apps

    import -- SPARQL update & graph store --> kg
```

## Usage

This component can be used both as Docker image (recommended) and from sources (for development and testing).

Two Docker volumes (or local directories) are used:

- `./stage` the stage directory with subdirectories
  - `./stage/collection/$ID` for collections with collection id `$ID`
  - `./stage/terminology/$ID` for terminologies with BARTOC id `$ID`
- `./import` a directory read RDF data from (not required if running from sources)

### Receive

*...not fully implemented yet...*

### Load

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

Internal scripts (don't call directly!):

- `load-collection`
- `load-collection-metadata`
- `load-rdf-graph`
- `sparql-update`
- `collection-context.json`


