# Guía de Despliegue API Workers en AWS (Producción)

## Actualización: Arquitectura JWT (Sin API-Key)

Esta guía actualiza el despliegue de API Workers para usar **solo JWT** (sin API-Key), alineado con la nueva arquitectura donde Backend Chat reenvía el JWT del usuario.

---

## Índice

1. [Cambios en la Arquitectura](#1-cambios-en-la-arquitectura)
2. [Estado Actual vs Deseado](#2-estado-actual-vs-deseado)
3. [Verificar Código (Eliminar API-Key)](#3-verificar-código-eliminar-api-key)
4. [Configuración de Producción](#4-configuración-de-producción)
5. [Deploy en AWS Elastic Beanstalk](#5-deploy-en-aws-elastic-beanstalk)
6. [Dominio y HTTPS](#6-dominio-y-https)
7. [Costos](#7-costos)
8. [Verificación](#8-verificación)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Cambios en la Arquitectura

### Arquitectura ANTIGUA (con API-Key) ❌

```
Android → Backend Chat (JWT del usuario)
            ↓
         Genera API-Key
            ↓
       API Workers (valida API-Key + JWT)
            ↓
          MySQL
```

**Problemas:**
- ❌ Dos sistemas de autenticación (JWT + API-Key)
- ❌ API-Key es estática (menos segura)
- ❌ Complejidad innecesaria
- ❌ Logs con diferentes usuarios (confuso)

---

### Arquitectura NUEVA (solo JWT) ✅

```
Android → Backend Chat (JWT del usuario)
            ↓
       Reenvía MISMO JWT
            ↓
       API Workers (valida solo JWT)
            ↓
          MySQL
```

**Ventajas:**
- ✅ Un solo sistema de autenticación (JWT)
- ✅ Trazabilidad: mismo userId en todos los logs
- ✅ Más simple y seguro
- ✅ JWT tiene expiración (15 min)

---

## 2. Estado Actual vs Deseado

### Verificar Estado Actual

```powershell
# 1. Ver variables de entorno en AWS
cd "c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"

# Si tienes eb configurado:
eb printenv

# Buscar estas variables:
# - API_KEY_PROD  ← DEBE ELIMINARSE
# - JWT_SECRET_KEY ← DEBE EXISTIR
```

### Estado Deseado (Solo JWT)

**Variables de entorno necesarias:**
```bash
# Autenticación (SOLO JWT)
JWT_SECRET_KEY=tu_secret_compartido_con_backend_chat_y_api_workers

# Base de datos
DB_PROD_HOST=tu-db.xxxxxx.rds.amazonaws.com
DB_PROD_PORT=3306
DB_PROD_USER=admin_prod
DB_PROD_PASS=xxxxx
DB_PROD_NAME=academia_prod

# CORS (permitir Backend Chat)
ALLOWED_ORIGINS=https://chat-backend-production.elasticbeanstalk.com,https://chat.tuacademia.com

# Entorno
APP_ENV=production
FLASK_ENV=production
```

**Variables a ELIMINAR:**
```bash
# ❌ ELIMINAR estas variables si existen:
API_KEY_DEV
API_KEY_PROD
```

---

## 3. Verificar Código (Eliminar API-Key)

### 3.1 Buscar Referencias a API-Key

```powershell
# Buscar todas las referencias a API_KEY en el código
cd "c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"

# PowerShell:
Select-String -Path "src\**\*.py" -Pattern "API_KEY|api_key" -CaseSensitive
```

### 3.2 Eliminar Middleware de API-Key

**Archivo a revisar:** `src/shared/middleware/auth.py`

```python
# ❌ ELIMINAR este código si existe:
def validate_api_key():
    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != os.getenv('API_KEY_PROD'):
        return jsonify({"error": "Invalid API key"}), 401

# ✅ MANTENER solo validación JWT:
@jwt_required()
def protected_endpoint():
    identity = get_jwt_identity()
    # ... tu lógica aquí
```

### 3.3 Actualizar Endpoints Protegidos

**Todos los endpoints deben usar SOLO `@jwt_required()`:**

```python
# src/alumnos/interfaces/flask/routes.py (ejemplo)
from flask_jwt_extended import jwt_required, get_jwt_identity

@alumnos_bp.route('/alumnos', methods=['GET'])
@jwt_required()  # ← SOLO esto, sin validar API-Key
def get_alumnos():
    identity = get_jwt_identity()
    # Extraer academia_id del JWT
    if isinstance(identity, str):
        try:
            identity = json.loads(identity)
        except:
            pass
    
    academia_id = identity.get('academia_id')
    usuario_id = identity.get('usuario_id')
    
    # ... tu lógica aquí
```

### 3.4 Actualizar `.env.example`

```bash
# Actualizar archivo .env.example
# ELIMINAR referencias a API_KEY
```

**Nuevo `.env.example`:**

```bash
# =============================================================================
# VARIABLES DE ENTORNO - API WORKERS
# =============================================================================

# -----------------------------------------------------------------------------
# ENTORNO
# -----------------------------------------------------------------------------
APP_ENV=production
FLASK_ENV=production

# -----------------------------------------------------------------------------
# AUTENTICACIÓN JWT (ÚNICO SISTEMA DE AUTH)
# -----------------------------------------------------------------------------
# Secret compartido con Backend Chat
# Debe ser el MISMO en ambos componentes
# Generar con: openssl rand -base64 64
JWT_SECRET_KEY=tu_secret_super_seguro_compartido_con_backend_chat

# Expiración de tokens (en minutos)
JWT_ACCESS_TOKEN_EXPIRES=15
JWT_REFRESH_TOKEN_EXPIRES=43200  # 30 días

# -----------------------------------------------------------------------------
# BASE DE DATOS MYSQL (PRODUCCIÓN)
# -----------------------------------------------------------------------------
DB_PROD_HOST=tu-db.xxxxxx.rds.amazonaws.com
DB_PROD_PORT=3306
DB_PROD_USER=admin_prod
DB_PROD_PASS=contraseña_segura_aquí
DB_PROD_NAME=academia_prod

# -----------------------------------------------------------------------------
# CORS
# -----------------------------------------------------------------------------
# Dominios permitidos (separados por coma)
ALLOWED_ORIGINS=https://chat-backend-production.elasticbeanstalk.com,https://chat.tuacademia.com

# -----------------------------------------------------------------------------
# URLS
# -----------------------------------------------------------------------------
BASE_URL_PROD=https://api-workers-production.elasticbeanstalk.com

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
LOG_LEVEL=INFO

# =============================================================================
# INSTRUCCIONES
# =============================================================================
# 1. Copiar este archivo como .env.production
# 2. Rellenar valores reales
# 3. NUNCA subir .env.production a Git (ya está en .gitignore)
# 4. En AWS Elastic Beanstalk, configurar con:
#    eb setenv JWT_SECRET_KEY=xxx DB_PROD_HOST=xxx ...
```

---

## 4. Configuración de Producción

### 4.1 Actualizar `config.py`

**Verificar que `config.py` NO use API_KEY:**

```python
# config.py
import os
from datetime import timedelta

class Config:
    # JWT Configuration (ÚNICO SISTEMA DE AUTH)
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 15)))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 30)))
    
    # ❌ ELIMINAR estas líneas si existen:
    # API_KEY = os.getenv('API_KEY_PROD')
    # API_KEY_HEADER = 'X-API-Key'
    
    # Database
    if os.getenv('APP_ENV') == 'production':
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('DB_PROD_USER')}:"
            f"{os.getenv('DB_PROD_PASS')}@"
            f"{os.getenv('DB_PROD_HOST')}:"
            f"{os.getenv('DB_PROD_PORT', 3306)}/"
            f"{os.getenv('DB_PROD_NAME')}"
        )
    else:
        # Desarrollo
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('DB_DEV_USER')}:"
            f"{os.getenv('DB_DEV_PASS')}@"
            f"{os.getenv('DB_DEV_HOST')}:"
            f"{os.getenv('DB_DEV_PORT', 3307)}/"
            f"{os.getenv('DB_DEV_NAME')}"
        )
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 3600,
        'pool_size': 10,
        'max_overflow': 20
    }
    
    # CORS
    CORS_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')
```

### 4.2 Verificar Middleware JWT

**Archivo:** `src/shared/middleware/auth.py`

```python
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
import json

def jwt_required_custom():
    """
    Decorador personalizado para validar JWT.
    NO valida API-Key (eliminado en nueva arquitectura).
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                # Verificar JWT
                verify_jwt_in_request()
                
                # Obtener identidad
                identity = get_jwt_identity()
                
                # Si es string JSON, parsear
                if isinstance(identity, str):
                    try:
                        identity = json.loads(identity)
                    except:
                        pass
                
                # Verificar que tenga campos obligatorios
                if isinstance(identity, dict):
                    if 'usuario_id' not in identity:
                        return jsonify({"error": "Invalid JWT: missing usuario_id"}), 401
                
                return fn(*args, **kwargs)
            
            except Exception as e:
                return jsonify({"error": f"JWT validation failed: {str(e)}"}), 401
        
        return decorator
    return wrapper

# Alias para compatibilidad
jwt_required = jwt_required_custom
```

---

## 5. Deploy en AWS Elastic Beanstalk

### 5.1 Verificar Entorno Actual

```powershell
cd "c:\Users\Angel FV\Desktop\FORMACION\api-workers-profesores"

# Ver entornos existentes
eb list

# Ver estado del entorno actual
eb status

# Ver variables de entorno configuradas
eb printenv
```

### 5.2 Actualizar Variables de Entorno

```powershell
# ELIMINAR variables antiguas (API-Key)
eb setenv API_KEY_DEV- API_KEY_PROD-

# CONFIGURAR variables nuevas (solo JWT)
eb setenv `
  APP_ENV=production `
  FLASK_ENV=production `
  JWT_SECRET_KEY=tu_secret_compartido_con_backend_chat `
  JWT_ACCESS_TOKEN_EXPIRES=15 `
  JWT_REFRESH_TOKEN_EXPIRES=43200 `
  DB_PROD_HOST=tu-db.xxxxx.rds.amazonaws.com `
  DB_PROD_PORT=3306 `
  DB_PROD_USER=admin_prod `
  DB_PROD_PASS=contraseña_segura `
  DB_PROD_NAME=academia_prod `
  ALLOWED_ORIGINS=https://chat-backend-production.elasticbeanstalk.com `
  BASE_URL_PROD=https://api-workers-production.elasticbeanstalk.com `
  LOG_LEVEL=INFO
```

**⚠️ CRÍTICO:** El `JWT_SECRET_KEY` **DEBE ser el MISMO** que uses en Backend Chat.

### 5.3 Compilar y Deploy

```powershell
# 1. Activar entorno virtual
.\.venv\Scripts\Activate.ps1

# 2. Instalar/actualizar dependencias
pip install -r requirements.txt

# 3. Verificar que no haya errores
python -m flask --app app.py check

# 4. Deploy a AWS
eb deploy

# 5. Monitorear logs
eb logs --stream
```

### 5.4 Verificar Salud del Entorno

```powershell
# Ver health status
eb health

# Debe mostrar:
# Environment: api-workers-production
# Status: Ready
# Health: Green
```

---

## 6. Dominio y HTTPS

### Opción 1: Dominio Gratuito AWS (Recomendado) ✅

**Ventajas:**
- ✅ **$0** de costo
- ✅ HTTPS incluido
- ✅ Sin configuración DNS

**URL resultante:**
```
https://api-workers-production.us-east-1.elasticbeanstalk.com
```

**Pasos:**
1. Ya lo tienes con el deploy de Elastic Beanstalk
2. Obtener URL: `eb status` (campo CNAME)
3. Configurar HTTPS con Let's Encrypt (igual que Backend Chat)

**Configuración HTTPS (mismo proceso que Backend Chat):**

```bash
# 1. SSH a la instancia
eb ssh

# 2. Instalar Certbot
sudo yum install -y certbot python3-certbot-nginx nginx

# 3. Configurar Nginx
sudo tee /etc/nginx/conf.d/flask.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name api-workers-production.us-east-1.elasticbeanstalk.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 4. Iniciar Nginx
sudo systemctl enable nginx
sudo systemctl start nginx

# 5. Obtener certificado SSL
sudo certbot --nginx -d api-workers-production.us-east-1.elasticbeanstalk.com --non-interactive --agree-tos --email tu-email@ejemplo.com

# 6. Abrir puerto 443 en Security Group
# (desde AWS Console → EC2 → Security Groups)
```

---

### Opción 2: Dominio Personalizado ($12/año) ⚠️

**Solo si necesitas:**
- Marca profesional: `api.tuacademia.com`
- Múltiples subdominios
- Comercialización

**Costo:**
- Dominio: $12/año (~$1/mes)
- Route 53: $0.50/mes
- **Total: ~$1.50/mes**

**Pasos:**
1. Comprar dominio en Route 53: `tuacademia.com`
2. Solicitar certificado ACM para: `api.tuacademia.com`
3. Configurar dominio con Load Balancer (requiere ALB, +$16/mes)
4. Crear registro DNS en Route 53

**⚠️ Importante:** Dominio personalizado requiere Application Load Balancer ($16/mes adicional) para HTTPS automático.

---

## 7. Costos

### Opción A: Single Instance + Let's Encrypt (100% GRATIS) ✅

| Recurso | Costo Primer Año | Después |
|---------|------------------|---------|
| **EC2 t3.micro** | **$0** (Free Tier) | $10/mes |
| **Dominio AWS** | **$0** (elasticbeanstalk.com) | $0 |
| **SSL (Let's Encrypt)** | **$0** | $0 |
| **RDS MySQL (compartido)** | **$0** (usar mismo que Backend Chat) | $15/mes |
| **Data Transfer (15 GB)** | **$0** | $1-3/mes |
| **TOTAL** | **$0/mes** | **$11-13/mes** |

**Capacidad:**
- 100-500 usuarios concurrentes
- ~50,000 peticiones/día
- 99% uptime

---

### Opción B: Con Load Balancer + Dominio Personalizado

| Recurso | Costo/Mes |
|---------|-----------|
| EC2 t3.small (2 instancias) | $30 |
| **Application Load Balancer** | $16 |
| Dominio personalizado | $1.50 |
| Route 53 | $0.50 |
| RDS MySQL | $15 |
| SSL (ACM) | $0 |
| Data Transfer | $3-5 |
| **TOTAL** | **~$66/mes** |

**Capacidad:**
- 1,000-5,000 usuarios concurrentes
- ~500,000 peticiones/día
- 99.9% uptime
- Alta disponibilidad

---

### Comparativa Rápida

| Característica | Gratis (Opción A) | Comercial (Opción B) |
|----------------|-------------------|----------------------|
| **Costo** | **$0** | ~$66/mes |
| **Dominio** | *.elasticbeanstalk.com | api.tuacademia.com |
| **SSL** | Let's Encrypt | ACM (automático) |
| **Alta disponibilidad** | ❌ | ✅ |
| **Auto-scaling** | ❌ | ✅ |
| **Mejor para** | Desarrollo/MVP | Producción comercial |

---

### Recomendación

**Para rúbrica educativa:**
- ✅ Usa **Opción A (GRATIS)**
- ✅ Dominio: `api-workers-production.elasticbeanstalk.com`
- ✅ HTTPS con Let's Encrypt
- ✅ Cumple 100% requisitos de seguridad

**Para comercialización:**
- ⚠️ Considera **Opción B** cuando tengas >500 usuarios/día
- ⚠️ Espera a tener ingresos >$200/mes para justificar $66/mes

---

## 8. Verificación

### 8.1 Test de Health Check

```powershell
# Health check (debe funcionar sin JWT)
curl -I https://api-workers-production.us-east-1.elasticbeanstalk.com/health

# Debe responder:
# HTTP/2 200
# {"status": "ok"}
```

### 8.2 Test de Login (sin API-Key)

```powershell
# Login debe funcionar SOLO con credenciales (sin API-Key)
curl -X POST https://api-workers-production.us-east-1.elasticbeanstalk.com/auth/login `
  -H "Content-Type: application/json" `
  -d '{\"email\":\"test@academia.com\",\"password\":\"Test123\"}'

# Debe responder con JWT tokens:
# {
#   "ok": true,
#   "tokens": {
#     "access_token": "eyJ...",
#     "refresh_token": "eyJ..."
#   },
#   "role": "Profesor",
#   "name": "Juan Pérez"
# }
```

### 8.3 Test de Endpoint Protegido (solo JWT)

```powershell
# Obtener token primero (del paso anterior)
$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Llamar endpoint protegido SOLO con JWT (sin API-Key)
curl -X GET https://api-workers-production.us-east-1.elasticbeanstalk.com/alumnos `
  -H "Authorization: Bearer $token"

# Debe responder con lista de alumnos
```

### 8.4 Verificar que API-Key No se Use

```powershell
# Intentar con API-Key antigua (debe funcionar sin ella)
curl -X GET https://api-workers-production.us-east-1.elasticbeanstalk.com/alumnos `
  -H "Authorization: Bearer $token" `
  -H "X-API-Key: cualquier_valor"

# Debe ignorar X-API-Key y responder solo basado en JWT ✅
```

### 8.5 Test de Integración con Backend Chat

```powershell
# Desde Backend Chat, hacer request a API Workers
# Backend Chat debe poder llamar endpoints con JWT que recibió de Android

# Backend Chat enviará:
# GET /alumnos
# Authorization: Bearer <JWT_del_usuario_de_android>

# API Workers valida JWT y responde ✅
```

---

## 9. Troubleshooting

### Problema: "JWT validation failed"

```bash
# Verificar que JWT_SECRET_KEY sea el mismo en ambos componentes

# API Workers:
eb printenv | grep JWT_SECRET_KEY

# Backend Chat:
# (en su entorno)
eb printenv | grep JWT_SECRET_KEY

# DEBEN SER EXACTAMENTE IGUALES
```

### Problema: "Database connection failed"

```bash
# Verificar conexión a RDS
eb ssh
mysql -h $DB_PROD_HOST -u $DB_PROD_USER -p$DB_PROD_PASS

# Si no conecta, verificar:
# 1. Security Group de RDS permite EC2 de API Workers
# 2. Credenciales correctas en variables de entorno
```

### Problema: "CORS error"

```bash
# Verificar ALLOWED_ORIGINS incluye Backend Chat
eb printenv | grep ALLOWED_ORIGINS

# Debe incluir:
# https://chat-backend-production.elasticbeanstalk.com

# Actualizar si falta:
eb setenv ALLOWED_ORIGINS=https://chat-backend-production.elasticbeanstalk.com
```

### Problema: "Certificate expired" (Let's Encrypt)

```bash
# Renovar certificado manualmente
eb ssh
sudo certbot renew
sudo systemctl reload nginx
```

---

## 10. Checklist de Migración

### Pre-Migración

- [ ] Código actualizado (API-Key eliminado)
- [ ] `.env.example` actualizado
- [ ] `config.py` sin referencias a API-Key
- [ ] Middleware solo valida JWT
- [ ] Todos los endpoints usan `@jwt_required()` sin API-Key

### Deploy

- [ ] Variables de entorno configuradas (sin API_KEY)
- [ ] JWT_SECRET_KEY compartido con Backend Chat
- [ ] Deploy exitoso: `eb deploy`
- [ ] Health check verde: `eb health`
- [ ] Logs sin errores: `eb logs`

### Post-Deploy

- [ ] Login funciona sin API-Key
- [ ] Endpoints protegidos funcionan solo con JWT
- [ ] HTTPS configurado (Let's Encrypt o ACM)
- [ ] CORS permite Backend Chat
- [ ] Backend Chat puede llamar API Workers con JWT
- [ ] Integración end-to-end funciona: Android → Backend Chat → API Workers → MySQL

---

## 11. Configuración de Backend Chat para Usar API Workers

**En Backend Chat, actualizar URL de API Workers:**

```properties
# application-production.properties (Backend Chat)
api.workers.base-url=https://api-workers-production.us-east-1.elasticbeanstalk.com

# NO enviar API-Key, solo reenviar JWT
# El interceptor HTTP debe incluir:
# Authorization: Bearer <jwt_recibido_de_android>
```

---

## 12. Resumen

### Arquitectura Final (Solo JWT)

```
Android App
    │ JWT
    ↓
Backend Chat
    │ Reenvía mismo JWT
    ↓
API Workers (valida JWT, NO API-Key)
    │
    ↓
MySQL
```

### Costos

- **MVP (GRATIS):** $0/mes con dominio AWS + Let's Encrypt
- **Comercial:** ~$66/mes con dominio personalizado + ALB

### Ventajas de Solo JWT

1. ✅ **Más simple:** Un solo mecanismo de autenticación
2. ✅ **Más seguro:** JWT expira cada 15 minutos
3. ✅ **Mejor trazabilidad:** Mismo userId en todos los logs
4. ✅ **Sin gestión de API-Keys:** No hay keys estáticas que rotar

---

## 13. Siguiente Paso

Con API Workers desplegado sin API-Key:
1. ✅ Backend Chat puede llamar API Workers con JWT del usuario
2. ✅ API Workers valida JWT y ejecuta lógica de negocio
3. ✅ Todo el flujo usa único JWT end-to-end
4. ✅ Cumple 100% requisitos de seguridad de la rúbrica

**¡Arquitectura lista para producción!** 🚀
