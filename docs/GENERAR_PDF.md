# Generar PDF de la documentación OpenAPI

## Opción 1: Usar wkhtmltopdf (Windows)
# 1. Descargar desde: https://wkhtmltopdf.org/downloads.html
# 2. Instalar
# 3. Ejecutar:
wkhtmltopdf --enable-local-file-access swagger-standalone.html documentacion-api.pdf

## Opción 2: Usar redoc-cli (Node.js)
# Instalar redoc-cli globalmente
npm install -g redoc-cli

# Generar HTML bundle (todo en un archivo)
redoc-cli bundle openapi-auto.json -o documentacion-api-bundle.html

# Generar PDF (requiere Chrome/Chromium instalado)
npx @redocly/cli build-docs openapi-auto.json --output=documentacion-api.pdf

## Opción 3: Desde el navegador
# 1. Abre swagger-standalone.html o redoc-standalone.html en el navegador
# 2. Presiona Ctrl+P
# 3. Selecciona "Guardar como PDF"
# 4. Guarda el archivo

## Opción 4: Usar swagger-cli (Node.js)
npm install -g @apidevtools/swagger-cli

# Validar el spec
swagger-cli validate openapi-auto.json

# Generar bundle (todo en un archivo JSON)
swagger-cli bundle openapi-auto.json -o openapi-bundle.json -t json
