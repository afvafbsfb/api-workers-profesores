# API Workers Profesores

Repositorio de desarrollo de la API para gestión de academias, usuarios y operaciones relacionadas.

Este README está centrado en el flujo actual de desarrollo (seeders, pruebas, generación de OpenAPI y uso de Swagger UI).

---

## Estructura relevante

- `app.py` - fábrica de la aplicación Flask y registro de blueprints.
- `main.py` - entrada auxiliar (si procede).
- `src/` - código de la aplicación (blueprints, servicios, esquemas, etc.).
  - `src/schemas/` - esquemas Marshmallow para validación y documentación.
  - `src/docs/` - blueprint para servir `/openapi.json` y `/docs` (Swagger UI).
- `scripts/dump_openapi.py` - script que vuelca la especificación OpenAPI a `docs/openapi-auto.json` / `.yml`.
- `docs/` - artefactos y documentación generada.
- `init_db_pruebas_test.py` - seeder idempotente para poblar datos de prueba.
- `tests/` - tests automatizados (pytest).

---

## Requisitos y virtualenv

Recomendado: usar la virtualenv del repo o crear una nueva.

PowerShell (ejemplos):

```powershell
# Activar venv existente
& ".\.venv/Scripts/Activate.ps1"

# O crear uno nuevo
python -m venv .venv
& ".\.venv/Scripts/Activate.ps1"

# Instalar dependencias
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

---

## Ejecutar la aplicación (desarrollo)

Opciones comunes:

1) Ejecutar directamente el script que contiene la fábrica:

```powershell
& ".venv/Scripts/python.exe" app.py
```

2) Usar la CLI de Flask (si prefieres):

```powershell
$env:FLASK_APP = "app:create_app"
& ".venv/Scripts/python.exe" -m flask run --host=0.0.0.0 --port=5000 --debug
```

Rutas útiles:
- `/health` → comprobación de estado.
- `/docs` → Swagger UI (si el blueprint está registrado).
- `/openapi.json` → especificación OpenAPI (generada o dinámica).

---

## Seeder de pruebas

El seeder `init_db_pruebas_test.py` inserta datos de prueba de forma idempotente y normaliza campos importantes para tests.

Para reset completo (DELETE + INSERT):

```powershell
& ".venv/Scripts/python.exe" init_db_pruebas_test.py --reset
```

Nota: el seeder crea usuarios `reserve_*` para pruebas destructivas; úsalos en tests que modifiquen datos.

---

## Documentación OpenAPI / Swagger

Flujo actual (code-first incremental):

- Generar spec desde el código:

```powershell
& ".venv/Scripts/python.exe" scripts/dump_openapi.py
```

- El script vuelca `docs/openapi-auto.json` y `docs/openapi-auto.yml`.
- `src/docs/swagger.py` sirve `/openapi.json` (usa la extensión apispec si está disponible) y `/docs` (página Swagger UI básica usando CDN).

Autorización en Swagger UI
- El spec incluye un security scheme `bearerAuth` (JWT). Para probar rutas protegidas:
  1. Ejecuta `POST /auth/login` desde la UI o con curl/PowerShell.
  2. Copia el `access_token` de la respuesta.
  3. Pulsa "Authorize" en Swagger UI e introduce: `Bearer <ACCESS_TOKEN>`.

Ejemplo (PowerShell):

```powershell
# Login y petición protegida
$body = @{ email = "reserve_activo@academia.com"; password = "password_reserve_activo" } | ConvertTo-Json
$response = Invoke-RestMethod -Uri "http://127.0.0.1:5000/auth/login" -Method POST -Body $body -ContentType "application/json"
$access = $response.tokens.access_token
Invoke-RestMethod -Uri "http://127.0.0.1:5000/academias" -Headers @{ Authorization = "Bearer $access" } -Method GET
```

---

## Tests (pytest)

Ejecutar la suite completa:

```powershell
& ".venv/Scripts/python.exe" -m pytest -q -s
```

Los tests se encuentran en `tests/` y usan fixtures y cuentas `reserve_*` para evitar interferencias.

---

## CI / GitHub Actions

El workflow actual ejecuta el seeder antes de los tests, corre los tests en orden y genera un reporte HTML (`report-all.html`) que se sube como artifact.

Recomendación: ejecutar `scripts/dump_openapi.py` en CI si quieres publicar la especificación generada como parte del build.

---

## Buenas prácticas y notas

- No exponer `Swagger UI` en producción: registra el blueprint solo en entornos `development`/`staging` o protege la ruta.
- Mantén los schemas en `src/schemas/` y reutilízalos en rutas y en el script de volcado.
- Usa las cuentas `reserve_*` para tests destructivos; no modificar los usuarios canónicos.
- Si mueves la base de datos o credenciales, usa variables de entorno o secrets en CI en lugar de valores en workflows.

---

Si quieres, puedo:

- Crear `docs/README.md` con los pasos exactos y ejemplos para desarrolladores.
- Proteger el blueprint `/docs` para que solo se registre fuera de `production`.

Indica cuál de los dos cambios quieres que haga y lo implemento.

