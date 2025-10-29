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


# ---------------------------------------------------------------------------
# Adapter / compatibility functions (map names used in scripts/permissions_map.json)
# These are thin wrappers that delegate to existing logic or implement minimal checks.
# ---------------------------------------------------------------------------


def can_view_academia(current_user, params: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Compatibility wrapper for permissions_map 'can_view_academia'.

    Delegates to `can_query_academias` and is intended to enforce scope_by_role
    semantics for: admin_plataforma, admin_academia, profesor_academia.
    """
    return can_query_academias(current_user, params)


def can_login(current_user, payload: Dict = None) -> Tuple[bool, Dict, Optional[str]]:
    """Login is a public operation: allow initiation of the flow.

    Returns (allowed, info, None). The actual authentication checks happen in the
    auth handlers and token validation paths.
    """
    return True, {}, None


def can_query_roles(current_user, params: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si `current_user` puede listar roles disponibles.
    
    Todos los usuarios autenticados pueden consultar roles para conocer
    los roles disponibles al crear/modificar usuarios.
    
    Returns: (allowed, effective_filters, reason)
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    
    # Todos los usuarios autenticados pueden ver roles
    # No se aplican filtros adicionales - se retornan todos los roles
    return True, {}, None


def can_logout(current_user) -> Tuple[bool, Optional[str]]:
    """Compatibility wrapper: logout requires an authenticated user."""
    if not current_user:
        return False, 'not_authenticated'
    return True, None


def can_refresh(current_user) -> Tuple[bool, Optional[str]]:
    """Token refresh requires an authenticated user (or a valid refresh token).

    This is a minimal check; token validation is done elsewhere.
    """
    if not current_user:
        return False, 'not_authenticated'
    return True, None


def can_unblock(current_user, target_user) -> Tuple[bool, Optional[str]]:
    """Allow unblocking according to scope_by_role: admin_plataforma global, admin_academia own_academia."""
    if not current_user:
        return False, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, 'user_has_no_academy'
        if getattr(target_user, 'academia_id', None) != int(acad_id):
            return False, 'forbidden_other_academia'
        return True, None

    return False, 'forbidden'


def can_view_my_profile(current_user, params: Dict = None) -> Tuple[bool, Dict, Optional[str]]:
    """Allow a user to view their own profile. For simplicity this returns allowed
    if the request is from an authenticated user; further checks can be done by handlers.
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    return True, {}, None


def can_view_user(current_user, target_user) -> Tuple[bool, Dict, Optional[str]]:
    """Check if current_user can view target_user according to role/academy scope."""
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, {}, None

    if user_role in ('admin_academia', 'profesor_academia'):
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if getattr(target_user, 'academia_id', None) != int(acad_id):
            return False, {}, 'forbidden_other_academia'
        return True, {}, None

    return False, {}, 'forbidden'


def can_recover_credentials(current_user, payload: Dict = None) -> Tuple[bool, Dict, Optional[str]]:
    """Recovery flow: initiation can be public (e.g. user provides email) but
    final recovery must be constrained to the own_user (token/email verification).
    We allow initiation here and rely on the handler to enforce further checks.
    """
    return True, {}, None


def can_modify_credentials(current_user, target_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Delegate to can_modify_user but ensure semantics are aligned for credentials.

    Reuses `can_modify_user` which enforces role-based restrictions. Mention
    role keywords for static heuristics: admin_plataforma, admin_academia, profesor_academia.
    """
    return can_modify_user(current_user, target_user, payload)


def can_modify_role(current_user, target_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Allow changing role according to existing modify rules: only admins, with admin_academia limited to own academy."""
    # Reuse can_modify_user but additionally ensure that non-admin_plataforma cannot assign admin_plataforma
    allowed, sanitized, reason = can_modify_user(current_user, target_user, payload)
    if not allowed:
        return allowed, sanitized, reason
    # if payload tries to change rol and the actor is admin_academia, block assigning admin_plataforma
    try:
        actor_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        actor_role = None
    if actor_role == 'admin_academia':
        new_rol = None
        if payload and 'rol' in payload:
            new_rol = normalize_role(payload.get('rol'))
        if new_rol == 'admin_plataforma':
            return False, {}, 'forbidden_role_assignment'
    return True, sanitized, None


def can_modify_status(current_user, target_user) -> Tuple[bool, Optional[str]]:
    """Allow status changes only to admins (admin_plataforma global; admin_academia own_academia)."""
    if not current_user:
        return False, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None
    if user_role == 'admin_plataforma':
        return True, None
    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, 'user_has_no_academy'
        if getattr(target_user, 'academia_id', None) != int(acad_id):
            return False, 'forbidden_other_academia'
        return True, None
    return False, 'forbidden'


# ---------------------------------------------------------------------------
# Reglas para Tarifas
# ---------------------------------------------------------------------------
def can_query_tarifas(current_user, params: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si `current_user` puede listar/consultar tarifas con `params`.

    Returns: (allowed, effective_filters, reason)
    - effective_filters puede contener 'academia_id' forzada para limitar al ámbito del usuario.
    """
    user_role = None
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    effective_filters = {}

    if user_role == 'admin_plataforma':
        # Puede ver tarifas de cualquier academia
        if 'academia_id' in params and params.get('academia_id'):
            try:
                effective_filters['academia_id'] = int(params.get('academia_id'))
            except Exception:
                return False, {}, 'invalid_academia_id'
        return True, effective_filters, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        # Forzar academia_id del usuario
        if 'academia_id' in params and params.get('academia_id'):
            try:
                if int(params.get('academia_id')) != int(acad_id):
                    return False, {}, 'forbidden_other_academia'
            except Exception:
                return False, {}, 'invalid_academia_id'
        effective_filters['academia_id'] = int(acad_id)
        return True, effective_filters, None

    # profesor_academia no tiene acceso
    return False, {}, 'forbidden'


def can_create_tarifa(current_user, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede crear una tarifa.

    Reglas:
    - admin_plataforma: puede crear tarifas para cualquier academia (academia_id obligatorio)
    - admin_academia: puede crear tarifas solo para su academia
    - profesor_academia: no puede crear tarifas
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    effective = dict(payload or {})

    if user_role == 'admin_plataforma':
        # academia_id es obligatorio
        if 'academia_id' not in effective or not effective.get('academia_id'):
            return False, {}, 'academia_id_required'
        return True, effective, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        
        # Si academia_id viene en el payload, validar que coincida
        if 'academia_id' in effective and effective.get('academia_id'):
            try:
                if int(effective.get('academia_id')) != int(acad_id):
                    return False, {}, 'forbidden_other_academia'
            except Exception:
                return False, {}, 'invalid_academia_id'
        
        # Forzar academia_id del usuario
        effective['academia_id'] = int(acad_id)
        return True, effective, None

    return False, {}, 'forbidden'


def can_view_tarifa(current_user, target_tarifa) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede ver una tarifa específica.

    Reglas:
    - admin_plataforma: puede ver cualquier tarifa
    - admin_academia: solo tarifas de su academia
    - profesor_academia: no puede ver tarifas
    """
    if not current_user:
        return False, {}, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, {}, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if getattr(target_tarifa, 'academia_id', None) != int(acad_id):
            return False, {}, 'forbidden_other_academia'
        return True, {}, None

    return False, {}, 'forbidden'


def can_modify_tarifa(current_user, target_tarifa, payload: Dict) -> Tuple[bool, Dict, Optional[str]]:
    """Decide si current_user puede modificar `target_tarifa`.

    Reglas:
    - admin_plataforma: puede modificar cualquier tarifa
    - admin_academia: solo tarifas de su academia
    - profesor_academia: no puede modificar tarifas
    - Campos mutables: descripcion, precio_base
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
        # Permitir modificar descripcion y precio_base
        for k in ('descripcion', 'precio_base'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, {}, 'user_has_no_academy'
        if getattr(target_tarifa, 'academia_id', None) != int(acad_id):
            return False, {}, 'forbidden_other_academia'
        # Permitir modificar descripcion y precio_base
        for k in ('descripcion', 'precio_base'):
            if k in payload:
                sanitized[k] = payload[k]
        return True, sanitized, None

    return False, {}, 'forbidden'


def can_delete_tarifa(current_user, target_tarifa) -> Tuple[bool, Optional[str]]:
    """Decide si current_user puede borrar (soft-delete) `target_tarifa`.

    Reglas:
    - admin_plataforma: puede eliminar cualquier tarifa
    - admin_academia: solo tarifas de su academia
    - profesor_academia: no puede eliminar tarifas
    - La validación de cursos activos se hace en la capa de servicio/routes
    """
    if not current_user:
        return False, 'not_authenticated'
    try:
        user_role = normalize_role(getattr(current_user, 'rol').nombre if getattr(current_user, 'rol', None) else None)
    except Exception:
        user_role = None

    if user_role == 'admin_plataforma':
        return True, None

    if user_role == 'admin_academia':
        acad_id = getattr(current_user, 'academia_id', None)
        if not acad_id:
            return False, 'user_has_no_academy'
        if getattr(target_tarifa, 'academia_id', None) != int(acad_id):
            return False, 'forbidden_other_academia'
        return True, None

    return False, 'forbidden'
