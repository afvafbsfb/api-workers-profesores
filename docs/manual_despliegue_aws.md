
# Manual de Despliegue y Configuración en AWS

## 1. Infraestructura AWS

- **Elastic Beanstalk**: Despliegue de la aplicación Flask (WSGI), configurado con variables de entorno para base de datos y claves.
- **API Gateway REST**: Expone la API de forma pública y segura, con protección por API Key y Usage Plan.
- **S3**: Almacena y publica la especificación OpenAPI (openapi-rest.yaml).
- **Base de datos**: Aurora/RDS para producción, MySQL local para desarrollo.
- **Roles IAM**: Para despliegue y acceso a recursos.

## 2. Despliegue en Elastic Beanstalk

1. Empaqueta el proyecto en un archivo ZIP (incluye app.py, requirements.txt, openapi-rest.yaml, Procfile, y la carpeta vlodeiro/).


Abre Git Bash en la raíz del proyecto.


### Automatización del empaquetado para despliegue

Puedes automatizar los tres pasos con este comando (ejecuta en la raíz del proyecto):

```sh
cp docs/openapi-rest.yaml openapi-rest.yaml; \
zip -r deploy.zip main.py models.py auth.py requirements.txt openapi-rest.yaml Procfile vlodeiro wsgi.py passenger_wsgi.py docs/index.html; \
rm openapi-rest.yaml
```

Esto copiará el YAML, generará el ZIP y eliminará el archivo temporal automáticamente.

---


### Acceso directo a la documentación Swagger UI en producción

No necesitas usar https://editor.swagger.io ni pegar la URL manualmente. Una vez desplegada la API, accede directamente a la documentación interactiva en:

**https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs**

Esta ruta, junto con `/openapi.yml`, es pública y no requiere API Key. Desde ahí puedes probar todos los endpoints y ver la especificación OpenAPI cargada automáticamente.

2. Accede a la consola de AWS > Elastic Beanstalk > tu entorno > "Cargar y desplegar".

3. Sube el ZIP y espera a que el entorno se actualice.

4. Elastic Beanstalk detecta requirements.txt y crea el entorno virtual automáticamente.

5. Asegúrate de que wsgi.py o passenger_wsgi.py están presentes y configurados.

6. Configura las variables de entorno para la base de datos y claves en el entorno de Beanstalk.


## 3. Configuración de API Gateway y CORS

- **Access-Control-Allow-Origin:** `*` (en producción, restringir a dominios autorizados)
- **Access-Control-Allow-Headers:** `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
- **Access-Control-Allow-Methods:** `GET,POST,OPTIONS`
- **Access-Control-Max-Age:** `3600`
- **Access-Control-Allow-Credentials:** `NO`

> Swagger UI y herramientas externas funcionarán correctamente con esta configuración. En producción, sustituye `*` por el dominio autorizado.

### Despliegue y configuración de CORS en API Gateway

1. En el recurso `/{proxy+}` de tu API Gateway, crea el método OPTIONS si no existe.
2. Selecciona "Simulación" (Mock) como tipo de integración para OPTIONS.
3. En la respuesta de integración de OPTIONS, añade los siguientes encabezados (en Header mappings):
	- Access-Control-Allow-Origin: '*' (con comillas simples)
	- Access-Control-Allow-Headers: 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token' (con comillas simples)
	- Access-Control-Allow-Methods: 'GET,POST,OPTIONS' (con comillas simples)
	> **Nota:** Si pones los valores sin comillas, la consola puede dar error de "Invalid mapping expression". Usa siempre comillas simples.
4. En el método ANY, asegúrate de tener el parámetro de ruta:
	- proxy → method.request.path.proxy
5. Guarda los cambios y haz "Deploy API" en la etapa `prod`.
6. Prueba desde Swagger UI o tu frontend. Si tienes Flask-CORS activo, el resto de headers los añade Flask automáticamente.

**Ejemplo de descripción para el despliegue:**
> Habilita CORS en API Gateway para integración con Swagger UI y frontends. Añadidos encabezados CORS en OPTIONS con comillas simples para evitar errores de mapeo. Confirmado mapeo de path parameter {proxy}. Listo para pruebas desde Swagger UI y clientes web.

---
## 4. Variables de entorno recomendadas

- `APP_ENV=production`
- `DB_PROD_HOST=...`
- `DB_PROD_PORT=...`
- `DB_PROD_USER=...`
- `DB_PROD_PASS=...`
- `DB_PROD_NAME=...`
- `API_KEY_PROD=...`

Configura estas variables en Elastic Beanstalk para conectar con la base de datos de producción y proteger la API.


### Configuración de CORS en S3 para servir openapi-rest.yaml a Swagger UI

Para que Swagger UI pueda cargar la especificación OpenAPI desde S3 sin errores de CORS, configura la política CORS del bucket de la siguiente manera:

1. Ve a la consola de AWS S3 y selecciona el bucket donde está `openapi-rest.yaml`.
2. Haz clic en la pestaña "Permisos" y busca la sección "Configuración de CORS".
3. Añade la siguiente política:

[
    {
        "AllowedHeaders": [
            "*"
        ],
        "AllowedMethods": [
            "GET"
        ],
        "AllowedOrigins": [
            "*"
        ],
        "ExposeHeaders": []
    }
]


4. Guarda los cambios.
5. Asegúrate de que el archivo `openapi-rest.yaml` es público o tiene permisos de lectura pública.

Con esto, Swagger UI podrá cargar la especificación OpenAPI desde cualquier origen, tanto en desarrollo como en producción.


## 5. URLs y Documentación

- **API REST Producción (API Gateway):** https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod

- **OpenAPI YAML:** https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml

**Swagger UI (API Gateway):** https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs

> Para exponer correctamente la documentación Swagger UI a través de API Gateway, asegúrate de:

(ver en los recursos del api gateway todas sus pestañas y como quedan parametrizadas)

> - Crear el recurso `/docs` explícitamente en API Gateway (no como proxy).
> - Añadir el método GET con integración HTTP (NO proxy) apuntando a la URL interna de Beanstalk `/docs`.
> - Marcar la opción de CORS al crear el recurso para permitir peticiones desde cualquier origen.
> - En la configuración de “Respuesta de método” y “Respuesta de integración” para el código 200, añadir el encabezado `Content-Type` para que API Gateway reenvíe correctamente el tipo de contenido HTML.
> - No usar plantillas de mapeo ni parámetros extra.
> - Desplegar la API tras cada cambio.

Si ves un error 500 en la URL de API Gateway, revisa la integración, los encabezados y la configuración de CORS como se describe arriba. Una vez todo esté correcto, la URL pública mostrará Swagger UI sin requerir autenticación ni API Key.

**Nota:** Si ves un error 500 en la URL de API Gateway, revisa la integración, los encabezados y la configuración de CORS como se describe arriba.

### URLs internas del backend (Elastic Beanstalk)

- **Endpoint GET /docs (para integración en API Gateway):** http://servicio-api-workers-env.eba-m5yrjv7b.eu-west-3.elasticbeanstalk.com/docs 
               
          esta url ahora si que me la carga bien el swagger: http://servicio-api-workers-env.eba-m5yrjv7b.eu-west-3.elasticbeanstalk.com/docs     
          ¡Perfecto! El hecho de que la URL interna de Beanstalk ya muestre correctamente Swagger UI confirma que el backend y la configuración de S3/CORS están bien.

## 6. Notas y buenas prácticas

- El despliegue es manual, no automatizado por CI/CD.
- Documenta cualquier cambio importante en CHANGELOG.md.
- Revisa y restringe CORS en producción.
- Haz backup de la base de datos antes de cambios críticos.
- Mantén las claves y contraseñas fuera del código fuente.

---

### Hacer público el endpoint /docs en API Gateway (sin API Key)

Para que la documentación Swagger UI (/docs) sea accesible públicamente sin necesidad de API Key, asegúrate de que la configuración del método GET del recurso /docs en API Gateway sea la siguiente:

1. Ve a la consola de AWS API Gateway.
2. Selecciona tu API y entra en el panel de recursos.
3. Haz clic en el recurso `/docs` y selecciona el método `GET`.
4. En la sección "Configuración de solicitud de método", verifica que:
	- **Autorización:** Ninguna
	- **Validador de solicitudes:** Ninguna
	- **Clave de API obligatoria:** NO
	- **Nombre de la operación:** (vacío)
5. Si es necesario, cambia la opción "Clave de API obligatoria" a NO.
6. Guarda los cambios y vuelve a desplegar la API en el stage correspondiente.

Con esto, cualquier usuario podrá acceder a la documentación en `/docs` sin necesidad de autenticación ni API Key.


## 7. Depuración de errores en producción (logging y debug)

Si tienes un error 500 y no ves el detalle en los logs estándar, sigue estos pasos para obtener el traceback real del backend:

### Logging de errores en Flask

Ya está configurado en `main.py`. Los errores se guardan en `tmp/flask_error.log` cada vez que ocurre un error 500.


### Acceso SSH y consulta del log de errores

Para conectarte por SSH a la instancia EC2 y ver el log de errores:

1. Asegúrate de tener el archivo `.pem` de tu clave privada (por ejemplo, `eb-angel-2025.pem`).
2. Ejecuta en tu terminal (ajusta la ruta si es necesario):

	```sh
	ssh -i "C:/Users/Angel FV/Downloads/eb-angel-2025.pem" ec2-user@51.44.98.213
	```

3. Una vez conectado, navega al directorio de la app y muestra el log:

	```sh
	cd /var/app/current
	cat tmp/flask_error.log
	```

	Para ver solo las últimas líneas del log:

	```sh
	tail -n 50 tmp/flask_error.log
	```

4. Copia el contenido relevante del log para analizar el error.


1. Busca en `main.py` el bloque:
	```python
	# Para activar el modo debug, descomenta la siguiente línea:
	app.debug = True
	```
2. Descomenta la línea `app.debug = True` para activar el modo debug.
3. Sube y despliega el código.
4. Reproduce el error y revisa el archivo `tmp/flask_error.log` para ver el traceback real.
5. Cuando termines, **vuelve a comentar** la línea `app.debug = True` antes de volver a producción.

> El logging de errores puede dejarse activo, ya que solo guarda errores (no información sensible si tu código no la imprime en los logs).

---

Este manual unifica los pasos y configuraciones clave para desplegar y mantener la API en AWS de forma segura y documentada.

## 8. Publicar la API en API Gateway y verificar acceso público

Una vez configurados los recursos y métodos en API Gateway, sigue estos pasos para publicar los cambios y comprobar que el endpoint /docs es accesible públicamente:

### Publicar (Deploy) la API
1. En la consola de AWS API Gateway, selecciona tu API.
2. Haz clic en "Acciones" > "Implementar API" (Deploy API).
3. Selecciona el stage correspondiente (por ejemplo, `prod`).
4. Confirma la publicación.

### Verificar acceso público a /docs
1. Abre un navegador y accede a la URL pública de Swagger UI, por ejemplo:
	- https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs
2. Deberías ver la interfaz Swagger UI sin que se solicite API Key.
3. Alternativamente, puedes comprobar con curl:
	```sh
	curl -i https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs
	```
	La respuesta debe ser 200 OK y mostrar el HTML de Swagger UI.

Si ves un error 403 o se solicita API Key, revisa la configuración del método GET de /docs y vuelve a desplegar la API.

---