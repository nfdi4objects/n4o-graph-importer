from flask import Flask, jsonify, request, render_template
from waitress import serve
from lib import CollectionRegistry, TerminologyRegistry, NotFound, NotAllowed, ValidationError, ServerError
import argparse
import subprocess
import os


app = Flask(__name__)

collectionRegistry = None
terminologyRegistry = None

# TODO: catch ServerError and return 500 response (e.g. backend not available)


def init(**config):
    global collectionRegistry
    global terminologyRegistry

    # TODO: move to __main__?
    app.config['title'] = config.get(
        'title', os.getenv('TITLE', 'N4O Graph Importer'))
    app.config['stage'] = config.get('stage', os.getenv('STAGE', 'stage'))
    app.config['sparql'] = config.get(
        'sparql', os.getenv('SPARQL', 'http://localhost:3030/n4o'))

    collectionRegistry = CollectionRegistry(**app.config)
    terminologyRegistry = TerminologyRegistry(**app.config)


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', **app.config)


@app.route('/collection', methods=['GET'])
@app.route('/collection/', methods=['GET'])
def collections():
    return jsonify(collectionRegistry.collections())


@app.route('/collection', methods=['PUT', 'POST'])
@app.route('/collection/', methods=['PUT', 'POST'])
def put_post_collections():
    try:
        data = request.get_json(force=True)
        if request.method == "PUT":
            return jsonify(collectionRegistry.set_all(data)), 200
        else:
            return jsonify(collectionRegistry.add(data)), 200
    except ValidationError as e:
        return jsonify(error=f"Invalid collection metadata: {e}"), 400
    except NotAllowed:
        return jsonify(error="Not allowed"), 403
    except Exception as e:
        return jsonify(error=f"Missing or malformed JSON body: {e}"), 400


@app.route('/collection/<int:id>', methods=['GET'])
def get_collection(id):
    try:
        return jsonify(collectionRegistry.get(id))
    except NotFound:
        return jsonify(error="collection {id} not found"), 404


@app.route('/collection/<int:id>', methods=['PUT'])
def put_collection(id):
    try:
        col = collectionRegistry.set(id, request.get_json(force=True))
        return jsonify(col)
    # except NotFound:
    #    return jsonify(error="collection {id} not found"), 404
    except ValidationError as e:
        return jsonify(error=f"Invalid collection metadata: {e}"), 400
    except Exception as e:
        return jsonify(error=f"Missing or malformed JSON body: {e}"), 400


@app.route('/collection/<int:id>', methods=['DELETE'])
def delete_collection(id):
    try:
        return jsonify(collectionRegistry.delete(id))
    except NotFound:
        return jsonify(error="collection {id} not found"), 404


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


@app.route('/terminology', methods=['GET'])
@app.route('/terminology/', methods=['GET'])
def terminologies():
    return jsonify(terminologyRegistry.list())


@app.route('/terminology/<int:id>', methods=['PUT'])
def put_terminology(id):
    return jsonify(terminologyRegistry.add(id))


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
