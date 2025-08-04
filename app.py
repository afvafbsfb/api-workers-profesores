import os
from flask import Flask, request, jsonify, send_from_directory
from vlodeiro.secretaria.interfaces.flask_routes import secretaria_bp
from datetime import datetime
from vlodeiro.secretaria.infrastructure.repositorio_mysql import ClaseMySQLRepository
from dotenv import load_dotenv

from vlodeiro.secretaria.domain.models import db, Turno  # Importa SQLAlchemy y modelos

load_dotenv()

app = Flask(__name__)
app.register_blueprint(secretaria_bp, url_prefix='/vlodeiro/secretaria')
print(app.url_map)

# Configuración de la base de datos usando variables de entorno
def get_env_var(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Falta la variable de entorno: {name}")
    return value

DB_USER = get_env_var('DB_USER')
DB_PASS = get_env_var('DB_PASS')
DB_HOST = get_env_var('DB_HOST')
DB_PORT = get_env_var('DB_PORT')
DB_NAME = get_env_var('DB_NAME')
API_KEY = get_env_var('API_KEY')

SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

app.debug = True  # Opcional: activa modo debug

def ok(result=None, **extra):
    return jsonify({"ok": True, "result": result, **extra})

def err(code, hint=None, status=400):
    return jsonify({"ok": False, "error": code, "hint": hint}), status

def _build():
    try:
        return open('.build', encoding='utf-8').read().strip()
    except Exception:
        return None

@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    resp.headers["X-LiteSpeed-Cache-Control"] = "no-store"
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
def command():
    if request.headers.get("X-Api-Key") != API_KEY:
        return err("unauthorized", status=401)
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").lower()
    args = data.get("args") or {}
    if action == "ping":
        return ok("pong")
    return err("unknown_action", action)

@app.route("/debug", methods=["GET"])
def debug():
    return "Flask está vivo"

import logging
logging.basicConfig(filename='/home/s018fbe6/workers-api/tmp/flask_error.log', level=logging.ERROR)

@app.route("/vlodeiro/secretaria/turnos", methods=["GET"])
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
        return jsonify({"ok": False, "error": str(e), "trace": traceback.format_exc()}), 500