from pathlib import Path
import requests
import re
import sys
from urllib.request import urlretrieve
from .utils import read_json, read_ndjson, write_json
from .errors import NotFound, ClientError
from .rdf import jskos_to_rdf, sparql_insert, sparql_update, rdf_convert
from .log import Log
from .registry import Registry


class TerminologyRegistry(Registry):

    def __init__(self, **config):
        super().__init__("terminology", **config)
        self.graph = "https://graph.nfdi4objects.net/terminology/"

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

    def add(self, id):
        uri = f"http://bartoc.org/en/node/{int(id)}"
        voc = requests.get(f"https://bartoc.org/api/data?uri={uri}").json()
        if not len(voc):
            raise NotFound(f"Terminology not found: {uri}")
        voc = voc[0]
        write_json(self.stage / f"{id}.json", voc)
        (self.stage / str(id)).mkdir(exist_ok=True)
        rdf = jskos_to_rdf(voc).serialize(format='ntriples')
        query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri

        sparql_update(self.sparql, self.graph, query)
        sparql_insert(self.sparql, self.graph, rdf)
        return voc

    def receive(self, id, file):
        self.get(id)  # make sure terminology has been registered
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

        log = Log(self.stage / str(id) / "receive.log",
                  f"Receiving terminology {id}")

        original = self.stage / str(id) / f"original.{fmt}"

        self.receive_file(log, file, original)

        # convert JSKOS to RDF
        if fmt == "ndjson":
            log.append("Converting JSKOS to RDF")
            jskos = read_ndjson(original)
            rdf = jskos_to_rdf(jskos).serialize(format='ntriples')
            fmt = "ttl"
            original = self.stage / str(id) / f"original.{fmt}"
            with open(original, "w") as f:
                f.write(rdf)

        # TODO: also validate and filter RDF
        rdf_convert(original, self.stage / str(id) / "filtered.nt")

        return log.done()
