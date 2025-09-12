from pathlib import Path
from datetime import datetime
from shutil import copy, copyfileobj, rmtree
import urllib
from .rdf import jsonld2nt, TripleStore
from .log import Log
from .errors import NotFound
from .utils import read_json, write_json
import re


class Registry:
    context = None
    schema = None

    def __init__(self, kind, **config):
        self.base = config["base"]
        self.sparql = TripleStore(config["sparql"])
        self.kind = kind
        # named graphs
        self.graph = f"{self.base}{kind}/"
        self.prefix = config.get("prefix", self.graph)
        # directories
        self.stage = Path(config.get("stage", "stage")) / kind
        self.stage.mkdir(exist_ok=True, parents=True)
        self.data = Path(config.get("data", "data"))
        self.data.mkdir(exist_ok=True, parents=True)

    def list(self):
        return [
            read_json(f) for f in self.stage.iterdir() if f.suffix == ".json" and re.match('^[0-9]+$', f.stem)
        ] if self.stage.is_dir() else []

    def get(self, id):
        return read_json(self.stage / f"{int(id)}.json")

    def _register(self, data):
        id = data["uri"].split("/")[-1]
        write_json(self.stage / f"{id}.json", data)
        (self.stage / str(id)).mkdir(exist_ok=True)
        self.update_metadata()
        return data

    def update_metadata(self):
        query = "SELECT * WHERE { GRAPH <" + self.graph + \
            "> { VALUES (?p) {(<http://purl.org/dc/terms/issued>)} ?s ?p ?o } }"
        issued = self.sparql.query_ttl(query)
        metadata = jsonld2nt(self.list(), self.context)
        file = self.stage / f"{self.kind}.ttl"
        with open(file, "w") as f:
            f.write(metadata)
            f.write(issued)
        self.sparql.store_file(self.graph, file)

    def delete(self, id):
        self.remove(id)
        (self.stage / f"{id}.json").unlink(missing_ok=False)
        rmtree(self.stage / str(id), ignore_errors=True)

    def load(self, id):
        stage = self.stage / str(id)
        file = stage / "checked.nt"
        uri = self.get(id)["uri"]
        if not file.is_file():
            raise NotFound(f"{self.kind} data has not been received!")
        log = Log(stage / "load.log", f"Loading {self.kind} {uri} from {file}")
        self.sparql.store_file(uri, file)
        issued = datetime.now().replace(microsecond=0).isoformat()
        log.append(f"Update timestamp to {issued}")
        triples = f'<{uri}> <http://purl.org/dc/terms/issued> "{issued}"^^<http://www.w3.org/2001/XMLSchema#dateTime>'
        self.sparql.insert(self.graph, triples)
        return log.done()

    def remove(self, id):
        uri = self.get(id)["uri"]
        rmtree(self.stage / str(id), ignore_errors=True)
        self.sparql.update(f"DROP GRAPH <{uri}>")

    def receive_log(self, id):
        return Log(self.stage / str(id) / "receive.log").load()

    def load_log(self, id):
        return Log(self.stage / str(id) / "load.log").load()

    def receive_source(self, id, source, fmt):
        stage = self.stage / str(id)
        stage.mkdir(exist_ok=True)

        original = stage / f"original.{fmt}"
        log = Log(stage / "receive.log", f"Receiving {id} from {source}")

        try:
            if "/" not in source:
                source = self.data / source
                log.append(f"Retrieving source {source} from data directory")
                copy(source, original)
            else:
                log.append(f"Retrieving source from {source}")
                with urllib.request.urlopen(source) as fsrc, open(original, 'wb') as fdst:
                    copyfileobj(fsrc, fdst)
        except Exception as e:
            log.done(f"Retrieving failed: {e}")
            raise NotFound(f"{source} not found")

        return (original, log)
