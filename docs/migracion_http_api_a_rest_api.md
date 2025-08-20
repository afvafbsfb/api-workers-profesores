## Referencias rápidas

- **URL API REST (producción):**
  https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod
- **OpenAPI REST (YAML en S3):**
  https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- **Swagger UI (documentación visual, usando OpenAPI REST):**
  https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml

# Migración de HTTP API a REST API en AWS API Gateway

Este documento describe los pasos para migrar la API actual de tipo **HTTP API** a una **REST API** en AWS API Gateway, con soporte para **API Keys** y **Usage Plans**.

---

## 1. Exportar la definición OpenAPI actual

* En la consola de AWS API Gateway, selecciona tu **HTTP API**.
* Usa la opción **Export API** para obtener el fichero OpenAPI (YAML o JSON).
* Guarda este archivo en tu proyecto (ejemplo: `openapi-http.yaml`).
** finalmente el export lo encontre en : 
Gateway de API
API
Workers API (proxy only) (o5nztloqde)
develop
Exportr

---

## 2. Adaptar el OpenAPI para REST API

En VSCode con GitHub Copilot puedes modificar el fichero exportado:

* Cambia la sección `servers`:

  ```yaml
  servers:
    - url: https://<api-id>.execute-api.<region>.amazonaws.com/prod
  ```

* Asegúrate de definir la seguridad con `apiKey`:

  ```yaml
  components:
    securitySchemes:
      api_key:
        type: apiKey
        in: header
        name: X-Api-Key
  security:
    - api_key: []
  ```

* Ajusta rutas y métodos según tu API actual (por ejemplo `/vlodeiro/secretaria/alumnos`).

* Guarda el archivo modificado como `openapi-rest.yaml`.


*Listo. He creado openapi-rest.yaml con la configuración adaptada para REST API: incluye el endpoint de servers para REST, la seguridad con API Key y mantiene el resto de la estructura.

*Ahora puedes importar este archivo en AWS API Gateway como REST API. 
---

*aquí tienes los pasos para importar y desplegar la nueva REST API en AWS API Gateway usando el archivo docs/openapi-rest.yaml:

## 3. Crear la nueva REST API en AWS

* Entra en **API Gateway → Create API → Import**.
* Selecciona **REST API** y sube tu `openapi-rest.yaml`.
* Una vez creada, ve a **Actions → Deploy API** y crea un stage (ejemplo: `prod`).

---

## 4. Configurar API Key y Usage Plan

* Si aún no lo tienes:

  * Crea una API Key (ejemplo: `chatgpt-secretaria-key`).
  * Crea un Usage Plan (ejemplo: `secretaria-plan`).
* En el Usage Plan, asocia:

  * Tu nueva **REST API**.
  * El stage `prod`.
* Añade la API Key al Usage Plan.

---

## 5. Actualizar el plugin de ChatGPT secretaria

* Cambia el `servers` en el OpenAPI del plugin para apuntar a tu nueva REST API:

  ```yaml
  servers:
    - url: https://<api-id>.execute-api.<region>.amazonaws.com/prod
  ```
* Asegúrate de que el plugin envíe la cabecera `X-Api-Key` con el valor de tu `chatgpt-secretaria-key`.

* archivo openapi-rest.yaml ahora apunta a tu nueva REST API en producción con la URL https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod.

* tu plugin de ChatGPT secretaria ya puede usar esta URL como servidor. 
---

Opciones para alojar el openapi-rest.yaml y obtener su URL pública

¿subir el archivo a S3 y obtener la URL, o prefieres servirlo desde tu backend/API Gateway?

Ambas opciones son válidas y seguras, pero cada una tiene ventajas según el caso de uso:

Subirlo a S3 (recomendado para la mayoría de APIs públicas)
Fácil de gestionar, versionar y actualizar.
AWS S3 es muy estable y rápido para servir archivos estáticos.
Puedes controlar permisos fácilmente (público o restringido).
La URL es directa y siempre disponible, incluso si tu backend/API está caído.
Ideal si no quieres consumir recursos de tu API Gateway solo para servir un archivo.

Servirlo desde tu backend/API Gateway
El archivo siempre está sincronizado con tu despliegue (útil si generas el OpenAPI dinámicamente).
Puedes proteger el endpoint si lo necesitas (por ejemplo, solo accesible para ciertos usuarios).
Útil si quieres que la URL esté bajo el mismo dominio que el resto de tu API.

Recomendación práctica

Si tu OpenAPI es estático y no cambia en cada despliegue, S3 es la opción más sencilla, robusta y económica.

Si quieres máxima integración y control desde tu backend, o el OpenAPI se genera dinámicamente, sirve el archivo desde tu API Gateway.

¿Quieres que te guíe paso a paso para subirlo a S3 y obtener la URL pública?

lo subimos a s3: creamos el bucked s3 llamado api-workers-plugins  y subimos el fichero openapi-rest.yaml, lo hacemos publico.
obtenemos la url publica que es: 

https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml

Verifica la URL pública
Selecciona el archivo y copia la URL pública que te muestra AWS (será algo como:
https://<bucket>.s3.<region>.amazonaws.com/openapi-rest.yaml)
Abre esa URL en una ventana de incógnito para comprobar que se descarga o muestra el YAML sin pedir login.




## 6. Probar la integración

* Lanza una llamada desde Swagger UI usando la URL pública de OpenAPI REST (S3) y la API Key → debe funcionar.
* Lanza la misma acción (`getAlumnos`, etc.) desde ChatGPT secretaria → debe devolver los datos reales.

> **Nota:** Tanto Swagger UI como ChatGPT deben usar la especificación OpenAPI REST alojada en S3 para máxima compatibilidad y documentación actualizada.

---

## Notas finales

* **HTTP API** es más barato y rápido, pero no soporta API Keys ni Usage Plans.
* **REST API** es más caro, pero soporta autenticación con claves, cuotas y throttling.
* Mantén actualizado tu fichero `openapi-rest.yaml` en tu repo para versionar cambios.
