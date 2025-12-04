# 📚 Documentación API para TFG

Este directorio contiene la documentación de la API REST del sistema de gestión de academias, preparada para incluir en el Trabajo Fin de Grado (TFG).

---

## 📄 Archivos para entregar en el TFG

### **Opción recomendada: Documentación interactiva (Swagger UI)**

#### **Archivos necesarios:**
```
📁 ANEXO_B_Especificacion_OpenAPI/
├── API_SWAGGER_STANDALONE_TFG.html  ⭐ PRINCIPAL
├── openapi-auto.json                 ⭐ REQUERIDO (spec)
└── README_DOCUMENTACION_TFG.md       ℹ️  Instrucciones
```

#### **Cómo usar:**
1. **Copiar AMBOS archivos** (`API_SWAGGER_STANDALONE_TFG.html` + `openapi-auto.json`) al mismo directorio
2. Abrir `API_SWAGGER_STANDALONE_TFG.html` en cualquier navegador web
3. ✅ Funciona **100% offline** - No requiere servidor en ejecución

#### **Qué verá el tribunal:**
- ✅ Interfaz Swagger UI profesional
- ✅ Todos los endpoints organizados por recursos
- ✅ Schemas de datos con ejemplos
- ✅ Descripciones completas de cada operación
- ✅ Códigos de respuesta HTTP documentados
- ✅ Información del TFG en la descripción

---

### **Alternativa: Documentación narrativa (para impresión/PDF)**

#### **Archivo:**
```
documentacion-api-completa.html
```

#### **Uso:**
- Abrir en navegador → Imprimir como PDF
- Incluir en memoria principal del TFG (Capítulo 4: API REST)
- Mejor para lectura lineal y explicación detallada

---

## 🎯 Recomendación para el TFG

### **Estructura sugerida:**

```
TFG_AcademiaAPP/
│
├── 📄 Memoria_Principal.pdf
│   └── Capítulo 4: API REST
│       ├── 4.1 Arquitectura
│       ├── 4.2 Endpoints principales (resumen)
│       ├── 4.3 Autenticación JWT
│       └── 4.4 Control de permisos por roles
│
└── 📁 ANEXOS/
    │
    ├── 📁 ANEXO_A_Documentacion_API_Narrativa/
    │   └── documentacion-api-completa.pdf  ← Convertir HTML a PDF
    │
    ├── 📁 ANEXO_B_Especificacion_OpenAPI/  ⭐⭐⭐
    │   ├── API_SWAGGER_STANDALONE_TFG.html
    │   ├── openapi-auto.json
    │   └── README_DOCUMENTACION_TFG.md (este archivo)
    │
    ├── 📁 ANEXO_C_Arquitectura_Android/
    │   ├── ARQUITECTURA_ACADEMIAAPP_ANDROID.html
    │   ├── UX_ACADEMIAAPP_ANDROID.html
    │   └── DIAPOSITIVA_ARQUITECTURA_MVVM.html
    │
    └── 📁 ANEXO_D_Backend_Chat/
        └── (documentación backend-chat si la tienes)
```

---

## 🔍 Comparación de opciones

| Característica | `API_SWAGGER_STANDALONE_TFG.html` | `documentacion-api-completa.html` |
|----------------|-----------------------------------|-----------------------------------|
| **Formato** | Interactivo (Swagger UI) | Narrativo (HTML estático) |
| **Offline** | ✅ Sí (con openapi-auto.json) | ✅ Sí |
| **Imprimible** | ⚠️ Funcional pero no óptimo | ✅ Ideal para PDF |
| **Navegación** | ✅ Filtros, búsqueda, expandir/colapsar | ⚠️ Scroll lineal |
| **Profesional** | ✅✅✅ Estándar industria | ✅✅ Bien documentado |
| **Para defensa** | ✅✅✅ Perfecto para demos en vivo | ✅ Bueno para explicar |
| **Tamaño** | ~2 KB HTML + 150 KB JSON | ~500 KB HTML |

---

## ✅ Checklist para incluir en el TFG

- [ ] Copiar `API_SWAGGER_STANDALONE_TFG.html` a carpeta de anexos
- [ ] Copiar `openapi-auto.json` al **mismo directorio**
- [ ] Verificar que se abre correctamente en navegador (Firefox, Chrome, Edge)
- [ ] Convertir `documentacion-api-completa.html` a PDF (para memoria impresa)
- [ ] Mencionar en la memoria: "Ver ANEXO B para especificación OpenAPI interactiva"
- [ ] Preparar laptop para defensa con el HTML abierto (por si hay preguntas técnicas)

---

## 🎓 Para la defensa del TFG

### **Ventajas de usar Swagger UI:**

1. **Profesionalidad:**
   - "La API está documentada siguiendo el estándar OpenAPI 3.0"
   - Muestra conocimiento de herramientas de la industria

2. **Demostración en vivo:**
   - "Como pueden ver aquí en Swagger, el endpoint `/alumnos` acepta estos parámetros..."
   - Respondes preguntas técnicas mostrando el schema directamente

3. **Validación automática:**
   - Los schemas muestran validaciones (required, format, type)
   - Demuestra rigor técnico sin explicar línea por línea

4. **Generación automática:**
   - "Esta documentación se genera automáticamente desde decoradores Flask-RESTX"
   - Prueba de código bien estructurado y autodocumentado

---

## 📋 Contenido de la especificación OpenAPI

La especificación incluye:

✅ **38 endpoints** documentados:
- `/auth/login` - Autenticación JWT
- `/academias` - Gestión de academias
- `/alumnos` - CRUD completo de alumnos
- `/cursos` - Gestión de cursos
- `/sesiones` - Registro de sesiones y asistencia
- `/matriculas` - Inscripciones de alumnos
- `/usuarios` - Gestión de profesores y roles
- ...y más

✅ **18 schemas de datos** con validación:
- Academia, Alumno, Curso, Usuario, Sesión, etc.
- Cada uno con propiedades, tipos, required, ejemplos

✅ **Códigos de respuesta HTTP** documentados:
- 200 OK
- 201 Created
- 400 Bad Request
- 401 Unauthorized
- 403 Forbidden
- 404 Not Found
- 500 Internal Server Error

✅ **Autenticación JWT** configurada en spec:
- Security scheme: `bearerAuth`
- Endpoints protegidos marcados con candado 🔒

---

## 🛠️ Troubleshooting

### **El archivo no se abre correctamente:**

1. **Verifica que ambos archivos estén juntos:**
   ```
   ✅ API_SWAGGER_STANDALONE_TFG.html
   ✅ openapi-auto.json  ← DEBE estar en el mismo directorio
   ```

2. **Prueba en diferentes navegadores:**
   - ✅ Chrome / Edge (recomendado)
   - ✅ Firefox
   - ⚠️ Safari (puede tener restricciones CORS)

3. **Si ves "Error al cargar especificación":**
   - Abre la consola del navegador (F12)
   - Busca el error específico
   - Verifica que `openapi-auto.json` existe y es válido

### **El "Try it out" no funciona:**

✅ **Esto es normal y esperado**. El botón "Try it out" está **deshabilitado** porque:
- No hay servidor backend corriendo
- El archivo es para documentación, no para pruebas en vivo
- Para el TFG solo necesitas mostrar la **especificación**, no ejecutar llamadas

Si el tribunal pregunta: *"Este documento es para visualizar la estructura de la API. Para pruebas reales, el servidor debe estar corriendo con `python main.py`"*

---

## 📞 Contacto

**Autor:** Ángel Fernández Vidal  
**Proyecto:** TFG FP DAM - Sistema Academia Chat-Driven  
**Centro:** IES Fernando Wirtz Suárez  
**Curso:** 2024-2025  

---

## 📌 Notas adicionales

- ✅ Este documento (`README_DOCUMENTACION_TFG.md`) también puede incluirse en el anexo
- ✅ La especificación OpenAPI es **auto-generada** desde el código Python (Flask-RESTX)
- ✅ Cualquier cambio en los endpoints se refleja automáticamente ejecutando el script de generación
- ✅ Compatible con generadores de código cliente (podría generarse SDK Android/iOS/JavaScript)

---

**¡Éxito en la defensa del TFG! 🎓🚀**
