#!/usr/bin/env python3
"""Exportar datos del DW a CSV para PowerBI Desktop."""

import sys
import pandas as pd
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "etl"))
import db

EXPORT_DIR = os.path.join(BASE, "dashboard")
os.makedirs(EXPORT_DIR, exist_ok=True)

conn = db.connect(db.DW_DB)

tablas = [
    "Dim_Tiempo",
    "Dim_Producto",
    "Dim_Cliente",
    "Dim_Tienda",
    "Dim_Empleado",
    "Dim_MetodoPago",
    "Dim_Proveedor",
    "Dim_Campana",
    "Fact_Ventas",
]

print("Exportando datos para Power BI...")
for tabla in tablas:
    try:
        df = pd.read_sql(f"SELECT * FROM {tabla}", conn)
        filename = os.path.join(EXPORT_DIR, f"{tabla}.csv")
        df.to_csv(filename, index=False, encoding="utf-8")
        print(f"  {tabla}.csv — {len(df)} registros")
    except Exception as e:
        print(f"  {tabla} — ERROR: {e}")

conn.close()

print(f"\nArchivos exportados a: {EXPORT_DIR}")
print("""
=== INSTRUCCIONES POWERBI ===
1. Abrir Power BI Desktop
2. Get Data → Text/CSV → seleccionar cada .csv
3. En Model View, crear relaciones:
   - Fact_Ventas.id_tiempo → Dim_Tiempo.id_tiempo
   - Fact_Ventas.id_producto → Dim_Producto.id_producto
   - Fact_Ventas.id_cliente → Dim_Cliente.id_cliente
   - Fact_Ventas.id_tienda → Dim_Tienda.id_tienda
   - Fact_Ventas.id_empleado → Dim_Empleado.id_empleado
   - Fact_Ventas.id_metodo_pago → Dim_MetodoPago.id_metodo_pago
4. Crear medidas DAX:
   Total Ventas = SUM(Fact_Ventas[subtotal])
   Transacciones = DISTINCTCOUNT(Fact_Ventas[id_orden])
   KPI Crecimiento YoY = DIVIDE([Total Ventas] - CALCULATE([Total Ventas], SAMEPERIODLASTYEAR(Dim_Tiempo[fecha])), CALCULATE([Total Ventas], SAMEPERIODLASTYEAR(Dim_Tiempo[fecha])))
   Margen Promedio = AVERAGE(Dim_Producto[margen_pct])
5. Diseñar dashboard:
   - Tarjetas: Total Ventas, Transacciones, KPI Crecimiento, Margen Promedio
   - Línea: Ventas por Mes (Trend)
   - Barras: Ventas por Categoría
   - Mapa: Ventas por Ciudad
   - Tabla: Top 10 Productos
""")
