"""Schema Marshmallow para Inscripcion."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema


class InscripcionSchema(Schema):
    """Schema para serialización/deserialización de Inscripcion (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(
        dump_only=True,
        metadata={
            'description': 'ID de la academia (calculado automáticamente)',
            'example': 1
        }
    )
    alumno_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del alumno inscrito',
            'example': 1
        }
    )
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso al que se inscribe',
            'example': 1
        }
    )
    fecha_inicio = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de inicio de la inscripción',
            'example': '2024-09-15'
        }
    )
    fecha_fin = fields.Date(
        allow_none=True,
        metadata={
            'description': 'Fecha de fin de la inscripción (null si activa)',
            'example': None
        }
    )
    motivo_baja = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Motivo de baja de la inscripción',
            'example': None
        }
    )
    # Nested relationships (opcional para enriquecer respuesta)
    alumno = fields.Nested(
        'AlumnoSchema',
        dump_only=True,
        metadata={'description': 'Información del alumno'}
    )
    curso = fields.Nested(
        'CursoSchema',
        dump_only=True,
        metadata={'description': 'Información del curso'}
    )


class InscripcionCreateSchema(Schema):
    """Schema para creación de Inscripcion (POST).
    
    Campos obligatorios:
    - alumno_id: ID del alumno
    - curso_id: ID del curso
    - fecha_inicio: Fecha de inicio de la inscripción
    
    Campos opcionales:
    - fecha_fin: null por defecto (inscripción activa)
    - motivo_baja: null por defecto
    
    Nota: La tarifa se obtiene del curso automáticamente.
    """
    
    alumno_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del alumno a inscribir',
            'example': 1
        }
    )
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso al que se inscribe',
            'example': 1
        }
    )
    fecha_inicio = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de inicio de la inscripción',
            'example': '2024-09-15'
        }
    )
    fecha_fin = fields.Date(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Fecha de fin (opcional, null si inscripción activa)',
            'example': None
        }
    )
    motivo_baja = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Motivo de baja (opcional)',
            'example': None
        }
    )

    @validates('alumno_id')
    def validate_alumno_id(self, value, **kwargs):
        """alumno_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El alumno_id debe ser un número positivo.')

    @validates('curso_id')
    def validate_curso_id(self, value, **kwargs):
        """curso_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El curso_id debe ser un número positivo.')

    @validates_schema
    def validate_fechas(self, data, **kwargs):
        """Si fecha_fin existe, debe ser posterior a fecha_inicio."""
        if data.get('fecha_fin') and 'fecha_inicio' in data:
            if data['fecha_fin'] <= data['fecha_inicio']:
                raise ValidationError('La fecha_fin debe ser posterior a la fecha_inicio.')


class InscripcionUpdateSchema(Schema):
    """Schema para actualización de Inscripcion (PATCH).
    
    Todos los campos son opcionales.
    Típicamente usado para dar de baja (fecha_fin + motivo_baja).
    
    Nota: La tarifa se gestiona a nivel de Curso, no de Inscripcion.
    """
    
    fecha_inicio = fields.Date(
        required=False,
        metadata={
            'description': 'Nueva fecha de inicio',
            'example': '2024-10-01'
        }
    )
    fecha_fin = fields.Date(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nueva fecha de fin (para dar de baja)',
            'example': '2024-12-31'
        }
    )
    motivo_baja = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Motivo de baja',
            'example': 'Cambio de ciudad'
        }
    )
    
    # Campos inmutables
    alumno_id = fields.Int(required=False, allow_none=True, load_only=True)
    curso_id = fields.Int(required=False, allow_none=True, load_only=True)

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'fecha_inicio', 'fecha_fin', 'motivo_baja'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')

    @validates_schema
    def validate_fechas(self, data, **kwargs):
        """Si se actualizan fechas, fecha_fin debe ser posterior a fecha_inicio."""
        if 'fecha_inicio' in data and 'fecha_fin' in data and data.get('fecha_fin'):
            if data['fecha_fin'] <= data['fecha_inicio']:
                raise ValidationError('La fecha_fin debe ser posterior a la fecha_inicio.')
