import os
from flask import request, current_app, jsonify
from functools import wraps

def get_api_key():
    """Obtiene la API Key desde variables de entorno, según el entorno de ejecución."""
    env = os.getenv('APP_ENV', 'development').strip().lower()
    return (
        os.getenv('API_KEY')
        or (os.getenv('API_KEY_PROD') if env in ('prod', 'production') else os.getenv('API_KEY_DEV'))
        or 'devkey'
    )

API_KEY = get_api_key()

PUBLIC_PATHS = ("/docs", "/openapi.yml")

def require_api_key(f):
    """Decorador para requerir API Key en endpoints concretos."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-Api-Key")
        if api_key != API_KEY:
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def enforce_api_key_globally():
    """Función para usar en before_request y proteger toda la API salvo rutas públicas."""
    if request.method == 'OPTIONS':
        return None
    raw_path = request.path or '/'
    if raw_path in PUBLIC_PATHS:
        return None
    api_key = request.headers.get('X-Api-Key')
    if api_key != API_KEY:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401
    return None
