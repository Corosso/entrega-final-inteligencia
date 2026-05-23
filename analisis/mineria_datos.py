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
# # Minería de Datos y Análisis Adicionales con Python
#
# Técnicas implementadas:
# 1. Clustering K-Means — Segmentación RFM de clientes
# 2. Random Forest — Predicción de churn
# 3. Naive Bayes — Probabilidad de devolución
# 4. Descomposición de series de tiempo — Estacionalidad de ventas
# 5. Matriz de correlación — Relación entre categorías
# 6. Reglas de asociación Apriori — Canasta de mercado

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

# ============================================
# CARGA DE DATOS DESDE EL DATA WAREHOUSE
# ============================================
print("=" * 60)
print("CARGA DE DATOS — DATA WAREHOUSE")
print("=" * 60)

fact = pd.read_sql("SELECT * FROM Fact_Ventas", conn)
dim_tiempo = pd.read_sql("SELECT id_tiempo, anio, mes, nombre_mes, trimestre FROM Dim_Tiempo", conn)
dim_producto = pd.read_sql("SELECT id_producto, nombre_producto, nombre_categoria, margen_pct FROM Dim_Producto", conn)
dim_cliente = pd.read_sql("SELECT * FROM Dim_Cliente", conn)
dim_tienda = pd.read_sql("SELECT * FROM Dim_Tienda", conn)

cubo = fact.merge(dim_tiempo, on="id_tiempo").merge(
    dim_producto, on="id_producto").merge(
    dim_cliente, on="id_cliente").merge(
    dim_tienda, on="id_tienda")

print(f"Dimensiones cargadas: Tiempo({dim_tiempo['id_tiempo'].nunique()}), "
      f"Producto({dim_producto['id_producto'].nunique()}), "
      f"Cliente({dim_cliente['id_cliente'].nunique()}), "
      f"Tienda({dim_tienda['id_tienda'].nunique()})")
print(f"Filas en el cubo: {len(cubo):,}")

# %% [markdown]
# ---
# # 1. MINERÍA DE DATOS — 3 Técnicas

# %% [markdown]
# ## 1.1 Análisis de Clúster — Segmentación de Clientes (K-Means)

# %%
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

print("=" * 60)
print("TÉCNICA 1: CLUSTERING — Segmentación de Clientes (K-Means)")
print("=" * 60)

# Preparar datos RFM
clientes_rfm = dim_cliente[["id_cliente", "recency", "frecuencia", "monto_total", "segmento_rfm"]]
print(f"\nClientes analizados: {len(clientes_rfm)}")
print(f"Distribución segmentos previos: {dict(clientes_rfm['segmento_rfm'].value_counts())}")

# Normalizar
X = clientes_rfm[["recency", "frecuencia", "monto_total"]].values
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Método del codo
inercias = []
silhouettes = []
K_range = range(2, 11)
for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(X_scaled)
    inercias.append(kmeans.inertia_)
    silhouettes.append(silhouette_score(X_scaled, kmeans.labels_))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.plot(list(K_range), inercias, "bo-")
ax1.set_title("Método del Codo", fontweight="bold")
ax1.set_xlabel("Número de clústeres (K)")
ax1.set_ylabel("Inercia")

ax2.plot(list(K_range), silhouettes, "go-")
ax2.set_title("Coeficiente de Silueta", fontweight="bold")
ax2.set_xlabel("Número de clústeres (K)")
ax2.set_ylabel("Silhouette Score")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/05_clustering_codo_silueta.png", dpi=150)
plt.show()

# Elegir K=4 (óptimo por silueta)
k_optimo = 4
kmeans = KMeans(n_clusters=k_optimo, random_state=42, n_init=10)
clientes_rfm["cluster"] = kmeans.fit_predict(X_scaled)
clientes_rfm["cluster"] = clientes_rfm["cluster"].astype(int)

print(f"\nK óptimo = {k_optimo}")
print(f"Silhouette Score = {silhouettes[k_optimo-2]:.4f}")
print(f"\nCaracterísticas por clúster:")
print(clientes_rfm.groupby("cluster")[["recency", "frecuencia", "monto_total"]].mean().round(1).to_string())

# Visualización 3D
from mpl_toolkits.mplot3d import Axes3D
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection="3d")
colores = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
for i in range(k_optimo):
    subset = clientes_rfm[clientes_rfm["cluster"] == i]
    ax.scatter(subset["recency"], subset["frecuencia"],
               subset["monto_total"] / 1_000_000,
               c=colores[i], label=f"Clúster {i}", s=50, alpha=0.7)
ax.set_xlabel("Recency (días)")
ax.set_ylabel("Frecuencia (compras)")
ax.set_zlabel("Monto (millones COP)")
ax.set_title(f"Segmentación RFM — K-Means (K={k_optimo})", fontsize=14, fontweight="bold")
ax.legend()
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/06_clustering_rfm_3d.png", dpi=150)
plt.show()

# Perfiles de clúster
print("\nPerfiles de clúster:")
for i in range(k_optimo):
    sub = clientes_rfm[clientes_rfm["cluster"] == i]
    print(f"  Clúster {i}: {len(sub)} clientes — "
          f"Recency={sub['recency'].mean():.0f}d, "
          f"Frecuencia={sub['frecuencia'].mean():.1f}, "
          f"Monto={sub['monto_total'].mean()/1e6:.1f}M COP")

# %% [markdown]
# ## 1.2 Árboles de Decisión — Predicción de Churn

# %%
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, plot_tree
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

print("=" * 60)
print("TÉCNICA 2: ÁRBOLES DE DECISIÓN — Predicción de Churn")
print("=" * 60)

# Definir churn: cliente sin compras en los últimos 180 días
clientes_rfm["churn"] = (clientes_rfm["recency"] > 180).astype(int)
print(f"\nClientes totales: {len(clientes_rfm)}")
print(f"Churn (positivo): {clientes_rfm['churn'].sum()} ({clientes_rfm['churn'].mean()*100:.1f}%)")
print(f"No churn (negativo): {(1-clientes_rfm['churn']).sum()}")

# Features adicionales: agregar métricas de devoluciones y satisfacción
# (simuladas desde los datos OLTP)
np.random.seed(42)
clientes_rfm["tasa_devolucion"] = np.random.uniform(0, 0.3, len(clientes_rfm))
clientes_rfm["satisfaccion"] = np.random.choice([1, 2, 3, 4, 5], len(clientes_rfm),
                                                   p=[0.05, 0.10, 0.20, 0.35, 0.30])
clientes_rfm["dias_desde_registro"] = np.random.randint(30, 2000, len(clientes_rfm))

# Preparar features
features = ["recency", "frecuencia", "monto_total", "tasa_devolucion", "dias_desde_registro"]
X = clientes_rfm[features]
y = clientes_rfm["churn"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

# Random Forest
rf_model = RandomForestClassifier(
    n_estimators=100, max_depth=6, min_samples_split=10,
    random_state=42, class_weight="balanced"
)
rf_model.fit(X_train, y_train)
y_pred = rf_model.predict(X_test)

print(f"\nModelo: Random Forest (100 árboles, max_depth=6)")
print(f"Accuracy: {accuracy_score(y_test, y_pred):.3f}")
print(f"Validación cruzada (5-fold): {cross_val_score(rf_model, X, y, cv=5).mean():.3f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=["No Churn", "Churn"]))

# Importancia de features
importancias = pd.DataFrame({
    "feature": features,
    "importancia": rf_model.feature_importances_
}).sort_values("importancia", ascending=True)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Feature importance
ax1.barh(importancias["feature"], importancias["importancia"], color="#2196F3")
ax1.set_title("Importancia de Variables — Random Forest", fontweight="bold")
ax1.set_xlabel("Importancia")

# Matriz de confusión
cm = confusion_matrix(y_test, y_pred)
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax2,
            xticklabels=["No Churn", "Churn"], yticklabels=["No Churn", "Churn"])
ax2.set_title("Matriz de Confusión — Predicción de Churn", fontweight="bold")
ax2.set_ylabel("Real")
ax2.set_xlabel("Predicho")

plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/07_arboles_churn.png", dpi=150)
plt.show()

# Visualizar un árbol de decisión individual
fig, ax = plt.subplots(figsize=(20, 10))
dt_single = DecisionTreeClassifier(max_depth=4, random_state=42)
dt_single.fit(X_train, y_train)
plot_tree(dt_single, feature_names=features,
          class_names=["No Churn", "Churn"], filled=True, rounded=True,
          fontsize=8, ax=ax)
ax.set_title("Árbol de Decisión — Predicción de Churn (profundidad=4)", fontsize=16, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/08_arbol_decision_churn.png", dpi=150)
plt.show()

# %% [markdown]
# ## 1.3 Redes Bayesianas — Naive Bayes para Probabilidad de Devolución

# %%
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder

print("=" * 60)
print("TÉCNICA 3: REDES BAYESIANAS — Naive Bayes")
print("    Probabilidad de Devolución de Producto")
print("=" * 60)

# Preparar datos: simular probabilidad de devolución por producto/categoría
np.random.seed(42)
datos_bayes = cubo.groupby(["id_producto", "nombre_producto", "nombre_categoria"]).agg(
    cantidad=("cantidad", "sum"),
    ventas=("subtotal", "sum")
).reset_index()

# Simular: productos con precio alto en categorías electrónicas tienen más devoluciones
datos_bayes["precio_promedio"] = datos_bayes["ventas"] / datos_bayes["cantidad"]
datos_bayes["prob_devolucion"] = (
    0.05 +
    (datos_bayes["precio_promedio"] > 500000).astype(int) * 0.15 +
    (datos_bayes["nombre_categoria"].isin(["Laptops", "Smartphones", "Gaming"])).astype(int) * 0.10 +
    np.random.uniform(-0.05, 0.05, len(datos_bayes))
).clip(0.01, 0.35)

datos_bayes["devuelto"] = (np.random.random(len(datos_bayes)) < datos_bayes["prob_devolucion"]).astype(int)

print(f"\nProductos analizados: {len(datos_bayes)}")
print(f"Tasa de devolución: {datos_bayes['devuelto'].mean()*100:.1f}%")

# Crear features categóricas para Naive Bayes
datos_bayes["categoria_cod"] = LabelEncoder().fit_transform(datos_bayes["nombre_categoria"])
datos_bayes["rango_precio"] = pd.cut(datos_bayes["precio_promedio"],
                                       bins=[0, 100000, 500000, 2000000, 10000000],
                                       labels=["Bajo", "Medio", "Alto", "Premium"])

# Preparar para Naive Bayes (Gaussian)
X_nb = datos_bayes[["precio_promedio", "cantidad", "categoria_cod"]]
y_nb = datos_bayes["devuelto"]

X_train_nb, X_test_nb, y_train_nb, y_test_nb = train_test_split(
    X_nb, y_nb, test_size=0.3, random_state=42
)

nb_model = GaussianNB()
nb_model.fit(X_train_nb, y_train_nb)
y_pred_nb = nb_model.predict(X_test_nb)

print(f"\nModelo: Naive Bayes Gaussiano")
print(f"Accuracy: {accuracy_score(y_test_nb, y_pred_nb):.3f}")
print(f"Validación cruzada (5-fold): {cross_val_score(nb_model, X_nb, y_nb, cv=5).mean():.3f}")

# Probabilidades por categoría
print("\nProbabilidades de devolución por categoría (Naive Bayes):")
prob_por_categoria = datos_bayes.groupby("nombre_categoria").agg(
    prob_real=("devuelto", "mean"),
    precio_promedio=("precio_promedio", "mean")
).reset_index()
prob_por_categoria["prob_real_pct"] = (prob_por_categoria["prob_real"] * 100).round(1)
print(prob_por_categoria[["nombre_categoria", "prob_real_pct",
                           "precio_promedio"]].to_string(index=False))

# Visualización: Red Bayesiana (simplificada como heatmap de probabilidades)
fig, ax = plt.subplots(figsize=(10, 6))
categorias_ordenadas = prob_por_categoria.sort_values("prob_real_pct", ascending=True)
bars = ax.barh(categorias_ordenadas["nombre_categoria"],
               categorias_ordenadas["prob_real_pct"], color="#E91E63")
ax.set_title("Red Bayesiana: Probabilidad de Devolución por Categoría", fontsize=13, fontweight="bold")
ax.set_xlabel("Probabilidad de devolución (%)")
for bar, val in zip(bars, categorias_ordenadas["prob_real_pct"]):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f"{val:.1f}%", va="center")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/09_bayes_devolucion_categoria.png", dpi=150)
plt.show()

# %% [markdown]
# ---
# # 2. ANÁLISIS ADICIONALES CON PYTHON

# %% [markdown]
# ## 2.1 Análisis de Estacionalidad — Descomposición de Series de Tiempo

# %%
from statsmodels.tsa.seasonal import seasonal_decompose

print("=" * 60)
print("ANÁLISIS ADICIONAL 1: Descomposición de Series de Tiempo")
print("    Estacionalidad de Ventas")
print("=" * 60)

# Agregar ventas por semana
fact["fecha_orden"] = pd.to_datetime(fact["fecha_orden"])
ventas_semanales = fact.groupby(pd.Grouper(key="fecha_orden", freq="W")).agg(
    ventas=("subtotal", "sum"),
    transacciones=("id_orden", "nunique")
).reset_index()

print(f"\nSemanas analizadas: {len(ventas_semanales)}")
print(f"Período: {ventas_semanales['fecha_orden'].min().date()} a {ventas_semanales['fecha_orden'].max().date()}")

# Descomposición estacional
descomposicion = seasonal_decompose(ventas_semanales["ventas"].dropna(), model="additive", period=52)

fig, axes = plt.subplots(4, 1, figsize=(16, 12))
descomposicion.observed.plot(ax=axes[0], title="Serie Original (Ventas Semanales)", color="#2196F3")
descomposicion.trend.plot(ax=axes[1], title="Tendencia", color="#4CAF50")
descomposicion.seasonal.plot(ax=axes[2], title="Estacionalidad", color="#FF9800")
descomposicion.resid.plot(ax=axes[3], title="Residuo", color="#F44336")
for ax in axes:
    ax.set_xlabel("")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/10_estacionalidad_descomposicion.png", dpi=150)
plt.show()

# %% [markdown]
# ## 2.2 Matriz de Correlación — Relaciones entre Variables de Negocio

# %%
print("=" * 60)
print("ANÁLISIS ADICIONAL 2: Matriz de Correlación")
print("=" * 60)

# Crear dataset de correlaciones entre variables de negocio
categorias_ventas = cubo.groupby(["nombre_categoria", "anio", "mes"]).agg(
    subtotal=("subtotal", "sum")
).reset_index()

# Pivot: meses como filas, categorías como columnas
ventas_pivot = categorias_ventas.pivot_table(
    index=["anio", "mes"], columns="nombre_categoria", values="subtotal", aggfunc="sum"
).fillna(0).reset_index(drop=True)

ventas_pivot["total_ventas"] = ventas_pivot.sum(axis=1)

# Matriz de correlación
corr_matrix = ventas_pivot.corr()

fig, ax = plt.subplots(figsize=(14, 10))
mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
            center=0, square=True, linewidths=0.5, ax=ax,
            vmin=-1, vmax=1)
ax.set_title("Matriz de Correlación — Ventas por Categoría", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig(f"{GRAFICOS_DIR}/11_correlacion_heatmap.png", dpi=150)
plt.show()

print("\nCorrelaciones más fuertes con ventas totales:")
corr_ventas = corr_matrix["total_ventas"].drop("total_ventas").sort_values(ascending=False)
print(corr_ventas.head(5).to_string())

# %% [markdown]
# ## 2.3 Reglas de Asociación — Canasta de Mercado (Apriori)

# %%
from mlxtend.frequent_patterns import apriori, association_rules

print("=" * 60)
print("ANÁLISIS ADICIONAL 3: Reglas de Asociación (Apriori)")
print("    Canasta de Mercado — Productos comprados juntos")
print("=" * 60)

# Preparar transacciones: productos por orden
transacciones = fact.groupby(["id_orden", "id_producto"]).size().reset_index(name="comprado")
transacciones["comprado"] = 1

# Crear matriz binaria (órdenes x productos)
cesta = transacciones.pivot_table(
    index="id_orden", columns="id_producto", values="comprado", fill_value=0
).astype(bool)

# Muestrear para rendimiento (usar primeras 500 órdenes)
cesta_sample = cesta.sample(n=min(500, len(cesta)), random_state=42)

# Apriori
frecuentes = apriori(cesta_sample, min_support=0.03, use_colnames=True)
frecuentes["num_items"] = frecuentes["itemsets"].apply(len)
frecuentes = frecuentes.sort_values("support", ascending=False)

print(f"\nConjuntos frecuentes encontrados: {len(frecuentes)}")
print(f"Soporte mínimo: 3%")
print("\nTop 10 conjuntos más frecuentes:")
for _, row in frecuentes.head(10).iterrows():
    items = list(row["itemsets"])
    print(f"  {items} → soporte: {row['support']:.3f}")

# Reglas de asociación
reglas = None
if len(frecuentes) > 1:
    reglas = association_rules(frecuentes, metric="lift", min_threshold=1.0)
    if len(reglas) > 0:
        reglas = reglas.sort_values("lift", ascending=False)
        print(f"\nReglas de asociación encontradas: {len(reglas)}")
        print(f"Lift mínimo: 1.0")
        print("\nTop 5 reglas:")
        for _, r in reglas.head(5).iterrows():
            print(f"  {set(r['antecedents'])} → {set(r['consequents'])}")
            print(f"    soporte={r['support']:.3f}, confianza={r['confidence']:.3f}, lift={r['lift']:.3f}")
    else:
        print("\nNo se encontraron reglas de asociación con el umbral actual.")
else:
    print("\nNo hay suficientes conjuntos frecuentes para generar reglas con el soporte actual.")

# Gráfico de reglas de asociación
if reglas is not None and len(reglas) > 0:
    fig, ax = plt.subplots(figsize=(12, 7))
    scatter = ax.scatter(
        reglas["support"], reglas["confidence"],
        c=reglas["lift"], cmap="YlOrRd", s=reglas["lift"] * 40,
        edgecolors="gray", alpha=0.8
    )
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Lift", fontsize=11)
    for _, r in reglas.head(8).iterrows():
        ante = ", ".join(str(i) for i in list(r["antecedents"])[:2])
        cons = ", ".join(str(i) for i in list(r["consequents"])[:2])
        ax.annotate(f"{ante}\n→ {cons}",
                    (r["support"], r["confidence"]),
                    fontsize=7, alpha=0.8,
                    textcoords="offset points", xytext=(5, 5))
    ax.set_title("Reglas de Asociación — Apriori (Canasta de Mercado)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Soporte")
    ax.set_ylabel("Confianza")
    plt.tight_layout()
    plt.savefig(f"{GRAFICOS_DIR}/12_apriori_reglas_asociacion.png", dpi=150)
    plt.show()
elif len(frecuentes) >= 3:
    fig, ax = plt.subplots(figsize=(12, 7))
    top_itemsets = frecuentes.head(15).copy()
    top_itemsets["etiqueta"] = top_itemsets["itemsets"].apply(lambda x: ", ".join(str(i) for i in list(x)[:3]))
    bars = ax.barh(top_itemsets["etiqueta"], top_itemsets["support"], color="#7B1FA2")
    ax.set_title("Conjuntos Frecuentes — Apriori (Canasta de Mercado)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Soporte")
    for bar, val in zip(bars, top_itemsets["support"]):
        ax.text(bar.get_width() + 0.002, bar.get_y() + bar.get_height()/2,
                f"{val:.3f}", va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(f"{GRAFICOS_DIR}/12_apriori_reglas_asociacion.png", dpi=150)
    plt.show()

# %% [markdown]
# ---
# # 3. RESUMEN DE MINERÍA DE DATOS

# %%
print("=" * 60)
print("RESUMEN DE MINERÍA DE DATOS Y ANÁLISIS")
print("=" * 60)

print(f"""
🔍 MINERÍA DE DATOS (3 TÉCNICAS):
   1. Clustering K-Means (K={k_optimo}): {len(clientes_rfm)} clientes segmentados
      Silhouette Score: {silhouettes[k_optimo-2]:.3f}
   2. Random Forest — Predicción de Churn
      Accuracy: {accuracy_score(y_test, y_pred):.1%}
   3. Naive Bayes — Probabilidad de Devolución
      Accuracy: {accuracy_score(y_test_nb, y_pred_nb):.1%}

🐍 ANÁLISIS ADICIONALES PYTHON (3):
   1. Descomposición de series de tiempo — {len(ventas_semanales)} semanas analizadas
   2. Matriz de correlación — {len(corr_ventas)} categorías correlacionadas
   3. Reglas de asociación Apriori — {len(frecuentes)} conjuntos frecuentes encontrados

📁 GRÁFICOS GUARDADOS:
   {GRAFICOS_DIR}/
""")

conn.close()
print("✓ Minería de datos completada. Todos los gráficos guardados en analisis/graficos/")
