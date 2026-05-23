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
# # Cubo OLAP — Consultas Multidimensionales
#
# Se construye el cubo OLAP sobre las dimensiones Tiempo, Producto, Tienda y
# Cliente, aplicando las operaciones clásicas: roll-up, drill-down, slice, dice
# y pivot. Las medidas incluyen cantidad vendida, ventas totales y margen.

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

# %%
# ============================================
# CUBO OLAP: Ventas por dimensiones
# ============================================
print("=" * 60)
print("CUBO OLAP — VENTAS RETAIL")
print("=" * 60)

# Cargar hecho + dimensiones
fact = pd.read_sql("SELECT * FROM Fact_Ventas", conn)
dim_tiempo = pd.read_sql("SELECT id_tiempo, anio, mes, nombre_mes, trimestre FROM Dim_Tiempo", conn)
dim_producto = pd.read_sql("SELECT id_producto, nombre_producto, nombre_categoria, margen_pct FROM Dim_Producto", conn)
dim_cliente = pd.read_sql("SELECT * FROM Dim_Cliente", conn)
dim_tienda = pd.read_sql("SELECT * FROM Dim_Tienda", conn)

# Unir hecho con dimensiones
cubo = fact.merge(dim_tiempo, on="id_tiempo").merge(
    dim_producto, on="id_producto").merge(
    dim_cliente, on="id_cliente").merge(
    dim_tienda, on="id_tienda")

print(f"Dimensiones cargadas: Tiempo({dim_tiempo['id_tiempo'].nunique()}), "
      f"Producto({dim_producto['id_producto'].nunique()}), "
      f"Cliente({dim_cliente['id_cliente'].nunique()}), "
      f"Tienda({dim_tienda['id_tienda'].nunique()})")
print(f"Medidas: Cantidad, Subtotal (ventas)")
print(f"Filas en el cubo: {len(cubo):,}")

# %% [markdown]
# ### 1.1 Roll-up: Ventas por Año -> Trimestre -> Mes

# %%
print("\n--- ROLL-UP: Ventas por Año -> Trimestre -> Mes ---")
ventas_jerarquia = cubo.groupby(["anio", "trimestre", "mes", "nombre_mes"]).agg(
    ventas=("subtotal", "sum"),
    cantidad=("cantidad", "sum"),
    transacciones=("id_orden", "nunique")
).reset_index()

for anio in sorted(ventas_jerarquia["anio"].unique()):
    print(f"\n{anio}:")
    print(ventas_jerarquia[ventas_jerarquia["anio"] == anio]
          [["trimestre", "nombre_mes", "ventas", "cantidad"]].to_string(index=False))

# Gráfico de ventas mensuales (serie temporal del cubo)
fig, ax = plt.subplots(figsize=(14, 6))
ventas_mensuales = ventas_jerarquia.groupby(["anio", "mes", "nombre_mes"]).agg(
    ventas=("ventas", "sum")
).reset_index()
ventas_mensuales["periodo"] = ventas_mensuales["anio"].astype(str) + "-" + \
                              ventas_mensuales["mes"].astype(str).str.zfill(2)
ax.plot(ventas_mensuales["periodo"], ventas_mensales["ventas"] / 1_000_000,
        marker="o", color="#2196F3", linewidth=2)
ax.set_title("Ventas Mensuales (Cubo OLAP)", fontsize=14, fontweight="bold")
ax.set_ylabel("Millones COP")
ax.tick_params(axis="x", rotation=45)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}M"))
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/01_olap_ventas_mensuales.png", dpi=150)
plt.show()

# %% [markdown]
# ### 1.2 Slice: Ventas solo de la categoría Laptops

# %%
print("\n--- SLICE: Ventas solo de la categoría Laptops ---")
slice_laptops = cubo[cubo["nombre_categoria"] == "Laptops"].groupby("anio").agg(
    ventas=("subtotal", "sum"),
    cantidad=("cantidad", "sum")
).reset_index()
slice_laptops["ventas_mm"] = slice_laptops["ventas"] / 1_000_000
print(slice_laptops.to_string(index=False))

# %% [markdown]
# ### 1.3 Dice: Laptops + Medellín + 2025

# %%
print("\n--- DICE: Laptops + Medellín + 2025 ---")
dice = cubo[(cubo["nombre_categoria"] == "Laptops") &
            (cubo["nombre_ciudad"] == "Medellín") &
            (cubo["anio"] == 2025)].groupby("nombre_mes").agg(
    ventas=("subtotal", "sum"),
    cantidad=("cantidad", "sum")
).reset_index()
print(dice.to_string(index=False))

# %% [markdown]
# ### 1.4 Drill-down: Año > Trimestre > Mes para Gaming

# %%
print("\n--- DRILL-DOWN: Gaming por Año > Trimestre > Mes ---")
drill = cubo[cubo["nombre_categoria"] == "Gaming"].groupby(
    ["anio", "trimestre", "nombre_mes"]
).agg(ventas=("subtotal", "sum")).reset_index()
drill_pivot = drill.pivot_table(
    values="ventas", index=["anio", "trimestre"], columns="nombre_mes", aggfunc="sum"
).fillna(0).astype(int)
print(drill_pivot.to_string())

# %% [markdown]
# ### 1.5 Pivot: Ventas por Categoría x Trimestre (matriz OLAP)

# %%
pivot_cubo = cubo.pivot_table(
    values="subtotal",
    index="nombre_categoria",
    columns="trimestre",
    aggfunc="sum",
    fill_value=0
) / 1_000_000  # en millones

fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(pivot_cubo, annot=True, fmt=".0f", cmap="YlOrRd", ax=ax,
            cbar_kws={"label": "Millones COP"}, linewidths=0.5)
ax.set_title("Cubo OLAP: Matriz de Ventas por Categoría × Trimestre", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/02_olap_matriz_categoria_trimestre.png", dpi=150)
plt.show()

# %% [markdown]
# ---
# # 2. RESUMEN DEL CUBO OLAP

# %%
print("=" * 60)
print("RESUMEN DEL CUBO OLAP")
print("=" * 60)

print(f"""
📊 DATOS DEL CUBO:
   - Registros: {len(cubo):,} (Fact_Ventas unida con 4 dimensiones)
   - Dimensiones: Tiempo, Producto, Cliente, Tienda
   - Período: {cubo['anio'].min()} - {cubo['anio'].max()}
   - Medidas: Cantidad, Subtotal (ventas)

📁 GRÁFICOS GUARDADOS:
   {GRAFICOS_DIR}/
""")

conn.close()
print("✓ Análisis OLAP completado. Gráficos guardados en analisis/graficos/")
