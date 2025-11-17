from marshmallow import Schema, fields


class AcademiaSchema(Schema):
    id = fields.Int(dump_only=True)
    nombre = fields.Str(required=True, metadata={'example': 'Academia de Idiomas Central'})
    direccion = fields.Str(metadata={'example': 'Calle Mayor 123, 28013 Madrid'})
    telefono = fields.Str(metadata={'example': '+34 912 345 678'})
    nombre_contacto = fields.Str(metadata={'example': 'Juan Pérez García'})
    email_contacto = fields.Email(metadata={'example': 'contacto@academiaidiomas.es'})
    descripcion = fields.Str(metadata={'example': 'Academia especializada en preparación de exámenes oficiales de inglés, francés y alemán'})


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
            'example': 'Calle Mayor 123, 28013 Madrid'
        }
    )
    telefono = fields.Str(
        metadata={
            'description': 'Teléfono de contacto',
            'example': '+34 912 345 678'
        }
    )
    nombre_contacto = fields.Str(
        metadata={
            'description': 'Nombre de la persona de contacto',
            'example': 'Juan Pérez García'
        }
    )
    email_contacto = fields.Email(
        metadata={
            'description': 'Email de contacto de la academia',
            'example': 'contacto@academiaidiomas.es'
        }
    )
    descripcion = fields.Str(
        metadata={
            'description': 'Descripción de la academia y sus servicios',
            'example': 'Academia especializada en preparación de exámenes oficiales de inglés, francés y alemán'
        }
    )
