"""
Consolida los CSV del DW en un único Excel (una hoja por tabla) para subirlo
fácilmente a Power BI (web o Desktop). Convierte las columnas de fecha a tipo
datetime para que Power BI las reconozca como fechas.
"""

import os
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, "Dataset_PowerBI.xlsx")

# Tablas a incluir (nombre de hoja -> archivo CSV)
TABLAS = [
    "Fact_Ventas", "Dim_Tiempo", "Dim_Producto", "Dim_Cliente",
    "Dim_Tienda", "Dim_Empleado", "Dim_MetodoPago", "Dim_Proveedor",
    "Dim_Campana",
]

# Columnas que deben interpretarse como fecha
COLS_FECHA = {
    "fecha", "fecha_date", "fecha_orden", "fecha_registro", "ultima_compra",
    "fecha_contratacion", "inicio", "fin",
}

with pd.ExcelWriter(SALIDA, engine="openpyxl", datetime_format="yyyy-mm-dd") as xw:
    for nombre in TABLAS:
        ruta = os.path.join(BASE, f"{nombre}.csv")
        df = pd.read_csv(ruta)
        for col in df.columns:
            if col in COLS_FECHA:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        # Las hojas de Excel admiten máximo 31 caracteres en el nombre
        df.to_excel(xw, sheet_name=nombre[:31], index=False)
        print(f"  hoja '{nombre}': {len(df):>6} filas, {len(df.columns)} columnas")

print(f"\nExcel generado: {SALIDA}")
