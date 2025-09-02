from pathlib import Path
from shutil import rmtree
from urllib.parse import urlparse
from jsonschema import validate
from .registry import Registry
from .utils import read_json, write_json
from .errors import NotFound, NotAllowed, ValidationError
from .rdf import write_ttl, load_graph_from_file
from .log import Log

JSON_SCHEMA = read_json(Path(__file__).parent.parent /
                        'collection-schema.json')

collection_context = read_json(
    Path(__file__).parent.parent / 'collection-context.json')


class CollectionRegistry(Registry):

    def __init__(self, **config):
        self.stage = stage = Path(config.get('stage', 'stage'))
        if not stage.is_dir():
            raise NotFound(f"Missing stage directory {stage}")
        (stage / "collection").mkdir(exist_ok=True)

        self.collections_file = stage / "collection" / "collections.json"
        self.collections_file_ttl = stage / "collection" / "collections.ttl"
        if not self.collections_file.exists():
            self.update_collections([])

        self.base = config.get(
            "base", "https://graph.nfdi4objects.net/collection/")

    def collections(self):
        return read_json(self.collections_file)

    def update_collections(self, cols):
        for col in cols:
            (self.stage / 'collection' / str(id)).mkdir(exist_ok=True)
        write_json(self.collections_file, cols)
        write_ttl(self.collections_file_ttl, cols, collection_context)

    def collection_metadata(self, col, id=None):
        if "id" in col and "uri" in col:
            if col["uri"] != self.base + col["id"]:
                raise ValidationError("uri and id do not match!")
        elif "uri" in col:
            col["id"] = col["uri"].split("/")[-1]
        else:
            if "id" not in col:
                if id:
                    col["id"] = str(id)
                else:
                    cols = self.collections()
                    col["id"] = str(max(int(c["id"])
                                    for c in cols) + 1 if cols else 1)
            col["uri"] = self.base + col["id"]

        if id and col["id"] != str(id):
            raise ValidationError("id does not match!")
        col["partOf"] = [self.base]
        validate(instance=col, schema=JSON_SCHEMA)
        return col

    def get(self, id):
        try:
            return next(c for c in self.collections() if c["id"] == str(id))
        except StopIteration:
            raise NotFound(f"Collection {id} not found")

    def set(self, id, col):
        if type(col) is not dict:
            raise ValidationError("Expected JSON object")
        col = self.collection_metadata(col, id)
        cols = self.collections()
        cols.append(col)
        self.update_collections(cols)
        return col

    def add(self, col):
        return self.set(None, col)

    def delete(self, id):
        col = self.get(id)
        cols = [c for c in self.collections() if c["id"] != str(id)]
        rmtree(self.stage / 'collection' / str(id), ignore_errors=True)
        self.update_collections(cols)
        return col

    def set_all(self, cols):
        if type(cols) is not list:
            raise ValidationError("Expected list of collections")
        if len(self.collections()):
            raise NotAllowed("List of collections is not empty")
        cols = [self.collection_metadata(c) for c in cols]
        self.update_collections(cols)
        return cols

    def receive(self, id, file=None, format=None):
        col = self.get(id)

        if "access" in col:
            if not file:
                file = col["access"].get("url")
            if not format:
                format = col["access"].get("format")

        if format:
            format = format.removeprefix('https://format.gbv.de/')
        else:
            format = "rdf"
        if format != "rdf":
            raise ServerException(
                f"Only RDF data supported so far, got {format}")

        #try:
        #    urlparse(file or "?")
        #except Exception:
        raise NotFound("Missing url or malformed URL to receive data from")

        # TODO: fmt => rdf/xml or nt / ttl
        #
        #log = Log(self.stage / str(id) / "receive.log",
        #          f"Receiving collection {id}")
        #
        #original = self.stage / str(id) / f"original.{fmt}"


        # self.receive_file(log, file, target)

        print(f"TODO: Receive {format} data from {file}")

        #transform_rdf

        # TODO: migrate from bash script to Python
        """
        # TODO: support OAI-PMH for LIDO/XML
        inbox=$STAGE/inbox/$id
        download_dir=$stage/download

        rm -rf $download_dir
        mkdir -p $download_dir

        if [[ $url == *doi.org* ]]; then
          ./download-from-repository.py $url $download_dir
        elif [[ $url == http* ]]; then
          wget -q $url --directory-prefix $download_dir
        elif [[ -d $inbox ]]; then
          cp $inbox/* $download_dir
        else
          error "No valid source $url"
        fi

        # TODO: support LIDO/XML via repository
        ./extract-rdf.py $download_dir $stage/triples.nt
        ./transform-rdf $stage/triples.nt     # includes validation
        """

    def load(self, id):
        col = self.get(id)
