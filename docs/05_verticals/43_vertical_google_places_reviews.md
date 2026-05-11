# Vertical Google Places Reviews


> **Nota de actualización (piloto IA Sevilla):** este documento conserva toda la documentación original de la subvertical Google Places Reviews y añade el estado posterior alcanzado. La subvertical sigue teniendo como responsabilidad adquirir y persistir reviews reales asociadas a locales ya consolidados. Posteriormente, esas reviews ya fueron exportadas y procesadas por la capa IA en modo piloto `sevilla_pilot`. Las partes que hablan de “futuras tareas NLP” se mantienen como contexto histórico de diseño, pero el flujo ya se ha ejecutado al menos como prototipo local no productivo.


## 1. Objetivo de la vertical

La vertical **Google Places Reviews** amplía la integración de Google Places para obtener comentarios reales de locales gastronómicos ya consolidados en el modelo canónico de Hidden Gems.

A diferencia de la vertical base de Google Places, cuyo objetivo era descubrir y consolidar locales, esta subvertical se centra en enriquecer esos locales con reseñas reales procedentes de Google Places mediante **Place Details**.

El objetivo principal es obtener comentarios asociados a locales reales de Sevilla para:

* enriquecer la base de datos operativa;
* disponer de reseñas reales vinculadas a `place`;
* preparar un corpus local inicial para futuras tareas de NLP;
* permitir, más adelante, extracción de platos mencionados;
* permitir análisis de sentimiento por comentario o por plato;
* conectar reseñas con barrio y distrito mediante el modelo geográfico existente;
* servir como base local para aplicar posteriormente modelos, reglas y señales desarrolladas inicialmente con Yelp Open Dataset como prototipo IA.

Esta vertical no sustituye a Yelp como corpus amplio de entrenamiento. Google Places Reviews se utiliza primero como fuente de comentarios reales y locales asociados a los locales del sistema.

---

## 2. Diferencia con la vertical Google Places base

La integración de Google Places se divide en dos partes:

| Vertical              | Objetivo principal                        | Resultado                                        |
| --------------------- | ----------------------------------------- | ------------------------------------------------ |
| Google Places base    | Descubrir y consolidar locales            | `place`, `place_source_ref`, categorías, barrio  |
| Google Places Reviews | Enriquecer locales existentes con reseñas | `review` asociado a `place` y `place_source_ref` |

La vertical de reviews **no descubre locales nuevos**. Solo trabaja con locales que ya existen en la base y que tienen una referencia Google válida.

Flujo base:

```text
Google Places Text Search
→ place
→ place_source_ref
```

Flujo de reviews:

```text
place_source_ref google_places
→ Google Place ID
→ Place Details
→ reviews
→ hidden_gems.review
```

Por tanto, no se guardan comentarios de locales que no estén ya consolidados en el sistema.

---

## 3. Principio de seguridad del modelo

La regla principal de esta vertical es:

```text
No se importan reviews huérfanas.
```

Cada review de Google debe estar asociada a:

```text
review.place_id
review.place_source_ref_id
review.source_place_record_id
```

Y esos tres valores deben coincidir con una referencia actual de Google Places en:

```text
hidden_gems.place_source_ref
```

Esto evita:

* comentarios sin local;
* comentarios asociados al local incorrecto;
* mezcla de fuentes;
* contaminación del modelo canónico;
* pérdida de trazabilidad;
* datos útiles para NLP pero no vinculables a barrio.

La relación final esperada es:

```text
review
→ place
→ place_source_ref
→ Google Place ID
→ place_neighborhood_assignment
→ neighborhood
→ district
```

---

## 4. Encaje en la arquitectura general

La vertical sigue el mismo patrón del resto del pipeline:

```text
external API
→ connector
→ raw
→ staging
→ quality check
→ import
→ post-import check
→ artifacts
```

Aplicado a Google Places Reviews:

```text
hidden_gems.place_source_ref
→ GooglePlacesConnector.run_place_details
→ raw_asset
→ GooglePlacesReviewsTransformer
→ NormalizedReviewCandidate
→ check staging
→ GooglePlacesReviewsImporter
→ hidden_gems.review
→ check import
→ batch summary
```

---

## 5. Fuente utilizada

La fuente utilizada sigue siendo:

```text
source_code = google_places
```

No se crea un `source_system` nuevo para reviews, porque las reseñas proceden de la misma fuente externa: Google Places.

La diferencia se registra mediante:

* `source_run.request_summary.purpose = place_details_reviews`;
* `raw_asset.asset_name` específico de details/reviews;
* rutas de staging diferenciadas;
* scripts específicos de reviews;
* campos de `review` asociados a Google Places.

---

## 6. Endpoint utilizado

La vertical utiliza **Place Details** de Places API New:

```text
GET https://places.googleapis.com/v1/places/{GOOGLE_PLACE_ID}
```

El `GOOGLE_PLACE_ID` se obtiene desde:

```text
hidden_gems.place_source_ref.source_record_id
```

Para Google Places, ese campo contiene el identificador externo del local.

Ejemplo:

```text
ChIJl5CETz9sEg0RBeilXxxRTFE
```

---

## 7. FieldMask utilizado

Para la fase actual se utiliza un FieldMask mínimo:

```text
id
 displayName
 reviews
```

En la llamada real se envía como:

```text
X-Goog-FieldMask: id,displayName,reviews
```

Este conjunto permite obtener:

* ID del place;
* nombre visible del local;
* lista de reviews devueltas por Google.

Opcionalmente, para pruebas controladas, el pipeline permite añadir:

```text
rating
userRatingCount
```

mediante:

```powershell
--include-rating-summary
```

Sin embargo, no es necesario para importar reseñas y no se utiliza por defecto.

---

## 8. Estructura real del payload de Google Reviews

La respuesta de Place Details para reviews tiene una estructura como esta:

```json
{
  "id": "ChIJl5CETz9sEg0RBeilXxxRTFE",
  "displayName": {
    "text": "Bar El 25 Bodega",
    "languageCode": "es"
  },
  "reviews": [
    {
      "name": "places/ChIJ.../reviews/...",
      "relativePublishTimeDescription": "Hace 8 meses",
      "rating": 5,
      "text": {
        "text": "Experiencia espectacular...",
        "languageCode": "es"
      },
      "originalText": {
        "text": "Experiencia espectacular...",
        "languageCode": "es"
      },
      "authorAttribution": {
        "displayName": "Ibra",
        "uri": "https://www.google.com/maps/contrib/.../reviews",
        "photoUri": "https://lh3.googleusercontent.com/..."
      },
      "publishTime": "2025-08-28T07:33:59.730025081Z",
      "flagContentUri": "https://www.google.com/local/content/rap/report?...",
      "googleMapsUri": "https://www.google.com/maps/reviews/data=..."
    }
  ]
}
```

Campos principales utilizados:

| Campo Google                               | Uso en Hidden Gems                  |
| ------------------------------------------ | ----------------------------------- |
| `id`                                       | `source_place_record_id`            |
| `displayName.text`                         | contexto del local                  |
| `reviews[].name`                           | señal de identidad de review        |
| `reviews[].rating`                         | `rating_value`                      |
| `reviews[].text.text`                      | `review_text_raw`                   |
| `reviews[].text.languageCode`              | `review_language`                   |
| `reviews[].originalText.text`              | `original_text_raw`                 |
| `reviews[].originalText.languageCode`      | `original_language`                 |
| `reviews[].authorAttribution.displayName`  | `author_name_raw`                   |
| `reviews[].authorAttribution.uri`          | `author_uri`                        |
| `reviews[].publishTime`                    | `review_created_at`                 |
| `reviews[].relativePublishTimeDescription` | `relative_publish_time_description` |
| `reviews[].googleMapsUri`                  | `source_review_url`                 |

---

## 9. Ampliación aplicada a la tabla `review`

Para soportar correctamente Google Places Reviews y preparar el modelo para NLP posterior, se amplió la tabla `hidden_gems.review`.

Campos añadidos:

```text
raw_asset_id
source_place_record_id
author_uri
relative_publish_time_description
source_payload_hash
is_operational_review
is_training_eligible
```

Objetivo de cada campo:

| Campo                               | Propósito                                                   |
| ----------------------------------- | ----------------------------------------------------------- |
| `raw_asset_id`                      | vincular la review al raw exacto del que procede            |
| `source_place_record_id`            | guardar el Google Place ID en la review                     |
| `author_uri`                        | conservar URL pública del autor cuando existe               |
| `relative_publish_time_description` | conservar texto relativo de publicación                     |
| `source_payload_hash`               | hash SHA-256 del payload fuente de la review                |
| `is_operational_review`             | indicar que la review pertenece a un local real del sistema |
| `is_training_eligible`              | indicar que puede usarse como corpus NLP                    |

También se añadieron índices y constraints para:

* `raw_asset_id`;
* `source_place_record_id`;
* `source_payload_hash`;
* `is_operational_review`;
* `is_training_eligible`;
* deduplicación por fuente, local fuente y review fuente.

---

## 10. Flags operativos y de entrenamiento

Google Places Reviews se inserta con:

```text
is_operational_review = true
is_training_eligible = true
```

Esto significa:

* la reseña está asociada a un local real del modelo canónico;
* la reseña puede utilizarse más adelante como ejemplo local para NLP.

Yelp Open Dataset ya se ha integrado como corpus externo y prototipo IA, pero con una naturaleza diferente. Yelp se utiliza para entrenamiento, validación e integración prototipo del módulo IA, no como fuente productiva de reviews de Sevilla. Google Places Reviews sigue siendo la fuente local y operativa sobre la que deberá aplicarse el sistema IA en la fase Sevilla.

---

## 11. Componentes implementados

### 11.1. Extensión del conector Google Places

Archivo:

```text
src/connectors/google_places.py
```

Método añadido:

```python
run_place_details(...)
```

Responsabilidades:

* recibir un Google Place ID;
* construir endpoint Place Details;
* construir FieldMask;
* ejecutar petición GET;
* crear `source_run`;
* guardar respuesta raw como `raw_asset`;
* generar resumen de reviews;
* cerrar el run como completado o fallido.

---

### 11.2. Modelo intermedio de review

Archivo:

```text
src/normalization/review_candidate.py
```

Modelo principal:

```python
NormalizedReviewCandidate
```

Submodelos:

```text
ReviewProvenance
ReviewAuthorInfo
ReviewTextInfo
ReviewRatingInfo
ReviewTimeInfo
ReviewQualitySignals
```

Este contrato intermedio permite representar una review antes de importarla a base de datos.

---

### 11.3. Transformer de Google Reviews

Archivo:

```text
src/normalization/google_places_reviews_transformer.py
```

Clase:

```python
GooglePlacesReviewsTransformer
```

Responsabilidades:

* leer payload raw de Place Details;
* extraer reviews;
* normalizar texto;
* extraer autor;
* extraer rating;
* extraer fechas;
* generar `source_review_id` estable;
* generar `source_payload_hash`;
* separar reviews aceptadas y rechazadas;
* generar incidencias de transformación.

---

### 11.4. Importador de Google Reviews

Archivo:

```text
src/normalization/google_places_reviews_importer.py
```

Clase:

```python
GooglePlacesReviewsImporter
```

Responsabilidades:

* leer candidatos aceptados;
* validar campos mínimos;
* validar relación `place` + `place_source_ref` + Google Place ID;
* buscar review existente;
* insertar review nueva;
* actualizar review existente;
* registrar incidencias si procede;
* actualizar contadores de `source_run`.

---

### 11.5. Orquestador individual

Archivo:

```text
scripts/load_google_places_reviews_pipeline.py
```

Ejecuta una unidad completa de reviews para un único local.

---

### 11.6. Batch de reviews

Archivo:

```text
scripts/run_google_places_reviews_batch.py
```

Ejecuta el orquestador individual para varios locales.

---

### 11.7. Check global de batch

Archivo:

```text
scripts/check_google_places_reviews_batch.py
```

Valida el resultado de un lote completo de reviews.

---

## 12. Generación de `source_review_id`

Google devuelve un campo `reviews[].name`, pero para evitar depender exclusivamente de un ID externo y mantener una deduplicación robusta, se genera un hash estable.

El `source_review_id` se calcula a partir de:

```text
google_place_id
review_name
author_name
publish_time
rating
review_text
```

Resultado:

```text
SHA-256 de 64 caracteres
```

Ejemplo:

```text
e8a7f720125ab1b1a5f6e2e4b5be0f336791ab7de2d815f1c7f42ea2ee48e90e
```

La deduplicación se realiza mediante:

```text
source_system_id
source_place_record_id
source_review_id
```

Esto permite reejecutar el pipeline sin duplicar reseñas.

---

## 13. Flujo individual paso a paso

El flujo individual es:

```text
1. Seleccionar place_source_ref de Google Places.
2. Obtener Google Place ID.
3. Ejecutar Place Details.
4. Guardar raw JSON.
5. Transformar reviews a NormalizedReviewCandidate.
6. Guardar staging.
7. Ejecutar check interno de staging.
8. Importar reviews aceptadas.
9. Ejecutar check interno post-importación.
10. Guardar pipeline_summary.json.
```

---

## 14. Script de Place Details individual

Archivo:

```text
scripts/run_google_places_place_details.py
```

Uso seleccionando automáticamente un local:

```powershell
python -m scripts.run_google_places_place_details `
  --limit-first
```

Uso con un `place_source_ref_id` concreto:

```powershell
python -m scripts.run_google_places_place_details `
  --place-source-ref-id <PLACE_SOURCE_REF_ID>
```

Uso incluyendo rating agregado:

```powershell
python -m scripts.run_google_places_place_details `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --include-rating-summary
```

Este script solo ejecuta Place Details y guarda raw. No transforma ni importa reviews.

---

## 15. Transformación de reviews

Archivo:

```text
scripts/transform_google_places_reviews.py
```

Uso:

```powershell
python -m scripts.transform_google_places_reviews `
  --raw-asset-id <RAW_ASSET_ID>
```

Genera:

```text
data/staging/google_places_reviews/<raw_asset_id>/summary.json
data/staging/google_places_reviews/<raw_asset_id>/accepted_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/rejected_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/issues.json
```

Resultado esperado en una respuesta normal de Google:

```text
total_reviews = 5
accepted_count = 5
rejected_count = 0
skipped_count = 0
issue_count = 0
```

---

## 16. Check de staging de reviews

Archivo:

```text
scripts/check_google_places_reviews_staging.py
```

Uso:

```powershell
python -m scripts.check_google_places_reviews_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Comprueba:

* coherencia de contadores;
* existencia de Google Place ID;
* coincidencia con el request original;
* existencia de reviews aceptadas;
* unicidad de `source_review_id`;
* formato SHA-256 de IDs y hashes;
* texto presente;
* vínculo con `place` y `place_source_ref`;
* flags `is_operational_review` e `is_training_eligible`.

Artefacto:

```text
data/artifacts/google_places_reviews_staging_qa/<raw_asset_id>_reviews_staging_check.json
```

---

## 17. Importación de reviews

Archivo:

```text
scripts/import_google_places_reviews.py
```

Uso:

```powershell
python -m scripts.import_google_places_reviews `
  --raw-asset-id <RAW_ASSET_ID>
```

Importa desde:

```text
data/staging/google_places_reviews/<raw_asset_id>/accepted_reviews.json
```

Hacia:

```text
hidden_gems.review
```

Campos principales insertados:

```text
place_id
place_source_ref_id
source_system_id
source_run_id
raw_asset_id
source_review_id
source_place_record_id
author_name_raw
author_uri
rating_value
review_text_raw
review_text_normalized
review_language
review_created_at
review_updated_at
relative_publish_time_description
source_review_url
translated_text
source_payload_hash
is_operational_review
is_training_eligible
is_active
is_deleted_in_source
```

La primera ejecución inserta reviews nuevas:

```text
inserted_count > 0
updated_count = 0
```

Una segunda ejecución sobre el mismo raw debe actualizar sin duplicar:

```text
inserted_count = 0
updated_count > 0
```

---

## 18. Check post-importación de reviews

Archivo:

```text
scripts/check_google_places_reviews_import.py
```

Uso:

```powershell
python -m scripts.check_google_places_reviews_import `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Comprueba:

* número de reviews importadas;
* coincidencia con `import_summary.json`;
* vínculo con `place`;
* vínculo con `place_source_ref`;
* existencia de texto;
* existencia de rating;
* idioma;
* `source_review_id`;
* `source_place_record_id`;
* `source_payload_hash`;
* flags operativos y de entrenamiento;
* estado activo;
* no duplicados;
* existencia de barrio actual;
* ausencia de incidencias.

Artefacto:

```text
data/artifacts/google_places_reviews_import_qa/<raw_asset_id>_reviews_import_check.json
```

---

## 19. Orquestador individual completo

Archivo:

```text
scripts/load_google_places_reviews_pipeline.py
```

Este es el script recomendado para ejecutar una adquisición completa de reviews para un local.

### Ejecución sin importación

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_no_import `
  --skip-import
```

### Ejecución con importación

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_import
```

### Ejecución automática sobre el primer local disponible

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --limit-first `
  --query-name gp_reviews_pipeline_limit_first_test
```

### Forzar error si no hay reviews

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_require_reviews `
  --require-reviews
```

Por defecto, el pipeline permite que un local devuelva 0 reviews, porque Google no garantiza que todos los Place Details devuelvan comentarios.

---

## 20. Artefactos del orquestador individual

Para cada ejecución se generan:

```text
data/raw/google_places/...
```

```text
data/staging/google_places_reviews/<raw_asset_id>/summary.json
data/staging/google_places_reviews/<raw_asset_id>/accepted_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/rejected_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/issues.json
```

Si hay importación:

```text
data/staging/google_places_reviews/<raw_asset_id>/import/import_summary.json
data/staging/google_places_reviews/<raw_asset_id>/import/pipeline_summary.json
```

Artefacto global:

```text
data/artifacts/google_places_reviews_pipeline/<raw_asset_id>_reviews_pipeline_summary.json
```

---

## 21. Batch de Google Places Reviews

Archivo:

```text
scripts/run_google_places_reviews_batch.py
```

Este script ejecuta varios pipelines individuales de reviews.

Permite:

* seleccionar locales concretos por `place_source_ref_id`;
* seleccionar por barrio;
* seleccionar por distrito;
* limitar número de locales;
* evitar locales que ya tienen reviews;
* incluir locales ya enriquecidos si se desea;
* ejecutar sin importación;
* ejecutar en dry-run;
* controlar errores;
* generar plan, resultados y resumen.

---

## 22. Comentario operativo de uso del batch

El script incluye un bloque de comentarios con ejemplos de uso.

### Dry-run

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_dry_run_v1 `
  --limit-places 5 `
  --dry-run
```

### Batch sin importación

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_no_import_v1 `
  --limit-places 5 `
  --skip-import `
  --max-total-places 5 `
  --max-errors 5
```

### Batch con importación

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

### Batch por barrio

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_santa_cruz_import_v1 `
  --neighborhood "SANTA CRUZ" `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

### Batch por distrito

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_distrito_triana_import_v1 `
  --district Triana `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

### Batch por IDs concretos

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_ids_import_v1 `
  --place-source-ref-id <PLACE_SOURCE_REF_ID_1> `
  --place-source-ref-id <PLACE_SOURCE_REF_ID_2> `
  --max-total-places 2
```

---

## 23. Opciones importantes del batch

### `--skip-import`

Ejecuta Place Details, raw, staging y checks, pero no inserta en `hidden_gems.review`.

### `--dry-run`

Solo construye el plan. No llama a Google.

### `--include-already-reviewed`

Incluye locales que ya tienen reviews de Google importadas.

Por defecto, el batch prioriza locales sin reviews previas para evitar repetir llamadas innecesarias.

### `--require-reviews`

Fuerza error si Google no devuelve reviews aceptadas para un local.

Por defecto, se permite que un local devuelva 0 reviews.

### `--max-total-places`

Límite de seguridad para evitar batches grandes por accidente.

### `--allow-large-batch`

Permite superar `--max-total-places`. Solo debería usarse cuando el flujo ya esté validado.

---

## 24. Artefactos del batch

Cada batch genera:

```text
data/artifacts/google_places_reviews_batches/<batch_name>/plan.json
data/artifacts/google_places_reviews_batches/<batch_name>/results.json
data/artifacts/google_places_reviews_batches/<batch_name>/batch_summary.json
```

Después del check global:

```text
data/artifacts/google_places_reviews_batches/<batch_name>/reviews_batch_check.json
```

---

## 25. Check global de batch

Archivo:

```text
scripts/check_google_places_reviews_batch.py
```

Uso:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --save-artifact
```

Para batches con errores que se quieran inspeccionar sin fallo final:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --allow-errors `
  --save-artifact
```

Checks principales:

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

---

## 26. Primera prueba individual validada

Se probó Place Details sobre el local:

```text
Bar El 25 Bodega
Google Place ID: ChIJl5CETz9sEg0RBeilXxxRTFE
```

Resultado:

```text
total_reviews = 5
accepted_count = 5
rejected_count = 0
skipped_count = 0
issue_count = 0
```

Posteriormente se importaron esas 5 reviews en `hidden_gems.review`.

Primera importación:

```text
input_count = 5
imported_count = 5
inserted_count = 5
updated_count = 0
skipped_count = 0
validation_issue_count = 0
```

La prueba de idempotencia confirmó que una segunda ejecución actualiza sin duplicar.

---

## 27. Primer batch real validado

Se ejecutó un batch real:

```text
batch_name = gp_reviews_batch_import_v1
planned_place_count = 5
executed_place_count = 5
success_count = 5
error_count = 0
```

Locales procesados:

```text
Restaurante La Reserva de Joaquín Márquez
Restaurante La Salá (Los Remedios)
Restaurante El Candil Los Remedios
Bar restaurante Casa Rafel
Bar Baratillo
```

Barrios procesados:

```text
LOS REMEDIOS
ARENAL
```

Distritos procesados:

```text
Los Remedios
Casco Antiguo
```

Totales:

```text
raw_review_count = 25
staging_total_reviews = 25
staging_accepted_count = 25
staging_rejected_count = 0
staging_skipped_count = 0
staging_issue_count = 0
imported_count = 25
inserted_count = 25
updated_count = 0
import_skipped_count = 0
validation_issue_count = 0
```

El check global del batch pasó correctamente con todos los checks en `true`.

---

## 28. Consulta útil para inspección operativa

Para ver reviews importadas por barrio y local:

```sql
SELECT
    d.official_name AS district,
    n.official_name AS neighborhood,
    p.display_name AS place_name,
    COUNT(r.review_id) AS review_count,
    ROUND(AVG(r.rating_value), 2) AS avg_rating,
    COUNT(*) FILTER (WHERE r.review_language = 'es') AS spanish_reviews
FROM hidden_gems.review r
JOIN hidden_gems.place p
    ON p.place_id = r.place_id
LEFT JOIN hidden_gems.place_neighborhood_assignment pna
    ON pna.place_id = p.place_id
   AND pna.is_current = TRUE
LEFT JOIN hidden_gems.neighborhood n
    ON n.neighborhood_id = pna.neighborhood_id
LEFT JOIN hidden_gems.district d
    ON d.district_id = pna.district_id
WHERE r.is_active = TRUE
  AND r.is_deleted_in_source = FALSE
  AND r.is_operational_review = TRUE
GROUP BY d.official_name, n.official_name, p.display_name
ORDER BY review_count DESC, avg_rating DESC;
```

Para obtener una muestra textual:

```sql
SELECT
    p.display_name AS place_name,
    n.official_name AS neighborhood,
    r.rating_value,
    r.review_language,
    r.review_created_at,
    LEFT(r.review_text_raw, 500) AS review_sample
FROM hidden_gems.review r
JOIN hidden_gems.place p
    ON p.place_id = r.place_id
LEFT JOIN hidden_gems.place_neighborhood_assignment pna
    ON pna.place_id = p.place_id
   AND pna.is_current = TRUE
LEFT JOIN hidden_gems.neighborhood n
    ON n.neighborhood_id = pna.neighborhood_id
WHERE r.is_active = TRUE
  AND r.is_deleted_in_source = FALSE
  AND r.is_operational_review = TRUE
ORDER BY r.review_created_at DESC NULLS LAST
LIMIT 20;
```

---

## 29. Reglas de coste y escalado

La vertical queda configurada para uso controlado.

Reglas actuales:

```text
1. No pedir reviews de todos los locales de golpe.
2. Ejecutar tandas pequeñas de 5 locales.
3. Usar FieldMask mínimo: id,displayName,reviews.
4. No usar FieldMask: *.
5. No añadir rating/userRatingCount salvo pruebas concretas.
6. No usar --allow-large-batch salvo validación previa.
7. Revisar Google Cloud tras cada tanda.
8. Priorizar locales sin reviews previas.
9. Permitir locales sin reviews salvo que se active --require-reviews.
10. Mantener raw auditable para cada Place Details.
```

Escalado recomendado:

```text
Tanda 1: 5 locales
Tanda 2: 5 locales
Tanda 3: 5 locales
Revisión de calidad
Después: ampliar solo si es necesario
```

---

## 30. Limitaciones actuales

La vertical tiene varias limitaciones asumidas:

* Google no devuelve necesariamente todas las reseñas históricas de un local;
* normalmente se obtiene un subconjunto limitado de reviews;
* no se usa paginación de reviews;
* no se scraping;
* no se solicitan reviews de locales no consolidados;
* esta vertical no ejecuta análisis NLP directamente;
* esta vertical no extrae platos directamente;
* esta vertical no calcula sentimiento por plato directamente;
* esta vertical no calcula ranking por barrio directamente.

Estas tareas ya existen como módulo IA prototipo en el repositorio, pero todavía no se han aplicado de forma productiva sobre Google Reviews de Sevilla.

Estas limitaciones son adecuadas para esta fase, cuyo objetivo es construir adquisición de comentarios locales de forma trazable y segura.

---

## 31. Relación con Yelp y NLP futuro

La estrategia final queda así:

```text
Google Places Reviews
→ comentarios reales de locales de Sevilla
→ vinculados a place/place_source_ref/barrio
→ útiles para app y corpus local NLP
```

```text
Yelp Open Dataset
→ corpus externo amplio
→ entrenamiento NLP posterior
→ no vinculado inicialmente a locales reales de Sevilla
```

Google Reviews se utilizará como corpus local y operativo.

Yelp ya se ha utilizado como corpus amplio para entrenar, validar e integrar un prototipo IA completo. El siguiente salto será adaptar ese flujo a las reviews locales de Google, especialmente por idioma, contexto de Sevilla y ranking por barrio.

---

## 32. Estado final de la vertical

La vertical Google Places Reviews queda en estado funcional validado y preparada para conectarse con la capa IA:

```text
[OK] Tabla review ampliada
[OK] Place Details implementado en GooglePlacesConnector
[OK] Raw details trazable
[OK] Modelo NormalizedReviewCandidate
[OK] Transformer de reviews
[OK] Check staging de reviews
[OK] Importador de reviews
[OK] Check post-importación
[OK] Orquestador individual completo
[OK] Batch de reviews
[OK] Check global de batch
[OK] Primera importación individual validada
[OK] Primer batch real validado: 5 locales → 25 reviews
[OK] Sin errores
[OK] Sin validation issues
[OK] Enlaces correctos con place/place_source_ref/barrio
[OK] Reviews locales preparadas como entrada futura de export_reviews_for_ai.py
```

La vertical queda preparada para enriquecer progresivamente locales ya consolidados con reseñas reales y para alimentar las futuras fases de NLP de Hidden Gems.

---

## 33. Fuera de alcance de esta vertical

No forma parte de esta vertical:

* entrenar modelos NLP dentro de esta vertical;
* extraer platos dentro de esta vertical;
* detectar sentimiento por plato dentro de esta vertical;
* calcular rankings por barrio dentro de esta vertical;
* integrar Yelp;
* construir dashboards;
* crear API pública;
* hacer scraping de reviews;
* obtener reviews de locales no importados previamente.

Estas tareas pertenecen a fases posteriores del proyecto.

---

## 34. Conclusión

La vertical Google Places Reviews completa una pieza fundamental del pipeline de Hidden Gems: la conexión entre locales reales de Sevilla y comentarios reales asociados a esos locales.

Con esta vertical, el sistema ya no solo dispone de locales geolocalizados y normalizados, sino también de texto gastronómico real vinculado a `place`, `place_source_ref`, barrio y distrito.

Esto deja preparada la base local para aplicar el módulo IA ya desarrollado como prototipo:

```text
reviews locales de Google
→ export_reviews_for_ai.py
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ señales place + dish
→ ranking de platos por barrio
```

La implementación mantiene el enfoque general del proyecto: adquisición controlada, raw trazable, staging validado, importación canónica, checks reproducibles y escalado gradual.


---

## 35. Relación con la integración IA en PostgreSQL

Tras la integración IA, Google Places Reviews pasa a ocupar un papel especialmente importante: es la fuente real local que deberá alimentar el sistema de detección de platos y ranking para Sevilla.

El prototipo IA ya está validado con Yelp y se ha materializado en PostgreSQL mediante:

```text
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Pero los candidatos actuales están marcados como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

Por tanto, no sustituyen todavía al ranking real de Sevilla. Para convertir Google Reviews en entrada de producción, el siguiente flujo será:

```text
hidden_gems.review
WHERE source_system = google_places
  AND is_operational_review = true
  AND is_training_eligible = true
→ export_reviews_for_ai.py
→ procesamiento IA
→ hidden_gem_candidate con ranking_scope = sevilla_neighborhood
```

Esta separación mantiene limpio el diseño: la vertical Google Reviews adquiere y persiste reseñas locales; la capa IA procesa esas reseñas después como una fase derivada y versionada.

---

## 36. Actualización posterior: recolección ampliada y uso en el piloto IA Sevilla

Después de la validación inicial descrita en este documento, la subvertical Google Places Reviews se utilizó para una recolección más amplia orientada al **piloto IA Sevilla**.

Esta actualización no elimina ni sustituye el flujo original; lo completa con el estado real posterior.

### 36.1. Recolección ampliada de reviews

La subvertical pasó de las primeras tandas controladas de 5 locales a una recolección más amplia sobre locales de Google Places ya consolidados.

Resultado aproximado de la base final de trabajo:

```text
Google Places locales: 800+
Google Places reviews: 4.000+
```

El flujo mantuvo las mismas garantías:

```text
Place Details controlado
→ raw_asset
→ staging reviews
→ checks de staging
→ importación en review
→ checks de batch
```

### 36.2. Límite importante de Google Reviews

La limitación ya documentada sigue siendo válida:

```text
Google no devuelve necesariamente todas las reseñas históricas de un local.
```

En la práctica, Places API devuelve un subconjunto limitado de reviews por local. Por eso el piloto Sevilla debe interpretarse como un prototipo basado en evidencia parcial, no como una lectura exhaustiva de todo el histórico de opiniones de Google.

### 36.3. Exportación para IA

Una vez cargadas las reviews locales, se creó y utilizó un flujo de exportación para IA:

```text
hidden_gems.review
WHERE source_system = google_places
  AND is_operational_review = true
  AND is_training_eligible = true
→ export_reviews_for_ai.py
→ reviews_for_ai_google_places.jsonl
```

Este artefacto sirvió como entrada para los notebooks locales de Sevilla.

### 36.4. Procesamiento IA ejecutado sobre reviews locales

Las reviews exportadas fueron procesadas mediante el flujo de notebooks del piloto Sevilla:

```text
12. Exploración corpus Sevilla
13. Detección de candidatos de platos
14. Normalización y catálogo local Sevilla
15. Sentimiento por mención
16. Agregación local-plato
17. Ranking Hidden Gems Sevilla piloto
```

El resultado demuestra que la subvertical no solo deja las reviews preparadas para NLP, sino que ya ha alimentado una primera ejecución completa del módulo IA local.

### 36.5. Resultados IA derivados de Google Places Reviews

El piloto IA Sevilla cargado en PostgreSQL dejó:

```text
dish = 190
dish_alias = 243
dish_mention = 2.979
dish_mention_sentiment = 2.979
dish_place_signal = 2.212
hidden_gem_candidate = 256
hidden_gem_selected = 150
```

También se validó que:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

### 36.6. Ranking generado

El ranking generado se conserva como piloto:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
```

La razón de `db_ranking_scope = other` es que la constraint actual de `hidden_gem_candidate.ranking_scope` no incluye todavía el valor literal `sevilla_pilot`. El valor real del alcance se conserva en la configuración JSON del candidato.

### 36.7. Nuevo papel de esta vertical dentro del proyecto

Antes de esta actualización, esta vertical se describía como preparación para futuras tareas de IA.

Actualmente su papel queda más claro:

```text
Google Places Reviews
→ fuente local real de texto gastronómico
→ entrada operativa para IA Sevilla
→ base del ranking sevilla_pilot
```

La vertical sigue sin ejecutar IA directamente. Su responsabilidad continúa siendo:

```text
adquirir reviews
validarlas
persistirlas
mantener trazabilidad
proteger integridad place/review/barrio
```

La capa IA se ejecuta después como proceso derivado y versionado.

### 36.8. Estado actualizado

Además del estado funcional inicial, ahora se añade:

```text
[OK] Recolección ampliada de Google Places Reviews
[OK] Base local con 4.000+ reviews aproximadas
[OK] Exportación reviews_for_ai_google_places.jsonl
[OK] Procesamiento IA Sevilla completado en notebooks 12–17
[OK] Señales local-plato generadas
[OK] Ranking sevilla_pilot generado
[OK] Resultados cargados en PostgreSQL
[OK] Check final de carga Sevilla sin errores ni warnings
[OK] Consulta demo del ranking Sevilla funcionando
```

### 36.9. Siguientes pasos tras el piloto

Después de esta fase, los siguientes pasos ya no son “aplicar por primera vez la IA”, sino:

```text
1. consolidar scripts demo finales;
2. crear dashboard piloto;
3. revisar manualmente falsos positivos;
4. analizar cobertura por barrio y plato;
5. valorar si merece la pena mejorar reglas o entrenar modelos específicos;
6. decidir cuándo una futura versión puede marcarse como producción.
```

