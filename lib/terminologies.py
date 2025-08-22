from pathlib import Path
import requests
import re
import shutil
from urllib.request import urlretrieve
from .utils import read_json, write_json
from .errors import NotFound, ValidationError
from .rdf import to_rdf, jskos_context, sparql_insert, sparql_update


class TerminologyRegistry:

    def __init__(self, **config):
        self.stage = Path(config.get('stage', 'stage')) / "terminology"
        self.stage.mkdir(exist_ok=True)
        self.data = Path(config.get('data', 'data'))
        self.data.mkdir(exist_ok=True)
        self.graph = "https://graph.nfdi4objects.net/terminology/"
        self.sparql = config['sparql']

    def json_file(self, id):
        return self.stage / str(id)

    def list(self):
        files = [f for f in self.stage.iterdir() if f.suffix ==
                 ".json" and re.match('^[0-9]+$', f.stem)]
        return [read_json(f) for f in files]

    def get(self, id):
        try:
            return read_json(self.stage / f"{int(id)}.json")
        except Exception:
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
            rdf = to_rdf(voc, jskos_context).serialize(format='ntriples')
            query = "DELETE { ?s ?p ?o } WHERE { VALUES ?s { <%s> } ?s ?p ?o }" % uri
            sparql_update(self.sparql, self.graph, query)
            sparql_insert(self.sparql, self.graph, rdf)
        except (ValueError, TypeError):
            raise NotFound("Malformed terminology identitfier")

    def receive(self, id, file):
        self.get(id)  # make sure terminology has been registered
        if not file:
            raise Exception("Missing URL or file to receive data from")

        fmt = "ttl" if Path(file).suffix in [".nt", ".ttl"] else "rdf"
        original = self.stage / str(id) / f"original.{fmt}"

        if "/" not in file:
            file = self.data / file
            if not file.is_file():
                raise Exception("File not found: {file}")
            shutil.copy(file, original)
        else:  # TODO: test this
            urlretrieve(file, original)

#        if Path(file).suffix

        # TODO: check and cleanup RDF
        e = ValidationError("")

        pass

    def load(self, id):
        file = self.stage / str(id) / "filtered.nt"
        if file.is_file():
            # TODO
            pass
        else:
            raise NotFound("Terminology data has not been received!")
