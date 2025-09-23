# Documentación: Sistema de Permisos por Rol

## Tabla de Permisos por Rol

### Descripción
La tabla `PermisosRol` define los permisos asociados a cada rol en el sistema. Esto permite parametrizar las acciones que cada rol puede realizar.

### Estructura de la Tabla
```sql
CREATE TABLE PermisosRol (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rol_id INT NOT NULL,
    recurso VARCHAR(100) NOT NULL,
    accion VARCHAR(50) NOT NULL,
    UNIQUE (rol_id, recurso, accion),
    FOREIGN KEY (rol_id) REFERENCES Rol(id)
);
```

### Ejemplo de Permisos
| rol_id | recurso         | accion     |
|--------|-----------------|------------|
| 1      | `academia`      | `crear`    |
| 1      | `academia`      | `eliminar` |
| 2      | `curso`         | `crear`    |
| 3      | `sesion`        | `leer`     |
| 3      | `sesion`        | `actualizar` |

---

## Middleware para Validación de Permisos

### Descripción
El middleware valida los permisos del usuario antes de procesar la solicitud. Esto asegura que solo los usuarios autorizados puedan realizar ciertas acciones.

### Ejemplo de Middleware en Python (Flask)
```python
from functools import wraps
from flask import request, jsonify

def validar_permiso(recurso, accion):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Obtener el rol del usuario autenticado
            rol_id = request.user.rol_id  # Suponiendo que el rol está en el token
            # Consultar permisos en la base de datos
            permiso = PermisosRol.query.filter_by(rol_id=rol_id, recurso=recurso, accion=accion).first()
            if not permiso:
                return jsonify({"error": "No tienes permiso para realizar esta acción"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Ejemplo de uso en un endpoint
@app.route('/academia', methods=['POST'])
@validar_permiso('academia', 'crear')
def crear_academia():
    # Lógica para crear una academia
    pass
```

---

## Validación de Permisos en el Worker

### Recomendación
1. **Enviar el Rol en la Solicitud**:
   - El backend debe incluir el rol del usuario en las solicitudes al worker.
   - Por ejemplo, en el cuerpo de la solicitud o en un encabezado HTTP.

2. **Validar Permisos en el Worker**:
   - El worker debe tener una lista de permisos predefinida o consultar una API para validar las acciones permitidas.

### Ejemplo de Validación en el Worker
```python
def validar_permiso_worker(rol_id, recurso, accion):
    permisos = {
        1: {'academia': ['crear', 'eliminar']},
        2: {'curso': ['crear', 'leer']},
        3: {'sesion': ['leer', 'actualizar']}
    }
    if recurso in permisos.get(rol_id, {}) and accion in permisos[rol_id][recurso]:
        return True
    return False
```

---

## Seguridad y Escalabilidad

1. **OAuth**:
   - Usa un proveedor de OAuth para autenticar usuarios y obtener su rol.
   - Incluye el rol en el token JWT para que el backend y el worker puedan validarlo.

2. **Centralización de Permisos**:
   - Mantén los permisos en la base de datos para facilitar actualizaciones y evitar duplicación.

3. **Logs**:
   - Registra intentos de acceso denegados para auditoría y depuración.