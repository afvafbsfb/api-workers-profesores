# Reglas de oro para GitHub Copilot en este proyecto

**Versión actual de Python del proyecto: 3.13.5**

Copilot debe encargarse siempre de:

- Al inicio de cada sesión, revisar la consistencia entre el código fuente y la documentación técnica y funcional del proyecto.

- Cuando el usuario solicite ejecutar el CI/CD, actualizar la documentación funcional y técnica en la carpeta `docs/`.

- Actualizar el archivo `VERSION` siguiendo el versionado semántico (semver) para cada cambio relevante.

- Mantener el archivo `CHANGELOG.md` actualizado con cada nueva funcionalidad, corrección de errores o refactorización.

- Preparar el commit con un mensaje claro, descriptivo y relacionado con el cambio realizado.

- Realizar el commit y el push al repositorio remoto.

- No omitir nunca estos pasos, aunque el usuario no los recuerde explícitamente.

Copilot debe priorizar la calidad, el contexto técnico y operativo para ayudar en desarrollo, testing y despliegue.

Si Copilot detecta un cambio relevante (nueva funcionalidad, bugfix, refactor), debe aplicar automáticamente el versionado y actualizar el changelog.

Copilot nunca debe editar manualmente `VERSION` ni `CHANGELOG.md` si el usuario lo hace, sino sincronizar y corregir inconsistencias.

Copilot debe avisar al usuario si detecta que falta alguna actualización de versión o changelog.

Copilot debe asegurarse de que los tests y el entorno de desarrollo se ejecuten siempre en la versión de Python estándar definida para el proyecto (actualmente Python 3.x). Si detecta una versión incorrecta, debe avisar y corregir antes de continuar.
# Instrucciones para GitHub Copilot

## PowerShell: Uso correcto de headers en Invoke-WebRequest

Cuando realices pruebas funcionales o invocaciones HTTP desde PowerShell usando `Invoke-WebRequest` o `Invoke-RestMethod`, los headers deben pasarse como un diccionario y no como una cadena:

```powershell
Invoke-WebRequest -Uri "https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/health" -Headers @{ "X-Api-Key" = "<TU_API_KEY_AQUI>" }
```

No usar:

```powershell
Invoke-WebRequest -Uri "https://o5nztloqde.execute-api.eu-west-3.amazonaws.com/health" -Headers "X-Api-Key: <TU_API_KEY_AQUI>" # Error
```

Esto evita el error de conversión de tipo y garantiza que las pruebas funcionen correctamente en PowerShell.
