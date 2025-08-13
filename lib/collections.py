import os
from pathlib import Path
from shutil import rmtree
from jsonschema import validate, ValidationError
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

    def get(self, id):
        try:
            return next(c for c in self.collections() if c["id"] == str(id))
        except StopIteration:
            raise NotFound(f"Collection {id} not found")

    def set(self, id, data):
        # TODO: check data["id"] and data["uri"]
        validate(instance=data, schema=collection_schema)
        # TODO: insert new collection in collections.json
        # ...
        return data

    def set_all(self, data):
        if type(data) is not list:
            raise ValidationError("Expected list of collections")
        # TODO: check "id" and must "uri" match
        validate(instance=data, schema=collection_schema)
        # TODO: remove/create stage directories
        write_json(self.collections_file, data)
        return data

