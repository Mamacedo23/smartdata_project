# smartdata_project

Pipeline de ingeniería de datos construido sobre **Azure Databricks** con **Unity Catalog**, implementando la **Arquitectura Medallion** (Bronze → Silver → Gold) para el procesamiento incremental de ventas, productos y personas.

---

## Arquitectura

```
Azure Data Lake Storage (ADLS)          Federated SQL Catalog
   abfss://raw/.../sales/              (dim_products, dim_persons)
           │                                       │
           └──────────────┬────────────────────────┘
                          ▼
                   [ Bronze Layer ]
                  Autoloader + MERGE
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
     Silver Sales   Silver Persons  Silver Products
    (limpiezas +   (limpiezas +    (limpiezas +
     validaciones)  validaciones)   validaciones)
           │              │              │
           ▼              ▼              ▼
      Gold Sales     Gold Persons   Gold Products
     (SCD + merge)  (SCD + merge)  (SCD + merge)
           └──────────────┼──────────────┘
                          ▼
               [ dbt — Snapshot Materialization ]
               (SCD Type 2 sobre Unity Catalog)
```

---

## Estructura del repositorio

```
smartdata_project/
│
├── proceso/                        # Notebooks del pipeline principal
│   ├── 0.Preparacion_Ambiente      # Setup de catalogs, schemas y volumes
│   ├── 1.Bronze_Ingestion          # Ingestión incremental (Autoloader + MERGE)
│   ├── 1.Silver_transform_products # Transformación y calidad — productos
│   ├── 2.Silver_transform_persons  # Transformación y calidad — personas
│   ├── 3.Silver_transform_sales    # Transformación y calidad — ventas
│   ├── 1.Gold_Load_products        # Carga Gold — productos
│   ├── 2.Gold_Load_persons         # Carga Gold — personas
│   ├── 3.Gold_Load_sales           # Carga Gold — ventas
│   ├── drop_medallion              # Utilidad: elimina capas medallion
│   └── grants_medallion            # Utilidad: asigna permisos sobre capas
│
├── reversion/                      # Notebooks para revertir el ambiente
│   ├── drop_medallion
│   └── grants_medallion
│
├── seguridad/                      # Notebooks de gestión de permisos
│   ├── drop_medallion
│   └── grants_medallion
│
├── PrepAmb/                        # Notebook standalone de preparación
│   └── 0.Preparacion_Ambiente
│
├── datasets/                       # Archivos CSV diarios de ventas
│   └── fact_sales_YYYY-MM-DD.csv   # 2025-01-01 → 2026-03-30 (~454 archivos)
│
├── watermarks.json                 # Control de marcas de agua por dominio
└── .github/workflows/
    └── deploy_notebook.yml         # CI/CD: deploy automático a Databricks
```

---

## Capas del Medallion

### Bronze — Ingestión incremental
- **Ventas**: ingesta con **Autoloader** (`cloudFiles`) desde ADLS, detectando archivos CSV nuevos por llegada. Resultado en `bronze_sales`.
- **Productos y Personas**: lectura desde **federated SQL catalog** con MERGE incremental usando watermark por fecha. Resultados en `bronze_products` y `bronze_persons`.
- Las marcas de agua se controlan vía `watermarks.json` y se propagan como task values al resto del workflow.

### Silver — Transformación y calidad
- Limpieza de tipos, estandarización de fechas y validaciones de integridad.
- Deduplificación y manejo de registros nulos o inconsistentes.
- Escritura incremental sobre tablas Delta con MERGE.

### Gold — Capa analítica
- Tablas optimizadas para consumo analítico y BI.
- Integración de cambios históricos (SCD).
- Escritura con MERGE sobre tablas Delta en el schema `gold`.

### dbt — Snapshot Materialization
- Tarea final del workflow que ejecuta `dbt snapshot` para materializar **Slowly Changing Dimensions (SCD Type 2)** sobre Unity Catalog.
- Fuente del proyecto dbt: [smart_data_dbt](https://github.com/Mamacedo23/smart_data_dbt)

---

## Dataset de ventas

Archivos diarios con el esquema:

| Campo | Descripción |
|---|---|
| `sales_id` | Identificador único de la venta |
| `created_at` | Fecha y hora de creación |
| `end_at` | Fecha y hora de cierre |
| `status` | Estado de la transacción |
| `product_id` | FK a dimensión de productos |
| `customer_id` | FK a dimensión de personas/clientes |
| `quantity` | Cantidad vendida |
| `sales_subtotal` | Monto subtotal |
| `updated_at` | Última actualización |
| `medio_de_pago` | Método de pago (transferencia, etc.) |
| `bank_origin` | Banco origen del pago |

Cobertura: **2025-01-01 → 2026-03-30** (~454 archivos)

---

## Unity Catalog

| Schema | Propósito |
|---|---|
| `raw` | Volume de Autoloader para archivos en tránsito |
| `bronze` | Datos ingestados sin transformar |
| `silver` | Datos limpios y validados |
| `gold` | Datos listos para análisis |

Catálogo: `smartdata_project`
Storage: `abfss://raw@adlssmartdataeastus2001.dfs.core.windows.net/`

---

## CI/CD — GitHub Actions

El workflow `.github/workflows/deploy_notebook.yml` se dispara en cada push a `main` y ejecuta los siguientes pasos:

1. **Export** — exporta los notebooks del workspace origen en formato DBC.
2. **Deploy** — importa los notebooks al workspace destino bajo `/Workspace/smartdata_project/proceso/`.
3. **Delete & Recreate Workflow** — elimina el workflow anterior `smartdata_project_prod` si existe y lo crea de nuevo con la configuración actualizada.
4. **Run** — ejecuta el workflow inmediatamente tras el despliegue.
5. **Monitor** — monitorea el estado de la ejecución con polling cada 30s (timeout: 10 min).

Credenciales requeridas en GitHub Secrets:

| Secret | Descripción |
|---|---|
| `DATABRICKS_ORIGIN_HOST` | URL del workspace origen |
| `DATABRICKS_ORIGIN_TOKEN` | Token PAT del workspace origen |
| `DATABRICKS_DEST_HOST` | URL del workspace destino (producción) |
| `DATABRICKS_DEST_TOKEN` | Token PAT del workspace destino |

---

## Databricks Workflow — `smartdata_project_prod`

El workflow usa **compute Serverless** y se dispara automáticamente por **file arrival** en ADLS.

```
PrepAmb
  └── Bronze_ingestion
        ├── Silver_Sales ──── Gold_Sales ──┐
        ├── Silver_persons ── Gold_Persons ─┤── Snapshot_Materialization (dbt)
        └── Silver_products ─ Gold_products ┘
```

- Timeout máximo: 2 horas
- Notificaciones por email en éxito y fallo a `kevin.gonzales.m@uni.pe`
- Performance target: `PERFORMANCE_OPTIMIZED`
