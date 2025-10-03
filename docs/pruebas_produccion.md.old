# Pruebas de Producción

A continuación se muestra un ejemplo de cómo probar el endpoint `/health` en producción usando `curl` y la API Key:

```bash
curl -H "X-Api-Key: zbiBJTkhSA6UVt1bGH6Ef4io0G5abDHJ3yEQmkUv" https://ppmr69im5j.execute-api.eu-west-3.amazonaws.com/prod/health
```

Puedes adaptar este comando para otros endpoints cambiando la URL al recurso que desees probar.


## Guía para ejecutar pruebas automáticas en producción

1. **Accede al entorno de producción (AWS):**
	- Sube el código fuente actualizado.
	- Instala las dependencias necesarias (`pip install -r requirements.txt`).
	- Configura las variables de entorno (API_KEY, conexión a MySQL, etc.).

2. **Verifica que la API esté corriendo:**
	- Prueba el endpoint `/health` como en el ejemplo anterior.

3. **Ejecuta los tests automáticos:**
	- Asegúrate de estar en la carpeta del backend.
	- Exporta la API_KEY de producción:
	  ```bash
	  export API_KEY="<tu_api_key_produccion>"
	  ```
	  (En PowerShell: `$env:API_KEY="<tu_api_key_produccion>"`)
	- Lanza los tests:
	  ```bash
	  pytest tests/test_endpoints.py
	  ```

4. **Revisa los resultados:**
	- Verifica que todos los tests pasen correctamente.
	- Si algún test falla, revisa los logs y la configuración.

5. **Precauciones:**
	- Si la base de datos contiene datos reales, revisa que los tests no borren ni modifiquen información crítica.
	- Es recomendable ejecutar primero en un entorno de staging.

---
¿Dudas o necesitas adaptar los tests para producción? Consulta con el equipo antes de ejecutar pruebas destructivas.
