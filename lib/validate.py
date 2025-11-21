import jsonschema

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
