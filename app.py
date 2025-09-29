from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
import os

# Crear instancia de SQLAlchemy
from models import db

def create_app():
    app = Flask(__name__)

    # Configuración de la base de datos
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///local.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configuración de la clave secreta para JWT
    app.config['JWT_SECRET_KEY'] = 'super-secret-key'

    # Inicializar extensiones
    db.init_app(app)
    jwt = JWTManager(app)

    # Registrar blueprints
    from src.usuarios.interfaces.usuarios_routes import usuarios_bp
    from auth import login_bp

    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(login_bp)

    # Ruta de salud
    @app.route('/health')
    def health():
        return {'status': 'ok'}

    return app

if __name__ == '__main__':
    app = create_app()
    print("[DEBUG] app.py se está ejecutando", flush=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
