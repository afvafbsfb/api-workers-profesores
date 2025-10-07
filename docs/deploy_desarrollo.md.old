
# Despliegue y pruebas en desarrollo

> **Nota:** Este documento es solo para el entorno de desarrollo local (Flask en localhost, SQLite/MySQL de desarrollo). Para despliegue en AWS y API REST consulta `deploy_aws.md` y la documentación de la API REST.

## 1. Configuración de la base de datos

- Por defecto, el proyecto puede funcionar con SQLite local (`local.db`) o con una base de datos MySQL de desarrollo.
- Para usar MySQL de desarrollo, configura las variables de entorno:
  - `DB_DEV_HOST`
  - `DB_DEV_PORT`
  - `DB_DEV_USER`
  - `DB_DEV_PASS`
  - `DB_DEV_NAME`
- Si no se configuran, se usará SQLite local.

## 2. Levantar el entorno de desarrollo

- Crea y activa un entorno virtual:
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- Instala las dependencias:
  ```powershell
  pip install -r requirements.txt
  pip install -r requirements-dev.txt
  ```
- Inicializa la base de datos (si es necesario):
  ```powershell
  python init_db.py
  ```

## 3. Ejecutar la aplicación

- Lanza el servidor Flask:
  ```powershell
  python app.py
  ```
  o usando Gunicorn (opcional):
  ```powershell
  gunicorn -w 4 -b 127.0.0.1:5000 app:app
  ```

## 4. Ejecutar los tests

- Ejecuta los tests y revisa la cobertura:
  ```powershell
  pytest --cov
  ```

## 5. Notas

- No uses nunca la base de datos de producción para pruebas locales.
- Puedes cambiar entre SQLite y MySQL de desarrollo modificando las variables de entorno.
- Para pruebas de endpoints, usa Swagger UI en `http://localhost:5000/docs` o herramientas como Postman/curl.
