
# Infraestructura AWS del proyecto Workers API

## 1. Elastic Beanstalk
- Entorno: `Servicio-api-workers-env`
- URL: `http://servicio-api-workers-env.eba-m5yrjv7b.eu-west-3.elasticbeanstalk.com`
- Despliegue de la aplicación Flask (WSGI), configurado con variables de entorno para base de datos y claves.

## 2. API Gateway

### HTTP API (antigua)
- Nombre: `Workers API (proxy only)`
- URL base: `https://o5nztloqde.execute-api.eu-west-3.amazonaws.com`
- Ruta única: `/{proxy+}` con método `ANY`
- Integración HTTP con Elastic Beanstalk.

### REST API (actual)
- Nombre: `Workers API REST`
- URL base: `https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod`
- Especificación OpenAPI: [openapi-rest.yaml en S3](https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml)
- Métodos y rutas explícitas según openapi-rest.yaml.
- Protección por API Key y Usage Plan.

## 3. S3 (especificación OpenAPI)
- Bucket: `api-workers-plugins`
- Archivo: `openapi-rest.yaml`
- URL pública: https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- Permisos: lectura pública para integraciones externas (ChatGPT, Swagger UI, etc).

## 4. API Key y Usage Plan
- API Key: `chatgpt-secretaria-key` (ejemplo)
- Usage Plan: `secretaria-plan`
- Asociados a la REST API y stage `prod`.

## 5. Base de datos
- Aurora o RDS: instancia/cluster `api-workers-prod`
- Variables de entorno configuradas en Elastic Beanstalk para conexión.

## 6. Otros recursos y configuraciones
- Roles IAM para despliegue y acceso a recursos.
- Variables de entorno para claves, configuración de CORS y endpoints.
- Configuración de CORS en API Gateway para permitir acceso desde Swagger UI y herramientas externas.
- Documentación y especificación OpenAPI accesibles públicamente.

---

Esta infraestructura permite exponer la API de forma segura, documentada y compatible con integraciones externas como ChatGPT, Postman y Swagger UI.
