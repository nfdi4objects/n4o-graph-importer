from pathlib import Path
from shutil import rmtree
import requests
import re
from .utils import read_json, read_ndjson, write_json
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
        super().__init__("terminology", **config)

    def list(self):
        files = [f for f in self.stage.iterdir() if f.suffix ==
                 ".json" and re.match('^[0-9]+$', f.stem)]
        return [read_json(f) for f in files]

    def namespaces(self):
        namespaces = {}
        for voc in self.list():
            if "namespace" in voc:
                namespaces[voc["uri"]] = voc["namespace"]
        return namespaces

    def get(self, id):
        return read_json(self.stage / f"{int(id)}.json")

    def register(self, id, cache=None):
        uri = f"http://bartoc.org/en/node/{int(id)}"

        if cache:
            voc = [v for v in cache if v["uri"] == uri]
        else:
            voc = requests.get(f"https://bartoc.org/api/data?uri={uri}").json()

        if not len(voc):
            raise NotFound(f"Terminology not found: {uri}")
        voc = voc[0]
        write_json(self.stage / f"{id}.json", voc)
        rdf = jskos_to_rdf(voc).serialize(format='ntriples')
        query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri
        sparql_update(self.sparql, self.graph, query)
        sparql_insert(self.sparql, self.graph, rdf)
        return voc

    def registerAll(self, terms, cache=None):
        add, remove = [], []
        try:
            add = bartoc_ids(terms)
            remove = [t["uri"].split("/")[-1] for t in self.list()]
        except Exception:
            raise ValidationError("Malformed array of terminologies")

        for id in remove:
            self.delete(id)
        for id in add:
            self.register(id, cache)

        return self.list()

    def delete(self, id):
        self.remove(id)
        uri = self.get(id)["uri"]
        # TODO: duplicated code above
        (self.stage / f"{id}.json").unlink(missing_ok=False)
        rmtree(self.stage / str(id), ignore_errors=True)
        query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri
        sparql_update(self.sparql, self.graph, query)

        return {"uri": uri}

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
            jskos = read_ndjson(original)
            rdf = jskos_to_rdf(jskos).serialize(format='ntriples')
            fmt = "ttl"
            original = stage / f"original.{fmt}"
            with open(original, "w") as f:
                f.write(rdf)

        namespaces = dict(self.namespaces())
        namespaces.pop(uri, None)
        rdf_receive(original, stage, log, namespaces)

        return log.done()
