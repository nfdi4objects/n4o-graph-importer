from pathlib import Path
import requests
import re
import json
from .utils import read_json
from .errors import NotFound, ValidationError
from .rdf import jsonld2nt, rdf_receive
from .registry import Registry


class TerminologyRegistry(Registry):
    context = read_json(Path(__file__).parent.parent / 'jskos-context.json')

    def __init__(self, **config):
        super().__init__("terminology", prefix="http://bartoc.org/en/node/", **config)

    def namespaces(self):
        namespaces = {}
        for voc in self.list():
            if "namespace" in voc:
                namespaces[voc["uri"]] = voc["namespace"]
        return namespaces

    def register(self, id, cache=None):
        uri = f"{self.prefix}{int(id)}"

        if cache:
            voc = [v for v in cache if v["uri"] == uri]
        else:
            voc = requests.get(f"https://bartoc.org/api/data?uri={uri}").json()

        if not len(voc):
            raise NotFound(f"Terminology not found: {uri}")

        return self._register(voc[0])

    def replace(self, terms, cache=None):
        add = []
        try:
            r = re.compile("^http://bartoc\\.org/en/node/[1-9][0-9]*$")
            assert type(terms) is list and all(
                (r.match(item["uri"]) for item in terms))
            add = [item["uri"].split("/")[-1] for item in terms]
        except Exception:
            raise ValidationError("Malformed array of terminologies")

        self.purge()
        for id in add:
            self.register(id, cache)

        return self.list()

    def receive(self, id, file=None):
        uri = self.get(id)["uri"]

        file, fmt = self.access_location(id, file)

        original, log = self.receive_source(id, file, fmt)

        stage = self.stage / str(id)

        # convert JSKOS to RDF
        if fmt == "ndjson":
            log.append("Converting JSKOS to RDF")
            with open(original) as file:
                jskos = [json.loads(line) for line in file]
            rdf = jsonld2nt(jskos, self.context)
            fmt = "ttl"
            original = stage / f"original.{fmt}"
            with open(original, "w") as f:
                f.write(rdf)

        namespaces = dict(self.namespaces())
        namespaces.pop(uri, None)
        rdf_receive(original, stage, log, namespaces)

        return log.done()
