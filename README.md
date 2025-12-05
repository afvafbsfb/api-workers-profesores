# API Workers Profesores - Backend REST

> **API REST backend para gestión de academias mediante sistema de permisos avanzado**  
> Proyecto Final de Ciclo - FP DAM | Ángel Fernández Vidal | 2025

## 📋 Descripción

API REST backend para la gestión integral de academias, incluyendo usuarios, alumnos, cursos, sesiones, inscripciones y gestión financiera. Implementa autenticación JWT con refresh tokens, sistema de permisos basado en roles (RBAC) con scoping multi-tenancy, y arquitectura Domain-Driven Design (DDD).

### Características Principales

- 🔐 **Autenticación JWT** con refresh tokens rotatorios (15min access + 30 días refresh)
- 👥 **Sistema de roles**: Admin_plataforma, Admin_academia, Profesor_academia
- 🏢 **Multi-tenancy** con scoping por academia_id
- 📊 **20+ entidades** del dominio académico y financiero
- 🔒 **Sistema de permisos avanzado** con extensión OpenAPI (x-permissions)
- 📝 **Especificación OpenAPI** automática con anotaciones de permisos
- 🧪 **Testing completo** con pytest (unitarios + integración)
- 🗄️ **MySQL 8.0** con SQLAlchemy ORM
- 🚀 **Arquitectura DDD** (Domain-Driven Design)

## 🏗️ Stack Tecnológico

| Componente | Tecnología | Versión |
|------------|------------|---------|
| **Lenguaje** | Python | 3.11+ |
| **Framework Web** | Flask | 3.0.0 |
| **ORM** | SQLAlchemy | 2.0.23 |
| **Base de Datos** | MySQL | 8.0 |
| **Autenticación** | Flask-JWT-Extended | 4.5.3 |
| **Validación** | Marshmallow | 3.20.1 |
| **Testing** | pytest | 7.4.3 |
| **API Docs** | Flasgger (Swagger UI) | 0.9.7.1 |
| **CORS** | Flask-CORS | 4.0.0 |
| **Migrations** | Alembic | 1.12.1 |

## 📋 Requisitos

- **Python 3.11+**
- **MySQL 8.0** (local o AWS RDS)
- **Virtualenv** recomendado

## 🚀 Quick Start

### 1. Setup del Entorno

```powershell
# Navegar a la raíz del proyecto
Set-Location 'C:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores'

# Crear virtualenv si no existe
if (-not (Test-Path .venv)) { python -m venv .venv }

# Activar virtualenv
.\.venv\Scripts\Activate.ps1

# Instalar dependencias
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

### 2. Configurar Variables de Entorno

```powershell
# Variables para desarrollo local (RDS development)
$env:DB_ENV = 'developmentAWS'
$env:JWT_SECRET_KEY = 'mi_secret_app_local_larga'
$env:JWT_DELEGATION_SECRET = 'mi_secret_delegacion_local_larga'
$env:DEBUG = '1'
$env:FLASK_DEBUG = '1'
$env:APP_ENV = 'development'
$env:JWT_DELEGATION_EXPIRATIONMINUTES = '5'
$env:DUMP_SECRETS = '1'
```

### 3. Poblar Base de Datos con Datos de Prueba

```powershell
# Resetear BD y crear usuarios de prueba (reserve_*)
python init_db_pruebas_test.py --reset
```

Esto crea usuarios de prueba:
- `admin_plataforma@academia.com` / `password_admin_plataforma`
- `admin_academia@academia.com` / `password_admin_academia`
- `user_academia_2_1@academia.com` / `password_user_academia_2_1`

### 4. Levantar la API

**Opción 1: Script recomendado**
```powershell
.\scripts\run_api_with_cleanup.ps1 -JwtSecret 'mi_secret_app_local_larga' -DelegationSecret 'mi_secret_delegacion_local_larga'
```

**Opción 2: Manual (con logs visibles)**
```powershell
# Asegurar que virtualenv está activo
if (Test-Path '.venv\Scripts\Activate.ps1') { . '.venv\Scripts\Activate.ps1' }

# Levantar API
python -u main.py
```

La API estará disponible en: **http://localhost:5000**

### 5. Acceder a Swagger UI

Abre en tu navegador: **http://localhost:5000/docs**

Desde Swagger puedes:
- Ver todos los endpoints disponibles
- Probar la API interactivamente
- Autenticarte con usuarios de prueba
- Ver schemas de request/response

## 🧪 Ejecutar Tests

```powershell
# Asegurar entorno configurado
$env:DB_ENV = 'developmentAWS'

# Ejecutar todos los tests
python -m pytest -q -s

# Ejecutar tests específicos
python -m pytest tests/usuarios/test_login.py -q -s
python -m pytest tests/academias/test_academias_get_patch.py -q -s

# Guardar logs de tests
New-Item -Path .\logs -ItemType Directory -Force
pytest -q tests/usuarios/test_login.py -s 2>&1 | Tee-Object -FilePath .\logs\api_tests.log
```

## 📚 Documentación Adicional

### Documentación en GitHub Pages

- 📖 **[Memoria Completa del TFG](https://afvafbsfb.github.io/api-workers-profesores/MEMORIA_TFG_SISTEMA_CHAT_ACADEMIAS.html)** - Documentación técnica completa del sistema
- 🔗 **[API REST (Swagger Standalone)](https://afvafbsfb.github.io/api-workers-profesores/API_SWAGGER_STANDALONE_TFG.html)** - Documentación interactiva online
- 📄 **[Especificación OpenAPI (JSON)](https://afvafbsfb.github.io/api-workers-profesores/served-openapi.json)** - Archivo consumido por Backend Chat + OpenAI GPT-4
- 🤖 **[Ingeniería de Prompts LLM](https://afvafbsfb.github.io/api-workers-profesores/INGENIERIA_PROMPTS_Y_OPTIMIZACION_LLM.html)** - Análisis técnico del sistema de chat IA
- 🏗️ **[Arquitectura Android MVVM](https://afvafbsfb.github.io/api-workers-profesores/ARQUITECTURA_ACADEMIAAPP_ANDROID.html)** - Documentación del cliente móvil
- 🎨 **[Experiencia de Usuario (UX)](https://afvafbsfb.github.io/api-workers-profesores/UX_ACADEMIAAPP_ANDROID.html)** - Guía UX del cliente Android
- 🗄️ **[Diagrama EER Base de Datos](https://afvafbsfb.github.io/api-workers-profesores/Diagrama%20EER%20Academias.pdf)** - Modelo de datos completo

### Documentación Local

- **[Guía de Desarrollo](docs/DEVELOPMENT.md)** - Setup completo, debugging, best practices
- **[Sistema de Permisos](docs/PERMISSIONS.md)** - Autorización, roles, scoping
- **[Workflow OpenAPI](docs/OPENAPI_WORKFLOW.md)** - Generación de especificaciones para mediador
- **[Referencia de Scripts](docs/SCRIPTS.md)** - Todos los scripts disponibles y su uso
- **[Autenticación JWT](docs/AUTH.md)** - Login, logout, refresh tokens, claims
- **[Ejemplos de Uso](docs/API_USAGE.md)** - Ejemplos con PowerShell y curl

## 🏗️ Estructura del Proyecto

```
api-workers-profesores/
├── src/
│   ├── domain/
│   │   ├── models/          # Entidades del negocio (Academia, Alumno, Curso...)
│   │   └── repositories/    # Interfaces de acceso a datos
│   ├── application/
│   │   └── services/        # Lógica de negocio
│   ├── infrastructure/      # Implementación con SQLAlchemy + MySQL
│   └── shared/
│       └── application/
│           └── permissions.py  # Sistema de autorización
├── tests/                   # Tests con pytest
├── scripts/                 # Scripts de generación OpenAPI y validación
├── docs/                    # Documentación detallada
├── main.py                  # Punto de entrada de la aplicación
└── requirements.txt         # Dependencias Python
```

## 🔧 Comandos Útiles

### Regenerar Especificación OpenAPI

```powershell
# 1. Exportar permisos
python scripts/export_permissions.py

# 2. Generar spec desde código
python scripts/dump_openapi.py

# 3. Anotar parámetros
python scripts/annotate_openapi_params.py docs/openapi-auto.json

# 4. Fusionar permisos (genera served-openapi.json para mediador)
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json

# 5. Validar sincronización
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json

# 6. Validar spec para mediador
python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json
```

## 📊 Base de Datos

El proyecto usa **MySQL 8.0** con el esquema definido en `docs/create_database.sql`.

**Tablas principales:**
- `Academia` - Entidades multi-tenancy
- `Usuario` - Usuarios con roles (Admin_plataforma, Admin_academia, Profesor_academia)
- `Alumno`, `Curso`, `Inscripcion` - Gestión académica
- `Sesion`, `HorarioCurso` - Clases y horarios
- `Extractos`, `Movimientos_Extracto` - Gestión financiera
- `RefreshToken`, `UserLoginLog` - Seguridad y auditoría

Ver esquema completo: [create_database.sql](docs/create_database.sql)

## 🔐 Seguridad

- **JWT Tokens:** Access tokens (15 min) + Refresh tokens (30 días)
- **Roles:** 3 niveles (Admin_plataforma, Admin_academia, Profesor_academia)
- **Scoping:** Aislamiento por academia (multi-tenancy)
- **Rotación de tokens:** Refresh tokens con rotación automática
- **Anti-fuerza bruta:** Bloqueo temporal tras intentos fallidos

## 🤝 Contribuir

Antes de hacer commit/push:

1. ✅ Ejecutar tests: `pytest -q -s`
2. ✅ Regenerar OpenAPI si cambiaste rutas/schemas
3. ✅ Validar permisos sincronizados
4. ✅ Revisar `/docs` en Swagger

Ver [CONTRIBUTING.md](docs/CONTRIBUTING.md) para más detalles.

## 📝 Notas

- No expongas `/docs` en producción sin control de acceso
- Usa cuentas `reserve_*` solo para testing
- El archivo `served-openapi.json` es consumido por el mediador (Backend Chat)
- Para desarrollo local, usa `DB_ENV=developmentAWS` (RDS development)

## 📞 Contacto y Soporte

**Autor:** Ángel Fernández Vidal  
**Proyecto:** Trabajo Final de Ciclo - FP Desarrollo de Aplicaciones Multiplataforma  
**Fecha:** Diciembre 2025  
**Email:** angel.fernandez@academia.es  
**GitHub:** [@afvafbsfb](https://github.com/afvafbsfb)

Para issues o consultas sobre la API, revisa la [documentación completa](https://afvafbsfb.github.io/api-workers-profesores/) o consulta los documentos técnicos en GitHub Pages.

## 🔗 Repositorios Relacionados

Este proyecto es parte de un ecosistema de 3 aplicaciones:

- 🐍 **API REST Python (este repo):** [api-workers-profesores](https://github.com/afvafbsfb/api-workers-profesores) - Backend principal con autenticación y datos
- ☕ **Backend Chat Java:** [backend-chat-openai-worker-profesores](https://github.com/afvafbsfb/backend-chat-openai-worker-profesores) - Mediador entre cliente y OpenAI GPT-4
- 📱 **Cliente Android (Kotlin):** [AcademiaAPP](https://github.com/afvafbsfb/AcademiaAPP) - App móvil con Jetpack Compose + MVVM

## 📄 Licencia

Este proyecto es parte de un Trabajo Final de Grado (TFG) y está disponible públicamente para fines educativos y de evaluación.
   
 