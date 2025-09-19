from pathlib import Path
from .utils import read_json
from .registry import Registry


class MappingRegistry(Registry):
    schema = read_json(Path(__file__).parent.parent / 'mappings-schema.json')
    context = read_json(Path(__file__).parent.parent / 'collection-context.json')

    def __init__(self, **config):
        super().__init__("mapping", **config)

    # TODO
    # register, replace, receive
