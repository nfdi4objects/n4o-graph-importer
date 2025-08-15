import os
from pathlib import Path
from shutil import rmtree
from jsonschema import validate, ValidationError
from SPARQLWrapper import SPARQLWrapper
from pyld import jsonld
from rdflib import Graph, Namespace
from .utils import read_json, write_json

JSON_SCHEMA = read_json(Path(__file__).parent.parent / 'collection-schema.json')
JSONLD_CONTEXT = read_json(Path(__file__).parent.parent / 'collection-context.json')
PREFIXES = read_json(Path(__file__).parent.parent / 'prefixes.json')

def to_rdf(doc):
    if type(doc) == list:
        doc = {"@context": JSONLD_CONTEXT, "@graph": doc}
    else:
        doc["@context"] = JSONLD_CONTEXT
    expanded = jsonld.expand(doc)
    nquads = jsonld.to_rdf(expanded, options={'format': 'application/n-quads'})
    g = Graph(bind_namespaces="core")
    for prefix, uri in PREFIXES.items():
        g.bind(prefix, Namespace(uri))    
    g.parse(data=nquads, format='nquads')
    return g

def write_ttl(file, doc):
    with open(file,"w") as f:
        f.write(to_rdf(doc).serialize(format='turtle', args={}))


class NotFound(Exception):
    pass


class CollectionRegistry:

    def __init__(self, **config):
        self.stage = stage = Path(config.get('stage', 'stage'))
        if not stage.is_dir():
            raise NotFound(f"Missing stage directory {stage}")
        (stage / "collection").mkdir(exist_ok=True)

        self.collections_file = stage / "collection" / "collections.json"
        self.collections_file_ttl = stage / "collection" / "collections.ttl"
        if not self.collections_file.exists():
            self.update_collections([])

    def collections(self):
        return read_json(self.collections_file)

    def update_collections(self, cols):
        write_json(self.collections_file, cols)
        write_ttl(self.collections_file_ttl, cols)


    def get(self, id):
        try:
            return next(c for c in self.collections() if c["id"] == str(id))
        except StopIteration:
            raise NotFound(f"Collection {id} not found")

    def set(self, id, col):
        if type(col) is not dict:
            raise ValidationError("Expected JSON object")
        # TODO: check/add data["id"] and data["uri"]
        validate(instance=col, schema=JSON_SCHEMA)
        cols = self.collections()
        cols.append(col)
        # TODO: create stage directory
        self.update_collections(cols)
        return col

    def delete(self, id):
        col = self.get(id)
        cols = [c for c in self.collections() if c["id"] != str(id)]
        rmtree(self.stage / 'collection' / str(id),  ignore_errors=True)
        self.update_collections(cols)
        return col

    def set_all(self, cols):
        if type(cols) is not list:
            raise ValidationError("Expected list of collections")
        #if len(self.collections()) > 1:
        #    raise 
        # TODO: check "id" and must "uri" match
        validate(instance=cols, schema=JSON_SCHEMA)
        # TODO: remove/create stage directories
        self.update_collections(cols)
        return cols

