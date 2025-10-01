from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import os
from config import Config

# Crear instancia de SQLAlchemy
from models import db


def create_app():
    app = Flask(__name__)

    # asegurar que las variables de entorno de DB estén establecidas
    Config.set_environment_variables()

    # Configuración de la base de datos: usar explícitamente la URL definida en Config
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuración de la clave secreta para JWT
    app.config['JWT_SECRET_KEY'] = 'super-secret-key'

    # Inicializar extensiones
    db.init_app(app)
    jwt = JWTManager(app)

    # Registrar blueprints
    from src.usuarios.interfaces.usuarios_routes import usuarios_bp
    # Registrar el blueprint canónico de login desde src.usuarios para evitar colisiones
    from src.usuarios.login_routes import login_bp as usuarios_login_bp

    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(usuarios_login_bp, url_prefix='/auth')

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
