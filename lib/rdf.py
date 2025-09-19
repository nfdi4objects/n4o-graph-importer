from rdflib import Graph, URIRef, Literal, BNode
from SPARQLWrapper import SPARQLWrapper
import requests
from pyld import jsonld
from .errors import ServerError


def jsonld2nt(doc, context):
    if type(doc) is list:
        for e in doc:
            e.pop("@context", None)
        doc = {"@context": context, "@graph": doc}
    else:
        doc["@context"] = context
    expanded = jsonld.expand(doc)
    return jsonld.to_rdf(expanded, options={'format': 'application/n-quads'})


# for pretty-printing
# Namespace prefixes for pretty RDF/Turtle
# prefixes = read_json(Path(__file__).parent.parent / 'prefixes.json')
#
# def to_rdf(doc, context):
#    nquads = jsonld2nt(doc, context)
#   g = Graph(bind_namespaces="none")
#    for prefix, uri in prefixes.items():
#        g.bind(prefix, Namespace(uri))
#    g.parse(data=nquads, format='nquads')
#   return g


class TripleStore:
    def __init__(self, api):
        self.api = api

    def query(self, query):
        wrapper = SPARQLWrapper(self.api, returnFormat='json')
        wrapper.setQuery(query)
        try:
            return wrapper.queryAndConvert()["results"]["bindings"]
        except Exception as e:
            raise ServerError(f"SPARQL Query failed: {e}")

    def query_ttl(self, query):
        data = self.query(query)
        rows = [dict([(key, sparql_to_rdf(val).n3())
                     for key, val in row.items()]) for row in data]
        return "\n".join([f"{row['s']} {row['p']} {row['o']} ." for row in rows])

    def update(self, query):
        sparql = SPARQLWrapper(self.api, returnFormat='json')
        sparql.method = 'POST'
        sparql.setQuery(query)
        try:
            res = sparql.query()
            if res.response.code != 200:
                raise ServerError(f"HTTP Status code {res.response.code}")
        except Exception as e:
            raise ServerError(f"SPARQL UPDATE failed: {e}")

    def insert(self, graph, triples):
        query = "INSERT DATA { GRAPH <%s> { %s } }" % (graph, triples)
        return self.update(query)

    def store_file(self, graph, file):
        headers = {"content-type": "text/turtle"}
        res = requests.put(f"{self.api}?graph={graph}",
                           data=open(file, 'rb'), headers=headers)
        return res.status_code == 200
        # TODO: detect error?


def sparql_to_rdf(binding):
    if binding['type'] == 'uri':
        return URIRef(binding['value'])
    elif binding['type'] == 'bnode':
        return BNode(binding['value'])
    elif binding['type'] == 'literal':
        if 'datatype' in binding:
            return Literal(binding['value'], datatype=URIRef(binding['datatype']))
        elif 'xml:lang' in binding:
            return Literal(binding['value'], lang=binding['xml:lang'])
        else:
            return Literal(binding['value'])


def rdf_receive(source, path, log, namespaces={}, properties=[]):
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
