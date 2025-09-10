from pathlib import Path
from shutil import copy, copyfileobj, rmtree
import urllib
from .rdf import load_graph_from_file, sparql_update
from .log import Log
from .errors import NotFound
from .utils import read_json
import re


class Registry:
    context = None
    schema = None

    def __init__(self, kind, **config):
        self.base = config["base"]
        self.sparql = config["sparql"]
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

    def remove_metadata(self, id):
        pass

    def delete(self, id):
        self.remove(id)
        (self.stage / f"{id}.json").unlink(missing_ok=False)
        rmtree(self.stage / str(id), ignore_errors=True)
        self.remove_metadata(id)

    def load(self, id):
        stage = self.stage / str(id)
        file = stage / "checked.nt"
        uri = self.get(id)["uri"]
        if not file.is_file():
            raise NotFound(f"{self.kind} data has not been received!")
        log = Log(stage / "load.log", f"Loading {self.kind} {uri} from {file}")
        load_graph_from_file(self.sparql, uri, file, "ttl")
        return log.done()

    def remove(self, id):
        uri = self.get(id)["uri"]
        rmtree(self.stage / str(id), ignore_errors=True)
        sparql_update(self.sparql, uri, f"DROP GRAPH <{uri}>")

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
