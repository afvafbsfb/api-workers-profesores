# Workflow OpenAPI - API Workers Profesores

Documentación completa del proceso de generación de especificaciones OpenAPI para consumo del mediador (Backend Chat).

## 📋 Tabla de Contenidos

- [Resumen del Flujo](#resumen-del-flujo)
- [Archivos Involucrados](#archivos-involucrados)
- [Pipeline Completo](#pipeline-completo)
- [Scripts de Generación](#scripts-de-generación)
- [Scripts de Validación](#scripts-de-validación)
- [Consumo por el Mediador](#consumo-por-el-mediador)
- [CI/CD](#cicd)

## Resumen del Flujo

```
Código fuente (rutas + schemas + permissions.py)
         ↓
[export_permissions.py] → permissions.json
         ↓
[dump_openapi.py] → openapi-auto.json
         ↓
[annotate_openapi_params.py] → openapi-auto.json (anotado)
         ↓
[merge_permissions_into_openapi.py] → served-openapi.json
         ↓
[validate_*] → Verificaciones de calidad
         ↓
served-openapi.json (ARTEFACTO FINAL para mediador)
```

## Archivos Involucrados

### Archivos Fuente (Editados Manualmente)

| Archivo | Propósito | Quién lo edita |
|---------|-----------|----------------|
| `src/shared/application/permissions.py` | Funciones `can_*` con lógica de autorización | Desarrolladores |
| `src/*/interfaces/flask/*_routes.py` | Endpoints con `operationId` | Desarrolladores |
| `src/*/interfaces/flask/schemas/*_schema.py` | Schemas Marshmallow | Desarrolladores |
| `scripts/permissions_map.json` | Mapeo `can_* → operationId` | Desarrolladores |

### Archivos Generados (No Editar Manualmente)

| Archivo | Generado Por | Propósito |
|---------|--------------|-----------|
| `docs/permissions.json` | `export_permissions.py` | Metadata de funciones `can_*` |
| `docs/permissions.yaml` | `export_permissions.py` | Idem en YAML |
| `docs/openapi-auto.json` | `dump_openapi.py` | Spec OpenAPI desde código |
| `docs/openapi-auto.yml` | `dump_openapi.py` | Idem en YAML |
| `docs/served-openapi.json` | `merge_permissions_into_openapi.py` | **Spec final con `x-permissions`** |

## Pipeline Completo

### Paso 1: Exportar Permisos

```powershell
python scripts/export_permissions.py
```

**Qué hace:**
- Lee `src/shared/application/permissions.py`
- Extrae metadata de todas las funciones `can_*`:
  - Nombre de la función
  - Docstring
  - Parámetros
  - Inferencia básica de `allowed_roles` y `scope`
- Genera `docs/permissions.json` y `docs/permissions.yaml`

**Ejemplo de salida (`permissions.json`):**
```json
{
  "can_query_users": {
    "function": "can_query_users",
    "allowed_roles": ["Admin_plataforma", "Admin_academia"],
    "scope": "varies",
    "description": "Determina si el usuario puede listar usuarios",
    "parameters": ["current_user", "request_params"]
  }
}
```

### Paso 2: Generar Spec desde Código

```powershell
python scripts/dump_openapi.py
```

**Qué hace:**
- Importa la app Flask (`create_app()`)
- Recorre todos los blueprints registrados
- Por cada ruta extrae:
  - Path, method (GET, POST, etc.)
  - `operationId` (si está definido en la view function)
  - Parámetros query/path
  - Schemas de request/response (desde decoradores/Marshmallow)
- Genera `docs/openapi-auto.json` y `docs/openapi-auto.yml`

**Configuración de operationId en rutas:**
```python
# usuarios_routes.py

@bp.route('/usuarios', methods=['GET'])
def listar_usuarios():
    """Lista usuarios según permisos."""
    pass

# Asignar operationId
listar_usuarios.operation_id = 'usuarios.listar_usuarios'
```

**Heurística de operationId automático:**
Si no defines `operation_id`, el script infiere uno basado en:
- Blueprint name (ej. `usuarios`)
- Function name (ej. `listar_usuarios`)
- Method (GET, POST, etc.)

Resultado: `usuarios.listar_usuarios_get`

### Paso 3: Anotar Parámetros Query

```powershell
python scripts/annotate_openapi_params.py docs/openapi-auto.json
```

**Qué hace:**
- Lee decoradores `@openapi_query_args` en view functions
- Añade descripción y metadata a parámetros query esperados
- Actualiza `docs/openapi-auto.json` in-place

**Ejemplo de decorador:**
```python
from src.shared.decorators import openapi_query_args

@bp.route('/usuarios', methods=['GET'])
@openapi_query_args({
    'academia_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de academia',
        'required': False
    },
    'rol_id': {
        'type': 'integer',
        'description': 'Filtrar por rol',
        'required': False
    }
})
def listar_usuarios():
    pass
```

### Paso 4: Fusionar Permisos

```powershell
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json
```

**Qué hace:**
- Lee `docs/openapi-auto.json`
- Lee `docs/permissions.json`
- Lee `scripts/permissions_map.json` (mapeo manual)
- Por cada operación en la spec:
  1. Busca el permiso correspondiente en `permissions_map.json`
  2. Inyecta campo `x-permissions` con:
     - `allowed_roles` (normalizado)
     - `scope` o `scope_by_role`
     - `enforced_filters`
     - `mutable_fields_by_role` (para PUT/PATCH)
     - `allowed_target_roles` (para crear usuarios)
     - `source` y `generated_at` (trazabilidad)
- Genera `docs/served-openapi.json`

**Ejemplo de `x-permissions` generado:**
```json
{
  "paths": {
    "/usuarios": {
      "get": {
        "operationId": "usuarios.listar_usuarios",
        "x-permissions": {
          "allowed_roles": ["Admin_plataforma", "Admin_academia"],
          "scope_by_role": {
            "Admin_plataforma": "global",
            "Admin_academia": "own_academia"
          },
          "enforced_filters": {
            "Admin_academia": {
              "academia_id": "current_user.academia_id"
            }
          },
          "source": "permissions_map",
          "generated_at": "2025-11-25T10:30:00Z"
        }
      }
    }
  }
}
```

### Paso 5: Validar Sincronización

```powershell
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json
```

**Qué valida:**
1. **Permisos en map sin función:** Si `permissions_map.json` referencia `can_foo` pero no existe en `permissions.py`
2. **operationId inexistente:** Si el map apunta a un `operationId` que no está en la spec
3. **Funciones sin mapear:** Funciones `can_*` en `permissions.py` que no están en el map
4. **Inconsistencias de scope:** Detecta heurísticamente si el scope declarado no coincide con el código

**Salida esperada:**
```
✓ All permissions in map have corresponding functions
✓ All operationIds referenced exist in spec
⚠ Warning: 2 functions in permissions.py not mapped (can_internal_*, can_deprecated_*)
✓ No scope inconsistencies detected
```

### Paso 6: Validar Endpoints Críticos

```powershell
python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json
```

**Qué valida:**
- Endpoints GET de recursos sensibles tienen `operationId`
- Endpoints POST/PUT/DELETE tienen `x-permissions`
- Endpoints tienen `security` (JWT requerido)

**Endpoints críticos considerados:**
- `/usuarios`, `/academias`, `/alumnos`, `/cursos`, `/sesiones`, `/inscripciones`, `/extractos`

### Paso 7: Validar Spec para Mediador

```powershell
python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json
```

**Qué valida:**
1. **Paths existen:** La spec tiene al menos un path definido
2. **operationId obligatorio:** Todas las operaciones tienen `operationId`
3. **x-permissions en críticos:** Endpoints de recursos sensibles tienen `x-permissions`
4. **Schemas referenciados:** Los `$ref` apuntan a schemas existentes en `components/schemas`
5. **Estructura mínima:** Info, servers, paths, components presentes

**⚠️ IMPORTANTE:** Este script es **obligatorio en CI**. Si falla, el job se bloquea.

## Scripts de Generación

### export_permissions.py

```powershell
python scripts/export_permissions.py
```

**Opciones:**
- Ninguna (usa defaults)

**Salidas:**
- `docs/permissions.json`
- `docs/permissions.yaml`

### dump_openapi.py

```powershell
python scripts/dump_openapi.py
```

**Opciones:**
- Ninguna (usa defaults)

**Salidas:**
- `docs/openapi-auto.json`
- `docs/openapi-auto.yml`

**Requisitos:**
- Flask app debe poder importarse sin errores
- Base de datos accesible (para imports de models)

### annotate_openapi_params.py

```powershell
python scripts/annotate_openapi_params.py docs/openapi-auto.json
```

**Opciones:**
- `--spec` - Path a la spec a anotar (default: `docs/openapi-auto.json`)

**Efecto:**
- Actualiza el archivo in-place

### merge_permissions_into_openapi.py

```powershell
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json
```

**Opciones:**
- `--spec` - Spec OpenAPI fuente
- `--out` - Spec OpenAPI de salida con `x-permissions`

**Dependencias:**
- `docs/permissions.json`
- `scripts/permissions_map.json`

## Scripts de Validación

### validate_permissions_sync.py

```powershell
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json
```

**Exit codes:**
- `0` - Todo sincronizado
- `1` - Errores detectados (falta función, operationId inválido, etc.)

### validate_critical_endpoints.py

```powershell
python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json
```

**Exit codes:**
- `0` - Endpoints críticos válidos
- `1` - Falta `operationId`, `x-permissions` o `security`

### validate_served_openapi_for_mediator.py

```powershell
python scripts/validate_served_openapi_for_mediador.py --spec docs/served-openapi.json
```

**Opciones:**
- `--spec` - Path a la spec a validar
- `--fix` - Aplicar normalizaciones automáticas (experimental)

**Exit codes:**
- `0` - Spec válida para mediador
- `1` - Problemas detectados (bloqueante en CI)

### check_operation_ids.py

```powershell
python scripts/check_operation_ids.py --spec docs/openapi-auto.json
```

**Qué valida:**
- Todas las operaciones tienen `operationId` no vacío

**Exit codes:**
- `0` - Todos los operationIds presentes
- `1` - Falta algún operationId

### validate_openapi_params.py

```powershell
python scripts/validate_openapi_params.py --spec docs/openapi-auto.json --fail-on-missing
```

**Qué valida:**
- Endpoints críticos (GET /usuarios, GET /academias) tienen parámetros query esperados
- Genera informe JSON con resultado

**Opciones:**
- `--fail-on-missing` - Salir con error si falta parámetro esperado

## Consumo por el Mediador

### Qué Archivo Usar

El **Backend Chat (mediador)** debe consumir **únicamente**:

```
docs/served-openapi.json
```

Este archivo contiene:
- Todos los paths y operaciones
- `operationId` por operación
- **`x-permissions`** con metadata de autorización
- Schemas en `components/schemas` (referenciados vía `$ref`)

### Cómo lo Usa el Mediador

```java
// SpecLoaderService.java (Backend Chat)

public void loadSpecification() {
    // Cargar served-openapi.json
    ObjectNode spec = loadJson("served-openapi.json");
    
    // Extraer paths
    ObjectNode paths = (ObjectNode) spec.get("paths");
    
    for (String path : paths.fieldNames()) {
        ObjectNode pathItem = (ObjectNode) paths.get(path);
        
        for (String method : pathItem.fieldNames()) {
            ObjectNode operation = (ObjectNode) pathItem.get(method);
            
            // Extraer operationId
            String operationId = operation.get("operationId").asText();
            
            // Extraer x-permissions
            ObjectNode xPermissions = (ObjectNode) operation.get("x-permissions");
            List<String> allowedRoles = extractRoles(xPermissions.get("allowed_roles"));
            
            // Guardar en mapa para autorización
            permissionsCache.put(operationId, allowedRoles);
        }
    }
}
```

### Autorización en el Mediador

```java
// AuthorizationServiceImpl.java

public boolean canExecuteOperation(String operationId, List<String> userRoles) {
    List<String> allowedRoles = permissionsCache.get(operationId);
    
    if (allowedRoles == null) {
        return false;  // Operación no encontrada
    }
    
    // Verificar intersección de roles
    return userRoles.stream().anyMatch(allowedRoles::contains);
}
```

## CI/CD

### Pipeline de GitHub Actions

El CI ejecuta todos los pasos en orden:

```yaml
# .github/workflows/test.yml

steps:
  - name: Setup Python
    uses: actions/setup-python@v4
    with:
      python-version: '3.11'
  
  - name: Install dependencies
    run: |
      pip install -r requirements.txt
      pip install -r requirements-dev.txt
  
  - name: Run seeder
    run: python init_db_pruebas_test.py --reset
  
  - name: Run tests
    run: pytest -q -s
  
  - name: Export permissions
    run: python scripts/export_permissions.py
  
  - name: Generate OpenAPI spec
    run: python scripts/dump_openapi.py
  
  - name: Annotate params
    run: python scripts/annotate_openapi_params.py docs/openapi-auto.json
  
  - name: Validate params
    run: python scripts/validate_openapi_params.py --spec docs/openapi-auto.json --fail-on-missing
  
  - name: Check operationIds
    run: python scripts/check_operation_ids.py --spec docs/openapi-auto.json
  
  - name: Merge permissions
    run: python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json
  
  - name: Validate permissions sync
    run: python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json
  
  - name: Validate critical endpoints
    run: python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json
  
  - name: Validate for mediator (BLOQUEANTE)
    run: python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json
  
  - name: Upload artifacts
    uses: actions/upload-artifact@v3
    with:
      name: openapi-specs
      path: |
        docs/openapi-auto.json
        docs/openapi-auto.yml
        docs/served-openapi.json
        docs/permissions.json
```

### Artifacts Publicados

Al finalizar el CI, se publican:
- `openapi-auto.json` (spec generada desde código)
- `openapi-auto.yml` (idem en YAML)
- **`served-openapi.json`** (spec final con `x-permissions` - **consumir este**)
- `permissions.json` (metadata de permisos)

El mediador debe descargar `served-openapi.json` del artifact más reciente.

## Troubleshooting

### Error: "Permission function not found"

```
ERROR: can_foo not found in permissions.py
```

**Solución:**
- Añadir función `can_foo` en `src/shared/application/permissions.py`
- O eliminar entrada de `scripts/permissions_map.json` si es obsoleta

### Error: "operationId not found in spec"

```
ERROR: operationId 'foo.bar' referenced in map but not in spec
```

**Solución:**
- Verificar que la ruta con ese `operationId` existe en el código
- Regenerar spec: `python scripts/dump_openapi.py`
- Verificar que el blueprint está registrado en `create_app()`

### Warning: "Function not mapped"

```
WARNING: Function can_internal_helper not mapped
```

**Solución:**
- Si la función es interna (helper), ignorar el warning
- Si debe estar mapeada, añadir entrada en `permissions_map.json`

### Error: "Missing x-permissions in critical endpoint"

```
ERROR: GET /usuarios missing x-permissions
```

**Solución:**
- Añadir mapeo en `permissions_map.json`
- Ejecutar merge: `python scripts/merge_permissions_into_openapi.py ...`

## Recursos Adicionales

- [Sistema de Permisos](PERMISSIONS.md) - Detalles de autorización
- [Referencia de Scripts](SCRIPTS.md) - Todos los scripts disponibles
- [Guía de Desarrollo](DEVELOPMENT.md) - Setup y debugging
