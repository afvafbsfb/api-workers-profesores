"""Schema Marshmallow para Tarifa."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema


class TarifaSchema(Schema):
    """Schema para serialización/deserialización de Tarifa."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(required=True, metadata={'example': 1})
    descripcion = fields.Str(
        required=True,
        allow_none=False,
        metadata={'example': 'Tarifa mensual básica'}
    )
    precio_base = fields.Float(required=True, metadata={'example': 50.0})
    fecha_alta = fields.DateTime(dump_only=True, metadata={'example': '2025-10-27T10:30:00'})
    fecha_baja = fields.DateTime(dump_only=True, allow_none=True, metadata={'example': None})
    fecha_ultima_modificacion = fields.DateTime(dump_only=True, metadata={'example': '2025-10-27T10:30:00'})

    @validates('descripcion')
    def validate_descripcion(self, value, **kwargs):
        """Descripción no puede ser vacía."""
        if not value or not value.strip():
            raise ValidationError('La descripción no puede estar vacía.')

    @validates('precio_base')
    def validate_precio_base(self, value, **kwargs):
        """Precio base debe ser mayor que 0."""
        if value is None or value <= 0:
            raise ValidationError('El precio_base debe ser mayor que 0.')


class TarifaCreateSchema(Schema):
    """Schema para creación de Tarifa (POST)."""
    
    academia_id = fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'ID de la academia (obligatorio para admin_plataforma, opcional para admin_academia)',
            'example': 1
        }
    )
    descripcion = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Descripción de la tarifa',
            'example': 'Tarifa mensual básica'
        }
    )
    precio_base = fields.Float(
        required=True,
        metadata={
            'description': 'Precio base de la tarifa (debe ser mayor que 0)',
            'example': 50.0
        }
    )

    @validates('descripcion')
    def validate_descripcion(self, value, **kwargs):
        if not value or not value.strip():
            raise ValidationError('La descripción no puede estar vacía.')

    @validates('precio_base')
    def validate_precio_base(self, value, **kwargs):
        if value is None or value <= 0:
            raise ValidationError('El precio_base debe ser mayor que 0.')


class TarifaUpdateSchema(Schema):
    """Schema para actualización de Tarifa (PUT/PATCH)."""
    
    # Campos mutables
    descripcion = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nueva descripción de la tarifa',
            'example': 'Tarifa mensual básica MODIFICADA'
        }
    )
    precio_base = fields.Float(
        required=False,
        metadata={
            'description': 'Nuevo precio base (debe ser mayor que 0)',
            'example': 55.0
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran en la sanitización)
    academia_id = fields.Int(required=False, allow_none=True, load_only=True)
    fecha_alta = fields.DateTime(required=False, allow_none=True, load_only=True)
    fecha_baja = fields.DateTime(required=False, allow_none=True, load_only=True)

    @validates('descripcion')
    def validate_descripcion(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('La descripción no puede estar vacía.')

    @validates('precio_base')
    def validate_precio_base(self, value, **kwargs):
        if value is not None and value <= 0:
            raise ValidationError('El precio_base debe ser mayor que 0.')

    @validates_schema
    def validate_at_least_one_mutable_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'descripcion', 'precio_base'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable (descripcion o precio_base) para actualizar.')
