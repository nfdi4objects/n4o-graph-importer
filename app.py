from flask import Flask, jsonify, request, render_template, send_from_directory
from waitress import serve
from lib import CollectionRegistry, TerminologyRegistry, MappingRegistry, ApiError, NotFound, ValidationError, TripleStore
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
    global sparql

    title = config.get('title', os.getenv('TITLE', 'N4O Graph Importer'))

    if config.get("debug", False):
        app.debug = True
        title = f"{title} (debugging mode)"

    app.config['title'] = title
    app.config['base'] = config.get('base', os.getenv(
        'BASE', 'https://graph.nfdi4objects.net/'))
    app.config['frontend'] = config.get('frontend', os.getenv(
        'FRONTEND', app.config['base']))
    app.config['sparql'] = config.get(
        'sparql', os.getenv('SPARQL', 'http://localhost:3030/n4o'))
    app.config['stage'] = config.get('stage', os.getenv('STAGE', 'stage'))
    app.config['data'] = config.get('data', os.getenv('DATA', 'data'))

    terminologies = TerminologyRegistry(**app.config)
    collections = CollectionRegistry(**app.config, terminologies=terminologies)
    mappings = MappingRegistry(**app.config)


@app.errorhandler(ValidationError)
def handle_validation_error(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(ApiError)
def handle_error(e):
    return jsonify(error=str(e)), type(e).code


def route(method, path, fn):
    fn.__name__ = f'{method}-{path}'
    app.add_url_rule(path, methods=[method], view_func=fn)


def api(method, path, fn):
    route(method, path, lambda *args, **kws: jsonify(fn(*args, **kws)))


route('GET', '/', lambda: render_template('index.html', **app.config))


def status():
    values = {key: str(val) for key, val in app.config.items() if key.islower()}
    try:
        sparql = TripleStore(app.config['sparql'])
        values['connected'] = sparql.insert(app.config['base']+'collection/', '')
    except Exception as e:
        values['connected'] = False
    return values


api('GET', '/status.json', status)

api('GET', '/terminology/', lambda: terminologies.list())
api('GET', '/terminology/namespaces.json', lambda: terminologies.namespaces())
api('PUT', '/terminology/', lambda: terminologies.replace(request.get_json(force=True)))
api('GET', '/terminology/<int:id>', lambda id: terminologies.get(id))
api('PUT', '/terminology/<int:id>', lambda id: terminologies.register({"id": str(id)}))
api('DELETE', '/terminology/<int:id>', lambda id: terminologies.delete(id))
api('POST', '/terminology/<int:id>/receive',
    lambda id: terminologies.receive(id, request.args.get('from', None)))
api('GET', '/terminology/<int:id>/receive', lambda id: terminologies.receive_log(id))
api('GET', '/terminology/<int:id>/load', lambda id: terminologies.load_log(id))
api('POST', '/terminology/<int:id>/load', lambda id: terminologies.load(id))
api('POST', '/terminology/<int:id>/remove', lambda id: terminologies.remove(id))

api('GET', '/collection/', lambda: collections.list())
api('GET', '/collection/schema.json', lambda: collections.schema)
api('PUT', '/collection/', lambda: collections.replace(request.get_json(force=True)))
api('POST', '/collection/', lambda: collections.register(request.get_json(force=True)))
api('GET', '/collection/<int:id>', lambda id: collections.get(id))
api('PUT', '/collection/<int:id>',
    lambda id: collections.register(request.get_json(force=True), id))
api('DELETE', '/collection/<int:id>', lambda id: collections.delete(id))
api('POST', '/collection/<int:id>/receive',
    lambda id: collections.receive(id, request.args.get("from", None)))
api('GET', '/collection/<int:id>/receive', lambda id: collections.receive_log(id))
api('POST', '/collection/<int:id>/load', lambda id: collections.load(id))
api('GET', '/collection/<int:id>/load', lambda id: collections.load_log(id))
api('POST', '/collection/<int:id>/remove', lambda id: collections.remove(id))

api('GET', '/mappings/', lambda: mappings.list())
api('GET', '/mappings/schema.json', lambda: mappings.schema)
api('GET', '/mappings/properties.json', lambda: mappings.properties)
api('PUT', '/mappings/', lambda: mappings.replace(request.get_json(force=True)))
api('POST', '/mappings/', lambda: mappings.register(request.get_json(force=True)))
api('GET', '/mappings/<int:id>', lambda id: mappings.get(id))
api('PUT', '/mappings/<int:id>', lambda id: mappings.register(request.get_json(force=True), id))
api('DELETE', '/mappings/<int:id>', lambda id: mappings.delete(id))
api('POST', '/mappings/<int:id>/append', lambda: mappings.append(id, request.get_json(force=True)))
api('POST', '/mappings/<int:id>/detach', lambda: mappings.detach(id, request.get_json(force=True)))
api('POST', '/mappings/<int:id>/receive',
    lambda id: mappings.receive(id, request.args.get("from", None)))
api('GET', '/mappings/<int:id>/receive', lambda id: mappings.receive_log(id))
api('POST', '/mappings/<int:id>/load', lambda id: mappings.load(id))
api('GET', '/mappings/<int:id>/load', lambda id: mappings.load_log(id))
api('POST', '/mappings/<int:id>/remove', lambda id: mappings.remove(id))


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


def stage(kind, id, filename=None):
    dir = Path(app.config["stage"]) / kind / str(id)
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


@app.route('/mappings/<int:id>/stage/')
@app.route('/mappings/<int:id>/stage/<filename>')
def mappings_stage(id, filename=None):
    return stage("mappings", id, filename)


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
