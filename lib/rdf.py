from pathlib import Path
from rdflib import Graph, Namespace
from pyld import jsonld
from .utils import read_json

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
