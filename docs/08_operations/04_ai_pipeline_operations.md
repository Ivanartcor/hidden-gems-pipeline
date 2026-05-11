# 04. AI Pipeline Operations

## 1. Propósito

Este documento describe cómo operar la parte IA de Hidden Gems desde el punto de vista práctico.

Cubre dos líneas de trabajo:

1. **Prototipo IA Yelp**, usado para validar la arquitectura completa sobre un corpus externo amplio.
2. **Piloto IA Sevilla**, usado para aplicar el flujo a reviews reales de Google Places en Sevilla.

La idea principal es que la IA no modifica directamente las entidades canónicas como `place` o `review`. La IA genera una capa derivada:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

Todo queda versionado mediante:

```text
ai_model_version
ai_pipeline_run
```

---

## 2. Principios operativos de la IA

Reglas principales:

```text
1. No cargar resultados IA sin mapeo a review, place y dish.
2. Ejecutar dry-run cuando el loader lo permita.
3. Validar readiness antes de cargas downstream.
4. Ejecutar checks después de cada carga.
5. Guardar reports JSON de cada operación.
6. Diferenciar siempre Yelp prototype y Sevilla pilot.
7. No marcar candidatos como production_ready sin validación específica.
8. No versionar artefactos pesados con reviews completas.
```

---

## 3. Diferencia entre Yelp prototype y Sevilla pilot

| Aspecto | Yelp prototype | Sevilla pilot |
|---|---|---|
| Fuente principal | Yelp Open Dataset | Google Places Reviews |
| Idioma dominante | Inglés | Español/multilingüe |
| Uso | Prototipo IA externo | Piloto local real |
| Geografía Sevilla | No productiva | Sí |
| Ranking scope de artefacto | `yelp_prototype` | `sevilla_pilot` |
| Ranking scope en DB | `yelp_prototype` | `other` por restricción DDL actual |
| Production ready | `false` | `false` |
| Consulta demo | `query_ai_ranking_demo.py` | `query_sevilla_hidden_gems_demo.py` |

---

## 4. Operación IA sobre Yelp prototype

### 4.1. Orden general

El flujo de integración IA de Yelp se ejecuta en este orden:

```text
1. Cargar catálogo de platos y aliases.
2. Validar catálogo.
3. Cargar núcleo Yelp para mapear businesses/reviews.
4. Validar readiness downstream.
5. Cargar menciones y sentimiento.
6. Cargar señales y ranking.
7. Validar ranking cargado.
8. Consultar demo.
```

---

### 4.2. Cargar catálogo de platos

Script:

```text
scripts/load_ai_dish_catalog.py
```

Dry-run:

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

---

### 4.3. Validar catálogo de platos

```powershell
python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --report-path data/artifacts/ai/normalization/check_ai_dish_catalog_report.json
```

Comprobar:

```text
- total de dishes esperado
- total de aliases esperado
- platos sin alias
- aliases duplicados
- aliases compartidos
```

---

### 4.4. Cargar núcleo Yelp para IA

Script:

```text
scripts/load_yelp_ai_core_reviews.py
```

Dry-run:

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

Esta carga crea el puente:

```text
Yelp business_id → place_source_ref → place
Yelp review_id   → review.source_review_id → review
```

---

### 4.5. Check de readiness downstream

```powershell
python -m scripts.check_ai_downstream_import_readiness `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/checks/check_ai_downstream_import_readiness_report.json
```

Debe confirmar:

```text
ready_to_load_dish_mentions = true
ready_to_load_dish_place_signals = true
ready_to_load_hidden_gem_candidates = true
```

Si no está en true, no cargar menciones ni ranking.

---

### 4.6. Cargar menciones y sentimiento

Script:

```text
scripts/load_ai_mentions_and_sentiment.py
```

Dry-run:

```powershell
python -m scripts.load_ai_mentions_and_sentiment `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_ai_mentions_and_sentiment `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --report-path data/artifacts/ai/sentiment/load_ai_mentions_and_sentiment_report.json
```

Validar que no haya:

```text
skipped_missing_review_mapping
skipped_missing_place_mapping
skipped_missing_dish_mapping
skipped_invalid_sentiment
```

---

### 4.7. Cargar señales y ranking Yelp

Script:

```text
scripts/load_ai_signals_and_ranking.py
```

Dry-run:

```powershell
python -m scripts.load_ai_signals_and_ranking `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_ai_signals_and_ranking `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/ranking/load_ai_signals_and_ranking_report.json
```

El ranking debe quedar como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

### 4.8. Check final del ranking Yelp

```powershell
python -m scripts.check_ai_ranking_loaded `
  --report-path data/artifacts/ai/ranking/check_ai_ranking_loaded_report.json
```

Debe confirmar:

```text
ready_for_querying_ai_ranking = true
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

---

### 4.9. Consulta demo Yelp

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

Con menciones:

```powershell
python -m scripts.query_ai_ranking_demo `
  --place-name "Sushi Ushi" `
  --dish-name "sushi" `
  --include-mentions `
  --mentions-top-n 25
```

---

## 5. Operación IA sobre Sevilla pilot

El piloto Sevilla se apoya en reviews reales de Google Places ya cargadas en `hidden_gems.review`.

Flujo general:

```text
Google Places Reviews en PostgreSQL
→ export_reviews_for_ai.py
→ notebooks 12-17
→ artefactos IA Sevilla
→ load_sevilla_ai_pilot_outputs.py
→ check_sevilla_ai_pilot_loaded.py
→ query_sevilla_hidden_gems_demo.py
```

---

## 6. Export de reviews para IA Sevilla

Script:

```text
scripts/export_reviews_for_ai.py
```

Objetivo:

```text
hidden_gems.review
→ reviews_for_ai_google_places.jsonl
```

El export debe contener reviews operativas enlazadas a:

```text
place
place_source_ref
neighborhood
district
```

Ejemplo de ejecución:

```powershell
python -m scripts.export_reviews_for_ai `
  --source-code google_places `
  --output-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl `
  --summary-path data/artifacts/ai/sevilla/reviews_for_ai_google_places_summary.json
```

Validación del export:

```powershell
python -m scripts.check_ai_review_export `
  --input-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl `
  --summary-path data/artifacts/ai/sevilla/reviews_for_ai_google_places_summary.json `
  --report-path data/artifacts/ai/sevilla/check_ai_review_export_report.json
```

---

## 7. Notebooks IA Sevilla

Los notebooks del piloto Sevilla se ejecutan sobre los artifacts exportados.

Secuencia lógica:

```text
12. Exploración de reviews Sevilla
13. Detección de candidatos de platos
14. Normalización y catálogo local Sevilla
15. Sentimiento por mención
16. Agregación place + dish
17. Ranking Hidden Gems Sevilla pilot
```

La salida principal del flujo Sevilla es:

```text
data/artifacts/ai/sevilla/
├── dish_detection/
├── dish_normalization/
├── sentiment/
├── aggregation/
└── ranking/
```

Artefactos clave:

```text
sevilla_dish_catalog_v1.csv
sevilla_dish_aliases_v1.csv
sevilla_dish_mentions_with_sentiment_v1.jsonl
sevilla_place_dish_signals_v1.jsonl
sevilla_place_dish_ranking_candidates_v1.jsonl
sevilla_hidden_gems_selected_candidates_v1.jsonl
sevilla_hidden_gems_ranking_summary_v1.json
```

---

## 8. Carga del piloto Sevilla en PostgreSQL

Script:

```text
scripts/load_sevilla_ai_pilot_outputs.py
```

Dry-run:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --dry-run
```

Carga real:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --report-path data/artifacts/ai/sevilla/load_sevilla_ai_pilot_outputs_report.json
```

El loader carga:

```text
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
ai_model_version
ai_pipeline_run
```

Resultado validado del piloto Sevilla:

```text
dishes_upserted = 190
aliases_upserted = 243
mentions_upserted = 2.979
sentiments_upserted = 2.979
signals_upserted = 2.212
ranking_candidates_upserted = 256
```

Notas importantes:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
```

El uso de `db_ranking_scope = other` se debe a la restricción actual del DDL.

---

## 9. Check del piloto Sevilla cargado

Script:

```text
scripts/check_sevilla_ai_pilot_loaded.py
```

Ejecución:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

Debe devolver:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

Conteos esperados:

```text
dish_catalog = 190
dish_alias = 243
dish_mention = 2.979
dish_mention_sentiment = 2.979
dish_place_signal = 2.212
hidden_gem_candidate = 256
hidden_gem_selected = 150
```

---

## 10. Consulta demo Sevilla

Script:

```text
scripts/query_sevilla_hidden_gems_demo.py
```

Consulta global:

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

---

## 11. Artefactos de consulta Sevilla

El script de demo genera outputs en:

```text
data/artifacts/ai/sevilla/query_demo/
```

Artefactos principales:

```text
sevilla_demo_top_global.csv
sevilla_demo_top_by_district.csv
sevilla_demo_top_by_neighborhood.csv
sevilla_demo_top_by_dish.csv
sevilla_demo_district_summary.csv
sevilla_demo_neighborhood_summary.csv
sevilla_demo_dish_summary.csv
sevilla_demo_place_summary.csv
sevilla_hidden_gems_query_demo_report.json
```

Estos artifacts son candidatos naturales para alimentar el dashboard piloto.

---

## 12. Interpretación del piloto Sevilla

El piloto Sevilla debe interpretarse como:

```text
- ranking local real sobre Google Reviews;
- trazado y consultable en PostgreSQL;
- útil para demo técnica;
- no marcado como producción final;
- sujeto a revisión manual y mejora de IA.
```

Resultados de referencia:

```text
selected_hidden_gem_candidates = 150
selected_places = 122
selected_dishes = 38
selected_neighborhoods = 55
selected_districts = 11
```

Tiers:

```text
top_hidden_gem = 2
strong_hidden_gem = 7
promising_hidden_gem = 72
exploratory_hidden_gem = 69
not_selected = 106
```

---

## 13. Cuándo repetir el flujo Sevilla

Repetir parcial o totalmente el flujo cuando:

```text
- se importen más reviews de Google Places;
- se actualice el diccionario de platos;
- se cambien reglas de detección;
- se cambie el sentimiento por mención;
- se cambien pesos del ranking;
- se quiera generar una nueva versión del piloto.
```

Si solo cambian los datos de reviews, se recomienda:

```text
1. export_reviews_for_ai.py
2. notebooks 12-17
3. load_sevilla_ai_pilot_outputs.py
4. check_sevilla_ai_pilot_loaded.py
5. query_sevilla_hidden_gems_demo.py
```

Si cambia el DDL o la restricción de `ranking_scope`, habría que revisar también el loader.

---

## 14. Errores frecuentes en IA

| Problema | Causa habitual | Solución |
|---|---|---|
| Falta mapping de review | Reviews no cargadas o ID distinto | Ejecutar readiness/check export |
| Falta mapping de place | `place_source_ref` incompleto | Revisar carga Google/Yelp core |
| Falta mapping de dish | Catálogo/aliases incompletos | Revisar `dish` y `dish_alias` |
| JSON summary no sube o falla | NaN/Infinity | Guardar JSON estricto con `allow_nan=False` |
| KeyError en notebook | Columna no generada o nombre distinto | Revisar columnas antes de seleccionar |
| Ranking sin seleccionados | Thresholds demasiado estrictos | Revisar `ranking_ready_v1` y score |
| Checks lentos | Joins grandes | Usar checks optimizados/separados |

---

## 15. Cierre operativo de una ejecución IA

Una ejecución IA se considera cerrada cuando:

```text
[ ] Los artefactos de entrada existen.
[ ] Los notebooks/scripts se ejecutan sin error.
[ ] Los summaries JSON existen y son válidos.
[ ] El loader se ejecuta en dry-run si aplica.
[ ] La carga real genera report JSON.
[ ] Los skip/error counters están en 0 o justificados.
[ ] El check final devuelve ready = true.
[ ] La demo de consulta devuelve resultados.
[ ] Los artifacts pesados no se suben a Git.
[ ] La documentación se actualiza si cambia el flujo.
```
