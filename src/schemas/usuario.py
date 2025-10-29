"""Schema Marshmallow para Usuario."""
from marshmallow import Schema, fields, validates, ValidationError, validates_schema
import re


class RolSchema(Schema):
    """Schema para el rol del usuario."""
    id = fields.Int(dump_only=True, metadata={'example': 2})
    nombre = fields.Str(metadata={'example': 'Admin_academia'})


class UsuarioSchema(Schema):
    """Schema para serialización/deserialización completa de Usuario (GET)."""
    
    id = fields.Int(dump_only=True, metadata={'example': 1})
    academia_id = fields.Int(
        allow_none=True,
        metadata={
            'description': 'ID de la academia a la que pertenece el usuario (null para admin_plataforma)',
            'example': 1
        }
    )
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre completo del usuario',
            'example': 'Angel Vidal Fernández'
        }
    )
    email = fields.Email(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Email del usuario (único en el sistema)',
            'example': 'afvidal@abanca.com'
        }
    )
    rol = fields.Nested(
        RolSchema,
        metadata={'description': 'Información del rol del usuario'}
    )
    rol_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del rol asignado al usuario',
            'example': 2
        }
    )
    password = fields.Str(
        load_only=True,
        allow_none=True,
        metadata={
            'description': 'Contraseña del usuario (opcional en alta, se usará el email como password temporal)',
            'example': 'MiPassword123!'
        }
    )
    estado = fields.Str(
        dump_only=True,
        metadata={
            'description': 'Estado del usuario',
            'example': 'Activo',
            'enum': ['Activo', 'Bloqueado', 'Baja']
        }
    )
    fecha_alta = fields.DateTime(
        dump_only=True,
        metadata={'example': '2025-10-27T10:30:00'}
    )


class UsuarioCreateSchema(Schema):
    """Schema para creación de Usuario (POST).
    
    Campos obligatorios:
    - nombre: Nombre completo del usuario
    - email: Email único en el sistema
    - rol_id: ID del rol a asignar
    
    Campos opcionales:
    - password: Si no se proporciona, se usa el email como password temporal
    - academia_id: Manejado por el backend según el rol del creador:
      * admin_plataforma: puede especificarlo o dejarlo null
      * admin_academia: forzado automáticamente a su propia academia
    """
    
    nombre = fields.Str(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Nombre completo del usuario',
            'example': 'Angel Vidal Fernández'
        }
    )
    email = fields.Email(
        required=True,
        allow_none=False,
        metadata={
            'description': 'Email del usuario (debe ser único)',
            'example': 'afvidal@abanca.com'
        }
    )
    rol_id = fields.Int(
        required=True,
        metadata={
            'description': 'ID del rol a asignar (1=admin_plataforma, 2=admin_academia, 3=profesor_academia)',
            'example': 2
        }
    )
    password = fields.Str(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Contraseña inicial (opcional). Si no se proporciona, se usará el email como password temporal que deberá cambiarse en el primer login',
            'example': None
        }
    )
    academia_id = fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'ID de la academia (solo admin_plataforma puede especificarlo, admin_academia lo tiene forzado)',
            'example': 1
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
        # Email ya validado por fields.Email(), solo verificar que no esté vacío
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise ValidationError('El email no tiene un formato válido.')

    @validates('password')
    def validate_password(self, value, **kwargs):
        """Password debe cumplir requisitos mínimos si se proporciona."""
        if value is not None and value.strip():
            if len(value) < 6:
                raise ValidationError('La contraseña debe tener al menos 6 caracteres.')
            # Opcional: añadir más validaciones (mayúsculas, números, etc.)

    @validates('rol_id')
    def validate_rol_id(self, value, **kwargs):
        """rol_id debe ser un ID válido."""
        if value is None or value <= 0:
            raise ValidationError('El rol_id debe ser un número positivo.')


class UsuarioUpdateSchema(Schema):
    """Schema para actualización de Usuario (PUT/PATCH).
    
    Todos los campos son opcionales en PATCH.
    PUT requeriría todos los campos obligatorios.
    """
    
    nombre = fields.Str(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo nombre del usuario',
            'example': 'Angel Vidal Fernández (Modificado)'
        }
    )
    email = fields.Email(
        required=False,
        allow_none=False,
        metadata={
            'description': 'Nuevo email del usuario',
            'example': 'nuevo_email@abanca.com'
        }
    )
    rol_id = fields.Int(
        required=False,
        metadata={
            'description': 'Nuevo rol del usuario',
            'example': 3
        }
    )
    academia_id = fields.Int(
        required=False,
        allow_none=True,
        metadata={
            'description': 'Nueva academia del usuario',
            'example': 2
        }
    )
    password = fields.Str(
        required=False,
        load_only=True,
        metadata={
            'description': 'Nueva contraseña del usuario',
            'example': 'NuevaPassword123!'
        }
    )
    estado = fields.Str(
        required=False,
        metadata={
            'description': 'Nuevo estado del usuario',
            'example': 'Bloqueado',
            'enum': ['Activo', 'Bloqueado', 'Baja']
        }
    )
    
    # Campos inmutables (se aceptan pero se ignoran)
    fecha_alta = fields.DateTime(required=False, load_only=True)
    fecha_baja = fields.DateTime(required=False, load_only=True)

    @validates('nombre')
    def validate_nombre(self, value, **kwargs):
        if value is not None and (not value or not value.strip()):
            raise ValidationError('El nombre no puede estar vacío.')
        if value is not None and len(value.strip()) < 3:
            raise ValidationError('El nombre debe tener al menos 3 caracteres.')

    @validates('email')
    def validate_email(self, value, **kwargs):
        if value is not None:
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, value):
                raise ValidationError('El email no tiene un formato válido.')

    @validates('password')
    def validate_password(self, value, **kwargs):
        if value is not None and value.strip():
            if len(value) < 6:
                raise ValidationError('La contraseña debe tener al menos 6 caracteres.')

    @validates('estado')
    def validate_estado(self, value, **kwargs):
        if value is not None and value not in ('Activo', 'Bloqueado', 'Baja'):
            raise ValidationError("El estado debe ser 'Activo', 'Bloqueado' o 'Baja'.")

    @validates_schema
    def validate_at_least_one_field(self, data, **kwargs):
        """Al menos un campo debe estar presente para actualizar."""
        updatable_fields = {'nombre', 'email', 'rol_id', 'academia_id', 'password', 'estado'}
        if not any(field in data for field in updatable_fields):
            raise ValidationError('Debe proporcionar al menos un campo para actualizar.')
