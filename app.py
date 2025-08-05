import os
from flask import Flask, request, jsonify, send_from_directory, current_app
from vlodeiro.secretaria.interfaces.flask_routes import secretaria_bp
# DDD: Importa blueprint de empresa
from vlodeiro.empresa.interfaces.empresa_routes import empresa_bp
from datetime import datetime
from vlodeiro.secretaria.infrastructure.repositorio_mysql import ClaseMySQLRepository
## from dotenv import load_dotenv
from functools import wraps
from models import db, Turno  # Importa SQLAlchemy y modelos
# Validación de entrada
from marshmallow import Schema, fields, ValidationError
# Esquema de validación para /v1/command
class CommandSchema(Schema):
    action = fields.Str(required=True)
    args = fields.Dict(missing={})
# Seguridad: CORS y headers
from flask_cors import CORS

## load_dotenv()  # Desactivado para evitar sobrescribir variables de entorno


app = Flask(__name__)
# Permite CORS solo para dominios confiables (ajusta en producción)
CORS(app, resources={r"/*": {"origins": ["http://localhost", "https://tudominio.com"]}}, supports_credentials=True)
app.register_blueprint(secretaria_bp, url_prefix='/vlodeiro/secretaria')
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
    return ok(ts=datetime.utcnow().isoformat(), up=True, build=_build())

@app.route("/health", methods=["GET"])
def health():
    return ok(ts=datetime.utcnow().isoformat(), build=_build())

@app.route("/openapi.yml", methods=["GET"])
def openapi_spec():
    return send_from_directory(".", "openapi.yml", mimetype="text/yaml")

@app.route("/v1/command", methods=["POST"])
@require_api_key
def command():
    data = request.get_json(silent=True) or {}
    # Validación y sanitización
    try:
        validated = CommandSchema().load(data)
    except ValidationError as ve:
        return err("invalid_input", hint=ve.messages, status=400)
    action = validated["action"].lower()
    args = validated["args"]
    if action == "ping":
        return ok("pong")
    return err("unknown_action", action)

@app.route("/debug", methods=["GET"])
def debug():
    return "Flask está vivo"

import logging
import os
if not os.path.exists('tmp'):
    os.makedirs('tmp')
logging.basicConfig(filename='tmp/flask_error.log', level=logging.ERROR)

@app.route("/vlodeiro/secretaria/turnos", methods=["GET"])
@require_api_key
def listar_turnos():
    try:
        repo = ClaseMySQLRepository()
        turnos = repo.listar_turnos()
        print("Turnos encontrados:", turnos)
        return jsonify([
            {
                "id": getattr(t, "id", None),
                "dia": getattr(t, "dia_semana", None),
                "hora": getattr(t, "hora", None) and t.hora.strftime('%H:%M'),
                "tipo": getattr(t, "tipo_alumno", None),
                "duracion": getattr(t, "duracion", None),
                "capacidad": getattr(t, "capacidad", None)
            } for t in turnos
        ])
    except Exception as e:
        import traceback
        logging.error(traceback.format_exc())
        print("ERROR EN TURNOS:", e)
        print(traceback.format_exc())
        # Sanitiza error en producción
        if current_app.config.get("ENV") == "production":
            return err("internal_error", status=500)
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)