from jsonschema import ValidationError  # noqa


class ApiError(Exception):
    code = 400


class NotFound(ApiError):
    code = 404


class NotAllowed(ApiError):
    code = 403


class ServerError(ApiError):
    code = 500


class ClientError(ApiError):
    code = 400
