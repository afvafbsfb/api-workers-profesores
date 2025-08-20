
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
    # Dotenv: opcional en desarrollo. Si no está instalado, usa no-op
    try:
        from dotenv import load_dotenv as _load_dotenv
    except Exception:
        def _load_dotenv(*args, **kwargs):
            return False
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
    # Autenticación API Key modularizada
    import auth

    # Carga variables desde .env si existe, sin sobrescribir variables del proceso
    # Seguro en producción (no hay .env en el servidor y override=False)
    try:
        _load_dotenv(override=False)
    except Exception:
        pass

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

    # Configuración por entorno y seguridad (dev/prod) + DB
    def _env(name, default=None):
        return os.getenv(name, default)

    APP_ENV = (_env('APP_ENV', 'development') or 'development').strip().lower()

    def _db_uri_from_components(prefix: str = ''):
        """
        Construye la URI a partir de variables de entorno con prefijos:
        - prefix='DB_DEV_'  -> usa DB_DEV_HOST, DB_DEV_PORT, DB_DEV_USER, DB_DEV_PASS, DB_DEV_NAME
        - prefix='DB_PROD_' -> usa DB_PROD_HOST, ...
        - prefix='DB_'      -> usa DB_HOST, DB_PORT, DB_USER, DB_PASS, DB_NAME
        """
        u = _env(f'{prefix}USER')
        p = _env(f'{prefix}PASS')
        h = _env(f'{prefix}HOST')
        pt = _env(f'{prefix}PORT')
        n = _env(f'{prefix}NAME')
        if all([u, h, pt, n]) and p is not None:
            return f"mysql+pymysql://{u}:{p}@{h}:{pt}/{n}"
        return None

    # Precedencia para DB: DATABASE_URL/SQLALCHEMY_DATABASE_URI > env por entorno > env genérico > SQLite local (/tmp en Lambda)
    is_lambda = bool(_env('AWS_LAMBDA_FUNCTION_NAME'))
    SQLALCHEMY_DATABASE_URI = (
        _env('DATABASE_URL')
        or _env('SQLALCHEMY_DATABASE_URI')
        or (_db_uri_from_components('DB_PROD_') if APP_ENV in ('prod', 'production') else _db_uri_from_components('DB_DEV_'))
        or _db_uri_from_components('DB_')
        or ("sqlite:////tmp/local.db" if is_lambda else "sqlite:///local.db")
    )


    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    # Debug solo si FLASK_DEBUG está activo explícitamente
    app.debug = str(os.getenv("FLASK_DEBUG", "0")).lower() in ("1", "true", "yes")

    def ok(result=None, **extra):
        return jsonify({"ok": True, "result": result, **extra})

    def err(code, hint=None, status=400):
        # Sanitiza errores en producción
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": code}), status
        return jsonify({"ok": False, "error": code, "hint": hint}), status

    # Enforce global API Key salvo rutas públicas mínimas (docs y spec)
    @app.before_request
    def _enforce_api_key_globally():
        print(f"[DEBUG] Path recibido: {request.path}", flush=True)
        return auth.enforce_api_key_globally()

    def _build():
        try:
            return open('.build', encoding='utf-8').read().strip()
        except Exception:
            return None


    @app.after_request
    def set_security_and_cors_headers(resp):
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
        # CORS
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
        return resp

    # Handler global para OPTIONS (catch-all)
    @app.route('/<path:path>', methods=['OPTIONS'])
    def options_handler(path):
        return '', 204

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