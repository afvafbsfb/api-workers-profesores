
# Pruebas locales de la API REST con base de datos SQLite

Este documento describe los pasos para lanzar y probar la API REST en local usando SQLite como base de datos.

## 1. Requisitos previos
- Python 3.11+ instalado
- Git Bash o PowerShell
- Entorno virtual configurado (`.venv`)
- Dependencias instaladas (`requirements.txt`)

## 2. Preparar el entorno

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

### d) Crear el archivo `.env` (si no existe)
```env
APP_ENV=development
API_KEY_DEV=devkey-change-me
```

## 3. Inicializar la base de datos SQLite

```powershell
python init_db.py
```
Esto creará las tablas y poblará datos de ejemplo.

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

### Ejemplo: Listar alumnos con paginación (página inicial)
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos?page=0&size=2" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```
O usando curl (Git Bash):
```sh
curl -X GET "http://localhost:5000/vlodeiro/secretaria/alumnos?page=0&size=2" -H "X-Api-Key: devkey-change-me"
```

### Ejemplo: Listar alumnos con paginación (página 1)
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos?page=1&size=2" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```
O usando curl (Git Bash):
```sh
curl -X GET "http://localhost:5000/vlodeiro/secretaria/alumnos?page=1&size=2" -H "X-Api-Key: devkey-change-me"
```

En todos los casos, la respuesta incluye los campos `list`, `total`, `page`, `size` y `hasMore`.


## 6. Notas y pruebas automáticas en distintos entornos

- La base de datos SQLite se crea en `instance/local.db`.
- Puedes modificar o poblar más datos usando los scripts de inicialización.
- Si cambias la API Key, actualízala en el archivo `.env` y en los headers de tus peticiones.

### Pruebas automáticas (`tests/test_endpoints.py`)

Este fichero de tests funciona igual para:
- SQLite local (por defecto)
- MySQL local/remoto
- Producción (API remota)

**¿Cómo lanzar los tests?**

- Por defecto (SQLite local):

.\.venv\Scripts\Activate
pip install pytest

	```powershell
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
