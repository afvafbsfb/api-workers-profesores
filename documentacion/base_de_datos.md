# Documentación de la Base de Datos

## Archivo de Configuración: `config.py`
El archivo `config.py` contiene la configuración de la base de datos para diferentes entornos. Define los parámetros necesarios para conectarse a la base de datos y establece las variables de entorno dinámicamente.

### Configuración por Entorno
- **`memory` (SQLite en memoria):**
  ```python
  'memory': {
      'DB_HOST': 'localhost',
      'DB_PORT': '3306',
      'DB_USER': 'root',
      'DB_PASS': '',
      'DB_NAME': 'memory_db',
  }
  ```
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
El entorno se define mediante la variable `DB_ENV`. Por defecto, está configurado como `memory`. Para cambiarlo, puedes establecer la variable de entorno `DB_ENV` antes de ejecutar la aplicación:
```bash
export DB_ENV=development  # En Linux/Mac
set DB_ENV=development     # En Windows
```
> **Nota:** No es necesario establecer esta variable manualmente, ya que el archivo `config.py` se encarga de configurarla automáticamente según el entorno definido en el programa.

## Archivo `init_db.py`
El archivo `init_db.py` se utiliza para inicializar la base de datos y poblarla con datos de prueba. Este script es idempotente, lo que significa que puede ejecutarse varias veces sin duplicar los datos.

El script utiliza db.create_all() para crear las tablas si no existen. Esto asegura que la estructura de la base de datos esté lista antes de insertar datos.

    python init_db.py 

El script verifica si las tablas están vacías antes de insertar datos.

Si ya hay datos en la tabla, no realiza ningún INSERT.

el script imprime mensajes en la consola para cada inserción realizada.

si no realiza un INSERT porque los datos ya existen, imprime un mensaje indicando que no se insertó ningún registro.

Solo elimina las tablas si se ejecuta con el argumento --reset. En ese caso, se ejecuta el método db.drop_all() para borrar todas las tablas antes de recrearlas.
    Ejemplo de uso con --reset:  python init_db.py --reset

### Contenido del Archivo
El archivo contiene funciones para:
- Crear tablas si no existen.
- Poblar datos iniciales para las tablas principales, como `Academia`, `Curso`, `Usuario`, etc.
- Comprobar si los registros ya existen antes de insertarlos.

### Uso del Script
Existen dos formas de ejecutar el script:
1. **Inicialización estándar:**
   ```bash
   python init_db.py
   ```
   Esto asegura que las tablas existan y que los datos iniciales se carguen si están vacíos.

2. **Reinicialización completa:**
   ```bash
   python init_db.py --reset
   ```
   Esto elimina todas las tablas y las recrea antes de cargar los datos iniciales. **Advertencia:** Este comando es destructivo y elimina todos los datos existentes.

### Ejemplo de Salida
Al ejecutar el script, verás mensajes como los siguientes:
```
[init_db] Academia creada con id=1
[init_db] Curso creado con id=1
[init_db] Usuarios creados: Activo, Bloqueado, Baja
[init_db] Reset completado: tablas recreadas y datos de prueba cargados
```

### ejecucion de los test apuntando a sqllite:

1- Para levantar la API en el entorno local, sigue estos pasos en una nueva sesión de PowerShell:
& "C:/Users/Angel FV/Desktop/FORMACION/api-workers-profesores/.venv/Scripts/Activate.ps1"

Ejecutar la aplicación:
python app.py

2- Asegurarnos de que DB_ENV esté configurado como memory en config.py  --> 
DB_ENV = os.getenv('DB_ENV', 'memory')  # Valores posibles: 'memory', 'development', 'production'

3- Ejecutar las pruebas específicas para test_login.py en otra sesion de powerShell:
pytest tests/usuarios/test_login.py

pytest tests/usuarios/test_login.py -s  --> ( Para que los prints se muestren por consola.)

