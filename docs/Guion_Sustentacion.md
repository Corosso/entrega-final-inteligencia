# Guion de Sustentación — Proyecto Final BI

## Diapositiva 1: Portada
**Título**: Inteligencia de Negocios aplicada al Retail de Tecnología
**Subtítulo**: Data Warehouse, OLAP, SCD, KPIs y Minería de Datos
**Autor**: Federico Rodríguez | ITM | 2026-1

---

## Diapositiva 2: Problema y Justificación
- **Problema**: Empresa retail con datos dispersos en 4 fuentes distintas (SQLite, CSV, Excel, XML). Sin visión integral del negocio.
- **Solución BI**: Integrar todo en un Data Warehouse → análisis multidimensional → dashboards → minería de datos.
- **Metodología**: CRISP-DM + Ciclo de Vida Kimball

**Hablar**: "La empresa tenía datos de ventas en una base SQLite, proveedores en Excel, datos de mercado en CSV y campañas en XML. Era imposible cruzar esta información para tomar decisiones. Implementamos un proceso ETL completo que unifica estas 4 fuentes en un solo Data Warehouse."

---

## Diapositiva 3: Dataset y Diseño de BD
- **65,177 registros** en 18 tablas OLTP → supera el mínimo de 30,000
- 4 tipos de fuentes: SQLite + CSV + Excel + XML
- **Diagrama ER**: 18 entidades con relaciones (mostrar imagen del diagrama Mermaid)

**Hablar**: "Generamos un dataset sintético de ventas retail con distribuciones realistas: 5,000 órdenes, 22,684 líneas de detalle, 500 clientes, 80 productos en 10 categorías. Usamos 4 tipos de fuentes diferentes porque la rúbrica lo exige."

---

## Diapositiva 4: Proceso ETL
- **Extract**: 4 fuentes → 65K registros
- **Transform**: Limpieza, RFM, segmentación, márgenes, unión de archivos (proveedores internos + externos)
- **Load**: DW con 8 dimensiones + 1 tabla de hechos (22,684 filas)
- **Herramienta**: Python (pandas, sqlalchemy)

**Hablar**: "El ETL extrae desde SQLite, CSV, Excel y XML. Las transformaciones incluyen cálculo de métricas RFM para cada cliente, márgenes de ganancia por producto, y la unión de archivos — combinamos proveedores internos con externos del Excel."

---

## Diapositiva 5: SCD Tipo 2 — El diferenciador (15 puntos en rúbrica)
- **Dim_Producto**: 244 versiones (80 productos, 62 con cambios de precio)
  - Ej: Logitech Air-002 pasó de $3.2M → $2.67M → $2.78M → $2.95M
- **Dim_Cliente**: 2,110 versiones (500 clientes, 499 con cambios de segmento)
  - Ej: Cliente #1 evolucionó: En riesgo → Regular → En riesgo → Regular → VIP

**Hablar**: "Esto es clave para la rúbrica — SCD Tipo 2 con alta funcionalidad vale 15 puntos. Implementamos historial completo de cambios: cuando un producto cambia de precio, no sobrescribimos, creamos una nueva fila con fecha de vigencia. Lo mismo para clientes: rastreamos su evolución de segmento RFM cada 6 meses."

---

## Diapositiva 6: Cubo OLAP + Medidas Precalculadas
- **5 niveles de granularidad**:
  - N0: Transacción (22,684) → N1: Producto×Día (19,998) → N2: Categoría×Mes (360) → N3: Categoría×Trimestre (120) → N4: Año (3)
- **Consistencia**: $147,272,278,170 COP en TODOS los niveles
- **Operaciones**: Roll-up, Drill-down, Slice, Dice, Pivot (mostrar ejemplos de gráficos)

**Hablar**: "El cubo tiene medidas precalculadas en 5 niveles. Lo importante: las ventas totales son idénticas en todos los niveles — $147 mil millones — lo que valida la integridad. Implementamos todas las operaciones OLAP que pide la rúbrica."

---

## Diapositiva 7: KPIs del Negocio
- **KPI 1 — Crecimiento YoY**: +1.3% promedio (2024: -0.4%, 2025: +3.0%)
  - Umbrales: verde >+5%, amarillo ±5%, rojo <-5%
- **KPI 2 — Margen por Categoría**: Promedio 42.9%
  - Laptops 48.2% | Audio 37.8%
  - Umbrales: verde >25%, amarillo 10-25%, rojo <10%

**(Mostrar gráficos 03 y 04)**

**Hablar**: "Dos KPIs alineados con objetivos de negocio. El crecimiento se recuperó en 2025. Los márgenes son saludables pero hay variabilidad: Laptops genera 48% de margen, Audio solo 38%. Esto permite decisiones sobre qué categorías impulsar."

---

## Diapositiva 8: Minería de Datos — 3 Técnicas
1. **Clustering K-Means** (K=4, Silhouette 0.34)
   - 4 segmentos RFM: VIP (31.8%), Regular, En riesgo (19.2%), Perdido
   - (mostrar gráfico 3D)
2. **Random Forest — Churn** (Accuracy 100%)
   - Variables clave: recency, frecuencia, días desde registro
   - (mostrar matriz de confusión y árbol)
3. **Naive Bayes — Devoluciones** (Accuracy 87.5%)
   - Mayor riesgo: Monitores 33.3%, Smartphones 33.3%
   - (mostrar gráfico de barras)

**Hablar**: "Aplicamos las 3 técnicas que pide la rúbrica. El clustering segmenta clientes para marketing dirigido. El Random Forest predice quién va a abandonar. El Naive Bayes calcula probabilidad de devolución por categoría."

---

## Diapositiva 9: Análisis Adicionales Python
1. **Estacionalidad**: Descomposición de 158 semanas (tendencia + estacionalidad + residuo)
2. **Correlación**: Mapa de calor — Accesorios (0.79) es el mejor predictor de ventas totales
3. **Apriori**: 80 conjuntos frecuentes en canasta de mercado (soporte 3%)

**(Mostrar gráficos 10, 11)**

**Hablar**: "Tres análisis extra con Python. La estacionalidad muestra picos de fin de año. La correlación revela qué categorías predicen mejor el desempeño general. El Apriori encuentra productos que se compran juntos para estrategias de cross-selling."

---

## Diapositiva 10: Dashboard Power BI
- 9 tablas exportadas del DW a CSV
- Relaciones estrella: Fact_Ventas → 6 dimensiones
- **Medidas DAX**: Total Ventas, Transacciones, Crecimiento YoY, Margen Promedio
- **Visualizaciones**: KPIs, tendencia, barras por categoría, mapa por ciudad, top productos

**Hablar**: "Los datos del DW se exportaron a CSV para Power BI. Creamos el modelo estrella con relaciones, medidas DAX, y un dashboard interactivo con filtros por fecha, región y categoría."

---

## Diapositiva 11: Conclusiones
1. Integración de 4 fuentes → DW unificado con 22K registros
2. SCD Tipo 2 → historia de precios (244 versiones) y segmentos (2,110 versiones)
3. Cubo OLAP → 5 niveles, medidas consistentes ($147.3B)
4. KPIs → crecimiento +1.3% YoY, margen 42.9%
5. Minería → 3 técnicas + 3 análisis Python completos
6. Power BI → dashboard gerencial listo para decisiones

---

## Diapositiva 12: Recomendaciones
1. Migrar ETL a Pentaho/Airflow para producción
2. Campañas de retención para el 19.2% de clientes "En riesgo"
3. Revisar políticas de devolución en Monitores (33.3%) y Smartphones (33.3%)
4. Activar estrategias de cross-selling basadas en reglas Apriori

---

## Diapositiva 13: ¡Gracias! ¿Preguntas?
- Demo en vivo disponible (Power BI, Python notebook, gráficos)
- Repositorio con todo el código y datos

---

## Tips para la sustentación

### Lo que más puntúa en la rúbrica (máximo 150-181 pts → nota 5):
- **SCD Tipo 2** (15 pts) — Enfatizar que hay historial de cambios con fechas de vigencia
- **Cubo OLAP** (20 pts) — Mostrar medidas precalculadas y consistencia entre niveles
- **Dashboard** (20 pts) — Demostrar Power BI conectado a los datos
- **KPIs** (10 pts) — Explicar umbrales y cómo se usan para decisiones
- **Minería de datos** (10 pts) — Mostrar los 3 modelos funcionando
- **Sustentación** (10 pts) — Demostrar conocimiento y responder preguntas

### Posibles preguntas del profesor:
1. "¿Por qué SCD Tipo 2 y no Tipo 1 o 3?" → Porque necesitamos preservar el historial completo de precios y segmentos para análisis de tendencias.
2. "¿Cómo garantizan la calidad de los datos?" → Validación de integridad referencial, sin nulos en campos críticos, medidas consistentes en todos los niveles del cubo.
3. "¿Qué pasaría si llegan nuevos datos mañana?" → El SCD Tipo 2 está diseñado para cargas incrementales: se insertan nuevas versiones para productos/servicios que cambiaron, se actualiza es_actual y fecha_fin.
4. "¿Por qué eligieron Random Forest y no otro algoritmo?" → Random Forest maneja bien datos desbalanceados (class_weight='balanced'), da importancia de variables interpretable, y evita overfitting por ensamble.
5. "¿Cómo escala esto a 1 millón de registros?" → Migrando a SQL Server (ya está dockerizado), usando índices en las llaves foráneas, y particionando Fact_Ventas por año.
