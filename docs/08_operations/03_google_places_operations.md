# 03. Google Places Operations



## 1. Propósito

Este documento actúa como **runbook operativo específico para Google Places** dentro de Hidden Gems.

Su objetivo no es repetir toda la documentación técnica de las verticales, sino explicar cómo operar de forma segura los procesos relacionados con:

- Google Places Text Search;
- Google Places Reviews mediante Place Details;
- batches por barrio o distrito;
- checks de raw, staging, deduplicación, importación y batch;
- control de coste, cuotas y errores;
- preparación de reviews locales para el piloto IA Sevilla.

Google Places es una fuente especialmente sensible porque depende de una API externa con clave, facturación, cuotas y posibles costes. Por eso, cualquier operación debe ejecutarse con límites claros, validaciones y revisión de artefactos.

---

## 2. Principios operativos

Las reglas principales para trabajar con Google Places son:

```text
1. Empezar siempre con dry-run cuando se use un batch.
2. Probar primero con pocos barrios o pocos locales.
3. Mantener max-result-count bajo.
4. No usar FieldMask: *.
5. No pedir Details de forma masiva.
6. No mezclar Text Search y Reviews en el mismo flujo.
7. Pedir reviews solo de locales ya consolidados.
8. Ejecutar checks después de cada batch.
9. Revisar artifacts JSON antes de escalar.
10. Revisar uso/cuotas en Google Cloud tras tandas reales.
```

La regla práctica es:

```text
Primero planificar → después ejecutar sin importar → después importar → después comprobar.
```

---

## 3. Variables y requisitos previos

Antes de ejecutar cualquier proceso de Google Places debe existir configuración válida en `.env`.

Variable principal:

```env
GOOGLE_MAPS_API_KEY=tu_clave_real
```

La clave real no debe subirse nunca al repositorio.

También debe estar configurada la conexión a PostgreSQL/PostGIS y el schema `hidden_gems` debe estar creado.

Checks mínimos recomendados antes de operar:

```powershell
python -m scripts.check_db_connection
python -m scripts.check_schema
```

Si se va a trabajar por barrios, la geografía de Sevilla debe estar cargada:

```powershell
python -m scripts.check_sevilla_geo_load
```

---

## 4. Diferencia entre Text Search y Reviews

Google Places se opera en dos bloques separados.

| Bloque | Endpoint | Objetivo | Resultado principal |
|---|---|---|---|
| Google Places Text Search | `places:searchText` | Descubrir y consolidar locales | `place`, `place_source_ref`, categoría, barrio |
| Google Places Reviews | `places/{place_id}` | Obtener reviews de locales ya consolidados | `review` |

La separación es importante porque:

- Text Search sirve para encontrar locales;
- Reviews sirve para enriquecer locales existentes;
- no se importan reviews huérfanas;
- el coste y los FieldMask se controlan de forma distinta;
- cada vertical tiene sus propios artifacts y checks.

---

## 5. Operación individual de Text Search

### 5.1. Ejecución recomendada con orquestador completo

Para una consulta individual, el script recomendado es:

```text
scripts/load_google_places_pipeline.py
```

Ejemplo:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_test `
  --max-result-count 5
```

Este flujo ejecuta:

```text
Text Search
→ raw
→ check raw interno
→ staging
→ check staging interno
→ deduplicación
→ check dedup interno
→ importación
→ check import interno
→ pipeline_summary.json
```

---

### 5.2. Ejecución sin importación

Antes de escribir en base de datos, puede probarse con:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_no_import `
  --max-result-count 5 `
  --skip-import
```

Este modo genera raw, staging y deduplicación, pero no inserta ni actualiza `place`.

---

### 5.3. Ejecución paso a paso

Aunque el orquestador es lo recomendado, también puede ejecutarse la vertical por piezas:

```powershell
python -m scripts.run_google_places_text_search `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_text_search_test `
  --max-result-count 3
```

Después:

```powershell
python -m scripts.check_google_places_raw `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

```powershell
python -m scripts.transform_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

```powershell
python -m scripts.check_google_places_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

```powershell
python -m scripts.deduplicate_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

```powershell
python -m scripts.check_google_places_deduplication `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

```powershell
python -m scripts.import_google_places_places `
  --raw-asset-id <RAW_ASSET_ID>
```

```powershell
python -m scripts.check_google_places_import `
  --source-run-id <SOURCE_RUN_ID> `
  --raw-asset-id <RAW_ASSET_ID>
```

---

## 6. Batch de Google Places por barrios

El script principal es:

```text
scripts/run_google_places_neighborhood_batch.py
```

Este script permite lanzar múltiples consultas Text Search por barrio o distrito usando el orquestador individual como unidad.

---

### 6.1. Dry-run del batch

Primer paso obligatorio antes de un batch real:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_dry_run `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --dry-run
```

El dry-run no llama a Google. Solo construye el plan.

Revisar:

```text
data/artifacts/google_places_batches/<batch_name>/plan.json
```

---

### 6.2. Batch sin importación

Segundo paso recomendado:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_no_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --skip-import `
  --max-errors 10
```

Después validar:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_test_no_import `
  --save-artifact
```

---

### 6.3. Batch con importación

Solo cuando el batch sin importación sea correcto:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-errors 10
```

Validar:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_test_import `
  --save-artifact
```

---

### 6.4. Batch por distrito

Ejemplo:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_distrito_triana_import_v1 `
  --district Triana `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-total-queries 10 `
  --max-errors 10
```

Usar `--max-total-queries` como límite de seguridad.

---

## 7. Artefactos de Google Places Text Search

Cada ejecución puede generar:

```text
data/raw/google_places/...
```

```text
data/staging/google_places/<raw_asset_id>/
├── summary.json
├── accepted_candidates.json
├── needs_review_candidates.json
├── rejected_candidates.json
└── issues.json
```

```text
data/staging/google_places/<raw_asset_id>/deduplication/
├── dedup_summary.json
├── unique_candidates.json
├── duplicate_groups.json
└── pair_evidences.json
```

```text
data/staging/google_places/<raw_asset_id>/deduplication/import/
├── import_summary.json
└── pipeline_summary.json
```

```text
data/artifacts/google_places_batches/<batch_name>/
├── plan.json
├── results.json
├── batch_summary.json
└── batch_check.json
```

---

## 8. Operación individual de Google Places Reviews

La vertical de reviews solo debe ejecutarse sobre locales con `place_source_ref` de Google Places.

El orquestador recomendado es:

```text
scripts/load_google_places_reviews_pipeline.py
```

---

### 8.1. Reviews de un local concreto

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_import
```

---

### 8.2. Reviews sin importación

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_no_import `
  --skip-import
```

---

### 8.3. Primera prueba automática

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --limit-first `
  --query-name gp_reviews_pipeline_limit_first_test
```

---

### 8.4. Forzar que haya reviews

Por defecto, Google puede devolver 0 reviews sin que sea fallo.

Si se quiere forzar error cuando no haya reviews:

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_require_reviews `
  --require-reviews
```

---

## 9. Batch de Google Places Reviews

Script principal:

```text
scripts/run_google_places_reviews_batch.py
```

---

### 9.1. Dry-run

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_dry_run_v1 `
  --limit-places 5 `
  --dry-run
```

---

### 9.2. Batch sin importación

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_no_import_v1 `
  --limit-places 5 `
  --skip-import `
  --max-total-places 5 `
  --max-errors 5
```

---

### 9.3. Batch con importación

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

Validar después:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --save-artifact
```

---

### 9.4. Batch por barrio

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_santa_cruz_import_v1 `
  --neighborhood "SANTA CRUZ" `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

---

### 9.5. Batch por distrito

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_distrito_triana_import_v1 `
  --district Triana `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

---

## 10. Artefactos de Google Places Reviews

Por ejecución individual:

```text
data/staging/google_places_reviews/<raw_asset_id>/
├── summary.json
├── accepted_reviews.json
├── rejected_reviews.json
└── issues.json
```

Si hay importación:

```text
data/staging/google_places_reviews/<raw_asset_id>/import/
├── import_summary.json
└── pipeline_summary.json
```

Por batch:

```text
data/artifacts/google_places_reviews_batches/<batch_name>/
├── plan.json
├── results.json
├── batch_summary.json
└── reviews_batch_check.json
```

---

## 11. Interpretación de checks de batch

Los checks de batch deben terminar con todos los checks críticos en `true`.

Para Google Places Text Search, revisar:

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

Para Google Places Reviews, revisar además:

```text
planned_place_count_matches_plan
staging_parts_match_total
import_count_matches_parts
all_success_have_raw_summary
all_success_have_staging_summary
all_success_have_staging_checks
all_staging_checks_pass
all_success_have_import_summary_when_required
all_success_have_import_checks_when_required
all_import_checks_pass_when_required
no_duplicate_place_source_ref_ids_in_success_scope
no_duplicate_google_place_ids_in_success_scope
no_failed_internal_staging_checks
no_failed_internal_import_checks
```

---

## 12. Relación con el piloto IA Sevilla

El flujo de Google Places y Reviews ya ha alimentado el piloto IA Sevilla.

Estado del piloto usado como referencia:

```text
Google Places Sevilla:
- 800+ locales de Google Places
- 4.000+ reviews de Google Places

Piloto IA Sevilla:
- 2.979 menciones de platos
- 2.212 señales place + dish
- 256 candidatos puntuados
- 150 candidatos seleccionados
- 55 barrios cubiertos
- 11 distritos cubiertos
- ready_for_sevilla_pilot_queries = true
```

La vertical Google Places sigue siendo de adquisición. La IA se ejecuta después, en notebooks/scripts específicos, y se carga en tablas derivadas.

---

## 13. Reglas de coste y seguridad

Checklist antes de ejecutar un batch real:

```text
[ ] API key configurada y restringida.
[ ] Presupuesto/alertas de Google Cloud activos.
[ ] FieldMask limitado.
[ ] max-result-count bajo.
[ ] max-total-queries o max-total-places definido.
[ ] dry-run ejecutado.
[ ] skip-import probado si es una tanda nueva.
[ ] batch_name único y descriptivo.
[ ] checks posteriores previstos.
```

No hacer:

```text
[ ] No usar FieldMask: *.
[ ] No ejecutar toda Sevilla de golpe.
[ ] No pedir reviews de locales no consolidados.
[ ] No usar --allow-large-batch salvo necesidad justificada.
[ ] No subir raw/reviews completas a Git.
[ ] No incluir la API key en documentación o logs.
```

---

## 14. Problemas frecuentes

| Problema | Causa habitual | Solución |
|---|---|---|
| API key no configurada | Falta `GOOGLE_MAPS_API_KEY` en `.env` | Revisar `.env` y settings |
| Error de JSON en `curl` | PowerShell interpreta mal comillas | Usar scripts Python |
| SSL `CRYPT_E_NO_REVOCATION_CHECK` | Problema de `curl.exe` en Windows | Usar `requests` desde Python |
| Rutas demasiado largas | `query_name` largo | Usar nombres cortos de batch/query |
| Barrio no encontrado | Diferencia de tildes o nombre oficial | Revisar aliases en YAML |
| Google devuelve 0 reviews | Comportamiento normal de Place Details | No usar `--require-reviews` salvo pruebas |
| Batch con errores | Límite, API, datos o conexión | Revisar `results.json` y `batch_check.json` |

---

## 15. Cierre operativo

Un proceso de Google Places o Reviews puede considerarse cerrado cuando:

```text
[ ] El batch_summary existe.
[ ] El batch_check existe.
[ ] No hay errores no permitidos.
[ ] Los checks críticos están en true.
[ ] Los contadores coinciden.
[ ] Los artifacts están guardados.
[ ] No se han subido datos sensibles a Git.
[ ] Si aplica, las reviews están disponibles para export IA.
```

---

## 16. Actualización final: papel de Google Places en Sevilla IA v2

Google Places y Google Places Reviews son la base real de la fase Sevilla IA v2.

```text
Google Places Text Search
→ locales reales de Sevilla
→ place / place_source_ref / barrio / distrito

Google Places Reviews
→ reseñas reales asociadas a esos locales
→ review
→ datasets IA Sevilla
→ modelos entrenados
→ ranking v2
→ dashboard final
```

Resultados derivados en la fase final:

```text
ranking_v2_candidates_scored = 2.335
selected_hidden_gem_candidates_v2 = 268
selected_places_v2 = 198
selected_neighborhoods_v2 = 67
selected_districts_v2 = 11
```

Para la entrega actual no es necesario volver a consumir Google Places si ya existen los artefactos finales. Si en el futuro se quiere generar un ranking v3, se mantiene la regla:

```text
batch pequeño → check → export IA → modelos/inferencia → ranking → dashboard
```

Dashboard final asociado:

```text
dashboard/streamlit_sevilla_v2_app.py
```
