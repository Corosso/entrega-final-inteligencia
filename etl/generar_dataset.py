#!/usr/bin/env python3
"""Generar dataset sintético de ventas retail para el proyecto BI.
Genera ~30,000 registros distribuidos en ~20 tablas.
Salida: SQL Server (OLTP), CSV, Excel, XML."""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
import random

import db

random.seed(42)
np.random.seed(42)

BASE = os.path.expanduser("~/Documents/Inteligencia de negocios/datos")
os.makedirs(os.path.join(BASE, "externos"), exist_ok=True)

# === TABLAS DE DIMENSION (lookup) ===

categorias = pd.DataFrame({
    "id_categoria": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
    "nombre": ["Laptops", "Smartphones", "Accesorios", "Audio", "Almacenamiento",
               "Monitores", "Impresoras", "Redes", "Software", "Gaming"],
    "descripcion": [
        "Computadores portátiles", "Teléfonos inteligentes",
        "Cables, fundas, cargadores", "Audífonos, parlantes, micrófonos",
        "Discos duros, SSD, USB", "Pantallas y monitores",
        "Impresoras y escáneres", "Routers, switches, access points",
        "Licencias y software", "Consolas, videojuegos, periféricos gaming"
    ]
})

proveedores = pd.DataFrame({
    "id_proveedor": range(1, 16),
    "nombre": [
        "TechSupply Corp", "DigitalWorld Inc", "GlobalParts SA",
        "ElectroMax", "NetProveedores", "DataStore Ltd",
        "CompuParts", "MegaTech", "MicroDistribuidores",
        "SuperDigital", "LogicPC SA", "ChipMex",
        "AsiaElectronics", "EuroComponents", "TecnoParts"
    ],
    "pais": ["USA", "China", "Argentina", "México", "Colombia",
             "Alemania", "Brasil", "Japón", "Corea del Sur",
             "India", "Taiwán", "Vietnam", "Malasia", "España", "Tailandia"],
    "tiempo_entrega_dias": [5, 15, 7, 4, 2, 10, 6, 14, 9, 12, 8, 16, 13, 7, 11],
    "calificacion": [4.5, 3.8, 4.2, 4.0, 4.7, 3.9, 4.1, 4.3, 3.7, 4.0, 4.4, 3.6, 3.9, 4.2, 3.8]
})

ciudades = pd.DataFrame({
    "id_ciudad": range(1, 16),
    "nombre": ["Medellín", "Bogotá", "Cali", "Barranquilla", "Cartagena",
               "Bucaramanga", "Pereira", "Manizales", "Santa Marta",
               "Cúcuta", "Ibagué", "Montería", "Villavicencio", "Pasto", "Neiva"],
    "region": ["Antioquia", "Cundinamarca", "Valle", "Atlántico", "Bolívar",
               "Santander", "Risaralda", "Caldas", "Magdalena",
               "Norte de Santander", "Tolima", "Córdoba", "Meta", "Nariño", "Huila"],
    "zona": ["Centro"] * 4 + ["Norte"] * 4 + ["Occidente"] * 3 + ["Oriente"] * 4
})

tiendas = pd.DataFrame({
    "id_tienda": range(1, 21),
    "nombre": [f"TechStore {c}" for c in ["Centro", "Norte", "Sur", "Este", "Oeste",
               "Plaza", "Mall", "Outlet", "Premium", "Express",
               "Digital", "Smart", "Online", "Megastore", "Plus",
               "Go", "Hub", "Zone", "Lab", "Point"]],
    "id_ciudad": np.random.choice(ciudades["id_ciudad"], 20, replace=True),
    "tipo": ["Física"] * 16 + ["Virtual"] * 4,
    "tamano_m2": np.random.randint(50, 800, 20)
})

metodos_pago = pd.DataFrame({
    "id_metodo_pago": range(1, 7),
    "nombre": ["Tarjeta Crédito", "Tarjeta Débito", "Efectivo contra entrega",
               "Transferencia", "Pago Móvil", "Criptomonedas"],
    "comision_pct": [3.5, 1.8, 0.0, 0.5, 2.0, 1.0]
})

# === TABLAS DE DIMENSION (con más registros) ===

n_productos = 80
productos = pd.DataFrame({
    "id_producto": range(1, n_productos + 1),
    "nombre": [
        f"{cat} {modelo}" for _ in range(n_productos)
        for cat, modelo in [random.choice([
            ("Laptop", "Pro X"), ("Laptop", "Air"), ("Laptop", "Gamer"),
            ("Smartphone", "Galaxy"), ("Smartphone", "Pixel"), ("Smartphone", "Redmi"),
            ("Audífonos", "BT"), ("Cable", "USB-C"), ("Cargador", "Rápido"),
            ("Parlante", "Portátil"), ("SSD", "NVMe"), ("HDD", "Externo"),
            ("USB", "64GB"), ("Monitor", "Curvo"), ("Monitor", "4K"),
            ("Impresora", "Láser"), ("Router", "WiFi6"), ("Switch", "24p"),
            ("Software", "Office"), ("Software", "Antivirus"),
            ("Consola", "Portátil"), ("Mouse", "Gamer"), ("Teclado", "Mecánico")
        ])]
    ][:n_productos],
    "id_categoria": np.random.choice(categorias["id_categoria"], n_productos),
    "id_proveedor": np.random.choice(proveedores["id_proveedor"], n_productos),
    "precio_unitario": np.round(np.random.uniform(10, 5000, n_productos) * 1000),
    "costo_unitario": None,  # Se calcula abajo
    "stock_minimo": np.random.randint(5, 50, n_productos),
    "activo": np.random.choice([True, False], n_productos, p=[0.92, 0.08])
})
productos["costo_unitario"] = np.round(productos["precio_unitario"] * np.random.uniform(0.35, 0.75, n_productos))
# Nombres más limpios
marcas = ["Dell", "HP", "Lenovo", "Asus", "Acer", "Samsung", "LG", "Sony", "Xiaomi", "Apple",
          "Corsair", "Logitech", "Kingston", "WD", "TP-Link"]
productos["nombre"] = [
    f"{random.choice(marcas)} {random.choice(['Pro','Air','Plus','Ultra','Lite','Max','X','S','Z','E'])}-{i:03d}"
    for i in range(1, n_productos + 1)
]

n_clientes = 500
clientes = pd.DataFrame({
    "id_cliente": range(1, n_clientes + 1),
    "nombre": [f"Cliente_{i:04d}" for i in range(1, n_clientes + 1)],
    "email": [f"cliente{i:04d}@email.com" for i in range(1, n_clientes + 1)],
    "id_ciudad": np.random.choice(ciudades["id_ciudad"], n_clientes),
    "fecha_registro": [
        datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))
        for _ in range(n_clientes)
    ],
    "segmento": np.random.choice(["Residencial", "PYME", "Corporativo", "Educativo"],
                                  n_clientes, p=[0.55, 0.25, 0.12, 0.08]),
    "edad": np.random.randint(18, 70, n_clientes),
    "genero": np.random.choice(["M", "F", "Otro"], n_clientes, p=[0.48, 0.48, 0.04])
})

n_empleados = 25
empleados = pd.DataFrame({
    "id_empleado": range(1, n_empleados + 1),
    "nombre": [f"Empleado_{i:03d}" for i in range(1, n_empleados + 1)],
    "cargo": np.random.choice(["Vendedor", "Cajero", "Supervisor", "Gerente Tienda",
                                "Soporte", "Bodega", "Servicio al Cliente"],
                              n_empleados, p=[0.30, 0.15, 0.15, 0.08, 0.12, 0.10, 0.10]),
    "id_tienda": np.random.choice(tiendas["id_tienda"], n_empleados),
    "fecha_contratacion": [
        datetime(2019, 1, 1) + timedelta(days=random.randint(0, 2000))
        for _ in range(n_empleados)
    ],
    "salario": np.round(np.random.uniform(1300000, 6000000, n_empleados))
})

# === TABLAS DE HECHOS (transacciones) ===

n_ordenes = 5000
ordenes = pd.DataFrame({
    "id_orden": range(1, n_ordenes + 1),
    "id_cliente": np.random.choice(clientes["id_cliente"], n_ordenes),
    "id_empleado": np.random.choice(empleados["id_empleado"], n_ordenes),
    "id_tienda": np.random.choice(tiendas["id_tienda"], n_ordenes),
    "id_metodo_pago": np.random.choice(metodos_pago["id_metodo_pago"], n_ordenes),
    "fecha_orden": [
        datetime(2023, 1, 1) + timedelta(
            days=random.randint(0, 1095),
            hours=random.randint(8, 22),
            minutes=random.randint(0, 59)
        )
        for _ in range(n_ordenes)
    ],
    "estado": np.random.choice(
        ["Completada", "Completada", "Completada", "Completada",
         "Pendiente", "Cancelada", "Enviada", "Devuelta"],
        n_ordenes, p=[0.55, 0.10, 0.10, 0.05, 0.05, 0.05, 0.05, 0.05]
    )
})
ordenes = ordenes.sort_values("fecha_orden").reset_index(drop=True)

# Detalle de órdenes (cada orden tiene entre 1 y 8 productos)
detalle_ordenes = []
for _, orden in ordenes.iterrows():
    n_items = np.random.randint(1, 9)
    productos_orden = np.random.choice(productos["id_producto"], n_items, replace=False)
    for id_prod in productos_orden:
        prod = productos[productos["id_producto"] == id_prod].iloc[0]
        cantidad = np.random.randint(1, 5)
        precio = prod["precio_unitario"]
        descuento = np.random.choice([0, 0, 0, 0.05, 0.10, 0.15, 0.20], p=[0.4, 0.15, 0.1, 0.1, 0.1, 0.1, 0.05])
        detalle_ordenes.append({
            "id_detalle": len(detalle_ordenes) + 1,
            "id_orden": orden["id_orden"],
            "id_producto": id_prod,
            "cantidad": cantidad,
            "precio_unitario": precio,
            "descuento": descuento,
            "subtotal": round(precio * cantidad * (1 - descuento))
        })
detalle_ordenes = pd.DataFrame(detalle_ordenes)

# Devoluciones (~8% de órdenes completadas)
ordenes_completadas = ordenes[ordenes["estado"].isin(["Completada", "Enviada", "Devuelta"])]
ids_ordenes_devueltas = np.random.choice(ordenes_completadas["id_orden"],
                                          int(len(ordenes_completadas) * 0.08), replace=False)
devoluciones = []
for id_orden in ids_ordenes_devueltas:
    items = detalle_ordenes[detalle_ordenes["id_orden"] == id_orden]
    n_devueltos = np.random.randint(1, max(2, len(items)))
    items_devueltos = items.sample(n=n_devueltos, replace=False)
    for _, item in items_devueltos.iterrows():
        devoluciones.append({
            "id_devolucion": len(devoluciones) + 1,
            "id_orden": id_orden,
            "id_producto": item["id_producto"],
            "cantidad": np.random.randint(1, item["cantidad"] + 1),
            "motivo": np.random.choice(
                ["Defecto", "No coincide descripción", "Cambio de opinión",
                 "Talla/Modelo incorrecto", "Llegó tarde", "Dañado en envío"],
                p=[0.25, 0.20, 0.25, 0.10, 0.10, 0.10]
            ),
            "fecha_devolucion": [
                ordenes[ordenes["id_orden"] == id_orden]["fecha_orden"].iloc[0] +
                timedelta(days=random.randint(2, 20))
            ][0],
            "reembolso_pct": np.random.choice([100, 80, 50], p=[0.7, 0.2, 0.1])
        })
devoluciones = pd.DataFrame(devoluciones)

# Inventario (stocks por producto y tienda, al final del período)
inventario = []
for _, prod in productos.iterrows():
    tiendas_con_stock = np.random.choice(tiendas["id_tienda"], np.random.randint(5, 16), replace=False)
    for id_tienda in tiendas_con_stock:
        inventario.append({
            "id_inventario": len(inventario) + 1,
            "id_producto": prod["id_producto"],
            "id_tienda": id_tienda,
            "cantidad_disponible": np.random.randint(0, 200),
            "cantidad_reservada": np.random.randint(0, 20),
            "ultima_actualizacion": datetime(2025, 12, 31) - timedelta(days=random.randint(0, 7))
        })
inventario = pd.DataFrame(inventario)

# Envíos
ordenes_enviadas = ordenes[ordenes["estado"].isin(["Enviada", "Completada", "Devuelta"])]
envios = pd.DataFrame({
    "id_envio": range(1, len(ordenes_enviadas) + 1),
    "id_orden": ordenes_enviadas["id_orden"].values,
    "empresa_envio": np.random.choice(
        ["Servientrega", "Interrapidisimo", "DHL", "FedEx", "Envía", "Coordinadora"],
        len(ordenes_enviadas), p=[0.30, 0.25, 0.15, 0.10, 0.12, 0.08]
    ),
    "costo_envio": np.round(np.random.uniform(0, 35000, len(ordenes_enviadas))),
    "tiempo_entrega_dias": np.random.randint(1, 10, len(ordenes_enviadas)),
    "fecha_estimada": None,
    "fecha_real": None
})
fechas_estimadas = []
fechas_reales = []
for i, row in envios.iterrows():
    fecha_orden = ordenes[ordenes["id_orden"] == row["id_orden"]]["fecha_orden"].iloc[0]
    fechas_estimadas.append(fecha_orden + timedelta(days=int(row["tiempo_entrega_dias"])))
    fechas_reales.append(fecha_orden + timedelta(days=int(row["tiempo_entrega_dias"] + np.random.randint(-2, 5))))
envios["fecha_estimada"] = fechas_estimadas
envios["fecha_real"] = fechas_reales

# Encuestas de satisfacción (~30% de clientes)
clientes_encuesta = np.random.choice(clientes["id_cliente"], int(n_clientes * 0.3), replace=False)
encuestas = pd.DataFrame({
    "id_encuesta": range(1, len(clientes_encuesta) + 1),
    "id_cliente": clientes_encuesta,
    "fecha_encuesta": [datetime(2025, 6, 1) + timedelta(days=random.randint(0, 200)) for _ in clientes_encuesta],
    "satisfaccion": np.random.choice([1, 2, 3, 4, 5], len(clientes_encuesta), p=[0.05, 0.08, 0.17, 0.35, 0.35]),
    "recomendaria": np.random.choice(["Sí", "No", "Tal vez"], len(clientes_encuesta), p=[0.6, 0.2, 0.2]),
    "comentarios": [np.random.choice([
        "Excelente servicio", "Buen producto", "Regular", "Podría mejorar",
        "Muy satisfecho", "No me gustó el empaque", "Entrega rápida",
        "El producto no funcionó", "Buena relación calidad-precio"
    ]) for _ in clientes_encuesta]
})

# === DATOS EXTERNOS ===

# Datos de mercado externo (CSV)
mercado = pd.DataFrame({
    "id_categoria": categorias["id_categoria"],
    "tamano_mercado_millones": [250, 500, 120, 80, 45, 90, 30, 60, 200, 150],
    "crecimiento_anual_pct": [5.2, 8.5, 3.1, 4.8, 2.0, 3.5, -1.2, 6.0, 7.5, 9.0],
    "indice_competitividad": [8.5, 9.2, 6.0, 7.0, 5.5, 6.8, 4.0, 7.2, 8.0, 8.8],
    "tendencia": ["Estable", "Creciente", "Estable", "Creciente", "Decreciente",
                  "Estable", "Decreciente", "Creciente", "Creciente", "Creciente"]
})

# Datos de proveedores externos (Excel)
proveedores_ext = pd.DataFrame({
    "id_proveedor_ext": range(1, 11),
    "nombre_empresa": [f"ProveedorExt_{i}" for i in range(1, 11)],
    "especialidad": np.random.choice(["Componentes", "Logística", "Empaque", "Marketing", "Financiero"], 10),
    "costo_mensual": np.round(np.random.uniform(500, 10000, 10) * 1000),
    "calificacion_promedio": np.round(np.random.uniform(2.5, 5.0, 10), 1),
    "pais": np.random.choice(["Colombia", "México", "Brasil", "Chile", "Perú"], 10)
})

# Datos de campañas (XML)
campanas_data = [
    {"id": "C001", "nombre": "Black Friday 2024", "tipo": "Descuento", "inicio": "2024-11-25",
     "fin": "2024-11-30", "presupuesto": "5000000", "categorias": "todas", "incremento_ventas_pct": "45"},
    {"id": "C002", "nombre": "Cyber Monday 2024", "tipo": "Online", "inicio": "2024-12-02",
     "fin": "2024-12-02", "presupuesto": "3000000", "categorias": "Laptops,Smartphones", "incremento_ventas_pct": "30"},
    {"id": "C003", "nombre": "Regreso a Clases 2025", "tipo": "Estacional", "inicio": "2025-01-10",
     "fin": "2025-02-05", "presupuesto": "4000000", "categorias": "Laptops,Software,Accesorios", "incremento_ventas_pct": "25"},
    {"id": "C004", "nombre": "Día del Padre 2025", "tipo": "Estacional", "inicio": "2025-06-10",
     "fin": "2025-06-15", "presupuesto": "2500000", "categorias": "Smartphones,Gaming,Audio", "incremento_ventas_pct": "20"},
    {"id": "C005", "nombre": "Aniversario TechStore", "tipo": "Corporativa", "inicio": "2025-03-01",
     "fin": "2025-03-15", "presupuesto": "8000000", "categorias": "todas", "incremento_ventas_pct": "35"},
]

# Histórico de precios (cambios de precio en el tiempo)
historico_precios = []
for _, prod in productos.iterrows():
    n_cambios = np.random.randint(1, 6)
    fechas_cambio = sorted([datetime(2023, 1, 1) + timedelta(days=random.randint(0, 1095))
                            for _ in range(n_cambios)])
    for j, fecha in enumerate(fechas_cambio):
        factor = 1.0 + (j * 0.05) + np.random.uniform(-0.05, 0.10)
        historico_precios.append({
            "id_historico_precio": len(historico_precios) + 1,
            "id_producto": prod["id_producto"],
            "precio": round(prod["precio_unitario"] * factor),
            "costo": round(prod["costo_unitario"] * factor),
            "fecha_inicio": fecha,
            "fecha_fin": fechas_cambio[j + 1] if j + 1 < len(fechas_cambio) else None,
            "motivo_cambio": np.random.choice(
                ["Inflación", "Cambio proveedor", "Estrategia comercial", "Ajuste margen", "Promoción"],
                p=[0.25, 0.20, 0.25, 0.20, 0.10]
            )
        })
historico_precios = pd.DataFrame(historico_precios)

# Promociones aplicadas a órdenes
promociones = pd.DataFrame({
    "id_promocion": range(1, 9),
    "nombre": ["BLACKFRIDAY", "CYBERMONDAY", "REGRESOACLASES", "DIADELPADRE",
               "ANIVERSARIO", "BIENVENIDA10", "VIP15", "ENVIOGRATIS"],
    "tipo": ["Porcentaje", "Porcentaje", "Fijo", "Porcentaje",
             "Porcentaje", "Porcentaje", "Porcentaje", "Envío"],
    "valor": [20, 15, 50000, 10, 25, 10, 15, 0],
    "fecha_inicio": [
        datetime(2024, 11, 25), datetime(2024, 12, 2), datetime(2025, 1, 10),
        datetime(2025, 6, 10), datetime(2025, 3, 1), datetime(2023, 1, 1),
        datetime(2023, 1, 1), datetime(2023, 1, 1)
    ],
    "fecha_fin": [
        datetime(2024, 11, 30), datetime(2024, 12, 2), datetime(2025, 2, 5),
        datetime(2025, 6, 15), datetime(2025, 3, 15), datetime(2026, 12, 31),
        datetime(2026, 12, 31), datetime(2026, 12, 31)
    ],
    "categoria_aplica": ["Todas", "Laptops,Smartphones", "Laptops,Software",
                          "Smartphones,Gaming,Audio", "Todas", "Todas", "Todas", "Todas"],
    "activa": [False, False, False, False, False, True, True, True]
})

# Promociones por orden
promociones_orden = []
for _, orden in ordenes.iterrows():
    if np.random.random() < 0.35:
        proms_aplicables = promociones[
            (promociones["fecha_inicio"] <= orden["fecha_orden"]) &
            (promociones["fecha_fin"] >= orden["fecha_orden"]) &
            (promociones["activa"] == True)
        ]
        if len(proms_aplicables) > 0:
            prom = proms_aplicables.sample(1).iloc[0]
            promociones_orden.append({
                "id_promocion_orden": len(promociones_orden) + 1,
                "id_orden": orden["id_orden"],
                "id_promocion": prom["id_promocion"],
                "descuento_aplicado": np.round(np.random.uniform(0.05, 0.30), 2)
            })
promociones_orden = pd.DataFrame(promociones_orden)

# Log de ETL (para trazabilidad)
n_registros_etl = len(ordenes) + len(detalle_ordenes) + len(devoluciones)
log_etl = pd.DataFrame({
    "id_log": range(1, n_registros_etl + 1),
    "proceso": (["CargaOrdenes"] * len(ordenes) +
                ["CargaDetalleOrdenes"] * len(detalle_ordenes) +
                ["CargaDevoluciones"] * len(devoluciones)),
    "estado": np.random.choice(["Éxito", "Éxito", "Éxito", "Éxito", "Error", "Reintento"],
                                n_registros_etl, p=[0.85, 0.05, 0.03, 0.02, 0.03, 0.02]),
    "timestamp": [datetime(2026, 1, 1) + timedelta(seconds=random.randint(0, 86400 * 30))
                  for _ in range(n_registros_etl)],
    "registros_procesados": np.random.randint(1, 100, n_registros_etl)
})

# ===========================
# === GUARDAR TODO ===
# ===========================

print("Guardando datos...")

# SQL Server OLTP
db.ensure_databases()
engine = db.get_engine(db.OLTP_DB)
for nombre, df in [
    ("Categorias", categorias), ("Proveedores", proveedores), ("Ciudades", ciudades),
    ("Tiendas", tiendas), ("MetodosPago", metodos_pago), ("Productos", productos),
    ("Clientes", clientes), ("Empleados", empleados), ("Ordenes", ordenes),
    ("DetalleOrdenes", detalle_ordenes), ("Devoluciones", devoluciones),
    ("Inventario", inventario), ("Envios", envios), ("Encuestas", encuestas),
    ("HistoricoPrecios", historico_precios), ("Promociones", promociones),
    ("PromocionesOrden", promociones_orden), ("LogETL", log_etl)
]:
    df.to_sql(nombre, engine, if_exists="replace", index=False,
              chunksize=200, method="multi")
    print(f"  SQL Server -> {nombre}: {len(df)} registros")
engine.dispose()

# CSV externos
mercado.to_csv(os.path.join(BASE, "externos", "mercado_categorias.csv"), index=False)
print(f"  CSV -> mercado_categorias: {len(mercado)} registros")

# Excel externo
proveedores_ext.to_excel(os.path.join(BASE, "externos", "proveedores_externos.xlsx"), index=False)
print(f"  Excel -> proveedores_externos: {len(proveedores_ext)} registros")

# XML externo (campañas)
root = ET.Element("campanas")
for c in campanas_data:
    camp = ET.SubElement(root, "campana", id=c["id"])
    for k, v in c.items():
        if k != "id":
            ET.SubElement(camp, k).text = v
xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="  ")
with open(os.path.join(BASE, "externos", "campanas_marketing.xml"), "w", encoding="utf-8") as f:
    f.write(xml_str)
print(f"  XML -> campanas_marketing: {len(campanas_data)} registros")

# También guardar CSVs de todas las tablas OLTP para fuentes múltiples
for nombre, df in [
    ("Categorias", categorias), ("Proveedores", proveedores), ("Ciudades", ciudades),
    ("Tiendas", tiendas), ("MetodosPago", metodos_pago), ("Productos", productos),
    ("Clientes", clientes), ("Empleados", empleados), ("Ordenes", ordenes),
    ("DetalleOrdenes", detalle_ordenes), ("Devoluciones", devoluciones),
    ("Inventario", inventario), ("Envios", envios), ("Encuestas", encuestas),
    ("HistoricoPrecios", historico_precios), ("Promociones", promociones),
    ("PromocionesOrden", promociones_orden), ("LogETL", log_etl)
]:
    df.to_csv(os.path.join(BASE, "externos", f"{nombre.lower()}.csv"), index=False)

# Resumen de registros generados
total = sum(len(df) for df in [
    categorias, proveedores, ciudades, tiendas, metodos_pago,
    productos, clientes, empleados, ordenes, detalle_ordenes,
    devoluciones, inventario, envios, encuestas,
    historico_precios, promociones, promociones_orden, log_etl
])
print(f"\n=== RESUMEN ===")
print(f"Total registros (tablas OLTP): {total}")
print(f"Registros transaccionales (órdenes + detalles + devoluciones): {len(ordenes) + len(detalle_ordenes) + len(devoluciones)}")
print(f"Tablas generadas: 18 OLTP + 3 externas = 21 tablas")
print(f"Fuentes: SQL Server + CSV + Excel + XML")
print(f"\nBase de datos SQL Server (OLTP): {db.OLTP_DB}")
print(f"Datos externos: {os.path.join(BASE, 'externos')}/")
print("¡Dataset generado exitosamente!")
