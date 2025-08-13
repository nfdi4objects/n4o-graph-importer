import unittest
import tempfile
import pytest
import json
from app import app, init

base = "https://graph.nfdi4objects.net/"
collection_1 = {
  "id": "1",
  "name": "test collection",
  "url": "https://example.org/",
  "uri": f"{base}collection/1"
}

@pytest.fixture
def stage():
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir

@pytest.fixture
def client(stage):
    app.testing = True
    app.config['TITLE'] = "N4O Graph Import API TEST"
    app.config['STAGE'] = stage
    app.config['BASE'] = base
    init()
    with app.test_client() as client:
        yield client

def test_home(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"N4O Graph Import API TEST" in resp.data

def test_empty_collection(client):
    resp = client.get('/collection')
    assert resp.status_code == 200
    assert resp.get_json() == []

    resp = client.get('/collection/1')
    assert resp.status_code == 404

def test_collection(client):
    resp = client.put('/collection/', json={})
    assert resp.status_code == 400
    assert b"Invalid collection metadata" in resp.data

    resp = client.put('/collection/', json=[collection_1])
    assert resp.status_code == 200

    resp = client.get('/collection/')
    assert resp.status_code == 200
    assert resp.get_json() == [collection_1]

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1

    resp = client.delete('/collection/1')
    assert resp.status_code == 200

    resp = client.get('/collection/1')
    assert resp.status_code == 404

    resp = client.put('/collection/1', json=collection_1)
    assert resp.status_code == 200  # TODO: should be 201 Created

    resp = client.get('/collection/1')
    assert resp.status_code == 200
    assert resp.get_json() == collection_1
