# 02 - AI Loaders and Checks

## Objetivo

Este documento describe los scripts utilizados para cargar artefactos IA en PostgreSQL y validar cada fase de integración.

La integración se ha realizado de forma incremental para evitar insertar datos huérfanos o resultados IA sin conexión con `place`, `review` y `dish`.

Actualmente hay dos familias de loaders/checks:

1. **Integración Yelp prototype**, usada para validar la arquitectura IA completa.
2. **Integración Sevilla pilot**, usada para cargar el primer ranking piloto local generado desde Google Places Reviews.

---

# 1. Integración Yelp prototype

## 1.1. Orden de carga utilizado

```text
1. load_ai_dish_catalog.py
2. check_ai_dish_catalog.py
3. check_ai_downstream_import_readiness.py
4. load_yelp_ai_core_reviews.py
5. check_ai_downstream_import_readiness.py
6. load_ai_mentions_and_sentiment.py
7. load_ai_signals_and_ranking.py
8. check_ai_ranking_loaded.py
```

Este orden respeta las dependencias:

```text
dish_alias depende de dish
dish_mention depende de review + place + dish
dish_mention_sentiment depende de dish_mention
dish_place_signal depende de place + dish
hidden_gem_candidate depende de dish_place_signal
```

---

## 1.2. `load_ai_dish_catalog.py`

Carga el catálogo de platos y aliases.

Entradas:

```text
dish_catalog_seed_v2.csv
dish_aliases_seed_v2.csv
dish_normalization_summary_v2.json
```

Tablas afectadas:

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
```

Resultado validado:

```text
dish = 9.937
dish_alias = 10.235
ai_model_version = 5
```

---

## 1.3. `check_ai_dish_catalog.py`

Comprueba:

- total de platos;
- total de aliases;
- distribución por idioma;
- distribución por tipo de alias;
- platos sin alias;
- aliases duplicados;
- aliases compartidos por varios platos.

---

## 1.4. `load_yelp_ai_core_reviews.py`

Carga el núcleo Yelp necesario para conectar artefactos IA con el modelo canónico:

```text
Yelp business_id → place_source_ref → place
Yelp review_id → review.source_review_id → review
```

Tablas afectadas:

```text
source_system
source_run
raw_asset
place
place_source_ref
review
```

Resultado validado:

```text
yelp_open_dataset place_source_ref_count = 5.150
yelp_open_dataset review_count = 79.882
```

---

## 1.5. `check_ai_downstream_import_readiness.py`

Valida que se pueden cargar:

```text
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Mapeos requeridos:

```text
artifact review_id → review.source_review_id
artifact business_id → place_source_ref.source_record_id
canonical_dish_name_v2 → dish.normalized_name
```

Resultado validado tras cargar Yelp core:

```text
ready_to_load_dish_mentions = true
ready_to_load_dish_place_signals = true
ready_to_load_hidden_gem_candidates = true
```

---

## 1.6. `load_ai_mentions_and_sentiment.py`

Carga:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
→ dish_mention
→ dish_mention_sentiment
```

Resultado validado:

```text
rows_total = 94.932
mentions_upserted = 94.932
sentiments_upserted = 94.932
invalid_json_lines = 0
skipped_missing_review_mapping = 0
skipped_business_mismatch = 0
skipped_missing_dish_mapping = 0
skipped_invalid_sentiment = 0
```

---

## 1.7. `load_ai_signals_and_ranking.py`

Carga:

```text
dish_business_ranking_candidates_v1.csv
→ dish_place_signal

hidden_gems_selected_candidates_v1.csv
→ hidden_gem_candidate
```

Resultado validado:

```text
signals_upserted = 31.036
hidden_gem_candidates_upserted = 622
skipped_missing_place_mapping = 0
skipped_missing_dish_mapping = 0
skipped_missing_signal_mapping = 0
skipped_invalid_score = 0
skipped_invalid_tier = 0
ready_for_querying_ai_ranking = true
```

El ranking se carga como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 1.8. `check_ai_ranking_loaded.py`

Valida la integración completa.

Resultado final:

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
orphan rows = 0
```

---

# 2. Integración Sevilla pilot

## 2.1. Contexto

Tras validar la arquitectura con Yelp, se ejecutó un flujo local sobre Google Places Reviews de Sevilla:

```text
Google Places Reviews Sevilla
→ export_reviews_for_ai
→ notebooks IA 12-17
→ ranking sevilla_pilot
→ loader PostgreSQL
→ check PostgreSQL
→ query demo
```

---

## 2.2. `export_reviews_for_ai.py`

Exporta reviews operativas desde PostgreSQL para ser procesadas por notebooks IA.

Entrada lógica:

```sql
hidden_gems.review
WHERE source_system = google_places
  AND is_operational_review = true
  AND is_training_eligible = true
```

Salida principal:

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

La exportación incluye información de:

- review;
- place;
- place_source_ref;
- barrio;
- distrito;
- rating;
- idioma;
- texto.

---

## 2.3. `check_ai_review_export.py`

Valida que el JSONL exportado es apto para IA.

Comprueba:

- filas existentes;
- IDs únicos;
- reviews con texto;
- places asociados;
- barrios/distritos presentes;
- idiomas;
- longitudes de texto;
- distribución por barrio/distrito.

---

## 2.4. Notebooks 12-17

Los notebooks generan los artefactos que después se cargan en PostgreSQL:

```text
12_sevilla_reviews_exploration.ipynb
13_sevilla_dish_detection.ipynb
14_sevilla_dish_normalization_and_catalog.ipynb
15_sevilla_mention_sentiment.ipynb
16_sevilla_place_dish_signal_aggregation.ipynb
17_sevilla_hidden_gems_ranking_pilot.ipynb
```

Artefactos principales:

```text
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_catalog_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_aliases_v1.csv
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.jsonl
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_signals_v1.jsonl
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_candidates_all_v1.jsonl
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_selected_candidates_v1.jsonl
```

---

## 2.5. `load_sevilla_ai_pilot_outputs.py`

Carga el piloto IA Sevilla en PostgreSQL.

Tablas afectadas:

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Ejecución recomendada en dry-run:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --report-path data/artifacts/ai/sevilla/load_sevilla_ai_pilot_outputs_report.json
```

Resultado validado:

```text
model_versions_upserted = 5
ai_runs_upserted = 5
dishes_upserted = 190
aliases_upserted = 243
mentions_upserted = 2.979
sentiments_upserted = 2.979
signals_upserted = 2.212
ranking_candidates_upserted = 256
dry_run = false
```

Checks:

```text
no_missing_review_mapping = true
no_missing_place_mapping = true
no_missing_dish_mapping = true
no_invalid_sentiment = true
```

---

## 2.6. `check_sevilla_ai_pilot_loaded.py`

Valida desde PostgreSQL que la carga del piloto Sevilla quedó consistente.

Ejecución:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

Resultado validado:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

Conteos validados:

```text
dish_catalog = 190
dish_alias = 243
dish_mention = 2.979
dish_mention_sentiment = 2.979
dish_place_signal = 2.212
hidden_gem_candidate = 256
hidden_gem_selected = 150
```

Estado del ranking:

```text
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
ranking_version = sevilla_hidden_gems_ranking_pilot_v1
is_production_ready = false
```

---

## 2.7. `query_sevilla_hidden_gems_demo.py`

Permite consultar el ranking Sevilla piloto desde las vistas IA.

Ejemplo global:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

Filtro por distrito:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --district "Casco Antiguo" `
  --limit 20
```

Filtro por barrio:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --neighborhood "TRIANA" `
  --limit 20
```

Filtro por plato:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --dish "tarta de queso" `
  --limit 20
```

Detalle con menciones:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --place-name "Golondrinas" `
  --include-mentions `
  --limit 10
```

Artefactos:

```text
data/artifacts/ai/sevilla/query_demo/
  sevilla_demo_top_global.csv
  sevilla_demo_top_by_district.csv
  sevilla_demo_top_by_neighborhood.csv
  sevilla_demo_top_by_dish.csv
  sevilla_hidden_gems_query_demo_report.json
```

---

# 3. Observaciones de rendimiento

Durante una primera versión del check de readiness, una consulta con varios `LEFT JOIN` generó una operación pesada en PostgreSQL y provocó:

```text
No space left on device
```

La consulta se corrigió para hacer conteos separados y evitar productos intermedios grandes.

Esta lección aplica también a futuros checks: deben priorizar consultas simples, filtradas y trazables.

---

## Conclusión

La cadena de carga y validación queda cerrada tanto para Yelp prototype como para Sevilla pilot:

```text
catálogo IA cargado
menciones cargadas
sentimientos cargados
señales cargadas
ranking cargado
integridad validada
ranking consultable
```

El siguiente trabajo operativo no es volver a cargar los mismos datos, sino consolidar scripts demo finales, crear un dashboard y revisar la calidad del ranking desde uso real.
