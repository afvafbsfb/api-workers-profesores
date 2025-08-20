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

# 1. Copia el archivo a la raíz temporalmente
cp docs/openapi-rest.yaml openapi-rest.yaml

# 2. Crea el ZIP con todo lo necesario (ejecuta esto en la raíz del proyecto)
zip -r deploy.zip main.py models.py auth.py requirements.txt openapi-rest.yaml Procfile vlodeiro wsgi.py passenger_wsgi.py

# 3. Elimina el archivo temporal de la raíz
rm openapi-rest.yaml

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
- **Swagger UI:** (puedes usar https://editor.swagger.io/ y cargar la URL del YAML)

## 6. Notas y buenas prácticas

- El despliegue es manual, no automatizado por CI/CD.
- Documenta cualquier cambio importante en CHANGELOG.md.
- Revisa y restringe CORS en producción.
- Haz backup de la base de datos antes de cambios críticos.
- Mantén las claves y contraseñas fuera del código fuente.

---

Este manual unifica los pasos y configuraciones clave para desplegar y mantener la API en AWS de forma segura y documentada.
