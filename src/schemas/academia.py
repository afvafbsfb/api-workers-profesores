from marshmallow import Schema, fields


class AcademiaSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str(required=True)
    direccion = fields.Str()
    telefono = fields.Str()


class CreateAcademiaSchema(Schema):
    nombre = fields.Str(required=True)
    direccion = fields.Str()
    telefono = fields.Str()
