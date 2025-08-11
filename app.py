from flask import Flask, jsonify, request, make_response, render_template
from waitress import serve
from pathlib import Path
import argparse
import subprocess
import csv
import os
from SPARQLWrapper import SPARQLWrapper


COLLECTION_SCHEMA = Path('collection-schema.json')
COLLECTION_CTX = Path('collection-context.json')
COLLECTIONS_DIR = Path('stage/collection')
COLLECTIONS_CVS = COLLECTIONS_DIR / 'collections.csv'
COLLECTIONS_TTL = COLLECTIONS_DIR / 'collections.ttl'
COLLECTIONS_JSON = COLLECTIONS_DIR / 'collections.json'
FIELD_NAMES = ['id', 'name', 'url', 'db', 'license', 'format', 'access']


def s_read(file: Path, func=lambda f: f.read(), **kw):
    """Open a file and apply a function"""
    if file.exists():
        with file.open(mode='r') as f:
            return func(f)
    return None


def load_csv_collections(file_path=COLLECTIONS_CVS):
    '''Load collections from CSV file and return a list of dictionaries'''
    def func(fp): return [row for row in csv.DictReader(fp)]
    return s_read(file_path, func=func)


def write_csv_collections(coll, file_path=COLLECTIONS_CVS):
    """Write collections to CSV file."""
    def write(f):
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(coll)
    with file_path.open('w', newline='') as f:
        write(f)


def load_collection_file(id):
    """Load a collection file by ID and return its content."""
    json_file = COLLECTIONS_DIR / str(id) / 'collection.json'
    return s_read(json_file)


app = Flask(__name__)


@app.route('/', methods=['GET'])
def home():
    return render_template('index.html', name="N4O Graph Import API")


@app.route('/initCT', methods=['GET'])
def initCT():
    '''Initialize the collections directory and create necessary files'''
    res = subprocess.run(f'./init_ct.sh', shell=True,
                         capture_output=True, text=True)
    if res.stderr:
        return jsonify(error=res.stderr), 500,  {'Content-Type': 'text/json'}
    return res.stdout, 200,  {'Content-Type': 'text/plain'}


@app.route('/collection', methods=['GET'])
@app.route('/collection.json', methods=['GET'])
def collection_json():
    '''Get all collections in JSON format'''
    with open(COLLECTIONS_JSON, 'r') as f:
        res = f.read()
        err = "No JSON file found" if not res else None
    if res:
        return res, 200, {'Content-Type': 'text/json'}
    return jsonify(error=err), 500


@app.route('/collection/<int:id>.json', methods=['GET'])
def collection_id_json(id):
    '''Get collection by ID in JSON format'''
    if js_str := load_collection_file(id):
        return js_str, 200, {'Content-Type': 'text/json'}
    return jsonify(error="collection not found", id=id), 404


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
    npm_cmd = '/usr/bin/npm run --silent -- '
    def run_s(cmd): return subprocess.run(
        f'{npm_cmd}{cmd} ', shell=True, capture_output=True, text=True)
    run_s(f'csv2json < ./{COLLECTIONS_CVS} > ./{COLLECTIONS_JSON}')
    run_s(f'ajv validate -s {COLLECTION_SCHEMA} -d {COLLECTIONS_JSON}')
    run_s(
        f'jsonld2rdf -c {COLLECTION_CTX} {COLLECTIONS_JSON} > {COLLECTIONS_TTL}')


@app.route('/collection/<int:id>', methods=['PUT'])
def collection_id(id):
    '''Add/update a json item to the collection.'''
    try:
        data = request.get_json()
        data_fixed = {k: v for k, v in data.items() if k in FIELD_NAMES}
        add_csv_item(data_fixed, id)
        csv_to_json_ttl()
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(message="Collection updated:", id=id), 200


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
    if args.wsgi:
        serve(app, host="0.0.0.0", **opts)
    else:
        app.run(host="0.0.0.0", **opts)
