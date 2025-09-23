from pathlib import Path
import json
from .utils import read_json
from .registry import Registry
from .errors import ValidationError


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
        super().__init__("mappings", **config)

    def process_received(self, id, original, fmt, log):
        if fmt == "ndjson":
            log.append("Converting JSKOS mappings to RDF mapping triples")
            source = open(original)
            original = self.stage / str(id) / "original.ttl"
            target = open(original, "w")
            try:
                for m in [json.loads(line) for line in source]:
                    prop = next((p for p in m["type"] if p in self.properties), None)
                    if not prop:
                        continue
                    f = m["from"].get("memberSet", [])
                    t = m["to"].get("memberSet", [])
                    if type(f) is not list or type(t) is not list or len(f) != 1 or len(t) != 1:
                        continue
                    target.write(f"<{f[0]['uri']}> <{prop}> <{t[0]['uri']}> .\n")
            except Exception as e:
                raise ValidationError("Failed to convert JSKOS mappings!")
            # TODO: log number of triples

        return original

    # TODO: def process_received_rdf to further filter triples from graph
