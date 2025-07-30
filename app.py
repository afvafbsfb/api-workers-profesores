import os
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", "pon-una-clave-larga")

def ok(result=None, **extra):
    return jsonify({"ok": True, "result": result, **extra})

def err(code, hint=None, status=400):
    return jsonify({"ok": False, "error": code, "hint": hint}), status

@app.get("/health")
def health():
    return ok(ts=datetime.utcnow().isoformat())

@app.post("/v1/command")
def command():
    if request.headers.get("X-Api-Key") != API_KEY:
        return err("unauthorized", status=401)
    data = request.get_json(silent=True) or {}
    action = data.get("action")
    args = data.get("args", {})

    if action == "ping":
        return ok("pong")

    return err("unknown_action", action)
