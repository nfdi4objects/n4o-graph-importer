from pathlib import Path
from .utils import read_json
from .registry import Registry


class MappingRegistry(Registry):
    schema = read_json(Path(__file__).parent.parent / 'mappings-schema.json')
    context = read_json(Path(__file__).parent.parent / 'collection-context.json')
    properties = [
        "http://www.w3.org/2004/02/skos/core#mappingRelation",
        "http://www.w3.org/2004/02/skos/core#closeMatch",
        "http://www.w3.org/2004/02/skos/core#exactMatch",
        "http://www.w3.org/2004/02/skos/core#broadMatch",
        "http://www.w3.org/2004/02/skos/core#narrowMatch",
        "http://www.w3.org/2004/02/skos/core#relatedMatch",
        "http://www.w3.org/2002/07/owl#sameAs",
        "http://www.w3.org/2002/07/owl#equivalentClass",
        "http://www.w3.org/2002/07/owl#equivalentProperty",
        "http://www.w3.org/2000/01/rdf-schema#subClassOf",
        "http://www.w3.org/2000/01/rdf-schema#subPropertyOf"
    ]

    def __init__(self, **config):
        super().__init__("mapping", **config)

    # TODO
    # register, replace, receive
