from functools import wraps
from flask import g, abort
from models import CursoProfesores, db

# Role names used in the system
ROLE_NAME_PLATFORM_ADMIN = 'Admin_plataforma'
ROLE_NAME_ACADEMY_ADMIN = 'Admin_academia'
ROLE_NAME_PROFESSOR = 'Profesor_academia'


def is_platform_admin(user):
    if not user:
        return False
    try:
        return bool(user.rol and getattr(user.rol, 'nombre', None) == ROLE_NAME_PLATFORM_ADMIN)
    except Exception:
        return False


def is_academy_admin(user, academia_id=None):
    # Platform admin always allowed
    if is_platform_admin(user):
        return True
    if not user:
        return False
    try:
        if not (user.rol and getattr(user.rol, 'nombre', None) == ROLE_NAME_ACADEMY_ADMIN):
            return False
        if academia_id is None:
            return user.academia_id is not None
        return int(user.academia_id) == int(academia_id)
    except Exception:
        return False


def is_professor_for_course(user, curso_id):
    # Platform admin always allowed
    if is_platform_admin(user):
        return True
    if not user:
        return False
    try:
        if not (user.rol and getattr(user.rol, 'nombre', None) == ROLE_NAME_PROFESSOR):
            return False
        # Check CursoProfesores mapping
        count = db.session.query(CursoProfesores).filter_by(curso_id=curso_id, usuario_id=user.id, fecha_baja=None).count()
        return count > 0
    except Exception:
        return False


# Decorator factory: accepts either legacy numeric kinds (1/2/3) or string kinds ('platform','academy','professor')
def require_role_kind(kind, academia_id_arg=None, curso_id_arg=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = getattr(g, 'current_user', None)
            # Legacy numeric mapping: 1=platform, 2=academy, 3=professor
            try:
                if kind in (1, 'platform'):
                    if not is_platform_admin(user):
                        abort(403)
                elif kind in (2, 'academy'):
                    academy_id = kwargs.get(academia_id_arg) or (user.academia_id if user else None)
                    if not is_academy_admin(user, academy_id):
                        abort(403)
                elif kind in (3, 'professor'):
                    curso_id = kwargs.get(curso_id_arg)
                    if not is_professor_for_course(user, curso_id):
                        abort(403)
                else:
                    # Unknown kind -> forbid by default
                    abort(403)
            except Exception:
                abort(403)
            return f(*args, **kwargs)
        # preserve _requires_auth marker if set
        try:
            wrapper._requires_auth = True
        except Exception:
            pass
        return wrapper
    return decorator
