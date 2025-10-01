"""Shim: re-exportar el blueprint de login desde la nueva estructura DDD.

Esto mantiene la ruta `/auth/login` registrada exactamente como antes
pero permite mover la lógica a `src.autenticacion` sin romper imports.
"""

from src.autenticacion.interfaces.flask import login_bp as auth_login_bp

# Mantener el nombre `login_bp` esperado por el resto de la app
login_bp = auth_login_bp