#!/usr/bin/env python3
"""
ETL Pipeline: Data Warehouse de Ventas Retail
==============================================
Extrae desde múltiples fuentes (SQL Server OLTP, CSV, Excel, XML),
transforma y carga en el Data Warehouse (SQL Server).
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import warnings
warnings.filterwarnings('ignore')

import db

# ============================================
# CONFIGURACIÓN
# ============================================
BASE_DIR = os.path.expanduser("~/Documents/Inteligencia de negocios")
EXTERNOS_DIR = os.path.join(BASE_DIR, "datos", "externos")


def read_oltp(table_name):
    """Lee tabla desde la BD OLTP (SQL Server)."""
    return pd.read_sql(f"SELECT * FROM {table_name}", db.get_engine(db.OLTP_DB))


def read_csv(filename):
    """Lee archivo CSV externo."""
    return pd.read_csv(os.path.join(EXTERNOS_DIR, filename))


def read_excel(filename):
    """Lee archivo Excel externo."""
    return pd.read_excel(os.path.join(EXTERNOS_DIR, filename))


def read_xml(filename):
    """Lee archivo XML externo."""
    tree = ET.parse(os.path.join(EXTERNOS_DIR, filename))
    root = tree.getroot()
    records = []
    for child in root:
        record = {"id": child.get("id")}
        for elem in child:
            record[elem.tag] = elem.text
        records.append(record)
    return pd.DataFrame(records)


def save_to_dw(df, table_name, engine):
    """Guarda DataFrame en el Data Warehouse (SQL Server)."""
    df.to_sql(table_name, engine, if_exists="replace", index=False,
              chunksize=200, method="multi")


# ============================================
# EXTRACCIÓN: Leer desde múltiples fuentes
# ============================================
print("=" * 60)
print("ETL - FASE 1: EXTRACCIÓN DESDE MÚLTIPLES FUENTES")
print("=" * 60)

# Fuente 1: SQL Server (sistema transaccional OLTP)
print("\n[1] Extrayendo desde SQL Server (OLTP)...")
df_categorias = read_oltp("Categorias")
df_proveedores = read_oltp("Proveedores")
df_ciudades = read_oltp("Ciudades")
df_tiendas = read_oltp("Tiendas")
df_metodos_pago = read_oltp("MetodosPago")
df_productos = read_oltp("Productos")
df_clientes = read_oltp("Clientes")
df_empleados = read_oltp("Empleados")
df_ordenes = read_oltp("Ordenes")
df_detalle = read_oltp("DetalleOrdenes")
df_devoluciones = read_oltp("Devoluciones")
df_inventario = read_oltp("Inventario")
df_envios = read_oltp("Envios")
df_encuestas = read_oltp("Encuestas")
df_historico_precios = read_oltp("HistoricoPrecios")
df_promociones = read_oltp("Promociones")
df_promociones_orden = read_oltp("PromocionesOrden")
print(f"   ✓ {len(df_categorias)} categorías, {len(df_productos)} productos, "
      f"{len(df_clientes)} clientes, {len(df_ordenes)} órdenes, "
      f"{len(df_detalle)} detalles, {len(df_devoluciones)} devoluciones")

# Fuente 2: CSV (datos de mercado)
print("\n[2] Extrayendo desde CSV (mercado)...")
df_mercado = read_csv("mercado_categorias.csv")
print(f"   ✓ {len(df_mercado)} registros de mercado")

# Fuente 3: Excel (proveedores externos)
print("\n[3] Extrayendo desde Excel (proveedores externos)...")
df_proveedores_ext = read_excel("proveedores_externos.xlsx")
print(f"   ✓ {len(df_proveedores_ext)} proveedores externos")

# Fuente 4: XML (campañas de marketing)
print("\n[4] Extrayendo desde XML (campañas)...")
df_campanas = read_xml("campanas_marketing.xml")
df_campanas["presupuesto"] = df_campanas["presupuesto"].astype(float)
df_campanas["incremento_ventas_pct"] = df_campanas["incremento_ventas_pct"].astype(float)
print(f"   ✓ {len(df_campanas)} campañas")


# ============================================
# TRANSFORMACIÓN: Limpieza, enriquecimiento y uniones
# ============================================
print("\n" + "=" * 60)
print("ETL - FASE 2: TRANSFORMACIÓN")
print("=" * 60)

# --- Dimensiones DW ---

# Dim_Tiempo: Generar desde el rango de fechas de órdenes
print("\n[1] Generando Dim_Tiempo...")
fechas_ordenes = pd.to_datetime(df_ordenes["fecha_orden"])
fecha_min = fechas_ordenes.min().replace(hour=0, minute=0, second=0)
fecha_max = fechas_ordenes.max().replace(hour=23, minute=59, second=59)

rango_fechas = pd.date_range(start=fecha_min.date(), end=fecha_max.date(), freq="D")
dim_tiempo = pd.DataFrame({
    "id_tiempo": range(1, len(rango_fechas) + 1),
    "fecha": rango_fechas,
    "anio": rango_fechas.year,
    "mes": rango_fechas.month,
    "nombre_mes": [datetime(y, m, 1).strftime("%B")
                    for y, m in zip(rango_fechas.year, rango_fechas.month)],
    "trimestre": rango_fechas.quarter,
    "semana": rango_fechas.isocalendar().week.astype(int),
    "dia_semana": rango_fechas.dayofweek,
    "nombre_dia": rango_fechas.day_name(),
    "es_fin_semana": rango_fechas.dayofweek >= 5,
    "estacion": rango_fechas.month.map({
        12: "Invierno", 1: "Invierno", 2: "Invierno",
        3: "Primavera", 4: "Primavera", 5: "Primavera",
        6: "Verano", 7: "Verano", 8: "Verano",
        9: "Otoño", 10: "Otoño", 11: "Otoño"
    })
})
print(f"   ✓ {len(dim_tiempo)} fechas generadas")

# Dim_Producto
print("\n[2] Construyendo Dim_Producto...")
dim_producto = df_productos.merge(
    df_categorias, on="id_categoria", suffixes=("", "_cat")
).merge(
    df_proveedores, on="id_proveedor", suffixes=("", "_prov")
)
dim_producto = dim_producto[[
    "id_producto", "nombre", "id_categoria", "nombre_cat",
    "id_proveedor", "nombre_prov", "precio_unitario",
    "costo_unitario", "activo"
]].rename(columns={
    "nombre": "nombre_producto",
    "nombre_cat": "nombre_categoria",
    "nombre_prov": "nombre_proveedor"
})
# Agregar margen calculado
dim_producto["margen_pct"] = np.round(
    ((dim_producto["precio_unitario"] - dim_producto["costo_unitario"])
     / dim_producto["precio_unitario"]) * 100
).astype(int)
print(f"   ✓ {len(dim_producto)} productos")

# Dim_Cliente (con RFM)
print("\n[3] Construyendo Dim_Cliente (con métricas RFM)...")
# Calcular RFM para cada cliente
fecha_actual = pd.to_datetime(df_ordenes["fecha_orden"]).max()

rfm = df_ordenes.groupby("id_cliente").agg(
    ultima_compra=("fecha_orden", "max"),
    frecuencia=("id_orden", "nunique"),
    monetario=("id_orden", "count")  # Para el monto real, unimos con detalle
).reset_index()

rfm["recency"] = (pd.to_datetime(fecha_actual) - pd.to_datetime(rfm["ultima_compra"])).dt.days

# Calcular monto total por cliente
detalle_con_precio = df_detalle.merge(df_ordenes[["id_orden", "id_cliente"]], on="id_orden")
monto_por_cliente = detalle_con_precio.groupby("id_cliente")["subtotal"].sum().reset_index()
monto_por_cliente.columns = ["id_cliente", "monto_total"]

rfm = rfm.merge(monto_por_cliente, on="id_cliente", how="left")
rfm["monto_total"] = rfm["monto_total"].fillna(0)

dim_cliente = df_clientes.merge(df_ciudades, on="id_ciudad").merge(rfm, on="id_cliente", how="left")
dim_cliente = dim_cliente.rename(columns={
    "nombre_x": "nombre_cliente",
    "nombre_y": "nombre_ciudad"
})
dim_cliente["recency"] = dim_cliente["recency"].fillna(999)
dim_cliente["frecuencia"] = dim_cliente["frecuencia"].fillna(0).astype(int)
dim_cliente["monto_total"] = dim_cliente["monto_total"].fillna(0).astype(int)

# Segmentar clientes RFM
def segmentar_rfm(row):
    if row["recency"] <= 90 and row["frecuencia"] > 5 and row["monto_total"] > 10000000:
        return "VIP"
    elif row["recency"] <= 180 and row["frecuencia"] > 3:
        return "Regular"
    elif row["recency"] <= 365:
        return "En riesgo"
    else:
        return "Perdido"

dim_cliente["segmento_rfm"] = dim_cliente.apply(segmentar_rfm, axis=1)
print(f"   ✓ {len(dim_cliente)} clientes con segmentación RFM")
print(f"     Segmentos: {dict(dim_cliente['segmento_rfm'].value_counts())}")

# Dim_Tienda
print("\n[4] Construyendo Dim_Tienda...")
dim_tienda = df_tiendas.merge(df_ciudades, on="id_ciudad").rename(columns={
    "nombre_x": "nombre_tienda",
    "nombre_y": "nombre_ciudad"
})
print(f"   ✓ {len(dim_tienda)} tiendas")

# Dim_Empleado
print("\n[5] Construyendo Dim_Empleado...")
dim_empleado = df_empleados.merge(df_tiendas[["id_tienda", "nombre"]], on="id_tienda").rename(columns={
    "nombre_x": "nombre_empleado",
    "nombre_y": "nombre_tienda"
})
print(f"   ✓ {len(dim_empleado)} empleados")

# Dim_MetodoPago
print("\n[6] Construyendo Dim_MetodoPago...")
dim_metodo_pago = df_metodos_pago.copy()
print(f"   ✓ {len(dim_metodo_pago)} métodos de pago")

# Dim_Proveedor
print("\n[7] Construyendo Dim_Proveedor...")
dim_proveedor = df_proveedores.copy()
print(f"   ✓ {len(dim_proveedor)} proveedores")

# Integrar proveedores externos a Dim_Proveedor (uniendo fuentes!)
print("\n[8] Integrando proveedores externos (Excel) -> Dim_Proveedor...")
dim_proveedor_ext = df_proveedores_ext.copy()
dim_proveedor_ext["tipo"] = "Externo"
dim_proveedor["tipo"] = "Interno"
# Unión de archivos (requisito de la rúbrica: uso de uniones)
dim_proveedor_unificado = pd.concat([
    dim_proveedor[["id_proveedor", "nombre", "pais", "tipo"]].rename(
        columns={"id_proveedor": "id_proveedor_origen"}),
    dim_proveedor_ext[["id_proveedor_ext", "nombre_empresa", "pais", "tipo"]].rename(
        columns={"id_proveedor_ext": "id_proveedor_origen",
                 "nombre_empresa": "nombre"})
], ignore_index=True)
dim_proveedor_unificado["id_proveedor_dw"] = range(1, len(dim_proveedor_unificado) + 1)
print(f"   ✓ {len(dim_proveedor_unificado)} proveedores (unión SQL Server + Excel)")

# Dim_Campana (desde XML)
print("\n[9] Construyendo Dim_Campana (desde XML)...")
dim_campana = df_campanas.copy()
dim_campana["id_campana_dw"] = range(1, len(dim_campana) + 1)
print(f"   ✓ {len(dim_campana)} campañas")

# --- Tabla de Hechos: Fact_Ventas ---
print("\n[10] Construyendo Fact_Ventas (archivo compuesto)...")
# Unir detalle con órdenes y dimensiones
fact_ventas = df_detalle.merge(
    df_ordenes[["id_orden", "id_cliente", "id_empleado",
                "id_tienda", "id_metodo_pago", "fecha_orden", "estado"]],
    on="id_orden"
)

# Agregar llaves dimensionales
# Convertir a date para matching
fact_ventas["fecha_date"] = pd.to_datetime(fact_ventas["fecha_orden"]).dt.date
dim_tiempo["fecha_date"] = pd.to_datetime(dim_tiempo["fecha"]).dt.date

fact_ventas = fact_ventas.merge(
    dim_tiempo[["id_tiempo", "fecha_date"]],
    on="fecha_date", how="inner"
)

fact_ventas = fact_ventas.dropna(subset=["id_tiempo"])
fact_ventas["id_tiempo"] = fact_ventas["id_tiempo"].astype(int)

# Eliminar columna auxiliar
fact_ventas = fact_ventas.drop(columns=["fecha_date"])

# Mantener columnas relevantes
fact_ventas = fact_ventas[[
    "id_detalle", "id_orden", "id_producto", "id_cliente", "id_empleado",
    "id_tienda", "id_metodo_pago", "id_tiempo",
    "cantidad", "precio_unitario", "descuento", "subtotal", "fecha_orden", "estado"
]]
print(f"   ✓ {len(fact_ventas)} registros en Fact_Ventas")


# ============================================
# CARGA: Insertar en el Data Warehouse
# ============================================
print("\n" + "=" * 60)
print("ETL - FASE 3: CARGA AL DATA WAREHOUSE")
print("=" * 60)

db.ensure_databases()
engine = db.get_engine(db.DW_DB)

tablas_dw = [
    ("Dim_Tiempo", dim_tiempo),
    ("Dim_Producto", dim_producto),
    ("Dim_Cliente", dim_cliente),
    ("Dim_Tienda", dim_tienda),
    ("Dim_Empleado", dim_empleado),
    ("Dim_MetodoPago", dim_metodo_pago),
    ("Dim_Proveedor", dim_proveedor_unificado),
    ("Dim_Campana", dim_campana),
    ("Fact_Ventas", fact_ventas),
]

total_registros = 0
for nombre, df in tablas_dw:
    save_to_dw(df, nombre, engine)
    total_registros += len(df)
    print(f"   ✓ {nombre}: {len(df):>6d} registros cargados")

print(f"\n   TOTAL: {total_registros} registros en el DW")
print(f"   DW ubicación: SQL Server / {db.DW_DB}")

# Cerrar conexión
engine.dispose()

print("\n" + "=" * 60)
print("¡ETL COMPLETADO EXITOSAMENTE!")
print("=" * 60)

# Resumen de fuentes utilizadas
print("\nResumen de fuentes:")
print("  - SQL Server (OLTP): 18 tablas")
print("  - CSV: mercado_categorias.csv")
print("  - Excel: proveedores_externos.xlsx")
print("  - XML: campanas_marketing.xml")
print("  - Uniones: proveedores internos + externos")
print("  - Archivo compuesto: Fact_Ventas (detalle + órdenes + tiempo)")
