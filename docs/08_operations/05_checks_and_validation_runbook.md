# 05. Checks and Validation Runbook



## 1. Propósito

Este documento centraliza los checks de Hidden Gems y explica cuándo ejecutar cada uno.

En el proyecto, cada vertical y cada carga importante debe cerrarse con un check. El objetivo es evitar avanzar con datos incompletos, huérfanos, duplicados o inconsistentes.

Este runbook responde a preguntas como:

```text
¿Qué check ejecuto después de cargar geografía?
¿Qué check ejecuto después de un batch de Google Places?
¿Qué check valida reviews?
¿Qué check confirma que la IA está lista?
Qué significa ready_for_sevilla_pilot_queries = true?
```

---

## 2. Principio general

La regla operativa es:

```text
Todo script que carga, transforma o importa datos debe tener un check asociado.
```

El patrón general es:

```text
run/load/import
→ check
→ report JSON
→ revisión de errors/warnings/checks
→ siguiente fase
```

No se debe pasar a la fase siguiente si el check detecta errores críticos.

---

## 3. Cómo interpretar un check

Los checks suelen devolver o guardar bloques como:

```text
checks
errors
warnings
summary
artifact_path
ready_for_...
```

Interpretación recomendada:

| Campo | Interpretación |
|---|---|
| `checks` | Lista de comprobaciones booleanas. Deben estar en `true` salvo excepción documentada. |
| `errors` | Debe estar vacío para considerar válido el proceso. |
| `warnings` | Puede tener avisos no bloqueantes, pero deben revisarse. |
| `ready_for_*` | Flag final de preparación. Debe ser `true` antes de avanzar. |
| `report_path` | Evidencia persistida de la validación. |

Criterio general:

```text
errors = []
checks críticos = true
ready flag = true
```

---

## 4. Checks base de entorno

### 4.1. Conexión a base de datos

```powershell
python -m scripts.check_db_connection
```

Valida:

```text
- conexión PostgreSQL;
- credenciales;
- host/puerto;
- base de datos disponible.
```

Ejecutar:

```text
- al preparar entorno;
- tras cambiar `.env`;
- si un script falla por conexión.
```

---

### 4.2. Schema

```powershell
python -m scripts.check_schema
```

Valida que el schema base existe y que las tablas principales están disponibles.

Ejecutar:

```text
- después de aplicar DDL;
- antes de lanzar verticales;
- cuando se trabaje en una máquina nueva.
```

---

## 5. Checks de Sevilla Geo

### 5.1. Check de carga geográfica

```powershell
python -m scripts.check_sevilla_geo_load
```

Valida:

```text
- distritos cargados;
- barrios cargados;
- geometrías válidas;
- relación barrio-distrito;
- SRID correcto;
- geometrías no vacías.
```

Debe ejecutarse después de:

```powershell
python -m scripts.load_sevilla_geo_reference
```

La geografía debe estar correcta antes de asignar locales a barrios.

---

## 6. Checks de Overpass

### 6.1. Check de staging Overpass

```powershell
python -m scripts.check_overpass_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- estructura de candidatos normalizados;
- accepted / needs_review / rejected;
- coordenadas;
- categorías;
- duplicados básicos;
- issues de transformación.
```

---

### 6.2. Check de importación Overpass

```powershell
python -m scripts.check_overpass_import `
  --source-run-id <SOURCE_RUN_ID> `
  --raw-asset-id <RAW_ASSET_ID>
```

Valida:

```text
- place_source_ref creados;
- places enlazados;
- categorías principales;
- asignación de barrio;
- validation issues;
- consistencia de contadores.
```

---

## 7. Checks de Google Places Text Search

### 7.1. Check raw

```powershell
python -m scripts.check_google_places_raw `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- raw_asset existe;
- fichero físico existe;
- checksum;
- tamaño;
- JSON válido;
- lista `places`;
- campos mínimos;
- pertenencia a source_code = google_places.
```

---

### 7.2. Check staging

```powershell
python -m scripts.check_google_places_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- accepted / needs_review / rejected;
- source_record_id;
- coordenadas;
- categoría;
- estados de negocio;
- duplicados de IDs;
- consistencia del summary.
```

---

### 7.3. Check deduplicación

```powershell
python -m scripts.check_google_places_deduplication `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- unique_candidates.json existe;
- duplicate_groups.json existe;
- output_count coherente;
- no hay source_record_id duplicados;
- coordenadas y categorías presentes.
```

---

### 7.4. Check importación

```powershell
python -m scripts.check_google_places_import `
  --source-run-id <SOURCE_RUN_ID> `
  --raw-asset-id <RAW_ASSET_ID>
```

Valida:

```text
- place_source_ref de Google creados/actualizados;
- refs actuales;
- geometría fuente;
- nombre fuente;
- categoría primaria;
- barrio actual;
- ausencia de incidencias no esperadas.
```

---

### 7.5. Check global de batch

```powershell
python -m scripts.check_google_places_batch `
  --batch-name <BATCH_NAME> `
  --save-artifact
```

Checks críticos:

```text
plan_has_no_duplicate_query_names
planned_query_count_matches_plan
executed_query_count_matches_results
success_count_matches_results
error_count_matches_results
no_errors_or_allowed
summary_totals_match_recomputed_totals
all_success_have_pipeline_output
all_success_have_source_run_id
all_success_have_raw_asset_id
all_success_have_transform_summary
all_success_have_dedup_summary
all_success_have_import_summary_when_required
all_import_checks_pass_when_required
no_duplicate_source_run_ids
no_duplicate_raw_asset_ids
```

Se considera válido si:

```text
error_count = 0
no_errors_or_allowed = true
all_import_checks_pass_when_required = true
```

---

## 8. Checks de Google Places Reviews

### 8.1. Check staging de reviews

```powershell
python -m scripts.check_google_places_reviews_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- Google Place ID;
- reviews aceptadas;
- source_review_id único;
- formato SHA-256;
- texto presente;
- rating;
- language;
- flags operativos;
- vínculo con place_source_ref.
```

---

### 8.2. Check importación de reviews

```powershell
python -m scripts.check_google_places_reviews_import `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Valida:

```text
- reviews importadas;
- coincidencia con import_summary;
- place_id;
- place_source_ref_id;
- source_place_record_id;
- source_review_id;
- source_payload_hash;
- texto;
- rating;
- is_operational_review;
- is_training_eligible;
- no duplicados;
- barrio actual del local.
```

---

### 8.3. Check global de batch de reviews

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name <BATCH_NAME> `
  --save-artifact
```

Checks críticos:

```text
plan_has_no_duplicate_query_names
planned_place_count_matches_plan
executed_place_count_matches_results
success_count_matches_results
error_count_matches_results
no_errors_or_allowed
summary_totals_match_recomputed_totals
staging_parts_match_total
import_count_matches_parts
all_success_have_pipeline_output
all_success_have_source_run_id
all_success_have_raw_asset_id
all_success_have_raw_summary
all_success_have_staging_summary
all_success_have_staging_checks
all_staging_checks_pass
all_success_have_import_summary_when_required
all_success_have_import_checks_when_required
all_import_checks_pass_when_required
no_imports_when_skip_import
no_duplicate_source_run_ids
no_duplicate_raw_asset_ids
no_duplicate_place_source_ref_ids_in_success_scope
no_duplicate_google_place_ids_in_success_scope
no_failed_internal_staging_checks
no_failed_internal_import_checks
```

Si el batch se ejecutó con `--skip-import`, debe cumplirse:

```text
no_imports_when_skip_import = true
```

---

## 9. Checks de Yelp Open Dataset

### 9.1. Check del corpus NLP

```powershell
python -m scripts.check_yelp_nlp_corpus `
  --corpus-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl `
  --save-artifact
```

Valida:

```text
- JSONL válido;
- IDs únicos;
- splits;
- labels;
- texto;
- ratings;
- metadata de negocio;
- task_scope;
- quality_flags.
```

---

## 10. Checks IA generales

### 10.1. Check catálogo IA

```powershell
python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --report-path data/artifacts/ai/normalization/check_ai_dish_catalog_report.json
```

Valida:

```text
- dish total;
- alias total;
- alias canónico;
- duplicados;
- aliases compartidos;
- idioma/tipo de alias.
```

---

### 10.2. Check readiness downstream IA

```powershell
python -m scripts.check_ai_downstream_import_readiness `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/checks/check_ai_downstream_import_readiness_report.json
```

Debe validar:

```text
ready_to_load_dish_mentions
ready_to_load_dish_place_signals
ready_to_load_hidden_gem_candidates
```

No avanzar si alguno está en `false`.

---

### 10.3. Check ranking IA Yelp cargado

```powershell
python -m scripts.check_ai_ranking_loaded `
  --report-path data/artifacts/ai/ranking/check_ai_ranking_loaded_report.json
```

Valida:

```text
- conteos de dish/dish_alias;
- conteos de mentions/sentiments;
- señales;
- ranking;
- distribución por tier;
- huérfanos;
- ready_for_querying_ai_ranking.
```

Debe terminar con:

```text
ready_for_querying_ai_ranking = true
orphan rows = 0
production_ready_rows = 0 para Yelp prototype
```

---

## 11. Checks IA Sevilla

### 11.1. Check del export de reviews

```powershell
python -m scripts.check_ai_review_export `
  --input-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl `
  --summary-path data/artifacts/ai/sevilla/reviews_for_ai_google_places_summary.json `
  --report-path data/artifacts/ai/sevilla/check_ai_review_export_report.json
```

Valida:

```text
- reviews exportadas;
- place_id presente;
- place_source_ref_id presente;
- barrio/distrito presente;
- texto útil;
- rating;
- idioma;
- IDs únicos;
- elegibilidad para IA.
```

---

### 11.2. Check del piloto Sevilla cargado

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

Valida:

```text
- tablas IA requeridas;
- vistas IA disponibles;
- versiones de modelo;
- runs IA;
- conteos esperados;
- integridad review/place/dish;
- sentimientos sin mención;
- señales sin place/dish;
- ranking sin señal;
- scores entre 0 y 100;
- selected con barrio/distrito/place/dish;
- artifact_ranking_scope = sevilla_pilot;
- db_ranking_scope = other;
- is_production_ready = false.
```

Resultado esperado:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

Conteos esperados del piloto actual:

```text
dish = 190
dish_alias = 243
dish_mention = 2.979
dish_mention_sentiment = 2.979
dish_place_signal = 2.212
hidden_gem_candidate = 256
hidden_gem_selected = 150
```

---

## 12. Checks de consulta/demo

### 12.1. Demo Yelp

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

Validar que:

```text
- devuelve candidatos;
- scores visibles;
- tiers visibles;
- no falla la vista;
- si se usa include-mentions, devuelve menciones asociadas.
```

---

### 12.2. Demo Sevilla

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

Validar que:

```text
- devuelve candidatos seleccionados;
- devuelve resumen por distrito;
- devuelve top por distrito/barrio/plato;
- genera artifacts en query_demo;
- final checks = true.
```

Con filtros:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --district "Casco Antiguo" `
  --limit 20
```

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --dish "tarta de queso" `
  --limit 20
```

---

## 13. Reports JSON recomendados

Siempre que el script lo permita, usar `--report-path` o `--save-artifact`.

Rutas recomendadas:

```text
data/artifacts/ai/checks/
data/artifacts/ai/sevilla/
data/artifacts/google_places_batches/<batch_name>/
data/artifacts/google_places_reviews_batches/<batch_name>/
data/artifacts/yelp_open_dataset_qa/
```

Los reports JSON son importantes porque:

```text
- dejan evidencia reproducible;
- permiten comparar ejecuciones;
- ayudan a depurar;
- documentan conteos y errores;
- sirven para justificar resultados en documentación.
```

---

## 14. Qué hacer si un check falla

### 14.1. Si falla por missing mapping

Ejemplos:

```text
missing_review_mapping
missing_place_mapping
missing_dish_mapping
ranking_missing_signal_mapping
```

Acciones:

```text
1. No continuar la carga.
2. Revisar el artefacto de entrada.
3. Revisar si la entidad existe en PostgreSQL.
4. Revisar source_record_id/source_review_id.
5. Ejecutar readiness/check específico.
```

---

### 14.2. Si falla por duplicados

Acciones:

```text
1. Revisar IDs duplicados en artifact.
2. Revisar constraints de base.
3. Confirmar si es reejecución idempotente o error real.
4. Revisar import_summary.
```

---

### 14.3. Si falla por score fuera de rango

Acciones:

```text
1. Revisar fórmula de ranking.
2. Revisar normalización a 0-100.
3. Revisar NaN/Infinity.
4. Regenerar artifact con JSON estricto.
```

---

### 14.4. Si falla por falta de barrio

Acciones:

```text
1. Revisar place_neighborhood_assignment.
2. Comprobar coordenadas del place.
3. Comprobar geometría de barrios.
4. Ejecutar check geográfico.
```

---

### 14.5. Si el check es muy lento

Acciones:

```text
1. Evitar joins masivos innecesarios.
2. Usar conteos separados.
3. Añadir límites si el script lo permite.
4. Revisar índices.
5. Comprobar espacio libre en disco de PostgreSQL.
```

---

## 15. Checklist final por fase

### Ingesta Google Places

```text
[ ] batch_summary.json existe.
[ ] batch_check.json existe.
[ ] error_count = 0 o justificado.
[ ] import checks en true.
[ ] no duplicados de raw/source_run.
[ ] artifacts guardados.
```

### Reviews Google

```text
[ ] reviews_batch_check.json existe.
[ ] staging checks en true.
[ ] import checks en true.
[ ] reviews enlazadas a place/place_source_ref.
[ ] reviews tienen texto/rating/source_review_id.
[ ] no hay duplicados.
```

### IA Yelp

```text
[ ] catálogo validado.
[ ] readiness downstream true.
[ ] menciones cargadas.
[ ] sentimiento cargado.
[ ] señales cargadas.
[ ] ranking cargado.
[ ] ready_for_querying_ai_ranking = true.
```

### IA Sevilla

```text
[ ] export reviews validado.
[ ] notebooks ejecutados.
[ ] loader Sevilla ejecutado.
[ ] check Sevilla cargado.
[ ] ready_for_sevilla_pilot_queries = true.
[ ] query demo funciona.
[ ] selected candidates > 0.
```

---

## 16. Conclusión

Los checks son una parte central del proyecto Hidden Gems. No son pasos secundarios: son el mecanismo que permite confiar en que el pipeline es reproducible, trazable y consistente.

La regla final es:

```text
Si no hay check correcto, la fase no está cerrada.
```

Todo avance hacia dashboard, API o modelos más avanzados debe apoyarse en estos reports de validación.

---

## 17. Checks y validaciones de Sevilla IA v2

La fase Sevilla IA v2 se valida principalmente mediante summaries de artefactos, no mediante una carga nueva completa en PostgreSQL.

### 17.1. Validación de `hybrid_ner_v2`

```text
hybrid_mentions > 0
ner_mentions > 0
matches > 0
candidate_rows_final > 0
JSONL serializable sin errores
sin duplicados críticos por review_id + mention_norm
```

### 17.2. Validación de normalización reranker

```text
input_rows = normalized_rows
linked + linked_needs_review + low_confidence + no_candidate = input_rows
ready_for_sentiment > 0
```

### 17.3. Validación de ABSA

```text
predicted_rows > 0
sentiment_label ∈ {negative, neutral, positive}
confidence entre 0 y 1
ready_for_downstream_sentiment > 0
sin NaN/Infinity en JSONL
```

### 17.4. Validación de ranking v2

Revisar:

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2_summary.json
```

Checks esperados:

```text
has_ranking = true
has_selected_candidates = true
selected_hidden_gem_candidates = 268
score_in_0_100 = true
selected_have_place = true
selected_have_dish = true
selected_have_neighborhood = true
selected_have_district = true
selected_ranks_are_unique = true
all_selected_are_not_production_ready = true
```

### 17.5. Validación de comparación v1/v2

Revisar:

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison/sevilla_ranking_v1_vs_v2_summary.json
```

Checks esperados:

```text
v1_selected_unique = 150
v2_selected_unique = 268
matched_candidates = 119
v1_coverage_in_v2 ≈ 0.793333
checks principales = true
```

### 17.6. Validación de dashboard_v2

Revisar:

```text
data/artifacts/ai/sevilla/dashboard_v2/dashboard_export_summary.json
```

Checks esperados:

```text
has_ranking = true
has_selected_candidates = true
expected_selected_matches = true
score_in_0_100 = true
selected_have_place = true
selected_have_dish = true
selected_have_neighborhood = true
selected_have_district = true
comparison_loaded = true
all_selected_are_not_production_ready = true
```

Regla final:

```text
ranking_v2_summary OK
comparison_summary OK
dashboard_export_summary OK
streamlit_sevilla_v2_app.py ejecuta sin error
README y docs actualizados
```
