"""Schema Marshmallow para Alumno."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema
import re


class AlumnoSchema(Schema):
    """Schema para serialización/deserialización de Alumno (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID de la academia a la que pertenece el alumno',
            'example': 1
        }
    )
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre completo del alumno',
            'example': 'Juan Pérez García'
        }
    )
    email = fields.Email(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Email del alumno (único en el sistema)',
            'example': 'juan.perez@email.com'
        }
    )
    dni = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'DNI/NIE del alumno',
            'example': '12345678A'
        }
    )
    telefono = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Teléfono del alumno',
            'example': '+34 600123456'
        }
    )
    fecha_nacimiento = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de nacimiento del alumno',
            'example': '2005-03-15'
        }
    )
    direccion = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Dirección del alumno',
            'example': 'Calle Mayor 123, 28001 Madrid'
        }
    )
    nombre_tutor = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Nombre del tutor (obligatorio para menores)',
            'example': 'María García López'
        }
    )
    relaccion_tutor_alumno = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Relación del tutor con el alumno',
            'example': 'Madre'
        }
    )
    telefono_tutor = fields.Str(
        allow_none=True,
        metadata={
            'description': 'Teléfono del tutor',
            'example': '+34 600654321'
        }
    )
    email_tutor = fields.Email(
        allow_none=True,
        metadata={
            'description': 'Email del tutor',
            'example': 'maria.garcia@email.com'
        }
    )


class AlumnoCreateSchema(Schema):
    """Schema para creación de Alumno (POST).
    
    Campos obligatorios:
    - nombre: Nombre completo
    - email: Email único
    - dni: DNI/NIE
    - telefono: Teléfono de contacto
    - fecha_nacimiento: Fecha de nacimiento
    - direccion: Dirección completa
    
    Campos opcionales (obligatorios para menores):
    - nombre_tutor, relaccion_tutor_alumno, telefono_tutor, email_tutor
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
            'description': 'Nombre completo del alumno',
            'example': 'Juan Pérez García'
        }
    )
    email = fields.Email(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Email del alumno (debe ser único)',
            'example': 'juan.perez@email.com'
        }
    )
    dni = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'DNI/NIE del alumno',
            'example': '12345678A'
        }
    )
    telefono = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Teléfono del alumno',
            'example': '+34 600123456'
        }
    )
    fecha_nacimiento = fields.Date(
        required=True,
        metadata={
            'description': 'Fecha de nacimiento del alumno',
            'example': '2005-03-15'
        }
    )
    direccion = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Dirección completa del alumno',
            'example': 'Calle Mayor 123, 28001 Madrid'
        }
    )
    nombre_tutor = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nombre del tutor (obligatorio si el alumno es menor de edad)',
            'example': 'María García López'
        }
    )
    relaccion_tutor_alumno = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Relación del tutor con el alumno (Padre, Madre, Tutor legal, etc.)',
            'example': 'Madre'
        }
    )
    telefono_tutor = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Teléfono del tutor',
            'example': '+34 600654321'
        }
    )
    email_tutor = fields.Email(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Email del tutor',
            'example': 'maria.garcia@email.com'
        }
    )

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        """Nombre no puede estar vacío."""
        if not value or not value.strip():
            raise ValidationError('El nombre no puede estar vacío.')
        if len(value.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')

    @validates('email')
    def validate_email(self, value, **kwargs):
        """Email debe tener formato válido."""
        if not value or not value.strip():
            raise ValidationError('El email no puede estar vacío.')

    @validates('dni')
    def validate_dni(self, value, **kwargs):
        """DNI debe tener formato válido."""
        if not value or not value.strip():
            raise ValidationError('El DNI no puede estar vacío.')
        # Validación básica de DNI español (8 dígitos + letra) o NIE (X/Y/Z + 7 dígitos + letra)
        dni_pattern = r'^[0-9]{8}[A-Z]$|^[XYZ][0-9]{7}[A-Z]$'
        if not re.match(dni_pattern, value.upper()):
            raise ValidationError('El DNI debe tener formato válido (12345678A o X1234567A).')

    @validates('telefono')
    def validate_telefono(self, value, **kwargs):
        """Teléfono no puede estar vacío."""
        if not value or not value.strip():
            raise ValidationError('El teléfono no puede estar vacío.')

    @validates('direccion')
    def validate_direccion(self, value, **kwargs):
        """Dirección no puede estar vacía."""
        if not value or not value.strip():
            raise ValidationError('La dirección no puede estar vacía.')

    @validates_schema
    def validate_menor_edad(self, data, **kwargs):
        """Si el alumno es menor de edad, debe tener datos de tutor."""
        from datetime import date, timedelta
        if 'fecha_nacimiento' in data:
            edad = (date.today() - data['fecha_nacimiento']).days // 365
            if edad < 18:
                # Es menor de edad, requiere tutor
                if not data.get('nombre_tutor'):
                    raise ValidationError('El alumno es menor de edad, debe proporcionar nombre_tutor.')
                if not data.get('telefono_tutor'):
                    raise ValidationError('El alumno es menor de edad, debe proporcionar telefono_tutor.')


class AlumnoUpdateSchema(Schema):
    """Schema para actualización de Alumno (PATCH).
    
    Todos los campos son opcionales.
    """
    
    nombre = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo nombre del alumno',
            'example': 'Juan Pérez García (Modificado)'
        }
    )
    email = fields.Email(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo email del alumno',
            'example': 'nuevo.email@email.com'
        }
    )
    dni = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo DNI del alumno',
            'example': '87654321B'
        }
    )
    telefono = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo teléfono del alumno',
            'example': '+34 600999888'
        }
    )
    fecha_nacimiento = fields.Date(
        required=False,
        metadata={
            'description': 'Nueva fecha de nacimiento',
            'example': '2005-05-20'
        }
    )
    direccion = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nueva dirección del alumno',
            'example': 'Avenida Principal 456, 28002 Madrid'
        }
    )
    nombre_tutor = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevo nombre del tutor',
            'example': 'Carlos García López'
        }
    )
    relaccion_tutor_alumno = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nueva relación del tutor',
            'example': 'Padre'
        }
    )
    telefono_tutor = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevo teléfono del tutor',
            'example': '+34 600777666'
        }
    )
    email_tutor = fields.Email(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nuevo email del tutor',
            'example': 'carlos.garcia@email.com'
        }
    )
    
    # Campos inmutables
    academia_id = fields.Int(required=False, allow_none=True, load_only=True)

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('El nombre no puede estar vacío.')
        if value is not None and len(value.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')

    @validates('dni')
    def validate_dni(self, value, **kwargs):
        if value is not None:
            dni_pattern = r'^[0-9]{8}[A-Z]$|^[XYZ][0-9]{7}[A-Z]$'
            if not re.match(dni_pattern, value.upper()):
                raise ValidationError('El DNI debe tener formato válido (12345678A o X1234567A).')

    @validates('telefono')
    def validate_telefono(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('El teléfono no puede estar vacío.')

    @validates('direccion')
    def validate_direccion(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('La dirección no puede estar vacía.')

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo mutable debe estar presente para actualizar."""
        mutable_fields = {
            'nombre', 'email', 'dni', 'telefono', 'fecha_nacimiento', 'direccion',
            'nombre_tutor', 'relaccion_tutor_alumno', 'telefono_tutor', 'email_tutor'
        }
        if not any(field in data for field in mutable_fields):
            raise ValidationError('Debe proporcionar al menos un campo mutable para actualizar.')
