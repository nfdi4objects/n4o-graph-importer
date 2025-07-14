from flask import Flask, jsonify
from waitress import serve
import argparse as AP
import subprocess
import csv

collections_file = 'stage/collection/collections.csv'
collection_list = []


def load_collections():
    with open(collections_file) as csvfile:
        reader = csv.DictReader(csvfile, delimiter=',', quotechar='|')
        return [row for row in reader]
    return []


app = Flask(__name__, template_folder='templates',
            static_folder='static', static_url_path='/assets')

def run_subprocess(args,timeout=20):
    """Run a subprocess command and return the output."""
    try:
        res = subprocess.run(args, capture_output=True, text=True, check=True,timeout=timeout)
        return res.stdout, res.stderr
    except FileNotFoundError as exc:
        return None,f"Process failed because the executable could not be found.\n{exc}"
    except subprocess.CalledProcessError as exc:
        return exc.stdout, exc.stderr
    except subprocess.TimeoutExpired as exc:
        return None, f"Process timed out.\n{exc}"
    

@app.route('/')
def home():
    res,err =run_subprocess(['uname', '-a'])
    return jsonify(result=res, err=err)

@app.route('/collections')
def collections():
    return jsonify(collection_list)


def find_p(lst, p=lambda x: True):
    '''Find object in list by predicate'''
    return next((x for x in lst if p(x)), None)


@app.route('/download/<int:id>')
def download(id):
    hasId =  lambda x: x['id'] == str(id)
    if coll := find_p(collection_list,hasId):
        url = coll['url']
        return jsonify(url=url)
    return jsonify(error="Collection not found",id=id), 404


if __name__ == '__main__':
    collection_list = load_collections()
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
