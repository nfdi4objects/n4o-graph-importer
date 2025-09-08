from pathlib import Path
from shutil import copy, copyfileobj
import urllib
from .rdf import load_graph_from_file
from .log import Log
from .errors import NotFound


class Registry:
    context = None
    schema = None

    def __init__(self, base, kind, **config):
        self.base = config.get("base", base)  # must be URL ending with /
        self.kind = kind
        self.graph = f"{base}{kind}/"
        self.stage = Path(config.get("stage", "stage")) / kind
        self.stage.mkdir(exist_ok=True)
        self.data = Path(config.get("data", "data"))
        self.data.mkdir(exist_ok=True)
        self.sparql = config["sparql"]

    def load(self, id):
        stage = self.stage / str(id)
        file = stage / "checked.nt"
        uri = self.get(id)["uri"]
        if not file.is_file():
            raise NotFound(f"{self.kind} data has not been received!")
        log = Log(stage / "load.log", f"Loading {self.kind} {uri} from {file}")
        load_graph_from_file(self.sparql, uri, file, "ttl")
        return log.done()

    def receive_log(self, id):
        return Log(self.stage / str(id) / "receive.log").load()

    def load_log(self, id):
        return Log(self.stage / str(id) / "load.log").load()

    def receive_source(self, id, source, fmt):
        stage = self.stage / str(id)
        stage.mkdir(exist_ok=True)

        original = stage / f"original.{fmt}"
        log = Log(stage / "receive.log", f"Receiving {id} from {source}")

        if "/" not in source:
            source = self.data / source
            log.append(f"Retrieving source {source} from data directory")
            copy(source, original)
        else:
            log.append(f"Retrieving source from {source}")
            with urllib.request.urlopen(source) as fsrc, open(original, 'wb') as fdst:
                copyfileobj(fsrc, fdst)

        return (original, log)
