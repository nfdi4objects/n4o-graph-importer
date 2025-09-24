from unittest.mock import patch
import tempfile
import os
from urllib.parse import urlparse, parse_qs
from shutil import copy
from pathlib import Path
import pytest

from rdflib import Graph
from lib import TripleStore, read_json
from app import app, init

cwd = Path().cwd()

sparqlApi = os.getenv('SPARQL', 'http://localhost:3033/n4o')
sparql = TripleStore(sparqlApi)

base = "https://graph.nfdi4objects.net/collection/"
terminology_graph = "https://graph.nfdi4objects.net/terminology/"

bartoc = read_json("tests/bartoc-subset.json")

collection_1 = read_json("tests/collection/1.json")
collection_1_full = {
    **collection_1,
    "partOf": [base]
}
collection_0 = {
    "name": "another test collection",
    "url": "https://example.com/",
}
collection_3_full = {
    **collection_0,
    "id": "3",
    "uri": f"{base}3",
    "partOf": [base]
}

# for pretty-printing
# Namespace prefixes for pretty RDF/Turtle
#def to_rdf(doc, context):
#    prefixes = read_json(Path(__file__).parent.parent / 'prefixes.json')
#    nquads = jsonld2nt(doc, context)
#    g = Graph(bind_namespaces="none")
#    for prefix, uri in prefixes.items():
#        g.bind(prefix, Namespace(uri))
#    g.parse(data=nquads, format='nquads')
#    return g


def count_graphs():
    query = "SELECT ?g (count(*) as ?t) { GRAPH ?g {?s ?p ?o} } GROUP BY ?g"
    graphs = {}
    for row in sparql.query(query):
        graphs[row['g']['value']] = int(row['t']['value'])
    return graphs


@pytest.fixture
def stage():
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir


@pytest.fixture
def client(stage):
    app.testing = True

    data = Path(__file__).parent
    init(title="N4O Graph Import API TEST",
         stage=stage, sparql=sparqlApi, data=data)

    with app.test_client() as client:
        yield client, stage


def mock_urlopen(url):
    urls = {"http://example.org/20533.concepts.ndjson": "tests/20533.concepts.ndjson"}
    return open(urls[url], "rb")


def mock_requests_get(url):
    uri = parse_qs(urlparse(url).query)['uri'][0]
    json = next(([item] for item in bartoc if item["uri"] == uri), [])
    return type('', (), {'json': lambda s: json})()


def test_errors(client):
    client, stage = client

    def fail(method, path, payload, msg=None):
        res = client.open(path, method=method, json=payload)
        assert res.status_code == 400
        if msg:
            assert res.get_json()["error"] == msg

    # malformed payload
    fail("PUT", "/collection/1", [], "expected JSON object")
    fail("PUT", "/collection/1", {"uri": "https://graph.nfdi4objects.net/collection/2"},
         "URI https://graph.nfdi4objects.net/collection/2 and id 1 don't match")
    fail("PUT", "/collection/1", {"id": "2"}, "ids 1 and 2 don't match")

    fail("PUT", "/collection/", {}, "expected list of collection")
    fail("PUT", "/collection/", [{"id": "1", "uri": "https://graph.nfdi4objects.net/collection/2"}],
         "URI https://graph.nfdi4objects.net/collection/2 and id 1 don't match")
    fail("POST", "/collection/",
         {"id": "1", "uri": "https://graph.nfdi4objects.net/collection/2", "name": "x"},
         "URI https://graph.nfdi4objects.net/collection/2 and id 1 don't match")
    fail("POST", "/collection/", {})


def test_terminology(client):
    client, stage = client

    # Additional endpoints
    client.get('/data/').status_code == 200
    client.get('/data/skos.rdf').status_code == 200
    client.get('/status.json').status_code == 200
    client.get(
        '/status.json').get_json()["title"] == "N4O Graph Import API TEST"

    # get unregisterd terminology
    assert client.get("/terminology/18274").status_code == 404
    assert client.get("/terminology/18274/stage/").status_code == 404

    with patch('requests.get', new=mock_requests_get):

        # register terminology, get afterwards
        assert client.put("/terminology/18274").status_code == 200
        assert client.get("/terminology/18274").status_code == 200

        # try to register non-existing terminology
        assert client.put("/terminology/0").status_code == 404

    assert client.get("/terminology/18274/stage/").status_code == 200
    assert client.get("/terminology/18274/stage/checked.nt").status_code == 404

    # get list of terminologies
    resp = client.get('/terminology/')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    # get list terminology namespaces
    assert client.get("/terminology/namespaces.json").get_json() == {
        "http://bartoc.org/en/node/18274": "http://www.w3.org/2004/02/skos/core#"}

    # replace list of terminologies
    assert client.put("/terminology/", json={}).status_code == 400
    assert client.put("/terminology/", json=[{}]).status_code == 400
    assert client.put("/terminology/", json=[{"uri": "x"}]).status_code == 400
    assert len(client.get('/terminology/').get_json()) == 1
    assert client.put("/terminology/", json=[]).status_code == 200
    assert client.get('/terminology/').get_json() == []
    assert client.get("/terminology/namespaces.json").get_json() == {}

    with patch('requests.get', new=mock_requests_get):
        json = [{"uri": "http://bartoc.org/en/node/18274"}]
        assert client.put("/terminology/", json=json).status_code == 200
    assert len(client.get('/terminology/').get_json()) == 1

    # receive terminology data and check log
    assert client.get('/terminology/18274/receive').status_code == 404
    assert client.post('/terminology/18274/receive').status_code == 404
    assert client.post(
        '/terminology/18274/receive?from=abc').status_code == 400
    assert client.post(
        '/terminology/18274/receive?from=abc.rdf').status_code == 404
    assert client.post(
        '/terminology/18274/receive?from=skos.rdf').status_code == 200
    assert client.get('/terminology/18274/receive').status_code == 200
    assert client.get("/terminology/18274/stage/checked.nt").status_code == 200

    # load terminology data and check log
    assert client.get('/terminology/18274/load').status_code == 404
    assert client.post('/terminology/18274/load').status_code == 200
    assert client.get('/terminology/18274/load').status_code == 200

    # try to receive and load an unregistered terminology
    assert client.post(
        '/terminology/20533/receive?from=abc').status_code == 404
    assert client.post('/terminology/20533/load').status_code == 404

    # register, receive, and load another terminology
    with patch('requests.get', new=mock_requests_get):
        assert client.put('/terminology/20533').status_code == 200
    assert client.post('/terminology/20533/load').status_code == 404
    assert client.post(
        '/terminology/20533/receive?from=20533.concepts.ndjson').status_code == 200
    assert client.post('/terminology/20533/load').status_code == 200

    with patch('urllib.request.urlopen', new=mock_urlopen):
        query = '/terminology/20533/receive?from=http://example.org/20533.concepts.ndjson'
        assert client.post(query).status_code == 200

    # check size of terminology graphs
    assert count_graphs() == {
        'https://graph.nfdi4objects.net/terminology/': 29,
        'http://bartoc.org/en/node/18274': 377,
        'http://bartoc.org/en/node/20533': 679
    }
    assert client.post("/terminology/20533/remove").status_code == 200
    assert count_graphs() == {
        'https://graph.nfdi4objects.net/terminology/': 29,
        'http://bartoc.org/en/node/18274': 377,
    }

    # no problem when graph has already been removed
    assert client.post("/terminology/20533/remove").status_code == 200

    # but graph must be registered
    assert client.post("/terminology/1234/remove").status_code == 404

    # delete terminology
    assert client.delete('/terminology/18274').status_code == 200
    assert count_graphs() == {
        'https://graph.nfdi4objects.net/terminology/': 29,
    }

    # TODO: this cleanup should not be required!
    graph = "https://graph.nfdi4objects.net/terminology/"
    sparql.update(f"DROP GRAPH <{graph}>")


def test_api(client):
    client, stage = client

    # start without collections
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"N4O Graph Import API TEST" in resp.data

    assert client.get('/icon.png').status_code == 200

    assert client.get('/data/').status_code == 200
    assert client.get('/data/data.ttl').status_code == 200

    resp = client.get('/collection/')
    assert resp.status_code == 200
    assert resp.get_json() == []

    assert client.get('/collection/1').status_code == 404

    assert client.get('/collection/schema.json').status_code == 200

    # register collection
    assert client.put('/collection/', json=[collection_1]).status_code == 200

    resp = client.get('/collection/')
    assert resp.status_code == 200
    assert resp.get_json() == [collection_1_full]

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1_full

    assert client.get("/collection/1/stage/").status_code == 200

    assert count_graphs() == {'https://graph.nfdi4objects.net/collection/': 4}

    # delete collection
    assert client.delete('/collection/1').status_code == 200
    assert client.get('/collection/1').status_code == 404

    # try to receive and load non-existing collection
    assert client.post('/collection/1/receive').status_code == 404
    assert client.post('/collection/1/load').status_code == 404

    # add again
    resp = client.put('/collection/1', json=collection_1)
    assert resp.status_code == 200  # TODO: should be 201 Created

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1_full

    # purge collections
    assert client.put('/collection/', json=[]).status_code == 200

    # add without id in record
    resp = client.put('/collection/3', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json() == collection_3_full

    # add without known id
    resp = client.post('/collection/', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json()["id"] == "4"

    # receive from file
    assert client.post('/collection/3/receive').status_code == 404
    assert client.post(
        '/collection/3/receive?from=data.ttl').status_code == 200
    assert client.get('/collection/3/receive').status_code == 200

    # load received RDF
    assert client.post('/collection/3/load').status_code == 200
    assert client.get('/collection/3/load').status_code == 200

    uri = f"{base}3"
    query = f"SELECT * {{ GRAPH <{uri}> {{?s ?p ?o}} }} ORDER BY DESC(?s)"
    res = sparql.query(query)
    graph = [{'s': {'type': 'uri', 'value': 'https://example.org/x'},
              'p': {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
             'o': {'type': 'uri', 'value': 'http://www.cidoc-crm.org/cidoc-crm/E1_CRM_Entity'}},
             {'s': {'type': 'uri', 'value': 'http://www.cidoc-crm.org/cidoc-crm/E1_CRM_Entity'},
             'p': {'type': 'uri', 'value': 'https://example.org/foo'},
              'o': {'type': 'uri', 'value': 'https://example.org/bar'}}]
    assert res == graph

    # register terminology and receive + load again
    # test local BARTOC cache
    copy("tests/bartoc-crm.json", "tests/bartoc.json")
    assert client.put('/terminology/18274').status_code == 404
    assert client.put('/terminology/1644').status_code == 200  # CIDOC-CRM
    os.remove("tests/bartoc.json")

    client.post('/collection/3/receive?from=data.ttl')
    client.post('/collection/3/load')
    assert sparql.query(query) == graph[:1]

    assert client.post('/collection/3/receive?from=rdf.zip').status_code == 200
    assert client.post('/collection/3/load').status_code == 200

    query = f"SELECT ?e {{ GRAPH <{base}3> {{ ?e a ?t }} }} ORDER BY ?o"
    res = [r["e"]["value"] for r in sparql.query(query)]
    assert res == [f'https://example.org/e{i}' for i in [1, 2, 3, 4]]

    assert client.post(
        '/terminology/1644/receive?from=crm.ttl').status_code == 200

    # TODO: test file upload
    # with open("tests/data.ttl", "rb") as f:
    #    data = {"data.ttl":f}
    #    res = client.post('/collection/1/receive', data=data,
    #                  content_type='multipart/form-data')
    #    assert res.status_code == 200

    # assert client.post('/collection/1/load').status_code == 404
    query = f"SELECT * {{ GRAPH <{base}> {{ <{base}3> <http://purl.org/dc/terms/issued> ?d}} }}"
    assert len(sparql.query(query)) == 1

    # remove graph, keep registered
    assert client.post('/collection/3/remove').status_code == 200
    assert client.get('/collection/3').status_code == 200
    # TODO: assert len(sparql.query(query)) == 0

    # TODO: metadata should be removed
    query = f"SELECT * {{ <{base}3> ?p ?o }}"
    # assert len(sparql.query(query)) == 0


def test_mappings(client):
    client, stage = client

    assert client.post('/mappings/', json={}).status_code == 200
    assert client.get('/mappings/1').status_code == 200

    assert client.put('/mappings/', json=[{"name": "A"}, {"name": "B"}]).status_code == 200
    assert client.get('/mappings/1').status_code == 200
    assert client.get('/mappings/2').status_code == 200

    # receive and load JSKOS mappings
    assert client.post('/mappings/1/receive?from=mappings.ndjson').status_code == 200
    assert client.post('/mappings/1/load').status_code == 200
    assert list(client.get('/mappings/1/receive').get_json().values()) == [
        'Receiving 1 from mappings.ndjson',
        f'Retrieving source {cwd}/tests/mappings.ndjson from data directory',
        'Converting JSKOS mappings to RDF mapping triples',
        'Processed 2 lines into 1 mappings',
        f'Extracting RDF from file://{stage}/mappings/1/original.ttl as turtle',
        'Removed 0 triples, remaining 1 unique triples.',
        'done']

    assert client.post('/mappings/2/receive?from=mappings.ttl').status_code == 200
    assert client.post('/mappings/2/load').status_code == 200
    # TODO: check contents

    assert client.get("/mappings/2/stage/").status_code == 200
