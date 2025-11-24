from pathlib import Path
from .registry import Registry
from .utils import read_json


class CollectionRegistry(Registry):
    schema = read_json(Path(__file__).parent / 'collection-schema.json')
    context = read_json(Path(__file__).parent / 'collection-context.json')

    def __init__(self, **config):
        super().__init__("collection", **config)
        self.terminologies = config.get("terminologies", None)

    def forbidden_namespaces(self, id):
        return self.terminologies.namespaces() if self.terminologies else {}
