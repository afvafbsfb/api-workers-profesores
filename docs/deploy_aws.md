# Despliegue manual en AWS Elastic Beanstalk

## Pasos recomendados

### 1. Preparar el paquete
- Verifica que todos los tests pasen y la cobertura sea suficiente.
- Empaqueta todo el proyecto en un archivo ZIP (incluye: app.py, requirements.txt, openapi-rest.yaml, Procfile, y la carpeta vlodeiro/).

### 2. Subir archivos a Elastic Beanstalk
- Accede a la consola de AWS y entra en Elastic Beanstalk.
- Selecciona tu entorno y haz clic en "Cargar y desplegar".
- Sube el ZIP y espera a que el entorno se actualice.ç

para generar el zip a subir:
Opción 1: Usar Git Bash (recomendado)

Abre Git Bash y sutuarse en la carpeta de tu proyecto.

cd "/c/Users/Angel FV/Desktop/FORMACION/api-workers-profesores"

Ejecuta:
zip -r deploy.zip . -x '*.git*' '*.venv*' '*__pycache__*' '*.pytest_cache*' '*.vscode*' '*.env*' 'dist/*' 'instance/*' 'tmp/*' 'tests/*'

subir el .zip a Elastic Beanstalk




### 3. Configurar entorno Python
- Elastic Beanstalk detecta automáticamente requirements.txt y crea el entorno virtual.
- Si necesitas instalar dependencias adicionales, agrégalas a requirements.txt y vuelve a desplegar.

### 4. Configurar WSGI
- Asegúrate de que el archivo wsgi.py o passenger_wsgi.py esté presente y correctamente configurado.
- Elastic Beanstalk usará wsgi.py por defecto si está presente.

### 5. Restaurar base de datos
- Si usas SQLite, sube el archivo instance/local.db (no recomendado para producción).
- Si usas MySQL, asegúrate de que la base de datos esté accesible y configurada en las variables de entorno.

### 6. Verificar endpoints
- Prueba los endpoints principales del api rest desde Swagger UI o con herramientas como curl o Postman.
- Ejemplo:

```bash
curl -X GET "https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/vlodeiro/secretaria/alumnos/2" -H "X-Api-Key: <tu_api_key>"
```

## Notas
- El despliegue es manual, no automatizado por CI/CD.
- Documenta cualquier cambio importante en CHANGELOG.md.
- Para ejemplos y pruebas, consulta la documentación Swagger UI: https://api-workers-plugins.s3.eu-west-3.amazonaws.com/openapi-rest.yaml
