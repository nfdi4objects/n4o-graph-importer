from pathlib import Path
from jsonschema import validate
from .registry import Registry
from .utils import read_json
from .errors import NotFound, NotAllowed, ValidationError, ClientError
from .rdf import rdf_receive


class CollectionRegistry(Registry):
    schema = read_json(Path(__file__).parent.parent / 'collection-schema.json')
    context = read_json(Path(__file__).parent.parent /
                        'collection-context.json')

    def __init__(self, **config):
        super().__init__("collection", **config)

    def collection_metadata(self, col, id=None):
        if "id" in col and "uri" in col:
            if col["uri"] != self.graph + col["id"]:
                raise ValidationError("uri and id do not match!")
        elif "uri" in col:
            col["id"] = col["uri"].split("/")[-1]
        else:
            if "id" not in col:
                if id:
                    col["id"] = str(id)
                else:
                    cols = self.list()
                    col["id"] = str(max(int(c["id"])
                                    for c in cols) + 1 if cols else 1)
            col["uri"] = self.graph + col["id"]

        if id and col["id"] != str(id):
            raise ValidationError("id does not match!")
        col["partOf"] = [self.graph]
        if self.schema:
            validate(instance=col, schema=self.schema)
        return col

    def register(self, col, id=None):
        if type(col) is not dict:
            raise ValidationError("Expected JSON object")

        col = self.collection_metadata(col, id)

        return self._register(col)

    def replace(self, cols):
        if type(cols) is not list:
            raise ValidationError("Expected list of collections")
        if len(self.list()):
            raise NotAllowed("List of collections is not empty")
        for c in cols:
            self.register(c)
        return self.list()

    def receive(self, id, file=None, namespaces={}):
        source, fmt = self.access_location(id, file)

        original, log = self.receive_source(id, source, fmt)

        stage = self.stage / str(id)
        rdf_receive(original, stage, log, namespaces)

        return log.done()
