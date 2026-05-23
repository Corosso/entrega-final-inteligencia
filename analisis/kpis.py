#!/usr/bin/env python3
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#   kernelspec:
#     display_name: 'Python 3'
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Proyecto Final — Inteligencia de Negocios
# # KPIs — Indicadores Clave de Desempeño
#
# Se calculan y visualizan los dos KPIs principales del negocio de retail:
# 1. Crecimiento de ventas año contra año (YoY)
# 2. Margen de ganancia por categoría de producto

# %%
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Configuración
plt.rcParams["figure.figsize"] = (14, 8)
plt.rcParams["figure.dpi"] = 100
sns.set_style("whitegrid")
sns.set_palette("Set2")

BASE = "/home/coro/Documents/Inteligencia de negocios"
GRAFICOS_DIR = f"{BASE}/analisis/graficos"
os.makedirs(GRAFICOS_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE, "etl"))
import db

def conectar_dw():
    return db.connect(db.DW_DB)

conn = conectar_dw()

# Cargar datos desde el Data Warehouse
print("=" * 60)
print("CARGA DE DATOS — DATA WAREHOUSE")
print("=" * 60)

fact = pd.read_sql("SELECT * FROM Fact_Ventas", conn)
dim_tiempo = pd.read_sql("SELECT id_tiempo, anio, mes, nombre_mes, trimestre FROM Dim_Tiempo", conn)
dim_producto = pd.read_sql("SELECT id_producto, nombre_producto, nombre_categoria, margen_pct FROM Dim_Producto", conn)

# Construir cubo (necesario para los KPIs)
cubo = fact.merge(dim_tiempo, on="id_tiempo").merge(
    dim_producto, on="id_producto")

print(f"Ventas totales: ${cubo['subtotal'].sum():,.0f} COP")
print(f"Transacciones (órdenes): {cubo['id_orden'].nunique()}")
print(f"Productos: {cubo['id_producto'].nunique()}")
print(f"Período: {cubo['anio'].min()} - {cubo['anio'].max()}")

# %%
# ============================================
# KPI 1: Crecimiento de Ventas Año contra Año (YoY)
# ============================================
print("=" * 60)
print("KPIs DEL NEGOCIO")
print("=" * 60)

print("\n--- KPI 1: Crecimiento de Ventas YoY ---")
ventas_anuales = cubo.groupby("anio").agg(
    ventas=("subtotal", "sum"),
    ordenes=("id_orden", "nunique")
).reset_index()
ventas_anuales["ventas_mm"] = ventas_anuales["ventas"] / 1_000_000

# Calcular crecimiento YoY
for i in range(1, len(ventas_anuales)):
    crecimiento = ((ventas_anuales.iloc[i]["ventas"] - ventas_anuales.iloc[i-1]["ventas"])
                   / ventas_anuales.iloc[i-1]["ventas"]) * 100
    ventas_anuales.at[i, "crecimiento_yoy_pct"] = round(crecimiento, 1)

print(ventas_anuales[["anio", "ventas_mm", "ordenes", "crecimiento_yoy_pct"]].to_string(index=False))

# Gráfico KPI
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Barras de ventas
bars = ax1.bar(ventas_anuales["anio"], ventas_anuales["ventas_mm"], color=["#4CAF50", "#FFC107", "#2196F3"])
ax1.set_title("KPI 1: Ventas Totales por Año", fontsize=13, fontweight="bold")
ax1.set_ylabel("Millones COP")
for bar, val in zip(bars, ventas_anuales["ventas_mm"]):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, f"{val:.0f}M",
             ha="center", fontweight="bold")

# Crecimiento
colores_crec = ["green" if v > 0 else "red" if v is not None and v < 0 else "gray"
                for v in ventas_anuales["crecimiento_yoy_pct"]]
ax2.bar(ventas_anuales["anio"], ventas_anuales["crecimiento_yoy_pct"], color=colores_crec)
ax2.set_title("Crecimiento YoY (%)", fontsize=13, fontweight="bold")
ax2.set_ylabel("% Crecimiento")
ax2.axhline(y=5, color="green", linestyle="--", alpha=0.5, label="Meta +5%")
ax2.axhline(y=-5, color="red", linestyle="--", alpha=0.5, label="Alerta -5%")
ax2.legend()

plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/03_kpi1_crecimiento_yoy.png", dpi=150)
plt.show()

# %%
# ============================================
# KPI 2: Margen de Ganancia por Categoría
# ============================================
print("\n--- KPI 2: Margen de Ganancia por Categoría ---")
# Calcular costo aproximado (margen = (precio - costo) / precio * 100)
cubo["costo_estimado"] = cubo["subtotal"] * (1 - cubo["margen_pct"] / 100)
margen_categoria = cubo.groupby("nombre_categoria").agg(
    ingresos=("subtotal", "sum"),
    costo_estimado=("costo_estimado", "sum"),
    margen_promedio=("margen_pct", "mean"),
    unidades=("cantidad", "sum")
).reset_index()
margen_categoria["margen_real_pct"] = (
    (margen_categoria["ingresos"] - margen_categoria["costo_estimado"])
    / margen_categoria["ingresos"] * 100
).round(1)

print("\nMargen por categoría:")
print(margen_categoria[["nombre_categoria", "ingresos", "costo_estimado",
                         "margen_real_pct", "unidades"]].to_string(index=False))

# Gráfico KPI
fig, ax = plt.subplots(figsize=(12, 7))
colores_margen = ["#E53935" if m < 10 else "#FFA726" if m < 25 else "#43A047"
                  for m in margen_categoria["margen_real_pct"]]
bars = ax.barh(margen_categoria["nombre_categoria"], margen_categoria["margen_real_pct"],
               color=colores_margen)
ax.set_title("KPI 2: Margen de Ganancia por Categoría (%)", fontsize=14, fontweight="bold")
ax.set_xlabel("Margen (%)")
ax.axvline(x=10, color="red", linestyle="--", alpha=0.5, label="Crítico (<10%)")
ax.axvline(x=25, color="green", linestyle="--", alpha=0.5, label="Meta (>25%)")
for bar, val, ing in zip(bars, margen_categoria["margen_real_pct"],
                          margen_categoria["ingresos"] / 1_000_000):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
            f"{val:.0f}% ({ing:.0f}M)", va="center", fontsize=10)
ax.legend()
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/04_kpi2_margen_categoria.png", dpi=150)
plt.show()

# %%
# ============================================
# RESUMEN DE KPIs
# ============================================
print("=" * 60)
print("RESUMEN DE KPIs")
print("=" * 60)

print(f"""
📈 KPI 1 — Crecimiento de Ventas YoY:
   - Promedio: {ventas_anuales['crecimiento_yoy_pct'].dropna().mean():.1f}%
   - 2024: {ventas_anuales.loc[ventas_anuales['anio']==2024, 'crecimiento_yoy_pct'].values[0]}%
   - 2025: {ventas_anuales.loc[ventas_anuales['anio']==2025, 'crecimiento_yoy_pct'].values[0]}%

📈 KPI 2 — Margen de Ganancia por Categoría:
   - Promedio: {margen_categoria['margen_real_pct'].mean():.1f}%
   - Mayor: {margen_categoria.loc[margen_categoria['margen_real_pct'].idxmax(), 'nombre_categoria']} ({margen_categoria['margen_real_pct'].max():.1f}%)
   - Menor: {margen_categoria.loc[margen_categoria['margen_real_pct'].idxmin(), 'nombre_categoria']} ({margen_categoria['margen_real_pct'].min():.1f}%)

📁 GRÁFICOS GUARDADOS:
   {GRAFICOS_DIR}/
""")

conn.close()
print("✓ KPIs calculados. Gráficos guardados en analisis/graficos/")
