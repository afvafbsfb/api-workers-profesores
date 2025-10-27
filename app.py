from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import os
from config import Config

# Crear instancia de SQLAlchemy
from src.shared.database import db


def create_app():
    app = Flask(__name__)

    # asegurar que las variables de entorno de DB estén establecidas
    Config.set_environment_variables()

    # Configuración de la base de datos: usar explícitamente la URL definida en Config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Estabilizar conexiones del pool (evitar 'MySQL server has gone away')
    # pool_pre_ping valida la conexión antes de usarla y pool_recycle la renueva periódicamente
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,
        # reciclar conexiones antes de que caduque el wait_timeout del servidor (p. ej., 300s)
        # 280s es un valor conservador para dev; ajustar según entorno si es necesario
        "pool_recycle": 280,
    }

    # Configuración de la clave secreta para JWT: preferimos la variable de entorno
    import hashlib
    jwt_secret = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
    app.config['JWT_SECRET_KEY'] = jwt_secret
    # Loguear una vista enmascarada (prefijo SHA-256 corto) para ayudar a depurar
    if os.getenv('DEBUG', '0').lower() in ('1', 'true', 'yes'):
        try:
            h = hashlib.sha256(jwt_secret.encode('utf-8')).digest()
            short = ''.join(f"{b:02x}" for b in h[:4])
            print(f"[DEBUG] JWT_SECRET_KEY SHA256 prefix: {short}")
        except Exception:
            pass

    # Inicializar extensiones
    db.init_app(app)
    jwt = JWTManager(app)

    # Registrar blueprints
    from src.usuarios.interfaces.usuarios_routes import usuarios_bp
    # Registrar el blueprint canónico de login desde src.usuarios para evitar colisiones
    from src.usuarios.login_routes import login_bp as usuarios_login_bp
    from src.academias.interfaces.flask.academias_routes import academias_bp
    from src.academias.interfaces.flask.tarifas_routes import tarifas_bp

    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(usuarios_login_bp, url_prefix='/auth')
    app.register_blueprint(academias_bp, url_prefix='/academias')
    app.register_blueprint(tarifas_bp, url_prefix='/tarifas')
    # Register docs blueprint (serves /openapi.json and /docs)
    try:
        from src.docs.swagger import swagger_bp
        app.register_blueprint(swagger_bp)
    except Exception:
        pass

    # Ruta de salud
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    # Compatibilidad: exponer explícitamente /auth/login delegando en AuthService
    try:
        from src.autenticacion.application.services import AuthService
        @app.route('/auth/login', methods=['POST'])
        def auth_login_compat():
            data = request.get_json() or {}
            email = data.get('email')
            password = data.get('password')
            ok, result = AuthService.login(email, password)
            if not ok:
                return jsonify({"ok": False, **result}), 401
            return jsonify({"ok": True, "tokens": result['tokens']}), 200
    except Exception:
        # Si por alguna razón el AuthService no está disponible, no romper la app
        pass

    return app

if __name__ == '__main__':
    app = create_app()
    print("[DEBUG] app.py se está ejecutando", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
