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
zip -r deploy.zip main.py models.py auth.py requirements.txt openapi-rest.yaml Procfile vlodeiro wsgi.py passenger_wsgi.py; \
rm openapi-rest.yaml
```

Esto copiará el YAML, generará el ZIP y eliminará el archivo temporal automáticamente.

---

### Acceso directo a la documentación Swagger UI en producción

No necesitas usar https://editor.swagger.io ni pegar la URL manualmente. Una vez desplegada la API, accede directamente a la documentación interactiva en:

**https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs**

Desde ahí puedes probar todos los endpoints y ver la especificación OpenAPI cargada automáticamente.

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

## 5. URLs y Documentación

- **API REST Producción:** https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod
- **OpenAPI YAML:** https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
**Swagger UI:** https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/docs

## 6. Notas y buenas prácticas

- El despliegue es manual, no automatizado por CI/CD.
- Documenta cualquier cambio importante en CHANGELOG.md.
- Revisa y restringe CORS en producción.
- Haz backup de la base de datos antes de cambios críticos.
- Mantén las claves y contraseñas fuera del código fuente.

---


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
