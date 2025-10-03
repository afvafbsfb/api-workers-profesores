# Pruebas locales de la API REST con MySQL o SQLite

Este documento describe cómo lanzar y probar la API REST en local usando **MySQL** o **SQLite** como base de datos, según la configuración del archivo `.env`.

## 1. Requisitos previos
- Python 3.11+ instalado
- Git Bash o PowerShell
- Entorno virtual configurado (`.venv`)
- Dependencias instaladas (`requirements.txt`)

## 2. Configuración del entorno

### a) Situarse en la carpeta del proyecto
```powershell
cd "C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"
```

### b) Crear y activar el entorno virtual (si no existe)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate
```

### c) Instalar dependencias
```powershell
pip install -r requirements.txt
```

### d) Configurar el archivo `.env`

- Para usar **MySQL** (desarrollo):
  ```env
  APP_ENV=development
  API_KEY_DEV=devkey-change-me
  DB_DEV_HOST=localhost
  DB_DEV_PORT=3307
  DB_DEV_USER=angel
  DB_DEV_PASS=Abanca0795
  DB_DEV_NAME=api_workers
  ```
- Para usar **SQLite** (por defecto):
  Comenta o elimina las variables `DB_DEV_*`:
  ```env
  APP_ENV=development
  API_KEY_DEV=devkey-change-me
  # DB_DEV_HOST=...
  # DB_DEV_PORT=...
  # DB_DEV_USER=...
  # DB_DEV_PASS=...
  # DB_DEV_NAME=...
  ```

**Nota:** Si las variables de MySQL están presentes y con valores, se usará MySQL. Si están ausentes o vacías, se usará SQLite automáticamente.

## 3. Inicializar la base de datos (opcional para SQLite)

```powershell
python init_db.py
```
Esto creará las tablas y poblará datos de ejemplo en SQLite.

## 4. Lanzar la aplicación

```powershell
python app.py
```
La API estará disponible en `http://localhost:5000`.

## 5. Probar los endpoints

### Ejemplo: Health check
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/health" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```

### Ejemplo: Listar alumnos (sin paginación)
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```
O usando curl (Git Bash):
```sh
curl -X GET "http://localhost:5000/vlodeiro/secretaria/alumnos" -H "X-Api-Key: devkey-change-me"
```

### Ejemplo: Listar alumnos con paginación
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos?page=0&size=2" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```
O usando curl (Git Bash):
```sh
curl -X GET "http://localhost:5000/vlodeiro/secretaria/alumnos?page=0&size=2" -H "X-Api-Key: devkey-change-me"
```

En todos los casos, la respuesta incluye los campos `list`, `total`, `page`, `size` y `hasMore`.

## 6. Pruebas automáticas

El fichero de tests `tests/test_endpoints.py` funciona igual para:
- SQLite local (por defecto)
- MySQL local/remoto
- Producción (API remota)

### ¿Cómo lanzar los tests?

- Por defecto (SQLite o MySQL según `.env`):

    ```powershell
    .\.venv\Scripts\Activate
    pip install pytest
    pytest
    ```

- Contra una API remota (MySQL o producción):
    ```powershell
    $env:USE_LIVE=1; $env:BASE_URL="https://tu-api-remota.com"; pytest
    ```
    O en Linux/macOS:
    ```sh
    USE_LIVE=1 BASE_URL="https://tu-api-remota.com" pytest
    ```

Si `USE_LIVE=1`, los tests usan peticiones HTTP reales y no manipulan la base de datos local.
Si no, usan el cliente Flask y la base de datos local (SQLite o la que tengas configurada).

---

Para cualquier error, revisa la consola donde lanzaste la app y asegúrate de que el entorno virtual está activo y las dependencias instaladas.

**Resumen:**
- Si el `.env` tiene las variables de MySQL con valores, usas MySQL.
- Si no, usas SQLite.
- No necesitas modificar el código fuente, solo el `.env` y reiniciar la API.

# 7. Pruebas desde Swagger UI en desarrollo

Puedes probar todos los endpoints de la API de forma visual e interactiva usando Swagger UI:

- **URL de Swagger UI en desarrollo:** [http://localhost:5000/docs](http://localhost:5000/docs)
- **API Key de pruebas:** Usa el valor de `API_KEY_DEV` de tu `.env` (por defecto suele ser `devkey-change-me`)
- **Selección de servidor:** En el desplegable de servidores de Swagger UI, selecciona `http://localhost:5000` para hacer pruebas contra tu backend local.

**Pasos:**
1. Accede a [http://localhost:5000/docs](http://localhost:5000/docs) en tu navegador.
2. Haz clic en el botón "Authorize" (candado) e introduce tu API Key de desarrollo.
3. Selecciona el servidor `http://localhost:5000` en el combo de servidores.
4. Prueba los endpoints y la paginación desde la interfaz Swagger.

Así puedes validar fácilmente la API y la autenticación en local antes de desplegar a producción.