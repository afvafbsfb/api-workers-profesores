import os
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", "changeme")

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
    # sirve el archivo OpenAPI desde la raíz del proyecto
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
