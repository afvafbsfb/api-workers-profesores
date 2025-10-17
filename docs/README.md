d# API Workers Profesores

--ejecucion de los scritps para generar y validar la especificacion del api para el mediador backend-chjatopenai:


Lo más probable: inicialmente el script no pudo generar por dependencias/entorno y estabas viendo un openapi-auto.json viejo. Después instalaste/ejecutaste correctamente y entonces el script pudo importar la app, detectar openapi_query_args y escribir el spec actualizado.
Para evitarlo en el futuro: guarda cambios, usa siempre el mismo intérprete/virtualenv, borra el openapi-auto.json viejo antes de generar y fíjate en la salida del script.


cd "c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"
# borrar auto-spec viejo
if (Test-Path .\docs\openapi-auto.json) { Remove-Item .\docs\openapi-auto.json -Force }

verificar que ¿Se puede importar apispec y marshmallow?:
python -c "import apispec, marshmallow; print('ok')"




# regenerar
python .\scripts\dump_openapi.py
# confirmar salida: debería decir "Wrote docs/openapi-auto.json and docs/openapi-auto.yml"


cd 'c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores'; python scripts/export_permissions.py; python scripts/dump_openapi.py; python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json; python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json; python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json

--ejecucion de los scritps para generar y validar la especificacion del api para el mediador backend-chjatopenai y para la especificacion swagger 
cd "c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"
python .\scripts\dump_openapi.py

# Anotar parámetros (genera cambios en docs/openapi-auto.json)
python .\scripts\annotate_openapi_params.py docs\openapi-auto.json

# Fusionar permisos y generar served-openapi.json
python .\scripts\merge_permissions_into_openapi.py docs\openapi-auto.json docs\served-openapi.json


python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json; python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json

# Ejecutar los tests (ejecuta todos los tests; puedes limitar a carpetas si quieres)
pytest -q







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
. .venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install --upgrade pip;
python -m pip install -r requirements.txt;
python -m pip install -r requirements-dev.txt
```

2) Variables de entorno útiles (solo para la sesión actual)

```powershell
# Opcional: ajustar según tu entorno
# $env:DB_ENV = 'developmentAWS'

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

# (opcional) activa el entorno virtual y exporta la secret delegada para pruebas
$env:DB_ENV = 'developmentAWS'
$env:JWT_SECRET_KEY = 'mi_secret_app_local_larga';
$env:DEBUG = '1';
$env:JWT_DELEGATION_SECRET = 'mi_secret_delegacion_local_larga';





# arrancar la app (o con tu comando habitual)
(.venv) PS C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores> python .\app.py

#otras opciones arrancar app:
python -m app
# o si usas main.pysaa
python main.py





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

Nuevo (oct-2025): claim display_name en el access token
-------------------------------------------------------

Con el objetivo de ahorrar una llamada extra al endpoint "mi perfil" en consumidores como el backend de chat, el access token ahora incluye un claim de nombre amigable:

- Claves incluidas: `display_name` y (alias) `name` con el mismo valor.
- Origen del valor: `Usuario.nombre` en el momento del login.
- Dónde se añade: en `additional_claims` del access token (NO se añade al refresh token).
- Compatibilidad: 100% retrocompatible. Servicios que no usen este claim lo ignoran.
- TTL: se recomienda mantener el TTL corto del access (15 min) para que posibles cambios de nombre se reflejen con rapidez.

Ejemplo de payload (parcial) del access token tras decodificar JWT:

```json
{
   "sub": "{\"usuario_id\":123,\"token_version\":2}",
   "type": "access",
   "roles": ["Admin_academia"],
   "academia_id": 77,
   "display_name": "Ana Pérez",
   "name": "Ana Pérez",
   "iat": 173...,
   "exp": 173...
}
```

Notas y buenas prácticas:
- No se añade al refresh token (mantenerlo mínimo y sin PII).
- Es un dato no sensible y de tamaño pequeño pensado para personalización.
- Consumidores OIDC pueden usar también claves estándar como `name`.

Verificación rápida (PowerShell):

```powershell
# Decodificar payload (base64url) del access y comprobar que aparecen display_name/name
$parts = $access.Split('.')
$payloadJson = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String(($parts[1].Replace('-', '+').Replace('_','/').PadRight($parts[1].Length + (4 - $parts[1].Length % 4) % 4, '='))))
$payloadJson | Out-Host
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


ejecutar test para ver los logs: 

# Crear la carpeta logs si no existe
New-Item -Path .\logs -ItemType Directory -Force

# Ejecutar el test y guardar stdout+stderr en el fichero
pytest -q tests/usuarios/test_login.py -s 2>&1 | Tee-Object -FilePath .\logs\api_tests.log





# validacion de end-points (solo valida end point logoff parametro en body de refresh token)
   pytest -q -s tests/test_openapi_requestbody.py

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
# Genera la especificacion: docs/openapi-auto.json y docs/openapi-auto.yml  a partir las rutas/blueprints que create_app() registra (todos los ficheros con blueprints registrados son fuente),
los attributes/decoradores en las view functions (operation_id, openapi_query_args, etc.),
los schemas Marshmallow que el script importa explícitamente (auth.py, academia.py), y
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

Fuente única / raíz de verdad
   Fuente de verdad del comportamiento (reglas reales que se ejecutan en runtime): permissions.py (las funciones can_*) junto con los operationId declarados por las rutas.
   
Justificación: permissions.py contiene la lógica aplicada en runtime (scoping, allowed/deny, sanitized payload); operationId en las rutas es cómo se enlazan operaciones con permisos cuando se genera la spec.
Qué NO es la fuente de verdad (pero sí artefactos importantes):
permissions.json, permissions_map.json, openapi-auto.json y served-openapi.json son artefactos derivados usados para revisión, mapeo y consumo (mediador), pero se generan a partir de permissions.py y del código de rutas; por tanto no reemplazan la lógica fuente.


ficheros que intervienen en la definición, exportación/transformación y consumo de permisos, y decir cuál es la raíz / fuente única de verdad.

Ficheros que intervienen:
permissions.py
      Lógica runtime de autorización: todas las funciones can_* (p. ej. can_query_academias, can_create_user, can_modify_user) — define reglas, scoping y sanización.

academias_routes.py
      Ejemplo de uso en rutas: llama a can_query_academias(...) y aplica enforced_filters/rechazo según resultado.

usuarios_routes.py
      Ejemplo de uso en rutas: llama a can_query_users, can_create_user, can_modify_user, can_delete_user.

export_permissions.py
      (Opcional/diagnóstico) Extrae metadatos de permissions.py y genera permissions.json / permissions.yaml.
      
permissions.json / permissions.yaml
      Artefacto generado que enumera las funciones/permissions extraídas; usado como entrada para el merge.

permissions_map.json
      Mapa editable (manual) que vincula nombres de permiso (funciones) a operationId de la spec; ayuda a decidir qué permiso aplica a qué operación.

      lo crean/editarán los desarrolladores responsables de la API (propietario del repositorio, equipo de backend o persona que añade el nuevo endpoint/permiso)

      Como se crea:  
         1) python scripts/export_permissions.py

           # -> genera docs/permissions.json (sugerencia de permisos extraídos)

           Wrote C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores\docs\permissions.yaml

           Wrote C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores\docs\permissions.json

         2) Generar spec desde código (para tener operationId actualizados) 
             python scripts/dump_openapi.py

             genera --> Wrote docs/openapi-auto.json and docs/openapi-auto.yml

                Ver en swagger la especificacion:
                   python main.py   (levanta el api en local en el puerto 5000)

               Abre en el navegador: http://localhost:5000/docs
               
               usuarios de pruebas:

                   {
                     "email": "admin_plataforma@academia.com",
                     "password": "password_admin_plataforma"
                   }


                   {
                     "email": "admin_academia@academia.com",
                     "password": "password_admin_academia"
                   }

                   {
                     "email": "user_academia_2_1@academia.com",
                     "password": "password_user_academia_2_1"
                   }


    


         3) Editar permissions_map.json manualmente añadiendo/ajustando entradas. Convenciones:
            Key = nombre de la función de permiso en permissions.py (ej. can_query_users).
            Campo "operationId" puede ser string o array de strings (p. ej. para PUT/PATCH).
            Opciones útiles: allowed_roles, scope o scope_by_role, enforced_filters, mutable_fields_by_role, note.
            Ejemplo mínimo (tomado del repo): { "can_query_users": { "operationId": "usuarios.listar_usuarios", "allowed_roles": ["admin_plataforma"], "scope": "global" } }

         4) Fusionar permisos en la spec y comprobar:

            python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json

            # Regenerar auto-spec (ya lo ejecutaste, pero por si acaso)


            genera el doc --> Wrote C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores\docs\served-openapi.json


         5) validar sincronia (local/CI). CI ejecuta estos pasos y fallará si el mapping no está correcto

            python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json

            python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json

      Papel en el flujo y relación con la “fuente de verdad”
      permissions_map.json es un mapa manual que conecta las funciones reales en permissions.py con operationId en la spec.
      La lógica ejecutada en runtime sigue siendo permissions.py (esa es la fuente de verdad del comportamiento). permissions_map.json es la fuente de verdad del mapeo permiso → operación que usan los scripts para inyectar x-permissions en served-openapi.json (consumido por el mediador).

      El backend-OpenAI solo necesita served-openapi.json. Ese fichero ya contiene las operaciones, los x-permissions y las components/schemas referenciadas (los $ref apuntan internamente), así que no requiere permissions_map.json para autorizar/validar en tiempo de ejecución.
      El campo "source": "permissions_map" que figura en el cuerpo del served-openapi.json es sólo metadato de procedencia (trazabilidad)


merge_permissions_into_openapi.py
      Fusiona openapi-auto.json + permissions.json + permissions_map.json e inyecta x-permissions por operación en served-openapi.json.
openapi-auto.json
      Spec generada automáticamente a partir del código (rutas, schemas).
served-openapi.json
      Spec final consumida por el mediador/servicios externos; contiene x-permissions añadidos por el merge.

      


validate_permissions_sync.py
      Validador que comprueba sincronía entre permissions_map.json, permissions.py y la spec (openapi-auto.json); usado en CI.
      test.yml

Flujo CI que ejecuta export/merge/validate para asegurar que served-openapi.json esté actualizado y que haya x-permissions en endpoints críticos.

(Consumidores/ejemplo externo) SpecLoaderService.java & AuthorizationServiceImpl.java

En el proyecto mediador/consumidor: cargan served-openapi.json y usan x-permissions (p. ej. allowed_roles, enforced_filters) para autorizar/transformar peticiones.





----
.`scripts/merge_permissions_into_openapi.py`: combina `docs/openapi-auto.json`, `docs/permissions.json` y `scripts/permissions_map.json` (mapa manual) para inyectar por operación el campo `x-permissions` con la metadata necesaria:
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

-  python scripts/validate_openapi_params.py --spec docs/openapi-auto.json --fail-on-missing

   - Valida que la especificación OpenAPI indicada contenga los parámetros query esperados para operaciones críticas (p. ej. GET /academias y GET /usuarios) y genera un informe JSON con el resultado.
   Si se pasa --fail-on-missing y falta algún parámetro esperado, imprime el informe y sale con código de error (exit != 0), haciendo fallar el job.

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
lo que hace CI (orden exacto):

1. Configura Python e instala dependencias.
2. Ejecuta el seeder y verifica que la base de datos de pruebas contiene datos (``python init_db_pruebas_test.py --reset`` y comprobaciones internas).
3. Ejecuta la suite de tests ordenada y genera el informe HTML (pytest).
4. Exporta permisos si existe el script: ``python scripts/export_permissions.py`` (opcional).
5. Regenera la especificación desde el código: ``python scripts/dump_openapi.py``.
6. Anota parámetros en la spec (si procede): ``python scripts/annotate_openapi_params.py docs/openapi-auto.json``.
7. Valida que la spec contiene los parámetros query esperados (nuevo paso bloqueante): ``python scripts/validate_openapi_params.py --spec docs/openapi-auto.json --fail-on-missing``.
8. Sincroniza copias raíz (openapi.json/openapi.yml) desde ``docs/openapi-auto.*`` (si procede).
9. Comprueba que todas las operaciones tienen `operationId`: ``python scripts/check_operation_ids.py --spec docs/openapi-auto.json``.
10. Fusiona permisos en la spec y produce el artefacto final: ``python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json``.
11. Valida sincronía de permisos y endpoints críticos:
    - ``python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json``
    - ``python scripts/validate_critical_endpoints.py --spec docs/served-openapi.json``
12. Ejecuta la validación del artefacto para el mediador (bloqueante): ``python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json``.
13. Sube artifacts: informe pytest, ``docs/openapi-auto.*``, ``docs/served-openapi.json``, y artefactos de permisos.

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
