# Documentación de la Base de Datos

Este documento describe cómo recrear la base de datos (DDL), preparar datos de prueba (DML) y ejecutar las comprobaciones básicas en este proyecto.

## Archivos canónicos
- Esquema / DDL: `docs/create_database.sql` (fuente de verdad para el esquema SQL disponible en el repositorio).
- Seeder de datos de prueba (DML idempotente): `init_db_pruebas_test.py`.
- Configuración de entornos: `config.py` (construye la URL de conexión a partir de `DB_ENV`).

## Valores de entorno soportados por `Config`
La clase `Config` define varias configuraciones de base de datos. Los valores de `DB_ENV` que encontrarás en el repo son:
- `development` (MySQL local de desarrollo)
- `developmentAWS` (MySQL en AWS RDS, usado por defecto en algunos scripts de pruebas)
- `production`

Para ver/usar la configuración correcta asegúrate de exportar `DB_ENV` antes de ejecutar scripts o arrancar la app.

## Recrear la base de datos (procedimiento seguro, PowerShell)
Aviso: `docs/create_database.sql` incluye `DROP DATABASE IF EXISTS` — haz backup si tienes datos que conservar.

1) Hacer backup (mysqldump):

```powershell
mysqldump --no-tablespaces -u <usuario> -p -h <host> -P <puerto> api_workers > C:\temp\backup_api_workers.sql
```

2) Ejecutar el script que crea el esquema (DROP + CREATE + DDL):

```powershell
mysql -u <usuario> -p -h <host> -P <puerto> < .\docs\create_database.sql
```

3) Si aplicaste el SQL manualmente, marca Alembic como sincronizado para evitar re-aplicar migraciones:

```powershell
& .\.venv\Scripts\Activate.ps1
alembic stamp head
```

Alternativa: usar Alembic como fuente de verdad (recomendado si desarrollas migraciones):

```powershell
# Crear base de datos vacía manualmente si es necesario, luego:
& .\.venv\Scripts\Activate.ps1
alembic upgrade head
```

4) Poblar datos de prueba idempotentes (DML-only):

```powershell
& .\.venv\Scripts\Activate.ps1
python init_db_pruebas_test.py
```

- Para borrar filas de datos de prueba y volver a insertar (destructivo a nivel de filas, no DDL):

```powershell
python init_db_pruebas_test.py --delete
# o alias --reset (script soporta --reset como alias de --delete)
python init_db_pruebas_test.py --reset
```

Nota de seguridad: `--delete` contra `production` requiere `--force` explícito; no lo uses salvo que estés seguro.

## Cambios recientes importantes en el seeder
- `init_db_pruebas_test.py` es idempotente y crea usuarios/roles/curso/tarifa/academia si faltan.
- Se añadió una normalización final que resetea campos anti-brute-force en todos los usuarios: `failed_login_count=0`, `last_failed_login_at=NULL`, `locked_until=NULL`. Esto evita bloqueos residuales en entornos de pruebas.
- El script en algunos casos establece por defecto `DB_ENV='developmentAWS'` cuando se ejecuta (ver cabecera del script). Revisa el contenido si quieres apuntar a otro entorno.

## Comprobaciones rápidas (sin modificar nada)
- Comprobar existencia de tablas críticas:

```powershell
mysql -u <usuario> -p -h <host> -P <puerto> -e "SHOW TABLES FROM api_workers LIKE 'RefreshToken'; SHOW TABLES FROM api_workers LIKE 'UserLoginLog';"
```

- Comprobar columnas en `Usuario`:

```powershell
mysql -u <usuario> -p -h <host> -P <puerto> -e "SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema='api_workers' AND table_name='Usuario';"
```

- Ver la URL de conexión que usará la app/tests (tras llamar a `Config.set_environment_variables()`):

```powershell
& .\.venv\Scripts\Activate.ps1
python -c "from config import Config; Config.set_environment_variables(); import os; print('DATABASE_URL=', os.environ.get('DATABASE_URL'))"
```

## Ejecución de tests apuntando a MySQL (PowerShell)
1. Activar virtualenv:

```powershell
& .\.venv\Scripts\Activate.ps1
```

2. Establecer entorno de BD (ejemplo `development`):

```powershell
$env:DB_ENV = 'development'
```

3. Preparar datos de prueba (opcional: --reset para borrar filas y volver a poblar):

```powershell
python init_db_pruebas_test.py --reset
```

4. Ejecutar tests (con -s para ver prints en tests individuales):

```powershell
python -m pytest tests/usuarios/test_login.py -q -s
# o ejecutar toda la suite
pytest -q
```

## Notas operativas y buenas prácticas
- Nunca persistas refresh tokens en texto plano: el proyecto ya persiste sólo el hash (SHA-256) en la tabla `RefreshToken`.
- Usa HTTPS en todos los despliegues productivos y almacena refresh tokens preferiblemente en cookies HttpOnly+Secure.
- Si aplicas el SQL manualmente recuerda `alembic stamp head` para mantener el historial de migraciones sincronizado.
- Antes de ejecutar operaciones destructivas revisa `DB_ENV` y evita `--force` en `production`.

---

Si quieres, puedo generar automáticamente un diff entre `models.py` y `docs/create_database.sql` listando campos/relaciones que coinciden o difieren para que lo incorpores a esta documentación. ¿Lo genero ahora?

