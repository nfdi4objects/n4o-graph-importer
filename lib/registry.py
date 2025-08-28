from pathlib import Path
from .rdf import load_graph_from_file
from .log import Log
from .errors import NotFound


class Registry:
    def __init__(self, what, **config):
        self.what = what
        self.stage = Path(config.get('stage', 'stage')) / what
        self.stage.mkdir(exist_ok=True)
        self.data = Path(config.get('data', 'data'))
        self.data.mkdir(exist_ok=True)
        self.sparql = config['sparql']

    def load(self, id):
        stage = self.stage / str(id)
        file = stage / "filtered.nt"
        uri = self.get(id)["uri"]
        if not file.is_file():
            raise NotFound(f"{self.what} data has not been received!")
        log = Log(stage / "load.log", f"Loading {self.what} {uri} from {file}")
        load_graph_from_file(self.sparql, uri, file, "ttl")
        return log.done()
