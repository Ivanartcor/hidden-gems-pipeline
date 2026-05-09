# 02 - AI Loaders and Checks

## Objetivo

Este documento describe los scripts utilizados para cargar los artefactos IA en PostgreSQL y validar cada fase de integración.

La integración se hizo de forma incremental para evitar insertar datos huérfanos o resultados IA sin conexión con `place`, `review` y `dish`.

---

## Orden de carga utilizado

El orden correcto fue:

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

# 1. `load_ai_dish_catalog.py`

## Responsabilidad

Carga el catálogo de platos y aliases en PostgreSQL.

## Entradas

```text
dish_catalog_seed_v2.csv
dish_aliases_seed_v2.csv
dish_normalization_summary_v2.json
```

## Tablas afectadas

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
```

## Ejecución recomendada

```powershell
python -m scripts.load_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --summary-path data/artifacts/ai/normalization/dish_normalization_summary_v2.json `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --summary-path data/artifacts/ai/normalization/dish_normalization_summary_v2.json
```

## Resultado validado

```text
dish = 9.937
dish_alias = 10.235
ai_model_version = 5
```

---

# 2. `check_ai_dish_catalog.py`

## Responsabilidad

Comprueba que el catálogo IA se ha cargado correctamente.

## Verificaciones

- Total de platos.
- Total de aliases.
- Distribución por idioma.
- Distribución por tipo de alias.
- Platos sin alias.
- Platos sin alias canónico.
- Duplicados potenciales.
- Aliases compartidos por varios platos.

## Ejecución básica

```powershell
python -m scripts.check_ai_dish_catalog
```

Con comparación contra CSV:

```powershell
python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv
```

Con informe JSON:

```powershell
python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --report-path data/artifacts/ai/normalization/check_ai_dish_catalog_report.json
```

---

# 3. `check_ai_downstream_import_readiness.py`

## Responsabilidad

Comprueba si la base está preparada para cargar las fases posteriores:

```text
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

## Primera ejecución

Antes de cargar el núcleo Yelp, el check indicó:

```text
ready_to_load_dish_mentions = false
ready_to_load_dish_place_signals = false
ready_to_load_hidden_gem_candidates = false
```

Esto era correcto, porque los artefactos IA de Yelp todavía no tenían correspondencia con `place` y `review`.

## Ejecución después de cargar Yelp core

```powershell
python -m scripts.check_ai_downstream_import_readiness `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/checks/check_ai_downstream_import_readiness_report_after_yelp_core.json
```

## Resultado validado después de Yelp core

```text
ready_to_load_dish_mentions = true
ready_to_load_dish_place_signals = true
ready_to_load_hidden_gem_candidates = true
```

Mapeos confirmados:

```text
mentions → review.source_review_id = 100%
mentions → business/place mapping = 100%
business_signals → business/place mapping = 100%
ranking → business/place mapping = 100%
dish names → dish = 100%
```

---

# 4. `load_yelp_ai_core_reviews.py`

## Responsabilidad

Carga el núcleo Yelp necesario para poder conectar los artefactos IA con el modelo canónico.

Este script no carga resultados IA. Carga la base canónica necesaria:

```text
Yelp business_id → place_source_ref → place
Yelp review_id → review.source_review_id → review
```

## Entradas

```text
food_businesses.jsonl
food_reviews.jsonl
```

## Tablas afectadas

```text
source_system
source_run
raw_asset
place
place_source_ref
review
```

## Ejecución recomendada

```powershell
python -m scripts.load_yelp_ai_core_reviews `
  --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
  --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_yelp_ai_core_reviews `
  --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
  --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl
```

## Resultado validado

Después de la carga, el sistema contenía:

```text
yelp_open_dataset source_run_count = 1
yelp_open_dataset place_source_ref_count = 5.150
yelp_open_dataset review_count = 79.882
```

Y el total global de la base quedó en:

```text
place = 7.230
review = 80.037
```

## Decisión importante

Esta carga se considera parte del prototipo IA de Yelp. No representa todavía datos productivos de Sevilla.

---

# 5. `load_ai_mentions_and_sentiment.py`

## Responsabilidad

Carga menciones de platos y sentimiento por mención.

## Entrada

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

## Tablas afectadas

```text
dish_mention
dish_mention_sentiment
```

## Mapeos utilizados

```text
artifact review_id → review.source_review_id → review_id interno
artifact business_id → place_source_ref.source_record_id → place_id
canonical_dish_name_v2 → dish.normalized_name → dish_id interno
```

## Ejecución recomendada

```powershell
python -m scripts.load_ai_mentions_and_sentiment `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --dry-run
```

Carga real con informe:

```powershell
python -m scripts.load_ai_mentions_and_sentiment `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --report-path data/artifacts/ai/sentiment/load_ai_mentions_and_sentiment_report.json
```

## Resultado validado

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

# 6. `load_ai_signals_and_ranking.py`

## Responsabilidad

Carga señales agregadas y candidatos finales del ranking.

## Entradas

```text
dish_business_ranking_candidates_v1.csv
hidden_gems_selected_candidates_v1.csv
```

## Tablas afectadas

```text
dish_place_signal
hidden_gem_candidate
```

## Ejecución recomendada

```powershell
python -m scripts.load_ai_signals_and_ranking `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --dry-run
```

Carga real con informe:

```powershell
python -m scripts.load_ai_signals_and_ranking `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/ranking/load_ai_signals_and_ranking_report.json
```

## Resultado validado

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

## Decisión importante

El ranking se carga como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

# 7. `check_ai_ranking_loaded.py`

## Responsabilidad

Valida la integración completa ya cargada en PostgreSQL.

## Ejecución

```powershell
python -m scripts.check_ai_ranking_loaded `
  --report-path data/artifacts/ai/ranking/check_ai_ranking_loaded_report.json
```

## Resultado final validado

Conteos principales:

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
place = 7.230
review = 80.037
```

Resumen de menciones:

```text
dish_mentions = 94.932
reviews_with_mentions = 42.461
places_with_mentions = 4.088
dishes_mentioned = 9.937
avg_ner_confidence = 0.97571
```

Resumen de señales:

```text
total_signals = 31.036
places_with_signals = 4.088
dishes_with_signals = 9.937
rankable_signals = 3.841
```

Resumen de ranking:

```text
total_candidates = 622
selected_candidates = 622
min_score = 60.00283
avg_score = 66.86828
max_score = 82.92816
production_ready_rows = 0
```

Integridad:

```text
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

---

## Observación sobre rendimiento

Durante una primera versión del check de readiness, una consulta con varios `LEFT JOIN` generó una operación pesada en PostgreSQL y provocó un error de disco temporal:

```text
No space left on device
```

La consulta fue corregida para hacer conteos separados y evitar productos intermedios grandes.

La versión corregida debe mantenerse como script actual:

```text
scripts/check_ai_downstream_import_readiness.py
```

---

## Conclusión

La cadena de carga y validación queda cerrada:

```text
catálogo IA cargado
núcleo Yelp cargado
menciones cargadas
sentimientos cargados
señales cargadas
ranking cargado
integridad validada
ranking consultable
```

El sistema está listo para explotación desde vistas SQL y scripts de consulta.
