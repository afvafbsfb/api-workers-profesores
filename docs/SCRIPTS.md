# Referencia de Scripts - API Workers Profesores

Documentación completa de todos los scripts disponibles en el proyecto.

## 📋 Tabla de Contenidos

- [Scripts de Generación OpenAPI](#scripts-de-generación-openapi)
- [Scripts de Validación](#scripts-de-validación)
- [Scripts de Base de Datos](#scripts-de-base-de-datos)
- [Scripts de Utilidades](#scripts-de-utilidades)
- [Scripts de CI/CD](#scripts-de-cicd)

## Scripts de Generación OpenAPI

### export_permissions.py

**Propósito:** Exporta metadata de funciones `can_*` desde `permissions.py`

**Ubicación:** `scripts/export_permissions.py`

**Uso:**
```powershell
python scripts/export_permissions.py
```

**Salidas:**
- `docs/permissions.json` - Metadata en JSON
- `docs/permissions.yaml` - Metadata en YAML

**Ejemplo de salida:**
```json
{
  "can_query_users": {
    "function": "can_query_users",
    "allowed_roles": ["Admin_plataforma", "Admin_academia"],
    "scope": "varies",
    "description": "Determina si el usuario puede listar usuarios"
  }
}
```

---

### dump_openapi.py

**Propósito:** Genera especificación OpenAPI desde código fuente (rutas + schemas)

**Ubicación:** `scripts/dump_openapi.py`

**Uso:**
```powershell
python scripts/dump_openapi.py
```

**Requisitos:**
- Flask app debe poder importarse sin errores
- Base de datos accesible (para imports de models)

**Salidas:**
- `docs/openapi-auto.json` - Spec en JSON
- `docs/openapi-auto.yml` - Spec en YAML

**Variables de entorno opcionales:**
```powershell
$env:FLASK_SKIP_DB_INIT = '1'  # Evita inicializar BD si da problemas
```

---

### annotate_openapi_params.py

**Propósito:** Añade descripciones a parámetros query basándose en decoradores `@openapi_query_args`

**Ubicación:** `scripts/annotate_openapi_params.py`

**Uso:**
```powershell
python scripts/annotate_openapi_params.py docs/openapi-auto.json
```

**Opciones:**
- `--spec` - Path a la spec (default: `docs/openapi-auto.json`)

**Efecto:**
- Actualiza el archivo in-place

**Ejemplo de decorador esperado:**
```python
@openapi_query_args({
    'academia_id': {
        'type': 'integer',
        'description': 'Filtrar por ID de academia',
        'required': False
    }
})
def listar_usuarios():
    pass
```

---

### merge_permissions_into_openapi.py

**Propósito:** Fusiona permisos desde `permissions_map.json` en la spec OpenAPI como `x-permissions`

**Ubicación:** `scripts/merge_permissions_into_openapi.py`

**Uso:**
```powershell
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json
```

**Opciones:**
- `--spec` - Spec OpenAPI fuente
- `--out` - Spec OpenAPI de salida con `x-permissions`

**Dependencias:**
- `docs/permissions.json` (generado por `export_permissions.py`)
- `scripts/permissions_map.json` (editado manualmente)

**Salida:**
- `docs/served-openapi.json` - **Spec final para mediador**

**Ejemplo de `x-permissions` generado:**
```json
{
  "x-permissions": {
    "allowed_roles": ["Admin_plataforma", "Admin_academia"],
    "scope_by_role": {
      "Admin_plataforma": "global",
      "Admin_academia": "own_academia"
    },
    "enforced_filters": {
      "Admin_academia": {"academia_id": "current_user.academia_id"}
    },
    "source": "permissions_map",
    "generated_at": "2025-11-25T10:30:00Z"
  }
}
```

---

## Scripts de Validación

### validate_permissions_sync.py

**Propósito:** Valida sincronización entre `permissions_map.json`, `permissions.py` y `openapi-auto.json`

**Ubicación:** `scripts/validate_permissions_sync.py`

**Uso:**
```powershell
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json
```

**Validaciones:**
1. Permisos en map tienen función correspondiente en `permissions.py`
2. `operationId` referenciados existen en spec
3. Funciones `can_*` sin mapear (warnings)
4. Inconsistencias de scope detectadas heurísticamente

**Exit codes:**
- `0` - Todo sincronizado
- `1` - Errores críticos encontrados

**Salida esperada:**
```
✓ All permissions in map have corresponding functions
✓ All operationIds referenced exist in spec
⚠ Warning: 2 functions in permissions.py not mapped
✓ No scope inconsistencies detected
```

---

### validate_critical_endpoints.py

**Propósito:** Valida que endpoints críticos tienen `operationId` y `x-permissions`

**Ubicación:** `scripts/validate_critical_endpoints.py`

**Uso:**
```powershell
python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json
```

**Endpoints críticos verificados:**
- `/usuarios`, `/academias`, `/alumnos`, `/cursos`, `/sesiones`, `/inscripciones`, `/extractos`

**Validaciones:**
- GET endpoints tienen `operationId`
- POST/PUT/DELETE tienen `x-permissions`
- Todos tienen `security` (JWT requerido)

**Exit codes:**
- `0` - Todos los endpoints críticos válidos
- `1` - Falta metadata requerida

---

### validate_served_openapi_for_mediator.py

**Propósito:** Valida que `served-openapi.json` está listo para consumo del mediador

**Ubicación:** `scripts/validate_served_openapi_for_mediador.py`

**Uso:**
```powershell
python scripts/validate_served_openapi_for_mediador.py --spec docs/served-openapi.json
```

**Opciones:**
- `--spec` - Path a la spec
- `--fix` - Aplicar normalizaciones automáticas (experimental)

**Validaciones:**
1. Paths existen
2. Todos los endpoints tienen `operationId`
3. Endpoints críticos tienen `x-permissions`
4. `$ref` apuntan a schemas existentes en `components/schemas`
5. Estructura mínima (info, servers, paths, components)

**Exit codes:**
- `0` - Spec válida para mediador
- `1` - Problemas detectados

**⚠️ CRÍTICO:** Este script es **bloqueante en CI**. Si falla, el pipeline se detiene.

---

### check_operation_ids.py

**Propósito:** Verifica que todas las operaciones tienen `operationId` no vacío

**Ubicación:** `scripts/check_operation_ids.py`

**Uso:**
```powershell
python scripts/check_operation_ids.py --spec docs/openapi-auto.json
```

**Exit codes:**
- `0` - Todos los `operationId` presentes
- `1` - Falta algún `operationId`

**Salida:**
```
✓ All operations have operationId
```

O:
```
✗ Missing operationId in GET /usuarios
✗ Missing operationId in POST /alumnos
```

---

### validate_openapi_params.py

**Propósito:** Valida que endpoints críticos tienen parámetros query esperados

**Ubicación:** `scripts/validate_openapi_params.py`

**Uso:**
```powershell
python scripts/validate_openapi_params.py --spec docs/openapi-auto.json --fail-on-missing
```

**Opciones:**
- `--spec` - Path a la spec
- `--fail-on-missing` - Salir con error si falta parámetro esperado

**Parámetros esperados verificados:**
- `GET /usuarios` → `academia_id`, `rol_id`
- `GET /academias` → `estado`
- `GET /alumnos` → `academia_id`, `curso_id`

**Salidas:**
- Informe JSON con resultado
- Exit code 0 o 1

---

## Scripts de Base de Datos

### init_db_pruebas_test.py

**Propósito:** Resetea BD y crea usuarios de prueba con cuentas `reserve_*`

**Ubicación:** `init_db_pruebas_test.py` (raíz)

**Uso:**
```powershell
# Resetear BD (⚠️ borra todos los datos)
python init_db_pruebas_test.py --reset

# Solo insertar usuarios de prueba (sin resetear)
python init_db_pruebas_test.py
```

**Usuarios creados:**
- `admin_plataforma@academia.com` / `password_admin_plataforma` (rol: Admin_plataforma)
- `admin_academia@academia.com` / `password_admin_academia` (rol: Admin_academia, academia_id=1)
- `user_academia_2_1@academia.com` / `password_user_academia_2_1` (rol: Profesor_academia, academia_id=2)

**⚠️ ADVERTENCIA:** `--reset` ejecuta `DROP DATABASE` y recrea todo desde `docs/create_database.sql`

---

### ensure_db.py

**Propósito:** Verifica que la BD existe y es accesible

**Ubicación:** `ensure_db.py` (raíz)

**Uso:**
```powershell
python ensure_db.py
```

**Validaciones:**
- Conexión a MySQL exitosa
- Base de datos especificada en `config.py` existe
- Tablas principales existen (Academia, Usuario, Alumno)

**Exit codes:**
- `0` - BD accesible y válida
- `1` - Error de conexión o BD no existe

---

### migration.sql

**Propósito:** Migraciones SQL manuales (no Alembic)

**Ubicación:** `migration.sql` (raíz)

**Uso:**
```powershell
# Aplicar manualmente en MySQL Workbench o CLI
mysql -u root -p academias_chat < migration.sql
```

**Contenido típico:**
- Añadir columnas nuevas
- Cambiar tipos de datos
- Crear índices

---

### migrate_refresh_token.py

**Propósito:** Migración específica para añadir columnas a `RefreshToken`

**Ubicación:** `migrate_refresh_token.py` (raíz)

**Uso:**
```powershell
python migrate_refresh_token.py
```

**Cambios aplicados:**
- Añade columna `ip_address VARCHAR(45)`
- Añade columna `user_agent VARCHAR(255)`

---

## Scripts de Utilidades

### run_api_with_cleanup.ps1

**Propósito:** Levanta la API con limpieza previa de procesos zombies

**Ubicación:** `scripts/run_api_with_cleanup.ps1`

**Uso:**
```powershell
.\scripts\run_api_with_cleanup.ps1 -JwtSecret 'mi_secret_app_local_larga' -DelegationSecret 'mi_secret_delegacion_local_larga'
```

**Parámetros:**
- `-JwtSecret` - Secret para access/refresh tokens
- `-DelegationSecret` - Secret para tokens de delegación

**Qué hace:**
1. Mata procesos Python/Flask antiguos
2. Activa virtualenv
3. Configura variables de entorno
4. Levanta API con `python -u main.py`

---

### start-api-with-env.ps1

**Propósito:** Levanta la API con variables de entorno predefinidas

**Ubicación:** `start-api-with-env.ps1` (raíz)

**Uso:**
```powershell
.\start-api-with-env.ps1
```

**Variables configuradas:**
- `DB_ENV=developmentAWS`
- `JWT_SECRET_KEY`, `JWT_DELEGATION_SECRET`
- `DEBUG=1`, `FLASK_DEBUG=1`
- `APP_ENV=development`

---

### verify_user.sql

**Propósito:** Script SQL para verificar estado de un usuario específico

**Ubicación:** `verify_user.sql` (raíz)

**Uso:**
```sql
-- Editar email en el script
-- Ejecutar en MySQL Workbench
```

**Información mostrada:**
- Datos del usuario
- Roles asignados
- Intentos fallidos y bloqueos
- Últimos logins

---

## Scripts de CI/CD

### GitHub Actions Workflow

**Ubicación:** `.github/workflows/test.yml`

**Triggers:**
- Push a `main`, `develop`, `ampliacion-proyecto`
- Pull requests

**Jobs:**
1. **Setup Python** (3.11)
2. **Install dependencies** (`requirements.txt` + `requirements-dev.txt`)
3. **Run seeder** (`init_db_pruebas_test.py --reset`)
4. **Run tests** (`pytest -q -s`)
5. **Export permissions** (`export_permissions.py`)
6. **Generate OpenAPI** (`dump_openapi.py`)
7. **Annotate params** (`annotate_openapi_params.py`)
8. **Validate params** (`validate_openapi_params.py --fail-on-missing`)
9. **Check operationIds** (`check_operation_ids.py`)
10. **Merge permissions** (`merge_permissions_into_openapi.py`)
11. **Validate sync** (`validate_permissions_sync.py`)
12. **Validate critical endpoints** (`validate_critical_endpoints.py`)
13. **Validate for mediator** (`validate_served_openapi_for_mediator.py`) **← BLOQUEANTE**
14. **Upload artifacts** (specs JSON/YAML + permissions.json)

**Artifacts publicados:**
- `openapi-auto.json`
- `openapi-auto.yml`
- `served-openapi.json` **← Usar este en mediador**
- `permissions.json`

---

## Resumen de Comandos Comunes

### Flujo Completo de Generación

```powershell
# 1. Exportar permisos
python scripts/export_permissions.py

# 2. Generar spec
python scripts/dump_openapi.py

# 3. Anotar parámetros
python scripts/annotate_openapi_params.py docs/openapi-auto.json

# 4. Fusionar permisos
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json

# 5. Validar sincronización
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json

# 6. Validar spec para mediador
python scripts/validate_served_openapi_for_mediador.py --spec docs/served-openapi.json
```

### Resetear BD y Levantar API

```powershell
# Resetear BD
python init_db_pruebas_test.py --reset

# Levantar API
.\scripts\run_api_with_cleanup.ps1 -JwtSecret 'mi_secret_app_local_larga' -DelegationSecret 'mi_secret_delegacion_local_larga'
```

### Ejecutar Tests

```powershell
# Todos los tests
pytest -q -s

# Tests específicos
pytest tests/usuarios/test_login.py -q -s

# Con logs guardados
pytest -q tests/usuarios/test_login.py -s 2>&1 | Tee-Object -FilePath .\logs\api_tests.log
```

---

## Recursos Adicionales

- [Workflow OpenAPI](OPENAPI_WORKFLOW.md) - Flujo completo explicado
- [Sistema de Permisos](PERMISSIONS.md) - Autorización
- [Autenticación JWT](AUTH.md) - Login/logout/refresh
- [Guía de Desarrollo](DEVELOPMENT.md) - Setup y debugging
