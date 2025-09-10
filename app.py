from flask import Flask, jsonify, request, render_template, send_from_directory
from waitress import serve
from lib import CollectionRegistry, TerminologyRegistry, ApiError, NotFound, ValidationError, read_json
import argparse
import os
from pathlib import Path


app = Flask(__name__)
app.json.compact = False

collectionRegistry = None
terminologyRegistry = None


def init(**config):
    global collectionRegistry
    global terminologyRegistry

    title = config.get('title', os.getenv('TITLE', 'N4O Graph Importer'))

    if config.get("debug", False):
        app.debug = True
        title = f"{title} (debugging enabled)"

    app.config['title'] = title
    app.config['base'] = config.get('base', os.getenv(
        'BASE', 'https://graph.nfdi4objects.net/'))
    app.config['sparql'] = config.get(
        'sparql', os.getenv('SPARQL', 'http://localhost:3030/n4o'))
    app.config['stage'] = config.get('stage', os.getenv('STAGE', 'stage'))
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
    return jsonify(terminologyRegistry.register_all(data))


@app.route('/terminology/namespaces.json', methods=['GET'])
def terminology_namspeaces():
    return jsonify(terminologyRegistry.namespaces())


@app.route('/terminology/<int:id>', methods=['GET'])
def get_terminology(id):
    return jsonify(terminologyRegistry.get(id))


@app.route('/terminology/<int:id>', methods=['PUT'])
def register_terminology(id):
    bartoc = Path(app.config["data"]) / 'bartoc.json'
    cache = read_json(bartoc) if bartoc.is_file() else None
    return jsonify(terminologyRegistry.register(id, cache))


@app.route('/terminology/<int:id>', methods=['DELETE'])
def delete_terminology(id):
    return jsonify(terminologyRegistry.delete(id))


@app.route('/terminology/<int:id>/receive', methods=['POST'])
def receive_terminology(id):
    source = request.args.get('from', None)
    return jsonify(terminologyRegistry.receive(id, source))


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
    return jsonify(collectionRegistry.list())


@app.route('/collection/schema.json', methods=['GET'])
def collection_schema():
    return jsonify(read_json("collection-schema.json"))


@app.route('/collection/', methods=['PUT', 'POST'])
def put_post_collections():
    data = request.get_json(force=True)
    if request.method == "PUT":
        return jsonify(collectionRegistry.register_all(data)), 200
    else:
        return jsonify(collectionRegistry.register(data)), 200


@app.route('/collection/<int:id>', methods=['GET'])
def get_collection(id):
    return jsonify(collectionRegistry.get(id))


@app.route('/collection/<int:id>', methods=['PUT'])
def put_collection(id):
    data = request.get_json(force=True)
    return jsonify(collectionRegistry.register(data, id))


@app.route('/collection/<int:id>', methods=['DELETE'])
def delete_collection(id):
    return jsonify(collectionRegistry.delete(id))


@app.route('/collection/<int:id>/receive', methods=['POST'])
def collection_receive_id(id):
    namespaces = terminologyRegistry.namespaces()
    return jsonify(collectionRegistry.receive(id, request.args.get("from", None), namespaces))


@app.route('/collection/<int:id>/receive', methods=['GET'])
def receive_collection_log(id):
    return jsonify(collectionRegistry.receive_log(id))


@app.route('/collection/<int:id>/load', methods=['POST'])
def load_collection(id):
    return jsonify(collectionRegistry.load(id))


@app.route('/collection/<int:id>/load', methods=['GET'])
def load_collection_log(id):
    return jsonify(collectionRegistry.load_log(id))


@app.route('/collection/<int:id>/remove', methods=['POST'])
def remove_collection(id):
    return jsonify(collectionRegistry.remove(id))


def serve_dir(dir, template, root, filename=None, id=None):
    if filename:
        file = dir / filename
        if "/" in filename or not file.is_file():
            raise NotFound("File not found!")
        return send_from_directory(dir, filename)
    else:
        files = [f.name for f in dir.iterdir() if f.is_file()
                 ] if dir.is_dir() else []
        return render_template(template, root=root, files=files, **app.config, id=id)


@app.route('/terminology/<int:id>/stage/')
@app.route('/terminology/<int:id>/stage/<filename>')
def terminology_stage(id, filename=None):
    dir = Path(app.config["stage"]) / "terminology" / str(id)
    return serve_dir(dir, "terminology-stage.html", "../../../", filename, id)


@app.route('/collection/<int:id>/stage/')
@app.route('/collection/<int:id>/stage/<filename>')
def collection_stage(id, filename=None):
    dir = Path(app.config["stage"]) / "collection" / str(id)
    return serve_dir(dir, "collection-stage.html", "../../../", filename, id)


@app.route('/data/')
@app.route('/data/<filename>')
def data_directory(filename=None):
    return serve_dir(Path(app.config["data"]), "data.html", "../", filename)


@app.route('/status.json')
def get_status():
    status = {key: str(val) for key, val in app.config.items()}
    # TODO: add status of triple store (try to connect)
    return jsonify(status)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-w', '--wsgi', action=argparse.BooleanOptionalAction, help="Use WSGI server")
    parser.add_argument('-p', '--port', type=int, default=5020)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    init(debug=args.debug)
    if args.wsgi:
        print(f"Starting WSGI server at http://localhost:{args.port}/")
        serve(app, host="0.0.0.0", port=args.port, threads=8)
    else:
        app.run(host="0.0.0.0", port=args.port, debug=args.debug)
