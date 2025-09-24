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

    def process_jskos_mappings(self, source, target, log):
        log.append("Converting JSKOS mappings to RDF mapping triples")
        lines = [line for line in open(source)]
        target = open(target, "w")
        count = 0
        try:
            for m in [json.loads(line) for line in lines]:
                prop = next((p for p in m["type"] if p in self.properties), None)
                if not prop:
                    continue
                f = m["from"].get("memberSet", [])
                t = m["to"].get("memberSet", [])
                if type(f) is not list or type(t) is not list or len(f) != 1 or len(t) != 1:
                    continue
                target.write(f"<{f[0]['uri']}> <{prop}> <{t[0]['uri']}> .\n")
                count = count + 1
        except Exception:
            raise ValidationError("Failed to convert JSKOS mappings!")
        log.append(f"Processed {len(lines)} lines into {count} mappings")

    def preprocess_source(self, id, original, fmt, log):
        if fmt == "ndjson":
            result = self.stage / str(id) / "original.ttl"
            self.process_jskos_mappings(original, result, log)
            return result
        else:
            return original

    # TODO: further filter triples from graph, also if mappings provided in RDF

    def save_mappings_stage(self, id, name, data):
        stage = self.stage / str(id)
        stage.mkdir(exist_ok=True)
        # TODO: guess format from first line
        # process_jskos_mappings(self, source, target, log):
        # fmt = ".ttl"
        # file = f"{name}{fmt}"
        # f = open(stage / file, "w")
        # f.write(data)

    def append(self, id, data):
        self.save_mappings_stage(id, "append")
        # TODO: sparql query
        pass

    def detach(self, id, data):
        self.save_mappings_stage(id, "detach")
        # TODO: sparql query
        pass
