"""Schema Marshmallow para Aula."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema


class AulaSchema(Schema):
    """Schema para serialización/deserialización de Aula (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la academia a la que pertenece el aula',
            'example': 1
        }
    )
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre del aula',
            'example': 'Aula 101'
        }
    )
    capacidad_maxima = fields.Int(
        required=True,
        metadata={
            'description': 'Capacidad máxima del aula',
            'example': 30
        }
    )


class AulaCreateSchema(Schema):
    """Schema para creación de Aula (POST).
    
    Ejemplo de JSON para crear aula:
    {
        "nombre": "Aula 102 - Informática",
        "capacidad_maxima": 30,
        "academia_id": 1
    }
    
    Campos obligatorios:
    - nombre: Nombre del aula
    - capacidad_maxima: Capacidad máxima del aula (> 0)
    
    Campos opcionales:
    - academia_id: Manejado por el backend según el rol del creador:
      * admin_plataforma: debe especificarlo
      * admin_academia: forzado automáticamente a su propia academia
    """
    
    academia_id = fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'ID de la academia (obligatorio para admin_plataforma, opcional para admin_academia)',
            'example': 1
        }
    )
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre del aula',
            'example': 'Aula 102 - Informática'
        }
    )
    capacidad_maxima = fields.Int(
        required=True,
        metadata={
            'description': 'Capacidad máxima del aula (debe ser mayor que 0)',
            'example': 30
        }
    )

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        """Nombre no puede estar vacío."""
        if not value or not value.strip():
            raise ValidationError('El nombre no puede estar vacío.')
        if len(value.strip()) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')

    @validates('capacidad_maxima')
    def validate_capacidad_maxima(self, value, **kwargs):
        """Capacidad máxima debe ser mayor que 0."""
        if value is None or value <= 0:
            raise ValidationError('La capacidad_maxima debe ser mayor que 0.')


class AulaUpdateSchema(Schema):
    """Schema para actualización de Aula (PATCH).
    
    Ejemplo de JSON para actualizar aula:
    {
        "nombre": "Aula 102 - Informática Renovada",
        "capacidad_maxima": 35
    }
    
    Todos los campos son opcionales.
    """
    
    nombre = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo nombre del aula',
            'example': 'Aula 102 - Informática Renovada'
        }
    )
    capacidad_maxima = fields.Int(
        required=False,
        metadata={
            'description': 'Nueva capacidad máxima del aula',
            'example': 35
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran)
    academia_id = fields.Int(required=False, allow_none=True, load_only=True)

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        """Nombre no puede estar vacío si se proporciona."""
        if value is not None and (not value or not value.strip()):
            raise ValidationError('El nombre no puede estar vacío.')
        if value is not None and len(value.strip()) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')

    @validates('capacidad_maxima')
    def validate_capacidad_maxima(self, value, **kwargs):
        """Capacidad máxima debe ser mayor que 0 si se proporciona."""
        if value is not None and value <= 0:
            raise ValidationError('La capacidad_maxima debe ser mayor que 0.')

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'nombre', 'capacidad_maxima'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable (nombre o capacidad_maxima) para actualizar.')
