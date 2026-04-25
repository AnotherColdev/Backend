# Backend — Plataforma Analítica Territorial

Plataforma de microservicios para el análisis territorial de datos geoespaciales y sociodemográficos.

---

## Tabla de Contenidos

- [Arquitectura General](#arquitectura-general)
- [Microservicios](#microservicios)
- [HU-20: Normalización Avanzada (ms-transformation)](#hu-20-normalización-avanzada-ms-transformation)
  - [Descripción de los Cambios](#descripción-de-los-cambios)
  - [Arquitectura del Pipeline](#arquitectura-del-pipeline)
  - [Endpoint: Transformación Avanzada](#endpoint-transformación-avanzada)
  - [Modelos de Datos](#modelos-de-datos)
  - [Detalle del Pipeline](#detalle-del-pipeline)
- [Guía de Pruebas](#guía-de-pruebas)
  - [Prueba General Integral](#prueba-general-integral)
  - [Pruebas Específicas por Funcionalidad](#pruebas-específicas-por-funcionalidad)
- [Configuración y Despliegue](#configuración-y-despliegue)

---

## Arquitectura General

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Frontend   │────▶│  Gateway    │────▶│  ms-ingestion    │
│  (Vite)     │     │  :8000      │     │  :8001           │
└─────────────┘     │             │     └──────────────────┘
                    │             │     ┌──────────────────┐
                    │             │────▶│  ms-audit-trace  │
                    │             │     │  :8002           │
                    │             │     └──────────────────┘
                    │             │     ┌──────────────────┐
                    │             │────▶│ ms-configuration │
                    │             │     │  :8003           │
                    │             │     └──────────────────┘
                    │             │     ┌──────────────────────┐
                    │             │────▶│ ms-transformation    │
                    │             │     │  :8004 (HU-20) ★     │
                    │             │     └──────────────────────┘
                    │             │     ┌──────────────────┐
                    │             │────▶│  ms-analytics    │
                    │             │     │  :8005           │
                    └─────────────┘     └──────────────────┘
                                        ┌──────────────────┐
                                        │  PostgreSQL      │
                                        │  territorial_db  │
                                        └──────────────────┘
```

---

## Microservicios

| Servicio | Puerto | Descripción |
|---|---|---|
| **Gateway** | 8000 | BFF / Proxy API con autenticación |
| **ms-ingestion** | 8001 | Ingesta y validación de datasets |
| **ms-audit-trace** | 8002 | Trazabilidad y auditoría |
| **ms-configuration** | 8003 | Configuración dinámica |
| **ms-transformation** | 8004 | **Transformación y normalización avanzada (HU-20) ★** |
| **ms-analytics** | 8005 | Scoring y ranking territorial |
| **ms-auth** | 8006 | Autenticación y autorización |

---

## HU-20: Normalización Avanzada (ms-transformation)

### Descripción de los Cambios

La **HU-20** evoluciona el microservicio `ms-transformation` de un skeleton básico a un **motor estadístico completo** que implementa:

| Funcionalidad | Descripción | Estado |
|---|---|---|
| **Limpieza de datos** | Imputación por mediana, deduplicación por zone_code, estandarización de zone_name | ✅ Preservado de HU-07 |
| **Detección de Outliers** | Identifica valores que superan ±3 desviaciones estándar | ✅ Nuevo |
| **Winsorización** | Capa outliers al percentil 1 y 99 (sin eliminar registros) | ✅ Nuevo |
| **Normalización Min-Max** | `(x - min) / (max - min)` → valores en [0, 1] | ✅ Nuevo |
| **Normalización Z-Score** | `(x - μ) / σ` → media ≈ 0, desviación ≈ 1 | ✅ Nuevo |
| **Reporte Estadístico** | min, max, mean, std, null_count, outliers_count por columna | ✅ Nuevo |
| **Persistencia** | Resultados almacenados en schema `transformation` | ✅ Nuevo |

### Arquitectura del Pipeline

```
          ┌─────────────────────────┐
          │  POST /api/v1/transform │
          │       /advanced         │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  1. Validar dataset     │
          │  (estado = VALID)       │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  2. Cargar CSV/JSON     │
          │  desde storage          │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  3. LIMPIEZA            │
          │  • Imputación mediana   │
          │  • Dedup zone_code      │
          │  • Estandarizar names   │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  4. OUTLIERS            │
          │  • Detectar ±3σ         │
          │  • Winsorizar P1/P99    │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  5. NORMALIZACIÓN       │
          │  • Min-Max ó Z-Score    │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  6. REPORTE             │
          │  • Stats por columna    │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  7. PERSISTIR           │
          │  • transformation_runs  │
          │  • transformed_records  │
          └────────┬────────────────┘
                   │
          ┌────────▼────────────────┐
          │  8. RESPUESTA           │
          │  • TransformResponse    │
          └─────────────────────────┘
```

### Endpoint: Transformación Avanzada

#### `POST /api/v1/transform/advanced`

**Descripción**: Ejecuta el pipeline completo de limpieza, detección de outliers, normalización y generación de reporte estadístico sobre un dataset previamente ingestado.

**Acceso vía Gateway**: `POST http://localhost:8000/api/v1/transformation/api/v1/transform/advanced`

**Acceso directo al servicio**: `POST http://localhost:8004/api/v1/transform/advanced`

---

#### Estructura del Request (Body JSON)

```json
{
  "dataset_load_id": "abc123def456",
  "method": "zscore"
}
```

| Campo | Tipo | Requerido | Default | Descripción |
|---|---|---|---|---|
| `dataset_load_id` | string | ✅ | — | ID del dataset cargado por ms-ingestion (`datasetId`) |
| `method` | string | ❌ | `"minmax"` | Método de normalización: `"minmax"` o `"zscore"` |

---

#### Estructura de la Respuesta (200 OK)

```json
{
  "success": true,
  "run_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "dataset_load_id": "abc123def456",
  "method": "zscore",
  "status": "COMPLETED",
  "records_input": 10,
  "records_output": 10,
  "rules_applied": {
    "method": "zscore",
    "total_columns_processed": 4,
    "columns_processed": ["population", "income_index", "education_score", "health_index"],
    "statistics": {
      "population": {
        "min": -1.456789,
        "max": 1.789012,
        "mean": 0.000000,
        "std": 1.000000,
        "null_count": 0,
        "outliers_count": 1
      },
      "income_index": {
        "min": -1.234567,
        "max": 1.567890,
        "mean": 0.000000,
        "std": 1.000000,
        "null_count": 0,
        "outliers_count": 0
      }
    }
  },
  "created_at": "2026-04-25T03:30:00.000000"
}
```

| Campo | Tipo | Descripción |
|---|---|---|
| `success` | bool | `true` si la transformación fue exitosa |
| `run_id` | string | UUID único de esta ejecución |
| `dataset_load_id` | string | ID del dataset procesado |
| `method` | string | Método utilizado (`minmax` o `zscore`) |
| `status` | string | Estado: `COMPLETED` o `FAILED` |
| `records_input` | int | Registros de entrada (antes de limpieza) |
| `records_output` | int | Registros de salida (después de limpieza) |
| `rules_applied` | object | **Reporte estadístico completo** (ver abajo) |
| `created_at` | datetime | Timestamp de la ejecución |

---

#### Estructura de `rules_applied`

```json
{
  "method": "zscore",
  "total_columns_processed": 4,
  "columns_processed": ["col1", "col2", ...],
  "statistics": {
    "<nombre_columna>": {
      "min": 0.0,
      "max": 1.0,
      "mean": 0.5,
      "std": 0.3,
      "null_count": 0,
      "outliers_count": 2
    }
  }
}
```

---

#### Respuestas de Error

| Código | Causa | Ejemplo |
|---|---|---|
| `400` | Dataset no está en estado VALID | `{"error": true, "message": "El dataset tiene estado 'UPLOADED'..."}` |
| `404` | Dataset no encontrado | `{"error": true, "message": "Dataset con ID 'xxx' no encontrado."}` |
| `422` | Método de normalización inválido | `{"detail": [{"msg": "Método 'abc' no válido..."}]}` |

---

### Modelos de Datos

#### Tabla `transformation.transformation_runs`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | VARCHAR (PK) | UUID de la ejecución |
| `dataset_load_id` | VARCHAR | FK lógica al dataset de ingestion |
| `method` | VARCHAR(10) | `"minmax"` o `"zscore"` |
| `status` | VARCHAR(20) | `PROCESSING`, `COMPLETED`, `FAILED` |
| `rules_applied` | JSON | Reporte estadístico completo |
| `records_input` | INTEGER | Registros de entrada |
| `records_output` | INTEGER | Registros de salida |
| `created_at` | TIMESTAMP | Fecha de creación |

#### Tabla `transformation.transformed_records`

| Columna | Tipo | Descripción |
|---|---|---|
| `id` | VARCHAR (PK) | UUID del registro |
| `run_id` | VARCHAR (FK) | Referencia a `transformation_runs.id` |
| `zone_code` | VARCHAR(50) | Código de la zona |
| `zone_name` | VARCHAR(255) | Nombre estandarizado de la zona |
| `column_name` | VARCHAR(100) | Nombre de la variable numérica |
| `original_value` | FLOAT | Valor original (post-capado) |
| `normalized_value` | FLOAT | Valor normalizado |

---

### Detalle del Pipeline

#### 1. Limpieza (preservada de HU-07)

| Paso | Descripción | Detalle |
|---|---|---|
| Imputación | Rellena nulos numéricos | Usa la **mediana** de cada columna |
| Deduplicación | Elimina duplicados por `zone_code` | Conserva el **último** registro (más reciente) |
| Estandarización | Normaliza `zone_name` | Aplica `strip()` + `title()` (ej: "  chapinero " → "Chapinero") |

#### 2. Detección de Outliers

- **Criterio**: Un valor es outlier si `|x - μ| > 3σ` (3 desviaciones estándar)
- **Acción**: Los outliers son **capados** (Winsorización), NO eliminados
- **Rango de capado**:
  - Valores extremos superiores → se capa al **percentil 99**
  - Valores extremos inferiores → se capa al **percentil 1**
- **Reporte**: Se cuenta el número de outliers detectados por columna

#### 3. Normalización Min-Max

```
valor_normalizado = (x - min) / (max - min)
```

- Produce valores estrictamente entre **0.0 y 1.0**
- Si `max == min` (columna constante), el valor se establece en **0.0**

#### 4. Normalización Z-Score

```
valor_normalizado = (x - μ) / σ
```

- Produce valores con **media ≈ 0** y **desviación estándar ≈ 1**
- Si `σ == 0` (columna constante), el valor se establece en **0.0**

---

### Selección Configurable de Reglas

El motor estadístico permite al consumidor elegir dinámicamente qué regla de normalización aplicar enviando el campo opcional `method` en el body del request. 

* **`"method": "minmax"` (Valor por defecto)**: Ideal para escenarios donde todos los indicadores deben estar confinados a una misma escala matemática de [0, 1]. Útil cuando se necesita crear índices compuestos simples o rangos de visualización de semáforos (Rojo/Amarillo/Verde).
* **`"method": "zscore"`**: Ideal para análisis estadístico profundo donde interesa conocer qué tan "lejos de la media" está un indicador. Valores muy positivos indican desempeños excepcionales por encima del promedio, y valores negativos indican rezago relativo. Útil para clustering o machine learning.

---

### Persistencia y Verificación de Datos

Una decisión arquitectónica clave del microservicio es que **NO sobrescribe el archivo original ni genera un nuevo archivo físico (CSV/Excel)**. 

Toda la salida de la transformación se persiste mediante un modelo de "registro largo" (*melted format*) directamente en PostgreSQL, lo que resulta ideal para analítica, trazabilidad y para ser consumido posteriormente por `ms-analytics`.

Para confirmar manualmente el éxito del procesamiento "celda por celda" sin alterar la estructura del proyecto, puedes verificar directamente la base de datos.

#### Consultar resultados vía Docker
Puedes ejecutar este comando en tu terminal para obtener una muestra rápida del antes y el después de la transformación (asegúrate de que los contenedores estén encendidos):

```bash
docker exec -i transformation_postgres psql -U postgres -d territorial_db -c "SELECT zone_code, column_name, original_value, ROUND(normalized_value::numeric, 4) as normalized FROM transformation.transformed_records LIMIT 20;"
```

**Estructura de Almacenamiento:**
* `transformation_runs`: Almacena la metadatos del request y el JSON completo del reporte estadístico (resumen de outliers, mín/máx, desviaciones).
* `transformed_records`: Almacena celda por celda.
    * `original_value`: Valor tras imputar vacíos y capar outliers, pero antes de aplicar la regla matemática de normalización.
    * `normalized_value`: El valor numérico final (Min-Max o Z-Score).

---

## Guía de Pruebas

### Prerrequisitos

1. Tener Docker y Docker Compose instalados
2. Ejecutar todos los servicios:
   ```bash
   docker-compose up --build
   ```
3. Verificar que los servicios estén corriendo:
   ```bash
   curl http://localhost:8000/api/v1/transformation/health
   ```

### Prueba General Integral (Aislada)

Para evitar dependencias con otros microservicios durante el desarrollo de **Transformation**, se ha aislado su configuración y suite de pruebas dentro de su propio directorio.

1. Navega al directorio del microservicio:
   ```bash
   cd transformation
   ```
2. Levanta únicamente este microservicio y su base de datos local:
   ```bash
   docker-compose up --build -d
   ```
3. Ejecuta el script de pruebas aislado:
   ```bash
   python tests/test_advanced_transformation.py
   ```

**El script automáticamente:**

1. ✅ Inyecta un dataset CSV con 10 zonas y un outlier extremo (population=99,999,999)
2. ✅ Ejecuta transformación Z-Score y verifica:
   - Outlier fue detectado y capado
   - Estadísticas contienen min, max, mean, std, null_count, outliers_count
   - Media ≈ 0 y desviación ≈ 1 para todas las columnas
3. ✅ Ejecuta transformación Min-Max y verifica:
   - Todos los valores están entre 0.0 y 1.0
4. ✅ Prueba casos de error (dataset inexistente, método inválido)

---

### Pruebas Específicas por Funcionalidad

#### Prueba 1: Selección de Método de Normalización

```bash
# Min-Max (default)
curl -X POST http://localhost:8004/api/v1/transform/advanced \
  -H "Content-Type: application/json" \
  -d '{"dataset_load_id": "<DATASET_ID>"}'

# Z-Score
curl -X POST http://localhost:8004/api/v1/transform/advanced \
  -H "Content-Type: application/json" \
  -d '{"dataset_load_id": "<DATASET_ID>", "method": "zscore"}'
```

**Verificar**: La respuesta contiene `"method": "minmax"` o `"method": "zscore"` respectivamente.

#### Prueba 2: Detección y Capado de Outliers

1. Subir un CSV con un valor extremo (ej: `population=99999999`)
2. Ejecutar la transformación
3. **Verificar** en `rules_applied.statistics.population`:
   - `outliers_count > 0`
   - El registro con el outlier **no fue eliminado** (`records_output == records_input` post-dedup)

#### Prueba 3: Reporte Estadístico por Columna

```bash
curl -X POST http://localhost:8004/api/v1/transform/advanced \
  -H "Content-Type: application/json" \
  -d '{"dataset_load_id": "<DATASET_ID>", "method": "zscore"}'
```

**Verificar** que cada columna en `rules_applied.statistics` contiene:
```json
{
  "min": <número>,
  "max": <número>,
  "mean": <número>,
  "std": <número>,
  "null_count": <entero>,
  "outliers_count": <entero>
}
```

#### Prueba 4: Verificación Z-Score (media ≈ 0, std ≈ 1)

Después de ejecutar con `method="zscore"`, verificar para cada columna:
- `mean` debe estar cercano a **0** (tolerancia ±0.1)
- `std` debe estar cercano a **1** (tolerancia ±0.15)

#### Prueba 5: Verificación Min-Max ([0, 1])

Después de ejecutar con `method="minmax"`, verificar para cada columna:
- `min >= 0.0`
- `max <= 1.0`

#### Prueba 6: Validación de Dataset

```bash
# Dataset inexistente → 404
curl -X POST http://localhost:8004/api/v1/transform/advanced \
  -H "Content-Type: application/json" \
  -d '{"dataset_load_id": "FAKE-ID"}'

# Método inválido → 422
curl -X POST http://localhost:8004/api/v1/transform/advanced \
  -H "Content-Type: application/json" \
  -d '{"dataset_load_id": "any-id", "method": "invalid"}'
```

---

## Configuración y Despliegue

### Variables de Entorno (ms-transformation)

| Variable | Default | Descripción |
|---|---|---|
| `POSTGRES_USER` | `postgres` | Usuario de PostgreSQL |
| `POSTGRES_PASSWORD` | `admin` | Contraseña de PostgreSQL |
| `POSTGRES_HOST` | `db_postgres` | Host de PostgreSQL |
| `POSTGRES_PORT` | `5432` | Puerto de PostgreSQL |
| `POSTGRES_DB` | `territorial_db` | Base de datos |
| `STORAGE_PATH` | `/app/storage` | Directorio de almacenamiento de archivos |

### Estructura de Archivos (ms-transformation)

```
transformation/
├── .env                          # Variables de entorno
├── Dockerfile                    # Imagen Docker
├── requirements.txt              # Dependencias Python
└── app/
    ├── main.py                   # FastAPI app + endpoint
    ├── core/
    │   ├── __init__.py
    │   ├── config.py             # Configuración (Settings)
    │   ├── database.py           # Engine + SessionLocal + init_db
    │   └── exceptions.py         # DomainException + handler
    ├── models/
    │   ├── __init__.py
    │   └── models.py             # TransformationRun + TransformedRecord
    ├── schemas/
    │   ├── __init__.py
    │   └── schemas.py            # TransformRequest + TransformResponse
    └── services/
        ├── __init__.py
        └── transformation_service.py  # Pipeline completo
```

### Documentación Swagger

Una vez el servicio esté corriendo, accede a:
- **Swagger UI**: http://localhost:8004/docs
- **ReDoc**: http://localhost:8004/redoc