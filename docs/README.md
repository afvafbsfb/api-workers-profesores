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
python -m 

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

$env:DB_ENV = 'developmentAWS'


(.venv) PS C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores> python .\init_db_pruebas_test.py --reset


cd 'C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores'; .\.venv\Scripts\python.exe init_db_pruebas_test.py --reset


Tests unitarios / de integración - instrucciones por fichero (orden exacto usado en CI):

```powershell
# A. Academias (ejecutados primero en CI)
python -m pytest tests/academias/test_altas_bajas_academias.py -q -s
python -m pytest tests/academias/test_busquedas_academias.py -q -s
python -m pytest tests/academias/test_academias_post.py -q -s
python -m pytest tests/academias/test_academias_get_patch.py -q -s

# B. Usuarios (ejecutados después de los tests de academias en CI)

python -m pytest tests/usuarios/test_altas_bajas_usuarios.py -q -s
python -m pytest tests/usuarios/test_busquedas_usuarios.py -q -s
python -m pytest tests/usuarios/test_login.py -q -s
python -m pytest tests/usuarios/test_jwt_claims.py -q -s
python -m pytest tests/usuarios/test_unblock.py -q -s
python -m pytest tests/usuarios/test_refresh_logout.py -q -s

# Ejecutar la suite completa (todos los tests)
python -m pytest -q -s
```
# Ejecutar la suite completa (todos los tests)
python -m pytest -q -s
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

Resumen rápido
--------------
La fuente de verdad para la autorización son dos tipos de artefactos dentro del código fuente:

- Las reglas de autorización y adaptadores en runtime: `src/shared/application/permissions.py`. Aquí residen las funciones `can_*` que definen la lógica real que se ejecuta cuando el API decide permitir, restringir o transformar una operación.

- Los endpoints instrumentados con un `operationId` determinado en sus rutas (por ejemplo `src/autenticacion/interfaces/flask/login_routes.py`, `src/academias/interfaces/flask/academias_routes.py`, `src/usuarios/interfaces/usuarios_routes.py`). Estas rutas son la fuente de verdad del identificador estable (`operationId`) que usamos para mapear permisos a operaciones.


Por claridad: el código (las funciones de `permissions.py` y los `operationId` en las rutas) es la fuente de verdad. Los ficheros en `docs/` son artefactos generados que sirven para consumo del mediador (backend-OpenAI), auditoría y despliegue.

Cómo se llega desde las fuentes de verdad hasta el artefacto consumible (`docs/served-openapi.json`):

1. `scripts/export_permissions.py` (opcional / diagnóstico): extrae metadatos a partir de `src/shared/application/permissions.py` y genera `docs/permissions.json` / `docs/permissions.yaml`. Esto facilita la revisión humana y sirve como base para el mapeo automático.

2. `scripts/dump_openapi.py`: recorre las rutas/blueprints del código, genera `docs/openapi-auto.json` (y `.yml`) garantizando que cada operación tenga un `operationId` estable. El `operationId` preferido se extrae de la propiedad aplicada en la view function (decorador/documentación en la ruta); si falta, se deriva con heurísticas.

3. `scripts/merge_permissions_into_openapi.py`: combina `docs/openapi-auto.json`, `docs/permissions.json` y `scripts/permissions_map.json` (mapa manual) para inyectar por operación el campo `x-permissions` con la metadata necesaria:
    - `allowed_roles` (lista normalizada de roles)
    - `scope` o `scope_by_role` (p.ej. `own_academia`, `own_user`, `global`)
    - `enforced_filters` (ej. `academia_id: current_user.academia_id`)
    - `allowed_target_roles` y `mutable_fields_by_role` (cuando aplican)
    - `source` y `generated_at` (trazabilidad)

    El resultado final es `docs/served-openapi.json`, el artefacto único recomendado para consumo del mediador.

Qué debe leer el mediador (backend-OpenAI)
-----------------------------------------
Principal: `docs/served-openapi.json`.

- Por operación obtiene `operationId` y `x-permissions`; con esto puede aplicar reglas de negocio en prompts y validar propuestas del modelo.

- `served-openapi.json` contiene además `paths`, `parameters`, `responses` y los `schemas` necesarios para construir prompts y validar las llamadas a la API.

Secundario (solo para debugging humano): `docs/openapi-auto.json` y `docs/permissions.json`.

Lista de scripts útiles y qué hacen
----------------------------------
- `scripts/export_permissions.py`
   - Extrae metadatos de `src/shared/application/permissions.py` y genera `docs/permissions.json` / `docs/permissions.yaml`.

   - Útil para auditoría y para tener un primer intento de mapeo automático.

- `scripts/dump_openapi.py`
   - Recorre el código (blueprints/routes) y genera `docs/openapi-auto.json` y `docs/openapi-auto.yml`.

   - Respeta `operation_id` cuando está definido en la view function; aplica heurísticas seguras cuando falta.

- `scripts/permissions_map.json` (no es un script, es un artefacto editable)

   - Archivo JSON donde se pueden definir mappings explícitos: `perm_name -> operationId | [operationId] | { operationId: ..., scope: ..., allowed_roles: ... }`.

   - Útil para operaciones multi-method (PUT/PATCH) o casos donde la heurística no acierta.

- `scripts/merge_permissions_into_openapi.py`
   - Fusiona `docs/openapi-auto.json` + `docs/permissions.json` + `scripts/permissions_map.json` y escribe `docs/served-openapi.json`.

   - Inyecta `x-permissions` por operación y normaliza keys/roles. También añade `operationId` faltantes y respuestas 200 heurísticas cuando procede.

- `scripts/validate_permissions_sync.py`
   - Valida sincronía entre `scripts/permissions_map.json`, `src/shared/application/permissions.py` y la spec (`docs/openapi-auto.json`).

   - Detecta permisos sin función homónima, operationIds faltantes y problemas heurísticos de scope.

- `scripts/check_operation_ids.py`
   - Comprueba que todas las operaciones de una spec OpenAPI (por defecto `docs/openapi-auto.json`) tienen un `operationId` no vacío.

   - Uso: `python scripts/check_operation_ids.py --spec docs/openapi-auto.json`. Sale con código 1 si faltan operationIds (útil para CI).

- `scripts/validate_critical_endpoints.py`
   - Heurísticamente identifica endpoints críticos (incluye GETs sensibles) y comprueba que tienen `operationId`, `x-permissions` y `security`.
   - Útil para bloquear regresiones de seguridad.

- `scripts/validate_served_openapi_for_mediator.py`
   - Comprueba que `docs/served-openapi.json` contiene la información mínima requerida para que el mediador construya prompts y valide llamadas (paths, operationId, x-permissions en endpoints críticos, schemas mínimos).

   - Nota: ESTE VALIDADOR ES OBLIGATORIO EN CI. El script sale con código de error distinto de 0 si detecta problemas, por lo que la ejecución en CI fallará y bloqueará el job cuando haya issues. Ejecuta localmente para comprobar antes de push:
     ```powershell
     python .\scripts\validate_served_openapi_for_mediator.py --spec .\docs\served-openapi.json
     # Para aplicar normalizaciones automáticas (si aplica):
     python .\scripts\validate_served_openapi_for_mediator.py --spec .\docs\served-openapi.json --fix
     ```

- `scripts/dump_openapi.py`, `scripts/json_to_yaml.py`, `scripts/compare_openapi.py`, `scripts/openapi_param_changes_report.py`
   - Herramientas auxiliares para generar, convertir y comparar specs, útiles para revisar cambios entre versiones de la API.

Buenas prácticas y flujo en CI
-----------------------------
- Añadir un job de CI en el repo API que ejecute, en orden:
   1. `python scripts/export_permissions.py`
   2. `python scripts/dump_openapi.py`
   3. `python scripts/check_operation_ids.py --spec docs/openapi-auto.json`
      - Comprueba que la spec generada contiene `operationId` para todas las operaciones (falla con código 1 si faltan).
   3. `python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json`
   4. `python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json`
   5. `python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json`
   6. `python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json`  (MANDATORY: fails CI when issues are found)

- Subir `docs/served-openapi.json` como artifact del job (o publicarlo en un S3/versioned-bucket). El mediador debe descargar ese artifact y no generar su propio mash-up desde el código del API.

Notas finales
------------
- Fuente de verdad del runtime: `src/shared/application/permissions.py` + `operationId` en las rutas (login/academias/usuarios).

- Artifactorigén: `docs/served-openapi.json` es el formato recomendado para consumo por el mediador y debe ser generado en CI a partir del código fuente y los mapas de permisos.
- Si quieres, preparo un workflow de GitHub Actions que automatice el pipeline y publique el artifact `served-openapi.json`. 

========================================================
checklist minimalísimo y directo al grano para añadir CRUD de Cursos + Aulas + Horario y garantizar operationId + permisos desde el inicio:

API design

Definir operationId por operación: cursos.list, cursos.create, cursos.get, cursos.update, cursos.delete (igual para aulas/horario: aulas., horarios.).
Código: rutas / handlers

Crear blueprint (p. ej. src/academias/interfaces/flask/cursos_routes.py) y registrar en main.py.
En cada view function fijar el operationId (ejemplo): view_fn.operation_id = 'cursos.create' o usar el decorador que ya usáis.
Permissions runtime

Añadir funciones en permissions.py: can_view_cursos, can_manage_cursos (determinando allowed_roles / scope).
Mantener nombres claros que encajen con permissions_map.json si lo usas.
Mapear permisos a operationId

Editar permissions_map.json o confiar en export_permissions.py para exponer las funciones y añadir entradas que vinculen permiso → operationId (+ scope/allowed_roles).
Schemas / validation

Añadir/actualizar Marshmallow schemas y request/response models usados por las rutas.
Tests mínimos

Crear tests para cada endpoint (happy-path) y uno que verifique x-permissions/security en served-openapi.json (o ejecutar los scripts de validación más abajo).
Generar y validar (comandos que debes ejecutar)

python dump_openapi.py
python check_operation_ids.py --spec openapi-auto.json
python merge_permissions_into_openapi.py --spec openapi-auto.json --out served-openapi.json
python validate_permissions_sync.py --map permissions_map.json --code permissions.py --spec openapi-auto.json
python validate_served_openapi_for_mediator.py --spec served-openapi.json
Criterio de éxito: todos los pasos devuelven exit code 0 y served-openapi.json contiene para cada operationId su x-permissions.
Edge cases a revisar (rápido)

Mismo path, distintos métodos → cada método necesita un operationId distinto.
Operaciones “own_*” necesitan scope/scope_by_role correctos.
Si usas wrappers/adaptadores en permissions, asegúrate que export_permissions.py las exponga con el nombre esperado.
