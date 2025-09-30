# --- INICIALIZACIÓN SEGURA PARA DEBUG ---
import traceback
init_error = None
try:
    import os
    from flask import Flask, request, jsonify, send_from_directory, current_app
    from flask_cors import CORS  # Para manejar CORS
    from flask_jwt_extended import JWTManager  # Para manejar JWT
    from dotenv import load_dotenv  # Para cargar variables de entorno desde un archivo .env
    from auth_module import enforce_jwt_globally, require_jwt  # Importa funciones específicas para la validación de JWT
    from config import Config  # Importa la clase Config para la configuración de la base de datos
    from datetime import datetime, timezone
    # from vlodeiro.secretaria.infrastructure.repositorio_mysql import TurnoMySQLRepository
    # Dotenv: opcional en desarrollo. Si no está instalado, usa no-op
    try:
        from dotenv import load_dotenv as _load_dotenv
    except Exception:
        def _load_dotenv(*args, **kwargs):
            return False
    from functools import wraps
    import models  # Importa SQLAlchemy y modelos
    from models import db

    app = Flask(__name__)


    # --- LOGGING DE ERRORES ---
    import logging
    from logging.handlers import RotatingFileHandler
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    handler = RotatingFileHandler('tmp/flask_error.log', maxBytes=100000, backupCount=3)
    handler.setLevel(logging.ERROR)
    app.logger.addHandler(handler)
    # --- FIN LOGGING ---

    # --- DEBUG (activar solo para depuración temporal) ---
    # Para activar el modo debug, descomenta la siguiente línea:
    app.debug = True
    #
    # IMPORTANTE: Vuelve a comentar esta línea antes de subir a producción.
    # --- FIN DEBUG ---
    # Permite CORS para cualquier origen (útil para pruebas, restringe en producción)
    CORS(app, resources={r"/*": {"origins": "*"}})
    try:
        if not os.path.exists('tmp'):
            os.makedirs('tmp')
        with open('tmp/blueprint_debug.log', 'a', encoding='utf-8') as f:
            f.write("[DEBUG] Blueprint secretaria_bp registrado\n")
            f.write("[DEBUG] Mapeo de rutas:\n")
            f.write(str(app.url_map) + "\n")
    except Exception as log_err:
        print("[DEBUG] Error escribiendo blueprint_debug.log:", log_err)
    db = models.db

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

    db_config = Config.get_database_config()

    # Configuración de la base de datos: usar Config para construir/leer la URL
    from config import Config as _Config
    _Config.set_environment_variables()
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')

    # Log adicional para verificar si se sobrescribe SQLALCHEMY_DATABASE_URI en algún punto
    print(f"[DEBUG] SQLALCHEMY_DATABASE_URI después de configuración inicial: {app.config['SQLALCHEMY_DATABASE_URI']}", flush=True)

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Evitar registrar SQLAlchemy varias veces
    if not hasattr(db, '_is_initialized'):
        db.init_app(app)
        db._is_initialized = True

    # Debug solo si FLASK_DEBUG está activo explícitamente
    app.debug = str(os.getenv("FLASK_DEBUG", "0")).lower() in ("1", "true", "yes")

    def ok(result=None, **extra):
        return jsonify({"ok": True, "result": result, **extra})

    def err(code, hint=None, status=400):
        # Sanitiza errores en producción
        if current_app.config.get("ENV") == "production":
            return jsonify({"ok": False, "error": code}), status
        return jsonify({"ok": False, "error": code, "hint": hint}), status

    # Permitir acceso público al endpoint /auth/login
    @app.before_request
    def _enforce_api_key_globally():
        public_paths = ["/auth/login", "/docs", "/openapi.yml", "/openapi-rest.yaml", "/health", "/"]
        print(f"[DEBUG][AUTH] before_request ejecutado. Path: {request.path} | Method: {request.method}", flush=True)
        if request.path in public_paths or request.path.startswith("/static/"):
            print(f"[DEBUG][AUTH] Ruta pública: {request.path}", flush=True)
            return None  # Permite acceso público sin validar el encabezado Authorization
        print(f"[DEBUG][AUTH] Ruta protegida: {request.path}", flush=True)
        return enforce_jwt_globally()

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
    jwt = JWTManager(app)

    # Middleware para validar JWT globalmente
    app.before_request(enforce_jwt_globally)

    def _build():
        try:
            return open('.build', encoding='utf-8').read().strip()
        except Exception:
            return None


    @app.after_request
    def set_security_and_cors_headers(resp):
        resp.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-LiteSpeed-Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), microphone=()",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        })
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
        import sys
        import logging
        print("Entrando en /health", file=sys.stderr)
        logging.getLogger().info("Entrando en /health (logger root)")
        try:
            return ok(ts=datetime.now(timezone.utc).isoformat(), build=_build())
        except Exception as e:
            import traceback
            print(f"[HEALTH ERROR] {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            logging.getLogger().error(f"[HEALTH ERROR] {e}\n{traceback.format_exc()}")
            # Muestra el error y el traceback en la respuesta para depuración
            return jsonify({
                "ok": False,
                "error": str(e),
                "trace": traceback.format_exc()
            }), 500


    @app.route("/openapi.yml", methods=["GET"])
    def openapi_spec():
        return send_from_directory(".", "openapi.yml", mimetype="text/yaml")

    @app.route("/openapi-rest.yaml", methods=["GET"])
    def openapi_rest_spec():
        return send_from_directory("docs", "openapi-rest.yaml", mimetype="text/yaml")

    @app.route("/docs", methods=["GET"])
    def docs_index():
        # Sirve la UI de Swagger ya configurada con la especificación de producción
        return send_from_directory("docs", "index.html", mimetype="text/html")


    @app.route("/debug", methods=["GET"])
    def debug():
        return "Flask está vivo"

    import logging
    import os
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    logging.basicConfig(filename='tmp/flask_error.log', level=logging.ERROR)


    # Nota: el registro de blueprints se realiza más abajo una vez que
    # se importan `usuarios_bp` y `login_bp`. Evitamos hacerlo aquí
    # para que `main` pueda ser importado por scripts (como init_db.py)
    # sin intentar registrar blueprints antes de sus importaciones.

    # Agregar log para listar todas las rutas registradas
    # Forzar el log a la consola con flush=True
    # Escribir el log de rutas tanto en la consola como en el archivo de depuración
    # Agregar mensaje de depuración para confirmar ejecución
    print("[DEBUG] Intentando escribir rutas registradas...", flush=True)
    rutas = [rule.rule for rule in app.url_map.iter_rules()]
    print("Rutas registradas:", rutas, flush=True)
    with open('tmp/blueprint_debug.log', 'a', encoding='utf-8') as f:
        f.write(f"Rutas registradas: {rutas}\n")

    # Configurar cabeceras de seguridad y CORS
    @app.after_request
    def set_security_and_cors_headers(resp):
        resp.headers.update({
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-LiteSpeed-Cache-Control": "no-store",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), microphone=()",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        })
        return resp

    # Depuración para verificar el entorno y la URI de la base de datos
    print(f"APP_ENV: {APP_ENV}")
    print(f"SQLALCHEMY_DATABASE_URI final: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Agregar un log inicial para confirmar que main.py se está ejecutando
    print("[DEBUG] main.py se está ejecutando", flush=True)

    # Log the final SQLALCHEMY_DATABASE_URI for debugging
    print(f"[DEBUG] Final SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}", flush=True)

    # Agregar un registro de depuración al inicio para verificar APP_ENV
    print(f"[DEBUG] APP_ENV al inicio: {os.getenv('APP_ENV')}", flush=True)

    # Asegurar que SQLALCHEMY_BINDS esté desactivado durante las pruebas
    if APP_ENV == 'testing':
        app.config['SQLALCHEMY_BINDS'] = None  # Desactiva cualquier configuración adicional de binds
        print(f"[DEBUG] SQLALCHEMY_BINDS desactivado en pruebas: {app.config['SQLALCHEMY_BINDS']}", flush=True)

    # Add debug logs to trace SQLALCHEMY_DATABASE_URI
    print(f"[DEBUG] APP_ENV at start: {APP_ENV}", flush=True)
    print(f"[DEBUG] Initial SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}", flush=True)

    # Add a log after app.config is set
    print(f"[DEBUG] Final SQLALCHEMY_DATABASE_URI in app.config: {app.config['SQLALCHEMY_DATABASE_URI']}", flush=True)

    # No forzamos SQLite en testing: la URL viene de Config/DATABASE_URL

    # Add a final debug log to confirm the database URI
    print(f"[DEBUG] Final SQLALCHEMY_DATABASE_URI before app initialization: {SQLALCHEMY_DATABASE_URI}", flush=True)

    # Add debug log for SQLALCHEMY_BINDS
    print(f"[DEBUG] SQLALCHEMY_BINDS: {app.config.get('SQLALCHEMY_BINDS')}")

    # Asegurar que SQLALCHEMY_BINDS sea un diccionario vacío si no está configurado
    if app.config.get('SQLALCHEMY_BINDS') is None:
        app.config['SQLALCHEMY_BINDS'] = {}

    # Agregar registro para verificar el estado de db
    print("[DEBUG] Verificando estado de db antes de inicializar.", flush=True)
    print(f"[DEBUG] db: {db}", flush=True)
    print(f"[DEBUG] app.config: {app.config}", flush=True)

    # Registrar blueprints al inicio
    from src.usuarios.interfaces.usuarios_routes import usuarios_bp
    from src.usuarios.login_routes import login_bp
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(login_bp, url_prefix='/auth')
    print("[DEBUG] Blueprints registrados en main.py.", flush=True)

    # Inicialización de la base de datos:
    # La instancia `db` ya se inicializó más arriba (si no estaba inicializada).
    # No ejecutamos `create_all()` en el momento de importar `main` para
    # evitar efectos secundarios cuando otros scripts (p. ej. init_db.py)
    # importan este módulo. La creación de tablas debe hacerse explícitamente
    # por los scripts de mantenimiento o desde el bloque `if __name__ == '__main__'`.

    if __name__ == "__main__":
        app.run(host="0.0.0.0", port=5000, debug=True)
except Exception as e:
    init_error = traceback.format_exc()
    print(init_error)
    # Fallback: crea un app mínimo para que Gunicorn/Beanstalk no fallen
    from flask import Flask
    app = Flask(__name__)
    @app.route("/error")
    def error():
        return f"<pre>{init_error}</pre>", 500
