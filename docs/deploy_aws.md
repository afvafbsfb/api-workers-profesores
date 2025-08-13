# Despliegue manual en AWS Elastic Beanstalk

## Pasos recomendados

### 1. Preparar el paquete
- Verifica que todos los tests pasen y la cobertura sea suficiente.
- Empaqueta el proyecto en un archivo ZIP (incluye app.py, requirements.txt, openapi.yml, Procfile, y la carpeta vlodeiro/).

### 2. Subir archivos a Elastic Beanstalk
- Accede a la consola de AWS y entra en Elastic Beanstalk.
- Selecciona tu entorno y haz clic en "Cargar y desplegar".
- Sube el ZIP y espera a que el entorno se actualice.

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
- Prueba los endpoints principales desde Swagger UI o con herramientas como curl o Postman.
- Ejemplo:

```bash
curl -X GET "https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/vlodeiro/secretaria/alumnos/2" -H "X-Api-Key: <tu_api_key>"
```

## Notas
- El despliegue es manual, no automatizado por CI/CD.
- Documenta cualquier cambio importante en CHANGELOG.md.
- Para ejemplos y pruebas, consulta la documentación Swagger UI: https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/docs
