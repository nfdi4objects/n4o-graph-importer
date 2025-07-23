from flask import Flask, jsonify, request
from waitress import serve
from jsonschema import validate
from pathlib import Path
import argparse as AP
import subprocess
import csv
import json
import requests


COLLECTIONS_DIR = Path('stage/collection')
COLLECTIONS_CVS = COLLECTIONS_DIR / 'collections.csv'
COLLECTIONS_TTL = COLLECTIONS_DIR / 'collections.ttl'
COLLECTIONS_JSON = COLLECTIONS_DIR / 'collections.json'

collection_info_list = []


def load_collections():
    if COLLECTIONS_CVS.exists():
        with COLLECTIONS_CVS.open() as f:
            dr = csv.DictReader(f, delimiter=',', quotechar='|')
            return [row for row in dr]
    return []


def load_collection_file(id):
    json_file = COLLECTIONS_DIR / str(id) / 'collection.json'
    if json_file.exists():
        with json_file.open() as f:
            return f.read()


def run_subprocess(args, timeout=20):
    """Run a subprocess command and return the output."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True, timeout=timeout)
        return res.stdout, res.stderr
    except FileNotFoundError as exc:
        return None, f"Process failed because the executable could not be found.\n{exc}"
    except subprocess.CalledProcessError as exc:
        return exc.stdout, exc.stderr
    except subprocess.TimeoutExpired as exc:
        return None, f"Process timed out.\n{exc}"


def preciate_find(lst, predicate=lambda x: True):
    return next((x for x in lst if predicate(x)), None)


def get_collection_id(id):
    '''Get collection by ID'''
    if collection_info := preciate_find(collection_info_list, lambda x: int(x['id']) == id):
        return collection_info
    return None


app = Flask(__name__, template_folder='templates',
            static_folder='static', static_url_path='/assets')


@app.route('/', methods=['GET'])
def home():
    '''Home page'''
    return jsonify(message="Welcome to the N4O REST API!")


@app.route('/ping', methods=['GET'])
def ping():
    '''Ping endpoint to check the server status'''
    res, err = run_subprocess(['uname', '-a'])
    return jsonify(result=res, err=err)


@app.route('/collection.json', methods=['GET'])
def collection_json():
    '''Get all collections in JSON format'''
    with open(COLLECTIONS_JSON, 'r') as f:
        res = f.read()
        err = "No JSON file found" if not res else None
    if res:
        return res, 200, {'Content-Type': 'text/json'}
    return jsonify(error=err), 500


@app.route('/collection.ttl', methods=['GET'])
def collection_ttl():
    '''Get all collections in Turtle format'''
    with open(COLLECTIONS_TTL, 'r') as f:
        res = f.read()
        err = "No Turtle file found" if not res else None
    if res:
        return res, 200, {'Content-Type': 'text/turtle'}
    return jsonify(error=err), 500


@app.route('/collection', methods=['GET'])
@app.route('/collection/', methods=['GET'])
def collection():
    accept = request.headers.get('Accept', 'application/json')
    if accept == 'text/turtle':
        return collection_ttl()
    return collection_json()


def add_collection(data):
    '''Add a new collection'''
    if not COLLECTIONS_CVS.exists():
        with COLLECTIONS_CVS.open('w', newline='') as csvfile:
            fieldnames = ['id', 'name', 'url', 'db', 'license', 'format', 'access']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    with COLLECTIONS_CVS.open('a', newline='') as csvfile:
        fieldnames = ['id', 'name', 'url', 'db', 'license', 'format', 'access']
        print(data)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writerow(data)


@app.route('/collection/<int:id>.json', methods=['GET'])
def collection_id_json(id):
    '''Get collection file by ID '''
    if js_str := load_collection_file(id):
        return js_str, 200, {'Content-Type': 'text/json'}
    return jsonify(error="collection not found", id=id), 404


@app.route('/collection/<int:id>.ttl', methods=['GET'])
def collection_id_ttl(id):
    host = 'https://graph.nfdi4objects.net'  # TODO: local_host
    return requests.get(f'{host}/collection/{id}').content, 200, {'Content-Type': 'text/turtle'}


@app.route('/collection/<int:id>', methods=['PUT'])
def collection_id(id):
    '''Update collection by ID'''
    data = request.get_json()
    with open('collection-schema.json', 'r') as f:
        st = json.load(f)
    try:
        validate(instance=data, schema=st)
        add_collection(data)
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(message="Collection updated:", id=id, data=data), 200


if __name__ == '__main__':
    collection_info_list = load_collections()
    parser = AP.ArgumentParser()
    parser.add_argument(
        '-w', '--wsgi', action=AP.BooleanOptionalAction, help="Use WSGI server")
    parser.add_argument('-p', '--port', type=int,
                        default=5020, help="Server port")
    args = parser.parse_args()
    opts = {"port": args.port}
    if args.wsgi:
        serve(app, host="0.0.0.0", **opts)
    else:
        app.run(host="0.0.0.0", **opts)
