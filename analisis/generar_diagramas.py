"""
Generación de diagramas de arquitectura del proyecto BI (matplotlib).

Produce 3 figuras en analisis/graficos/:
  12_modelo_relacional_oltp.png  -> Modelo relacional (ER) del OLTP
  13_esquema_estrella_dw.png     -> Esquema estrella del Data Warehouse
  14_flujo_etl.png               -> Flujo ETL (4 fuentes -> E-T-L -> DW)

Los dos primeros se construyen introspectando los esquemas reales con INFORMATION_SCHEMA de SQL Server,
de modo que reflejen exactamente las tablas y columnas existentes. Las
relaciones del OLTP se infieren por convención de nombres (una columna id_X que
coincide con la PK id_X de otra tabla es una llave foránea).
"""

import os
import sys
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "etl"))
import db

OLTP_DB = db.OLTP_DB
DW_DB = db.DW_DB
GRAFICOS_DIR = os.path.join(BASE, "analisis", "graficos")
os.makedirs(GRAFICOS_DIR, exist_ok=True)


# --------------------------------------------------------------------------- #
# Utilidades de introspección
# --------------------------------------------------------------------------- #
def leer_esquema(database, incluir=None, excluir_prefijos=()):
    """Devuelve {tabla: {'cols': [(nombre, es_pk)], 'pk': nombre_o_None}}.

    Introspecta la base SQL Server vía INFORMATION_SCHEMA. Como las tablas no
    declaran PK (se crean con to_sql), la PK se infiere por convención: la
    primera columna "id_*".
    """
    import pandas as pd
    engine = db.get_engine(database)
    with engine.connect() as con:
        tablas = pd.read_sql(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME", con
        )["TABLE_NAME"].tolist()
        esquema = {}
        for t in tablas:
            if incluir is not None and t not in incluir:
                continue
            if any(t.startswith(p) for p in excluir_prefijos):
                continue
            nombres = pd.read_sql(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_NAME = '{t}' ORDER BY ORDINAL_POSITION", con
            )["COLUMN_NAME"].tolist()
            cols, pk = [[n, False] for n in nombres], None
            # Convención: la primera columna "id_*" es la llave primaria.
            for c in cols:
                if c[0].startswith("id_"):
                    pk = c[0]
                    c[1] = True
                    break
            cols = [(n, b) for n, b in cols]
            esquema[t] = {"cols": cols, "pk": pk}
    engine.dispose()
    return esquema


def inferir_relaciones(esquema):
    """Infiere FKs: columna que es PK de OTRA tabla -> relación (origen, destino)."""
    pk_a_tabla = {info["pk"]: t for t, info in esquema.items() if info["pk"]}
    rels = []
    for t, info in esquema.items():
        for col, es_pk in info["cols"]:
            if es_pk:
                continue
            destino = pk_a_tabla.get(col)
            if destino and destino != t:
                rels.append((t, destino))
    return rels


# --------------------------------------------------------------------------- #
# Dibujo de cajas tipo "tabla"
# --------------------------------------------------------------------------- #
def dibujar_tabla(ax, x, y, titulo, columnas, w=2.3, color="#2E86AB",
                  max_cols=7, fontsize=7):
    """Dibuja una caja-tabla con cabecera y lista de columnas. (x,y) = esquina sup-izq."""
    columnas = list(columnas)
    mostrar = columnas[:max_cols]
    extra = len(columnas) - len(mostrar)
    n = len(mostrar) + (1 if extra else 0)
    fila = 0.30
    head = 0.42
    h = head + n * fila

    # cuerpo
    ax.add_patch(
        FancyBboxPatch(
            (x, y - h), w, h, boxstyle="round,pad=0.02,rounding_size=0.05",
            linewidth=1.1, edgecolor="#333333", facecolor="white", zorder=3,
        )
    )
    # cabecera
    ax.add_patch(
        FancyBboxPatch(
            (x, y - head), w, head, boxstyle="round,pad=0.02,rounding_size=0.05",
            linewidth=1.1, edgecolor="#333333", facecolor=color, zorder=4,
        )
    )
    ax.text(x + w / 2, y - head / 2, titulo, ha="center", va="center",
            fontsize=fontsize + 1.5, fontweight="bold", color="white", zorder=5)

    for i, (col, es_pk) in enumerate(mostrar):
        ty = y - head - fila * (i + 0.5)
        etiqueta = ("PK  " if es_pk else "") + col
        ax.text(x + 0.10, ty, etiqueta, ha="left", va="center",
                fontsize=fontsize, color="#222222",
                fontweight="bold" if es_pk else "normal", zorder=5)
    if extra:
        ty = y - head - fila * (len(mostrar) + 0.5)
        ax.text(x + 0.10, ty, f"… (+{extra} columnas)", ha="left", va="center",
                fontsize=fontsize - 0.5, color="#888888", style="italic", zorder=5)

    # centro y caja (x0,y0,x1,y1) para trazar líneas
    centro = (x + w / 2, y - h / 2)
    return centro, (x, y - h, x + w, y)


def conectar(ax, caja_a, caja_b, color="#888888"):
    """Dibuja una línea entre los centros de dos cajas (bordes aproximados)."""
    (ax0, ay0, ax1, ay1) = caja_a
    (bx0, by0, bx1, by1) = caja_b
    ca = ((ax0 + ax1) / 2, (ay0 + ay1) / 2)
    cb = ((bx0 + bx1) / 2, (by0 + by1) / 2)
    ax.add_patch(
        FancyArrowPatch(
            ca, cb, arrowstyle="-", linewidth=1.0, color=color,
            connectionstyle="arc3,rad=0.05", zorder=1, alpha=0.7,
        )
    )


# --------------------------------------------------------------------------- #
# 1) Modelo relacional (ER) del OLTP
# --------------------------------------------------------------------------- #
def diagrama_oltp():
    esquema = leer_esquema(OLTP_DB)
    rels = inferir_relaciones(esquema)

    # Posiciones manuales (esquina sup-izq) para una lectura limpia de 18 tablas.
    pos = {
        "Ciudades":        (0.3, 11.3),
        "Clientes":        (0.3, 9.2),
        "Encuestas":       (0.3, 5.6),
        "Tiendas":         (3.2, 11.3),
        "Empleados":       (3.2, 8.6),
        "Inventario":      (6.1, 11.3),
        "Ordenes":         (3.2, 5.6),
        "MetodosPago":     (0.3, 2.6),
        "Promociones":     (3.2, 2.6),
        "PromocionesOrden":(6.1, 2.6),
        "DetalleOrdenes":  (6.1, 5.6),
        "Devoluciones":    (9.0, 5.6),
        "Envios":          (9.0, 2.6),
        "Productos":       (9.0, 11.3),
        "Categorias":      (11.9, 11.3),
        "Proveedores":     (11.9, 8.6),
        "HistoricoPrecios":(11.9, 5.6),
        "LogETL":          (11.9, 2.6),
    }

    fig, ax = plt.subplots(figsize=(17, 12))
    cajas = {}
    for t, info in esquema.items():
        if t not in pos:
            continue
        x, y = pos[t]
        rows = info["cols"][0] if info["cols"] else None
        _, caja = dibujar_tabla(ax, x, y, t, info["cols"], color="#2E86AB")
        cajas[t] = caja

    for origen, destino in rels:
        if origen in cajas and destino in cajas:
            conectar(ax, cajas[origen], cajas[destino], color="#C0392B")

    ax.set_xlim(-0.3, 14.6)
    ax.set_ylim(-0.5, 12.2)
    ax.axis("off")
    ax.set_title(
        "Modelo Relacional (ER) — Base de Datos Operacional (OLTP)\n"
        f"{len(esquema)} tablas · relaciones inferidas por llave foránea (líneas rojas)",
        fontsize=14, fontweight="bold", pad=14,
    )
    plt.tight_layout()
    out = os.path.join(GRAFICOS_DIR, "12_modelo_relacional_oltp.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"OK -> {out}  ({len(esquema)} tablas, {len(rels)} relaciones)")


# --------------------------------------------------------------------------- #
# 2) Esquema estrella del DW
# --------------------------------------------------------------------------- #
def diagrama_estrella():
    # Dimensiones limpias (sin variantes _SCD ni tablas del cubo).
    dims = [
        "Dim_Tiempo", "Dim_Producto", "Dim_Cliente", "Dim_Tienda",
        "Dim_Empleado", "Dim_MetodoPago", "Dim_Proveedor", "Dim_Campana",
    ]
    esquema = leer_esquema(DW_DB, incluir=set(dims) | {"Fact_Ventas"})

    import math

    fig, ax = plt.subplots(figsize=(16, 11))

    # Fact al centro
    fx, fy = 6.5, 5.4
    fcols = esquema["Fact_Ventas"]["cols"]
    _, caja_fact = dibujar_tabla(
        ax, fx - 1.4, fy + 1.6, "Fact_Ventas", fcols, w=2.8,
        color="#C0392B", max_cols=14, fontsize=7,
    )

    # Dimensiones en círculo
    n = len(dims)
    R = 5.2
    for i, d in enumerate(dims):
        ang = math.pi / 2 + i * 2 * math.pi / n
        cx = fx + R * math.cos(ang) * 1.15
        cy = fy + R * math.sin(ang) * 0.78
        cols = esquema[d]["cols"]
        _, caja = dibujar_tabla(ax, cx - 1.15, cy + 1.0, d, cols, w=2.3,
                                color="#2E86AB", max_cols=7)
        conectar(ax, caja_fact, caja, color="#888888")

    ax.set_xlim(-1, 14)
    ax.set_ylim(-1.5, 12)
    ax.axis("off")
    ax.set_title(
        "Esquema Estrella — Data Warehouse (Fact_Ventas + 8 dimensiones)",
        fontsize=14, fontweight="bold", pad=10,
    )
    plt.tight_layout()
    out = os.path.join(GRAFICOS_DIR, "13_esquema_estrella_dw.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"OK -> {out}  (Fact_Ventas + {n} dimensiones)")


# --------------------------------------------------------------------------- #
# 3) Flujo ETL
# --------------------------------------------------------------------------- #
def diagrama_etl():
    fig, ax = plt.subplots(figsize=(16, 9))

    def caja(x, y, w, h, texto, color, fc="white", fs=10, tcolor="#222"):
        ax.add_patch(
            FancyBboxPatch(
                (x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.08",
                linewidth=1.6, edgecolor=color, facecolor=fc, zorder=3,
            )
        )
        ax.text(x + w / 2, y + h / 2, texto, ha="center", va="center",
                fontsize=fs, color=tcolor, zorder=4, wrap=True)

    def flecha(x0, y0, x1, y1):
        ax.add_patch(
            FancyArrowPatch(
                (x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=20,
                linewidth=2, color="#555", zorder=2,
            )
        )

    # Fuentes (izquierda)
    fuentes = [
        ("SQL Server — OLTP\n18 tablas · 65.177 reg.", "#2E86AB"),
        ("CSV\nmercado_categorias", "#27AE60"),
        ("Excel (.xlsx)\nproveedores_externos", "#F39C12"),
        ("XML\ncampanas_marketing", "#8E44AD"),
    ]
    fy0 = 6.6
    for i, (txt, col) in enumerate(fuentes):
        y = fy0 - i * 1.7
        caja(0.3, y, 2.9, 1.3, txt, col, fc="#F7F9FB", fs=9, tcolor=col)
        flecha(3.2, y + 0.65, 4.4, 4.0)

    # Extract
    caja(4.4, 3.3, 1.7, 1.4, "EXTRACT\nlectura de\n4 formatos", "#2C3E50",
         fc="#EAF2F8", fs=10)
    flecha(6.1, 4.0, 6.9, 4.0)

    # Transform
    transform_txt = (
        "TRANSFORM\n"
        "• Limpieza de nulos/formatos\n"
        "• Cálculo RFM por cliente\n"
        "• Segmentación (VIP/Regular/Riesgo/Perdido)\n"
        "• Márgenes por producto\n"
        "• Unión de archivos (15 internos + 10 externos)\n"
        "• Dim_Tiempo con jerarquías\n"
        "• SCD Tipo 2 (Producto, Cliente)"
    )
    caja(6.9, 2.4, 4.6, 3.2, transform_txt, "#2C3E50", fc="#FEF9E7", fs=9.5)
    flecha(11.5, 4.0, 12.3, 4.0)

    # Load
    caja(12.3, 3.3, 1.6, 1.4, "LOAD\ncarga al\nDW", "#2C3E50", fc="#EAF2F8", fs=10)
    flecha(13.1, 3.3, 13.1, 2.4)

    # DW
    caja(11.5, 0.5, 3.2, 1.7,
         "DATA WAREHOUSE\nEsquema estrella\n9 tablas (8 dim + 1 hechos)\n22.684 reg. de hechos",
         "#C0392B", fc="#FDEDEC", fs=10, tcolor="#C0392B")

    ax.set_xlim(0, 15)
    ax.set_ylim(0, 8.2)
    ax.axis("off")
    ax.set_title(
        "Flujo ETL — Integración de 4 fuentes heterogéneas hacia el DW",
        fontsize=14, fontweight="bold", pad=10,
    )
    plt.tight_layout()
    out = os.path.join(GRAFICOS_DIR, "14_flujo_etl.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"OK -> {out}")


if __name__ == "__main__":
    print("Generando diagramas de arquitectura...")
    diagrama_oltp()
    diagrama_estrella()
    diagrama_etl()
    print("Listo. Diagramas en analisis/graficos/ (12, 13, 14).")
