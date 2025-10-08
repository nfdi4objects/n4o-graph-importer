from pathlib import Path
import requests
import json
from .utils import read_json
from .errors import NotFound, ValidationError
from .rdf import jsonld2nt
from .registry import Registry

ROOT = Path(__file__).parent.parent


class TerminologyRegistry(Registry):
    context = read_json(ROOT / 'jskos-context.json')
    skosmos_context = read_json(ROOT / 'skosmos-context.json')
    increment = False

    def __init__(self, **config):
        super().__init__("terminology", prefix="http://bartoc.org/en/node/", **config)

    def namespaces(self):
        namespaces = {}
        for voc in self.list():
            if "namespace" in voc:
                namespaces[voc["uri"]] = voc["namespace"]
        return namespaces

    def register(self, item):
        try:
            id = str(int(item.get("id")))
        except Exception:
            raise ValidationError("Missing or malformed BARTOC id")

        uri = f"{self.prefix}{id}"

        bartoc = Path(self.data) / 'bartoc.json'
        if bartoc.is_file():
            voc = [v for v in read_json(bartoc) if v["uri"] == uri]
        else:
            voc = requests.get(f"https://bartoc.org/api/data?uri={uri}").json()

        if not len(voc):
            raise NotFound(f"Terminology not found: {uri}")

        voc = super().register(voc[0], id)

        # Experimental: create Skosmos configuration section
        config = voc.copy()
        config["a"] = ["skosmos:Vocabulary", "void:Dataset"]
        config["id"] = f"{uri}#{id}"
        with open(self.stage / id / "skosmos.ttl", "w") as f:
            ttl = jsonld2nt(config, self.skosmos_context)
            ttl = "\n".join(sorted(ttl.rstrip().split("\n")))
            f.write(ttl)

        return voc

    def preprocess_source(self, id, original, fmt, log):
        if fmt == "ndjson":
            log.append("Converting JSKOS to RDF")
            with open(original) as file:
                jskos = [json.loads(line) for line in file]
            rdf = jsonld2nt(jskos, self.context)
            original = self.stage / str(id) / "original.ttl"
            with open(original, "w") as f:
                f.write(rdf)

        return original

    def forbidden_namespaces(self, id):
        namespaces = dict(self.namespaces())
        namespaces.pop(f"{self.prefix}{id}", None)
        return namespaces
