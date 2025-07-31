import os
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)
API_KEY = os.getenv("API_KEY", "changeme")

def ok(result=None, **extra): return jsonify({"ok": True, "result": result, **extra})
def err(code, hint=None, status=400): return jsonify({"ok": False, "error": code, "hint": hint}), status

@app.route("/", methods=["GET"])
def root():
    return ok(ts=datetime.utcnow().isoformat(), up=True)

@app.route("/health", methods=["GET"])
def health():
    return ok(ts=datetime.utcnow().isoformat())

@app.route("/v1/command", methods=["POST"])
def command():
    if request.headers.get("X-Api-Key") != API_KEY:
        return err("unauthorized", status=401)
    data = request.get_json(silent=True) or {}
    if (data.get("action") or "").lower() == "ping":
        return ok("pong")
    return err("unknown_action", data.get("action"))