# Pruebas en local con MySQL y SQLite

Este documento explica cómo alternar entre el uso de MySQL y SQLite como base de datos en desarrollo para la API.

## Usar MySQL en desarrollo

1. Asegúrate de tener en el archivo `.env` las siguientes variables configuradas:

```
DB_DEV_HOST=localhost
DB_DEV_PORT=3307
DB_DEV_USER=angel
DB_DEV_PASS=Abanca0795
DB_DEV_NAME=api_workers
```

2. Inicia o reinicia la API. Se conectará automáticamente a MySQL usando estos datos.

3. Si necesitas cambiar usuario, contraseña o base de datos, edita el archivo `.env` y reinicia la API.

## Usar SQLite en desarrollo

1. Comenta o elimina (o deja vacías) las variables de MySQL en el archivo `.env`:

```
# DB_DEV_HOST=...
# DB_DEV_PORT=...
# DB_DEV_USER=...
# DB_DEV_PASS=...
# DB_DEV_NAME=...
```

2. Inicia o reinicia la API. Usará automáticamente SQLite (archivo local.db en la carpeta del proyecto).

## Notas
- No es necesario modificar el código fuente para alternar entre MySQL y SQLite.
- Solo cambia el archivo `.env` y reinicia la API.
- Si tienes problemas de conexión, revisa que los datos del `.env` sean correctos y que el servicio MySQL esté iniciado.


Para hacer las pruebas en desarrollo contra la base de datos MySQL de desarrollo, solo tienes que:

Asegurarte de que el archivo .env tiene estos valores (ajusta si cambiaste usuario o contraseña):
DB_DEV_HOST=localhost
DB_DEV_PORT=3307
DB_DEV_USER=angel
DB_DEV_PASS=Abanca0795
DB_DEV_NAME=api_workers

Verifica que el servicio MySQL está iniciado y accesible en el puerto 3307.

     Desde MySQL Workbench:

        Intenta conectarte con el usuario angel, puerto 3307, host localhost.
        Si la conexión es exitosa, el servicio está activo y accesible.

Inicia o reinicia tu API (por ejemplo, ejecutando el script o comando habitual para arrancarla).

        Si la API la ejecutas desde la terminal (por ejemplo, con un comando como python app.py), simplemente detén la ejecución (Ctrl+C en la terminal) y vuelve a lanzar el comando.

Realiza tus pruebas: la API usará automáticamente la base de datos MySQL de desarrollo.

        Invoke-WebRequest -Uri "http://localhost:5000/health" -Headers @{ "X-Api-Key" = "devkey-change-me" }

        (Invoke-WebRequest -Uri "http://localhost:5000/vlodeiro/secretaria/alumnos" -Headers @{ "X-Api-Key" = "devkey-change-me" }).Content

No necesitas tocar el código fuente, solo el archivo .env y reiniciar la API.