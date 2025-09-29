from flask import Blueprint, request, jsonify
from marshmallow import Schema, fields, ValidationError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from models import Usuario  # Modelo de usuario
from src.shared.security import verify_password, generate_access_token

# Crear Blueprint para las rutas de login
login_bp = Blueprint('login', __name__)

# Configurar Rate-Limiting
limiter = Limiter(get_remote_address, default_limits=["5 per minute"])

# Esquema para validar la entrada
class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)

# Ruta para el login
@login_bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # Limitar a 5 intentos por minuto
def login():
    try:
        # Validar entrada
        data = request.get_json()
        schema = LoginSchema()
        validated_data = schema.load(data)

        # Buscar usuario
        user = Usuario.query.filter_by(email=validated_data['email']).first()
        if not user:
            return jsonify({"error": "Usuario no encontrado"}), 404

        # Verificar estado del usuario
        if user.estado != 'Activo':
            return jsonify({"error": f"Usuario no está activo (estado: {user.estado})"}), 403

        # Verificar contraseña
        if not verify_password(validated_data['password'], user.password):
            return jsonify({"error": "Contraseña incorrecta"}), 401

        # Generar token
        token = generate_access_token(identity={"id": user.id, "roles": user.rol_id})

        return jsonify({"token": token}), 200

    except ValidationError as e:
        return jsonify({"error": e.messages}), 400