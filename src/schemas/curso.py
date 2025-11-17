"""Schema Marshmallow para Curso."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema
from datetime import date


class CursoSchema(Schema):
    """Schema para serialización/deserialización de Curso (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la academia a la que pertenece el curso',
            'example': 1
        }
    )
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre del curso',
            'example': 'Inglés B1 - Mañanas'
        }
    )
    anio_academico = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Año académico del curso',
            'example': '2024-2025'
        }
    )
    fecha_inicio = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de inicio del curso',
            'example': '2024-09-15'
        }
    )
    fecha_fin = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de finalización del curso',
            'example': '2025-06-30'
        }
    )
    acepta_nuevos_alumnos = fields.Bool(
        required=True,
        metadata={
            'description': 'Indica si el curso acepta nuevos alumnos',
            'example': True
        }
    )
    capacidad_maxima = fields.Int(
        required=True,
        metadata={
            'description': 'Capacidad máxima de alumnos del curso',
            'example': 25
        }
    )
    tarifa_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la tarifa asociada al curso',
            'example': 1
        }
    )
    tipo_alumno = fields.Str(
        required=True,
        metadata={
            'description': 'Tipo de alumno del curso',
            'example': 'Adultos',
            'enum': ['Infantil', 'Juvenil', 'Adultos']
        }
    )
    estado = fields.Str(
        required=True,
        metadata={
            'description': 'Estado del curso',
            'example': 'Activo',
            'enum': ['Activo', 'Inactivo', 'Finalizado']
        }
    )
    # Nested tarifa (opcional para enriquecer respuesta)
    tarifa = fields.Nested(
        'TarifaSchema',
        dump_only=True,
        metadata={'description': 'Información de la tarifa asociada'}
    )


class CursoCreateSchema(Schema):
    """Schema para creación de Curso (POST).
    
    Ejemplo de JSON para crear curso:
    {
        "nombre": "Inglés B2 - Tardes",
        "anio_academico": "2024-2025",
        "fecha_inicio": "2024-09-15",
        "fecha_fin": "2025-06-30",
        "capacidad_maxima": 25,
        "tarifa_id": 1,
        "tipo_alumno": "Adultos",
        "estado": "Activo",
        "acepta_nuevos_alumnos": true
    }
    
    Campos obligatorios:
    - nombre: Nombre del curso
    - anio_academico: Año académico (formato: YYYY-YYYY)
    - fecha_inicio: Fecha de inicio
    - fecha_fin: Fecha de finalización
    - capacidad_maxima: Capacidad máxima (> 0)
    - tarifa_id: ID de la tarifa
    - tipo_alumno: Tipo de alumno (Infantil, Juvenil, Adultos)
    - estado: Estado del curso (Activo, Inactivo, Finalizado)
    
    Campos opcionales:
    - acepta_nuevos_alumnos: Por defecto True
    - academia_id: Manejado por el backend según el rol del creador
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
            'description': 'Nombre del curso',
            'example': 'Inglés B1 - Mañanas'
        }
    )
    anio_academico = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Año académico (formato: YYYY-YYYY)',
            'example': '2024-2025'
        }
    )
    fecha_inicio = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de inicio del curso',
            'example': '2024-09-15'
        }
    )
    fecha_fin = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de finalización del curso',
            'example': '2025-06-30'
        }
    )
    acepta_nuevos_alumnos = fields.Bool(
        required=False,
        load_default=True,
        metadata={
            'description': 'Indica si el curso acepta nuevos alumnos (por defecto True)',
            'example': True
        }
    )
    capacidad_maxima = fields.Int(
        required=True,
        metadata={
            'description': 'Capacidad máxima de alumnos (debe ser mayor que 0)',
            'example': 25
        }
    )
    tarifa_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la tarifa asociada al curso',
            'example': 1
        }
    )
    tipo_alumno = fields.Str(
        required=True,
        metadata={
            'description': 'Tipo de alumno (Infantil, Juvenil, Adultos)',
            'example': 'Adultos',
            'enum': ['Infantil', 'Juvenil', 'Adultos']
        }
    )
    estado = fields.Str(
        required=True,
        metadata={
            'description': 'Estado del curso (Activo, Inactivo, Finalizado)',
            'example': 'Activo',
            'enum': ['Activo', 'Inactivo', 'Finalizado']
        }
    )

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        """Nombre no puede estar vacío."""
        if not value or not value.strip():
            raise ValidationError('El nombre no puede estar vacío.')
        if len(value.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')

    @validates('anio_academico')
    def validate_anio_academico(self, value, **kwargs):
        """Año académico debe tener formato YYYY-YYYY."""
        if not value or not value.strip():
            raise ValidationError('El año académico no puede estar vacío.')
        # Validar formato YYYY-YYYY
        import re
        if not re.match(r'^\d{4}-\d{4}$', value):
            raise ValidationError('El año académico debe tener formato YYYY-YYYY (ej: 2024-2025).')

    @validates('capacidad_maxima')
    def validate_capacidad_maxima(self, value, **kwargs):
        """Capacidad máxima debe ser mayor que 0."""
        if value is None or value <= 0:
            raise ValidationError('La capacidad_maxima debe ser mayor que 0.')

    @validates('tipo_alumno')
    def validate_tipo_alumno(self, value, **kwargs):
        """Tipo de alumno debe ser válido."""
        if value not in ('Infantil', 'Juvenil', 'Adultos'):
            raise ValidationError("El tipo_alumno debe ser 'Infantil', 'Juvenil' o 'Adultos'.")

    @validates('estado')
    def validate_estado(self, value, **kwargs):
        """Estado debe ser válido."""
        if value not in ('Activo', 'Inactivo', 'Finalizado'):
            raise ValidationError("El estado debe ser 'Activo', 'Inactivo' o 'Finalizado'.")

    @validates_schema
    def validate_fechas(self, data, **kwargs):
        """Fecha fin debe ser posterior a fecha inicio."""
        if 'fecha_inicio' in data and 'fecha_fin' in data:
            if data['fecha_fin'] <= data['fecha_inicio']:
                raise ValidationError('La fecha_fin debe ser posterior a la fecha_inicio.')


class CursoUpdateSchema(Schema):
    """Schema para actualización de Curso (PATCH).
    
    Ejemplo de JSON para actualizar curso:
    {
        "nombre": "Inglés B2 - Tardes (Modificado)",
        "capacidad_maxima": 30,
        "acepta_nuevos_alumnos": false
    }
    
    Todos los campos son opcionales.
    """
    
    nombre = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo nombre del curso',
            'example': 'Inglés B1 - Mañanas (Modificado)'
        }
    )
    anio_academico = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo año académico',
            'example': '2025-2026'
        }
    )
    fecha_inicio = fields.Date(
        required=False,
        metadata={
            'description': 'Nueva fecha de inicio',
            'example': '2025-09-15'
        }
    )
    fecha_fin = fields.Date(
        required=False,
        metadata={
            'description': 'Nueva fecha de finalización',
            'example': '2026-06-30'
        }
    )
    acepta_nuevos_alumnos = fields.Bool(
        required=False,
        metadata={
            'description': 'Nuevo valor de acepta_nuevos_alumnos',
            'example': False
        }
    )
    capacidad_maxima = fields.Int(
        required=False,
        metadata={
            'description': 'Nueva capacidad máxima',
            'example': 30
        }
    )
    tarifa_id = fields.Int(
        required=False,
        metadata={
            'description': 'Nuevo ID de tarifa',
            'example': 2
        }
    )
    tipo_alumno = fields.Str(
        required=False,
        metadata={
            'description': 'Nuevo tipo de alumno',
            'example': 'Juvenil',
            'enum': ['Infantil', 'Juvenil', 'Adultos']
        }
    )
    estado = fields.Str(
        required=False,
        metadata={
            'description': 'Nuevo estado del curso',
            'example': 'Finalizado',
            'enum': ['Activo', 'Inactivo', 'Finalizado']
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran)
    academia_id = fields.Int(required=False, allow_none=True, load_only=True)

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('El nombre no puede estar vacío.')
        if value is not None and len(value.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')

    @validates('anio_academico')
    def validate_anio_academico(self, value, **kwargs):
        if value is not None:
            import re
            if not re.match(r'^\d{4}-\d{4}$', value):
                raise ValidationError('El año académico debe tener formato YYYY-YYYY.')

    @validates('capacidad_maxima')
    def validate_capacidad_maxima(self, value, **kwargs):
        if value is not None and value <= 0:
            raise ValidationError('La capacidad_maxima debe ser mayor que 0.')

    @validates('tipo_alumno')
    def validate_tipo_alumno(self, value, **kwargs):
        if value is not None and value not in ('Infantil', 'Juvenil', 'Adultos'):
            raise ValidationError("El tipo_alumno debe ser 'Infantil', 'Juvenil' o 'Adultos'.")

    @validates('estado')
    def validate_estado(self, value, **kwargs):
        if value is not None and value not in ('Activo', 'Inactivo', 'Finalizado'):
            raise ValidationError("El estado debe ser 'Activo', 'Inactivo' o 'Finalizado'.")

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {
            'nombre', 'anio_academico', 'fecha_inicio', 'fecha_fin',
            'acepta_nuevos_alumnos', 'capacidad_maxima', 'tarifa_id',
            'tipo_alumno', 'estado'
        }
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')

    @validates_schema
    def validate_fechas(self, data, **kwargs):
        """Si se actualizan fechas, fecha_fin debe ser posterior a fecha_inicio."""
        if 'fecha_inicio' in data and 'fecha_fin' in data:
            if data['fecha_fin'] <= data['fecha_inicio']:
                raise ValidationError('La fecha_fin debe ser posterior a la fecha_inicio.')
