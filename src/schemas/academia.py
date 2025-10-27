from marshmallow import Schema, fields


class AcademiaSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str(required=True, metadata={'example': 'Academia de Idiomas Central'})
    direccion = fields.Str(metadata={'example': 'Calle Mayor 123, Madrid'})
    telefono = fields.Str(metadata={'example': '+34 912 345 678'})


class CreateAcademiaSchema(Schema):
    nombre = fields.Str(
        required=True,
        metadata={
            'description': 'Nombre de la academia',
            'example': 'Academia de Idiomas Central'
        }
    )
    direccion = fields.Str(
        metadata={
            'description': 'Dirección física de la academia',
            'example': 'Calle Mayor 123, Madrid'
        }
    )
    telefono = fields.Str(
        metadata={
            'description': 'Teléfono de contacto',
            'example': '+34 912 345 678'
        }
    )
