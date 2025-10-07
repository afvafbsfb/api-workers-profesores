"""Permisos compartidos para la aplicación.

Este módulo agrupa reglas coherentes para los dominios principales.
- Primero: reglas relacionadas con Academias (consulta, alta, modificación, baja)
- Después: reglas relacionadas con Usuarios (consulta, alta, modificación, baja)

Las reglas son intencionalmente simples: deciden permisos y devuelven
filtros o payloads forzados cuando procede; la validación de dependencias
(p.ej. si una academia tiene cursos) se debe realizar en la capa de
infraestructura/servicio y no en esta función de permisos.
"""
from typing import Tuple, Dict, Optional
from src.shared.database import db
from src.usuarios.infrastructure.models import Rol


def normalize_role(role_name: Optional[str]) -> Optional[str]:
    if not role_name:
        return None
    return role_name.strip().lower()


# ---------------------------------------------------------------------------
# Reglas para Academias
# ---------------------------------------------------------------------------
def can_query_academias(current_user, params: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si `current_user` puede listar/consultar academias con `params`.

    Returns: (allowed, effective_filters, reason)
    - effective_filters puede contener 'id' forzada para limitar al ámbito del usuario.
    """
    user_role = None
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    effective_filters = {}

    if user_role == 'admin_plataforma':
        if 'id' in params and params.get('id'):
            try:
                effective_filters['id'] = int(params.get('id'))
            except Exception:
                return False, {}, 'invalid_id'
        return True, effective_filters, None

    if user_role in ('admin_academia', 'profesor_academia'):
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if 'id' in params and params.get('id'):
            try:
                if int(params.get('id')) != int(acad_id):
                    return False, {}, 'forbidden_other_academia'
            except Exception:
                return False, {}, 'invalid_id'
        effective_filters['id'] = int(acad_id)
        return True, effective_filters, None

    return False, {}, 'forbidden'


def can_create_academia(current_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede crear una academia.

    Regla: solo `admin_plataforma` puede crear academias.
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, dict(payload or {}), None
    return False, {}, 'forbidden'


def can_modify_academia(current_user, target_academia, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede modificar `target_academia`.

    Reglas:
    - admin_plataforma: puede modificar cualquier academia
    - admin_academia: puede modificar solo su propia academia (target_academia.id == current_user.academia_id)
    - profesor_academia: no puede modificar academias
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    sanitized = {}
    payload = payload or {}

    if user_role == 'admin_plataforma':
        # allow sensible academia fields
        for k in ('nombre', 'fecha_baja'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if getattr(target_academia, 'id', None) != int(acad_id):
            return False, {}, 'forbidden_other_academia'
        for k in ('nombre',):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    return False, {}, 'forbidden'


def can_delete_academia(current_user, target_academia) -> Tuple[bool, Optional[str]]:
    """Decide si current_user puede borrar (soft-delete) `target_academia`.

    Regla: solo admin_plataforma puede dar de baja academias. La comprobación de
    dependencias (cursos, aulas, etc.) debe hacerse fuera de esta función.
    """
    if not current_user:
        return False, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, None
    return False, 'forbidden'


# ---------------------------------------------------------------------------
# Reglas para gestión de Usuarios (altas, bajas, modificaciones)
# ---------------------------------------------------------------------------
def can_query_users(current_user, params: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si `current_user` puede listar/consultar usuarios con `params`.

    Returns: (allowed, effective_filters, reason)
    - effective_filters: dict de filtros que la API debe aplicar (p.ej. forzar academia_id)
    """
    user_role = None
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    effective_filters = {}

    if user_role == 'admin_plataforma':
        if 'academia_id' in params and params.get('academia_id'):
            try:
                effective_filters['academia_id'] = int(params.get('academia_id'))
            except Exception:
                return False, {}, 'invalid_academia_id'
        return True, effective_filters, None

    if user_role in ('admin_academia', 'profesor_academia'):
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if 'academia_id' in params and params.get('academia_id'):
            try:
                if int(params.get('academia_id')) != int(acad_id):
                    return False, {}, 'forbidden_other_academia'
            except Exception:
                return False, {}, 'invalid_academia_id'
        effective_filters['academia_id'] = int(acad_id)
        return True, effective_filters, None

    return False, {}, 'forbidden'


def can_create_user(current_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede crear un usuario.

    - admin_plataforma: puede crear cualquier usuario
    - admin_academia: solo puede crear usuarios asignados a su academia y nunca con rol admin_plataforma
    - otros: denegado
    """
    user_role = None
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    effective = dict(payload or {})

    if user_role == 'admin_plataforma':
        return True, effective, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if 'academia_id' in effective and effective.get('academia_id') and int(effective.get('academia_id')) != int(acad_id):
            return False, {}, 'forbidden_other_academia'
        effective['academia_id'] = int(acad_id)

        # impedir asignación de admin_plataforma
        role_name_in_payload = None
        try:
            if 'rol' in effective and effective.get('rol'):
                role_name_in_payload = normalize_role(effective.get('rol'))
            elif 'rol_nombre' in effective and effective.get('rol_nombre'):
                role_name_in_payload = normalize_role(effective.get('rol_nombre'))
            elif 'rol_id' in effective and effective.get('rol_id'):
                try:
                    rid = int(effective.get('rol_id'))
                except Exception:
                    return False, {}, 'invalid_rol_id'
                role_obj = db.session.get(Rol, rid)
                if not role_obj:
                    return False, {}, 'invalid_rol_id'
                role_name_in_payload = normalize_role(getattr(role_obj, 'nombre', None))
        except Exception:
            return False, {}, 'role_lookup_error'

        if role_name_in_payload == 'admin_plataforma':
            return False, {}, 'forbidden_role_assignment'

        return True, effective, None

    return False, {}, 'forbidden'


def can_delete_user(current_user, target_user) -> Tuple[bool, Optional[str]]:
    """Decide si current_user puede dar de baja (soft-delete) a target_user."""
    if not current_user:
        return False, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, None

    if user_role == 'admin_academia':
        if not getattr(current_user, 'academia_id', None):
            return False, 'user_has_no_academy'
        if getattr(target_user, 'academia_id', None) != getattr(current_user, 'academia_id'):
            return False, 'forbidden_other_academia'
        return True, None

    return False, 'forbidden'


def can_modify_user(current_user, target_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide qué puede modificar current_user sobre target_user.

    - admin_plataforma: puede cambiar rol/academia/estado/demás campos
    - admin_academia: solo puede modificar usuarios de su academia y no cambiar rol ni academia
    - profesor_academia: solo puede modificar su propio nombre/password
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    sanitized = {}
    payload = payload or {}

    if user_role == 'admin_plataforma':
        for k in ('nombre', 'email', 'password', 'rol_id', 'academia_id', 'estado'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    if user_role == 'admin_academia':
        if not getattr(current_user, 'academia_id', None):
            return False, {}, 'user_has_no_academy'
        if getattr(target_user, 'academia_id', None) != getattr(current_user, 'academia_id'):
            return False, {}, 'forbidden_other_academia'
        for k in ('nombre', 'email', 'password', 'estado'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    if user_role == 'profesor_academia':
        if current_user.id != getattr(target_user, 'id', None):
            return False, {}, 'forbidden'
        for k in ('nombre', 'password'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    return False, {}, 'forbidden'
