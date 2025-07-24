from flask import Flask, jsonify, request
from waitress import serve
from pathlib import Path
import argparse as AP
import subprocess
import csv
import requests

COLLECTION_SCHEMA = Path('collection-schema.json')
COLLECTIONS_DIR = Path('stage/collection')
COLLECTIONS_CVS = COLLECTIONS_DIR / 'collections.csv'
COLLECTIONS_TTL = COLLECTIONS_DIR / 'collections.ttl'
COLLECTIONS_JSON = COLLECTIONS_DIR / 'collections.json'
FIELD_NAMES = ['id', 'name', 'url', 'db', 'license', 'format', 'access']


def s_read(file: Path, **kw):
    """Open a file and apply a function"""
    func = kw.get('func', lambda f: f.read())
    if file.exists():
        with file.open(mode='r') as f:
            return func(f)
    return None


def load_csv_collections():
    '''Load collections from CSV file and return a list of dictionaries'''
    def read(fp): return [row for row in csv.DictReader(fp, delimiter=',', quotechar='|')]
    return s_read(COLLECTIONS_CVS, func=read)


def write_csv_collections(coll):
    """Write collections to CSV file."""
    def write(f):
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        for c in coll:
            writer.writerow(c)
    with COLLECTIONS_CVS.open('w', newline='') as f:
        write(f)


def add_csv_item(item, id):
    """Update collections with a new item."""
    item['id'] = str(id)  # Reset ID to the provided one
    items = load_csv_collections()
    items = list(filter(lambda x: x['id'] != item['id'], items))
    items.append(item)
    items.sort(key=lambda x: int(x['id']))
    write_csv_collections(items)
    return items


def load_collection_file(id):
    """Load a collection file by ID and return its content."""
    json_file = COLLECTIONS_DIR / str(id) / 'collection.json'
    return s_read(json_file)


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
    """Find the first item in a list that matches a predicate."""
    return next((x for x in lst if predicate(x)), None)


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
    '''Return collections in JSON or Turtle format based on the Accept header'''
    accept = request.headers.get('Accept', 'application/json')
    if accept == 'text/turtle':
        return collection_ttl()
    return collection_json()


@app.route('/collection/<int:id>.json', methods=['GET'])
def collection_id_json(id):
    '''Get collection by ID in JSON format'''
    if js_str := load_collection_file(id):
        return js_str, 200, {'Content-Type': 'text/json'}
    return jsonify(error="collection not found", id=id), 404


@app.route('/collection/<int:id>.ttl', methods=['GET'])
def collection_id_ttl(id):
    '''Get collection by ID in Turtle format'''
    host = 'https://graph.nfdi4objects.net'  # TODO: local_host
    return requests.get(f'{host}/collection/{id}').content, 200, {'Content-Type': 'text/turtle'}


def apply_csv():
    """Apply the new CSV file to the collections."""
    npm_cmd = '/usr/bin/npm run --silent -- '
    run_s = lambda cmd: subprocess.run(f'{npm_cmd}{cmd} ', shell=True, capture_output=True, text=True)
    run_s(f'csv2json < ./{COLLECTIONS_CVS} > ./{COLLECTIONS_JSON}')
    run_s(f'ajv validate -s collection-schema.json -d {COLLECTIONS_JSON}')
    run_s(f'jsonld2rdf -c collection-context.json {COLLECTIONS_JSON} > {COLLECTIONS_TTL}')


@app.route('/collection/<int:id>', methods=['PUT'])
def collection_id(id):
    '''Update collection by ID'''
    try:
        data = request.get_json()
        data_fixed = {k: v for k, v in data.items() if k in FIELD_NAMES}
        add_csv_item(data_fixed, id)
        apply_csv()
    except Exception as e:
        return jsonify(error=str(e)), 400
    return jsonify(message="Collection updated:", id=id), 200


@app.route('/collection/<int:id>/receive', methods=['POST'])
def collection_receive_id(id):
    '''Receive a collection by ID'''
    if other_src := request.args.get('from',None):
        fmt = request.args.get('format','')
        res = subprocess.run(f'./receive-collection {id} {other_src} {fmt}', shell=True, capture_output=True, text=True)
    else:
        res = subprocess.run(f'./receive-collection {id}', shell=True, capture_output=True, text=True)
    if res.stderr:
        return jsonify(error=res.stderr), 500
    return jsonify(message=f"receive {id} executed.", output=res.stdout, id=id), 200

@app.route('/collection/<int:id>/import', methods=['POST'])
def collection_import_id(id):
    '''Import a collection by ID'''
    res = subprocess.run(f'./import-collection {id}', shell=True, capture_output=True, text=True)
    if res.stderr:
        return jsonify(error=res.stderr), 500
    return jsonify(message=f"import {id} executed.", output=res.stdout, id=id), 200


if __name__ == '__main__':

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
