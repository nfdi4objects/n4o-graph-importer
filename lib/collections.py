from pathlib import Path
from jsonschema import validate
from .registry import Registry
from .utils import read_json, write_json
from .errors import NotFound, NotAllowed, ValidationError, ClientError
from .rdf import rdf_receive


class CollectionRegistry(Registry):
    schema = read_json(Path(__file__).parent.parent / 'collection-schema.json')
    context = read_json(Path(__file__).parent.parent /
                        'collection-context.json')

    def __init__(self, **config):
        super().__init__("collection", **config)

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
                    cols = self.list()
                    col["id"] = str(max(int(c["id"])
                                    for c in cols) + 1 if cols else 1)
            col["uri"] = self.graph + col["id"]

        if id and col["id"] != str(id):
            raise ValidationError("id does not match!")
        col["partOf"] = [self.graph]
        if self.schema:
            validate(instance=col, schema=self.schema)
        return col

    def register(self, col, id=None):
        if type(col) is not dict:
            raise ValidationError("Expected JSON object")
        col = self.collection_metadata(col, id)
        id = col["uri"].split("/")[-1]
        write_json(self.stage / f"{id}.json", col)
        # TODO: update metadata in triple store
        return col

    def register_all(self, cols):
        if type(cols) is not list:
            raise ValidationError("Expected list of collections")
        if len(self.list()):
            raise NotAllowed("List of collections is not empty")
        for c in cols:
            self.register(c)
        return self.list()

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
