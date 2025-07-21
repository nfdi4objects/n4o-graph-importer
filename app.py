from flask import Flask, jsonify
from waitress import serve
import argparse as AP
import subprocess
import csv
from pathlib import Path    

collections_file = 'stage/collection/collections.csv'
collection_info_list = []


def load_collections():
    p = Path(collections_file)
    if p.exists():
        with p.open() as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
            return [row for row in reader]
    return []


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

def get_collection_info(id):
    '''Get collection by ID'''
    if collection_info := preciate_find(collection_info_list, lambda x: int(x['id']) == id):
        return collection_info
    return None

app = Flask(__name__, template_folder='templates',
            static_folder='static', static_url_path='/assets')


@app.route('/')
def home():
    '''Home page'''
    return jsonify(message="Welcome to the N4O REST API!")


@app.route('/ping')
def ping():
    '''Ping endpoint to check the server status'''
    res, err = run_subprocess(['uname', '-a'])
    return jsonify(result=res, err=err)

@app.route('/collection_info', defaults={'id': None})
@app.route('/collection_info/<int:id>')
def collection_info(id):
    '''Get collection information by ID or list all collections if no ID is provided'''
    if not id:
        return jsonify(collection_info_list)
    if coll := get_collection_info(id):
        return jsonify(coll)
    return jsonify(error="collection not found", id=id), 404


@app.route('/import_collection/<int:id>')
def import_collection(id):
    '''Import a collection by ID'''
    if coll := get_collection_info(id):
        url = coll['url']
        return jsonify(url=url)
    return jsonify(error="Collection not found", id=id), 404


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
