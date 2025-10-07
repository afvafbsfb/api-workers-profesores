from marshmallow import Schema, fields


class LoginRequestSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class LoginResponseSchema(Schema):
    name = fields.Str()
    role = fields.Str()
    tokens = fields.Dict()
