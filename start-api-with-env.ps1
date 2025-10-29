# Script para arrancar el API Python con las variables de entorno correctas
# Alineadas con el backend Java

Write-Host "🚀 Arrancando API Python con configuración alineada..." -ForegroundColor Green

# Variables de entorno requeridas
$env:DB_ENV = 'developmentAWS'
$env:JWT_SECRET_KEY = 'mi_secret_app_local_larga'
$env:JWT_DELEGATION_SECRET = 'mi_secret_delegacion_local_larga'
$env:JWT_DELEGATION_EXPIRATIONMINUTES = '5'
$env:DEBUG = '1'
$env:FLASK_DEBUG = '1'
$env:APP_ENV = 'development'

Write-Host "✅ Variables configuradas:" -ForegroundColor Cyan
Write-Host "   DB_ENV: $env:DB_ENV"
Write-Host "   JWT_DELEGATION_SECRET: $(if($env:JWT_DELEGATION_SECRET.Length -gt 10) { $env:JWT_DELEGATION_SECRET.Substring(0,10) + '...' } else { $env:JWT_DELEGATION_SECRET })"
Write-Host "   JWT_DELEGATION_EXPIRATIONMINUTES: $env:JWT_DELEGATION_EXPIRATIONMINUTES"

# Activar virtualenv si existe
if (Test-Path '.venv\Scripts\Activate.ps1') {
    Write-Host "✅ Activando virtualenv..." -ForegroundColor Cyan
    . .venv\Scripts\Activate.ps1
}

Write-Host ""
Write-Host "🌐 Arrancando servidor en http://localhost:5000 ..." -ForegroundColor Green
Write-Host "   Presiona Ctrl+C para detener" -ForegroundColor Yellow
Write-Host ""

# Arrancar la aplicación
python -u main.py
