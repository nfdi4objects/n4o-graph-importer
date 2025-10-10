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

    def skosmos(self):
        ttl = ""
        for voc in self.list():
            file = self.stage / voc["id"] / "skosmos.ttl"
            if file.is_file():
                ttl = ttl + file.read_text()

        return ttl

    def register(self, item):
        id = str(int(item.get("id")))
        uri = f"{self.prefix}{id}"

        bartoc = Path(self.data) / 'bartoc.json'
        if bartoc.is_file():
            voc = [v for v in read_json(bartoc) if v["uri"] == uri]
        else:
            voc = requests.get(f"https://bartoc.org/api/data?uri={uri}").json()

        if not len(voc):
            raise NotFound(f"Terminology not found: {uri}")

        return super().register(voc[0], id)

    def update_distribution(self, id, log, published=True):
        super().update_distribution(id, log, published)

        stage = self.stage / str(id)
        if not stage.is_dir():
            return

        skosmos = stage / "skosmos.ttl"
        voc = self.get(id)
        query = f"SELECT * {{ GRAPH <{voc['uri']}> {{ ?voc a <http://www.w3.org/2004/02/skos/core#ConceptScheme> }} }} LIMIT 1"
        if not (voc.get("languages", []) and self.sparql.query(query)):
            if skosmos.is_file():
                skosmos.unlink()
            return

        voc["a"] = ["skosmos:Vocabulary", "void:Dataset"]
        voc["id"] = f"{self.graph}{id}/stage/skosmos.ttl#{id}"
        with open(skosmos, "w") as f:
            ttl = jsonld2nt(voc, self.skosmos_context)
            ttl = "\n".join(sorted(ttl.rstrip().split("\n")))
            f.write(ttl)

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
