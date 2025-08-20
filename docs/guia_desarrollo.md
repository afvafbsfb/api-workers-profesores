# Documentación de endpoints (OpenAPI y Swagger UI)

- La especificación completa de la API REST está en el archivo `openapi-rest.yaml` (versión pública en S3: https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml).
- Para ver, probar y documentar los endpoints de forma interactiva, utiliza Swagger UI en `/docs` (antigua HTTP API) o accede a la nueva especificación OpenAPI REST para integraciones externas y el plugin de OpenAI:
  https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
- Si necesitas editar la especificación, puedes abrir `openapi-rest.yaml` en [Swagger Editor](https://editor.swagger.io/).
- Actualiza siempre `openapi-rest.yaml` cuando añadas o modifiques un endpoint.
  
**Integración con ChatGPT (plugin OpenAI):**
- Usa la URL pública del OpenAPI REST (https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml) al registrar el plugin en ChatGPT o cualquier herramienta compatible con OpenAPI 3.1.

# Guía de desarrollo y testing

## Ejecución de tests

- Todos los tests están en la carpeta `tests/`.
- Para ejecutar todos los tests:
  ```powershell
  pytest
  ```
- Para ver la cobertura de código:
  ```powershell
  pytest --cov=vlodeiro --cov-report=term-missing
  ```
- Los tests cubren endpoints, lógica de dominio y casos de error.

# CI/CD (pendiente de implementar)

Actualmente no hay un workflow de CI/CD automatizado en este proyecto.
Se recomienda crear un workflow de GitHub Actions en `.github/workflows/ci-cd.yml` que:
- Se ejecute automáticamente al hacer push o pull request en las ramas `staging` y `main`.
- Instale dependencias, ejecute tests y suba artefactos si es necesario.
- El despliegue en AWS Elastic Beanstalk sigue siendo manual por ahora.

# Añadir nuevos tests

- Crea un archivo en la carpeta `tests/` siguiendo el patrón `test_*.py`.
- Usa `pytest` y, si es necesario, fixtures para inicializar la base de datos o el cliente Flask.
- Ejemplo de test:

  ```python
  def test_nuevo_endpoint(client):
    res = client.get(
      "/vlodeiro/secretaria/alumnos",
      headers={"X-Api-Key": "devkey"}  # Usa la API Key de desarrollo configurada
    )
    assert res.status_code == 200
  ```

  # Versionado y recomendaciones

- El archivo `VERSION` contiene la versión actual del proyecto.
- Los cambios importantes deben reflejarse en `CHANGELOG.md`.
- Se recomienda mantener la cobertura de código por encima del 80%.
- Documenta los endpoints nuevos en `openapi-rest.yaml` y en la carpeta `docs/`.

  # Reglas de entorno Python

  - Todos los tests deben ejecutarse en la versión de Python definida como estándar del proyecto (actualmente Python 3.13.5).
  - Si se detecta ejecución en una versión incorrecta, se debe avisar y corregir el entorno antes de continuar.
  - Documenta cualquier cambio de versión en el changelog y en la documentación técnica.


