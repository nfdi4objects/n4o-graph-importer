from flask import Flask, jsonify, request, make_response, render_template
from waitress import serve
from pathlib import Path
from lib import read_json, write_json, CollectionRegistry, NotFound
import json
import argparse
import subprocess
import csv
import os
from shutil import rmtree
from SPARQLWrapper import SPARQLWrapper
from jsonschema import validate, ValidationError


app = Flask(__name__)
app.config['STAGE'] = os.getenv('STAGE', 'stage')
app.config['TITLE'] = os.getenv('TITLE', 'N4O Graph Importer')
app.config['SPARQL'] = os.getenv('SPARQL', 'http://localhost:3030/n4o')
app.config['SPARQL_UPDATE'] = os.getenv('SPARQL_UPDATE', app.config['SPARQL'])
app.config['SPARQL_STORE'] = os.getenv('SPARQL_STORE', app.config['SPARQL'])

FIELD_NAMES = ['id', 'name', 'url', 'db', 'license', 'format', 'access']


def stage():
    return Path(app.config['STAGE'])


def collections_file():
    return stage() / "collection" / "collections.json"


def load_collection_file(id):
    json_file = stage() / 'collection' / str(id) / 'collection.json'
    return s_read(json_file)


collectionRegistry = CollectionRegistry(app.config['STAGE'])


def init():
    global collectionRegistry
    collectionRegistry = CollectionRegistry(stage())
    (stage() / "terminology").mkdir(exist_ok=True)


def s_read(file: Path, func=lambda f: f.read(), **kw):
    """Open a file and apply a function"""
    if file.exists():
        with file.open(mode='r') as f:
            return func(f)
    return None


def load_csv_collections():
    '''Load collections from CSV file and return a list of dictionaries'''
    file_path = stage() / 'collection' / 'collections.csv'
    def func(fp): return [row for row in csv.DictReader(fp)]
    return s_read(file_path, func=func)


def write_csv_collections(coll):
    """Write collections to CSV file."""
    file_path = stage() / 'collection' / 'collections.csv'

    def write(f):
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(coll)
    with file_path.open('w', newline='') as f:
        write(f)


@app.route('/initCT', methods=['GET'])
def initCT():
    '''Initialize the collections directory and create necessary files'''
    res = subprocess.run(f'./init_ct.sh', shell=True,
                         capture_output=True, text=True)
    if res.stderr:
        return jsonify(error=res.stderr), 500,  {'Content-Type': 'application/json'}
    return res.stdout, 200,  {'Content-Type': 'text/plain'}


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', title=app.config['TITLE'])


@app.route('/collection', methods=['GET'])
@app.route('/collection/', methods=['GET'])
def collections():
    return jsonify(collectionRegistry.collections())


@app.route('/collection', methods=['PUT'])
@app.route('/collection/', methods=['PUT'])
def put_collections():
    try:
        data = request.get_json(force=True)
        return jsonify(collectionRegistry.set_all(data)), 200
    except ValidationError as e:
        return jsonify(error="Invalid collection metadata"), 400
    except Exception as e:
        return jsonify(error="Missing or malformed JSON body"), 400


@app.route('/collection/<int:id>', methods=['GET'])
def get_collection(id):
    try:
        return jsonify(collectionRegistry.get(id))
    except NotFound:
        return jsonify(error="collection {id} not found"), 404


@app.route('/collection/<int:id>', methods=['PUT'])
def put_collection(id):    
    try:
        return jsonify(collectionRegistry.set(id, request.get_json(force=True)))
    except NotFound:
        return jsonify(error="collection {id} not found"), 404
    except ValidationError as e:
        return jsonify(error="Invalid collection metadata"), 400
    except Exception as e:
        return jsonify(error="Missing or malformed JSON body"), 400


@app.route('/collection/<int:id>', methods=['DELETE'])
def delete_collection(id):
    try:
        data = read_json(collections_file())
        cur = next(c for c in data if c["id"] == str(id))
        data = [c for c in data if c["id"] != str(id)]
        write_json(collections_file(), data)
        rmtree(stage() / "collection" / str(id), ignore_errors=True)
        return jsonify(data)
    except StopIteration:
        return jsonify(error="collection {id} not found"), 404


def add_csv_item(item, id):
    """Update/add the collections with a new item."""
    item['id'] = str(id)  # Reset ID to the provided one
    items = load_csv_collections()
    items = list(filter(lambda x: x['id'] != item['id'], items))
    items.append(item)
    items.sort(key=lambda x: int(x['id']))
    write_csv_collections(items)
    return items


def csv_to_json_ttl():
    """Convert the current csv file to json and turtle files"""
    COLLECTIONS_CSV = stage() / 'collection' / 'collections.csv'
    COLLECTIONS_JSON = stage() / 'collection' / 'collections.json'
    COLLECTIONS_TTL = stage() / 'collection' / 'collections.ttl'

    npm_cmd = '/usr/bin/npm run --silent -- '
    def run_s(cmd): return subprocess.run(
        f'{npm_cmd}{cmd} ', shell=True, capture_output=True, text=True)
    run_s(f'csv2json < ./{COLLECTIONS_CVS} > ./{COLLECTIONS_JSON}')
    run_s(f'ajv validate -s collection-schema.json -d {COLLECTIONS_JSON}')
    run_s(
        f'jsonld2rdf -c collection-context.json {COLLECTIONS_JSON} > {COLLECTIONS_TTL}')


@app.route('/collection/<int:id>/receive', methods=['POST'])
def collection_receive_id(id):
    '''Receive the data of a collection entry by.'''
    cmds = ['./receive-collection', str(id)]
    if other_src := request.args.get('from', None):
        cmds.append(other_src)
        if fmt := request.args.get('format', None):
            cmds.append(fmt)
    response = subprocess.run(cmds, capture_output=True, text=True)
    if response.stderr:
        return jsonify(error=response.stderr), 500
    else:
        return jsonify(message=f"receive {id} executed.", output=response.stdout, id=id), 200


@app.route('/collection/<int:id>/import', methods=['POST'])
def collection_import_id(id):
    '''Import the data of an collection entry.'''
    response = subprocess.run(
        f'./import-collection {id}', shell=True, capture_output=True, text=True)
    if response.stderr:
        return jsonify(error=response.stderr), 500
    return jsonify(message=f"import {id} executed.", output=response.stdout, id=id), 200


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-w', '--wsgi', action=argparse.BooleanOptionalAction, help="Use WSGI server")
    parser.add_argument('-p', '--port', type=int,
                        default=5020, help="Server port")
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    opts = {"port": args.port}
    init()
    if args.wsgi:
        serve(app, host="0.0.0.0", **opts)
    else:
        app.run(host="0.0.0.0", **opts)
