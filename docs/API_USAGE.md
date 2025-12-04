# Ejemplos de Uso - API Workers Profesores

Ejemplos prácticos de uso de la API con PowerShell y curl.

## 📋 Tabla de Contenidos

- [Autenticación](#autenticación)
- [Gestión de Usuarios](#gestión-de-usuarios)
- [Gestión de Academias](#gestión-de-academias)
- [Gestión de Alumnos](#gestión-de-alumnos)
- [Gestión de Cursos](#gestión-de-cursos)
- [Gestión de Sesiones](#gestión-de-sesiones)
- [Gestión de Inscripciones](#gestión-de-inscripciones)
- [Workflows Comunes](#workflows-comunes)

---

## Autenticación

### Login (PowerShell)

```powershell
$baseUrl = 'http://localhost:5000'

# Login como Admin Academia
$loginBody = @{
    email = 'admin_academia@academia.com'
    password = 'password_admin_academia'
} | ConvertTo-Json

$loginResp = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method POST -Body $loginBody -ContentType 'application/json'

# Guardar tokens
$accessToken = $loginResp.tokens.access_token
$refreshToken = $loginResp.tokens.refresh_token

Write-Host "✓ Login exitoso: $($loginResp.user.nombre)"
Write-Host "Academia ID: $($loginResp.user.academia_id)"
Write-Host "Roles: $($loginResp.user.roles -join ', ')"
```

### Login (curl)

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin_academia@academia.com",
    "password": "password_admin_academia"
  }'
```

### Refresh Token (PowerShell)

```powershell
$refreshHeaders = @{
    Authorization = "Bearer $refreshToken"
}

$refreshResp = Invoke-RestMethod -Uri "$baseUrl/auth/refresh" -Method POST -Headers $refreshHeaders

# Actualizar tokens
$accessToken = $refreshResp.tokens.access_token
$refreshToken = $refreshResp.tokens.refresh_token

Write-Host "✓ Tokens renovados"
```

### Logout (PowerShell)

```powershell
$logoutHeaders = @{
    Authorization = "Bearer $accessToken"
    'X-Refresh-Token' = $refreshToken
}

Invoke-RestMethod -Uri "$baseUrl/auth/logout" -Method POST -Headers $logoutHeaders

Write-Host "✓ Logout exitoso"
```

---

## Gestión de Usuarios

### Listar Usuarios (PowerShell)

```powershell
$headers = @{
    Authorization = "Bearer $accessToken"
}

# Todos los usuarios (con scoping automático según rol)
$usuarios = Invoke-RestMethod -Uri "$baseUrl/usuarios" -Headers $headers

$usuarios.data | Format-Table id, nombre, email, roles, academia_id

# Filtrar por academia
$params = @{
    academia_id = 1
}
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'
$usuarios = Invoke-RestMethod -Uri "$baseUrl/usuarios?$queryString" -Headers $headers
```

### Listar Usuarios (curl)

```bash
curl -X GET http://localhost:5000/usuarios \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Con filtro
curl -X GET "http://localhost:5000/usuarios?academia_id=1&rol_id=2" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Crear Usuario (PowerShell)

```powershell
$nuevoUsuario = @{
    nombre = 'María González'
    email = 'maria@academia.com'
    password = 'password123'
    rol_id = 3  # Profesor_academia
    academia_id = 1
    estado = 'A'
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $accessToken"
}

$usuario = Invoke-RestMethod -Uri "$baseUrl/usuarios" -Method POST -Headers $headers -Body $nuevoUsuario -ContentType 'application/json'

Write-Host "✓ Usuario creado: ID $($usuario.data.id)"
```

### Modificar Usuario (PowerShell)

```powershell
$updateBody = @{
    nombre = 'María González López'
    email = 'maria.gonzalez@academia.com'
} | ConvertTo-Json

$headers = @{
    Authorization = "Bearer $accessToken"
}

$updated = Invoke-RestMethod -Uri "$baseUrl/usuarios/15" -Method PATCH -Headers $headers -Body $updateBody -ContentType 'application/json'

Write-Host "✓ Usuario actualizado"
```

### Dar de Baja Usuario (PowerShell)

```powershell
$bajaBody = @{
    estado = 'B'
    motivo_baja = 'Finalización de contrato'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/usuarios/15" -Method PATCH -Headers $headers -Body $bajaBody -ContentType 'application/json'

Write-Host "✓ Usuario dado de baja"
```

---

## Gestión de Academias

### Listar Academias (PowerShell)

```powershell
$headers = @{
    Authorization = "Bearer $accessToken"
}

$academias = Invoke-RestMethod -Uri "$baseUrl/academias" -Headers $headers

$academias.data | Format-Table id, nombre, cif, email, telefono
```

### Crear Academia (PowerShell)

```powershell
# Solo Admin_plataforma puede crear academias

$nuevaAcademia = @{
    nombre = 'Academia de Inglés Cambridge'
    cif = 'B12345678'
    email = 'contacto@cambridge.com'
    telefono = '912345678'
    direccion = 'Calle Mayor 10'
    ciudad = 'Madrid'
    provincia = 'Madrid'
    codigo_postal = '28001'
    estado = 'A'
} | ConvertTo-Json

$academia = Invoke-RestMethod -Uri "$baseUrl/academias" -Method POST -Headers $headers -Body $nuevaAcademia -ContentType 'application/json'

Write-Host "✓ Academia creada: ID $($academia.data.id)"
```

### Modificar Academia (PowerShell)

```powershell
$updateBody = @{
    telefono = '912345679'
    email = 'info@cambridge.com'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/academias/1" -Method PATCH -Headers $headers -Body $updateBody -ContentType 'application/json'

Write-Host "✓ Academia actualizada"
```

---

## Gestión de Alumnos

### Listar Alumnos (PowerShell)

```powershell
$alumnos = Invoke-RestMethod -Uri "$baseUrl/alumnos" -Headers $headers

$alumnos.data | Format-Table id, nombre, apellido1, apellido2, email, fecha_nacimiento

# Filtrar por curso
$params = @{
    curso_id = 5
}
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'
$alumnos = Invoke-RestMethod -Uri "$baseUrl/alumnos?$queryString" -Headers $headers
```

### Crear Alumno (PowerShell)

```powershell
$nuevoAlumno = @{
    nombre = 'Carlos'
    apellido1 = 'Martínez'
    apellido2 = 'Pérez'
    fecha_nacimiento = '2010-05-15'
    email = 'carlos.martinez@email.com'
    telefono = '612345678'
    direccion = 'Calle Luna 5'
    ciudad = 'Madrid'
    provincia = 'Madrid'
    codigo_postal = '28002'
    academia_id = 1
    estado = 'A'
} | ConvertTo-Json

$alumno = Invoke-RestMethod -Uri "$baseUrl/alumnos" -Method POST -Headers $headers -Body $nuevoAlumno -ContentType 'application/json'

Write-Host "✓ Alumno creado: ID $($alumno.data.id)"
```

### Modificar Alumno (PowerShell)

```powershell
$updateBody = @{
    email = 'carlos.martinez.nuevo@email.com'
    telefono = '612345679'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/alumnos/10" -Method PATCH -Headers $headers -Body $updateBody -ContentType 'application/json'

Write-Host "✓ Alumno actualizado"
```

---

## Gestión de Cursos

### Listar Cursos (PowerShell)

```powershell
$cursos = Invoke-RestMethod -Uri "$baseUrl/cursos" -Headers $headers

$cursos.data | Format-Table id, nombre, nivel, fecha_inicio, fecha_fin, estado
```

### Crear Curso (PowerShell)

```powershell
$nuevoCurso = @{
    nombre = 'Inglés B1 - Grupo A'
    nivel = 'B1'
    descripcion = 'Curso intensivo de inglés nivel intermedio'
    fecha_inicio = '2025-09-01'
    fecha_fin = '2026-06-30'
    precio_mensual = 120.00
    academia_id = 1
    estado = 'A'
} | ConvertTo-Json

$curso = Invoke-RestMethod -Uri "$baseUrl/cursos" -Method POST -Headers $headers -Body $nuevoCurso -ContentType 'application/json'

Write-Host "✓ Curso creado: ID $($curso.data.id)"
```

### Asignar Profesor a Curso (PowerShell)

```powershell
$asignacionBody = @{
    usuario_id = 12  # ID del profesor
    curso_id = 5
    fecha_inicio = '2025-09-01'
    estado = 'A'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/cursos/5/profesores" -Method POST -Headers $headers -Body $asignacionBody -ContentType 'application/json'

Write-Host "✓ Profesor asignado al curso"
```

---

## Gestión de Sesiones

### Listar Sesiones (PowerShell)

```powershell
# Sesiones de un curso específico
$params = @{
    curso_id = 5
    fecha_desde = '2025-11-01'
    fecha_hasta = '2025-11-30'
}
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'

$sesiones = Invoke-RestMethod -Uri "$baseUrl/sesiones?$queryString" -Headers $headers

$sesiones.data | Format-Table id, fecha, hora_inicio, hora_fin, tipo_clase, estado
```

### Crear Sesión (PowerShell)

```powershell
$nuevaSesion = @{
    horario_curso_id = 10
    fecha = '2025-11-25'
    hora_inicio = '10:00:00'
    hora_fin = '11:30:00'
    tipo_clase = 'NORMAL'
    academia_id = 1
    estado = 'A'
} | ConvertTo-Json

$sesion = Invoke-RestMethod -Uri "$baseUrl/sesiones" -Method POST -Headers $headers -Body $nuevaSesion -ContentType 'application/json'

Write-Host "✓ Sesión creada: ID $($sesion.data.id)"
```

### Registrar Asistencia (PowerShell)

```powershell
$asistenciaBody = @{
    inscripcion_id = 25  # ID de la inscripción del alumno
    sesion_id = 100
    asistio = $true
    observaciones = 'Participación activa'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/sesiones/100/asistencias" -Method POST -Headers $headers -Body $asistenciaBody -ContentType 'application/json'

Write-Host "✓ Asistencia registrada"
```

---

## Gestión de Inscripciones

### Listar Inscripciones (PowerShell)

```powershell
# Inscripciones de un alumno
$params = @{
    alumno_id = 10
}
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'

$inscripciones = Invoke-RestMethod -Uri "$baseUrl/inscripciones?$queryString" -Headers $headers

$inscripciones.data | Format-Table id, alumno_nombre, curso_nombre, fecha_inscripcion, estado
```

### Crear Inscripción (PowerShell)

```powershell
$nuevaInscripcion = @{
    alumno_id = 10
    curso_id = 5
    fecha_inscripcion = '2025-09-01'
    precio_acordado = 120.00
    forma_pago = 'MENSUAL'
    estado = 'A'
} | ConvertTo-Json

$inscripcion = Invoke-RestMethod -Uri "$baseUrl/inscripciones" -Method POST -Headers $headers -Body $nuevaInscripcion -ContentType 'application/json'

Write-Host "✓ Inscripción creada: ID $($inscripcion.data.id)"
```

### Modificar Estado Inscripción (PowerShell)

```powershell
$updateBody = @{
    estado = 'B'
    motivo_baja = 'Solicitud del alumno'
    fecha_baja = '2025-11-25'
} | ConvertTo-Json

Invoke-RestMethod -Uri "$baseUrl/inscripciones/25" -Method PATCH -Headers $headers -Body $updateBody -ContentType 'application/json'

Write-Host "✓ Inscripción dada de baja"
```

---

## Workflows Comunes

### Workflow: Nuevo Alumno + Inscripción

```powershell
# 1. Login
$loginBody = @{
    email = 'admin_academia@academia.com'
    password = 'password_admin_academia'
} | ConvertTo-Json

$loginResp = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method POST -Body $loginBody -ContentType 'application/json'
$accessToken = $loginResp.tokens.access_token

$headers = @{
    Authorization = "Bearer $accessToken"
}

# 2. Crear alumno
$nuevoAlumno = @{
    nombre = 'Laura'
    apellido1 = 'Sánchez'
    apellido2 = 'Torres'
    fecha_nacimiento = '2008-03-20'
    email = 'laura.sanchez@email.com'
    telefono = '623456789'
    academia_id = 1
    estado = 'A'
} | ConvertTo-Json

$alumnoResp = Invoke-RestMethod -Uri "$baseUrl/alumnos" -Method POST -Headers $headers -Body $nuevoAlumno -ContentType 'application/json'
$alumnoId = $alumnoResp.data.id

Write-Host "✓ Alumno creado: ID $alumnoId"

# 3. Listar cursos disponibles
$cursos = Invoke-RestMethod -Uri "$baseUrl/cursos?estado=A" -Headers $headers
$cursos.data | Format-Table id, nombre, nivel, precio_mensual

# 4. Inscribir en curso
$cursoId = 5  # Seleccionado de la lista

$nuevaInscripcion = @{
    alumno_id = $alumnoId
    curso_id = $cursoId
    fecha_inscripcion = (Get-Date -Format 'yyyy-MM-dd')
    precio_acordado = 120.00
    forma_pago = 'MENSUAL'
    estado = 'A'
} | ConvertTo-Json

$inscripcionResp = Invoke-RestMethod -Uri "$baseUrl/inscripciones" -Method POST -Headers $headers -Body $nuevaInscripcion -ContentType 'application/json'

Write-Host "✓ Inscripción creada: ID $($inscripcionResp.data.id)"
```

### Workflow: Pasar Lista de Asistencia

```powershell
# 1. Listar sesión de hoy
$hoy = Get-Date -Format 'yyyy-MM-dd'
$params = @{
    curso_id = 5
    fecha = $hoy
}
$queryString = ($params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join '&'

$sesiones = Invoke-RestMethod -Uri "$baseUrl/sesiones?$queryString" -Headers $headers
$sesionId = $sesiones.data[0].id

Write-Host "Sesión de hoy: ID $sesionId"

# 2. Listar inscripciones del curso
$inscripciones = Invoke-RestMethod -Uri "$baseUrl/inscripciones?curso_id=5&estado=A" -Headers $headers

# 3. Registrar asistencia de cada alumno
foreach ($inscripcion in $inscripciones.data) {
    $asistenciaBody = @{
        inscripcion_id = $inscripcion.id
        sesion_id = $sesionId
        asistio = $true  # Cambiar según asistencia real
    } | ConvertTo-Json
    
    Invoke-RestMethod -Uri "$baseUrl/sesiones/$sesionId/asistencias" -Method POST -Headers $headers -Body $asistenciaBody -ContentType 'application/json'
    
    Write-Host "✓ Asistencia registrada: $($inscripcion.alumno_nombre)"
}

Write-Host "✓ Lista de asistencia completada"
```

### Workflow: Reporte de Asistencias de un Alumno

```powershell
# 1. Obtener inscripciones del alumno
$alumnoId = 10
$inscripciones = Invoke-RestMethod -Uri "$baseUrl/inscripciones?alumno_id=$alumnoId" -Headers $headers

foreach ($inscripcion in $inscripciones.data) {
    Write-Host "`nCurso: $($inscripcion.curso_nombre)"
    
    # 2. Obtener asistencias de la inscripción
    $asistencias = Invoke-RestMethod -Uri "$baseUrl/asistencias?inscripcion_id=$($inscripcion.id)" -Headers $headers
    
    $total = $asistencias.data.Count
    $asistio = ($asistencias.data | Where-Object { $_.asistio -eq $true }).Count
    $porcentaje = if ($total -gt 0) { ($asistio / $total) * 100 } else { 0 }
    
    Write-Host "  Total sesiones: $total"
    Write-Host "  Asistió: $asistio"
    Write-Host "  Porcentaje: $([math]::Round($porcentaje, 2))%"
}
```

---

## Recursos Adicionales

- [Autenticación JWT](AUTH.md) - Login, logout, refresh
- [Sistema de Permisos](PERMISSIONS.md) - Autorización
- [Guía de Desarrollo](DEVELOPMENT.md) - Setup y debugging
- [Workflow OpenAPI](OPENAPI_WORKFLOW.md) - Generación de specs
