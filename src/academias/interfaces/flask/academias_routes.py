from flask import Blueprint, request, jsonify, g
from src.shared.middleware.auth import require_role
from models import Academia, db
from config import Config

academias_bp = Blueprint('academias', __name__)


@academias_bp.route('', methods=['POST'])
@require_role('Admin_plataforma')
def crear_academia():
    # Enhanced debugging to trace 422 issues
    if Config.DEBUG:
        try:
            user = getattr(g, 'current_user', None)
            print(f"[DEBUG][academias] g.current_user: {user}")
        except Exception as _:
            print(f"[DEBUG][academias] g.current_user: <error al acceder>")
        print(f"[DEBUG][academias] Request headers: {dict(request.headers)}")
        print(f"[DEBUG][academias] Request is_json: {request.is_json}")
        try:
            body = request.get_data(as_text=True)
            print(f"[DEBUG][academias] Raw body: {body}")
            parsed = request.get_json(silent=True)
            print(f"[DEBUG][academias] Parsed JSON (silent): {parsed}")
        except Exception as e:
            print(f"[DEBUG][academias] Error parsing body: {e}")
        # Avoid printing fixed misleading message here

    data = request.get_json() or {}
    nombre = data.get('nombre')
    if not nombre or not isinstance(nombre, str) or not nombre.strip():
        if Config.DEBUG:
            print(f"[DEBUG][academias] nombre inválido recibidO: {nombre!r}")
        return jsonify({"ok": False, "error": "nombre_required"}), 400

    nombre = nombre.strip()

    # Comprobar existencia
    existing = Academia.query.filter_by(nombre=nombre).first()
    if existing:
        return jsonify({"ok": False, "error": "conflict", "message": "academia_exists"}), 409

    try:
        a = Academia(nombre=nombre)
        db.session.add(a)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
