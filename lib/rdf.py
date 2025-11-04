from rdflib import URIRef, Literal, BNode
from SPARQLWrapper import SPARQLWrapper
import requests
from pyld import jsonld
from .errors import ServerError
from .walk import walk
import lightrdf


def jsonld2nt(doc, context):
    if type(doc) is list:
        for e in doc:
            e.pop("@context", None)
        doc = {"@context": context, "@graph": doc}
    else:
        doc["@context"] = context
    expanded = jsonld.expand(doc)
    return jsonld.to_rdf(expanded, options={'format': 'application/n-quads'})


class TripleStore:
    def __init__(self, api):
        self.api = api
        self.prefixes = {
            "dcat": "http://www.w3.org/ns/dcat#",
            "dct": "http://purl.org/dc/terms/",
            "xsd": "http://www.w3.org/2001/XMLSchema#"
        }

    def client(self, query):
        client = SPARQLWrapper(self.api, returnFormat='json')
        prefixes = "".join([f"PREFIX {p}: <{self.prefixes[p]}>\n" for p in self.prefixes])
        client.setQuery(prefixes + query)
        return client

    def query(self, query):
        client = self.client(query)
        try:
            return client.queryAndConvert()["results"]["bindings"]
        except Exception as e:
            raise ServerError(f"SPARQL Query failed: {e}")

    def query_ttl(self, query):
        data = self.query(query)
        rows = [dict([(key, sparql_to_rdf(val).n3())
                     for key, val in row.items()]) for row in data]
        return "\n".join([f"{row['s']} {row['p']} {row['o']} ." for row in rows])

    def update(self, query):
        client = self.client(query)
        client.method = 'POST'
        try:
            res = client.query()
            if res.response.code != 200:
                raise ServerError(f"HTTP Status code {res.response.code}")
        except Exception as e:
            raise ServerError(f"SPARQL UPDATE failed: {e}")

    def insert(self, graph, triples):
        query = "INSERT DATA { GRAPH <%s> { %s } }" % (graph, triples)
        return self.update(query)

    def delete(self, graph, triples):
        query = "DELETE WHERE { GRAPH <%s> { %s } }" % (graph, triples)
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


def triple_iterator(source, log):
    """Recursively extract RDF triples from a file, directory and/or ZIP archive."""
    rdfparser = lightrdf.Parser()
    for name, path, archive in walk(source):
        format = None
        if name.endswith(".ttl"):
            format = "turtle"
        elif name.endswith(".nt"):
            format = "nt"
        elif name.endswith(".owl"):
            format = "owl"
        elif name.endswith(".rdf"):
            format = "xml"
        elif name.endswith(".xml"):
            format = "xml"
        else:
            continue

        if archive:
            file = archive.open(name)
            base = f"file://{file.name}"
        else:
            file = f"{'/'.join(path)}/{name}"
            base = f"file://{file}"

        #  Check whether XML file is RDF/XML
        if format == "xml":
            f = open(file, "r") if type(file) is str else file
            # FIXME: this requires all XML files to be UTF-8!
            xml = f.read()
            if type(xml) is bytes:
                xml = xml.decode("utf-8")
            if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#' not in xml:
                continue
            f.seek(0)

        try:
            log.append(f"Extracting RDF from {base} as {format}")
            # TODO: pass errors as warnings to logger instead of STDERR
            for triple in rdfparser.parse(file, format=format):
                yield triple
        except Exception as e:
            log.append(f"Error parsing {base}: {e}")
            raise e
