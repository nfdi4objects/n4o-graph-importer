from pathlib import Path
import requests
import re
from SPARQLWrapper import SPARQLWrapper
from .utils import read_json, write_json
from .errors import NotFound, NotAllowed, ValidationError, ServerError
from .rdf import to_rdf

terminology_context = read_json(
    Path(__file__).parent.parent / 'jskos-context.json')

# TODO
"""
DELETE { ?s ?p ?o }
WHERE {
  { VALUES ?s { <%s> } ?s ?p ?o }
  UNION
  { VALUES ?o { <%s> } ?s ?p ?o } 
}
"""


def sparql_update(api, graph, rdf):
    print(f"Executing SPARQL Update at {api}")
    sparql = SPARQLWrapper(api, returnFormat='json')
    sparql.method = 'POST'
    sparql.setQuery("INSERT DATA { GRAPH <%s> { %s } }" % (graph, rdf))
    try:
        res = sparql.query()
        if res.response.code != 200:
            raise Exception(f"HTTP Status code {res.response.code}")
    except Exception as e:
        raise ServerError(f"SPARQL UPDATE failed: {e}")


class TerminologyRegistry:

    def __init__(self, **config):
        self.stage = Path(config.get('stage', 'stage')) / "terminology"
        self.stage.mkdir(exist_ok=True)
        self.graph = "https://graph.nfdi4objects.net/terminology/"
        self.sparql = config['sparql']

    def json_file(self, id):
        return self.stage / str(id)

    def list(self):
        files = [f for f in self.stage.iterdir() if re.match('^[0-9]+$', f.stem)]
        return [read_json(f) for f in files]

    def get(self, id):
        try:
            return read_json(self.stage / str(int(id)) + ".json")
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
            rdf = to_rdf(voc, terminology_context).serialize(format='ntriples')
            sparql_update(self.sparql, self.graph, rdf)

        except (ValueError, TypeError) as e:
            print(e)
            raise NotFound("Malformed terminology identitfier")

    # TODO
    # def receive
    # def load
