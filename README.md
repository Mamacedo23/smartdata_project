# Job ETL de Retail en Databricks + CI/CD + Dbt

Arquitectura Medallion en Azure Databricks

Pipeline automatizado de datos para el análisis de ventas por producto, canal de pago y cliente, implementando una arquitectura de tres capas con despliegue continuo y materialización de dimensiones históricas.

---

## 🎯 Descripción

Pipeline ETL que transforma datos crudos de ventas diarias, catálogos de productos y registros de personas, implementando la **Arquitectura Medallion (Bronze → Silver → Gold)** en Azure Databricks con Unity Catalog, CI/CD completo vía GitHub Actions y Delta Lake para garantizar consistencia ACID. La capa final incluye materialización de **SCD Type 2** mediante dbt.

---

## ✨ Características Principales

* 🔄 **ETL Automatizado** — Pipeline completo con despliegue automático vía GitHub Actions en cada push a `main`
* 🏗️ **Arquitectura Medallion** — Separación clara de capas Bronze → Silver → Gold
* 📦 **Ingestión Incremental** — Autoloader con `cloudFiles` para ventas y MERGE con watermarks para productos y personas
* 📸 **SCD Type 2** — Materialización de snapshots históricos mediante dbt sobre Unity Catalog
* ⚡ **Delta Lake** — Transacciones ACID, time travel y merge incremental en todas las capas
* 🔐 **Unity Catalog** — Gobierno de datos centralizado con permisos gestionados por notebooks
* 🚀 **Serverless Compute** — Workflow optimizado con `PERFORMANCE_OPTIMIZED` y trigger por llegada de archivos
* 📧 **Monitoreo** — Notificaciones automáticas por email en éxito y fallo

---

## 🏛️ Arquitectura

![Arquitectura Medallion](imagenes/smartdata_project_arquitectura.drawio.png)

---

## 📁 Estructura del Repositorio

```
smartdata_project/
│
├── proceso/                         # Notebooks del pipeline principal
│   ├── 0.Preparacion_Ambiente       # Setup de catalogs, schemas y volumes
│   ├── 1.Bronze_Ingestion           # Ingestión incremental (Autoloader + MERGE)
│   ├── 1.Silver_transform_products  # Transformación y calidad — productos
│   ├── 2.Silver_transform_persons   # Transformación y calidad — personas
│   ├── 3.Silver_transform_sales     # Transformación y calidad — ventas
│   ├── 1.Gold_Load_products         # Carga Gold — productos
│   ├── 2.Gold_Load_persons          # Carga Gold — personas
│   ├── 3.Gold_Load_sales            # Carga Gold — ventas
│   ├── drop_medallion               # Utilidad: elimina capas medallion
│   └── grants_medallion             # Utilidad: asigna permisos sobre capas
│
├── reversion/                       # Notebooks para revertir el ambiente
├── seguridad/                       # Notebooks de gestión de permisos
├── PrepAmb/                         # Notebook standalone de preparación
│
├── datasets/                        # Archivos CSV diarios de ventas
│   └── fact_sales_YYYY-MM-DD.csv    # 2025-01-01 → 2026-03-30 (~454 archivos)
│
├── watermarks.json                  # Marcas de agua por dominio (sales, persons, products)
└── .github/workflows/
    └── deploy_notebook.yml          # CI/CD: deploy automático a Databricks
```

---

## 🗂️ Capas del Pipeline

### 🟤 Bronze — Ingestión incremental

| Dominio | Fuente | Mecanismo | Tabla destino |
|---|---|---|---|
| Ventas | ADLS `abfss://raw/.../sales/` | Autoloader (`cloudFiles`) | `bronze_sales` |
| Productos | `federated_sql_catalog.source.dim_products` | MERGE + watermark | `bronze_products` |
| Personas | `federated_sql_catalog.source.dim_persons` | MERGE + watermark | `bronze_persons` |

Las marcas de agua se propagan como **task values** al resto del workflow vía `watermarks.json`.

### 🥈 Silver — Transformación y calidad

- Limpieza de tipos y estandarización de fechas
- Validaciones de integridad y deduplicación
- Escritura incremental sobre tablas Delta con MERGE

### 🥇 Gold — Capa analítica

- Tablas optimizadas para consumo analítico y BI
- Escritura con MERGE incremental sobre tablas Delta en schema `gold`

### 📸 dbt — Snapshot Materialization

- Ejecuta `dbt snapshot` sobre Unity Catalog para materializar **SCD Type 2**
- Proyecto dbt externo: [smart_data_dbt](https://github.com/Mamacedo23/smart_data_dbt)

---

## 📊 Dataset de Ventas

Archivos diarios `fact_sales_YYYY-MM-DD.csv` con cobertura **2025-01-01 → 2026-03-30** (~454 archivos):

| Campo | Descripción |
|---|---|
| `sales_id` | Identificador único de la venta |
| `created_at` | Fecha y hora de creación |
| `end_at` | Fecha y hora de cierre |
| `status` | Estado de la transacción |
| `product_id` | FK → dimensión de productos |
| `customer_id` | FK → dimensión de clientes |
| `quantity` | Cantidad vendida |
| `sales_subtotal` | Monto subtotal |
| `updated_at` | Última actualización del registro |
| `medio_de_pago` | Método de pago (Transferencia bancaria, etc.) |
| `bank_origin` | Banco origen (Scotiabank, Interbank, etc.) |

---

## ⚙️ Instalación y Configuración

### 1️⃣ Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/smartdata_project
cd smartdata_project
```

### 2️⃣ Generar Tokens PAT en Databricks

Para ambos workspaces (origen y destino):

1. Ir al Databricks Workspace
2. **User Settings** → **Developer** → **Access Tokens**
3. Click en **Generate New Token**
4. Configurar:
   - **Comment**: `GitHub CI/CD`
   - **Lifetime**: `90 days`
5. ⚠️ Copiar y guardar el token generado

### 3️⃣ Configurar GitHub Secrets

En el repositorio: **Settings** → **Secrets and variables** → **Actions**

| Secret | Descripción |
|---|---|
| `DATABRICKS_ORIGIN_HOST` | URL del workspace origen (ej. `https://adb-xxxxx.azuredatabricks.net`) |
| `DATABRICKS_ORIGIN_TOKEN` | Token PAT del workspace origen |
| `DATABRICKS_DEST_HOST` | URL del workspace destino / producción |
| `DATABRICKS_DEST_TOKEN` | Token PAT del workspace destino |

### 4️⃣ Verificar Unity Catalog

El pipeline opera sobre el catálogo `smartdata_project` con la siguiente estructura:

| Schema | Propósito |
|---|---|
| `raw` | Volume de Autoloader para archivos en tránsito |
| `bronze` | Datos ingestados sin transformar |
| `silver` | Datos limpios y validados |
| `gold` | Datos listos para análisis |

Storage: `abfss://raw@adlssmartdataeastus2001.dfs.core.windows.net/`

✅ **¡Configuración completa!**

---

## 💻 Uso

### 🚀 Despliegue Automático (Recomendado)

```bash
git add .
git commit -m "feat: mejoras en pipeline"
git push origin main
```

**GitHub Actions ejecutará automáticamente**:
- 📤 Export de notebooks del workspace origen en formato DBC
- 📥 Deploy de notebooks a `/Workspace/smartdata_project/proceso`
- 🔁 Eliminación y recreación del workflow `smartdata_project_prod`
- ▶️ Ejecución completa: PrepAmb → Bronze → Silver → Gold → dbt
- 📧 Notificaciones de resultado por email

### 🔧 Ejecución Local en Databricks

Navegar a `/Workspace/smartdata_project/proceso` y ejecutar en orden:

```
- 0.Preparacion_Ambiente         → Setup del ambiente
- 1.Bronze_Ingestion             → Bronze Layer
- 1.Silver_transform_products    → Silver Layer — productos
- 2.Silver_transform_persons     → Silver Layer — personas
- 3.Silver_transform_sales       → Silver Layer — ventas
- 1.Gold_Load_products           → Gold Layer  — productos
- 2.Gold_Load_persons            → Gold Layer  — personas
- 3.Gold_Load_sales              → Gold Layer  — ventas
```

---

## 🔄 CI/CD

### Pipeline de GitHub Actions

```
Workflow: Dynamic Databricks Notebook Deploy
├── Checkout del repositorio
├── Export de notebooks desde workspace origen (formato DBC)
├── Deploy de notebooks al workspace destino
├── Eliminar workflow antiguo (si existe)
├── Crear workflow smartdata_project_prod (Serverless)
├── Ejecutar pipeline automáticamente
└── Monitorear ejecución y notificar resultado
```

---

## 🛠️ Workflow Databricks — `smartdata_project_prod`

```
PrepAmb
  └── Bronze_ingestion
        ├── Silver_Sales ──── Gold_Sales ──┐
        ├── Silver_persons ── Gold_Persons ─┤── Snapshot_Materialization (dbt)
        └── Silver_products ─ Gold_products ┘
```

- ⚡ **Compute**: Serverless (`PERFORMANCE_OPTIMIZED`)
- 🔔 **Trigger**: File Arrival en `abfss://raw@adlssmartdataeastus2001.dfs.core.windows.net/sales/`
- ⏱️ **Timeout máximo**: 2 horas
- 🔁 **Max concurrent runs**: 1
- 📧 **Notificaciones**: éxito y fallo vía email

---

## 📈 Monitoreo

### En Databricks

**Workflows**:
- Ir a **Workflows** en el menú lateral
- Buscar `smartdata_project_prod`
- Ver historial de ejecuciones y estado por tarea

**Logs por Tarea**:
- Click en una ejecución específica
- Click en cada tarea para ver logs detallados
- Revisar stdout/stderr en caso de errores

### En GitHub Actions

- Tab **Actions** del repositorio
- Ver historial de workflows y logs por step
- El step **Monitor Workflow Execution** reporta el estado en tiempo real con polling cada 30s

---

## 👤 Autor

**Kevin Gonzales Muñoz**

[![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:kevin.gonzales.m@uni.pe)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=for-the-badge&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/kevin-jose-gonzales-macedo-9a771420a/)
[![Phone](https://img.shields.io/badge/Phone-25D366?style=for-the-badge&logo=whatsapp&logoColor=white)](tel:+51942886274)

**Data Engineering** | **Azure Databricks** | **Delta Lake** | **Unity Catalog** | **CI/CD**

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

**Proyecto**: Data Engineering — Arquitectura Medallion  
**Tecnología**: Azure Databricks + Delta Lake + Unity Catalog + dbt + GitHub Actions
