# 13. Dashboard Sevilla IA v2

## 1. Objetivo del dashboard

El dashboard Sevilla IA v2 es la interfaz de explotación visual de la fase IA v2 de Hidden Gems.

Su objetivo es permitir explorar de forma interactiva:

- el ranking Hidden Gems Sevilla v2;
- los candidatos seleccionados;
- la distribución territorial por distrito y barrio;
- los platos y locales destacados;
- la evidencia y calidad de las señales;
- la comparación entre ranking v1 y ranking v2;
- las menciones y reseñas que justifican cada candidato;
- la explicación conceptual del cálculo de la puntuación.

El dashboard no sustituye a los artefactos técnicos. Es una capa de presentación para análisis, validación y demostración.

---

## 2. Archivo principal

El dashboard se encuentra en:

```text
dashboard/streamlit_sevilla_v2_app.py
```

Comando de ejecución desde la raíz del repositorio:

```powershell
streamlit run dashboard/streamlit_sevilla_v2_app.py
```

Dependencias principales:

```powershell
pip install streamlit plotly pandas
```

Estas dependencias deben estar reflejadas en `requirements.txt`.

---

## 3. Carpeta de datos consumida

Por defecto, el dashboard carga los datos desde:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Esta carpeta es generada por:

```text
scripts/export_sevilla_dashboard_data_v2.py
```

y contiene todos los CSV/JSON necesarios para la visualización.

---

## 4. Export utilizado

El export del dashboard v2 se genera con un comando similar a:

```powershell
python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --include-mentions `
  --examples-per-candidate 5 `
  --include-full-review-text `
  --strict
```

El parámetro `--include-full-review-text` permite que el dashboard muestre el texto completo de reseñas en la vista de detalle cuando esté disponible.

El parámetro `--coordinates-path` permite reutilizar coordenadas reales del dashboard v1 u otro archivo compatible.

---

## 5. Archivos principales del dashboard

La carpeta `dashboard_v2` incluye:

| Archivo | Uso en dashboard |
|---|---|
| `dashboard_metadata.json` | Metadatos de ejecución del export. |
| `kpi_summary.json` | KPIs principales del ranking v2. |
| `ranking_detail.csv` | Todos los candidatos puntuados. |
| `selected_candidates.csv` | Candidatos seleccionados. |
| `top_global.csv` | Ranking global seleccionado. |
| `top_by_district.csv` | Top candidatos por distrito. |
| `top_by_neighborhood.csv` | Top candidatos por barrio. |
| `top_by_dish.csv` | Top candidatos por plato. |
| `district_summary.csv` | Resumen agregado por distrito. |
| `neighborhood_summary.csv` | Resumen agregado por barrio. |
| `dish_summary.csv` | Resumen agregado por plato. |
| `place_summary.csv` | Resumen agregado por local. |
| `tier_summary.csv` | Distribución por tier de ranking. |
| `evidence_summary.csv` | Distribución por tier de evidencia. |
| `quality_summary.csv` | Distribución por calidad agregada. |
| `filter_options.json` | Valores disponibles para filtros. |
| `data_contract.json` | Contrato de datos del dashboard. |
| `mention_examples.csv` | Ejemplos de menciones/reseñas. |
| `place_coordinates.csv` | Coordenadas reales cuando están disponibles. |
| `comparison/` | Artefactos comparativos v1 vs v2. |

---

## 6. KPIs mostrados

El dashboard muestra los principales KPIs de la fase IA v2:

| KPI | Valor |
|---|---:|
| Candidatos puntuados v2 | 2.335 |
| Candidatos seleccionados v2 | 268 |
| Locales seleccionados | 198 |
| Platos seleccionados | 40 |
| Barrios seleccionados | 67 |
| Distritos seleccionados | 11 |
| Menciones seleccionadas | 651 |
| Reviews seleccionadas | 627 |
| Score medio seleccionado | 80,58 |
| Score máximo seleccionado | 91,65 |
| Score mínimo seleccionado | 66,12 |
| Filas production-ready | 0 |

La ausencia de filas `production_ready` es deliberada: el ranking se presenta como experimental.

---

## 7. Pestañas o secciones del dashboard

El dashboard está organizado en varias secciones.

### 7.1 Resumen ejecutivo

Muestra los KPIs principales y una visión rápida del ranking IA v2.

Incluye:

- número de candidatos;
- locales, platos, barrios y distritos;
- distribución de tiers;
- comparación breve con v1;
- advertencias sobre estado experimental.

---

### 7.2 Ranking IA v2

Permite explorar los candidatos seleccionados.

Filtros principales:

- distrito;
- barrio;
- plato;
- local;
- tier;
- evidence tier;
- quality tier;
- rango de score;
- mínimo de menciones;
- mínimo de reviews.

La tabla principal muestra:

- rank;
- local;
- plato;
- distrito;
- barrio;
- score;
- tier;
- menciones;
- reviews;
- ratio positivo;
- ratio negativo;
- evidencia;
- calidad;
- explicación.

---

### 7.3 Territorio

Analiza la distribución geográfica del ranking.

Incluye:

- resumen por distrito;
- resumen por barrio;
- rankings territoriales;
- mapa interactivo.

El mapa usa, en orden de preferencia:

1. coordenadas reales (`latitude_std`, `longitude_std`);
2. `place_coordinates.csv`, si está disponible;
3. fallback aproximado por distrito/barrio si no hay coordenadas reales.

Esto permite visualizar los resultados sobre el territorio y detectar concentración o cobertura por zonas.

---

### 7.4 Platos y locales

Permite analizar:

- platos más frecuentes;
- locales con más candidatos seleccionados;
- score medio por plato;
- número de barrios por plato;
- candidatos top por plato.

Esta sección es útil para responder preguntas como:

```text
¿Qué platos aparecen más en el ranking?
¿Qué locales concentran más señales?
¿Qué platos tienen mejor score medio?
```

---

### 7.5 Evidencia y calidad

Muestra los niveles de confianza del ranking.

Incluye:

- distribución por `evidence_tier`;
- distribución por `quality_tier`;
- relación entre score y número de reviews;
- relación entre score y evidencia;
- filas de baja calidad o revisión.

Esta sección es clave para evitar sobreinterpretar señales débiles.

---

### 7.6 Comparativa v1 vs v2

Integra los artefactos generados por:

```text
scripts/compare_sevilla_ranking_v1_vs_v2.py
```

Muestra:

- solapamiento entre v1 y v2;
- candidatos coincidentes;
- candidatos solo v2;
- candidatos solo v1;
- cambios de score;
- cambios de ranking;
- cambios por distrito, barrio y plato.

KPIs integrados:

| Métrica | Valor |
|---|---:|
| Candidatos v1 | 150 |
| Candidatos v2 | 268 |
| Coincidencias | 119 |
| Cobertura de v1 en v2 | 79,3 % |
| Jaccard overlap | 0,397993 |
| Delta locales | +76 |
| Delta barrios | +12 |

---

### 7.7 Reseñas y menciones

Esta sección permite consultar la evidencia textual detrás de los candidatos.

Funcionalidades:

- seleccionar local;
- seleccionar plato dentro del local;
- filtrar por sentimiento;
- filtrar por confianza;
- filtrar por rating;
- ver mención detectada;
- ver plato normalizado;
- ver sentimiento ABSA;
- ver score del candidato;
- ver contexto local;
- ver texto completo de reseña, si está disponible.

Esta sección es importante porque permite comprobar por qué un candidato ha sido seleccionado.

Ejemplo de uso:

```text
Seleccionar "Café Los Pilares Bar"
→ seleccionar "churros"
→ revisar menciones positivas
→ leer contexto/reseñas asociadas
```

---

### 7.8 Puntuación

Explica cómo se calcula conceptualmente `hidden_gem_score_v2`.

La fórmula conceptual es:

```text
hidden_gem_score_v2 =
  sentimiento ABSA ponderado
+ evidencia de menciones/reviews
+ calidad de señal
+ consenso híbrido + NER
+ especificidad/rareza del plato
+ señal débil de rating
- penalización por negativos
- penalización por baja evidencia
- penalización por baja confianza
- penalización por revisión manual
```

El dashboard no pretende exponer todos los detalles internos de pesos como una fórmula matemática cerrada, sino facilitar una interpretación clara.

Componentes visibles:

| Componente | Interpretación |
|---|---|
| `score_std` | Score final normalizado 0-100. |
| `positive_ratio_std` | Proporción de menciones positivas. |
| `negative_ratio_std` | Proporción de menciones negativas. |
| `mention_count_std` | Número de menciones. |
| `review_count_std` | Número de reviews únicas. |
| `evidence_tier_std` | Nivel de evidencia. |
| `quality_tier_std` | Nivel de calidad agregada. |
| `explanation_std` | Explicación textual generada para el candidato. |

---

### 7.9 Contrato de datos y artefactos

Muestra o resume el contenido de:

```text
data_contract.json
dashboard_metadata.json
dashboard_export_summary.json
```

Su objetivo es dejar claro:

- qué archivos alimentan el dashboard;
- qué granularidad tiene cada archivo;
- qué columnas son obligatorias;
- qué limitaciones se deben tener en cuenta;
- cuándo fue generado el export.

---

## 8. Filtros recomendados

Para presentación y validación, se recomienda empezar con:

```text
Tier: top_hidden_gem + strong_hidden_gem
Evidence: solid + strong
Quality: high + medium
Min reviews: 2
Min mentions: 2
```

Para exploración amplia, se pueden incluir también:

```text
promising_hidden_gem
exploratory_hidden_gem
evidence = emerging
quality = low
```

pero estos casos deben presentarse como señales exploratorias.

---

## 9. Interpretación visual

El dashboard debe evitar dar la impresión de que todos los resultados son igual de fiables.

Recomendación visual:

- usar `tier` para jerarquía principal;
- usar `evidence_tier` como filtro de robustez;
- usar `quality_tier` como indicador de confianza;
- mostrar warnings cuando existan candidatos con evidencia baja;
- mantener visible que el ranking es experimental.

---

## 10. Limitaciones del dashboard

El dashboard muestra resultados generados por modelos, pero no sustituye a una validación humana.

Limitaciones principales:

- no todos los candidatos tienen evidencia fuerte;
- puede haber platos genéricos en posiciones altas;
- algunas reseñas pueden tener sentimiento ambiguo;
- la cobertura depende de los datos disponibles;
- el ranking v2 no es production-ready;
- los scores v2 no son comparables directamente con v1.

---

## 11. Resultado esperado

Con este dashboard se puede presentar la fase IA v2 de forma clara:

```text
De reseñas y menciones dispersas
→ a señales local-plato normalizadas
→ a ranking territorial de platos destacados
→ con evidencia, calidad y comparación frente al baseline
```

El dashboard queda como una pieza central para la defensa del proyecto, la memoria técnica y futuras iteraciones.
