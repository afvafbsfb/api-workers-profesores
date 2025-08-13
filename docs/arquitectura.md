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
