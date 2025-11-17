"""Schema Marshmallow para Sesion."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from datetime import time


class SesionSchema(Schema):
    """Schema para serialización/deserialización de Sesion (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    horario_curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del horario del curso',
            'example': 1
        }
    )
    aula_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del aula donde se realiza la sesión',
            'example': 1
        }
    )
    curso_profesor_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la relación Curso_Profesores',
            'example': 1
        }
    )
    timestamp_alta = fields.DateTime(
        dump_only=True,
        metadata={
            'description': 'Timestamp de creación de la sesión',
            'example': '2024-10-27T08:00:00'
        }
    )
    hora_inicio = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de inicio real de la sesión',
            'example': '09:00:00'
        }
    )
    hora_fin = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de finalización real de la sesión',
            'example': '10:30:00'
        }
    )
    timestamp_baja = fields.DateTime(
        dump_only=True,
        allow_none=True,
        metadata={
            'description': 'Timestamp de baja lógica (null si activo)',
            'example': None
        }
    )
    motivo_baja = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Motivo de la baja lógica',
            'example': None
        }
    )
    notas_sesion = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Notas generales de la sesión',
            'example': 'Clase muy participativa'
        }
    )
    notas_materia = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Notas sobre la materia impartida',
            'example': 'Tema 3: Verbos irregulares'
        }
    )
    # Nested relationships (opcional para enriquecer respuesta)
    horario_curso = fields.Nested(
        'HorarioCursoSchema',
        dump_only=True,
        metadata={'description': 'Información del horario del curso'}
    )
    aula = fields.Nested(
        'AulaSchema',
        dump_only=True,
        metadata={'description': 'Información del aula'}
    )


class SesionCreateSchema(Schema):
    """Schema para creación de Sesion (POST).
    
    Campos obligatorios:
    - horario_curso_id: ID del horario del curso
    - aula_id: ID del aula
    - curso_profesor_id: ID de la relación Curso_Profesores
    - hora_inicio: Hora de inicio real
    - hora_fin: Hora de finalización real
    
    Campos opcionales:
    - notas_sesion: Notas generales
    - notas_materia: Notas sobre la materia
    """
    
    horario_curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del horario del curso',
            'example': 1
        }
    )
    aula_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del aula donde se realiza la sesión',
            'example': 1
        }
    )
    curso_profesor_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la relación Curso_Profesores (profesor asignado al curso)',
            'example': 1
        }
    )
    hora_inicio = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de inicio real de la sesión (formato HH:MM:SS)',
            'example': '09:00:00'
        }
    )
    hora_fin = fields.Time(
        required=True,
        metadata={
            'description': 'Hora de finalización real de la sesión (formato HH:MM:SS)',
            'example': '10:30:00'
        }
    )
    notas_sesion = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Notas generales de la sesión',
            'example': 'Clase muy participativa'
        }
    )
    notas_materia = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Notas sobre la materia impartida',
            'example': 'Tema 3: Verbos irregulares'
        }
    )

    @validates_schema
    def validate_horas(self, data, **kwargs):
        """Hora fin debe ser posterior a hora inicio."""
        if 'hora_inicio' in data and 'hora_fin' in data:
            if data['hora_fin'] <= data['hora_inicio']:
                raise ValidationError('La hora_fin debe ser posterior a la hora_inicio.')


class SesionUpdateSchema(Schema):
    """Schema para actualización de Sesion (PATCH).
    
    Todos los campos son opcionales.
    """
    
    aula_id = fields.Int(
        required=False,
        metadata={
            'description': 'Nuevo ID del aula',
            'example': 2
        }
    )
    hora_inicio = fields.Time(
        required=False,
        metadata={
            'description': 'Nueva hora de inicio',
            'example': '09:15:00'
        }
    )
    hora_fin = fields.Time(
        required=False,
        metadata={
            'description': 'Nueva hora de finalización',
            'example': '10:45:00'
        }
    )
    notas_sesion = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevas notas de sesión',
            'example': 'Clase muy participativa - actualizado'
        }
    )
    notas_materia = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevas notas de materia',
            'example': 'Tema 3: Verbos irregulares - completado'
        }
    )
    motivo_baja = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Motivo de baja (para dar de baja la sesión)',
            'example': 'Sesión cancelada por festivo'
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran)
    horario_curso_id = fields.Int(required=False, allow_none=True, load_only=True)
    curso_profesor_id = fields.Int(required=False, allow_none=True, load_only=True)
    timestamp_alta = fields.DateTime(required=False, allow_none=True, load_only=True)
    timestamp_baja = fields.DateTime(required=False, allow_none=True, load_only=True)

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'aula_id', 'hora_inicio', 'hora_fin', 'notas_sesion', 'notas_materia', 'motivo_baja'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')

    @validates_schema
    def validate_horas(self, data, **kwargs):
        """Si se actualizan horas, hora_fin debe ser posterior a hora_inicio."""
        if 'hora_inicio' in data and 'hora_fin' in data:
            if data['hora_fin'] <= data['hora_inicio']:
                raise ValidationError('La hora_fin debe ser posterior a la hora_inicio.')


class PasarListaSchema(Schema):
    """Schema para pasar lista en una sesión (operación batch).
    
    Permite registrar asistencia de múltiples alumnos en una sola operación.
    """
    
    sesion_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la sesión',
            'example': 1
        }
    )
    asistencias = fields.List(
        fields.Nested(lambda: AsistenciaSchema()),
        required=True,
        metadata={
            'description': 'Lista de asistencias de alumnos'
        }
    )


class AsistenciaSchema(Schema):
    """Schema para registrar asistencia individual de un alumno."""
    
    alumno_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del alumno',
            'example': 1
        }
    )
    estado_asistencia = fields.Str(
        required=True,
        metadata={
            'description': 'Estado de asistencia del alumno',
            'example': 'Presente',
            'enum': ['Presente', 'Ausente', 'Justificado', 'Retrasado']
        }
    )
    observaciones = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Observaciones sobre la asistencia',
            'example': 'Llegó 10 minutos tarde'
        }
    )

    @validates('estado_asistencia')
    def validate_estado_asistencia(self, value, **kwargs):
        """Estado de asistencia debe ser válido."""
        estados_validos = ['Presente', 'Ausente', 'Justificado', 'Retrasado']
        if value not in estados_validos:
            raise ValidationError(f'El estado_asistencia debe ser uno de: {", ".join(estados_validos)}')
