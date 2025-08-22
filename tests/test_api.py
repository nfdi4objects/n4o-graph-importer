import unittest
import responses
import tempfile
import re
from pathlib import Path
import pytest
import json

from lib import sparql_query, read_json
from app import app, init

docker_port = 3033
sparql = f"http://localhost:{docker_port}/n4o"

base = "https://graph.nfdi4objects.net/collection/"
terminology_graph = "https://graph.nfdi4objects.net/terminology/"

bartoc_18274 = read_json("tests/18274.json")

collection_1 = {
  "id": "1",
  "name": "test collection",
  "url": "https://example.org/",
  "uri": f"{base}1"
}
collection_1_full = {
    **collection_1,
    "partOf": [ base ]
}
collection_0 = {
  "name": "another test collection",
  "url": "https://example.com/",
}
collection_3_full = {
  **collection_0,
  "id": "3",
  "uri": f"{base}3",
  "partOf": [ base ]
}

@pytest.fixture
def stage():
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir

@pytest.fixture
def client(stage):
    app.testing = True

    data = Path(__file__).parent
    init(title="N4O Graph Import API TEST", stage=stage, sparql=sparql, data=data)

    with app.test_client() as client:
        yield client


def test_terminology(client):
    uri = "http://bartoc.org/en/node/18274"
    with responses.RequestsMock() as mock:
        mock.get(
            f"https://bartoc.org/api/data?uri={uri}",
            json=[ bartoc_18274 ]
        )
        resp = client.put('/terminology/18274')
        assert resp.status_code == 200

    resp = client.get('/terminology/')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    query = "SELECT * { GRAPH <%s> { <%s> a ?type } } LIMIT 1" % (terminology_graph, uri)
    resp = sparql_query(sparql, query)
    assert len(resp["results"]["bindings"]) == 1

    # TODO: check list of prefixes

    resp = client.post('/terminology/18274/receive')
    assert resp.status_code == 400

    resp = client.post('/terminology/18274/receive?from=skos.rdf')
    assert resp.status_code == 200

    # TODO: load terminology

def test_api(client):

    # start without collections
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"N4O Graph Import API TEST" in resp.data

    resp = client.get('/collection')
    assert resp.status_code == 200
    assert resp.get_json() == []

    resp = client.get('/collection/1')
    assert resp.status_code == 404

    # add collection
    resp = client.put('/collection/', json={})
    assert resp.status_code == 400
    assert b"Invalid collection metadata" in resp.data

    resp = client.put('/collection/', json=[collection_1])
    assert resp.status_code == 200

    resp = client.get('/collection/')
    assert resp.status_code == 200
    assert resp.get_json() == [collection_1_full]

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1_full

    # only allowed when empty
    resp = client.put('/collection/', json=[])
    assert resp.status_code == 403

    # delete collection
    resp = client.delete('/collection/1')
    assert resp.status_code == 200

    resp = client.get('/collection/1')
    assert resp.status_code == 404

    # add again
    resp = client.put('/collection/1', json=collection_1)
    assert resp.status_code == 200  # TODO: should be 201 Created

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1_full

    # add without id in record
    resp = client.put('/collection/3', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json() == collection_3_full

    # add without known id
    resp = client.post('/collection/', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json()["id"] == "4"
