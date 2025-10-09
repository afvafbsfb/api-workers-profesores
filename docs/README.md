d# API Workers Profesores

Esto es un README nuevo y completo para desarrollo, pruebas y documentación de la API.

Contenido rápido
- Setup local (venv, deps)
- Seeder y datos de prueba
- Cómo arrancar la app (desarrollo)
- Uso de Swagger UI (/docs) y de la especificación OpenAPI
- Detalle del endpoint `POST /auth/logout` (uso de refresh token)
- Ejecutar tests (pytest)
- Checklist antes de commit/push

Requisitos
- Python 3.11+
- Virtualenv
- MySQL (local o remoto) según `DATABASE_URL` o la configuración en `config.py`

1) Preparar el entorno (PowerShell)

```powershell
# Sitúate en la raíz del repo
Set-Location 'C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores'

# Crear y activar virtualenv
python -m venv .venv
. .\.venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

2) Variables de entorno útiles (solo para la sesión actual)

```powershell
# Opcional: ajustar según tu entorno
# $env:DB_ENV = 'development'
# $env:DATABASE_URL = 'mysql+pymysql://user:pass@host:port/db'
# $env:JWT_SECRET_KEY = 'mi-secreto-local'
```

3) Seeder — poblar datos de prueba

El seeder `init_db_pruebas_test.py` crea roles, academias y usuarios `reserve_*` para pruebas.

```powershell
python init_db_pruebas_test.py --reset
```

Observa la salida: el script imprime un resumen con usuarios y (temporalmente) las contraseñas planas para pruebas.

4) Arrancar la aplicación (desarrollo)

Opción recomendada (ver logs):

```powershell
python main.py
```

Alternativa (flask run):

```powershell
$env:FLASK_APP = 'main.py'
flask run --port 5000
```

5) Documentación y Swagger UI

- Abre en el navegador: `http://localhost:5000/docs`
- La UI carga la especificación desde `/openapi.json`. También existe `/openapi-auto.json` (archivo generado en `docs/`).

Si ves "No API definition provided":

1. Comprueba que `http://localhost:5000/openapi.json` devuelve JSON (usa `Invoke-RestMethod`).
2. Limpia la caché del navegador y recarga la página.

6) Uso del endpoint `/auth/logout` (importante)

Resumen: `POST /auth/logout` revoca el refresh token.

Requisitos:
- Debes enviar un refresh token. Opciones:
	- En header: `Authorization: Bearer <REFRESH_TOKEN>` (modo que utilizan los tests existentes).
	- En body JSON: `{ "refresh_token": "<REFRESH_TOKEN>" }` (útil desde Swagger UI cuando la UI haya puesto un access token en Authorization).

Comportamiento:
- Si envías un access token en Authorization y no envías refresh en body → 422 `Only refresh tokens are allowed`.
- Si envías header con refresh o body con refresh válido → 200 {"ok": true} (token marcado como revocado en BD).

7) Ejemplos PowerShell rápidos

Login y obtener tokens:

```powershell
$body = @{ email = 'reserve_activo@academia.com'; password = '...' } | ConvertTo-Json
$resp = Invoke-RestMethod -Uri 'http://localhost:5000/auth/login' -Method Post -Body $body -ContentType 'application/json'
$access = $resp.tokens.access_token
$refresh = $resp.tokens.refresh_token
```

Logout usando body + header access (caso Swagger UI):

```powershell
$headers = @{ Authorization = "Bearer $access"; 'Content-Type' = 'application/json' }
$payload = @{ refresh_token = $refresh } | ConvertTo-Json
Invoke-RestMethod -Uri 'http://localhost:5000/auth/logout' -Method Post -Headers $headers -Body $payload
```

Logout usando refresh en header:

```powershell
Invoke-RestMethod -Uri 'http://localhost:5000/auth/logout' -Method Post -Headers @{ Authorization = "Bearer $refresh" }
```

8) Ejecutar tests (pytest)

Tests de autenticación:

```powershell
python -m pytest tests/usuarios/test_login.py -q -s
python -m pytest tests/usuarios/test_refresh_logout.py -q -s
```

Ejecutar la suite completa:

```powershell
python -m pytest -q -s
```

Los tests usan cuentas `reserve_*` creadas por el seeder.

9) Generar OpenAPI para publicar (opcional)

```powershell
python scripts/dump_openapi.py
# Genera: docs/openapi-auto.json y docs/openapi-auto.yml
```

10) Checklist antes de commit/push

1. Ejecuta y supera los tests (`pytest`).
2. Asegúrate de haber ejecutado el seeder si los tests o cambios lo requieren.
3. Genera OpenAPI si has cambiado rutas/schemas.
4. Revisa `/docs` y `/openapi.json` manualmente.

11) Notas y buenas prácticas

- No expongas `/docs` en producción sin control de acceso.
- Mantén las pruebas reproducibles usando las cuentas `reserve_*`.
- Si necesitas, puedo añadir un `docs/README.md` con ejemplos HTTP/Postman.

---

Administración de permisos (roles) — qué leer y cómo se usa
---------------------------------------------------------

La lógica de autorización se implementa en `src/shared/application/permissions.py` (fuente de verdad). Para que otros servicios —especialmente el mediador `backend-OpenAI`— puedan comprender las reglas sin ejecutar código, generamos artefactos estáticos y unificamos la información en un único spec final consumible.

Archivos relevantes (en este repositorio)
- `src/shared/application/permissions.py` — implementación de las funciones `can_*`.
- `scripts/export_permissions.py` — extrae metadatos desde `permissions.py` y genera:
  - `docs/permissions.yaml`
  - `docs/permissions.json`
- `scripts/roles_whitelist.txt` — roles canónicos (ej.: `Admin_plataforma`, `Admin_academia`, `Profesor_academia`).
- `scripts/dump_openapi.py` — genera `docs/openapi-auto.json` / `.yml` desde el código.
- `scripts/permissions_map.json` — (mapa explícito) mapeo permiso → operationId y metadata enriquecida (scope, enforced_filters, allowed_target_roles, mutable_fields_by_role).
- `scripts/merge_permissions_into_openapi.py` — combina `docs/openapi-auto.json` y `docs/permissions.json` (y el mapa) e inyecta `x-permissions` por operación.
- `docs/served-openapi.json` — ARTIFACTO ÚNICO RECOMENDADO (final) que contiene rutas, parámetros, responses y `x-permissions`.
- `docs/permissions-mapping-report.json`, `docs/permissions-validation-report.json` — informes de mapeo y validación generados en CI/local.

Qué debe leer el mediador (backend-OpenAI)
1. Primario (recomendado): `docs/served-openapi.json`
   - Contiene: `paths`, `operationId`, `parameters`, `responses[200].content` (schemas), y por operación `x-permissions` con:
     - `allowed_roles`, `scope` (e.g. `own_academia`, `own_user`, `global`)
     - `enforced_filters` (p. ej. `"academia_id": "current_user.academia_id"`)
     - `allowed_target_roles` (qué roles puede asignar cada rol)
     - `mutable_fields_by_role` (qué campos puede modificar cada rol)
     - `generated_at`, `source`
   - Con este único archivo el mediador puede construir prompts, validar propuestas y aplicar filtros de ámbito sin combinar fuentes en tiempo de ejecución.

2. Secundario (opcional, diagnóstico): `docs/permissions.json` y `docs/openapi-auto.json` — útiles para debugging humano o auditoría, pero no necesarios en producción si existe `served-openapi.json`.

Flujo recomendado antes de cada despliegue / CI (repo API)
1. En el job de CI del repo API:
   1. `python scripts/export_permissions.py` → genera `docs/permissions.*`.
   2. `python scripts/dump_openapi.py` → genera `docs/openapi-auto.json` / `.yml`.
   3. `python scripts/merge_permissions_into_openapi.py` → genera `docs/served-openapi.json` (añade `operationId`, `responses[200].content` donde haga falta e inyecta `x-permissions` usando `permissions.json` y `permissions_map.json`).
   4. Subir `docs/served-openapi.json` (y opcionalmente `docs/permissions.json`) como artifact del job de CI (o publicarlo en bucket/versioned release).

Flujo recomendado en el mediador (CI o runtime)
1. Descargar el artifact `served-openapi.json` del último run exitoso del workflow del repo API (recomendado: GitHub Actions artifacts).
2. Validar integridad y contenido mínimo (JSON válido, `paths` con endpoints críticos, `x-permissions` presentes para ellos).
3. Usar `served-openapi.json` para:
   - Construir el system prompt / function schema para OpenAI.
   - Validar cualquier `tool_call` propuesto por el modelo contra `x-permissions` y aplicar `enforced_filters` (ej. `academia_id = current_user.academia_id`) antes de ejecutar la llamada.
   - Rechazar o ajustar propuestas que intenten actuar fuera del `scope` o asignen roles no permitidos.

Nota de seguridad y responsabilidad
- El mediador usa `served-openapi.json` para decidir y validar, pero la AUTORIZACIÓN FINAL debe realizarla siempre el API (p. ej. `AuthorizationService`) en tiempo de ejecución. No ejecutar sensibles basadas sólo en la recomendación del modelo.
- Si el repo es privado, usar secrets con permisos mínimos (actions:read o repo:contents read) para descargar artifacts.

Mantenimiento y buenas prácticas
- Incluir `generated_at` y `git_commit` dentro de `served-openapi.json` para trazabilidad.
- Regenerar `served-openapi.json` en CI en cada push que cambie rutas / permisos.
- Añadir tests en la CI del mediador que fallen si `served-openapi.json` no contiene `x-permissions` para endpoints críticos (p. ej. `/usuarios`, `/academias`).
- Mantener actualizado `scripts/permissions_map.json` cuando se renombren permisos o `operationId`.

Ejemplo breve de uso en el mediador
- Descargar artifact → extraer `docs/served-openapi.json` → comprobar `paths["/usuarios/"].get.x-permissions.scope == "own_academia"` → añadir `academia_id=current_user.academia_id` a la query generada por el modelo.

// ...existing code...


