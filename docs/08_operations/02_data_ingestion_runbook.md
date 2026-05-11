# 02. Data Ingestion Runbook

## 1. Propósito

Este runbook describe cómo ejecutar las verticales de adquisición e importación de datos de **Hidden Gems Pipeline**.

El objetivo es documentar el flujo operativo de ingesta, no repetir todo el diseño interno de cada vertical.

Aquí se resume:

- qué verticales existen;
- qué scripts principales se usan;
- en qué orden se ejecutan;
- qué checks hay que lanzar;
- qué artefactos se generan;
- qué precauciones aplicar antes de escalar.

---

## 2. Patrón general de una vertical

La mayoría de verticales siguen este patrón:

```text
1. Ingesta raw
2. Check raw
3. Transformación a staging
4. Check staging
5. Deduplicación si aplica
6. Check deduplicación si aplica
7. Importación canónica
8. Check post-importación
9. Report/artifact final
```

No todas las fuentes tienen exactamente todos los pasos. Por ejemplo:

- Sevilla Geo carga datos de referencia territorial.
- Google Places necesita deduplicación de locales.
- Google Places Reviews no deduplica locales, pero sí deduplica reviews mediante IDs/hash.
- Yelp usa lectura streaming y construcción de corpus.
- IA se trata en otro runbook porque ya no es adquisición fuente, sino procesamiento derivado.

---

## 3. Orden recomendado de ingesta desde una base limpia

Si se parte de una base vacía o recién creada, el orden recomendado es:

```text
1. Preparar entorno y DB.
2. Ejecutar seed_source_systems.
3. Cargar Sevilla Geo.
4. Ejecutar Overpass para POIs iniciales.
5. Ejecutar Google Places Text Search por tandas.
6. Ejecutar Google Places Reviews sobre locales ya consolidados.
7. Construir/exportar corpus IA si aplica.
8. Ejecutar loaders IA o notebooks posteriores.
```

Secuencia resumida:

```text
source_systems
→ sevilla_geo
→ osm_overpass
→ google_places
→ google_places_reviews
→ ai/export/reviews/notebooks/loaders
```

---

## 4. Sevilla Geo

### 4.1. Objetivo

Cargar la geografía oficial de Sevilla:

```text
district
neighborhood
```

Esta vertical es necesaria antes de asignar locales a barrios.

---

### 4.2. Scripts principales

```text
run_sevilla_geo_ingestion.py
load_sevilla_geo_reference.py
check_sevilla_geo_load.py
```

---

### 4.3. Flujo recomendado

```powershell
python -m scripts.run_sevilla_geo_ingestion
```

Después cargar la referencia:

```powershell
python -m scripts.load_sevilla_geo_reference
```

Validar:

```powershell
python -m scripts.check_sevilla_geo_load
```

---

### 4.4. Resultado esperado

```text
[OK] distritos cargados
[OK] barrios cargados
[OK] geometrías válidas
[OK] relación distrito-barrio correcta
[OK] geometría disponible para point_in_polygon
```

---

## 5. OSM / Overpass

### 5.1. Objetivo

Obtener POIs gastronómicos abiertos desde OpenStreetMap mediante Overpass.

Categorías habituales:

```text
restaurant
cafe
bar
fast_food
pub
```

---

### 5.2. Scripts disponibles

```text
run_overpass_ingestion.py
profile_overpass_raw.py
transform_overpass_candidates.py
check_overpass_staging.py
deduplicate_overpass_candidates.py
import_overpass_places.py
check_overpass_import.py
load_overpass_pipeline.py
```

---

### 5.3. Flujo recomendado con orquestador

El modo más cómodo es usar:

```powershell
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Este script ejecuta el flujo completo:

```text
Overpass raw
→ transform
→ staging check
→ dedup
→ import
→ import check
```

---

### 5.4. Flujo manual alternativo

Si se quiere ejecutar paso a paso:

```powershell
python -m scripts.run_overpass_ingestion `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Después, usando el `raw_asset_id` generado:

```powershell
python -m scripts.profile_overpass_raw --raw-asset-id <RAW_ASSET_ID>
python -m scripts.transform_overpass_candidates --raw-asset-id <RAW_ASSET_ID>
python -m scripts.check_overpass_staging --raw-asset-id <RAW_ASSET_ID>
python -m scripts.deduplicate_overpass_candidates --raw-asset-id <RAW_ASSET_ID>
python -m scripts.import_overpass_places --raw-asset-id <RAW_ASSET_ID>
python -m scripts.check_overpass_import --raw-asset-id <RAW_ASSET_ID>
```

---

### 5.5. Resultado esperado

```text
[OK] raw Overpass guardado
[OK] candidatos normalizados
[OK] deduplicación aplicada
[OK] places creados/actualizados
[OK] place_source_ref creadas
[OK] categorías asignadas
[OK] barrios asignados
[OK] validation issues controladas
```

---

## 6. Google Places Text Search

### 6.1. Objetivo

Descubrir y enriquecer locales gastronómicos reales mediante Google Places.

Esta vertical alimenta:

```text
place
place_source_ref
category
place_category
place_neighborhood_assignment
```

---

### 6.2. Scripts disponibles

```text
run_google_places_text_search.py
check_google_places_raw.py
transform_google_places_candidates.py
check_google_places_staging.py
deduplicate_google_places_candidates.py
check_google_places_deduplication.py
import_google_places_places.py
check_google_places_import.py
load_google_places_pipeline.py
run_google_places_neighborhood_batch.py
check_google_places_batch.py
run_google_places_place_details.py
```

---

### 6.3. Reglas antes de ejecutar

```text
1. GOOGLE_MAPS_API_KEY debe estar configurada.
2. Places API debe estar habilitada.
3. Facturación y alertas deben estar activas.
4. No usar FieldMask: *.
5. Empezar con dry-run o muestra pequeña.
6. No lanzar toda Sevilla de golpe.
```

---

### 6.4. Flujo individual recomendado

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_test `
  --max-result-count 5
```

Modo sin importación:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_no_import `
  --max-result-count 5 `
  --skip-import
```

---

### 6.5. Batch por barrios

Dry-run:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_dry_run `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --dry-run
```

Ejecución real con importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-errors 10
```

Check de batch:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_test_import `
  --save-artifact
```

---

### 6.6. Resultado esperado

```text
plan_has_no_duplicate_query_names = true
executed_query_count_matches_results = true
no_errors_or_allowed = true
all_success_have_raw_asset_id = true
all_import_checks_pass_when_required = true
no_duplicate_source_run_ids = true
no_duplicate_raw_asset_ids = true
```

---

## 7. Google Places Reviews

### 7.1. Objetivo

Obtener reviews reales de locales ya consolidados con `place_source_ref` de Google.

La vertical alimenta:

```text
review
```

Y deja cada review enlazada a:

```text
review → place → place_source_ref → neighborhood → district
```

---

### 7.2. Scripts disponibles

```text
transform_google_places_reviews.py
check_google_places_reviews_staging.py
import_google_places_reviews.py
check_google_places_reviews_import.py
load_google_places_reviews_pipeline.py
run_google_places_reviews_batch.py
check_google_places_reviews_batch.py
```

También se puede usar:

```text
run_google_places_place_details.py
```

para obtener solo el raw de Place Details.

---

### 7.3. Flujo individual recomendado

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_import
```

Modo sin importación:

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_no_import `
  --skip-import
```

---

### 7.4. Batch de reviews

Dry-run:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_dry_run `
  --limit-places 5 `
  --dry-run
```

Batch real:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_import_v1 `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

Check:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_import_v1 `
  --save-artifact
```

---

### 7.5. Reglas de escalado

```text
1. Pedir reviews solo de locales ya importados.
2. Ejecutar tandas pequeñas.
3. Priorizar locales sin reviews previas.
4. No usar --allow-large-batch salvo validación previa.
5. Permitir 0 reviews por local salvo que se use --require-reviews.
6. Revisar Google Cloud tras tandas reales.
```

---

### 7.6. Resultado esperado

```text
planned_place_count_matches_plan = true
executed_place_count_matches_results = true
success_count_matches_results = true
no_errors_or_allowed = true
staging_parts_match_total = true
import_count_matches_parts = true
all_staging_checks_pass = true
all_import_checks_pass_when_required = true
no_duplicate_google_place_ids_in_success_scope = true
```

---

## 8. Yelp Open Dataset

### 8.1. Objetivo

Construir un corpus externo gastronómico para IA y validar el prototipo IA completo.

Yelp no se usa como producción Sevilla.

---

### 8.2. Scripts disponibles

```text
profile_yelp_tar.py
extract_yelp_selected_files.py
profile_yelp_jsonl_files.py
build_yelp_food_business_subset.py
build_yelp_food_review_subset.py
build_yelp_nlp_corpus.py
check_yelp_nlp_corpus.py
```

---

### 8.3. Flujo recomendado

Perfil del TAR:

```powershell
python -m scripts.profile_yelp_tar `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

Extracción controlada:

```powershell
python -m scripts.extract_yelp_selected_files `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

Perfil JSONL:

```powershell
python -m scripts.profile_yelp_jsonl_files `
  --save-artifact
```

Subset de negocios gastronómicos:

```powershell
python -m scripts.build_yelp_food_business_subset `
  --min-review-count 1 `
  --save-artifact
```

Subset de reviews:

```powershell
python -m scripts.build_yelp_food_review_subset `
  --max-lines 100000 `
  --min-text-length 40 `
  --save-artifact
```

Corpus NLP:

```powershell
python -m scripts.build_yelp_nlp_corpus `
  --corpus-name yelp_food_reviews_corpus_sample_100k_lines `
  --min-text-length 80 `
  --max-text-length 5000 `
  --save-artifact
```

Check del corpus:

```powershell
python -m scripts.check_yelp_nlp_corpus `
  --corpus-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl `
  --save-artifact
```

---

### 8.4. Resultado esperado

```text
[OK] TAR perfilado
[OK] business/review extraídos
[OK] JSONL válido
[OK] food businesses subset generado
[OK] food reviews subset generado
[OK] corpus NLP generado
[OK] corpus NLP validado
```

---

## 9. Handoff hacia IA

La ingesta termina cuando existen datos suficientes y validados para IA.

### Para Yelp prototype

El handoff fue:

```text
Yelp corpus
→ notebooks IA
→ artefactos IA
→ loaders IA
→ PostgreSQL
```

### Para Sevilla pilot

El handoff actual es:

```text
Google Places Reviews
→ export_reviews_for_ai.py
→ check_ai_review_export.py
→ notebooks 12–17
→ load_sevilla_ai_pilot_outputs.py
→ check_sevilla_ai_pilot_loaded.py
→ query_sevilla_hidden_gems_demo.py
```

El flujo IA detallado se documenta en:

```text
docs/10_ai_module/
docs/11_ai_integration/
docs/12_sevilla_ai_pilot/
docs/08_operations/04_ai_pipeline_operations.md
```

---

## 10. Checks mínimos tras una ingesta

Después de cualquier ejecución real, debe existir al menos un check asociado.

| Vertical | Check principal |
|---|---|
| Sevilla Geo | `check_sevilla_geo_load.py` |
| Overpass | `check_overpass_import.py` |
| Google Places | `check_google_places_batch.py` o `check_google_places_import.py` |
| Google Places Reviews | `check_google_places_reviews_batch.py` o `check_google_places_reviews_import.py` |
| Yelp corpus | `check_yelp_nlp_corpus.py` |
| IA Yelp | `check_ai_ranking_loaded.py` |
| IA Sevilla | `check_sevilla_ai_pilot_loaded.py` |

---

## 11. Naming recomendado para ejecuciones

Usar nombres claros y estables:

```text
gp_test_import
gp_pilot_5_barrios_import_v1
gp_reviews_ai_pilot_03_import
sevilla_gastronomy_bbox
yelp_food_reviews_corpus_sample_100k_lines
sevilla_pilot_v1
```

Evitar nombres excesivamente largos, especialmente en Windows, porque pueden provocar problemas de rutas largas.

---

## 12. Gestión de artefactos

Los scripts generan archivos en:

```text
data/raw/
data/staging/
data/artifacts/
```

Regla general:

```text
Raw, staging, JSONL grandes, CSV grandes y reviews completas no deben subirse a Git.
```

Sí se pueden versionar:

```text
- scripts;
- documentación;
- DDL;
- summaries pequeños si no contienen texto sensible;
- ejemplos mínimos anonimizados si fueran necesarios.
```

---

## 13. Criterio de ingesta correcta

Una ingesta se considera correcta cuando:

```text
[OK] el script finaliza sin excepción
[OK] se genera artifact/report
[OK] el check asociado pasa
[OK] no hay errores críticos
[OK] los contadores cuadran
[OK] no hay huérfanos
[OK] no hay duplicados inesperados
[OK] la base refleja los registros esperados
```

Para Google Places y Reviews, además:

```text
[OK] Google Cloud usage revisado
[OK] no se han hecho llamadas masivas accidentales
[OK] no se ha usado FieldMask excesivo
```

---

## 14. Cuándo escalar

No escalar una fuente hasta que:

```text
1. Una prueba individual funcione.
2. Un batch pequeño funcione.
3. El check global sea correcto.
4. Los artifacts sean coherentes.
5. No existan validation issues críticas.
6. Se conozca el coste aproximado si hay API externa.
```

Escalado recomendado:

```text
1 local / 1 query
→ 5 locales / pocas queries
→ 1 barrio
→ varios barrios
→ 1 distrito
→ varios distritos
```

---

## 15. Conclusión

La ingesta en Hidden Gems debe realizarse de forma incremental, controlada y validada.

El proyecto ya cuenta con verticales suficientes para pasar de fuentes externas a un modelo canónico y a una capa IA derivada:

```text
Sevilla Geo + Overpass + Google Places + Google Reviews + Yelp
→ place / review / neighborhood
→ artefactos IA
→ ranking consultable
```

El siguiente runbook operativo recomendado es:

```text
03_google_places_operations.md
```

porque Google Places y Google Places Reviews son las fuentes más sensibles por coste, cuotas y dependencia externa.
