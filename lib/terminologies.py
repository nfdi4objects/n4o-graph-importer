from pathlib import Path
import requests
import re
import json
from .utils import write_json
from .errors import NotFound, ClientError, ValidationError
from .rdf import jskos_to_rdf, sparql_insert, sparql_update, rdf_receive
from .registry import Registry


def bartoc_ids(lst):
    r = re.compile("^http://bartoc\\.org/en/node/[1-9][0-9]*$")
    if type(lst) is not list or not all((r.match(item["uri"]) for item in lst)):
        raise Exception()
    return [item["uri"].split("/")[-1] for item in lst]


class TerminologyRegistry(Registry):

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
        voc = voc[0]

        # TODO: move to super class
        write_json(self.stage / f"{id}.json", voc)
        (self.stage / str(id)).mkdir(exist_ok=True)
        rdf = jskos_to_rdf(voc).serialize(format='ntriples')
        query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri
        sparql_update(self.sparql, self.graph, query)
        sparql_insert(self.sparql, self.graph, rdf)
        return voc

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

    def remove_metadata(self, id):
        # TODO: replace full graph instead
        uri = f"{self.prefix}{id}"
        query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri
        sparql_update(self.sparql, self.graph, query)

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
            rdf = jskos_to_rdf(jskos).serialize(format='ntriples')
            fmt = "ttl"
            original = stage / f"original.{fmt}"
            with open(original, "w") as f:
                f.write(rdf)

        namespaces = dict(self.namespaces())
        namespaces.pop(uri, None)
        rdf_receive(original, stage, log, namespaces)

        return log.done()
