# Principios clave de la arquitectura

- **Arquitectura DDD (Domain Driven Design):**  
	✔️ El proyecto está organizado por dominios (`vlodeiro/empresa`, `vlodeiro/secretaria`) y capas (`domain`, `application`, `infrastructure`, `interfaces`).

- **Separación clara entre dominio, infraestructura y presentación:**  
	✔️ Cada dominio tiene sus propias carpetas para lógica de negocio, acceso a datos y endpoints HTTP.

- **Endpoints REST protegidos por API Key (X-Api-Key):**  
	✔️ Parcialmente.  
	Los endpoints están protegidos por API Key, pero la API está expuesta mediante AWS API Gateway (HTTP API), no como REST API Gateway clásico.  
	La validación de la API Key se realiza en el backend Flask, no en el gateway.

- **Despliegue:**  
	✔️ El despliegue se realiza en AWS Elastic Beanstalk, no en cPanel.

# Arquitectura y organización del proyecto Workers API

## Estructura principal

- `app.py`: Entrada principal de la aplicación Flask, configuración y registro de blueprints.
- `auth.py`: Módulo independiente para la autenticación por API Key (decoradores y protección global de endpoints).
- `models.py`: Modelos globales de SQLAlchemy.
- `vlodeiro/`: Módulo principal, dividido por dominios:
	- `empresa/`, `secretaria/`...
		- `domain/`: Lógica de negocio y modelos de dominio.
		- `application/`: Casos de uso y servicios.
		- `infrastructure/`: Repositorios y acceso a datos.
		- `interfaces/`: Endpoints Flask y rutas HTTP.
- `tests/`: Pruebas unitarias y de integración.
- `docs/`: Documentación extendida y ejemplos.

> Nota: Desde agosto 2025, la autenticación por API Key está modularizada en `auth.py` y ya no reside en `app.py`.

# Flujo típico de una petición

1. El usuario realiza una petición HTTP a un endpoint (por ejemplo, `/vlodeiro/secretaria/alumnos/2`).
2. El endpoint valida la API Key y los parámetros de entrada.
3. Se consulta el dominio correspondiente (por ejemplo, `Alumno`) y se ejecuta la lógica de negocio.
4. El resultado se devuelve en formato JSON.

# Dependencias principales

El proyecto utiliza las siguientes dependencias principales:

- Flask
- Flask-SQLAlchemy
- Marshmallow
- flask-cors
- python-dotenv
- pymysql
- cryptography
- requests
- pyyaml
- gunicorn
- awsgi (solo en Linux)

Para testing y desarrollo:
- pytest
- pytest-cov

# Ejemplos de uso

Para ver y probar ejemplos de todos los endpoints, consulta la documentación interactiva en Swagger UI:

**[Swagger UI / OpenAPI REST (documentación y pruebas de endpoints)](https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml)**

Allí puedes ver los parámetros, respuestas y realizar pruebas en tiempo real sobre la API.