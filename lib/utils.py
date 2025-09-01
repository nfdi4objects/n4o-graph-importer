import json
from .errors import NotFound, ServerError


def read_json(file):
    try:
        with open(file) as f:
            return json.load(f)
    except Exception as e:
        raise NotFound(e)


def read_ndjson(file):
    try:
        with open(file) as file:
            return [json.loads(line) for line in file]
    except FileNotFoundError as e:
        raise NotFound(e)


def write_json(file, data):
    try:
        with open(file, "w") as f:
            f.write(json.dumps(data, indent=4))
    except Exception as e:
        raise ServerError(str(e))
