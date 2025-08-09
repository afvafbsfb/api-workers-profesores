
# --- INICIALIZACIÓN SEGURA PARA DEBUG ---
import traceback
init_error = None
try:
    import os
    from flask import Flask, request, jsonify, send_from_directory, current_app
    from vlodeiro.secretaria.interfaces.flask_routes import secretaria_bp
    # DDD: Importa blueprint de empresa
    from vlodeiro.empresa.interfaces.empresa_routes import empresa_bp
    from datetime import datetime, timezone
    # from vlodeiro.secretaria.infrastructure.repositorio_mysql import TurnoMySQLRepository
    ## from dotenv import load_dotenv
    from functools import wraps
    from models import db, Turno  # Importa SQLAlchemy y modelos
    # Validación de entrada
    from marshmallow import Schema, fields, ValidationError
    # Esquema de validación para /v1/command
    class CommandSchema(Schema):
        action = fields.Str(required=True)
        args = fields.Dict(load_default={})
    # Seguridad: CORS y headers
    from flask_cors import CORS

    ## load_dotenv()  # Desactivado para evitar sobrescribir variables de entorno

    app = Flask(__name__)
    # Permite CORS solo para dominios confiables (ajusta en producción)
    CORS(app, resources={r"/*": {"origins": ["http://localhost", "https://tudominio.com"]}}, supports_credentials=True)
    app.register_blueprint(secretaria_bp, url_prefix='/vlodeiro/secretaria')
    try:
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        with open('tmp/blueprint_debug.log', 'a', encoding='utf-8') as f:
            f.write("[DEBUG] Blueprint secretaria_bp registrado\n")
            f.write("[DEBUG] Mapeo de rutas:\n")
            f.write(str(app.url_map) + "\n")
    except Exception as log_err:
        print("[DEBUG] Error escribiendo blueprint_debug.log:", log_err)
    # DDD: Registra blueprint de empresa
    app.register_blueprint(empresa_bp, url_prefix='/vlodeiro/empresa')
    print(app.url_map)

    # Configuración de la base de datos usando variables de entorno
    def get_env_var(name):
        value = os.getenv(name)
        if not value:
            raise RuntimeError(f"Falta la variable de entorno: {name}")
        return value

    try:
        DB_USER = get_env_var('DB_USER')
        DB_PASS = get_env_var('DB_PASS')
        DB_HOST = get_env_var('DB_HOST')
        DB_PORT = get_env_var('DB_PORT')
        DB_NAME = get_env_var('DB_NAME')
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    except RuntimeError:
        # Si faltan variables, usa SQLite en local
        SQLALCHEMY_DATABASE_URI = "sqlite:///local.db"
    API_KEY = os.getenv('API_KEY', 'devkey')
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    app.debug = True  # Opcional: activa modo debug

    def ok(result=None, **extra):
        return jsonify({"ok": True, "result": result, **extra})

    def err(code, hint=None, status=400):
        # Sanitiza errores en producción
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": code}), status
        return jsonify({"ok": False, "error": code, "hint": hint}), status

    # Decorador para requerir API Key
    def require_api_key(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            api_key = request.headers.get("X-Api-Key")
            if api_key != API_KEY:
                return err("unauthorized", status=401)
            return f(*args, **kwargs)
        return decorated

    def _build():
        try:
            return open('.build', encoding='utf-8').read().strip()
        except Exception:
            return None

    @app.after_request
    def set_security_headers(resp):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        resp.headers["X-LiteSpeed-Cache-Control"] = "no-store"
        # Headers de seguridad
        resp.headers["X-Frame-Options"] = "DENY"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        resp.headers["Referrer-Policy"] = "no-referrer"
        resp.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
        return resp

    @app.route("/", methods=["GET"])
    def root():
        return ok(ts=datetime.now(timezone.utc).isoformat(), up=True, build=_build())

    @app.route("/health", methods=["GET"])
    def health():
        try:
            return ok(ts=datetime.now(timezone.utc).isoformat(), build=_build())
        except Exception as e:
            import traceback
            # Muestra el error y el traceback en la respuesta para depuración
            return jsonify({
                "ok": False,
                "error": str(e),
                "trace": traceback.format_exc()
            }), 500

    @app.route("/openapi.yml", methods=["GET"])
    def openapi_spec():
        return send_from_directory(".", "openapi.yml", mimetype="text/yaml")

    @app.route("/docs", methods=["GET"])
    def docs_index():
        # Sirve la UI de Swagger desde /docs
        return send_from_directory("docs", "index.html", mimetype="text/html")


    # ...existing code...

    @app.route("/debug", methods=["GET"])
    def debug():
        return "Flask está vivo"

    import logging
    import os
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    logging.basicConfig(filename='tmp/flask_error.log', level=logging.ERROR)


    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=True)
except Exception as e:
    init_error = traceback.format_exc()
    print(init_error)