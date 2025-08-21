from pathlib import Path
from rdflib import Graph, Namespace
from SPARQLWrapper import SPARQLWrapper
from pyld import jsonld
from .utils import read_json
from .errors import ServerError

prefixes = read_json(Path(__file__).parent.parent / 'prefixes.json')


def to_rdf(doc, context):
    if type(doc) is list:
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


def write_ttl(file, doc, context):
    with open(file, "w") as f:
        f.write(to_rdf(doc, context).serialize(format='turtle'))


def sparql_update(api, graph, query):
    print(f"Executing SPARQL Update at {api}")
    sparql = SPARQLWrapper(api, returnFormat='json')
    sparql.method = 'POST'
    sparql.setQuery(query)
    try:
        res = sparql.query()
        if res.response.code != 200:
            raise Exception(f"HTTP Status code {res.response.code}")
    except Exception as e:
        raise ServerError(f"SPARQL UPDATE failed: {e}")


def sparql_insert(api, graph, rdf):
    query = "INSERT DATA { GRAPH <%s> { %s } }" % (graph, rdf)
    sparql_update(api, graph, query)
