import json


def read_json(file):
    with open(file) as f:
        return json.load(f)

def read_ndjson(file):
    with open(file) as file:
        return [json.loads(line) for line in file]


def write_json(file, data):
    with open(file, "w") as f:
        f.write(json.dumps(data, indent=4))
