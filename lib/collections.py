import os
from pathlib import Path
from shutil import rmtree
from jsonschema import validate, ValidationError
from SPARQLWrapper import SPARQLWrapper
from .utils import read_json, write_json

class NotFound(Exception):
    pass


collection_schema = read_json(Path(__file__).parent.parent / 'collection-schema.json')

class CollectionRegistry:
    def __init__(self, stage):
        self.stage = stage = Path(stage)
        if not stage.is_dir():
            raise NotFound(f"Missing stage directory {stage}")
        (stage / "collection").mkdir(exist_ok=True)

        self.collections_file = stage / "collection" / "collections.json"
        if not self.collections_file.exists():
            write_json(self.collections_file, [])

    def collections(self):
        return read_json(self.collections_file)

    def update_collections(self, cols):

        #COLLECTIONS_TTL = stage() / 'collection' / 'collections.ttl'

        #npm_cmd = '/usr/bin/npm run --silent -- '
        #def run_s(cmd): return subprocess.run(
        #    f'{npm_cmd}{cmd} ', shell=True, capture_output=True, text=True)
        #run_s(
        #    f'jsonld2rdf -c collection-context.json {COLLECTIONS_JSON} > {COLLECTIONS_TTL}')
        # TODO: JSON => RDF
        write_json(self.collections_file, cols)

    def get(self, id):
        try:
            return next(c for c in self.collections() if c["id"] == str(id))
        except StopIteration:
            raise NotFound(f"Collection {id} not found")

    def set(self, id, col):
        if type(col) is not dict:
            raise ValidationError("Expected JSON object")
        # TODO: check/add data["id"] and data["uri"]
        validate(instance=col, schema=collection_schema)
        cols = self.collections()
        cols.append(col)
        # TODO: create stage directory
        self.update_collections(cols)
        return col

    def delete(self, id):
        col = self.get(id)
        cols = [c for c in self.collections() if c["id"] != str(id)]
        # TODO: remove stage directory
        self.update_collections(cols)
        return col

    def set_all(self, cols):
        if type(cols) is not list:
            raise ValidationError("Expected list of collections")
        # TODO: check "id" and must "uri" match
        validate(instance=cols, schema=collection_schema)
        # TODO: remove/create stage directories
        self.update_collections(cols)
        return cols

