"""Schema Marshmallow para AnotacionesAlumnoSesion."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema


class AnotacionSchema(Schema):
    """Schema para serialización/deserialización de AnotacionesAlumnoSesion (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    sesion_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la sesión',
            'example': 1
        }
    )
    inscripcion_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la inscripción del alumno',
            'example': 1
        }
    )
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso',
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
    alumno_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del alumno',
            'example': 1
        }
    )
    tipo_anotacion = fields.Str(
        required=True,
        metadata={
            'description': 'Tipo de anotación: Ausencia (pasar lista), Evaluacion (académica), Comportamiento (conducta), Observacion (notas generales), Otros (miscelánea)',
            'example': 'Evaluacion',
            'enum': ['Ausencia', 'Evaluacion', 'Comportamiento', 'Observacion', 'Otros']
        }
    )
    texto = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Texto de la anotación',
            'example': 'Ausencia justificada por enfermedad'
        }
    )
    timestamp_alta = fields.DateTime(
        dump_only=True,
        metadata={
            'description': 'Timestamp de creación de la anotación',
            'example': '2024-10-27T09:15:00'
        }
    )
    timestamp_baja = fields.DateTime(
        dump_only=True,
        allow_none=True,
        metadata={
            'description': 'Timestamp de baja lógica (null si activa)',
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
    # Nested relationships (opcional para enriquecer respuesta)
    alumno = fields.Nested(
        'AlumnoSchema',
        dump_only=True,
        metadata={'description': 'Información del alumno'}
    )
    sesion = fields.Nested(
        'SesionSchema',
        dump_only=True,
        metadata={'description': 'Información de la sesión'}
    )


class AnotacionCreateSchema(Schema):
    """Schema para creación de AnotacionesAlumnoSesion (POST).
    
    TIPOS DE ANOTACIONES PERMITIDAS MANUALMENTE:
    - Evaluacion: Anotaciones académicas (rendimiento, participación, comprensión)
    - Comportamiento: Observaciones de conducta (positiva o negativa)
    - Observacion: Notas generales del profesor
    - Otros: Categoría genérica para otras observaciones
    
    IMPORTANTE: Las anotaciones de tipo 'Ausencia' NO se pueden crear mediante este endpoint.
    Las ausencias se registran automáticamente mediante POST /sesiones/{sesion_id}/pasar-lista.
    
    Ejemplo JSON para crear anotación académica:
    {
        "sesion_id": 123,
        "inscripcion_id": 45,
        "curso_id": 1,
        "curso_profesor_id": 10,
        "alumno_id": 5,
        "tipo_anotacion": "Evaluacion",
        "texto": "Excelente participación en la discusión sobre gramática inglesa. Demuestra comprensión avanzada."
    }
    
    Campos obligatorios:
    - sesion_id: ID de la sesión
    - inscripcion_id: ID de la inscripción
    - curso_id: ID del curso
    - curso_profesor_id: ID de Curso_Profesores
    - alumno_id: ID del alumno
    - tipo_anotacion: Tipo (Evaluacion, Comportamiento, Observacion, Otros)
    
    Campos opcionales:
    - texto: Texto descriptivo de la anotación
    """
    
    sesion_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la sesión',
            'example': 1
        }
    )
    inscripcion_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la inscripción del alumno',
            'example': 1
        }
    )
    curso_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del curso',
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
    alumno_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del alumno',
            'example': 1
        }
    )
    tipo_anotacion = fields.Str(
        required=True,
        metadata={
            'description': 'Tipo de anotación permitido: Evaluacion, Comportamiento, Observacion, Otros (NO se permite Ausencia - usar pasar-lista)',
            'example': 'Evaluacion',
            'enum': ['Evaluacion', 'Comportamiento', 'Observacion', 'Otros']
        }
    )
    texto = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Texto descriptivo de la anotación',
            'example': 'Excelente participación en la discusión sobre gramática inglesa. Demuestra comprensión avanzada.'
        }
    )

    @validates('sesion_id')
    def validate_sesion_id(self, value, **kwargs):
        """sesion_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El sesion_id debe ser un número positivo.')

    @validates('inscripcion_id')
    def validate_inscripcion_id(self, value, **kwargs):
        """inscripcion_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El inscripcion_id debe ser un número positivo.')

    @validates('curso_id')
    def validate_curso_id(self, value, **kwargs):
        """curso_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El curso_id debe ser un número positivo.')

    @validates('curso_profesor_id')
    def validate_curso_profesor_id(self, value, **kwargs):
        """curso_profesor_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El curso_profesor_id debe ser un número positivo.')

    @validates('alumno_id')
    def validate_alumno_id(self, value, **kwargs):
        """alumno_id debe ser válido."""
        if value is None or value <= 0:
            raise ValidationError('El alumno_id debe ser un número positivo.')

    @validates('tipo_anotacion')
    def validate_tipo_anotacion(self, value, **kwargs):
        """Tipo de anotación debe ser válido y NO puede ser 'Ausencia'."""
        # Rechazar explícitamente 'Ausencia'
        if value == 'Ausencia':
            raise ValidationError(
                'No se pueden crear anotaciones de tipo "Ausencia" manualmente. '
                'Las ausencias se registran mediante POST /sesiones/{sesion_id}/pasar-lista.'
            )
        
        # Validar que sea uno de los tipos permitidos
        tipos_permitidos = ['Evaluacion', 'Comportamiento', 'Observacion', 'Otros']
        if value not in tipos_permitidos:
            raise ValidationError(f'El tipo_anotacion debe ser uno de: {", ".join(tipos_permitidos)}')


class AnotacionUpdateSchema(Schema):
    """Schema para actualización de AnotacionesAlumnoSesion (PATCH).
    
    Ejemplo JSON para actualizar texto de anotación:
    {
        "texto": "Comportamiento disruptivo en clase. Habló durante la explicación."
    }
    
    Todos los campos son opcionales.
    Típicamente usado para modificar texto o dar de baja.
    """
    
    tipo_anotacion = fields.Str(
        required=False,
        metadata={
            'description': 'Nuevo tipo de anotación',
            'example': 'Comportamiento',
            'enum': ['Ausencia', 'Evaluacion', 'Comportamiento', 'Observacion', 'Otros']
        }
    )
    texto = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevo texto de la anotación',
            'example': 'Comportamiento disruptivo en clase'
        }
    )
    motivo_baja = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Motivo de baja (para dar de baja la anotación)',
            'example': 'Anotación errónea'
        }
    )
    
    # Campos inmutables
    sesion_id = fields.Int(required=False, allow_none=True, load_only=True)
    inscripcion_id = fields.Int(required=False, allow_none=True, load_only=True)
    curso_id = fields.Int(required=False, allow_none=True, load_only=True)
    curso_profesor_id = fields.Int(required=False, allow_none=True, load_only=True)
    alumno_id = fields.Int(required=False, allow_none=True, load_only=True)
    timestamp_alta = fields.DateTime(required=False, allow_none=True, load_only=True)
    timestamp_baja = fields.DateTime(required=False, allow_none=True, load_only=True)

    @validates('tipo_anotacion')
    def validate_tipo_anotacion(self, value, **kwargs):
        if value is not None:
            tipos_validos = ['Ausencia', 'Evaluacion', 'Comportamiento', 'Observacion', 'Otros']
            if value not in tipos_validos:
                raise ValidationError(f'El tipo_anotacion debe ser uno de: {", ".join(tipos_validos)}')

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {'tipo_anotacion', 'texto', 'motivo_baja'}
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')
