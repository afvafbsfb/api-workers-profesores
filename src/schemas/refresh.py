from marshmallow import Schema, fields


class RefreshRequestSchema(Schema):
    # marshmallow Field does not accept `description` in older versions; keep minimal args
    refresh_token = fields.Str(required=True)
