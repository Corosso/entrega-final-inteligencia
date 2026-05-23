Guía paso a paso — Dashboard en Power BI

## Proyecto Final BI · Retail de Tecnología

Esta guía permite construir el dashboard de Power BI a partir de los datos ya exportados
del Data Warehouse. Los archivos fuente están en la carpeta `dashboard/` (8 dimensiones +
1 tabla de hechos en formato CSV, codificación UTF-8).

> **Nota**: El archivo `.pbix` no se incluye porque requiere Power BI Desktop (Windows).
> Siguiendo esta guía se reconstruye en ~15 minutos. Al final se indica cómo exportar la
> captura del dashboard para incrustarla en el informe (Figura del Dashboard).

---

## Paso 0 — Requisitos

- **Power BI Desktop** (gratuito): https://powerbi.microsoft.com/desktop/
- Carpeta `dashboard/` con los CSV:
  `Fact_Ventas.csv`, `Dim_Tiempo.csv`, `Dim_Producto.csv`, `Dim_Cliente.csv`,
  `Dim_Tienda.csv`, `Dim_Empleado.csv`, `Dim_MetodoPago.csv`, `Dim_Proveedor.csv`,
  `Dim_Campana.csv`.

---

## Paso 1 — Importar los datos

1. Abrir Power BI Desktop → **Inicio → Obtener datos → Texto/CSV**.
2. Importar **cada** archivo CSV de la carpeta `dashboard/` (uno por uno o con
   **Obtener datos → Carpeta** para cargarlos todos a la vez).
3. En el cuadro de vista previa, verificar que el **delimitador** sea coma y el
   **origen de archivo** sea *65001: Unicode (UTF-8)* (para que las tildes y la ñ se vean
   bien). Pulsar **Cargar**.
4. Repetir hasta tener las 9 tablas en el panel **Datos**.

---

## Paso 2 — Crear la tabla de calendario (recomendado para inteligencia de tiempo)

`Dim_Tiempo` ya trae las jerarquías, pero para que funcionen las funciones DAX de tiempo
(`SAMEPERIODLASTYEAR`, etc.) conviene marcarla como tabla de fechas:

1. Seleccionar `Dim_Tiempo` en el panel Datos.
2. Asegurarse de que la columna `fecha` sea de tipo **Fecha** (no texto).
   Si está como texto: pestaña de la columna → **Tipo de datos → Fecha**.
3. Menú **Herramientas de tabla → Marcar como tabla de fechas** → columna `fecha`.

---

## Paso 3 — Construir el modelo estrella (relaciones)

Ir a la **Vista de Modelo** (icono de diagrama a la izquierda) y crear las relaciones
arrastrando desde `Fact_Ventas` hacia cada dimensión. Todas son **muchos-a-uno** (la
tabla de hechos en el lado *muchos*), de **dirección de filtro simple** (de la dimensión
hacia los hechos):

| Desde (Fact_Ventas) | Hacia (Dimensión) | Columna clave |
|---|---|---|
| `id_tiempo` | `Dim_Tiempo` | `id_tiempo` |
| `id_producto` | `Dim_Producto` | `id_producto` |
| `id_cliente` | `Dim_Cliente` | `id_cliente` |
| `id_tienda` | `Dim_Tienda` | `id_tienda` |
| `id_empleado` | `Dim_Empleado` | `id_empleado` |
| `id_metodo_pago` | `Dim_MetodoPago` | `id_metodo_pago` |

Dimensiones complementarias (no se enlazan directamente a la tabla de hechos):

- `Dim_Proveedor` → se relaciona con `Dim_Producto` por `id_proveedor` →
  `id_proveedor_origen` (esquema copo de nieve, opcional).
- `Dim_Campana` → tabla informativa de campañas de marketing (sin clave en los hechos);
  se deja sin relación o se usa en una página aparte.

> **Verificación**: el diagrama debe verse como una estrella con `Fact_Ventas` al centro
> y las 6 dimensiones alrededor (igual que la Figura 3 del informe).

---

## Paso 4 — Crear las medidas DAX

Clic derecho en `Fact_Ventas` → **Nueva medida**, y crear una por una:

```dax
Total Ventas = SUM(Fact_Ventas[subtotal])
```

```dax
Transacciones = DISTINCTCOUNT(Fact_Ventas[id_orden])
```

```dax
Unidades Vendidas = SUM(Fact_Ventas[cantidad])
```

```dax
Ticket Promedio = DIVIDE([Total Ventas], [Transacciones])
```

```dax
N Clientes = DISTINCTCOUNT(Fact_Ventas[id_cliente])
```

```dax
Ventas Anio Anterior =
CALCULATE([Total Ventas], SAMEPERIODLASTYEAR(Dim_Tiempo[fecha]))
```

```dax
Crecimiento YoY % =
DIVIDE([Total Ventas] - [Ventas Anio Anterior], [Ventas Anio Anterior])
```

```dax
Margen Promedio % = AVERAGE(Dim_Producto[margen_pct])
```

Medida de margen ponderado (más precisa, opcional). Requiere el costo: usa
`precio_unitario` y `costo_unitario` de `Dim_Producto` vía la relación:

```dax
Costo Total =
SUMX(Fact_Ventas, Fact_Ventas[cantidad] * RELATED(Dim_Producto[costo_unitario]))
```

```dax
Margen Ponderado % =
DIVIDE([Total Ventas] - [Costo Total], [Total Ventas])
```

Formatear: selecciona cada medida y en **Herramientas de medida** asigna formato
**Moneda** (Total Ventas, Ticket, Costo) o **Porcentaje** (YoY, Margen) y los decimales.

---

## Paso 5 — Diseñar el dashboard (página principal)

Arrastra estos elementos desde el panel **Visualizaciones**:

| Visual | Tipo | Campos |
|---|---|---|
| Total Ventas | **Tarjeta** | `[Total Ventas]` |
| Transacciones | **Tarjeta** | `[Transacciones]` |
| Crecimiento YoY | **Tarjeta** | `[Crecimiento YoY %]` |
| Margen Promedio | **Tarjeta** | `[Margen Promedio %]` |
| Ventas por mes | **Gráfico de líneas** | Eje X: `Dim_Tiempo[fecha]` (jerarquía año/mes) · Valores: `[Total Ventas]` |
| Ventas por categoría | **Gráfico de barras** | Eje Y: `Dim_Producto[nombre_categoria]` · Valores: `[Total Ventas]` |
| Ventas por ciudad/región | **Mapa** | Ubicación: `Dim_Cliente[nombre_ciudad]` (o `region`) · Tamaño: `[Total Ventas]` |
| Top 10 productos | **Tabla** | `Dim_Producto[nombre_producto]`, `[Total Ventas]` (filtro Top N = 10 por Total Ventas) |
| Margen por categoría | **Barras** | Eje: `Dim_Producto[nombre_categoria]` · Valores: `[Margen Promedio %]` |

**Segmentadores** (filtros interactivos), arrastrando como visual **Segmentación**:

- `Dim_Tiempo[anio]` (o `nombre_mes`)
- `Dim_Cliente[region]`
- `Dim_Producto[nombre_categoria]`

**Semáforos (formato condicional)** para los KPI, según el informe:

- *Crecimiento YoY*: verde > +5 %, amarillo entre −5 % y +5 %, rojo < −5 %.
- *Margen*: verde > 25 %, amarillo 10–25 %, rojo < 10 %.

Se aplica en la tarjeta/tabla con **Formato → Color de fuente → fx (formato
condicional) → Reglas**.

---

## Paso 6 — (Opcional) Segunda página de análisis de clientes

- Tabla con `Dim_Cliente[segmento_rfm]` y medidas `[N Clientes]`, `[Total Ventas]`.
- Gráfico de dispersión: `recency` vs `frecuencia` con tamaño `monto_total`.
- Segmentador por `zona` / `region`.

---

## Paso 7 — Exportar la captura para el informe (Figura del Dashboard)

La estructura exige mostrar el dashboard (Figure 7 de las directrices). Una vez armado:

1. **Archivo → Exportar → Exportar a PDF** (exporta todas las páginas), **o**
2. Captura de pantalla de la página principal → guardarla como
   `analisis/graficos/15_dashboard_powerbi.png`.

Para incluirla en el informe tienes dos opciones:

- **Manual (más rápido)**: pega la captura directamente en
  `docs/Informe_Final_BI.docx`, dentro de la sección **7.7 Dashboard y KPIs**, con el pie
  *"Figura 15. Dashboard interactivo en Power BI."*. Las figuras 1–14 ya están en el
  documento; esta sería la 15.
- **Automática**: guarda la captura como `analisis/graficos/15_dashboard_powerbi.png`,
  descomenta la entrada `"7.7 Dashboard"` que ya está preparada (comentada) en el
  diccionario `FIGURAS` de [docs/generar_docx.py](generar_docx.py) y vuelve a ejecutar
  `python docs/generar_docx.py`. La figura del dashboard se insertará tras el párrafo de
  la sección 7.7.

---

## Resumen de cifras para sustentar el dashboard

- **Total Ventas**: $147.272.278.170 COP (idéntico al cubo OLAP)
- **Transacciones**: 5.000 órdenes · 22.684 líneas de detalle
- **Crecimiento YoY**: +1,3 % promedio (2024 −0,4 %, 2025 +3,0 %)
- **Margen promedio**: 42,9 % (Laptops 48,2 % … Audio 37,8 %)
- **Modelo**: estrella, 6 relaciones activas desde `Fact_Ventas`
