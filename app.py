from flask import Flask, jsonify, request, render_template, send_from_directory
from waitress import serve
from lib import CollectionRegistry, TerminologyRegistry, MappingRegistry, ApiError, NotFound, ValidationError, read_json
import argparse
import os
from pathlib import Path


app = Flask(__name__)
app.json.compact = False

collections = None
terminologies = None
mappings = None


def init(**config):
    global collections
    global terminologies
    global mappings

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

    collections = CollectionRegistry(**app.config)
    terminologies = TerminologyRegistry(**app.config)
    mappings = MappingRegistry(**app.config)


@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify(error=f"Invalid data: {e}"), 400


@app.errorhandler(ApiError)
def handle_error(e):
    return jsonify(error=str(e)), type(e).code


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', **app.config)


def route(method, path, fn):
    f = lambda *args, **kwargs: jsonify(fn(*args, **kwargs))
    f.__name__ = f'{method}-{path}'
    app.add_url_rule(path, methods=[method], view_func=f)


route('GET', '/terminology/', lambda: terminologies.list())
route('GET', '/terminology/namespaces.json', lambda: terminologies.namespaces())
route('PUT', '/terminology/', lambda: terminologies.replace(request.get_json(force=True)))
route('GET', '/terminology/<int:id>', lambda id: terminologies.get(id))
route('DELETE', '/terminology/<int:id>', lambda id: terminologies.delete(id))
route('GET', '/terminology/<int:id>/receive', lambda id: terminologies.receive_log(id))
route('GET', '/terminology/<int:id>/load', lambda id: terminologies.load_log(id))
route('POST', '/terminology/<int:id>/load', lambda id: terminologies.load(id))
route('POST', '/terminology/<int:id>/remove', lambda id: terminologies.remove(id))

route('GET', '/collection/', lambda: collections.list())
route('GET', '/collection/schema.json', lambda: collections.schema)
route('PUT', '/collection/', lambda: collections.replace(request.get_json(force=True)))
route('POST', '/collection/', lambda: collections.register(request.get_json(force=True)))
route('GET', '/collection/<int:id>', lambda id: collections.get(id))
route('PUT', '/collection/<int:id>', lambda id: collections.register(request.get_json(force=True), id))
route('DELETE', '/collection/<int:id>', lambda id: collections.delete(id))
route('GET', '/collection/<int:id>/receive', lambda id: collections.receive_log(id))
route('POST', '/collection/<int:id>/load', lambda id: collections.load(id))
route('GET', '/collection/<int:id>/load', lambda id: collections.load_log(id))
route('POST', '/collection/<int:id>/remove', lambda id: collections.remove(id))

# TODO: mapping registry
route('GET', '/mappings/', lambda: mappings.list())
route('GET', '/mappings/schema.json', lambda: mappingss.schema)
route('PUT', '/mappings/', lambda: mappings.replace(request.get_json(force=True)))
route('GET', '/mappings/<int:id>', lambda id: mappings.get(id))
route('POST', '/mappings/', lambda: mappings.register(request.get_json(force=True)))
route('DELETE', '/mappings/<int:id>', lambda id: mappings.delete(id))
route('GET', '/mappings/<int:id>/receive', lambda id: mappings.receive_log(id))
# TODO: load and remove
# TODO: add individual mappings


@app.route('/status.json')
def get_status():
    status = {key: str(val) for key, val in app.config.items()}
    # TODO: add status of triple store (try to connect)
    return jsonify(status)


@app.route('/terminology/<int:id>', methods=['PUT'])
def register_terminology(id):
    bartoc = Path(app.config["data"]) / 'bartoc.json'
    cache = read_json(bartoc) if bartoc.is_file() else None
    return jsonify(terminologies.register(id, cache))


@app.route('/terminology/<int:id>/receive', methods=['POST'])
def receive_terminology(id):
    source = request.args.get('from', None)
    return jsonify(terminologies.receive(id, source))


@app.route('/collection/<int:id>/receive', methods=['POST'])
def collection_receive_id(id):
    namespaces = terminologies.namespaces()
    return jsonify(collections.receive(id, request.args.get("from", None), namespaces))


def stage(kind, id, filename):
    dir = Path(app.config["stage"]) / kind / str(id)
    print(dir)
    if dir.is_dir():
        return serve_dir(dir, f"{kind}-stage.html", "../../../", filename, id)
    else:
        raise NotFound(f"{kind} {id} not found!")


@app.route('/terminology/<int:id>/stage/')
@app.route('/terminology/<int:id>/stage/<filename>')
def terminology_stage(id, filename=None):
    return stage("terminology", id, filename)


@app.route('/collection/<int:id>/stage/')
@app.route('/collection/<int:id>/stage/<filename>')
def collection_stage(id, filename=None):
    return stage("collection", id, filename)


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


@app.route('/data/')
@app.route('/data/<filename>')
def data_directory(filename=None):
    return serve_dir(Path(app.config["data"]), "data.html", "../", filename)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-w', '--wsgi', action=argparse.BooleanOptionalAction, help="Use WSGI")
    parser.add_argument('-p', '--port', type=int, default=5020)
    parser.add_argument('-d', '--debug', action=argparse.BooleanOptionalAction)
    args = parser.parse_args()
    init(debug=args.debug)
    if args.wsgi:
        print(f"Starting WSGI server at http://localhost:{args.port}/")
        serve(app, host="0.0.0.0", port=args.port, threads=8)
    else:
        app.run(host="0.0.0.0", port=args.port, debug=args.debug)
