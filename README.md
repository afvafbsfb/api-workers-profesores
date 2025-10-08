# API Workers Profesores

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

Si quieres que haga commit y push de este README a la rama actual, dime y lo hago con un mensaje de commit descriptivo.

