from pathlib import Path
import requests
import re
import shutil
from urllib.request import urlretrieve
from .utils import read_json, read_ndjson, write_json
from .errors import NotFound, ClientError
from .rdf import jskos_to_rdf, sparql_insert, sparql_update, load_graph_from_file, rdf_convert


class TerminologyRegistry:

    def __init__(self, **config):
        self.stage = Path(config.get('stage', 'stage')) / "terminology"
        self.stage.mkdir(exist_ok=True)
        self.data = Path(config.get('data', 'data'))
        self.data.mkdir(exist_ok=True)
        self.graph = "https://graph.nfdi4objects.net/terminology/"
        self.sparql = config['sparql']

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
        try:
            return read_json(self.stage / f"{int(id)}.json")
        except (NotFound, FileNotFoundError):
            raise NotFound(f"Terminology not found: {id}")

    def add(self, id):
        try:
            id = int(id)
            uri = f"http://bartoc.org/en/node/{id}"
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
        except (ValueError, TypeError):
            raise NotFound("Malformed terminology identitfier")

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

        original = self.stage / str(id) / f"original.{fmt}"

        if "/" not in file:
            file = self.data / file
            if not file.is_file():
                raise NotFound("File not found: {file}")
            shutil.copy(file, original)
        else:  # TODO: test this
            urlretrieve(file, original)

        # convert JSKOS to RDF
        if fmt == "ndjson":
            jskos = read_ndjson(original)
            rdf = jskos_to_rdf(jskos).serialize(format='ntriples')
            fmt = "ttl"
            original = self.stage / str(id) / f"original.{fmt}"
            with open(original, "w") as f:
                f.write(rdf)

        # TODO: also validate and filter RDF
        rdf_convert(original, self.stage / str(id) / "filtered.nt")

        return {"ok": True}

    def load(self, id):
        file = self.stage / str(id) / "filtered.nt"
        uri = self.get(id)["uri"]
        if file.is_file():
            load_graph_from_file(self.sparql, uri, file, "ttl")
            return {"uri": uri}
        else:
            raise NotFound("Terminology data has not been received!")
