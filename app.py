from flask import Flask, jsonify, request, render_template
from waitress import serve
from lib import CollectionRegistry, TerminologyRegistry, ApiError, ValidationError, read_json
import argparse
import subprocess
import os


app = Flask(__name__)
app.json.compact = False

collectionRegistry = None
terminologyRegistry = None


def init(**config):
    global collectionRegistry
    global terminologyRegistry

    # TODO: move to __main__?
    app.config['title'] = config.get(
        'title', os.getenv('TITLE', 'N4O Graph Importer'))
    app.config['stage'] = config.get('stage', os.getenv('STAGE', 'stage'))
    app.config['sparql'] = config.get(
        'sparql', os.getenv('SPARQL', 'http://localhost:3030/n4o'))
    app.config['data'] = config.get('data', os.getenv('DATA', 'data'))

    collectionRegistry = CollectionRegistry(**app.config)
    terminologyRegistry = TerminologyRegistry(**app.config)


@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify(error=f"Invalid data: {e}"), 400


@app.errorhandler(ApiError)
def handle_error(e):
    return jsonify(error=str(e)), type(e).code


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', **app.config)


@app.route('/terminology', methods=['GET'])
@app.route('/terminology/', methods=['GET'])
def terminologies():
    return jsonify(terminologyRegistry.list())


@app.route('/terminology/', methods=['PUT'])
def register_terminologies():
    data = request.get_json(force=True)
    return jsonify(terminologyRegistry.registerAll(data))


@app.route('/terminology/namespaces.json', methods=['GET'])
def terminology_namspeaces():
    return jsonify(terminologyRegistry.namespaces())


@app.route('/terminology/<int:id>', methods=['GET'])
def get_terminology(id):
    return jsonify(terminologyRegistry.get(id))


@app.route('/terminology/<int:id>', methods=['PUT'])
def register_terminology(id):
    return jsonify(terminologyRegistry.add(id))


@app.route('/terminology/<int:id>/receive', methods=['POST'])
def receive_terminology(id):
    return jsonify(terminologyRegistry.receive(id, request.args.get('from', None)))


@app.route('/terminology/<int:id>/receive', methods=['GET'])
def receive_terminology_log(id):
    return jsonify(terminologyRegistry.receive_log(id))


@app.route('/terminology/<int:id>/load', methods=['POST'])
def load_terminology(id):
    return jsonify(terminologyRegistry.load(id))


@app.route('/terminology/<int:id>/load', methods=['GET'])
def load_terminology_log(id):
    return jsonify(terminologyRegistry.load_log(id))


@app.route('/terminology/<int:id>/remove', methods=['POST'])
def remove_terminology(id):
    return jsonify(terminologyRegistry.remove(id))


@app.route('/collection', methods=['GET'])
@app.route('/collection/', methods=['GET'])
def collections():
    return jsonify(collectionRegistry.collections())


@app.route('/collection/schema.json', methods=['GET'])
def collection_schema():
    return jsonify(read_json("collection-schema.json"))


@app.route('/collection', methods=['PUT', 'POST'])
@app.route('/collection/', methods=['PUT', 'POST'])
def put_post_collections():
    data = request.get_json(force=True)
    if request.method == "PUT":
        return jsonify(collectionRegistry.set_all(data)), 200
    else:
        return jsonify(collectionRegistry.add(data)), 200


@app.route('/collection/<int:id>', methods=['GET'])
def get_collection(id):
    return jsonify(collectionRegistry.get(id))


@app.route('/collection/<int:id>', methods=['PUT'])
def put_collection(id):
    return jsonify(collectionRegistry.set(id, request.get_json(force=True)))


@app.route('/collection/<int:id>', methods=['DELETE'])
def delete_collection(id):
    return jsonify(collectionRegistry.delete(id))


@app.route('/collection/<int:id>/receive', methods=['POST'])
def collection_receive_id(id):
    return jsonify(collectionRegistry.receive(id, request.args.get("from", None)))


@app.route('/collection/<int:id>/receive', methods=['GET'])
def receive_collection_log(id):
    return jsonify(collectionRegistry.receive_log(id))


@app.route('/collection/<int:id>/load', methods=['POST'])
def load_collection(id):
    return jsonify(collectionRegistry.load(id))


@app.route('/collection/<int:id>/load', methods=['GET'])
def load_collection_log(id):
    return jsonify(collectionRegistry.load_log(id))


@app.route('/terminology/<int:id>/remove', methods=['POST'])
def remove_collection(id):
    return jsonify(collectionRegistry.remove(id))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-w', '--wsgi', action=argparse.BooleanOptionalAction, help="Use WSGI server")
    parser.add_argument('-p', '--port', type=int, default=5020)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    init()
    if args.wsgi:
        print(f"Starting WSGI server at http://localhost:{args.port}/")
        serve(app, host="0.0.0.0", port=args.port, threads=8)
    else:
        app.run(host="0.0.0.0", port=args.port, debug=args.debug)
