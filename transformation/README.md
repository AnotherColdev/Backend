# HU-28: Exportación de Resultados — Documentación Técnica

## 1. Resumen de la Implementación

La **HU-28** implementa la funcionalidad de exportación de resultados de análisis territorial desde el **BFF Gateway** (puerto 8000). Permite a los usuarios descargar el ranking de zonas en formato **CSV** y obtener reportes detallados de zonas individuales en formato **JSON**.

### Criterios de Aceptación Cubiertos

| Criterio | Estado |
|----------|--------|
| CSV con encabezados en español y una fila por zona | ✅ Implementado |
| JSON de reporte incluye indicadores, score, predicción, combined_score y recomendación | ✅ Implementado |
| Descarga directa desde el navegador (sin página intermedia) | ✅ StreamingResponse |
| Solo se pueden exportar análisis COMPLETED | ✅ Middleware de validación |
| Evento de exportación registrado en ms-audit-trace | ✅ BackgroundTasks |
| CSV compatible con Excel/LibreOffice con UTF-8 | ✅ BOM + delimitador `;` |

---

## 2. Detalle de Modificaciones

### Archivos Creados

#### `Backend/gateway/app/services/export_service.py`
**Responsabilidad**: Servicio principal de exportación (SRP).

- `fetchRankingData(executionId)` — Obtiene todos los datos de ranking desde `ms-analytics` con paginación interna automática.
- `fetchZoneIndicators(zoneCode)` — Consulta el endpoint `/api/v1/zone-summary/{zone_code}` de `ms-analytics`.
- `validateExecutionStatus(executionId)` — Valida que la ejecución esté en estado `COMPLETED` consultando `ms-analytics`. Rechaza estados `IN_PROGRESS`, `NOT_FOUND` y otros.
- `generateRankingCsv(rankingData)` — Genera el archivo CSV en memoria (`io.StringIO`) con:
  - Codificación **UTF-8 con BOM** (`\ufeff`) para compatibilidad con Excel.
  - Delimitador `;` (punto y coma) para locales internacionales.
  - Encabezados: `Zona`, `Indicadores`, `Score`, `Nivel`, `Recomendación`.
- `buildZoneReport(zoneCode)` — Construye el reporte JSON completo de una zona con indicadores, score, `combined_score`, predicción y recomendación.

#### `Backend/gateway/app/services/audit_service.py`
**Responsabilidad**: Cliente de auditoría para ms-audit-trace (SRP).

- `sendExportAuditEvent(...)` — Envía un evento de traza al endpoint `POST /api/v1/audit/trace` de `ms-audit-trace`. Implementa patrón fire-and-forget con manejo de errores silencioso para no afectar la respuesta al usuario.

#### `Backend/gateway/app/api/endpoints/export.py`
**Responsabilidad**: Endpoints REST de exportación (SRP).

- `GET /api/v1/export/ranking` — Genera y descarga CSV del ranking.
- `GET /api/v1/export/zone-report/{zone_code}` — Retorna JSON del reporte de zona.
- Incluye extracción automática de `user_id` desde el JWT decodificado.
- Dispara auditoría como `BackgroundTask` (no bloquea la respuesta).

#### `Backend/gateway/tests/test_export.py`
**Responsabilidad**: Suite de pruebas autónomas.

- **Test 1** — Integridad del CSV: parseo, encabezados, filas, UTF-8.
- **Test 2** — Formato de auditoría: valida el schema contra `TraceCreate`.
- **Test 3** — Flujo negativo: rechaza `IN_PROGRESS`, acepta `COMPLETED`.
- **Test 4** — Reporte JSON: campos completos, serialización correcta.

### Archivos Modificados

#### `Backend/gateway/app/main.py`
- **Línea 4**: Agregado import `from app.api.endpoints.export import router as export_router`.
- **Línea 68**: Agregado `app.include_router(export_router, prefix="/api/v1", tags=["export"])`.
- Sin cambios en middlewares ni en el proxy existente.

---

## 3. Requisitos de Ejecución

### Librerías Necesarias

Todas las dependencias ya están incluidas en `Backend/gateway/requirements.txt`:

```
fastapi
uvicorn
httpx
pydantic
pydantic-settings
python-jose[cryptography]==3.3.0
```

> **Nota**: No se requieren librerías adicionales. Los módulos `csv`, `io`, `json` son parte de la librería estándar de Python.

### Variables de Entorno

Las siguientes variables son leídas desde `Backend/gateway/app/core/config.py`:

| Variable | Valor por defecto | Descripción |
|----------|-------------------|-------------|
| `MS_ANALYTICS_URL` | `http://ms-analytics:8005` | URL interna de ms-analytics |
| `MS_AUDIT_TRACE_URL` | `http://ms-audit-trace:8002` | URL interna de ms-audit-trace |
| `SECRET_KEY` | *(definida en .env)* | Clave para decodificar JWT |
| `ALGORITHM` | `HS256` | Algoritmo de JWT |

---

## 4. Guía de Implementación

### Ejecución del Sistema Completo

```bash
# Desde la raíz del proyecto
docker-compose up --build
```

### Ejecución de Pruebas Autónomas

```bash
# Desde Backend/gateway/
set PYTHONIOENCODING=utf-8
python tests/test_export.py
```

### Probar Endpoints con cURL

#### Endpoint 1: Exportar Ranking CSV

```bash
# Obtener token JWT primero
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

# Exportar ranking CSV
curl -X GET "http://localhost:8000/api/v1/export/ranking?execution_id=YOUR_EXEC_ID&format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -o ranking_export.csv

# Verificar el contenido
cat ranking_export.csv
```

**Respuesta exitosa**: Descarga directa del archivo CSV con headers:
- `Content-Disposition: attachment; filename="ranking_XXXXXXXX_TIMESTAMP.csv"`
- `Content-Type: text/csv; charset=utf-8`
- `X-Export-Total-Zones: N`

**Errores posibles**:

| Código | Error | Causa |
|--------|-------|-------|
| 400 | `INVALID_FORMAT` | Se usó un formato diferente a `csv` |
| 401 | `No autenticado` | Falta el token JWT o es inválido |
| 403 | `EXPORT_NOT_ALLOWED` | La ejecución no está en estado COMPLETED |
| 502 | `UPSTREAM_ERROR` | ms-analytics no está disponible |

#### Endpoint 2: Exportar Reporte de Zona JSON

```bash
# Exportar reporte de zona
curl -X GET "http://localhost:8000/api/v1/export/zone-report/BOG-001?format=json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json" | jq .
```

**Respuesta exitosa** (ejemplo):
```json
{
  "zone_code": "BOG-001",
  "zone_name": "Chapinero",
  "indicators": {
    "population_indicator": 0.82,
    "income_indicator": 0.91,
    "education_indicator": 0.88,
    "competition_indicator": 0.45
  },
  "score": {
    "score_value": 0.87,
    "score_level": "ALTA"
  },
  "combined_score": 0.765,
  "prediction": {
    "trend": "ASCENDENTE",
    "confidence": 0.85,
    "projected_level": "ALTA",
    "analysis_note": "Basado en el score combinado de 0.7650..."
  },
  "recommendation": "Zona con alto potencial de inversión...",
  "export_metadata": {
    "format": "json",
    "version": "1.0"
  }
}
```

---

## 5. Lógica y Conexión con Microservicios

### Flujo de Datos — Exportación CSV

```
Frontend (React)
    │
    ▼
BFF Gateway (:8000)
  GET /api/v1/export/ranking?execution_id=xxx&format=csv
    │
    ├──► ms-analytics (:8005)
    │      GET /api/v1/ranking?execution_id=xxx
    │      → Retorna ranking paginado (zonas con score)
    │
    ├──► [Validación] Estado COMPLETED
    │
    ├──► [Generación CSV] io.StringIO → bytes UTF-8+BOM
    │
    ├──► StreamingResponse → Descarga directa al navegador
    │
    └──► [Background] ms-audit-trace (:8002)
           POST /api/v1/audit/trace
           → Registra evento EXPORT_RANKING_CSV
```

### Flujo de Datos — Exportación JSON de Zona

```
Frontend (React)
    │
    ▼
BFF Gateway (:8000)
  GET /api/v1/export/zone-report/{zone_code}?format=json
    │
    ├──► ms-analytics (:8005)
    │      GET /api/v1/zone-summary/{zone_code}
    │      → Retorna indicadores + score de la zona
    │
    ├──► [Enriquecimiento] Predicción + Recomendación + combined_score
    │
    ├──► JSONResponse → Respuesta directa
    │
    └──► [Background] ms-audit-trace (:8002)
           POST /api/v1/audit/trace
           → Registra evento EXPORT_ZONE_REPORT_JSON
```

### Contrato de Auditoría (ms-audit-trace)

El payload enviado a `POST /api/v1/audit/trace` sigue el schema `TraceCreate`:

```json
{
  "dataset_load_id": "execution-uuid",
  "score_execution_id": "execution-uuid",
  "event_type": "EXPORT_RANKING_CSV",
  "status": "success",
  "user_id": "user-id-from-jwt",
  "parameters": {
    "export_format": "csv",
    "export_type": "RANKING_CSV",
    "zone_code": null,
    "timestamp": "2026-05-11T21:00:00Z"
  },
  "result_summary": {
    "total_zones": 12,
    "filename": "ranking_abc12345_20260511_210000.csv"
  }
}
```

---

## 6. Instrucciones para Frontend (React)

### Exportar Ranking CSV

```jsx
// Botón "Exportar CSV" en la página de ranking
const handleExportCsv = async (executionId) => {
  try {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch(
      `http://localhost:8000/api/v1/export/ranking?execution_id=${executionId}&format=csv`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      
      if (response.status === 403) {
        // Análisis no completado
        alert(errorData.detail.message);
        return;
      }
      throw new Error(errorData.detail?.message || 'Error al exportar');
    }

    // Obtener el blob del CSV
    const blob = await response.blob();
    
    // Extraer nombre del archivo del header Content-Disposition
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'ranking_export.csv';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="(.+)"/);
      if (match) filename = match[1];
    }

    // Descargar directamente sin página intermedia
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
  } catch (error) {
    console.error('Error exportando CSV:', error);
    alert('Error al exportar el ranking');
  }
};
```

### Exportar Reporte de Zona JSON

```jsx
// Botón "Exportar JSON" en la card de detalle de zona
const handleExportJson = async (zoneCode) => {
  try {
    const token = localStorage.getItem('access_token');
    
    const response = await fetch(
      `http://localhost:8000/api/v1/export/zone-report/${zoneCode}?format=json`,
      {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Accept': 'application/json',
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail?.message || 'Error al exportar');
    }

    const data = await response.json();
    
    // Descargar como archivo JSON
    const blob = new Blob(
      [JSON.stringify(data, null, 2)],
      { type: 'application/json' }
    );
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `reporte_zona_${zoneCode}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
  } catch (error) {
    console.error('Error exportando JSON:', error);
    alert('Error al exportar el reporte de zona');
  }
};
```

### Manejo de Errores en el Frontend

```jsx
// Interpretar errores del backend
const handleExportError = (response, errorData) => {
  switch (response.status) {
    case 400:
      // Formato inválido o parámetros incorrectos
      return `Error de validación: ${errorData.detail.message}`;
    
    case 401:
      // Token expirado o inválido → redirigir a login
      window.location.href = '/login';
      return 'Sesión expirada. Redirigiendo al login...';
    
    case 403:
      // Ejecución no completada
      // → Deshabilitar botón de exportación en la UI
      return errorData.detail.message;
    
    case 502:
      // Servicio de analítica no disponible
      return 'El servicio de análisis no está disponible. Intente más tarde.';
    
    default:
      return 'Error inesperado al exportar.';
  }
};
```

### Control del Botón de Exportación

```jsx
// Deshabilitar botón si el análisis no está COMPLETED
<button
  onClick={() => handleExportCsv(executionId)}
  disabled={analysisStatus !== 'COMPLETED'}
  className={analysisStatus !== 'COMPLETED' ? 'btn-disabled' : 'btn-export'}
>
  {analysisStatus === 'COMPLETED' ? 'Exportar CSV' : 'Análisis en progreso...'}
</button>
```

---

## 7. Estructura de Archivos Afectados

```
Backend/gateway/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── proxy.py          # Sin cambios
│   │       └── export.py         # [NUEVO] Endpoints de exportación
│   ├── core/
│   │   ├── config.py             # Sin cambios (ya tenía URLs de MS)
│   │   └── auth_middleware.py    # Sin cambios
│   ├── services/
│   │   ├── __init__.py           # Sin cambios
│   │   ├── audit_service.py      # [NUEVO] Cliente de auditoría
│   │   └── export_service.py     # [NUEVO] Lógica de exportación
│   └── main.py                   # [MODIFICADO] +2 líneas (import + router)
├── tests/
│   └── test_export.py            # [NUEVO] Suite de pruebas
└── requirements.txt              # Sin cambios
```

---

## 8. Principios de Diseño Aplicados

| Principio | Aplicación |
|-----------|------------|
| **SRP** | Cada archivo tiene una responsabilidad única: endpoints, servicio de exportación, servicio de auditoría |
| **DIP** | El BFF no accede directamente a la BD; consume APIs de ms-analytics vía HTTP |
| **OCP** | Las recomendaciones y predicciones son extensibles sin modificar la estructura |
| **Clean Code** | Nombres descriptivos en camelCase, docstrings completos, tipado fuerte |
| **Aislamiento** | Cero cambios en Frontend, cero cambios en microservicios de negocio |

---

*Documentación generada para HU-28 — Plataforma de Analítica Territorial*
*Última actualización: 2026-05-11*
