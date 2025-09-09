import unittest
from unittest.mock import patch
import responses
import urllib.request
from werkzeug.datastructures import FileStorage
import tempfile
import re
import os
from pathlib import Path
import pytest
import json

from lib import sparql_query, read_json
from app import app, init

sparql = os.getenv('SPARQL', 'http://localhost:3033/n4o')

base = "https://graph.nfdi4objects.net/collection/"
terminology_graph = "https://graph.nfdi4objects.net/terminology/"

bartoc = read_json("tests/bartoc.json")

collection_1 = read_json("tests/collection/1.json")[0]
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


@pytest.fixture
def stage():
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir


@pytest.fixture
def client(stage):
    app.testing = True

    data = Path(__file__).parent
    init(title="N4O Graph Import API TEST",
         stage=stage, sparql=sparql, data=data)

    with app.test_client() as client:
        yield client


# TODO: use mocked_urls like below
def register_terminology(client, id):
    with responses.RequestsMock() as mock:
        uri = f"http://bartoc.org/en/node/{id}"
        json = next(([item] for item in bartoc if item["uri"] == uri), [])
        mock.get(f"https://bartoc.org/api/data?uri={uri}", json=json)
        res = client.put(f'/terminology/{id}')
        assert type(res.get_json()) is dict
        return res


mocked_urls = {
    "http://example.org/20533.concepts.ndjson": "tests/20533.concepts.ndjson"
}


def urlopen_from_cache(url):
    return open(mocked_urls[url], "rb")


def test_terminology(client):

    # Additional endpoints
    client.get('/data/').status_code == 200
    client.get('/status.json').status_code == 200

    # get unregisterd terminology
    assert client.get("/terminology/18274").status_code == 404

    # register terminology, get afterwards
    assert register_terminology(client, "18274").status_code == 200
    assert client.get("/terminology/18274").status_code == 200

    # try to register non-existing terminology
    assert register_terminology(client, "0").status_code == 404

    # get list of terminologies
    resp = client.get('/terminology/')
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1

    # get list terminology namespaces
    assert client.get("/terminology/namespaces.json").get_json() == {
        "http://bartoc.org/en/node/18274": "http://www.w3.org/2004/02/skos/core#"}

    # receive terminology data and check log
    assert client.get('/terminology/18274/receive').status_code == 404
    assert client.post('/terminology/18274/receive').status_code == 400
    assert client.post(
        '/terminology/18274/receive?from=abc').status_code == 400
    assert client.post(
        '/terminology/18274/receive?from=skos.rdf').status_code == 200
    assert client.get('/terminology/18274/receive').status_code == 200

    # load terminology data and check log
    assert client.get('/terminology/18274/load').status_code == 404
    assert client.post('/terminology/18274/load').status_code == 200
    assert client.get('/terminology/18274/load').status_code == 200

    # try to receive and load an unregistered terminology
    assert client.post(
        '/terminology/20533/receive?from=abc').status_code == 404
    assert client.post('/terminology/20533/load').status_code == 404

    # register, receive, and load another terminology
    assert register_terminology(client, "20533").status_code == 200
    assert client.post('/terminology/20533/load').status_code == 404
    assert client.post(
        '/terminology/20533/receive?from=20533.concepts.ndjson').status_code == 200
    assert client.post('/terminology/20533/load').status_code == 200

    with patch('urllib.request.urlopen', new=urlopen_from_cache):
        query = '/terminology/20533/receive?from=http://example.org/20533.concepts.ndjson'
        assert client.post(query).status_code == 200

    # check size of terminology graphs
    query = "SELECT ?g (count(*) as ?t) { GRAPH ?g {?s ?p ?o} } GROUP BY ?g ORDER BY ?t"
    graphs = [
        {'g': {'type': 'uri', 'value': 'https://graph.nfdi4objects.net/terminology/'},
         't': {'type': 'literal', 'datatype': 'http://www.w3.org/2001/XMLSchema#integer', 'value': '25'}},
        {'g': {'type': 'uri', 'value': 'http://bartoc.org/en/node/18274'},
         't': {'type': 'literal', 'datatype': 'http://www.w3.org/2001/XMLSchema#integer', 'value': '377'}},
        {'g': {'type': 'uri', 'value': 'http://bartoc.org/en/node/20533'},
         't': {'type': 'literal', 'datatype': 'http://www.w3.org/2001/XMLSchema#integer', 'value': '679'}}]

    assert sparql_query(sparql, query) == graphs

    assert client.post("/terminology/20533/remove").status_code == 200
    assert sparql_query(sparql, query) == graphs[:-1]

    # no problem when graph has already been removed
    assert client.post("/terminology/20533/remove").status_code == 200

    # but graph must be registered
    assert client.post("/terminology/1234/remove").status_code == 404


def test_api(client):

    # start without collections
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"N4O Graph Import API TEST" in resp.data

    resp = client.get('/collection')
    assert resp.status_code == 200
    assert resp.get_json() == []

    assert client.get('/collection/1').status_code == 404

    # add collection
    resp = client.put('/collection/', json={})
    assert resp.status_code == 400
    assert b"Expected list of collections" in resp.data

    assert client.put('/collection/', json=[collection_1]).status_code == 200

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

    # add without id in record
    resp = client.put('/collection/3', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json() == collection_3_full

    # add without known id
    resp = client.post('/collection/', json=collection_0)
    assert resp.status_code == 200  # TODO: should be 201 Created
    assert resp.get_json()["id"] == "4"

    # receive from file
    assert client.post(
        '/collection/1/receive?from=data.ttl').status_code == 200
    assert client.get('/collection/1/receive').status_code == 200

    # load received RDF
    assert client.post('/collection/1/load').status_code == 200
    assert client.get('/collection/1/load').status_code == 200

    uri = collection_1["uri"]
    query = f"SELECT * {{ GRAPH <{uri}> {{?s ?p ?o}} }} ORDER BY DESC(?s)"
    res = sparql_query(sparql, query)
    graph = [{'s': {'type': 'uri', 'value': 'https://example.org/x'},
              'p': {'type': 'uri', 'value': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'},
              'o': {'type': 'uri', 'value': 'http://www.cidoc-crm.org/cidoc-crm/E1_CRM_Entity'}},
             {'s': {'type': 'uri', 'value': 'http://www.cidoc-crm.org/cidoc-crm/E1_CRM_Entity'},
             'p': {'type': 'uri', 'value': 'https://example.org/foo'},
              'o': {'type': 'uri', 'value': 'https://example.org/bar'}}]
    assert res == graph

    # register terminology and receive + load again
    register_terminology(client, "1644")  # CIDOC-CRM
    client.post('/collection/1/receive?from=data.ttl')
    client.post('/collection/1/load')
    assert sparql_query(sparql, query) == graph[:1]

    # TODO: test file upload
    # with open("tests/data.ttl", "rb") as f:
    #    data = {"data.ttl":f}
    #    res = client.post('/collection/1/receive', data=data,
    #                  content_type='multipart/form-data')
    #    assert res.status_code == 200

    # assert client.post('/collection/1/load').status_code == 404
