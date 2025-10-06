# Ejecución de pruebas (orden)

Este documento contiene el flujo recomendado para crear la base de datos de pruebas, seedear los datos y ejecutar los tests en el orden solicitado. Ejecuta los comandos desde la raíz del repositorio `api-workers-profesores`.

Requisitos previos
- Tener MySQL accesible y la BBDD configurada (el script `create_database.sql` debe haberse ejecutado o la DB debe estar disponible).
- Activar el entorno virtual del proyecto (si existe `.venv`).
- Ajustar credenciales/puerto en `init_db_pruebas_test.py` si fuera necesario.

Orden de ejecución (PowerShell)

```powershell
# 1) Activar el entorno virtual
& .\.venv\Scripts\Activate.ps1

# 2) Fijar variable de entorno de DB usada por el seeder
$env:DB_ENV='developmentAWS'

# 3) Seed/reset de datos de prueba (borra filas y vuelve a insertar)
python .\init_db_pruebas_test.py --reset

# 4) Ejecutar tests uno a uno en el siguiente orden:
python -m pytest tests/academias/test_academias_post.py -q -s
python -m pytest tests/academias/test_academias_get_patch.py -q -s
python -m pytest tests/usuarios/test_login.py -q -s
python -m pytest tests/usuarios/test_unblock.py -q -s
python -m pytest tests/usuarios/test_refresh_logout.py -q -s
```

Notas
- Los comandos deben ejecutarse desde la raíz del proyecto (donde está `init_db_pruebas_test.py`).
- Si algún test falla por falta de datos o estado incorrecto, vuelve a lanzar `python .\init_db_pruebas_test.py --reset` y reintenta el test.
- Para ver salida de depuración/prints utiliza `-s` (ya incluido). Para más detalle, puedes ejecutar `pytest -k <nombre_test>` o usar los nodeids para ejecutar pruebas individuales.
- Si prefieres, puedo generar un script PowerShell que ejecute todo en secuencia y pare en el primer fallo; dímelo y lo añado.
