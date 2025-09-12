from pathlib import Path
import requests
import re
import json
from .utils import read_json
from .errors import NotFound, ClientError, ValidationError
from .rdf import jsonld2nt, rdf_receive
from .registry import Registry


def bartoc_ids(lst):
    r = re.compile("^http://bartoc\\.org/en/node/[1-9][0-9]*$")
    if type(lst) is not list or not all((r.match(item["uri"]) for item in lst)):
        raise Exception()
    return [item["uri"].split("/")[-1] for item in lst]


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

    # TODO: make this generic
    def register_all(self, terms, cache=None):
        add, remove = [], []
        try:
            # better check before removing
            add = bartoc_ids(terms)
            remove = [t["uri"].split("/")[-1] for t in self.list()]
        except Exception:
            raise ValidationError("Malformed array of terminologies")

        for id in remove:
            self.delete(id)
        for id in add:
            self.register(id, cache)

        return self.list()

    def receive(self, id, file):
        uri = self.get(id)["uri"]  # make sure terminology has been registered

        if not file:
            raise ClientError("Missing URL or file to receive data from")

        if Path(file).suffix in [".nt", ".ttl"]:
            fmt = "ttl"
        elif Path(file).suffix in [".rdf", ".xml"]:
            fmt = "xml"
        elif Path(file).suffix == ".ndjson":
            fmt = "ndjson"
        else:
            raise ClientError("Unknown file extension of file {file}")

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
