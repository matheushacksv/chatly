from ninja.schema import Schema

class GenericErrorSchema(Schema):
    detail: str

class ErrorWithCodeSchema(Schema):
    detail: str
    code: str

