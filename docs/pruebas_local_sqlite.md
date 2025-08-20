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

### Ejemplo: Listar alumnos
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos" -Headers @{ "X-Api-Key" = "devkey-change-me" }
```

O usando curl (Git Bash):
```sh
curl -X GET "http://localhost:5000/vlodeiro/secretaria/alumnos" -H "X-Api-Key: devkey-change-me"
```

## 6. Notas
- La base de datos SQLite se crea en `instance/local.db`.
- Puedes modificar o poblar más datos usando los scripts de inicialización.
- Si cambias la API Key, actualízala en el archivo `.env` y en los headers de tus peticiones.

---

Para cualquier error, revisa la consola donde lanzaste la app y asegúrate de que el entorno virtual está activo y las dependencias instaladas.
