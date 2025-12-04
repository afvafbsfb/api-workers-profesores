# Sistema de Permisos - API Workers Profesores

Documentación completa del sistema de autorización basado en roles y scoping.

## 📋 Tabla de Contenidos

- [Roles del Sistema](#roles-del-sistema)
- [Arquitectura de Permisos](#arquitectura-de-permisos)
- [Archivos y Fuente de Verdad](#archivos-y-fuente-de-verdad)
- [Scoping y Filtros](#scoping-y-filtros)
- [Cómo Funciona en Runtime](#cómo-funciona-en-runtime)
- [Añadir Nuevos Permisos](#añadir-nuevos-permisos)

## Roles del Sistema

La API maneja 3 roles principales definidos en la tabla `Rol_Usuario`:

| ID | Nombre | Descripción | Scope |
|----|--------|-------------|-------|
| 1 | `Admin_plataforma` | Administrador global de la plataforma | Acceso a todas las academias |
| 2 | `Admin_academia` | Administrador de una academia específica | Solo su academia |
| 3 | `Profesor_academia` | Profesor de una academia específica | Solo su academia, datos limitados |

## Arquitectura de Permisos

### Fuente de Verdad

**La lógica real ejecutada en runtime está en:**

1. **`src/shared/application/permissions.py`** - Funciones `can_*` que definen:
   - Roles permitidos (`allowed_roles`)
   - Alcance (`scope`: global, own_academia, own_user)
   - Filtros forzados (`enforced_filters`)
   - Campos mutables por rol (`mutable_fields_by_role`)

2. **Rutas (blueprints)** - Cada endpoint tiene un `operationId` que vincula la operación con el permiso correspondiente

### Artefactos Derivados

Estos archivos se **generan** a partir del código fuente:

- `docs/permissions.json` - Metadata extraída de `permissions.py`
- `docs/openapi-auto.json` - Spec generada desde rutas
- `docs/served-openapi.json` - Spec final con `x-permissions` (consumida por mediador)

### Mapa Manual

- **`scripts/permissions_map.json`** - Vincula funciones `can_*` con `operationId`

Este archivo es **editado manualmente** cuando añades endpoints nuevos.

## Scoping y Filtros

### Tipos de Scope

```python
# En permissions.py

def can_query_academias(current_user, request_params):
    """
    Admin_plataforma: scope global (ve todas las academias)
    Admin_academia: scope own_academia (solo su academia)
    """
    if 'Admin_plataforma' in current_user.roles:
        return {
            'allowed': True,
            'scope': 'global',
            'enforced_filters': {}
        }
    
    if 'Admin_academia' in current_user.roles:
        return {
            'allowed': True,
            'scope': 'own_academia',
            'enforced_filters': {
                'academia_id': current_user.academia_id
            }
        }
    
    return {'allowed': False}
```

### Scoping por Recurso

| Recurso | Admin_plataforma | Admin_academia | Profesor_academia |
|---------|------------------|----------------|-------------------|
| Academias | Global | Own academia | ❌ Denegado |
| Usuarios | Global | Own academia | Own user (solo lectura) |
| Alumnos | Global | Own academia | Own academia (limitado) |
| Cursos | Global | Own academia | Own cursos asignados |
| Sesiones | Global | Own academia | Own sesiones |

### Enforced Filters

Los filtros forzados se aplican automáticamente a las queries SQL:

```python
# Ejemplo: Admin_academia listando alumnos
enforced_filters = {
    'academia_id': 5  # Solo ve alumnos de su academia
}

# SQL generado automáticamente:
# SELECT * FROM Alumno WHERE academia_id = 5
```

## Cómo Funciona en Runtime

### Flujo de Autorización

```
1. Request → JWT validado → Claims extraídos
                ↓
2. Route handler llama función can_* en permissions.py
                ↓
3. can_* retorna: { allowed, scope, enforced_filters, sanitized_payload }
                ↓
4. Si allowed=False → 403 Forbidden
                ↓
5. Aplicar enforced_filters a query SQL
                ↓
6. Retornar resultados filtrados
```

### Ejemplo Real: Listar Usuarios

```python
# usuarios_routes.py

@bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    # 1. Extraer current_user del JWT
    current_user = get_jwt_identity()
    
    # 2. Llamar función de permisos
    perm = can_query_users(current_user, request.args)
    
    if not perm['allowed']:
        return jsonify({'error': 'Forbidden'}), 403
    
    # 3. Construir query base
    query = Usuario.query
    
    # 4. Aplicar enforced_filters
    for key, value in perm.get('enforced_filters', {}).items():
        query = query.filter(getattr(Usuario, key) == value)
    
    # 5. Ejecutar y retornar
    usuarios = query.all()
    return jsonify({'ok': True, 'data': usuarios})
```

### Sanitización de Payloads

Para operaciones de escritura (POST/PUT/PATCH), los permisos también sanitizan el payload:

```python
def can_modify_user(current_user, target_user, request_payload):
    """
    Admin_plataforma: puede modificar cualquier campo
    Admin_academia: puede modificar usuarios de su academia, campos limitados
    Profesor_academia: solo puede modificar su propio perfil, campos muy limitados
    """
    
    # Admin_plataforma tiene acceso completo
    if 'Admin_plataforma' in current_user.roles:
        return {
            'allowed': True,
            'scope': 'global',
            'sanitized_payload': request_payload,  # Sin filtrar
            'mutable_fields': ['*']
        }
    
    # Admin_academia solo su academia
    if 'Admin_academia' in current_user.roles:
        if target_user.academia_id != current_user.academia_id:
            return {'allowed': False}
        
        allowed_fields = ['nombre', 'email', 'estado']
        sanitized = {k: v for k, v in request_payload.items() 
                    if k in allowed_fields}
        
        return {
            'allowed': True,
            'scope': 'own_academia',
            'sanitized_payload': sanitized,
            'mutable_fields': allowed_fields
        }
    
    # Profesor_academia solo su usuario
    if 'Profesor_academia' in current_user.roles:
        if target_user.id != current_user.id:
            return {'allowed': False}
        
        allowed_fields = ['nombre', 'email']  # Solo puede cambiar nombre/email
        sanitized = {k: v for k, v in request_payload.items() 
                    if k in allowed_fields}
        
        return {
            'allowed': True,
            'scope': 'own_user',
            'sanitized_payload': sanitized,
            'mutable_fields': allowed_fields
        }
    
    return {'allowed': False}
```

## Añadir Nuevos Permisos

### Checklist Completo

#### 1. Crear Función en permissions.py

```python
# src/shared/application/permissions.py

def can_query_cursos(current_user, request_params):
    """
    Determina si el usuario puede listar cursos.
    
    Returns:
        dict: {
            'allowed': bool,
            'scope': str,  # 'global' | 'own_academia' | 'own_user'
            'enforced_filters': dict
        }
    """
    if 'Admin_plataforma' in current_user.roles:
        return {
            'allowed': True,
            'scope': 'global',
            'enforced_filters': {}
        }
    
    if 'Admin_academia' in current_user.roles or 'Profesor_academia' in current_user.roles:
        return {
            'allowed': True,
            'scope': 'own_academia',
            'enforced_filters': {
                'academia_id': current_user.academia_id
            }
        }
    
    return {'allowed': False}
```

#### 2. Crear Ruta con operationId

```python
# src/academias/interfaces/flask/cursos_routes.py

@bp.route('/cursos', methods=['GET'])
def listar_cursos():
    """Lista cursos según permisos del usuario."""
    # Asignar operationId
    listar_cursos.operation_id = 'cursos.list'
    
    current_user = get_jwt_identity()
    perm = can_query_cursos(current_user, request.args)
    
    if not perm['allowed']:
        return jsonify({'error': 'Forbidden'}), 403
    
    # ... implementación
```

#### 3. Mapear en permissions_map.json

```json
{
  "can_query_cursos": {
    "operationId": "cursos.list",
    "allowed_roles": ["Admin_plataforma", "Admin_academia", "Profesor_academia"],
    "scope_by_role": {
      "Admin_plataforma": "global",
      "Admin_academia": "own_academia",
      "Profesor_academia": "own_academia"
    },
    "enforced_filters": {
      "Admin_academia": {"academia_id": "current_user.academia_id"},
      "Profesor_academia": {"academia_id": "current_user.academia_id"}
    },
    "note": "Listar cursos con scoping por academia"
  }
}
```

#### 4. Crear Tests

```python
# tests/cursos/test_cursos_permissions.py

def test_admin_plataforma_ve_todos_cursos(client):
    # Login como admin plataforma
    login_resp = client.post('/auth/login', json={
        'email': 'admin_plataforma@academia.com',
        'password': 'password_admin_plataforma'
    })
    token = login_resp.json['tokens']['access_token']
    
    # Listar cursos
    resp = client.get('/cursos', headers={
        'Authorization': f'Bearer {token}'
    })
    
    assert resp.status_code == 200
    # Admin plataforma ve cursos de todas las academias


def test_admin_academia_solo_ve_sus_cursos(client):
    # Login como admin academia (academia_id=1)
    login_resp = client.post('/auth/login', json={
        'email': 'admin_academia@academia.com',
        'password': 'password_admin_academia'
    })
    token = login_resp.json['tokens']['access_token']
    
    # Listar cursos
    resp = client.get('/cursos', headers={
        'Authorization': f'Bearer {token}'
    })
    
    assert resp.status_code == 200
    cursos = resp.json['data']
    
    # Verificar que solo ve cursos de su academia
    for curso in cursos:
        assert curso['academia_id'] == 1
```

#### 5. Regenerar y Validar OpenAPI

```powershell
# Exportar permisos
python scripts/export_permissions.py

# Generar spec
python scripts/dump_openapi.py

# Fusionar permisos
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json

# Validar sincronización
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json

# Validar spec para mediador
python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json
```

## Debugging de Permisos

### Verificar Permisos en served-openapi.json

```powershell
# Ver x-permissions de un endpoint
python -c "import json; spec=json.load(open('docs/served-openapi.json')); print(spec['paths']['/cursos']['get']['x-permissions'])"
```

### Logs de Autorización

Habilitar logging detallado:

```powershell
$env:DEBUG = '1'
$env:LOG_LEVEL = 'DEBUG'
python main.py
```

Verás en consola:
```
[DEBUG] can_query_cursos: user_id=12, roles=['Admin_academia'], academia_id=5
[DEBUG] Permission result: {'allowed': True, 'scope': 'own_academia', 'enforced_filters': {'academia_id': 5}}
[DEBUG] Applied enforced_filters to SQL: academia_id = 5
```

## Casos Especiales

### Permisos Multi-Method (PUT/PATCH)

```json
{
  "can_modify_curso": {
    "operationId": ["cursos.update", "cursos.patch"],
    "allowed_roles": ["Admin_plataforma", "Admin_academia"],
    "scope_by_role": {
      "Admin_plataforma": "global",
      "Admin_academia": "own_academia"
    }
  }
}
```

### Allowed Target Roles (Crear/Modificar Usuarios)

```python
def can_create_user(current_user, request_payload):
    """
    Admin_plataforma: puede crear cualquier rol
    Admin_academia: solo puede crear Profesor_academia de su academia
    """
    target_role = request_payload.get('rol_id')
    
    if 'Admin_plataforma' in current_user.roles:
        return {
            'allowed': True,
            'allowed_target_roles': ['Admin_plataforma', 'Admin_academia', 'Profesor_academia']
        }
    
    if 'Admin_academia' in current_user.roles:
        # Solo puede crear profesores de su academia
        if target_role != 3:  # 3 = Profesor_academia
            return {'allowed': False}
        
        return {
            'allowed': True,
            'allowed_target_roles': ['Profesor_academia'],
            'enforced_payload': {
                'academia_id': current_user.academia_id  # Forzar su academia
            }
        }
```

## Recursos Adicionales

- [Guía de Desarrollo](DEVELOPMENT.md) - Setup y debugging
- [Workflow OpenAPI](OPENAPI_WORKFLOW.md) - Generación de specs
- [Referencia de Scripts](SCRIPTS.md) - Herramientas de validación
