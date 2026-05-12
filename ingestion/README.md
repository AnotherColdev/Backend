# Microservicio de Ingesta (ms-ingestion)

Este microservicio se encarga de la recepción, validación y persistencia inicial de los datasets territoriales cargados en la plataforma.

## 📋 Responsabilidades

1.  **Recepción de archivos**: Soporte para formatos `.csv` y `.json`.
2.  **Validación de Dominio**:
    *   Verificación de columnas requeridas (`zone_code`, `zone_name`).
    *   Detección de variables numéricas (mínimo 3 requeridas para análisis posterior).
    *   Control de nulos (máximo 30% permitido en columnas clave).
    *   Validación de duplicidad de contenido vía Hash (SHA256).
3.  **Extracción Geográfica**: Identificación de códigos de zona y departamentos para el catálogo territorial.
4.  **Almacenamiento**: Persistencia física de archivos en volumen compartido (`/app/storage`).

---

## 🛠 Especificaciones Técnicas

- **Framework**: FastAPI
- **Procesamiento de Datos**: Pandas
- **Base de Datos**: PostgreSQL (Esquema `ingestion`)
- **ORM**: SQLAlchemy

---

## 🚀 Endpoints Principales

### `POST /datasets/upload`
Carga un nuevo dataset al sistema.
- **Parámetros (Form)**:
    - `file`: Archivo CSV/JSON.
    - `sourceName` (Opcional): Nombre descriptivo de la fuente de datos.
    - `sourceType` (Opcional): Categoría de la fuente (ej. Salud, Educación).
- **Respuesta**: Objeto `DatasetLoad` con el `datasetId` generado.

### `GET /datasets/`
Lista todos los cargues realizados con sus estadísticas básico.

### `GET /datasets/zones`
Consulta el catálogo de zonas (municipios/departamentos) extraídos de los datasets.

---

## 🏗 Convenciones de Código

- El servicio sigue los principios **SOLID**.
- Se utiliza la inyección de dependencias para los repositorios.
- Todos los modelos y esquemas utilizan **camelCase** para sus atributos.
- **Lógica de Zonas**: Se asume que códigos >= 5 dígitos corresponden a municipios colombianos, mientras que códigos de 2 dígitos son departamentos.

---

## 🧪 Pruebas Locales

Para verificar el funcionamiento de la lógica de negocio sin levantar la base de datos:

```bash
# Desde la raíz del microservicio
$env:PYTHONPATH="."; python verify_changes.py
```

---
*Este componente es vital para garantizar la calidad del dato antes de pasar a las fases de transformación y analítica.*
