from flask import Blueprint, request, jsonify, g
from src.shared.middleware.auth import require_role, require_auth
from src.shared.auth_helpers import is_platform_admin, is_academy_admin
from src.academias.infrastructure.models import Academia
from src.shared.database import db
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



@academias_bp.route('', methods=['GET'])
@require_auth
def listar_academias():
    # Solo Admin_plataforma puede listar todas las academias
    user = getattr(g, 'current_user', None)
    if not is_platform_admin(user):
        return jsonify({"ok": False, "error": "forbidden"}), 403

    academias = Academia.query.all()
    result = [{"id": a.id, "nombre": a.nombre} for a in academias]
    return jsonify({"ok": True, "result": result}), 200


@academias_bp.route('/<int:academia_id>', methods=['GET'])
@require_auth
def obtener_academia(academia_id):
    user = getattr(g, 'current_user', None)
    rol_nombre = user.rol.nombre if user and user.rol else None

    # Use Session.get to avoid SQLAlchemy 2.0 LegacyAPIWarning
    a = db.session.get(Academia, academia_id)
    if not a:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Admin_plataforma puede ver cualquiera
    if is_platform_admin(user):
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 200

    # Otros roles sólo si el usuario está vinculado a la academia o es academy_admin
    if is_academy_admin(user, academia_id=a.id):
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 200

    return jsonify({"ok": False, "error": "forbidden"}), 403


@academias_bp.route('/<int:academia_id>', methods=['PATCH'])
@require_auth
def modificar_academia(academia_id):
    user = getattr(g, 'current_user', None)
    rol_nombre = user.rol.nombre if user and user.rol else None

    # Use Session.get to avoid SQLAlchemy 2.0 LegacyAPIWarning
    a = db.session.get(Academia, academia_id)
    if not a:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Authorization: Admin_plataforma puede modificar cualquiera; Admin_academia sólo la suya
    if is_platform_admin(user):
        allowed = True
    elif is_academy_admin(user, academia_id=a.id):
        allowed = True
    else:
        allowed = False

    if not allowed:
        return jsonify({"ok": False, "error": "forbidden"}), 403

    data = request.get_json() or {}
    nombre = data.get('nombre')
    if nombre is None:
        return jsonify({"ok": False, "error": "nombre_required"}), 400
    if not isinstance(nombre, str) or not nombre.strip():
        return jsonify({"ok": False, "error": "nombre_required"}), 400

    nombre = nombre.strip()
    # Check uniqueness
    existing = Academia.query.filter(Academia.nombre == nombre, Academia.id != a.id).first()
    if existing:
        return jsonify({"ok": False, "error": "conflict", "message": "academia_exists"}), 409

    try:
        a.nombre = nombre
        db.session.add(a)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
