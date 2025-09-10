from pathlib import Path
from rdflib import Graph, Namespace
from SPARQLWrapper import SPARQLWrapper
import requests
from pyld import jsonld
from .utils import read_json
from .errors import ServerError

# Namespace prefixes for pretty RDF/Turtle
prefixes = read_json(Path(__file__).parent.parent / 'prefixes.json')

# TODO: https://github.com/nfdi4objects/n4o-graph-importer/issues/12
jskos_context = read_json(Path(__file__).parent.parent / 'jskos-context.json')


def to_rdf(doc, context):
    if type(doc) is list:
        for e in doc:
            e.pop("@context", None)
        doc = {"@context": context, "@graph": doc}
    else:
        doc["@context"] = context
    expanded = jsonld.expand(doc)
    nquads = jsonld.to_rdf(expanded, options={'format': 'application/n-quads'})
    g = Graph(bind_namespaces="none")
    for prefix, uri in prefixes.items():
        g.bind(prefix, Namespace(uri))
    g.parse(data=nquads, format='nquads')
    return g


def jskos_to_rdf(doc):
    return to_rdf(doc, jskos_context)


def sparql_query(api, query):
    sparql = SPARQLWrapper(api, returnFormat='json')
    sparql.setQuery(query)
    try:
        return sparql.queryAndConvert()["results"]["bindings"]
    except Exception as e:
        raise ServerError(f"SPARQL Query failed: {e}")


def sparql_update(api, graph, query):
    sparql = SPARQLWrapper(api, returnFormat='json')
    sparql.method = 'POST'
    sparql.setQuery(query)
    try:
        res = sparql.query()
        if res.response.code != 200:
            raise ServerError(f"HTTP Status code {res.response.code}")
    except Exception as e:
        raise ServerError(f"SPARQL UPDATE failed: {e}")


def sparql_insert(api, graph, rdf):
    query = "INSERT DATA { GRAPH <%s> { %s } }" % (graph, rdf)
    sparql_update(api, graph, query)


def load_graph_from_file(api, graph, file, fmt):
    print(f"Storing RDF graph {graph} from {file} at {api}")
    mime = "text/turtle" if fmt == "ttl" else "application/rdf+xml"
    headers = {"content-type": mime}
    res = requests.put(f"{api}?graph={graph}",
                       data=open(file, 'rb'), headers=headers)
    return res.status_code == 200
    # TODO: detect error?


def rdf_receive(source, path, log, namespaces):
    namespaces = tuple(list(namespaces.values()))

    graph = Graph()
    graph.parse(source)
    size = len(graph)
    log.append(f"Parsed {size} unique triples")

    checked = open(path / "checked.nt", "w")
    removed = open(path / "removed.nt", "w")

    count = 0
    for s, p, o in graph.triples((None, None, None)):
        if str(s).startswith(namespaces):
            removed.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")
        else:
            count = count + 1
            # TODO: filter out namespaces
            # if predicate.startswith(rdflib.RDFS)
            checked.write(f"{s.n3()} {p.n3()} {o.n3()} .\n")

    log.append(
        f"Removed {size - count} triples, remaining {count} unique triples.")


"""
checked=$stage/checked.nt
removed=$stage/removed.nt
namespace=$(jq -r --arg uri "$uri" '.[$uri]' $STAGE/terminology/namespaces.json)

export RDFFILTER_ALLOW_NAMESPACE=$namespace
npm run --silent -- rdffilter $unique -o $checked --stats -f ./js/rdffilter.js
# TODO: extend rdffilter for one-pass
npm run --silent -- rdffilter $unique -o $removed -r -f ./js/rdffilter.js
unset RDFFILTER_ALLOW_NAMESPACE

wc -l $duplicated
wc -l $removed
wc -l $checked
"""
