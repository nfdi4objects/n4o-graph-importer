from pathlib import Path
from shutil import rmtree
from urllib.parse import urlparse
from jsonschema import validate
from .registry import Registry
from .utils import read_json, write_json
from .errors import NotFound, NotAllowed, ValidationError, ClientError
from .rdf import write_ttl, load_graph_from_file, rdf_receive
from .log import Log


class CollectionRegistry(Registry):
    schema = read_json(Path(__file__).parent.parent / 'collection-schema.json')
    context = read_json(Path(__file__).parent.parent /
                        'collection-context.json')

    def __init__(self, **config):
        super().__init__("collection", **config)

        self.collections_file = self.stage / "collections.json"
        self.collections_file_ttl = self.stage / "collections.ttl"
        if not self.collections_file.exists():
            self.update_collections([])

    def collections(self):
        return read_json(self.collections_file)

    def update_collections(self, cols):
        for col in cols:
            (self.stage / str(id)).mkdir(exist_ok=True)
        write_json(self.collections_file, cols)
        write_ttl(self.collections_file_ttl, cols, self.context)

    def collection_metadata(self, col, id=None):
        if "id" in col and "uri" in col:
            if col["uri"] != self.graph + col["id"]:
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
            col["uri"] = self.graph + col["id"]

        if id and col["id"] != str(id):
            raise ValidationError("id does not match!")
        col["partOf"] = [self.graph]
        if self.schema:
            validate(instance=col, schema=self.schema)
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

    def register(self, col):
        return self.set(None, col)

    def delete(self, id):
        col = self.get(id)
        cols = [c for c in self.collections() if c["id"] != str(id)]
        rmtree(self.stage / str(id), ignore_errors=True)
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

    def receive(self, id, file=None, namespaces={}):
        col = self.get(id)
        fmt = None

        if "access" in col:
            file = col["access"].get("url", file)
            fmt = col["access"].get("format", None)

        if not file:
            raise NotFound("Missing URL or file to receive data from")

        if not fmt:
            if Path(file).suffix in [".nt", ".ttl"]:
                fmt = "rdf/turtle"
            elif Path(file).suffix in [".rdf", ".xml"]:
                fmt = "rdf/xml"

        if fmt:
            fmt = fmt.removeprefix('https://format.gbv.de/')

        if fmt == "rdf/turtle":
            fmt = "ttl"
        elif fmt == "rdf/xml":
            fmt = "xml"
        else:  # TODO: support LIDO/XML
            raise ClientError("Unknown file format")

        original, log = self.receive_source(id, file, fmt)

        stage = self.stage / str(id)
        rdf_receive(original, stage, log, namespaces)

        return log.done()

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
