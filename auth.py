"""
Compatibility shim: original module was renamed to auth_module.py to avoid
shadowing problems during development. This file re-exports the public
symbols so code importing `auth` keeps working.
"""
"""
Compatibility shim: keep exporting auth helpers from auth_module but do NOT
declare or register any route here to avoid duplicate endpoints.
"""
from auth_module import (
    require_jwt,
    generar_tokens,
    renovar_token,
    enforce_jwt_globally,
)

__all__ = [
    'require_jwt',
    'generar_tokens',
    'renovar_token',
    'enforce_jwt_globally',
]
