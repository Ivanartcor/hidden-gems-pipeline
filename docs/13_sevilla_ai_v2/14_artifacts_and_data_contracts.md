# 14. Artefactos y contratos de datos de la fase IA v2

## 1. Objetivo del documento

Este documento recopila los principales artefactos generados durante la fase IA v2 de Hidden Gems Sevilla.

El objetivo es dejar claro:

- qué carpetas se generan;
- qué scripts producen cada artefacto;
- qué archivos son entrada y salida;
- qué granularidad tiene cada dataset;
- qué archivos alimentan el dashboard;
- qué modelos deben mantenerse en local;
- qué elementos no deben subirse al repositorio.

---

## 2. Principio general de organización

La fase IA v2 sigue una estructura por capas.

Cada capa:

1. recibe un artefacto de entrada;
2. aplica reglas, modelos o agregaciones;
3. genera una salida persistida;
4. produce un summary JSON;
5. deja trazabilidad suficiente para análisis posterior.

Flujo general:

```text
NER model output
→ hybrid_ner_v2
→ normalization_reranker_v1
→ sentiment_absa_v1
→ place_dish_signals_v2
→ ranking_v2
→ ranking_v2_comparison
→ dashboard_v2
```

---

## 3. Modelos locales

Los modelos entrenados en Kaggle no se suben al repositorio.

Deben guardarse localmente en:

```text
models/
├── sevilla_dish_ner_beto_v1_2/
├── sevilla_dish_normalization_reranker_beto_v1/
└── sevilla_mention_sentiment_absa_beto_v1/
```

La carpeta debe estar ignorada en Git:

```gitignore
models/
```

Motivos:

- los pesos son pesados;
- no forman parte del código fuente;
- pueden distribuirse por Drive, Hugging Face privado u otro mecanismo;
- el repositorio debe seguir siendo ligero.

---

## 4. Artefactos de NER

### Carpeta recomendada

```text
data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/
```

### Contenido esperado

| Archivo | Descripción |
|---|---|
| `sevilla_dish_mentions_ner_model_v1_2.jsonl` | Menciones detectadas por el modelo NER. |
| `sevilla_dish_mentions_ner_model_v1_2.csv` | Versión tabular. |
| `summary.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = una mención de plato detectada en una reseña.
```

### Uso posterior

Estas menciones se combinan con las menciones híbridas previas para construir la capa `hybrid_ner_v2`.

---

## 5. Artefactos Hybrid + NER v2

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
```

### Script productor

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
```

### Archivos principales

| Archivo | Descripción |
|---|---|
| `sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl` | Capa unificada de menciones candidatas. |
| `sevilla_dish_mentions_hybrid_ner_candidates_v2.csv` | Versión CSV. |
| `sevilla_hybrid_ner_normalization_queue_v2.csv` | Cola priorizada para normalización/revisión. |
| `sevilla_hybrid_ner_summary_v2.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = una mención candidata única por review_id + mención normalizada.
```

### Campos importantes

| Campo | Descripción |
|---|---|
| `review_id` | Identificador de reseña. |
| `place_id` | Local asociado. |
| `selected_mention_text_v2` | Texto de la mención elegida. |
| `selected_mention_norm_v2` | Normalización textual de la mención. |
| `mention_strategy_v2` | `hybrid_and_ner`, `hybrid_only` o `ner_only`. |
| `needs_manual_review_v2` | Indica si requiere revisión. |
| `ready_for_sentiment_v2` | Indica si puede avanzar a sentimiento. |

---

## 6. Artefactos de normalización / entity linking

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
```

o, en ejecución completa:

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1_full/
```

### Script productor

```text
scripts/run_sevilla_dish_normalization_reranker_v1.py
```

### Archivos principales

| Archivo | Descripción |
|---|---|
| `sevilla_dish_mentions_normalized_reranker_v1.jsonl` | Menciones con plato normalizado. |
| `sevilla_dish_mentions_normalized_reranker_v1.csv` | Versión CSV. |
| `sevilla_dish_normalization_low_confidence_v1.csv` | Casos de baja confianza. |
| `sevilla_dish_normalization_no_candidate_v1.csv` | Casos sin candidato de catálogo. |
| `sevilla_dish_normalization_summary_v1.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = una mención candidata con posible dish_id enlazado.
```

### Campos importantes

| Campo | Descripción |
|---|---|
| `dish_id_v2` | Identificador del plato enlazado. |
| `dish_display_name_v2` | Nombre visible del plato. |
| `normalization_status_v1` | Estado de normalización. |
| `normalization_confidence_v1` | Confianza del reranker. |
| `normalization_margin_v1` | Diferencia entre primer y segundo candidato. |
| `normalization_needs_review_v1` | Marca de revisión. |

---

## 7. Artefactos de sentimiento ABSA

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
```

### Script productor

```text
scripts/run_sevilla_mention_sentiment_absa_v1.py
```

### Archivos principales

| Archivo | Descripción |
|---|---|
| `sevilla_dish_mentions_with_absa_sentiment_v1.jsonl` | Menciones normalizadas con sentimiento. |
| `sevilla_dish_mentions_with_absa_sentiment_v1.csv` | Versión CSV. |
| `sevilla_absa_sentiment_low_confidence_v1.csv` | Predicciones de baja confianza. |
| `sevilla_absa_sentiment_not_ready_v1.csv` | Filas no preparadas para sentimiento. |
| `sevilla_absa_sentiment_summary_v1.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = una mención normalizada con sentimiento ABSA.
```

### Campos importantes

| Campo | Descripción |
|---|---|
| `absa_sentiment_label_v1` | `positive`, `neutral` o `negative`. |
| `absa_confidence_v1` | Confianza de la predicción. |
| `absa_positive_prob_v1` | Probabilidad positiva. |
| `absa_neutral_prob_v1` | Probabilidad neutral. |
| `absa_negative_prob_v1` | Probabilidad negativa. |
| `absa_sentiment_score_v1` | Señal continua de sentimiento. |
| `ready_for_downstream_sentiment_v1` | Si puede agregarse. |

---

## 8. Artefactos place-dish signals v2

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/
```

### Script productor

```text
scripts/build_sevilla_place_dish_signals_v2.py
```

### Archivos principales

| Archivo | Descripción |
|---|---|
| `sevilla_place_dish_signals_v2.jsonl` | Señales agregadas por local-plato. |
| `sevilla_place_dish_signals_v2.csv` | Versión CSV. |
| `sevilla_top_place_dish_signals_v2.csv` | Señales principales ordenadas. |
| `sevilla_place_dish_signals_by_district_v2.csv` | Agregación por distrito. |
| `sevilla_place_dish_signals_by_neighborhood_v2.csv` | Agregación por barrio. |
| `sevilla_place_dish_signals_by_dish_v2.csv` | Agregación por plato. |
| `sevilla_place_dish_signals_manual_review_v2.csv` | Señales revisables. |
| `sevilla_place_dish_signal_tier_summary_v2.csv` | Resumen por tier de señal. |
| `sevilla_place_dish_signal_summary_v2.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = una señal agregada place_id + dish_id.
```

### Campos importantes

| Campo | Descripción |
|---|---|
| `place_id` | Local. |
| `dish_id_v2` | Plato normalizado. |
| `mention_count_v2` | Número de menciones. |
| `review_count_v2` | Número de reviews. |
| `positive_ratio_v2` | Ratio positivo. |
| `negative_ratio_v2` | Ratio negativo. |
| `weighted_sentiment_score_v2` | Sentimiento ponderado. |
| `avg_absa_confidence_v2` | Confianza media ABSA. |
| `avg_normalization_confidence_v2` | Confianza media de normalización. |
| `evidence_tier_v2` | Fuerza de evidencia. |
| `aggregate_quality_tier_v2` | Calidad agregada. |
| `ready_for_ranking_v2` | Elegibilidad para ranking. |

---

## 9. Artefactos ranking v2

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2/
```

### Script productor

```text
scripts/build_sevilla_hidden_gems_ranking_v2.py
```

### Archivos principales

| Archivo | Descripción |
|---|---|
| `sevilla_hidden_gems_ranking_v2.jsonl` | Ranking completo. |
| `sevilla_hidden_gems_ranking_v2.csv` | Ranking completo en CSV. |
| `sevilla_hidden_gems_selected_v2.jsonl` | Candidatos seleccionados. |
| `sevilla_hidden_gems_selected_v2.csv` | Seleccionados en CSV. |
| `sevilla_hidden_gems_top_global_v2.csv` | Top global. |
| `sevilla_hidden_gems_top_by_district_v2.csv` | Top por distrito. |
| `sevilla_hidden_gems_top_by_neighborhood_v2.csv` | Top por barrio. |
| `sevilla_hidden_gems_top_by_dish_v2.csv` | Top por plato. |
| `sevilla_hidden_gems_manual_review_v2.csv` | Candidatos revisables. |
| `sevilla_hidden_gems_tier_summary_v2.csv` | Resumen por tier. |
| `sevilla_hidden_gems_district_summary_v2.csv` | Resumen por distrito. |
| `sevilla_hidden_gems_neighborhood_summary_v2.csv` | Resumen por barrio. |
| `sevilla_hidden_gems_dish_summary_v2.csv` | Resumen por plato. |
| `sevilla_hidden_gems_ranking_v2_summary.json` | Resumen de ejecución. |

### Granularidad

```text
Una fila = un candidato Hidden Gem place-dish.
```

---

## 10. Artefactos comparación v1 vs v2

### Carpeta

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison/
```

### Script productor

```text
scripts/compare_sevilla_ranking_v1_vs_v2.py
```

### Archivos

| Archivo | Descripción |
|---|---|
| `sevilla_ranking_v1_vs_v2_summary.json` | Resumen comparativo. |
| `ranking_overlap.csv` | Candidatos presentes en v1 y v2. |
| `v2_only_candidates.csv` | Candidatos solo v2. |
| `v1_only_candidates.csv` | Candidatos solo v1. |
| `score_shift_comparison.csv` | Cambios de score y ranking. |
| `top_district_shift.csv` | Cambios por distrito. |
| `top_neighborhood_shift.csv` | Cambios por barrio. |
| `top_dish_shift.csv` | Cambios por plato. |
| `tier_shift_summary.csv` | Cambios de tier. |

---

## 11. Artefactos dashboard v2

### Carpeta

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

### Script productor

```text
scripts/export_sevilla_dashboard_data_v2.py
```

### Archivos principales

| Archivo | Granularidad | Descripción |
|---|---|---|
| `ranking_detail.csv` | Una fila por candidato puntuado | Ranking completo preparado para dashboard. |
| `selected_candidates.csv` | Una fila por seleccionado | Selección final v2. |
| `mention_examples.csv` | Cero a muchas filas por candidato | Evidencia textual y reseñas. |
| `top_global.csv` | Una fila por seleccionado top | Ranking global. |
| `top_by_district.csv` | Top por distrito | Vista territorial. |
| `top_by_neighborhood.csv` | Top por barrio | Vista territorial granular. |
| `top_by_dish.csv` | Top por plato | Vista gastronómica. |
| `district_summary.csv` | Una fila por distrito | Resumen territorial. |
| `neighborhood_summary.csv` | Una fila por barrio | Resumen territorial. |
| `dish_summary.csv` | Una fila por plato | Resumen gastronómico. |
| `place_summary.csv` | Una fila por local | Resumen por local. |
| `tier_summary.csv` | Una fila por tier | Distribución de tiers. |
| `evidence_summary.csv` | Una fila por evidence tier | Distribución de evidencia. |
| `quality_summary.csv` | Una fila por quality tier | Distribución de calidad. |
| `place_coordinates.csv` | Una fila por local | Coordenadas cuando están disponibles. |
| `filter_options.json` | Valores de filtros | Opciones para Streamlit. |
| `data_contract.json` | Contrato | Campos y granularidad. |
| `dashboard_export_summary.json` | Resumen | Checks, warnings y KPIs. |
| `comparison/` | Varios | Copia de artefactos v1 vs v2. |

---

## 12. Contrato de datos del dashboard

El contrato define tres granularidades principales.

### `ranking_detail.csv`

```text
Una fila = un candidato/señal place-dish puntuado.
```

Columnas estándar principales:

| Columna | Descripción |
|---|---|
| `dashboard_candidate_key` | Clave estable para dashboard. |
| `place_id_std` | Identificador del local. |
| `place_name_std` | Nombre del local. |
| `dish_id_std` | Identificador del plato. |
| `dish_name_std` | Nombre del plato. |
| `district_name_std` | Distrito. |
| `neighborhood_name_std` | Barrio. |
| `score_std` | Score v2 0-100. |
| `tier_std` | Tier Hidden Gem. |
| `mention_count_std` | Menciones. |
| `review_count_std` | Reviews. |
| `positive_ratio_std` | Ratio positivo. |
| `negative_ratio_std` | Ratio negativo. |
| `evidence_tier_std` | Nivel de evidencia. |
| `quality_tier_std` | Nivel de calidad. |
| `explanation_std` | Explicación textual. |
| `latitude_std` | Latitud del local, si existe. |
| `longitude_std` | Longitud del local, si existe. |

### `selected_candidates.csv`

```text
Una fila = un candidato seleccionado como Hidden Gem v2.
```

Se utiliza como tabla principal del dashboard.

### `mention_examples.csv`

```text
Una fila = una mención/reseña asociada a un candidato seleccionado.
```

Permite mostrar evidencia textual, contexto y texto completo de reseña cuando está disponible.

---

## 13. Reglas de versionado

Los artefactos de esta fase deben mantener sufijos explícitos:

```text
_v2
_v1_2
_reranker_v1
_absa_v1
```

Esto evita confundir:

- ranking piloto v1;
- NER v1.2;
- normalización reranker v1;
- ABSA v1;
- ranking IA v2.

---

## 14. Reproducibilidad

Para reproducir la fase completa, el orden recomendado es:

```text
1. Ejecutar NER v1.2 sobre reviews.
2. Limpiar salida NER.
3. Construir hybrid_ner_v2.
4. Ejecutar normalization reranker.
5. Ejecutar ABSA sentiment.
6. Construir place_dish_signals_v2.
7. Construir ranking_v2.
8. Comparar v1 vs v2.
9. Exportar dashboard_v2.
10. Ejecutar Streamlit.
```

---

## 15. Consideraciones de almacenamiento

No deberían subirse al repositorio:

```text
models/
data/raw/
data/artifacts/ai/sevilla/model_inference/
data/artifacts/ai/sevilla/dashboard_v2/
```

salvo que se decida versionar una muestra reducida.

El código, documentación y contratos sí deben subirse.

---

## 16. Conclusión

La fase IA v2 queda documentada como una cadena trazable de artefactos.

Cada resultado importante tiene:

- script productor;
- carpeta de salida;
- summary JSON;
- CSV/JSONL de análisis;
- granularidad clara;
- relación explícita con la siguiente capa.

Esto permite defender técnicamente el pipeline y facilita futuras mejoras.
