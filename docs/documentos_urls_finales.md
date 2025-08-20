# URLs finales de documentación y especificación de la API

## 1. Especificación OpenAPI (YAML)

- **URL  del api antigua HTTP API :**  
fichero origen openapi-http.yaml

https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/openapi.yml

** **URL  del api REST nueva :** 
fichero origen openapi-rest.yaml

--url del api rest de produccion: https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod

- **¿Qué es?**  
  Es el archivo de especificación OpenAPI de la API, en formato YAML. Describe de forma técnica y estructurada todos los endpoints, métodos, parámetros, respuestas y seguridad de la API. Es utilizado por herramientas como Swagger UI, Postman, y asistentes como ChatGPT para entender y consumir la API automáticamente. No es una documentación visual, sino la "descripción técnica" de la API.


## 2. Documentación interactiva Swagger UI

- **URL Swagger UI (HTTP API antigua):**  
  https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/docs

- **URL Swagger UI (API REST nueva, OpenAPI 3.1 en S3):**  
  https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml

- **¿Qué es?**  
  Es la documentación visual e interactiva de la API, generada automáticamente a partir del archivo OpenAPI correspondiente. Permite ver, probar y documentar todos los endpoints de la API desde el navegador, facilitando el desarrollo, testing y la integración con otros sistemas.

---

Ambas URLs deben estar siempre accesibles en producción para facilitar el uso y la integración de la API por parte de desarrolladores y herramientas externas.

--url del api rest de produccion: https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod
