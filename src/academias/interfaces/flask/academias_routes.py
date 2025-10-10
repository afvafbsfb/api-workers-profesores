from flask import Blueprint, request, jsonify, g
from webargs import fields
from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE
from webargs.flaskparser import use_args
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_role, require_auth
from src.shared.auth_helpers import is_platform_admin, is_academy_admin
from src.shared.application.permissions import can_query_academias
from src.academias.infrastructure.models import Academia
from src.shared.database import db
from config import Config
from src.shared.docs.operation_id import operation_id

academias_bp = Blueprint('academias', __name__)


@academias_bp.route('', methods=['POST'])
@require_role('Admin_plataforma')
@operation_id('academias.crear_academia')
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




# Define query parameters so OpenAPI generator (and webargs) know about them
academias_list_query_args = {
    'id': fields.Int(required=False, allow_none=True),
    'nombre': fields.Str(required=False, allow_none=True),
    # use load_default for Marshmallow 3 compatibility
    'page': fields.Int(required=False, load_default=1),
    'size': fields.Int(required=False, load_default=20),
}


@academias_bp.route('', methods=['GET'])
@require_auth
@use_args(academias_list_query_args, location='query')
@openapi_query_args(academias_list_query_args)
@operation_id('academias.listar_academias')
def listar_academias(args):
    user = getattr(g, 'current_user', None)

    # Normalize incoming params and consult shared permission helper
    params = {'id': args.get('id')}
    allowed, effective_filters, reason = can_query_academias(user, params)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # If the permission helper forces an 'id', return only that academy in a list
    if 'id' in effective_filters:
        acad = db.session.get(Academia, effective_filters['id'])
        if not acad:
            return jsonify({"ok": False, "error": "not_found"}), 404
        result = [{"id": acad.id, "nombre": acad.nombre}]
        return jsonify({"ok": True, "result": result}), 200

    # Otherwise (platform admin with no forced filters) apply optional filters
    query = Academia.query
    nombre = args.get('nombre')
    if nombre:
        try:
            query = query.filter(Academia.nombre.ilike(f"%{nombre}%"))
        except Exception:
            # Fallback if ilike isn't available for the configured DB dialect
            query = query.filter(Academia.nombre.like(f"%{nombre}%"))

    # Pagination (simple offset/limit) — parse and clamp using shared helper
    try:
        parsed_page = int(args.get('page')) if args.get('page') is not None else None
    except Exception:
        parsed_page = None
    try:
        parsed_size = int(args.get('size')) if args.get('size') is not None else None
    except Exception:
        parsed_size = None

    page, size = clamp_pagination(parsed_page, parsed_size)
    offset = (max(page, 1) - 1) * max(size, 1)
    academias = query.offset(offset).limit(size).all()
    result = [{"id": a.id, "nombre": a.nombre} for a in academias]
    return jsonify({"ok": True, "result": result}), 200

# Exposed via @openapi_query_args decorator above


@academias_bp.route('/<int:academia_id>', methods=['GET'])
@require_auth
@operation_id('academias.obtener_academia')
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
@operation_id('academias.modificar_academia')
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
        # registrar quién modificó la academia
        try:
            a.usuario_id_ultima_modificacion = getattr(user, 'id', None)
        except Exception:
            pass
        db.session.add(a)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500








@academias_bp.route('/<int:academia_id>', methods=['DELETE'])
@require_role('Admin_plataforma')
@operation_id('academias.eliminar_academia')
def eliminar_academia(academia_id):
    """Soft-delete an academy only if no dependent active records exist.

    This endpoint sets `fecha_baja` and records the user who performed the
    operation. It refuses deletion if there are related Cursos, Aulas, Tarifas,
    Alumnos o Curso_Profesores linked to the academy.
    """
    user = getattr(g, 'current_user', None)
    a = db.session.get(Academia, academia_id)
    if not a:
        return jsonify({"ok": False, "error": "not_found"}), 404

    # Check for dependent records. If any exist, deny deletion.
    # We check the most common related tables; adjust if more are added.
    from src.academias.infrastructure.models import Curso, Aula, Tarifa
    from src.alumnos.infrastructure.models import Alumno
    from src.profesores.infrastructure.models import CursoProfesores

    deps = []
    try:
        if db.session.query(Curso).filter_by(academia_id=a.id).count() > 0:
            deps.append('Curso')
    except Exception:
        pass
    try:
        if db.session.query(Aula).filter_by(academia_id=a.id).count() > 0:
            deps.append('Aula')
    except Exception:
        pass
    try:
        if db.session.query(Tarifa).filter_by(academia_id=a.id).count() > 0:
            deps.append('Tarifa')
    except Exception:
        pass
    try:
        if db.session.query(Alumno).filter_by(academia_id=a.id).count() > 0:
            deps.append('Alumno')
    except Exception:
        pass
    try:
        if db.session.query(CursoProfesores).join(Curso, CursoProfesores.curso_id == Curso.id).filter(Curso.academia_id == a.id).count() > 0:
            deps.append('CursoProfesores')
    except Exception:
        # If join fails due to missing import or model differences, skip safely
        pass

    if deps:
        return jsonify({"ok": False, "error": "has_dependents", "details": deps}), 400

    # Soft-delete
    try:
        from datetime import datetime, timezone
        a.fecha_baja = datetime.now(timezone.utc)
        try:
            a.usuario_id_ultima_modificacion = getattr(user, 'id', None)
        except Exception:
            pass
        db.session.add(a)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": a.id, "nombre": a.nombre}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500
