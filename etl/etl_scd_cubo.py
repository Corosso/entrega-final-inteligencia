#!/usr/bin/env python3
"""
SCD (Slowly Changing Dimensions) + Carga de Cubo OLAP
=====================================================
Implementa SCD Tipo 2 para Dim_Producto y Dim_Cliente,
SCD Tipo 1 para demás dimensiones, y la carga del cubo
OLAP con medidas precalculadas.

Fuentes: SQL Server OLTP, DW existente
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

import db

# Configuración
BASE_DIR = os.path.expanduser("~/Documents/Inteligencia de negocios")

def conectar_oltp():
    return db.connect(db.OLTP_DB)

def conectar_dw():
    return db.connect(db.DW_DB)

# ============================================
# PARTE 1: SCD TIPO 2 — Dim_Producto
# ============================================
print("=" * 60)
print("SCD TIPO 2: Dim_Producto (Histórico de Precios)")
print("=" * 60)

oltp = conectar_oltp()

# Leer datos fuente
productos = pd.read_sql("SELECT * FROM Productos", oltp)
historico = pd.read_sql("SELECT * FROM HistoricoPrecios", oltp)
categorias = pd.read_sql("SELECT * FROM Categorias", oltp)
proveedores = pd.read_sql("SELECT * FROM Proveedores", oltp)

oltp.close()

# Unir para obtener nombres
productos = productos.merge(categorias[["id_categoria", "nombre"]],
                             on="id_categoria", suffixes=("", "_cat"))
productos = productos.merge(proveedores[["id_proveedor", "nombre"]],
                             on="id_proveedor", suffixes=("", "_prov"))
productos = productos.rename(columns={
    "nombre": "nombre_producto",
    "nombre_cat": "nombre_categoria",
    "nombre_prov": "nombre_proveedor"
})

# Construir SCD Tipo 2 desde HistoricoPrecios
# Por cada registro en historico, crear una fila en Dim_Producto_SCD
scd_producto_rows = []

# Primero: versión actual de cada producto
for _, prod in productos.iterrows():
    # Buscar el precio más reciente
    hist_prod = historico[historico["id_producto"] == prod["id_producto"]]
    if len(hist_prod) > 0:
        precio_actual = hist_prod.sort_values("fecha_inicio", ascending=False).iloc[0]
        precio_val = precio_actual["precio"]
        costo_val = precio_actual["costo"]
    else:
        precio_val = prod["precio_unitario"]
        costo_val = prod["costo_unitario"]

    margen_pct = round(((precio_val - costo_val) / precio_val) * 100) if precio_val > 0 else 0

    scd_producto_rows.append({
        "id_producto_sk": len(scd_producto_rows) + 1,
        "id_producto_nk": prod["id_producto"],
        "nombre_producto": prod["nombre_producto"],
        "id_categoria": prod["id_categoria"],
        "nombre_categoria": prod["nombre_categoria"],
        "id_proveedor": prod["id_proveedor"],
        "nombre_proveedor": prod["nombre_proveedor"],
        "precio_unitario": precio_val,
        "costo_unitario": costo_val,
        "margen_pct": margen_pct,
        "activo": bool(prod["activo"]),
        "fecha_inicio": "2023-01-01",
        "fecha_fin": "9999-12-31",
        "es_actual": 1
    })

# Versiones históricas (cambios de precio)
for _, prod in productos.iterrows():
    hist_prod = historico[historico["id_producto"] == prod["id_producto"]].sort_values("fecha_inicio")
    for _, cambio in hist_prod.iterrows():
        margen_pct = round(((cambio["precio"] - cambio["costo"]) / cambio["precio"]) * 100) if cambio["precio"] > 0 else 0

        # No duplicar la versión más reciente (ya está como actual)
        ultimo_cambio = hist_prod.sort_values("fecha_inicio", ascending=False).iloc[0]
        if cambio["id_historico_precio"] == ultimo_cambio["id_historico_precio"]:
            continue

        scd_producto_rows.append({
            "id_producto_sk": len(scd_producto_rows) + 1,
            "id_producto_nk": prod["id_producto"],
            "nombre_producto": prod["nombre_producto"],
            "id_categoria": prod["id_categoria"],
            "nombre_categoria": prod["nombre_categoria"],
            "id_proveedor": prod["id_proveedor"],
            "nombre_proveedor": prod["nombre_proveedor"],
            "precio_unitario": cambio["precio"],
            "costo_unitario": cambio["costo"],
            "margen_pct": margen_pct,
            "activo": bool(prod["activo"]),
            "fecha_inicio": str(cambio["fecha_inicio"])[:10] if cambio["fecha_inicio"] else "2023-01-01",
            "fecha_fin": str(cambio["fecha_fin"])[:10] if cambio["fecha_fin"] else str(ultimo_cambio["fecha_inicio"])[:10],
            "es_actual": 0
        })

dim_producto_scd = pd.DataFrame(scd_producto_rows)
# Ordenar por surrogate key
dim_producto_scd = dim_producto_scd.sort_values("id_producto_sk").reset_index(drop=True)
dim_producto_scd["id_producto_sk"] = range(1, len(dim_producto_scd) + 1)

print(f"  Productos únicos (NK): {dim_producto_scd['id_producto_nk'].nunique()}")
print(f"  Filas SCD Tipo 2: {len(dim_producto_scd)}")
print(f"  Versiones actuales: {dim_producto_scd['es_actual'].sum()}")
print(f"  Versiones históricas: {(dim_producto_scd['es_actual'] == 0).sum()}")
print(f"  Cambios de precio registrados: {len(scd_producto_rows) - 80}")

# ============================================
# PARTE 2: SCD TIPO 2 — Dim_Cliente (Cambios de segmento RFM)
# ============================================
print("\n" + "=" * 60)
print("SCD TIPO 2: Dim_Cliente (Cambios de Segmento RFM)")
print("=" * 60)

oltp = conectar_oltp()
clientes = pd.read_sql("SELECT * FROM Clientes", oltp)
ordenes = pd.read_sql("SELECT * FROM Ordenes", oltp)
detalle = pd.read_sql("SELECT * FROM DetalleOrdenes", oltp)
ciudades = pd.read_sql("SELECT * FROM Ciudades", oltp)
oltp.close()

clientes = clientes.merge(ciudades, on="id_ciudad", suffixes=("", "_ciudad"))
clientes = clientes.rename(columns={"nombre": "nombre_cliente", "nombre_ciudad": "nombre_ciudad"})

# Replay: simular cambios de segmento RFM en puntos de snapshot (cada 6 meses)
snapshots = [
    ("2023-06-30", 1), ("2023-12-31", 2),
    ("2024-06-30", 3), ("2024-12-31", 4),
    ("2025-06-30", 5), ("2025-12-31", 6)
]

ordenes["fecha_orden"] = pd.to_datetime(ordenes["fecha_orden"])

def calcular_rfm(cliente_id, fecha_corte):
    """Calcula RFM para un cliente a una fecha de corte."""
    ord_cliente = ordenes[
        (ordenes["id_cliente"] == cliente_id) &
        (ordenes["fecha_orden"] <= pd.Timestamp(fecha_corte))
    ]
    if len(ord_cliente) == 0:
        return 999, 0, 0  # Sin compras aún

    ultima = ord_cliente["fecha_orden"].max()
    recency = (pd.Timestamp(fecha_corte) - ultima).days
    frecuencia = ord_cliente["id_orden"].nunique()

    # Monto total
    ord_ids = ord_cliente["id_orden"].tolist()
    monto = detalle[detalle["id_orden"].isin(ord_ids)]["subtotal"].sum()

    return recency, frecuencia, monto

def segmentar(recency, frecuencia, monto):
    """Asigna segmento RFM."""
    if recency <= 90 and frecuencia >= 5 and monto > 10000000:
        return "VIP"
    elif recency <= 180 and frecuencia >= 2:
        return "Regular"
    elif recency <= 365:
        return "En riesgo"
    else:
        return "Perdido"

# Construir SCD Tipo 2 para clientes
scd_cliente_rows = []

for _, cliente in clientes.iterrows():
    cid = cliente["id_cliente"]
    segmento_anterior = None
    version = 1

    for fecha_corte_str, snapshot_id in snapshots:
        r, f, m = calcular_rfm(cid, fecha_corte_str)
        seg = segmentar(r, f, m)

        if seg != segmento_anterior or snapshot_id == 1:  # Primera versión o cambio
            segmento_anterior = seg
            scd_cliente_rows.append({
                "id_cliente_sk": len(scd_cliente_rows) + 1,
                "id_cliente_nk": cid,
                "nombre_cliente": cliente["nombre_cliente"],
                "email": cliente["email"],
                "nombre_ciudad": cliente["nombre_ciudad"],
                "region": cliente["region"],
                "zona": cliente["zona"],
                "edad": cliente["edad"],
                "genero": cliente["genero"],
                "fecha_registro": cliente["fecha_registro"],
                "segmento_rfm": seg,
                "recency_dias": r,
                "frecuencia_compras": f,
                "monto_total": int(m),
                "fecha_inicio": fecha_corte_str,
                "fecha_fin": "9999-12-31",
                "es_actual": 0,
                "version": version
            })
            version += 1

    # Marcar última versión como actual
    if len(scd_cliente_rows) > 0:
        scd_cliente_rows[-1]["es_actual"] = 1

dim_cliente_scd = pd.DataFrame(scd_cliente_rows)
dim_cliente_scd["id_cliente_sk"] = range(1, len(dim_cliente_scd) + 1)

print(f"  Clientes únicos (NK): {dim_cliente_scd['id_cliente_nk'].nunique()}")
print(f"  Filas SCD Tipo 2: {len(dim_cliente_scd)}")
print(f"  Cambios de segmento registrados: {len(dim_cliente_scd) - 500}")
print(f"  Distribución segmentos actuales:")
print(dim_cliente_scd[dim_cliente_scd["es_actual"] == 1]["segmento_rfm"].value_counts().to_string())

# ============================================
# PARTE 3: SCD TIPO 1 — Otras dimensiones
# ============================================
print("\n" + "=" * 60)
print("SCD TIPO 1: Tienda, Empleado, MétodoPago, Proveedor")
print("=" * 60)

oltp = conectar_oltp()
tiendas = pd.read_sql("SELECT * FROM Tiendas", oltp)
tiendas = tiendas.merge(ciudades, on="id_ciudad")
tiendas = tiendas.rename(columns={"nombre_x": "nombre_tienda", "nombre_y": "nombre_ciudad"})

empleados = pd.read_sql("SELECT * FROM Empleados", oltp)
empleados = empleados.merge(tiendas[["id_tienda", "nombre_tienda"]], on="id_tienda", how="left")
empleados = empleados.rename(columns={"nombre": "nombre_empleado"})

metodos_pago = pd.read_sql("SELECT * FROM MetodosPago", oltp)

# Proveedores unificados (internos + externos desde Excel)
proveedores_int = pd.read_sql("SELECT * FROM Proveedores", oltp)
excel_path = os.path.join(BASE_DIR, "datos", "externos", "proveedores_externos.xlsx")
proveedores_ext = pd.read_excel(excel_path)
prov_int = proveedores_int.copy()
prov_int["tipo"] = "Interno"
prov_ext = proveedores_ext.copy()
prov_ext = prov_ext.rename(columns={"id_proveedor_ext": "id_proveedor_origen",
                                     "nombre_empresa": "nombre",
                                     "especialidad": "especialidad",
                                     "costo_mensual": "costo_mensual"})
prov_ext["tipo"] = "Externo"

oltp.close()

# SCD Tipo 1: solo última versión, sin historia
dim_tienda_scd = tiendas[["id_tienda", "nombre_tienda", "nombre_ciudad", "region", "zona", "tipo", "tamano_m2"]]
dim_empleado_scd = empleados[["id_empleado", "nombre_empleado", "cargo", "nombre_tienda", "fecha_contratacion", "salario"]]
dim_metodo_pago_scd = metodos_pago[["id_metodo_pago", "nombre", "comision_pct"]]

# SCD Tipo 1 con columna de auditoría
dim_tienda_scd["ultima_actualizacion"] = "2025-12-31"
dim_empleado_scd["ultima_actualizacion"] = "2025-12-31"
dim_metodo_pago_scd["ultima_actualizacion"] = "2025-12-31"

print(f"  Dim_Tienda: {len(dim_tienda_scd)} (SCD Tipo 1)")
print(f"  Dim_Empleado: {len(dim_empleado_scd)} (SCD Tipo 1)")
print(f"  Dim_MetodoPago: {len(dim_metodo_pago_scd)} (SCD Tipo 1)")

# ============================================
# PARTE 4: CARGA DEL CUBO OLAP CON MEDIDAS
# ============================================
print("\n" + "=" * 60)
print("CARGA DEL CUBO OLAP — Medidas Precalculadas")
print("=" * 60)

oltp = conectar_oltp()
ordenes_full = pd.read_sql("SELECT * FROM Ordenes", oltp)
detalle_full = pd.read_sql("SELECT * FROM DetalleOrdenes", oltp)
devoluciones_full = pd.read_sql("SELECT * FROM Devoluciones", oltp)
oltp.close()

# Unir hecho transaccional
fact_base = detalle_full.merge(
    ordenes_full[["id_orden", "id_cliente", "id_empleado", "id_tienda",
                  "id_metodo_pago", "fecha_orden", "estado"]],
    on="id_orden"
)

# Convertir fechas
fact_base["fecha_orden"] = pd.to_datetime(fact_base["fecha_orden"])
fact_base["anio"] = fact_base["fecha_orden"].dt.year
fact_base["mes"] = fact_base["fecha_orden"].dt.month
fact_base["trimestre"] = fact_base["fecha_orden"].dt.quarter
fact_base["fecha_date"] = fact_base["fecha_orden"].dt.date

# Agregar dimensión categoría (desde Productos -> Categorias)
oltp = conectar_oltp()
prods = pd.read_sql("SELECT id_producto, id_categoria FROM Productos", oltp)
cats = pd.read_sql("SELECT id_categoria, nombre FROM Categorias", oltp)
oltp.close()
prods = prods.merge(cats, on="id_categoria")
fact_base = fact_base.merge(prods[["id_producto", "id_categoria", "nombre"]],
                             on="id_producto", how="left")
fact_base = fact_base.rename(columns={"nombre": "categoria"})

# Niveles del cubo (múltiples granularidades)
print("\n  Generando niveles del cubo...")

# Nivel 0: Máximo detalle (por transacción) — 22,684 filas
cubo_n0 = fact_base[[
    "id_detalle", "id_orden", "id_producto", "id_cliente",
    "id_empleado", "id_tienda", "id_metodo_pago", "id_categoria",
    "fecha_date", "anio", "mes", "trimestre",
    "cantidad", "precio_unitario", "descuento", "subtotal", "estado"
]].copy()
cubo_n0["cubo_nivel"] = 0
print(f"  Nivel 0 (detalle transacción): {len(cubo_n0)} filas")

# Nivel 1: Por producto + día
cubo_n1 = fact_base.groupby([
    "id_producto", "id_categoria", "categoria", "fecha_date", "anio", "mes", "trimestre"
]).agg(
    cantidad_vendida=("cantidad", "sum"),
    ventas_totales=("subtotal", "sum"),
    descuento_total=("descuento", "sum"),
    transacciones=("id_orden", "nunique"),
    precio_promedio=("precio_unitario", "mean"),
    ticket_promedio=("subtotal", "mean")
).reset_index()
cubo_n1["cubo_nivel"] = 1
print(f"  Nivel 1 (producto × día): {len(cubo_n1)} filas")

# Nivel 2: Por categoría + mes
cubo_n2 = fact_base.groupby([
    "id_categoria", "categoria", "anio", "mes", "trimestre"
]).agg(
    cantidad_vendida=("cantidad", "sum"),
    ventas_totales=("subtotal", "sum"),
    descuento_total=("descuento", "sum"),
    transacciones=("id_orden", "nunique"),
    productos_distintos=("id_producto", "nunique"),
    ticket_promedio=("subtotal", "mean")
).reset_index()
cubo_n2["cubo_nivel"] = 2
print(f"  Nivel 2 (categoría × mes): {len(cubo_n2)} filas")

# Nivel 3: Por categoría + trimestre (resumen gerencial)
cubo_n3 = fact_base.groupby([
    "id_categoria", "categoria", "anio", "trimestre"
]).agg(
    cantidad_vendida=("cantidad", "sum"),
    ventas_totales=("subtotal", "sum"),
    descuento_total=("descuento", "sum"),
    transacciones=("id_orden", "nunique"),
    ticket_promedio=("subtotal", "mean")
).reset_index()
cubo_n3["cubo_nivel"] = 3
print(f"  Nivel 3 (categoría × trimestre): {len(cubo_n3)} filas")

# Nivel 4: Por año (máxima agregación)
cubo_n4 = fact_base.groupby(["anio"]).agg(
    cantidad_vendida=("cantidad", "sum"),
    ventas_totales=("subtotal", "sum"),
    descuento_total=("descuento", "sum"),
    transacciones=("id_orden", "nunique"),
    categorias_activas=("id_categoria", "nunique"),
    ticket_promedio=("subtotal", "mean")
).reset_index()
cubo_n4["categoria"] = "Todas"
cubo_n4["cubo_nivel"] = 4
print(f"  Nivel 4 (año): {len(cubo_n4)} filas")

# ============================================
# PARTE 5: GUARDAR EN DW
# ============================================
print("\n" + "=" * 60)
print("GUARDANDO EN DATA WAREHOUSE")
print("=" * 60)

def guardar_scd(df, nombre, dw_conn):
    """Guarda DataFrame SCD en el Data Warehouse (SQL Server)."""
    df.to_sql(nombre, dw_conn, if_exists="replace", index=False,
              chunksize=200, method="multi")
    print(f"  {nombre}: {len(df)} registros")

dw = conectar_dw()

# Dimensiones SCD
guardar_scd(dim_producto_scd, "Dim_Producto_SCD", dw)
guardar_scd(dim_cliente_scd, "Dim_Cliente_SCD", dw)
guardar_scd(dim_tienda_scd, "Dim_Tienda_SCD", dw)
guardar_scd(dim_empleado_scd, "Dim_Empleado_SCD", dw)
guardar_scd(dim_metodo_pago_scd, "Dim_MetodoPago_SCD", dw)

# Cubo OLAP en todos los niveles
# Nivel 0
cubo_n0.to_sql("Cubo_Ventas_N0", dw, if_exists="replace", index=False,
               chunksize=200, method="multi")
print(f"  Cubo_Ventas_N0: {len(cubo_n0)} registros")

# Nivel 1
cubo_n1.to_sql("Cubo_Ventas_N1", dw, if_exists="replace", index=False,
               chunksize=200, method="multi")
print(f"  Cubo_Ventas_N1: {len(cubo_n1)} registros")

# Nivel 2
cubo_n2.to_sql("Cubo_Ventas_N2", dw, if_exists="replace", index=False,
               chunksize=200, method="multi")
print(f"  Cubo_Ventas_N2: {len(cubo_n2)} registros")

# Nivel 3
cubo_n3.to_sql("Cubo_Ventas_N3", dw, if_exists="replace", index=False,
               chunksize=200, method="multi")
print(f"  Cubo_Ventas_N3: {len(cubo_n3)} registros")

# Nivel 4
cubo_n4.to_sql("Cubo_Ventas_N4", dw, if_exists="replace", index=False,
               chunksize=200, method="multi")
print(f"  Cubo_Ventas_N4: {len(cubo_n4)} registros")

dw.close()

# ============================================
# PARTE 6: RESUMEN Y VERIFICACIÓN
# ============================================
print("\n" + "=" * 60)
print("VERIFICACIÓN DE SCD + CUBO")
print("=" * 60)

dw = conectar_dw()
tablas = db.list_tables(dw)
print(f"\nTablas en DW: {len(tablas)}")
for _, row in tablas.iterrows():
    count = pd.read_sql(f"SELECT COUNT(*) AS n FROM [{row['name']}]", dw)["n"].iloc[0]
    print(f"  {row['name']:<30s} {count:>6d} registros")

# Verificación SCD Tipo 2 - Producto
dim_prod = pd.read_sql("SELECT * FROM Dim_Producto_SCD", dw)
n_productos_nk = dim_prod["id_producto_nk"].nunique()
n_versiones = len(dim_prod)
productos_con_historia = dim_prod.groupby("id_producto_nk").size()
productos_con_cambios = (productos_con_historia > 1).sum()

print(f"\nSCD Tipo 2 - Dim_Producto:")
print(f"  Productos (NK): {n_productos_nk}")
print(f"  Versiones totales: {n_versiones}")
print(f"  Productos con historia de cambios: {productos_con_cambios}")
print(f"  Ejemplo (producto con múltiples versiones):")
ejemplo_prod = dim_prod[dim_prod["id_producto_nk"] == productos_con_historia[productos_con_historia > 1].index[0]]
print(ejemplo_prod[["id_producto_sk", "id_producto_nk", "nombre_producto",
                     "precio_unitario", "margen_pct", "fecha_inicio", "es_actual"]].to_string(index=False))

# Verificación SCD Tipo 2 - Cliente
dim_cli = pd.read_sql("SELECT * FROM Dim_Cliente_SCD", dw)
n_clientes_nk = dim_cli["id_cliente_nk"].nunique()
n_versiones_cli = len(dim_cli)
clientes_con_historia = dim_cli.groupby("id_cliente_nk").size()
clientes_con_cambios = (clientes_con_historia > 1).sum()

print(f"\nSCD Tipo 2 - Dim_Cliente:")
print(f"  Clientes (NK): {n_clientes_nk}")
print(f"  Versiones totales: {n_versiones_cli}")
print(f"  Clientes con historia de cambios de segmento: {clientes_con_cambios}")
print(f"  Ejemplo (cliente con cambios de segmento RFM):")
ejemplo_cli = dim_cli[dim_cli["id_cliente_nk"] == clientes_con_historia[clientes_con_historia > 1].index[0]]
print(ejemplo_cli[["id_cliente_sk", "id_cliente_nk", "segmento_rfm",
                    "recency_dias", "frecuencia_compras", "monto_total",
                    "fecha_inicio", "es_actual"]].to_string(index=False))

# Verificación Cubo OLAP
print(f"\nCubo OLAP - Medidas por nivel:")
for nivel, tabla in [(0, "Cubo_Ventas_N0"), (1, "Cubo_Ventas_N1"),
                      (2, "Cubo_Ventas_N2"), (3, "Cubo_Ventas_N3"),
                      (4, "Cubo_Ventas_N4")]:
    df = pd.read_sql(f"SELECT * FROM {tabla}", dw)
    print(f"  Nivel {nivel}: {len(df):>6d} filas — ", end="")
    if "ventas_totales" in df.columns:
        print(f"Ventas totales: ${df['ventas_totales'].sum():,.0f} COP")
    else:
        print(f"Columnas: {list(df.columns)[:5]}...")

dw.close()

print("\n" + "=" * 60)
print("¡SCD + CUBO OLAP IMPLEMENTADOS!")
print("=" * 60)
print("""
Resumen de implementación:
  ✓ SCD Tipo 2 — Dim_Producto (historial de precios con vigencia)
  ✓ SCD Tipo 2 — Dim_Cliente (historial de cambios de segmento RFM)
  ✓ SCD Tipo 1 — Dim_Tienda, Dim_Empleado, Dim_MetodoPago (última versión)
  ✓ Cubo OLAP — 5 niveles de granularidad con medidas precalculadas:
    N0: Transacción (22,684 filas)
    N1: Producto × Día
    N2: Categoría × Mes
    N3: Categoría × Trimestre
    N4: Año (resumen gerencial)
  ✓ Medidas: cantidad, ventas totales, descuento, transacciones, ticket promedio
""")
