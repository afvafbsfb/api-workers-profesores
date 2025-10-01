# Documentación de la Base de Datos

## Archivo de Configuración: `config.py`
El archivo `config.py` contiene la configuración de la base de datos para diferentes entornos. Define los parámetros necesarios para conectarse a la base de datos y establece las variables de entorno dinámicamente.

### Configuración por Entorno
- **`development` (MySQL para desarrollo):**
  ```python
  'development': {
      'DB_HOST': 'dev-host',
      'DB_PORT': '3306',
      'DB_USER': 'dev_user',
      'DB_PASS': 'dev_pass',
      'DB_NAME': 'dev_db',
  }
  ```
- **`production` (MySQL para producción):**
  ```python
  'production': {
      'DB_HOST': 'prod-host',
      'DB_PORT': '3306',
      'DB_USER': 'prod_user',
      'DB_PASS': 'prod_pass',
      'DB_NAME': 'prod_db',
  }
  ```

### Cómo Configurar el Entorno
El entorno se define mediante la variable `DB_ENV`. Por defecto, está configurado como `development` (ver `config.py`). Para cambiarlo, puedes establecer la variable de entorno `DB_ENV` antes de ejecutar la aplicación:
```bash
export DB_ENV=development  # En Linux/Mac
set DB_ENV=development     # En Windows
```
> **Nota:** No es necesario establecer esta variable manualmente, ya que el archivo `config.py` se encarga de configurarla automáticamente según el entorno definido en el programa.

## Archivo `init_db_pruebas_test.py`
El archivo `init_db_pruebas_test.py` se utiliza para preparar datos de prueba mediante operaciones DML (INSERT/DELETE) y es idempotente por registro: puede ejecutarse varias veces sin duplicar datos.

IMPORTANTE: Este script NO modifica la estructura de la base de datos. No ejecuta db.create_all(), db.drop_all() ni ningún CREATE/DROP/ALTER. Su objetivo es garantizar que existan los registros necesarios para pruebas (roles, usuarios, curso, etc.).

Ejemplo de uso (no destructivo):

  python init_db_pruebas_test.py

El script comprueba la existencia de registros y sólo inserta los que falten (patrón get-or-create).

Si necesitas eliminar las filas de las tablas de datos de prueba y volver a insertar (operación destructiva a nivel de filas, nunca DDL), usa la opción `--delete`.

  python init_db_pruebas_test.py --delete

Por seguridad, `--delete` no se permite contra `production` a menos que añadas `--force` explícitamente:

  python init_db_pruebas_test.py --delete --force

Esto evita borrados accidentales en entornos productivos.

### Contenido del Archivo
El archivo contiene funciones para:
- Asegurar la existencia de registros principales (Academia, Curso, Usuario, Rol, etc.) usando get-or-create por registro.
- Borrar filas de las tablas de datos de prueba en orden controlado cuando se usa `--delete` (DELETE sobre filas, no DROP).
- Proveer mensajes en consola indicando si cada registro fue creado o ya existía.

### Uso del Script
Formas de ejecutar el script:
1. **Inicialización estándar (idempotente, no destructiva):**
  ```bash
  python init_db_pruebas_test.py
  ```
  Esto asegura que los registros necesarios para las pruebas existan; no modifica la estructura de la BD.

2. **Eliminar filas de datos de prueba y volver a insertar (destructivo a nivel de filas):**
  ```bash
  python init_db_pruebas_test.py --delete
  ```
  Advertencia: `--delete` elimina filas (DELETE) en un orden controlado para respetar claves foráneas. No borra ni recrea tablas. Para permitir `--delete` contra `production` es necesario añadir `--force`:
  ```bash
  python init_db_pruebas_test.py --delete --force
  ```
  **No uses `--force` en production salvo que estés absolutamente seguro.**

### Ejemplo de Salida
Al ejecutar el script verás mensajes indicativos, por ejemplo:
```
[init_db_pruebas_test] Usando configuración de base de datos: {...}
[init_db_pruebas_test] Academia creada con id=1
[init_db_pruebas_test] Tarifa creada con id=2
[init_db_pruebas_test] Usuario creado: activo@academia.com (id=5)
[init_db_pruebas_test] Usuario ya existe: bloqueado@academia.com
[init_db_pruebas_test] Init DB pruebas: datos de prueba asegurados (solo DML)
```

### ejecucion de los test apuntando a mysql_desarrollo:

1- Para levantar la API en el entorno local (opcional) y preparar el entorno, abre una nueva sesión de PowerShell y activa el virtualenv:

& "C:/Users/Angel FV/Desktop/FORMACION/api-workers-profesores/.venv/Scripts/Activate.ps1"

Si quieres iniciar la API (no es necesario para ejecutar los tests ya que pytest crea la app):

python app.py

2- Configurar el entorno de base de datos a `development` (MySQL de desarrollo). En PowerShell:

$env:DB_ENV = 'development'

Esto hace que `Config.set_environment_variables()` construya la URL de conexión para MySQL de desarrollo.

3- Preparar los datos de prueba con el script idempotente `init_db_pruebas_test.py` (ATENCIÓN: este script SOLO realiza operaciones DML — nunca crea ni borra tablas). Ejemplos:

python init_db_pruebas_test.py

# Si necesitas forzar un borrado ordenado de filas y volver a insertar los datos de prueba (destructivo):
python init_db_pruebas_test.py --delete

# Para permitir --delete en production se debe añadir --force explícitamente (NO recomendado salvo que sepas lo que haces):
python init_db_pruebas_test.py --delete --force

4- Ejecutar las pruebas específicas para `test_login.py` en otra sesión de PowerShell (usar -s para ver los prints):

python -m pytest tests/usuarios/test_login.py -q -s

O ejecutar la suite completa:

pytest -q

Notas importantes:
- `init_db_pruebas_test.py` garantiza los registros necesarios (usuarios, roles, curso, etc.) usando get-or-create por registro. No ejecuta DDL (CREATE/DROP/ALTER).
- Antes de crear la app en los tests se llama a `Config.set_environment_variables()` para asegurar que la app y los tests usan la misma URL de conexión MySQL.
- La variable `DB_ENV` admite los valores: `memory` (solo para entornos muy aislados), `development` (MySQL de desarrollo) y `production`.

