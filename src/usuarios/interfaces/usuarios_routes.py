from flask import Blueprint, jsonify, request, g, Response
from webargs import fields
from src.shared.pagination import clamp_pagination, DEFAULT_SIZE, MAX_PAGE_SIZE, DEFAULT_PAGE, build_page_envelope, EXPORT_SYNC_THRESHOLD
from src.shared.docs.openapi_args import openapi_query_args
from src.shared.middleware.auth import require_auth
from src.usuarios.infrastructure.models import Usuario
from src.shared.application.permissions import can_query_users, can_create_user, can_modify_user, can_delete_user
from src.shared.database import db
from src.shared.docs.operation_id import operation_id
from src.shared.middleware.auth import logger as auth_logger
import logging

logger = logging.getLogger(__name__)

usuarios_bp = Blueprint('usuarios', __name__)
usuarios_list_query_args = {
    'academia_id': fields.Int(required=False, allow_none=True),
    'rol': fields.Str(required=False, allow_none=True),
    # nombre legacy: mantiene comportamiento contains; añadimos nombre_contains explícito
    'nombre': fields.Str(required=False, allow_none=True),
    'nombre_contains': fields.Str(required=False, allow_none=True),
    # nuevos filtros
    'email': fields.Str(required=False, allow_none=True),
    'email_contains': fields.Str(required=False, allow_none=True),
    'estado': fields.Str(required=False, allow_none=True),
    'rol_id': fields.Int(required=False, allow_none=True),
    'id': fields.Int(required=False, allow_none=True),
    'page': fields.Int(required=False, allow_none=True),
    'size': fields.Int(required=False, allow_none=True),
    'with_total': fields.Bool(required=False, allow_none=True),
    'order_by': fields.Str(required=False, allow_none=True),
    'order_dir': fields.Str(required=False, allow_none=True),
    # rangos de fechas (ISO)
    'fecha_alta_gte': fields.Str(required=False, allow_none=True),
    'fecha_alta_lte': fields.Str(required=False, allow_none=True),
    'fecha_baja_gte': fields.Str(required=False, allow_none=True),
    'fecha_baja_lte': fields.Str(required=False, allow_none=True),
    'fecha_ultima_modificacion_gte': fields.Str(required=False, allow_none=True),
    'fecha_ultima_modificacion_lte': fields.Str(required=False, allow_none=True),
}


@usuarios_bp.route('/', methods=['GET'])
@require_auth  # Middleware para validar el token y extraer el rol
@operation_id('usuarios.listar_usuarios')
@openapi_query_args(usuarios_list_query_args)
def listar_usuarios():
    """
    Endpoint para listar usuarios con filtros opcionales.
    - Si el rol es admin_academia o profesor_academia, se fuerza el filtro por academia_id.
    - Si el rol es admin_plataforma, se permite ver todos los usuarios o filtrar por academia opcionalmente.
    """
    # Usuario autenticado cargado por el middleware
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401

    # Recopilar parámetros tal como llegarían desde la petición
    params = {
        'academia_id': request.args.get('academia_id'),
        'rol': request.args.get('rol'),
        'nombre': request.args.get('nombre'),
        'nombre_contains': request.args.get('nombre_contains'),
        'email': request.args.get('email'),
        'email_contains': request.args.get('email_contains'),
        'estado': request.args.get('estado'),
        'rol_id': request.args.get('rol_id'),
        'id': request.args.get('id') or request.args.get('usuario_id'),
        'page': request.args.get('page'),
        'size': request.args.get('size'),
        'with_total': request.args.get('with_total'),
        'order_by': request.args.get('order_by'),
        'order_dir': request.args.get('order_dir'),
        'fecha_alta_gte': request.args.get('fecha_alta_gte'),
        'fecha_alta_lte': request.args.get('fecha_alta_lte'),
        'fecha_baja_gte': request.args.get('fecha_baja_gte'),
        'fecha_baja_lte': request.args.get('fecha_baja_lte'),
        'fecha_ultima_modificacion_gte': request.args.get('fecha_ultima_modificacion_gte'),
        'fecha_ultima_modificacion_lte': request.args.get('fecha_ultima_modificacion_lte'),
    }

    allowed, effective_filters, reason = can_query_users(user, params)
    if not allowed:
        return jsonify({'ok': False, 'error': 'forbidden', 'reason': reason}), 403

    # Audit log: list request received
    try:
        logger.info("usuarios.list_request", extra={
            'user_id': getattr(user, 'id', None),
            'action': 'list',
            'filters': effective_filters,
            'page': page,
            'size': size,
        })
    except Exception:
        # best-effort logging
        auth_logger.debug("Failed to emit audit log for usuarios.list_request")

    # Construir la consulta base y aplicar filtros efectivos
    query = Usuario.query
    if 'academia_id' in effective_filters:
        query = query.filter(Usuario.academia_id == effective_filters['academia_id'])

    # Aplicar filtros opcionales aportados por el caller (si no contradicen effective_filters)
    if params.get('id'):
        try:
            uid = int(params.get('id'))
            query = query.filter(Usuario.id == uid)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid_id'}), 400

    # nombre: mantenemos compatibilidad (nombre trabaja como contains); nombre_contains también soportado
    nombre_contains = params.get('nombre_contains') or params.get('nombre')
    if nombre_contains:
        query = query.filter(Usuario.nombre.ilike(f"%{nombre_contains}%"))

    # email exacto / contains (si se usa exacto, ignora contains)
    email_exact = params.get('email')
    email_like = params.get('email_contains')
    if email_exact:
        query = query.filter(Usuario.email == email_exact)
    elif email_like:
        query = query.filter(Usuario.email.ilike(f"%{email_like}%"))

    if params.get('rol'):
        query = query.join(Usuario.rol).filter(Usuario.rol.has(nombre=params.get('rol')))

    # rol_id directo si se provee
    if params.get('rol_id'):
        try:
            rid = int(params.get('rol_id'))
            query = query.filter(Usuario.rol_id == rid)
        except Exception:
            return jsonify({'ok': False, 'error': 'invalid_rol_id'}), 400

    # estado
    if params.get('estado'):
        query = query.filter(Usuario.estado == params.get('estado'))

    # rangos de fecha
    from datetime import datetime
    def parse_dt(v: str):
        if not v:
            return None
        try:
            # intenta datetime ISO completo
            return datetime.fromisoformat(v)
        except Exception:
            try:
                # intenta solo fecha
                return datetime.fromisoformat(v + 'T00:00:00')
            except Exception:
                return None
    fa_gte = parse_dt(params.get('fecha_alta_gte'))
    fa_lte = parse_dt(params.get('fecha_alta_lte'))
    fb_gte = parse_dt(params.get('fecha_baja_gte'))
    fb_lte = parse_dt(params.get('fecha_baja_lte'))
    fum_gte = parse_dt(params.get('fecha_ultima_modificacion_gte'))
    fum_lte = parse_dt(params.get('fecha_ultima_modificacion_lte'))
    try:
        if fa_gte:
            query = query.filter(Usuario.fecha_alta >= fa_gte)
        if fa_lte:
            query = query.filter(Usuario.fecha_alta <= fa_lte)
        if fb_gte:
            query = query.filter(Usuario.fecha_baja >= fb_gte)
        if fb_lte:
            query = query.filter(Usuario.fecha_baja <= fb_lte)
        if fum_gte:
            query = query.filter(Usuario.fecha_ultima_modificacion >= fum_gte)
        if fum_lte:
            query = query.filter(Usuario.fecha_ultima_modificacion <= fum_lte)
    except Exception:
        return jsonify({'ok': False, 'error': 'invalid_date_range'}), 400

    # Pagination: parse page/size, apply offset/limit
    # Parse page/size and clamp to configured maxima/defaults. We prefer to be
    # tolerant and clamp rather than rejecting requests with large sizes.
    try:
        parsed_page = int(params.get('page')) if params.get('page') is not None else None
    except Exception:
        parsed_page = None
    try:
        parsed_size = int(params.get('size')) if params.get('size') is not None else None
    except Exception:
        parsed_size = None

    page, size = clamp_pagination(parsed_page, parsed_size)
    # Parse optional with_total and ordering
    with_total = params.get('with_total') in ('1', 'true', 'True', True)

    # Whitelist of allowed order_by fields to avoid SQL injection
    ORDER_WHITELIST = {'id', 'nombre', 'email', 'fecha_alta'}
    order_by = params.get('order_by') if params.get('order_by') in ORDER_WHITELIST else 'id'
    order_dir = params.get('order_dir') if params.get('order_dir') in ('asc', 'desc') else 'asc'

    # Apply ordering deterministically; add id as tie-breaker
    if order_by == 'id':
        if order_dir == 'asc':
            query = query.order_by(Usuario.id.asc())
        else:
            query = query.order_by(Usuario.id.desc())
    else:
        # Use SQLAlchemy-safe attributes
        col = getattr(Usuario, order_by, Usuario.id)
        if order_dir == 'asc':
            query = query.order_by(col.asc(), Usuario.id.asc())
        else:
            query = query.order_by(col.desc(), Usuario.id.desc())

    offset = (page - 1) * size
    # LIMIT+1 strategy to determine has_more without COUNT(*)
    usuarios_objs = query.offset(offset).limit(size + 1).all()

    def serialize(u: Usuario):
        return {
            'id': u.id,
            'nombre': u.nombre,
            'email': u.email,
            'rol': u.rol.nombre if getattr(u, 'rol', None) else None,
            'academia_id': u.academia_id,
            'estado': u.estado,
            'fecha_alta': u.fecha_alta.isoformat() if getattr(u, 'fecha_alta', None) else None,
        }

    serialized = [serialize(u) for u in usuarios_objs]

    total = None
    if with_total:
        try:
            total = query.order_by(None).count()
        except Exception:
            total = None

    envelope = build_page_envelope(serialized, page, size, with_total=with_total, total=total)

    return jsonify(envelope)

    def serialize(u: Usuario):
        return {
            'id': u.id,
            'nombre': u.nombre,
            'email': u.email,
            'rol': u.rol.nombre if getattr(u, 'rol', None) else None,
            'academia_id': u.academia_id,
            'estado': u.estado,
            'fecha_alta': u.fecha_alta.isoformat() if getattr(u, 'fecha_alta', None) else None,
        }

    return jsonify([serialize(u) for u in usuarios])


@usuarios_bp.route('/', methods=['POST'])
@require_auth
@operation_id('usuarios.crear_usuario')
def crear_usuario():
    user = getattr(g, 'current_user', None)
    data = request.get_json() or {}
    allowed, effective, reason = can_create_user(user, data)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Minimal creation logic: expect nombre, email, password, rol_id
    nombre = effective.get('nombre')
    email = effective.get('email')
    password = effective.get('password')
    rol_id = effective.get('rol_id')
    academia_id = effective.get('academia_id')

    if not nombre or not email or not password or not rol_id:
        return jsonify({"ok": False, "error": "missing_fields"}), 400

    # Check email uniqueness
    if Usuario.query.filter_by(email=email).first():
        return jsonify({"ok": False, "error": "conflict", "message": "email_exists"}), 409

    try:
        u = Usuario(nombre=nombre, email=email, password=password, rol_id=int(rol_id), academia_id=academia_id)
        db.session.add(u)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": u.id, "email": u.email}}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>', methods=['GET'])
@operation_id('usuarios.obtener_usuario')
def obtener_usuario(usuario_id):
    return jsonify({"message": f"Detalles del usuario {usuario_id}"})
    
@usuarios_bp.route('/<int:usuario_id>', methods=['PUT', 'PATCH'])
@require_auth
@operation_id({'put': 'usuarios.actualizar_usuario_put', 'patch': 'usuarios.actualizar_usuario_patch'})
def actualizar_usuario(usuario_id):
    user = getattr(g, 'current_user', None)
    target = db.session.get(Usuario, usuario_id)
    if not target:
        return jsonify({"ok": False, "error": "not_found"}), 404

    payload = request.get_json() or {}
    allowed, sanitized, reason = can_modify_user(user, target, payload)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Apply sanitized fields
    try:
        for k, v in sanitized.items():
            setattr(target, k, v)
        db.session.add(target)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": target.id}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>', methods=['DELETE'])
@require_auth
@operation_id('usuarios.eliminar_usuario')
def eliminar_usuario(usuario_id):
    user = getattr(g, 'current_user', None)
    target = db.session.get(Usuario, usuario_id)
    if not target:
        return jsonify({"ok": False, "error": "not_found"}), 404

    allowed, reason = can_delete_user(user, target)
    if not allowed:
        return jsonify({"ok": False, "error": "forbidden", "reason": reason}), 403

    # Soft-delete: set fecha_baja and estado='Baja'
    try:
        from datetime import datetime, timezone
        target.fecha_baja = datetime.now(timezone.utc)
        target.estado = 'Baja'
        db.session.add(target)
        db.session.commit()
        return jsonify({"ok": True, "result": {"id": target.id}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": "db_error", "message": str(e)}), 500

@usuarios_bp.route('/<int:usuario_id>/credentials', methods=['PUT'])
@operation_id('usuarios.actualizar_credenciales')
def actualizar_credenciales(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Credenciales del usuario {usuario_id} actualizadas", "data": data})

@usuarios_bp.route('/<int:usuario_id>/role', methods=['PUT'])
@operation_id('usuarios.actualizar_rol')
def actualizar_rol(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Rol del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/<int:usuario_id>/status', methods=['PUT'])
@operation_id('usuarios.actualizar_estado')
def actualizar_estado(usuario_id):
    data = request.get_json()
    return jsonify({"message": f"Estado del usuario {usuario_id} actualizado", "data": data})

@usuarios_bp.route('/recover', methods=['GET'])
@operation_id('usuarios.recuperar_credenciales')
def recuperar_credenciales():
    email = request.args.get('email')
    return jsonify({"message": f"Instrucciones enviadas al correo {email}"})



@usuarios_bp.route('/export', methods=['GET'])
@require_auth
@operation_id('usuarios.exportar_usuarios')
def exportar_usuarios():
    """Exportar usuarios a CSV o XLSX. Uses same filters as listar_usuarios.

    Query params: format=csv|xlsx (default csv), same filters as listar_usuarios.
    """
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({'ok': False, 'error': 'user_not_authenticated'}), 401

    fmt = (request.args.get('format') or 'csv').lower()

    # Reuse filters from listar_usuarios to build the same query
    params = {
        'academia_id': request.args.get('academia_id'),
        'rol': request.args.get('rol'),
        'nombre': request.args.get('nombre'),
        'id': request.args.get('id') or request.args.get('usuario_id'),
    }

    allowed, effective_filters, reason = can_query_users(user, params)
    if not allowed:
        return jsonify({'ok': False, 'error': 'forbidden', 'reason': reason}), 403

    # Audit log: export request received
    try:
        logger.info("usuarios.export_request", extra={
            'user_id': getattr(user, 'id', None),
            'action': 'export',
            'filters': effective_filters,
            'format': fmt,
        })
    except Exception:
        auth_logger.debug("Failed to emit audit log for usuarios.export_request")

    query = Usuario.query
    if 'academia_id' in effective_filters:
        query = query.filter(Usuario.academia_id == effective_filters['academia_id'])
    if params.get('id'):
        try:
            uid = int(params.get('id'))
            query = query.filter(Usuario.id == uid)
        except ValueError:
            return jsonify({'ok': False, 'error': 'invalid_id'}), 400
    if params.get('nombre'):
        query = query.filter(Usuario.nombre.ilike(f"%{params.get('nombre')}%"))
    if params.get('rol'):
        query = query.join(Usuario.rol).filter(Usuario.rol.has(nombre=params.get('rol')))

    # Estimate rows; use count for decision making (acceptable here)
    try:
        rows = query.order_by(None).count()
    except Exception:
        rows = None

    # If small enough, stream CSV/XLSX synchronously
    if rows is None or (rows is not None and rows <= EXPORT_SYNC_THRESHOLD):
        users = query.order_by(Usuario.id.asc()).all()

        def generate_csv():
            import csv
            from io import StringIO

            si = StringIO()
            writer = csv.writer(si)
            writer.writerow(['id', 'nombre', 'email', 'rol', 'academia_id', 'estado', 'fecha_alta'])
            yield si.getvalue()
            si.seek(0)
            si.truncate(0)

            for u in users:
                writer.writerow([
                    u.id,
                    u.nombre,
                    u.email,
                    u.rol.nombre if getattr(u, 'rol', None) else None,
                    u.academia_id,
                    u.estado,
                    u.fecha_alta.isoformat() if getattr(u, 'fecha_alta', None) else None,
                ])
                yield si.getvalue()
                si.seek(0)
                si.truncate(0)

        if fmt == 'csv':
            headers = {
                'Content-Type': 'text/csv',
                'Content-Disposition': 'attachment; filename="usuarios.csv"'
            }
            return Response(generate_csv(), headers=headers)
        elif fmt == 'xlsx':
            # create in-memory workbook
            from io import BytesIO
            from openpyxl import Workbook

            wb = Workbook(write_only=True)
            ws = wb.create_sheet(title='usuarios')
            ws.append(['id', 'nombre', 'email', 'rol', 'academia_id', 'estado', 'fecha_alta'])
            for u in users:
                ws.append([
                    u.id,
                    u.nombre,
                    u.email,
                    u.rol.nombre if getattr(u, 'rol', None) else None,
                    u.academia_id,
                    u.estado,
                    u.fecha_alta.isoformat() if getattr(u, 'fecha_alta', None) else None,
                ])

            bio = BytesIO()
            wb.save(bio)
            bio.seek(0)
            return Response(bio.read(), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', headers={'Content-Disposition': 'attachment; filename="usuarios.xlsx"'})

    # Otherwise, return accepted and job placeholder (async implementation)
    return jsonify({'ok': True, 'status': 'accepted', 'message': 'export_started_async', 'job_id': None}), 202


# Endpoint para obtener los datos del usuario autenticado
@usuarios_bp.route('/me', methods=['GET'])
@require_auth
@operation_id('usuarios.obtener_mi_perfil')
def obtener_mi_perfil():
    print("[DEBUG] Controlador obtener_mi_perfil alcanzado", flush=True)
    user = getattr(g, 'current_user', None)
    if not user:
        return jsonify({"ok": False, "error": "user_not_authenticated"}), 401

    # Construir la respuesta con los campos útiles para la capa de presentación
    perfil = {
        "id": user.id,
        "nombre": user.nombre,
        "email": user.email,
        "rol": user.rol.nombre if getattr(user, 'rol', None) else None,
        "academia_id": user.academia_id,
        "estado": user.estado,
        "fecha_alta": user.fecha_alta.isoformat() if getattr(user, 'fecha_alta', None) else None,
    }

    return jsonify(perfil)