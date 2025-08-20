# Configuración de CORS en API Gateway

CORS (Cross-Origin Resource Sharing) permite que navegadores carguen recursos de diferentes dominios. Si se configura en API Gateway, las cabeceras CORS de tu backend son ignoradas y se aplican las de la configuración de API Gateway.

## Recomendaciones de configuración para Swagger UI y pruebas

* **Access-Control-Allow-Origin:** `*`
  Permite llamadas desde cualquier origen. Para producción es recomendable restringirlo a dominios específicos, por ejemplo: `https://editor.swagger.io`, `https://miacademia.com`.

* **Access-Control-Allow-Headers:**

  ```
  Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token
  ```

  Permite al navegador enviar cabeceras necesarias para autenticar y usar la API.

* **Access-Control-Allow-Methods:**

  ```
  GET,POST,OPTIONS
  ```

  Incluye los métodos usados en la API y el método `OPTIONS` requerido para preflight CORS.

* **Access-Control-Expose-Headers:** *(vacío)*
  Solo necesario si se requieren cabeceras personalizadas en la respuesta.

* **Access-Control-Max-Age:** `3600`
  El navegador puede cachear la respuesta preflight durante 1 hora.

* **Access-Control-Allow-Credentials:** `NO`
  Mantener en NO salvo que la API necesite cookies o sesiones.

## Ejemplo de configuración final (para pruebas con Swagger UI)

* Access-Control-Allow-Origin: `*`
* Access-Control-Allow-Headers: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
* Access-Control-Allow-Methods: `GET,POST,OPTIONS`
* Access-Control-Expose-Headers: *(vacío)*
* Access-Control-Max-Age: `3600`
* Access-Control-Allow-Credentials: `NO`

## Notas

* Con esta configuración Swagger UI debería dejar de mostrar el error **"Failed to fetch"**.
* En producción se recomienda sustituir `*` en **Allow-Origin** por el dominio autorizado.
