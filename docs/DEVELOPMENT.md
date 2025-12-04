# Guía de Desarrollo - API Workers Profesores

Documentación completa para desarrolladores trabajando en la API Workers.

## 📑 Tabla de Contenidos

- [Setup Completo del Entorno](#setup-completo-del-entorno)
- [Configuración de Base de Datos](#configuración-de-base-de-datos)
- [Seeder y Datos de Prueba](#seeder-y-datos-de-prueba)
- [Variables de Entorno](#variables-de-entorno)
- [Debugging](#debugging)
- [Testing Avanzado](#testing-avanzado)
- [Buenas Prácticas](#buenas-prácticas)

## Setup Completo del Entorno

### Prerrequisitos

- Python 3.11+
- MySQL 8.0 (local o AWS RDS)
- PowerShell 5.1+ (Windows) o bash (Linux/Mac)
- Git

### Instalación Paso a Paso

```powershell
# 1. Clonar repositorio
git clone https://github.com/afvafbsfb/api-workers-profesores.git
cd api-workers-profesores

# 2. Crear virtualenv
python -m venv .venv

# 3. Activar virtualenv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# source .venv/bin/activate    # Linux/Mac

# 4. Actualizar pip
python -m pip install --upgrade pip

# 5. Instalar dependencias
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

# 6. Verificar instalación
python -c "import flask, sqlalchemy, marshmallow; print('Dependencies OK')"
```

## Configuración de Base de Datos

### Opción 1: AWS RDS (Recomendado para desarrollo)

```powershell
# Configurar para usar RDS development
$env:DB_ENV = 'developmentAWS'
```

Las credenciales RDS están configuradas en `config.py` según `DB_ENV`.

### Opción 2: MySQL Local

```powershell
# 1. Crear base de datos
mysql -u root -p < docs/create_database.sql

# 2. Configurar DATABASE_URL
$env:DATABASE_URL = 'mysql+pymysql://usuario:password@localhost:3306/api_workers'
```

### Verificar Conexión

```powershell
python -c "from src.infrastructure.database import db; print('DB Connection OK')"
```

## Seeder y Datos de Prueba

El script `init_db_pruebas_test.py` crea datos de prueba reproducibles.

### Ejecutar Seeder

```powershell
# Resetear BD completamente y poblar
python init_db_pruebas_test.py --reset
```

### Usuarios Creados

El seeder crea usuarios con prefijo `reserve_` para testing:

| Email | Password | Rol | Academia ID |
|-------|----------|-----|-------------|
| `admin_plataforma@academia.com` | `password_admin_plataforma` | Admin_plataforma | NULL |
| `admin_academia@academia.com` | `password_admin_academia` | Admin_academia | 1 |
| `user_academia_2_1@academia.com` | `password_user_academia_2_1` | Profesor_academia | 2 |

**⚠️ IMPORTANTE:** Estos usuarios solo deben usarse en tests, nunca en producción.

## Variables de Entorno

### Variables Esenciales

```powershell
# Base de datos
$env:DB_ENV = 'developmentAWS'  # o 'local' para MySQL local
$env:DATABASE_URL = 'mysql+pymysql://...'  # solo si DB_ENV != developmentAWS

# JWT
$env:JWT_SECRET_KEY = 'mi_secret_app_local_larga'  # min 32 caracteres
$env:JWT_DELEGATION_SECRET = 'mi_secret_delegacion_local_larga'
$env:JWT_DELEGATION_EXPIRATIONMINUTES = '5'

# Debug
$env:DEBUG = '1'
$env:FLASK_DEBUG = '1'
$env:APP_ENV = 'development'
$env:DUMP_SECRETS = '1'  # muestra secrets al inicio (solo dev)
```

### Variables Opcionales

```powershell
# Configuración de tokens
$env:JWT_ACCESS_TOKEN_EXPIRES = '15'  # minutos (default: 15)
$env:JWT_REFRESH_TOKEN_EXPIRES = '43200'  # minutos (default: 30 días)

# OpenAPI
$env:OPENAPI_MOCK = 'false'  # true para mockear OpenAI en backend-chat

# Logging
$env:LOG_LEVEL = 'DEBUG'  # DEBUG, INFO, WARNING, ERROR
```

## Debugging

### Levantar con Logs Detallados

```powershell
# Activar virtualenv
.\.venv\Scripts\Activate.ps1

# Configurar debug
$env:DEBUG = '1'
$env:FLASK_DEBUG = '1'

# Ejecutar con output unbuffered
python -u main.py
```

### Usar Debugger de VS Code

Crear `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Flask",
      "type": "python",
      "request": "launch",
      "module": "flask",
      "env": {
        "FLASK_APP": "main.py",
        "FLASK_DEBUG": "1",
        "DB_ENV": "developmentAWS",
        "JWT_SECRET_KEY": "mi_secret_app_local_larga",
        "JWT_DELEGATION_SECRET": "mi_secret_delegacion_local_larga"
      },
      "args": ["run", "--port", "5000"],
      "jinja": true,
      "justMyCode": false
    }
  ]
}
```

### Inspeccionar BD Durante Desarrollo

```powershell
# Conectar a MySQL (local)
mysql -u root -p api_workers

# Queries útiles
SELECT * FROM Usuario WHERE email LIKE 'reserve_%';
SELECT * FROM RefreshToken WHERE revoked_at IS NULL;
SELECT * FROM UserLoginLog ORDER BY login_at DESC LIMIT 10;
```

## Testing Avanzado

### Estructura de Tests

```
tests/
├── academias/
│   ├── test_altas_bajas_academias.py
│   ├── test_busquedas_academias.py
│   └── test_academias_get_patch.py
├── usuarios/
│   ├── test_login.py
│   ├── test_jwt_claims.py
│   ├── test_refresh_logout.py
│   └── test_unblock.py
└── test_openapi_requestbody.py
```

### Ejecutar Tests con Coverage

```powershell
# Instalar coverage
pip install pytest-cov

# Ejecutar con coverage
pytest --cov=src --cov-report=html --cov-report=term

# Ver reporte HTML
start htmlcov/index.html  # Windows
# open htmlcov/index.html  # Mac
```

### Tests Parametrizados

```python
import pytest

@pytest.mark.parametrize("email,expected_role", [
    ("admin_plataforma@academia.com", "Admin_plataforma"),
    ("admin_academia@academia.com", "Admin_academia"),
    ("user_academia_2_1@academia.com", "Profesor_academia"),
])
def test_user_roles(client, email, expected_role):
    # Login
    resp = client.post('/auth/login', json={
        'email': email,
        'password': f'password_{email.split("@")[0]}'
    })
    assert resp.status_code == 200
    
    # Verificar rol en claims
    claims = decode_jwt(resp.json['tokens']['access_token'])
    assert expected_role in claims['roles']
```

### Ejecutar Suite Completa (Orden CI)

```powershell
# A. Tests de Academias
pytest tests/academias/test_altas_bajas_academias.py -q -s
pytest tests/academias/test_busquedas_academias.py -q -s
pytest tests/academias/test_academias_post.py -q -s
pytest tests/academias/test_academias_get_patch.py -q -s

# B. Tests de Usuarios
pytest tests/usuarios/test_altas_bajas_usuarios.py -q -s
pytest tests/usuarios/test_busquedas_usuarios.py -q -s
pytest tests/usuarios/test_login.py -q -s
pytest tests/usuarios/test_jwt_claims.py -q -s
pytest tests/usuarios/test_unblock.py -q -s
pytest tests/usuarios/test_refresh_logout.py -q -s

# C. Validación OpenAPI
pytest tests/test_openapi_requestbody.py -q -s
```

## Buenas Prácticas

### Commits

```bash
# Formato recomendado
git commit -m "feat(usuarios): add display_name to JWT claims"
git commit -m "fix(auth): resolve logout with refresh token in body"
git commit -m "docs(readme): update quick start guide"

# Prefijos: feat, fix, docs, test, refactor, chore
```

### Antes de Hacer Push

```powershell
# 1. Ejecutar tests
pytest -q -s

# 2. Regenerar OpenAPI si cambiaste rutas
python scripts/dump_openapi.py
python scripts/merge_permissions_into_openapi.py --spec docs/openapi-auto.json --out docs/served-openapi.json

# 3. Validar permisos
python scripts/validate_permissions_sync.py --map scripts/permissions_map.json --code src/shared/application/permissions.py --spec docs/openapi-auto.json

# 4. Validar spec para mediador
python scripts/validate_served_openapi_for_mediator.py --spec docs/served-openapi.json
```

### Añadir Nuevo Endpoint

Ver [Checklist de Nuevos Endpoints](#) en CONTRIBUTING.md

1. Crear route function con `operationId`
2. Añadir función `can_*` en `permissions.py`
3. Mapear en `permissions_map.json`
4. Crear tests
5. Regenerar y validar OpenAPI

### Code Style

```powershell
# Instalar black y flake8
pip install black flake8

# Formatear código
black src/ tests/

# Linting
flake8 src/ tests/ --max-line-length=120
```

## Troubleshooting Común

### Error: "Cannot import app"

```powershell
# Verificar que estás en la raíz del proyecto
pwd  # debe mostrar .../api-workers-profesores

# Verificar virtualenv activo
python -c "import sys; print(sys.prefix)"  # debe apuntar a .venv
```

### Error: "Table doesn't exist"

```powershell
# Ejecutar seeder para crear tablas
python init_db_pruebas_test.py --reset
```

### Swagger UI muestra "No API definition provided"

```powershell
# 1. Verificar que /openapi.json responde
Invoke-RestMethod -Uri 'http://localhost:5000/openapi.json' | ConvertTo-Json

# 2. Limpiar caché del navegador
# 3. Regenerar spec
python scripts/dump_openapi.py
```

### Tests fallan con "JWT expired"

Los tests usan tokens generados dinámicamente. Si fallan por expiración, verifica:

```powershell
# Asegurar que JWT_DELEGATION_EXPIRATIONMINUTES es suficiente
$env:JWT_DELEGATION_EXPIRATIONMINUTES = '5'
```

## Recursos Adicionales

- [Sistema de Permisos](PERMISSIONS.md)
- [Workflow OpenAPI](OPENAPI_WORKFLOW.md)
- [Autenticación JWT](AUTH.md)
- [Referencia de Scripts](SCRIPTS.md)
