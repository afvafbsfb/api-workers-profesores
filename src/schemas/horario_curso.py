"""Schema Marshmallow para HorarioCurso."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from datetime import time


class HorarioCursoSchema(Schema):
    """Schema para serialización/deserialización de HorarioCurso (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso al que pertenece el horario',
            'example': 1
        }
    )
    aula_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del aula donde se imparte el curso',
            'example': 1
        }
    )
    dia_semana = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Día de la semana',
            'example': 'Lunes',
            'enum': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        }
    )
    hora_inicio = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de inicio de la clase',
            'example': '09:00:00'
        }
    )
    hora_fin = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de finalización de la clase',
            'example': '10:30:00'
        }
    )
    # Nested relationships (opcional para enriquecer respuesta)
    curso = fields.Nested(
        'CursoSchema',
        dump_only=True,
        metadata={'description': 'Información del curso'}
    )
    aula = fields.Nested(
        'AulaSchema',
        dump_only=True,
        metadata={'description': 'Información del aula'}
    )


class HorarioCursoCreateSchema(Schema):
    """Schema para creación de HorarioCurso (POST).
    
    Ejemplo de JSON para crear horario:
    {
        "curso_id": 1,
        "aula_id": 1,
        "dia_semana": "Lunes",
        "hora_inicio": "09:00:00",
        "hora_fin": "10:30:00"
    }
    
    Campos obligatorios:
    - curso_id: ID del curso
    - aula_id: ID del aula
    - dia_semana: Día de la semana
    - hora_inicio: Hora de inicio
    - hora_fin: Hora de finalización
    """
    
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso al que se asigna el horario',
            'example': 1
        }
    )
    aula_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del aula donde se imparte',
            'example': 1
        }
    )
    dia_semana = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Día de la semana (capitalizado)',
            'example': 'Lunes',
            'enum': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        }
    )
    hora_inicio = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de inicio de la clase (formato HH:MM:SS)',
            'example': '09:00:00'
        }
    )
    hora_fin = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de finalización de la clase (formato HH:MM:SS)',
            'example': '10:30:00'
        }
    )

    @validates('dia_semana')
    def validate_dia_semana(self, value, **kwargs):
        """Día de la semana debe ser válido."""
        dias_validos = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if value not in dias_validos:
            raise ValidationError(f'El dia_semana debe ser uno de: {", ".join(dias_validos)}')

    @validates_schema
    def validate_horas(self, data, **kwargs):
        """Hora fin debe ser posterior a hora inicio."""
        if 'hora_inicio' in data and 'hora_fin' in data:
            if data['hora_fin'] <= data['hora_inicio']:
                raise ValidationError('La hora_fin debe ser posterior a la hora_inicio.')


class HorarioCursoUpdateSchema(Schema):
    """Schema para actualización de HorarioCurso (PATCH).
    
    Ejemplo de JSON para actualizar horario:
    {
        "aula_id": 2,
        "hora_inicio": "10:00:00",
        "hora_fin": "11:30:00"
    }
    
    Todos los campos son opcionales.
    """
    
    aula_id = fields.Int(
        required=False,
        metadata={
            'description': 'Nuevo ID del aula',
            'example': 2
        }
    )
    dia_semana = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo día de la semana',
            'example': 'Martes',
            'enum': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        }
    )
    hora_inicio = fields.Time(
        required=False,
        metadata={
            'description': 'Nueva hora de inicio',
            'example': '10:00:00'
        }
    )
    hora_fin = fields.Time(
        required=False,
        metadata={
            'description': 'Nueva hora de finalización',
            'example': '11:30:00'
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran)
    curso_id = fields.Int(required=False, allow_none=True, load_only=True)

    @validates('dia_semana')
    def validate_dia_semana(self, value, **kwargs):
        if value is not None:
            dias_validos = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            if value not in dias_validos:
                raise ValidationError(f'El dia_semana debe ser uno de: {", ".join(dias_validos)}')

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'aula_id', 'dia_semana', 'hora_inicio', 'hora_fin'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')

    @validates_schema
    def validate_horas(self, data, **kwargs):
        """Si se actualizan horas, hora_fin debe ser posterior a hora_inicio."""
        if 'hora_inicio' in data and 'hora_fin' in data:
            if data['hora_fin'] <= data['hora_inicio']:
                raise ValidationError('La hora_fin debe ser posterior a la hora_inicio.')
