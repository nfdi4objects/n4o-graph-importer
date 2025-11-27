import jsonschema
from pyoxigraph import NamedNode
import re

# Data Validation Error Format


class ValidationError(Exception):
    def __init__(self, message, position=None):
        super().__init__(message)
        self.position = position

    def to_dict(self):
        e = {"message": str(self)}
        if self.position:
            e["position"] = self.position
        return e

    def wrapInFile(self, file):
        message = f"{str(self)} in {file}"
        position = [{
            "dimension": "file",
            "address": file,
            "errors": [self.to_dict()]
        }]
        return ValidationError(message, position)

    def fromException(error):
        msg = str(error)
        pos = None
        if type(error) is SyntaxError and error.lineno:
            pos = {"line": error.lineno}
            if error.offset:
                pos["linecol"] = f"{error.lineno}:{error.offset}"
            # remove location from message
            msg = re.sub(f"^[^:]+line {error.lineno}[^:]*: ", "", msg)
            msg = re.sub(f"\\s*\\([^)]*line {error.lineno}[^)]*\\)$", "", msg)
        return ValidationError(msg, pos)


def validateJSON(data, schema):
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as err:
        pos = ""
        for elem in err.absolute_path:
            if isinstance(elem, int):
                pos += "/" + str(elem)
            else:
                pos += "/" + elem.replace("~", "~0").replace("/", "~1")
        pos = {"jsonpointer": pos}
        raise ValidationError(err.message, pos)


IRI = re.compile('^[a-z][a-z0-9+.-]*:[^<>"{}|^`\\\x00-\x20]*$', re.I)


def invalidIRI(node):
    return type(node) is NamedNode and not IRI.match(str(node.value))
