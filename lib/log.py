import datetime
from .utils import read_json, write_json


class Log:
    def __init__(self, file, start=None):
        self.file = file
        self.items = []
        if start:
            self.append(start)

    def append(self, entry):
        self.items.append(f"{datetime.datetime.now()}: {entry}")

    def done(self, message="done"):
        self.append(message)
        write_json(self.file, self.items)
        return self.items

    def load(self):
        return read_json(self.file)
