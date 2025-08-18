from jsonschema import ValidationError  # noqa


class NotFound(Exception):
    pass


class NotAllowed(Exception):
    pass


class ServerError(Exception):
    pass
