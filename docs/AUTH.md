# Autenticación JWT - API Workers Profesores

Documentación completa del sistema de autenticación basado en JSON Web Tokens (JWT).

## 📋 Tabla de Contenidos

- [Resumen del Sistema](#resumen-del-sistema)
- [Tipos de Tokens](#tipos-de-tokens)
- [Flujo de Login](#flujo-de-login)
- [Flujo de Refresh](#flujo-de-refresh)
- [Flujo de Logout](#flujo-de-logout)
- [Claims del Token](#claims-del-token)
- [Rotación de Tokens](#rotación-de-tokens)
- [Seguridad](#seguridad)
- [Ejemplos PowerShell](#ejemplos-powershell)

## Resumen del Sistema

La API usa **JWT (JSON Web Tokens)** para autenticación stateless con dos tipos de tokens:

- **Access Token:** Token de corta duración (15 min) para acceder a endpoints protegidos
- **Refresh Token:** Token de larga duración (30 días) para renovar access tokens expirados

### Características de Seguridad

✅ **Tokens firmados con HS256** (HMAC con SHA-256)  
✅ **Rotación automática** de refresh tokens al renovar  
✅ **Invalidación en logout** (blacklist de refresh tokens)  
✅ **Claims personalizados** con metadata del usuario  
✅ **Protección contra fuerza bruta** (bloqueo temporal tras intentos fallidos)  
✅ **Auditoría completa** en tabla `UserLoginLog`

## Tipos de Tokens

### Access Token

```json
{
  "type": "access",
  "exp": 1700000000,
  "iat": 1699999100,
  "sub": "12",
  "academia_id": 5,
  "roles": ["Admin_academia"],
  "nombre": "Juan Pérez",
  "email": "juan@academia.com",
  "display_name": "Juan Pérez"
}
```

**Características:**
- **Duración:** 15 minutos (configurable con `JWT_ACCESS_TOKEN_EXPIRES`)
- **Uso:** Enviado en header `Authorization: Bearer <access_token>`
- **Claims:** Contiene identidad y permisos del usuario
- **Almacenamiento:** Cliente (localStorage, memoria, etc.)

### Refresh Token

```json
{
  "type": "refresh",
  "exp": 1702591100,
  "iat": 1699999100,
  "sub": "12",
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Características:**
- **Duración:** 30 días (configurable con `JWT_REFRESH_TOKEN_EXPIRES`)
- **Uso:** Endpoint `/auth/refresh` para obtener nuevo access token
- **Claims:** Identidad mínima + JTI (JWT ID único)
- **Almacenamiento:** Base de datos tabla `RefreshToken` + cliente
- **Rotación:** Se invalida tras uso y se emite uno nuevo

## Flujo de Login

### 1. Request

```http
POST /auth/login
Content-Type: application/json

{
  "email": "admin_academia@academia.com",
  "password": "password_admin_academia"
}
```

### 2. Proceso Interno

```python
# auth_routes.py

@bp.route('/login', methods=['POST'])
def login():
    email = request.json['email']
    password = request.json['password']
    
    # 1. Buscar usuario
    user = Usuario.query.filter_by(email=email).first()
    
    if not user:
        # Log intento fallido
        UserLoginLog.create(email=email, exito=False, razon='Usuario no existe')
        return jsonify({'error': 'Credenciales inválidas'}), 401
    
    # 2. Verificar password
    if not user.check_password(password):
        # Incrementar intentos fallidos
        user.intentos_fallidos += 1
        
        if user.intentos_fallidos >= 5:
            user.bloqueado_hasta = datetime.now() + timedelta(minutes=15)
        
        db.session.commit()
        UserLoginLog.create(email=email, exito=False, razon='Password incorrecta')
        return jsonify({'error': 'Credenciales inválidas'}), 401
    
    # 3. Verificar bloqueo temporal
    if user.bloqueado_hasta and user.bloqueado_hasta > datetime.now():
        return jsonify({'error': 'Usuario bloqueado temporalmente'}), 403
    
    # 4. Verificar estado del usuario
    if user.estado != 'A':  # A=Activo, B=Baja
        return jsonify({'error': 'Usuario inactivo'}), 403
    
    # 5. Generar tokens
    access_token = create_access_token(identity=user.id, additional_claims={
        'academia_id': user.academia_id,
        'roles': [role.nombre for role in user.roles],
        'nombre': user.nombre,
        'email': user.email,
        'display_name': user.display_name or user.nombre
    })
    
    refresh_token_jti = str(uuid.uuid4())
    refresh_token = create_refresh_token(identity=user.id, additional_claims={
        'jti': refresh_token_jti
    })
    
    # 6. Guardar refresh token en BD
    RefreshToken.create(
        user_id=user.id,
        token_jti=refresh_token_jti,
        expira_en=datetime.now() + timedelta(days=30),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    # 7. Resetear intentos fallidos
    user.intentos_fallidos = 0
    user.bloqueado_hasta = None
    db.session.commit()
    
    # 8. Log exitoso
    UserLoginLog.create(email=email, exito=True, user_id=user.id)
    
    return jsonify({
        'ok': True,
        'tokens': {
            'access_token': access_token,
            'refresh_token': refresh_token
        },
        'user': {
            'id': user.id,
            'nombre': user.nombre,
            'email': user.email,
            'roles': [role.nombre for role in user.roles],
            'academia_id': user.academia_id
        }
    }), 200
```

### 3. Response

```json
{
  "ok": true,
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  },
  "user": {
    "id": 12,
    "nombre": "Juan Pérez",
    "email": "juan@academia.com",
    "roles": ["Admin_academia"],
    "academia_id": 5
  }
}
```

### 4. Cliente Almacena Tokens

```javascript
// Almacenar en localStorage (ejemplo)
localStorage.setItem('access_token', response.tokens.access_token);
localStorage.setItem('refresh_token', response.tokens.refresh_token);
```

## Flujo de Refresh

### 1. Request

```http
POST /auth/refresh
Authorization: Bearer <refresh_token>
```

### 2. Proceso Interno

```python
# auth_routes.py

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    # 1. Obtener identidad del refresh token actual
    current_user_id = get_jwt_identity()
    jti = get_jwt()['jti']
    
    # 2. Verificar que el token no ha sido invalidado
    refresh_token_db = RefreshToken.query.filter_by(
        token_jti=jti,
        revocado=False
    ).first()
    
    if not refresh_token_db:
        return jsonify({'error': 'Token inválido o revocado'}), 401
    
    # 3. Verificar que no ha expirado
    if refresh_token_db.expira_en < datetime.now():
        return jsonify({'error': 'Token expirado'}), 401
    
    # 4. Cargar usuario
    user = Usuario.query.get(current_user_id)
    
    if not user or user.estado != 'A':
        return jsonify({'error': 'Usuario inactivo'}), 403
    
    # 5. Generar nuevo access token
    access_token = create_access_token(identity=user.id, additional_claims={
        'academia_id': user.academia_id,
        'roles': [role.nombre for role in user.roles],
        'nombre': user.nombre,
        'email': user.email,
        'display_name': user.display_name or user.nombre
    })
    
    # 6. ROTACIÓN: Revocar refresh token actual y generar uno nuevo
    refresh_token_db.revocado = True
    refresh_token_db.revocado_en = datetime.now()
    
    new_refresh_token_jti = str(uuid.uuid4())
    new_refresh_token = create_refresh_token(identity=user.id, additional_claims={
        'jti': new_refresh_token_jti
    })
    
    RefreshToken.create(
        user_id=user.id,
        token_jti=new_refresh_token_jti,
        expira_en=datetime.now() + timedelta(days=30),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent')
    )
    
    db.session.commit()
    
    return jsonify({
        'ok': True,
        'tokens': {
            'access_token': access_token,
            'refresh_token': new_refresh_token
        }
    }), 200
```

### 3. Response

```json
{
  "ok": true,
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

### 4. Cliente Actualiza Tokens

```javascript
// Reemplazar tokens antiguos
localStorage.setItem('access_token', response.tokens.access_token);
localStorage.setItem('refresh_token', response.tokens.refresh_token);
```

## Flujo de Logout

### 1. Request

```http
POST /auth/logout
Authorization: Bearer <access_token>
```

**Headers opcionales:**
- `X-Refresh-Token: <refresh_token>` - Para revocar refresh token también

### 2. Proceso Interno

```python
# auth_routes.py

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # 1. Obtener identidad del access token
    current_user_id = get_jwt_identity()
    
    # 2. Revocar refresh token si se proporciona
    refresh_token_header = request.headers.get('X-Refresh-Token')
    
    if refresh_token_header:
        try:
            # Decodificar refresh token para obtener JTI
            decoded = decode_token(refresh_token_header)
            jti = decoded['jti']
            
            # Revocar en BD
            RefreshToken.query.filter_by(
                token_jti=jti
            ).update({
                'revocado': True,
                'revocado_en': datetime.now()
            })
            
            db.session.commit()
        except Exception as e:
            # Ignorar errores si el token ya expiró
            pass
    
    # 3. Log de logout
    UserLoginLog.create(
        user_id=current_user_id,
        event_type='logout',
        exito=True
    )
    
    return jsonify({
        'ok': True,
        'message': 'Logout exitoso'
    }), 200
```

### 3. Response

```json
{
  "ok": true,
  "message": "Logout exitoso"
}
```

### 4. Cliente Elimina Tokens

```javascript
// Limpiar tokens del almacenamiento
localStorage.removeItem('access_token');
localStorage.removeItem('refresh_token');
```

## Claims del Token

### Claims Estándar (RFC 7519)

| Claim | Tipo | Descripción |
|-------|------|-------------|
| `sub` | string | Subject (user ID) |
| `iat` | timestamp | Issued At (cuándo se emitió) |
| `exp` | timestamp | Expiration Time (cuándo expira) |
| `jti` | string | JWT ID (solo refresh tokens) |

### Claims Personalizados

| Claim | Tipo | Descripción | En Access | En Refresh |
|-------|------|-------------|-----------|------------|
| `type` | string | "access" o "refresh" | ✅ | ✅ |
| `academia_id` | integer | ID de la academia del usuario | ✅ | ❌ |
| `roles` | array | Lista de roles del usuario | ✅ | ❌ |
| `nombre` | string | Nombre completo | ✅ | ❌ |
| `email` | string | Email del usuario | ✅ | ❌ |
| `display_name` | string | Nombre para mostrar en UI | ✅ | ❌ |

### Ejemplo Completo de Access Token

```json
{
  "type": "access",
  "sub": "12",
  "iat": 1699999100,
  "exp": 1700000000,
  "academia_id": 5,
  "roles": ["Admin_academia"],
  "nombre": "Juan Pérez García",
  "email": "juan@academia.com",
  "display_name": "Juan Pérez"
}
```

### Nota sobre display_name

**Añadido:** Octubre 2025

El claim `display_name` se usa para mostrar el nombre del usuario en la UI sin necesidad de concatenar campos. Si no está definido en la BD, se usa el valor de `nombre`.

```python
# Generación de display_name
display_name = user.display_name or user.nombre
```

## Rotación de Tokens

### ¿Por Qué Rotamos?

La **rotación de refresh tokens** es una práctica de seguridad que invalida el token anterior cada vez que se usa, reduciendo la ventana de ataque en caso de robo.

### Flujo Completo

```
1. Cliente hace login
   ↓
2. Recibe refresh_token_1 (JTI=abc123)
   ↓
3. Access token expira (15 min después)
   ↓
4. Cliente usa refresh_token_1 en /auth/refresh
   ↓
5. Servidor:
   - Valida refresh_token_1
   - Revoca refresh_token_1 (marca revocado=True en BD)
   - Genera refresh_token_2 (JTI=def456)
   - Retorna access_token_nuevo + refresh_token_2
   ↓
6. Cliente almacena refresh_token_2
   ↓
7. Si alguien intenta reusar refresh_token_1 → 401 Unauthorized
```

### Detección de Reuso

```python
# Intento de reusar un token revocado
refresh_token_db = RefreshToken.query.filter_by(token_jti=jti).first()

if refresh_token_db.revocado:
    # ⚠️ ALERTA DE SEGURIDAD: Token revocado siendo reusado
    # Posible robo de token
    
    # Revocar TODOS los refresh tokens del usuario
    RefreshToken.query.filter_by(
        user_id=refresh_token_db.user_id,
        revocado=False
    ).update({'revocado': True, 'revocado_en': datetime.now()})
    
    db.session.commit()
    
    # Enviar alerta de seguridad
    send_security_alert(refresh_token_db.user_id, 'token_reuse_detected')
    
    return jsonify({'error': 'Token inválido'}), 401
```

## Seguridad

### Secretos de Firma

La API usa **dos secretos diferentes**:

```python
# config.py

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_secret')  # Para access/refresh tokens
JWT_DELEGATION_SECRET = os.getenv('JWT_DELEGATION_SECRET', 'default_delegation')  # Para tokens de delegación
```

**⚠️ IMPORTANTE:** En producción, usar secretos largos y aleatorios (mínimo 32 caracteres).

### Protección Contra Fuerza Bruta

```python
# Después de 5 intentos fallidos
if user.intentos_fallidos >= 5:
    user.bloqueado_hasta = datetime.now() + timedelta(minutes=15)
    db.session.commit()
    return jsonify({'error': 'Usuario bloqueado temporalmente'}), 403
```

### Auditoría de Logins

Tabla `UserLoginLog` registra:
- ✅ Intentos exitosos
- ❌ Intentos fallidos (con razón)
- 🚪 Logouts
- 🔄 Refreshes

```sql
SELECT * FROM UserLoginLog 
WHERE user_id = 12 
ORDER BY timestamp_alta DESC 
LIMIT 10;
```

### Headers de Seguridad

Recomendaciones para cliente:

```http
Authorization: Bearer <access_token>
X-Refresh-Token: <refresh_token>  # Solo en logout
Content-Type: application/json
```

## Ejemplos PowerShell

### Login

```powershell
$loginUrl = 'http://localhost:5000/auth/login'
$loginBody = @{
    email = 'admin_academia@academia.com'
    password = 'password_admin_academia'
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri $loginUrl -Method POST -Body $loginBody -ContentType 'application/json'

# Guardar tokens
$accessToken = $response.tokens.access_token
$refreshToken = $response.tokens.refresh_token

Write-Host "Access Token: $accessToken"
Write-Host "User: $($response.user.nombre)"
```

### Llamar Endpoint Protegido

```powershell
$usuariosUrl = 'http://localhost:5000/usuarios'
$headers = @{
    Authorization = "Bearer $accessToken"
}

$usuarios = Invoke-RestMethod -Uri $usuariosUrl -Method GET -Headers $headers

$usuarios.data | Format-Table id, nombre, email, roles
```

### Refresh Token

```powershell
$refreshUrl = 'http://localhost:5000/auth/refresh'
$headers = @{
    Authorization = "Bearer $refreshToken"
}

$response = Invoke-RestMethod -Uri $refreshUrl -Method POST -Headers $headers

# Actualizar tokens
$accessToken = $response.tokens.access_token
$refreshToken = $response.tokens.refresh_token

Write-Host "Tokens renovados exitosamente"
```

### Logout

```powershell
$logoutUrl = 'http://localhost:5000/auth/logout'
$headers = @{
    Authorization = "Bearer $accessToken"
    'X-Refresh-Token' = $refreshToken
}

Invoke-RestMethod -Uri $logoutUrl -Method POST -Headers $headers

Write-Host "Logout exitoso"
```

### Script Completo de Sesión

```powershell
# Login
$loginBody = @{
    email = 'admin_academia@academia.com'
    password = 'password_admin_academia'
} | ConvertTo-Json

$loginResp = Invoke-RestMethod -Uri 'http://localhost:5000/auth/login' -Method POST -Body $loginBody -ContentType 'application/json'

$accessToken = $loginResp.tokens.access_token
$refreshToken = $loginResp.tokens.refresh_token

# Listar usuarios
$headers = @{ Authorization = "Bearer $accessToken" }
$usuarios = Invoke-RestMethod -Uri 'http://localhost:5000/usuarios' -Headers $headers
Write-Host "Usuarios: $($usuarios.data.Count)"

# Simular expiración (esperar 15 min o cambiar JWT_ACCESS_TOKEN_EXPIRES)
# ...

# Renovar tokens
$refreshHeaders = @{ Authorization = "Bearer $refreshToken" }
$refreshResp = Invoke-RestMethod -Uri 'http://localhost:5000/auth/refresh' -Method POST -Headers $refreshHeaders

$accessToken = $refreshResp.tokens.access_token
$refreshToken = $refreshResp.tokens.refresh_token

# Volver a listar usuarios con nuevo access token
$headers = @{ Authorization = "Bearer $accessToken" }
$usuarios = Invoke-RestMethod -Uri 'http://localhost:5000/usuarios' -Headers $headers
Write-Host "Usuarios (con nuevo token): $($usuarios.data.Count)"

# Logout
$logoutHeaders = @{
    Authorization = "Bearer $accessToken"
    'X-Refresh-Token' = $refreshToken
}
Invoke-RestMethod -Uri 'http://localhost:5000/auth/logout' -Method POST -Headers $logoutHeaders
Write-Host "Sesión cerrada"
```

## Recursos Adicionales

- [Sistema de Permisos](PERMISSIONS.md) - Autorización basada en roles
- [Guía de Desarrollo](DEVELOPMENT.md) - Setup y debugging
- [Ejemplos de Uso](API_USAGE.md) - Más ejemplos con PowerShell y curl
