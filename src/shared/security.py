from argon2 import PasswordHasher
from flask_jwt_extended import create_access_token
import os

# Inicializar PasswordHasher
ph = PasswordHasher()

# Clave secreta para JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "clave_secreta_segura")

# Función para hashear contraseñas
def hash_password(password: str) -> str:
    return ph.hash(password)

# Función para verificar contraseñas
def verify_password(password: str, hashed_password: str) -> bool:
    try:
        ph.verify(hashed_password, password)
        return True
    except Exception:
        return False

# Función para generar un token de acceso
def generate_access_token(identity: dict) -> str:
    return create_access_token(identity=identity)