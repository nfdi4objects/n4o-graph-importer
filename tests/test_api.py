import unittest
import tempfile
import pytest
from app import app, init

@pytest.fixture
def stage():
    with tempfile.TemporaryDirectory() as tempdir:
        yield tempdir

@pytest.fixture
def client(stage):
    app.testing = True
    app.config['TITLE'] = "N4O Graph Import API TEST"
    app.config['STAGE'] = stage
    init()
    with app.test_client() as client:
        yield client

def test_home(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert b"N4O Graph Import API TEST" in resp.data

def test_collections(client):
    resp = client.get('/collection/')
    assert resp.status_code == 200
    assert resp.get_json() == []
