import json


def read_json(file):
    with open(file) as f:
        return json.load(f)


def write_json(file, data):
    with open(file, "w") as f:
        f.write(json.dumps(data, indent=4))
