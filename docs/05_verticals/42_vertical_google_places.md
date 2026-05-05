# Vertical Google Places

## 1. Objetivo de la vertical

La vertical **Google Places** implementa el flujo completo de adquisición, validación, normalización, deduplicación e importación canónica de locales gastronómicos procedentes de Google Places.

Su objetivo no es descargar todos los locales posibles ni construir una aplicación final, sino integrar Google Places como una fuente dinámica dentro del pipeline de Hidden Gems.

La vertical permite:

* ejecutar consultas controladas contra Google Places;
* guardar respuestas raw trazables;
* transformar resultados en candidatos normalizados;
* validar calidad de datos;
* deduplicar resultados de una misma fuente;
* importar candidatos al modelo canónico;
* enlazar Google Places con `place` mediante `place_source_ref`;
* ejecutar batches por barrios;
* mantener control de coste, errores y trazabilidad;
* dejar locales preparados para una subvertical posterior de reseñas mediante Place Details.

La parte de reseñas se documenta en un archivo específico:

```text
docs/43_vertical_google_places_reviews.md
```

---

## 2. Encaje en la arquitectura general

La vertical sigue la arquitectura por capas definida para Hidden Gems:

```text
external source
→ connector
→ raw
→ staging
→ normalization
→ deduplication
→ canonical import
→ quality checks
→ artifacts
```

Aplicado a Google Places Text Search:

```text
Google Places API
→ GooglePlacesConnector
→ source_run + raw_asset
→ raw JSON
→ GooglePlacesTransformer
→ NormalizedPlaceCandidate
→ GooglePlacesDeduplicator
→ unique_candidates.json
→ GooglePlacesImporter
→ place / place_source_ref / category / barrio
→ checks + artifacts
```

La salida más importante de esta vertical es:

```text
place + place_source_ref.source_record_id = Google Place ID
```

Ese identificador permite después enriquecer locales ya consolidados con reviews mediante la vertical Google Places Reviews.

---

## 3. Principio de diseño

La vertical se ha construido con varios principios.

### 3.1. No sobrescribir directamente el modelo canónico

Google Places no escribe directamente sobre `place` al recibir la respuesta. Primero pasa por:

```text
raw
→ staging
→ deduplication
→ importación controlada
```

### 3.2. Raw siempre trazable

Cada respuesta se guarda como evidencia reproducible en `data/raw` y se registra en `raw_asset`.

### 3.3. Importación incremental

Cada ejecución puede:

* crear nuevos `place`;
* actualizar `place` existentes;
* crear nuevas referencias externas;
* actualizar referencias Google ya existentes.

### 3.4. Deduplicación antes de importar

Aunque Google Place ID es estable, los resultados pueden repetirse entre consultas diferentes. Por eso se deduplica antes de importar.

### 3.5. Control de coste

La vertical evita:

* paginación masiva;
* campos avanzados;
* reviews dentro del flujo base de Text Search;
* `FieldMask: *`;
* batches grandes.

---

## 4. Componentes implementados

### 4.1. Conector

```text
src/connectors/google_places.py
```

Clase:

```python
GooglePlacesConnector
```

Responsabilidades para esta vertical:

* validar API key;
* construir endpoint;
* construir FieldMask;
* ejecutar Text Search;
* crear `source_run`;
* guardar `raw_asset`;
* registrar errores;
* devolver resumen.

El mismo conector también contiene el método `run_place_details(...)`, usado por la subvertical de reviews, pero el flujo principal de este documento se centra en Text Search.

---

### 4.2. Transformer

```text
src/normalization/google_places_transformer.py
```

Clase:

```python
GooglePlacesTransformer
```

Responsabilidades:

* leer payload raw;
* validar estructura;
* extraer campos útiles;
* normalizar nombres;
* construir coordenadas GeoJSON;
* resolver categoría primaria;
* calcular señales de calidad;
* separar candidatos accepted / needs_review / rejected.

---

### 4.3. Deduplicador

```text
src/normalization/google_places_deduplicator.py
```

Clase:

```python
GooglePlacesDeduplicator
```

Responsabilidades:

* detectar duplicados intra-fuente;
* agrupar candidatos repetidos;
* seleccionar representante;
* generar evidencias;
* producir `unique_candidates.json`.

---

### 4.4. Importador

```text
src/normalization/google_places_importer.py
```

Clase:

```python
GooglePlacesImporter
```

Responsabilidades:

* importar candidatos aceptados;
* buscar `place_source_ref` existente;
* hacer matching con `place` existente;
* crear nuevos `place` si no hay match;
* crear/actualizar `place_source_ref`;
* crear/actualizar categoría primaria;
* asignar barrio;
* registrar incidencias.

La lógica común vive en:

```text
src/normalization/base_place_candidate_importer.py
```

---

### 4.5. Orquestador individual

```text
scripts/load_google_places_pipeline.py
```

Ejecuta una consulta completa de principio a fin.

---

### 4.6. Batch por barrios

```text
scripts/run_google_places_neighborhood_batch.py
```

Ejecuta múltiples consultas por barrios usando el orquestador individual.

---

### 4.7. Configuración de consultas

```text
src/config/google_places_query_plan.yaml
```

Define:

* valores por defecto;
* plantillas de búsqueda;
* alias de barrios;
* nombres naturales para Google Places.

---

## 5. Flujo individual completo

El flujo individual se ejecuta con:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_test `
  --max-result-count 5
```

Internamente ejecuta:

```text
1. Google Places Text Search
2. Guardado raw
3. Validación raw
4. Transformación a NormalizedPlaceCandidate
5. Validación staging
6. Deduplicación
7. Validación dedup
8. Importación canónica
9. Validación post-import
10. Generación de pipeline_summary.json
```

---

## 6. Flujo individual sin importación

Para pruebas seguras:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_no_import `
  --max-result-count 5 `
  --skip-import
```

Este modo ejecuta hasta deduplicación, pero no escribe en:

* `place`;
* `place_source_ref`;
* `place_category`;
* `place_neighborhood_assignment`.

---

## 7. Artefactos generados por una ejecución individual

Para cada `raw_asset_id` se genera:

```text
data/raw/google_places/...
```

```text
data/staging/google_places/<raw_asset_id>/
  summary.json
  accepted_candidates.json
  needs_review_candidates.json
  rejected_candidates.json
  issues.json
```

```text
data/staging/google_places/<raw_asset_id>/deduplication/
  dedup_summary.json
  unique_candidates.json
  duplicate_groups.json
  pair_evidences.json
```

```text
data/staging/google_places/<raw_asset_id>/deduplication/import/
  import_summary.json
  pipeline_summary.json
```

```text
data/artifacts/google_places_pipeline/
  <raw_asset_id>_pipeline_summary.json
```

---

## 8. Comandos individuales disponibles

### 8.1. Ingesta raw

```powershell
python -m scripts.run_google_places_text_search `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_text_search_test `
  --max-result-count 3
```

### 8.2. Check raw

```powershell
python -m scripts.check_google_places_raw `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

### 8.3. Transformación

```powershell
python -m scripts.transform_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

### 8.4. Check staging

```powershell
python -m scripts.check_google_places_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

### 8.5. Deduplicación

```powershell
python -m scripts.deduplicate_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

### 8.6. Check deduplicación

```powershell
python -m scripts.check_google_places_deduplication `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

### 8.7. Importación

```powershell
python -m scripts.import_google_places_places `
  --raw-asset-id <RAW_ASSET_ID>
```

### 8.8. Check importación

```powershell
python -m scripts.check_google_places_import `
  --source-run-id <SOURCE_RUN_ID> `
  --raw-asset-id <RAW_ASSET_ID>
```

---

## 9. Batch por barrios

El batch por barrios permite ejecutar varias consultas Google Places de forma controlada.

Script:

```text
scripts/run_google_places_neighborhood_batch.py
```

Este script incluye un bloque de comentario operativo con ejemplos de uso para:

* `dry-run`;
* ejecución sin importación;
* ejecución con importación;
* piloto de cinco barrios;
* ejecución por distrito;
* plantillas personalizadas.

---

## 10. Selección por barrios concretos

Ejemplo en modo `dry-run`:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_dry_run_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --dry-run
```

Ejemplo con importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-errors 10
```

---

## 11. Selección por distrito

Ejemplo para distrito Triana:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_distrito_triana_import_v1 `
  --district Triana `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-total-queries 10
```

El script selecciona todos los barrios pertenecientes al distrito indicado.

---

## 12. Modo sin importación

Para probar sin escribir en tablas canónicas:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_no_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --skip-import `
  --max-errors 10
```

---

## 13. Artefactos de batch

Cada batch genera:

```text
data/artifacts/google_places_batches/<batch_name>/
  plan.json
  results.json
  batch_summary.json
```

Si se ejecuta check global, también:

```text
data/artifacts/google_places_batches/<batch_name>/batch_check.json
```

---

## 14. Check global de batch

Script:

```text
scripts/check_google_places_batch.py
```

Uso:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_alias_import_v1 `
  --save-artifact
```

Comprueba:

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

---

## 15. Configuración YAML de la vertical

Archivo:

```text
src/config/google_places_query_plan.yaml
```

Ejemplo:

```yaml
version: 1

defaults:
  language_code: es
  region_code: ES
  max_result_count: 5
  queries_per_neighborhood: 2
  sleep_seconds: 1.0

text_search:
  query_templates:
    - "restaurantes en {search_name}, Sevilla"
    - "bares de tapas en {search_name}, Sevilla"
    - "cafeterías en {search_name}, Sevilla"

neighborhood_aliases:
  NERVION: "Nervión"
  TRIANA CASCO ANTIGUO: "Triana"
  TRIANA ESTE: "Triana Este"
  TRIANA OESTE: "Triana Oeste"
  EL TARDON-EL CARMEN: "El Tardón, Triana"
  BARRIO LEON: "Barrio León"
  SANTA CRUZ: "Santa Cruz"
  ARENAL: "El Arenal"
  LOS REMEDIOS: "Los Remedios"
```

---

## 16. Nombres oficiales vs nombres de búsqueda

Los nombres oficiales proceden de la fuente geográfica de Sevilla y se conservan para trazabilidad.

Ejemplo:

```text
TRIANA CASCO ANTIGUO
```

Pero Google Places puede responder mejor con un texto más natural:

```text
Triana
```

Por eso el batch usa:

```text
neighborhood_name = TRIANA CASCO ANTIGUO
search_name = Triana
```

La consulta enviada es:

```text
restaurantes en Triana, Sevilla
```

pero el pipeline conserva el barrio oficial para análisis y trazabilidad.

La asignación geográfica final se realiza por coordenadas:

```text
place.location
→ point_in_polygon
→ neighborhood / district
```

---

## 17. Piloto de cinco barrios

La vertical se validó con un piloto de cinco barrios:

```text
TRIANA CASCO ANTIGUO
NERVION
SANTA CRUZ
ARENAL
LOS REMEDIOS
```

Configuración:

```text
2 consultas por barrio
5 resultados por consulta
10 llamadas máximas
sin paginación
sin Place Details
sin reviews en Text Search
```

Comando:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_pilot_5_barrios_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --neighborhood "SANTA CRUZ" `
  --neighborhood "ARENAL" `
  --neighborhood "LOS REMEDIOS" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-total-queries 10 `
  --max-errors 10
```

Check:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_pilot_5_barrios_import_v1 `
  --save-artifact
```

Resultado: correcto.

---

## 18. Relación con Google Places Reviews

Esta vertical base consolida locales y crea `place_source_ref` de Google.

La subvertical de reviews usa precisamente esas referencias:

```text
place_source_ref.source_record_id
→ Google Place ID
→ Place Details
→ reviews
→ hidden_gems.review
```

No se pueden importar reviews de locales que no existan previamente en `place` y `place_source_ref`.

Esto mantiene el modelo limpio:

```text
Google Places Text Search
→ descubre local
→ place + place_source_ref

Google Places Reviews
→ enriquece local existente
→ review enlazada a place
```

La documentación completa de la subvertical está en:

```text
docs/43_vertical_google_places_reviews.md
```

---

## 19. Problemas detectados y soluciones aplicadas

### 19.1. Quoting de PowerShell con curl

La primera prueba con `curl` falló por cómo PowerShell interpretaba el JSON. Se resolvió probando la API con Python y `requests`.

### 19.2. Certificado SSL en curl de Windows

Apareció un error `CRYPT_E_NO_REVOCATION_CHECK` al usar `curl.exe`. Se evitó usando Python para las pruebas reales.

### 19.3. Rutas largas en Windows

Durante batches con `query_name` largo, `RawStorage` falló al escribir ficheros raw. Se solucionó acortando:

* `_slugify` de `RawStorage`;
* `query_name` generado por batch.

### 19.4. Nombres de barrio con tildes

`Nervión` no coincidía con `NERVION`. Se añadió normalización sin tildes mediante `unicodedata`.

### 19.5. Barrios administrativos poco naturales

`TRIANA CASCO ANTIGUO` no era ideal como texto de búsqueda. Se añadió `search_name` mediante YAML de alias.

### 19.6. Dependencia conceptual del importer de OSM

Google Places heredaba provisionalmente de `OSMOverpassImporter`. Se refactorizó a `BasePlaceCandidateImporter`.

### 19.7. Enriquecimiento posterior con reviews

Al añadir reviews se decidió no mezclar la lógica de Text Search con la de Place Details Reviews. Se creó una vertical separada para mantener:

* coste controlado;
* trazabilidad clara;
* reviews solo para locales ya consolidados;
* separación entre descubrimiento de locales y enriquecimiento textual.

---

## 20. Reglas actuales de escalado

La vertical queda cerrada con estas reglas:

```text
1. Escalar por barrios, no por grid/círculos todavía.
2. Usar Text Search para descubrimiento de locales.
3. Usar aliases/search_name.
4. Ejecutar batches pequeños.
5. No activar paginación.
6. No pedir reviews en el flujo base de Text Search.
7. No pedir Details masivos.
8. Mantener max_result_count bajo.
9. Comprobar batch después de cada ejecución.
10. Revisar uso en Google Cloud.
```

Para reviews, la regla adicional es:

```text
Pedir reviews solo de locales ya importados y por tandas pequeñas.
```

---

## 21. Flujo recomendado de uso

### Paso 1. Probar plan

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_dry_run `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --dry-run
```

### Paso 2. Ejecutar sin importación

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_no_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --skip-import
```

### Paso 3. Revisar batch

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_test_no_import `
  --save-artifact
```

### Paso 4. Ejecutar con importación

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 2 `
  --max-result-count 5
```

### Paso 5. Check final

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_test_import `
  --save-artifact
```

### Paso 6. Enriquecimiento posterior con reviews

Cuando los locales ya existen en `place` y `place_source_ref`, se puede ejecutar la vertical de reviews:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

Y validar:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --save-artifact
```

---

## 22. Estado final de la vertical

La vertical Google Places queda finalizada en su primera versión funcional:

```text
[OK] Preparación externa de Google Cloud
[OK] API key validada
[OK] Text Search operativo
[OK] Conector Google Places
[OK] Raw trazable
[OK] Checks de raw
[OK] Transformer a NormalizedPlaceCandidate
[OK] Checks de staging
[OK] Deduplicador intra-fuente
[OK] Checks de deduplicación
[OK] Importador canónico
[OK] Refactor a BasePlaceCandidateImporter
[OK] Checks post-importación
[OK] Orquestador individual
[OK] Batch por barrios
[OK] YAML de aliases/query plan
[OK] Check global de batch
[OK] Piloto de cinco barrios validado
[OK] Locales preparados para enrichment con reviews
```

La vertical queda lista para alimentar el modelo canónico de Hidden Gems mediante adquisiciones incrementales, controladas y trazables.

---

## 23. Fuera de alcance de esta vertical

No se incluye en esta vertical base:

* Nearby Search;
* grid/círculos;
* Place Details masivo;
* importación de reviews dentro del flujo Text Search;
* scraping;
* ranking de platos;
* extracción NLP;
* scoring gastronómico;
* API pública;
* dashboard BI.

La importación de reviews existe como subvertical separada:

```text
docs/43_vertical_google_places_reviews.md
```

---

## 24. Conclusión

La vertical Google Places completa una parte clave del pipeline de Hidden Gems: la incorporación de una fuente dinámica y comercial de alta cobertura, integrada de forma segura, incremental y trazable.

El sistema ya permite obtener datos reales de Google Places, almacenarlos como raw auditable, normalizarlos a un contrato común, deduplicarlos, importarlos al modelo canónico y validar todo el proceso tanto a nivel individual como por batch de barrios.

Además, la creación de `place_source_ref` con Google Place ID deja preparada la base para enriquecer locales con reviews reales mediante la vertical Google Places Reviews.

Gracias a esta vertical, Hidden Gems dispone de una base más sólida para fases posteriores de enriquecimiento, NLP, extracción de platos y ranking por barrio.
