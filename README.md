# Proyecto Final — Inteligencia de Negocios

Solución completa de **Inteligencia de Negocios** sobre un caso de *retail de tecnología*:
generación de un dataset transaccional, proceso **ETL** multi-fuente hacia un **Data
Warehouse** (esquema estrella), análisis **OLAP**, cálculo de **KPIs**, técnicas de
**minería de datos** y un **dashboard en Power BI**.

Todo el proyecto se ejecuta sobre **SQL Server** (un único motor) con scripts en Python.

---

## 1. Estructura del repositorio

```
.
├── etl/                         # Generación de datos y proceso ETL
│   ├── db.py                    # Conexión centralizada a SQL Server
│   ├── generar_dataset.py       # Crea el dataset OLTP (SQL Server + CSV/Excel/XML)
│   ├── etl_pipeline.py          # Extrae de 4 fuentes y carga el Data Warehouse
│   └── etl_scd_cubo.py          # Dimensiones SCD y construcción del cubo
├── analisis/                    # Análisis y figuras del informe
│   ├── generar_diagramas.py     # Diagramas ER, esquema estrella y flujo ETL
│   ├── olap_cubo.py             # Consultas OLAP (roll-up, drill-down, slice, dice)
│   ├── kpis.py                  # KPIs (crecimiento YoY, margen por categoría)
│   ├── mineria_datos.py         # Clustering, churn, Naive Bayes, Apriori, etc.
│   └── graficos/                # Figuras .png generadas (usadas por el informe)
├── dashboard/                   # Insumos para Power BI
│   ├── exportar_powerbi.py      # Exporta el DW a CSV
│   ├── consolidar_excel.py      # Consolida los CSV en un único Excel
│   ├── *.csv                    # Dimensiones + tabla de hechos
│   └── Dataset_PowerBI.xlsx     # Dataset consolidado para Power BI
├── datos/externos/              # Fuentes externas del ETL (CSV, Excel, XML)
├── docs/
│   ├── Informe_Final_BI.md      # Informe final (con las figuras incrustadas)
│   ├── Guia_PowerBI.md          # Guía paso a paso para armar el dashboard
│   └── Guion_Sustentacion.md    # Guion para la sustentación
├── Entregable.pbix              # Dashboard de Power BI
├── requirements.txt
└── README.md
```

---

## 2. Requisitos previos

- **Python 3.12 o superior** (probado con 3.14)
- **Docker** (para levantar SQL Server)

---

## 3. Instalación

```bash
# 1. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
```

---

## 3. Levantar SQL Server

Todos los scripts se conectan a SQL Server (configuración en `etl/db.py`). Levanta una
instancia con Docker:

```bash
docker run -e "ACCEPT_EULA=Y" -e "MSSQL_SA_PASSWORD=TuPassword123!" \
  -p 1433:1433 --name sqlserver-bi -d \
  mcr.microsoft.com/mssql/server:2022-latest
```

> El password debe coincidir con el de `etl/db.py` (`TuPassword123!`). Las bases
> `RetailOLTP` y `RetailDW` se crean automáticamente al ejecutar los scripts.

---

## 4. Ejecución paso a paso

Ejecuta los scripts **en este orden** (con el entorno virtual activo):

```bash
# --- 1. Generar el dataset transaccional (OLTP) ---
python etl/generar_dataset.py

# --- 2. ETL: extraer de las 4 fuentes y cargar el Data Warehouse ---
python etl/etl_pipeline.py
python etl/etl_scd_cubo.py

# --- 3. Análisis y figuras del informe ---
python analisis/generar_diagramas.py     # diagramas de arquitectura
python analisis/olap_cubo.py             # consultas OLAP
python analisis/kpis.py                  # KPIs
python analisis/mineria_datos.py         # minería de datos

# --- 4. Exportar datos para el dashboard de Power BI ---
python dashboard/exportar_powerbi.py
python dashboard/consolidar_excel.py
```


-

---

