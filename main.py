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
    # Importaciones actualizadas tras la refactorización
    from src.shared.database import db
    from src.academias.infrastructure.models import Academia, Aula, Curso, HorarioCurso
    from src.usuarios.infrastructure.models import Usuario, Rol, RefreshToken, UserLoginLog
    from src.alumnos.infrastructure.models import Alumno, Inscripcion
    from src.profesores.infrastructure.models import CursoProfesores, Sesion

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
    # Nota: no forzamos app.debug aquí para evitar inconsistencias con
    # las variables de entorno (FLASK_DEBUG/DEBUG). El valor final se
    # determina más abajo en base a FLASK_DEBUG.
    # --- FIN DEBUG ---
    # Permite CORS para cualquier origen (útil para pruebas, restringe en producción)
    CORS(app, resources={r"/*": {"origins": "*"}})
    # Asegurar directorio tmp para logs
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    db = db

    # Configuración por entorno y seguridad (dev/prod) + DB
    def _env(name, default=None):
        return os.getenv(name, default)

    APP_ENV = (_env('APP_ENV', 'development') or 'development').strip().lower()

    # Forcing APP_ENV to log its value for debugging purposes
    print(f"[DEBUG] APP_ENV: {APP_ENV}", flush=True)

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
        or (
            _db_uri_from_components('DB_PROD_')
            if APP_ENV in ('prod', 'production')
            else _db_uri_from_components('DB_DEV_')
        )
        or _db_uri_from_components('DB_')
    )

    # Log the selected database URI for debugging
    print(f"[DEBUG] Selected SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}", flush=True)

    db_config = Config.get_database_config()

    # Configuración de la base de datos: permitir que la clase Config
    # establezca variables de entorno si es necesario, pero no depender
    # únicamente de ello. Elegimos la URL en este orden de precedencia:
    # 1) VARIABLE de entorno DATABASE_URL (más explícita)
    # 2) la URI calculada en la variable SQLALCHEMY_DATABASE_URI
    from config import Config as _Config
    try:
        _Config.set_environment_variables()
    except Exception:
        # No fatal: seguir con variables de entorno ya presentes o con la URI calculada
        pass

    final_db_uri = os.getenv('DATABASE_URL') or SQLALCHEMY_DATABASE_URI
    # Seguridad: exigir explicitamente una URL de conexión a la BBDD
    if not final_db_uri:
        raise RuntimeError(
            "DATABASE_URL is required. Set the DATABASE_URL environment variable with your connection string."
        )

    app.config['SQLALCHEMY_DATABASE_URI'] = final_db_uri

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
        # Normalize path comparison so '/auth/login/' and '/auth/login' both match
        public_paths = [
            "/auth/login",
            "/docs",
            "/openapi.yml",
            "/openapi-rest.yaml",
            "/openapi.json",
            "/openapi-auto.json",
            "/openapi-auto.yml",
            "/openapi-rest.yml",
            "/health",
            "/"
        ]
        raw_path = request.path
        norm_path = raw_path if raw_path == '/' else raw_path.rstrip('/')
        norm_public = [p if p == '/' else p.rstrip('/') for p in public_paths]
        print(f"[DEBUG][AUTH] before_request ejecutado. Path: {raw_path} | Normalized: {norm_path} | Method: {request.method}", flush=True)
        if norm_path in norm_public or request.path.startswith("/static/"):
            print(f"[DEBUG][AUTH] Ruta pública: {raw_path}", flush=True)
            return None  # Permite acceso público sin validar el encabezado Authorization
        print(f"[DEBUG][AUTH] Ruta protegida: {request.path}", flush=True)
        return enforce_jwt_globally()

    # Configurar JWT
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
    jwt = JWTManager(app)

    # Nota: la validación JWT se realiza a través de la función
    # `_enforce_api_key_globally` definida más arriba, que permite
    # rutas públicas y llama a `enforce_jwt_globally` cuando procede.

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
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
            "Referrer-Policy": "no-referrer",
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

    @app.route('/openapi-auto.json', methods=['GET'])
    def openapi_auto_json():
        # Serve the generated spec from docs/openapi-auto.json if present
        import os
        path = os.path.join(os.getcwd(), 'docs', 'openapi-auto.json')
        if os.path.exists(path):
            return send_from_directory(os.path.join(os.getcwd(), 'docs'), 'openapi-auto.json', mimetype='application/json')
        return jsonify({}), 404

    @app.route('/openapi.json', methods=['GET'])
    def openapi_json():
        # Try to serve an app-provided spec or fall back to docs/openapi-auto.json
        try:
            from src.docs.swagger import openapi_json as swagger_openapi
            return swagger_openapi()
        except Exception:
            import os
            path = os.path.join(os.getcwd(), 'docs', 'openapi-auto.json')
            if os.path.exists(path):
                return send_from_directory(os.path.join(os.getcwd(), 'docs'), 'openapi-auto.json', mimetype='application/json')
            return jsonify({}), 404

    @app.route("/docs", methods=["GET"])
    def docs_index():
        # Sirve la UI de Swagger: intenta primero docs/index.html, luego docs/swagger-ui.html
        import os
        docs_dir = os.path.join(os.getcwd(), 'docs')
        index_path = os.path.join(docs_dir, 'index.html')
        swagger_ui_path = os.path.join(docs_dir, 'swagger-ui.html')
        if os.path.exists(index_path):
            return send_from_directory('docs', 'index.html', mimetype='text/html')
        if os.path.exists(swagger_ui_path):
            return send_from_directory('docs', 'swagger-ui.html', mimetype='text/html')

        # Fallback: si existe el blueprint que sirve una UI embebida, úsalo
        try:
            from src.docs.swagger import docs_ui as embedded_docs_ui
            return embedded_docs_ui()
        except Exception:
            return jsonify({"ok": False, "error": "docs_not_found"}), 404


    @app.route("/debug", methods=["GET"])
    def debug():
        return "Flask está vivo"

    import logging
    import os
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    logging.basicConfig(filename='tmp/flask_error.log', level=logging.ERROR)
    logging.basicConfig(level=logging.DEBUG)  # Agregado para asegurar que los logs de depuración se muestren en consola

    from logging import StreamHandler

    # Ensure logs are printed to the console
    console_handler = StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(console_handler)


    # Nota: el registro de blueprints se realiza más abajo una vez que
    # se importan `usuarios_bp` y `login_bp`. Evitamos hacerlo aquí
    # para que `main` pueda ser importado por scripts (como init_db.py)
    # sin intentar registrar blueprints antes de sus importaciones.

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

    # Depuración mínima: entorno y URI final de BBDD
    print(f"APP_ENV: {APP_ENV}")
    print(f"SQLALCHEMY_DATABASE_URI: {app.config['SQLALCHEMY_DATABASE_URI']}")

    # Dump relevant environment variables (mask secrets)
    def mask(v):
        try:
            if v is None:
                return "<null>"
            s = str(v)
            if s.strip() == "":
                return "<blank>"
            if len(s) <= 8:
                return s[:4] + "..."
            return s[:4] + "..."
        except Exception:
            return "<err>"

    env_keys = [
        'APP_ENV', 'FLASK_DEBUG', 'DEBUG', 'JWT_SECRET_KEY', 'JWT_DELEGATION_SECRET',
        'DATABASE_URL', 'SQLALCHEMY_DATABASE_URI', 'AWS_LAMBDA_FUNCTION_NAME', 'ACADEMIA_API_BASEURL', 'ACADEMIA_API_KEY'
    ]
    print("[StartupEnv][INFO] Dumping selected environment variables (masked where appropriate):")
    for k in env_keys:
        try:
            v = os.getenv(k)
            if k.lower().find('secret') != -1 or k.lower().find('key') != -1 or k.lower().find('pass') != -1:
                print(f"[StartupEnv][ENV] {k}={mask(v)}")
            else:
                print(f"[StartupEnv][ENV] {k}={v}")
        except Exception as e:
            print(f"[StartupEnv][ENV] {k}=<error:{e}>")

        # Additionally, print sha256 and length of delegation secret (safe, non-reversible)
        try:
            ds = os.getenv('JWT_DELEGATION_SECRET')
            if ds is None:
                print("[StartupEnv][ENV] JWT_DELEGATION_SECRET_SHA256=<null>, JWT_DELEGATION_SECRET_LEN=0")
            elif ds == "":
                print("[StartupEnv][ENV] JWT_DELEGATION_SECRET_SHA256=<blank>, JWT_DELEGATION_SECRET_LEN=0")
            else:
                import hashlib
                h = hashlib.sha256(ds.encode('utf-8')).hexdigest()
                print(f"[StartupEnv][ENV] JWT_DELEGATION_SECRET_SHA256={h}, JWT_DELEGATION_SECRET_LEN={len(ds)}")
        except Exception as e:
            print(f"[StartupEnv][ENV] JWT_DELEGATION_SECRET_SHA256=<err>, JWT_DELEGATION_SECRET_LEN=<err> - {e}")

    # If running with debug enabled or explicit dump flag, also print unmasked values
    try:
        dump_unmasked = (str(os.getenv('DUMP_SECRETS', '')).lower() in ('1', 'true', 'yes')) or app.debug
        if dump_unmasked:
            print("[StartupEnv][DEBUG] Dumping UNMASKED environment variables because app.debug or DUMP_SECRETS is set:")
            for k in env_keys:
                try:
                    v = os.getenv(k)
                    print(f"[StartupEnv][DEBUG] {k}={v}")
                except Exception as e:
                    print(f"[StartupEnv][DEBUG] {k}=<error:{e}>")
    except Exception:
        pass

    # Asegurar que SQLALCHEMY_BINDS esté desactivado durante las pruebas
    if APP_ENV == 'testing':
        app.config['SQLALCHEMY_BINDS'] = None  # Desactiva cualquier configuración adicional de binds
        print(f"SQLALCHEMY_BINDS desactivado en pruebas: {app.config['SQLALCHEMY_BINDS']}")

    # Asegurar que SQLALCHEMY_BINDS sea un diccionario vacío si no está configurado
    if app.config.get('SQLALCHEMY_BINDS') is None:
        app.config['SQLALCHEMY_BINDS'] = {}
    # Registrar blueprints al inicio
    from src.usuarios.interfaces.usuarios_routes import usuarios_bp
    from src.usuarios.interfaces.roles_routes import roles_bp
    from src.usuarios.login_routes import login_bp
    from src.academias.interfaces.flask.academias_routes import academias_bp
    from src.academias.interfaces.flask.tarifas_routes import tarifas_bp
    app.register_blueprint(usuarios_bp, url_prefix='/usuarios')
    app.register_blueprint(roles_bp, url_prefix='/roles')
    app.register_blueprint(login_bp, url_prefix='/auth')
    app.register_blueprint(academias_bp, url_prefix='/academias')
    app.register_blueprint(tarifas_bp, url_prefix='/tarifas')

    # Log rutas registradas DESPUÉS de registrar blueprints
    rutas = [rule.rule for rule in app.url_map.iter_rules()]
    print(f"Rutas registradas: {rutas}")
    print("Blueprints registrados en main.py.")

    # Inicialización de la base de datos:
    # La instancia `db` ya se inicializó más arriba (si no estaba inicializada).
    # No ejecutamos `create_all()` en el momento de importar `main` para
    # evitar efectos secundarios cuando otros scripts (p. ej. init_db.py)
    # importan este módulo. La creación de tablas debe hacerse explícitamente
    # por los scripts de mantenimiento o desde el bloque `if __name__ == '__main__'`.

    if __name__ == "__main__":
        # Use the app.debug value which is derived from FLASK_DEBUG
        app.run(host="0.0.0.0", port=5000, debug=app.debug)
except Exception as e:
    init_error = traceback.format_exc()
    print(init_error)
    # Fallback: crea un app mínimo para que Gunicorn/Beanstalk no fallen
    from flask import Flask
    app = Flask(__name__)
    @app.route("/error")
    def error():
        return f"<pre>{init_error}</pre>", 500
