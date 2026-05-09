# Fuente de datos: Google Places

## 1. Propósito de la fuente

Google Places se incorpora al proyecto **Hidden Gems** como la fuente dinámica principal para descubrir, enriquecer y consolidar información de locales gastronómicos.

Dentro del pipeline, Google Places no sustituye al modelo canónico ni se utiliza como única verdad del sistema. Su función es actuar como una fuente externa de alta cobertura que permite:

* obtener locales gastronómicos actuales;
* enriquecer locales ya existentes procedentes de OSM / Overpass;
* añadir identificadores externos estables mediante Google Place ID;
* mejorar direcciones, coordenadas, categorías de origen y estado operativo;
* enriquecer locales ya consolidados con reseñas reales mediante Place Details;
* preparar una base más rica para aplicar el módulo IA ya prototipado: extracción de platos, sentimiento por mención, agregación de señales y ranking por barrio.

La fuente se integra siguiendo el mismo enfoque arquitectónico del resto del proyecto:

```text
fuente externa
→ conector
→ source_run
→ raw_asset
→ staging
→ normalización
→ deduplicación / validación
→ importación canónica
→ checks
→ artifacts
```

Google Places se utiliza mediante la API oficial, no mediante scraping.

---

## 2. Rol dentro de Hidden Gems

Google Places tiene un rol distinto al de las otras fuentes ya integradas:

| Fuente | Rol principal |
|---|---|
| Sevilla Geo | Geometría oficial de barrios y distritos |
| OSM / Overpass | Fuente abierta inicial de locales y POIs gastronómicos |
| Google Places | Fuente dinámica de descubrimiento, enriquecimiento y reseñas locales |
| Yelp Open Dataset | Fuente de apoyo IA/NLP y prototipo ya integrado |

En el modelo de datos, Google Places se representa principalmente mediante:

* `source_system`, con `source_code = 'google_places'`;
* `source_run`, para registrar cada ejecución;
* `raw_asset`, para conservar cada respuesta original de la API;
* `place_source_ref`, para enlazar cada `place` canónico con su Google Place ID;
* `review`, para almacenar reseñas reales de locales ya consolidados;
* `validation_issue`, para registrar incidencias de calidad o importación.

Google Places no escribe directamente de forma descontrolada sobre `place` ni sobre `review`. Primero pasa por raw, staging, validación y deduplicación/importación controlada.

---

## 3. Tipo de fuente

Google Places se clasifica como:

```text
source_type = api
auth_type = api_key
data_format_default = json
refresh_mode_default = incremental
supports_incremental = true
```

La fuente se registra en `hidden_gems.source_system` mediante el seed de fuentes:

```python
{
    "source_code": "google_places",
    "source_name": "Google Places",
    "source_type": "api",
    "description": "Fuente dinámica para enriquecimiento y consolidación de locales gastronómicos.",
    "base_url": "https://places.googleapis.com/v1",
    "auth_type": "api_key",
    "data_format_default": "json",
    "refresh_mode_default": "incremental",
    "supports_incremental": True,
    "is_active": True,
    "notes": "Fuente activada para la vertical Google Places con Places API New.",
}
```

No se crea un `source_system` adicional para reviews. Las reseñas de Google siguen perteneciendo a la misma fuente `google_places`, diferenciándose por el `purpose` del `source_run` y por los scripts/artefactos específicos de reviews.

---

## 4. Configuración externa necesaria

Antes de utilizar la fuente en el repositorio, es necesario preparar Google Cloud:

1. Crear un proyecto específico en Google Cloud.
2. Activar facturación asociada al proyecto.
3. Habilitar **Places API**.
4. Crear una API key.
5. Restringir la API key a Places API.
6. Configurar presupuestos y alertas.
7. Configurar cuotas bajas para desarrollo.
8. No subir nunca la clave al repositorio.

Aunque el uso inicial se ha planteado para mantenerse dentro de límites controlados, Google Places requiere facturación activa. Por tanto, se ha decidido trabajar con:

* pocas llamadas;
* `max_result_count` bajo;
* sin paginación inicial;
* sin `FieldMask: *`;
* sin Place Details masivo;
* reviews solo de locales ya consolidados y por tandas pequeñas;
* cuotas bajas y alertas activas.

---

## 5. Variables de entorno

La clave de Google Places se guarda en el archivo `.env` local:

```env
GOOGLE_MAPS_API_KEY=tu_clave_real
```

En `.env.example` solo debe aparecer la plantilla vacía:

```env
GOOGLE_MAPS_API_KEY=
```

La clave real no debe incluirse en:

* GitHub;
* documentación;
* scripts;
* notebooks;
* logs;
* capturas públicas.

La configuración se carga desde:

```text
src/config/settings.py
```

Con los campos:

```python
google_maps_api_key: str | None = None
google_places_base_url: str = "https://places.googleapis.com/v1"
```

---

## 6. Modos de uso de la fuente

Google Places se usa actualmente en dos modos controlados:

| Modo | Endpoint | Objetivo | Resultado |
|---|---|---|---|
| Text Search | `POST /places:searchText` | Descubrir y consolidar locales | `place`, `place_source_ref`, categorías, barrio |
| Place Details Reviews | `GET /places/{GOOGLE_PLACE_ID}` | Obtener reseñas de locales ya consolidados | `review` enlazada a `place` y `place_source_ref` |

El primer modo alimenta el modelo canónico de locales. El segundo modo solo se puede ejecutar sobre locales que ya tienen `place_source_ref` de Google Places.

---

## 7. Endpoint Text Search

La integración inicial utiliza **Text Search** de Places API New:

```text
POST https://places.googleapis.com/v1/places:searchText
```

El cuerpo básico de la petición es:

```json
{
  "textQuery": "restaurantes en Sevilla, España",
  "maxResultCount": 5,
  "languageCode": "es",
  "regionCode": "ES"
}
```

La llamada requiere cabeceras:

```text
Content-Type: application/json
X-Goog-Api-Key: <GOOGLE_MAPS_API_KEY>
X-Goog-FieldMask: <campos solicitados>
```

---

## 8. FieldMask de Text Search

Para controlar coste, tamaño de respuesta y estabilidad del pipeline, se utiliza un conjunto mínimo de campos:

```text
places.id
places.displayName
places.formattedAddress
places.location
places.types
places.businessStatus
places.googleMapsUri
```

Estos campos permiten construir candidatos con:

* identificador externo (`places.id`);
* nombre visible;
* dirección formateada;
* coordenadas;
* categorías/tipos de Google;
* estado operativo;
* URL de Google Maps.

No se utiliza:

```text
X-Goog-FieldMask: *
```

En esta vertical base no se solicitan inicialmente:

* reviews;
* rating;
* número de reseñas;
* teléfono;
* web;
* horarios;
* precio;
* atributos gastronómicos avanzados.

Las reseñas se trabajan en una subvertical específica mediante Place Details y solo sobre locales ya consolidados.

---

## 9. Estructura de respuesta Text Search esperada

La respuesta mínima esperada tiene esta forma:

```json
{
  "places": [
    {
      "id": "ChIJ...",
      "types": [
        "restaurant",
        "food",
        "point_of_interest",
        "establishment"
      ],
      "formattedAddress": "C/ Guadalquivir, 8, Casco Antiguo, 41002 Sevilla",
      "location": {
        "latitude": 37.399851399999996,
        "longitude": -5.9970805
      },
      "googleMapsUri": "https://maps.google.com/?cid=...",
      "businessStatus": "OPERATIONAL",
      "displayName": {
        "text": "Restaurante Casa Manolo León",
        "languageCode": "es"
      }
    }
  ]
}
```

El pipeline valida que:

* el payload sea un objeto JSON;
* exista la clave `places` o se trate como lista vacía;
* `places` sea una lista;
* cada local tenga, cuando sea posible, ID, nombre, dirección, coordenadas, tipos y estado.

---

## 10. Endpoint Place Details para reviews

La subvertical de reviews utiliza **Place Details**:

```text
GET https://places.googleapis.com/v1/places/{GOOGLE_PLACE_ID}
```

El `GOOGLE_PLACE_ID` procede de:

```text
hidden_gems.place_source_ref.source_record_id
```

Para esta fase se solicita un FieldMask mínimo:

```text
id,displayName,reviews
```

Opcionalmente, para pruebas controladas, puede añadirse:

```text
rating,userRatingCount
```

mediante la opción:

```powershell
--include-rating-summary
```

---

## 11. Estructura de respuesta Place Details Reviews

La respuesta real de Place Details para reviews tiene esta forma:

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

| Campo Google | Uso en Hidden Gems |
|---|---|
| `id` | `review.source_place_record_id` |
| `reviews[].name` | señal de identidad externa de la review |
| `reviews[].rating` | `review.rating_value` |
| `reviews[].text.text` | `review.review_text_raw` |
| `reviews[].text.languageCode` | `review.review_language` |
| `reviews[].originalText.text` | texto original en staging |
| `reviews[].authorAttribution.displayName` | `review.author_name_raw` |
| `reviews[].authorAttribution.uri` | `review.author_uri` |
| `reviews[].publishTime` | `review.review_created_at` |
| `reviews[].relativePublishTimeDescription` | `review.relative_publish_time_description` |
| `reviews[].googleMapsUri` | `review.source_review_url` |

---

## 12. Conector implementado

El conector se encuentra en:

```text
src/connectors/google_places.py
```

Clase principal:

```python
GooglePlacesConnector
```

Responsabilidades para Text Search:

* leer `GOOGLE_MAPS_API_KEY` desde settings;
* construir el endpoint de Google Places;
* construir `FieldMask`;
* ejecutar `Text Search`;
* aplicar reintentos básicos en errores recuperables;
* iniciar `source_run`;
* guardar respuesta raw como `raw_asset`;
* cerrar el run como completado o fallido;
* devolver resumen de resultados.

Responsabilidades para Place Details Reviews:

* recibir un Google Place ID;
* construir endpoint `GET /places/{place_id}`;
* solicitar `id,displayName,reviews`;
* guardar respuesta raw;
* registrar `source_run.request_summary.purpose = place_details_reviews`;
* devolver resumen de reviews recibidas.

El conector no transforma, no deduplica y no importa directamente a tablas canónicas.

---

## 13. Ingesta raw

Cada llamada a Google Places genera:

* un registro en `hidden_gems.source_run`;
* un fichero JSON en `data/raw/google_places/...`;
* un registro en `hidden_gems.raw_asset`;
* checksum SHA-256;
* tamaño del fichero;
* ruta relativa de almacenamiento;
* `query_name`;
* `request_signature_hash`.

Ejemplo de ruta de Text Search:

```text
data/raw/google_places/2026/05/05/google_places_20260505T105915Z_xxxxxxxx/20260505T105916Z_google_places_text_search_....json
```

Ejemplo de ruta de Place Details Reviews:

```text
data/raw/google_places/2026/05/05/google_places_20260505T150554Z_xxxxxxxx/20260505T150555Z_google_places_details_....json
```

Durante el desarrollo se detectó un problema de rutas largas en Windows. Para evitarlo, se acortó la generación de nombres en `RawStorage` y en los `query_name` generados por batch.

---

## 14. Comprobación raw Text Search

Script:

```text
scripts/check_google_places_raw.py
```

Uso:

```powershell
python -m scripts.check_google_places_raw `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Comprueba:

* existencia del `raw_asset` en base de datos;
* pertenencia a `source_code = 'google_places'`;
* existencia del fichero físico;
* coincidencia de tamaño;
* coincidencia de checksum;
* estructura JSON válida;
* lista `places`;
* campos mínimos por place;
* coherencia con `records_extracted_count`.

Genera artefacto opcional en:

```text
data/artifacts/google_places_raw_qa/
```

---

## 15. Transformación a candidato normalizado de local

Transformer:

```text
src/normalization/google_places_transformer.py
```

Script operativo:

```text
scripts/transform_google_places_candidates.py
```

Uso:

```powershell
python -m scripts.transform_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

La transformación convierte cada elemento de `places` en un `NormalizedPlaceCandidate`.

Campos principales mapeados:

| Campo Google | Campo candidato |
|---|---|
| `id` | `provenance.source_record_id` |
| `displayName.text` | `names.display_name` |
| `formattedAddress` | `address.source_address_raw` |
| `location.latitude` | `location.latitude` |
| `location.longitude` | `location.longitude` |
| `types` | `classification.source_categories_raw` |
| categoría prioritaria | `classification.source_primary_category_raw` |
| `businessStatus` | `provenance.source_status_raw` |
| `googleMapsUri` | `provenance.source_url` |

La salida se guarda en:

```text
data/staging/google_places/<raw_asset_id>/
```

Con ficheros:

```text
summary.json
accepted_candidates.json
needs_review_candidates.json
rejected_candidates.json
issues.json
```

---

## 16. Criterios de calidad en staging de locales

Un candidato se considera `accepted` cuando tiene:

* ID de origen;
* coordenadas;
* categoría;
* nombre utilizable;
* estado operativo aceptable.

Puede pasar a `needs_review` si:

* falta nombre;
* el estado no es `OPERATIONAL`;
* presenta avisos no bloqueantes.

Se marca como `rejected` si faltan campos críticos como:

* `source_record_id`;
* coordenadas;
* categoría.

Cada candidato recibe un `completeness_score`, calculado a partir de señales como:

* nombre;
* coordenadas;
* categoría;
* dirección;
* URL de Google Maps;
* estado operativo.

---

## 17. QA de staging de locales

Script:

```text
scripts/check_google_places_staging.py
```

Uso:

```powershell
python -m scripts.check_google_places_staging `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Comprueba:

* consistencia de contadores del `summary.json`;
* candidatos aceptados procedentes de `google_places`;
* ausencia de IDs duplicados en accepted;
* coordenadas presentes;
* categoría presente;
* distribución de tipos Google;
* estados de negocio;
* campos ausentes;
* duplicados potenciales.

Artefacto:

```text
data/artifacts/google_places_qa/
```

---

## 18. Deduplicación intra-fuente de locales

Deduplicador:

```text
src/normalization/google_places_deduplicator.py
```

Script:

```text
scripts/deduplicate_google_places_candidates.py
```

Uso:

```powershell
python -m scripts.deduplicate_google_places_candidates `
  --raw-asset-id <RAW_ASSET_ID>
```

Aunque Google Places proporciona un ID estable, la deduplicación sigue siendo necesaria porque diferentes consultas pueden devolver el mismo local.

Reglas principales:

1. Mismo Google Place ID.
2. Mismo nombre normalizado y coordenadas redondeadas.
3. Mismo nombre normalizado y distancia geográfica muy pequeña.

La salida se guarda en:

```text
data/staging/google_places/<raw_asset_id>/deduplication/
```

Con ficheros:

```text
dedup_summary.json
unique_candidates.json
duplicate_groups.json
pair_evidences.json
```

---

## 19. QA de deduplicación de locales

Script:

```text
scripts/check_google_places_deduplication.py
```

Uso:

```powershell
python -m scripts.check_google_places_deduplication `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

Comprueba:

* existencia de ficheros de deduplicación;
* coherencia de `output_count`;
* coherencia de grupos duplicados;
* coherencia de evidencias de pares;
* ausencia de `source_record_id` duplicados en `unique_candidates`;
* presencia de coordenadas;
* presencia de categoría;
* pertenencia a `google_places`.

Artefacto:

```text
data/artifacts/google_places_dedup_qa/
```

---

## 20. Importación canónica de locales

Importador:

```text
src/normalization/google_places_importer.py
```

Script:

```text
scripts/import_google_places_places.py
```

Uso:

```powershell
python -m scripts.import_google_places_places `
  --raw-asset-id <RAW_ASSET_ID>
```

La importación lee:

```text
data/staging/google_places/<raw_asset_id>/deduplication/unique_candidates.json
```

Y escribe en:

* `hidden_gems.place`;
* `hidden_gems.place_source_ref`;
* `hidden_gems.category`;
* `hidden_gems.place_category`;
* `hidden_gems.place_neighborhood_assignment`;
* `hidden_gems.validation_issue`.

La lógica de importación se apoya en:

```text
src/normalization/base_place_candidate_importer.py
```

Esto permite compartir lógica común entre OSM Overpass, Google Places y futuras fuentes.

---

## 21. Refactor del importador base

Durante la integración de Google Places se detectó que `GooglePlacesImporter` heredaba provisionalmente de `OSMOverpassImporter`, lo cual funcionaba pero era conceptualmente incorrecto.

Se refactorizó la lógica común a:

```text
BasePlaceCandidateImporter
```

Quedando la estructura:

```text
BasePlaceCandidateImporter
├── OSMOverpassImporter
└── GooglePlacesImporter
```

La clase base contiene:

* resolución de `source_system`;
* búsqueda de `place_source_ref` existente;
* matching básico por nombre normalizado y distancia;
* inserción/actualización de `place`;
* inserción/actualización de `place_source_ref`;
* creación/actualización de categoría;
* asignación de barrio por punto en polígono;
* registro de incidencias;
* actualización de contadores de `source_run`.

---

## 22. Check post-importación de locales

Script:

```text
scripts/check_google_places_import.py
```

Uso:

```powershell
python -m scripts.check_google_places_import `
  --source-run-id <SOURCE_RUN_ID> `
  --raw-asset-id <RAW_ASSET_ID>
```

Comprueba:

* número de `place_source_ref` de Google;
* número de places distintos;
* refs actuales;
* refs marcadas como eliminadas;
* geometría de origen presente;
* nombre de origen presente;
* métodos de matching;
* categorías principales;
* places sin categoría primaria;
* places sin barrio actual;
* incidencias generadas.

Checks esperados:

```text
has_google_place_source_refs = true
all_source_refs_current = true
no_deleted_source_refs = true
no_missing_source_geometry = true
no_missing_source_name = true
all_places_have_primary_category = true
all_places_have_current_neighborhood = true
no_validation_issues_for_filtered_scope = true
```

---

## 23. Flujo de reseñas Google Places

La fuente también soporta enriquecimiento de reseñas, pero solo para locales ya existentes.

Flujo:

```text
place_source_ref google_places
→ Google Place ID
→ Place Details
→ raw details
→ NormalizedReviewCandidate
→ check staging reviews
→ importación en hidden_gems.review
→ check import reviews
```

La tabla `review` fue ampliada con campos de trazabilidad y uso NLP:

```text
raw_asset_id
source_place_record_id
author_uri
relative_publish_time_description
source_payload_hash
is_operational_review
is_training_eligible
```

Una review de Google se guarda como:

```text
is_operational_review = true
is_training_eligible = true
```

Esto indica que:

* pertenece a un local real de Hidden Gems;
* puede utilizarse como corpus local para fases futuras de NLP.

---

## 24. Scripts de reviews

Scripts principales:

```text
scripts/run_google_places_place_details.py
scripts/transform_google_places_reviews.py
scripts/check_google_places_reviews_staging.py
scripts/import_google_places_reviews.py
scripts/check_google_places_reviews_import.py
scripts/load_google_places_reviews_pipeline.py
scripts/run_google_places_reviews_batch.py
scripts/check_google_places_reviews_batch.py
```

Artefactos principales:

```text
data/staging/google_places_reviews/<raw_asset_id>/summary.json
data/staging/google_places_reviews/<raw_asset_id>/accepted_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/rejected_reviews.json
data/staging/google_places_reviews/<raw_asset_id>/issues.json
data/staging/google_places_reviews/<raw_asset_id>/import/import_summary.json
data/staging/google_places_reviews/<raw_asset_id>/import/pipeline_summary.json
data/artifacts/google_places_reviews_batches/<batch_name>/batch_summary.json
data/artifacts/google_places_reviews_batches/<batch_name>/reviews_batch_check.json
```

La documentación completa de esta subvertical se mantiene en:

```text
docs/43_vertical_google_places_reviews.md
```

---

## 25. Orquestador individual de Text Search

Script:

```text
scripts/load_google_places_pipeline.py
```

Este script ejecuta el flujo completo de una consulta:

```text
Text Search
→ raw ingestion
→ check raw interno
→ transformación
→ check staging interno
→ deduplicación
→ check dedup interno
→ importación canónica
→ check import interno
→ pipeline_summary.json
```

Uso con importación:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_test `
  --max-result-count 5
```

Uso sin importación:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Triana, Sevilla" `
  --query-name gp_triana_restaurantes_dry `
  --max-result-count 5 `
  --skip-import
```

---

## 26. Configuración de consultas por barrio

Se creó configuración externa en:

```text
src/config/google_places_query_plan.yaml
```

Esta configuración permite separar:

* plantillas de búsqueda;
* valores por defecto;
* alias de barrios;
* nombres oficiales frente a nombres de búsqueda.

Ejemplo:

```yaml
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
  EL TARDON-EL CARMEN: "El Tardón, Triana"
  BARRIO LEON: "Barrio León"
  ARENAL: "El Arenal"
  SANTA CRUZ: "Santa Cruz"
  LOS REMEDIOS: "Los Remedios"
```

El campo oficial `neighborhood_name` se conserva para trazabilidad, pero la consulta enviada a Google utiliza `search_name`.

Ejemplo:

```text
neighborhood_name = TRIANA CASCO ANTIGUO
search_name = Triana
text_query = restaurantes en Triana, Sevilla
```

La asignación final al barrio no depende de ese texto, sino de coordenadas y `point_in_polygon`.

---

## 27. Batch por barrios Text Search

Script:

```text
scripts/run_google_places_neighborhood_batch.py
```

Ejecuta varias consultas individuales usando el orquestador `load_google_places_pipeline.py` como unidad operativa.

Permite:

* seleccionar barrios concretos;
* seleccionar distritos completos;
* limitar número de barrios;
* limitar consultas por barrio;
* limitar resultados por consulta;
* ejecutar en modo `dry-run`;
* ejecutar con o sin importación;
* guardar plan, resultados y resumen;
* controlar errores;
* pausar entre llamadas.

Uso en dry-run:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_dry_run_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --dry-run
```

Uso sin importación:

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

Uso con importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-errors 10
```

Uso por distrito:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_distrito_triana_import_v1 `
  --district Triana `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-total-queries 10
```

---

## 28. Comentario operativo del batch de Text Search

El script `run_google_places_neighborhood_batch.py` incluye un bloque de comentarios con ejemplos de uso:

```text
MODO 1: dry-run
MODO 2: ejecución sin importación
MODO 3: ejecución con importación
MODO 4: piloto de cinco barrios
MODO 5: ejecución por distrito
MODO 6: plantilla personalizada
```

Reglas recomendadas:

```text
1. Empezar siempre con --dry-run.
2. Probar después con --skip-import.
3. Importar solo cuando el batch sin importación sea correcto.
4. Mantener max-result-count bajo.
5. No usar FieldMask amplio ni pedir reviews en esta vertical base.
6. No lanzar toda Sevilla de golpe.
7. Escalar por tandas pequeñas de barrios o distritos.
8. Revisar Google Cloud usage tras tandas reales.
```

---

## 29. Check global de batch Text Search

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

* que el plan no tenga `query_name` duplicados;
* que el número de consultas planificadas coincida;
* que el número de consultas ejecutadas coincida;
* que los éxitos y errores coincidan;
* que no haya errores salvo que se permitan explícitamente;
* que los totales del resumen coincidan con los resultados individuales;
* que cada éxito tenga `pipeline_output`;
* que cada éxito tenga `source_run_id`;
* que cada éxito tenga `raw_asset_id`;
* que cada éxito tenga resumen de transformación;
* que cada éxito tenga resumen de deduplicación;
* que cada éxito tenga resumen de importación cuando corresponda;
* que los checks de importación pasen;
* que no haya `source_run_id` duplicados;
* que no haya `raw_asset_id` duplicados.

Artefacto:

```text
data/artifacts/google_places_batches/<batch_name>/batch_check.json
```

---

## 30. Pilotos ejecutados y validados

Durante la implementación se validaron progresivamente:

### Prueba ID-only

Se validó la API con campos mínimos:

```text
places.id
places.name
```

Resultado: `STATUS 200` y varios Google Place IDs.

### Prueba útil individual

Se validó una consulta de restaurantes en Sevilla con:

```text
places.id
places.displayName
places.formattedAddress
places.location
places.types
places.businessStatus
places.googleMapsUri
```

Resultado: respuesta correcta con locales reales.

### Pipeline individual

Se ejecutó:

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_pipeline_test `
  --max-result-count 3
```

Resultado: flujo completo correcto.

### Batch de dos barrios

Barrios:

```text
TRIANA CASCO ANTIGUO
NERVION
```

Resultado final:

```text
planned_query_count = 4
executed_query_count = 4
success_count = 4
error_count = 0
raw_place_count = 20
accepted_count = 20
imported_count = 20
validation_issue_count = 0
```

### Piloto de cinco barrios

Barrios:

```text
TRIANA CASCO ANTIGUO
NERVION
SANTA CRUZ
ARENAL
LOS REMEDIOS
```

Configuración:

```text
2 queries por barrio
5 resultados por query
10 llamadas máximas
sin paginación
sin Details
sin reviews en Text Search
```

Resultado: ejecución y check global correctos.

### Primera tanda de reviews

Después de consolidar locales, se validó la subvertical de reviews:

```text
5 locales
25 reviews
0 errores
0 validation issues
reviews enlazadas a place/place_source_ref/barrio
```

La documentación completa está en:

```text
docs/43_vertical_google_places_reviews.md
```

---

## 31. Decisiones de seguridad y coste

Para esta fuente se han fijado las siguientes reglas:

```text
1. No usar FieldMask: *.
2. No pedir reviews en la fase de adquisición base con Text Search.
3. No pedir Place Details de forma masiva.
4. No activar paginación inicialmente.
5. Mantener max_result_count bajo.
6. Ejecutar batches pequeños.
7. Usar cuotas bajas en Google Cloud.
8. Revisar uso tras cada tanda.
9. No subir nunca la API key.
10. Mantener trazabilidad raw de cada respuesta.
11. Pedir reviews solo para locales ya consolidados.
12. Ejecutar reviews por tandas pequeñas de locales.
```

El escalado se realizará por tandas pequeñas, nunca descargando toda Sevilla de golpe.

---

## 32. Limitaciones actuales

La fuente Google Places actual tiene estas limitaciones intencionadas:

* Text Search no usa Nearby Search;
* no usa grid/círculos;
* no pagina resultados;
* no solicita teléfonos ni webs;
* no realiza enriquecimiento masivo de Details;
* las reviews se solicitan solo para locales ya importados;
* Google no devuelve necesariamente todas las reseñas históricas de un local;
* no analiza platos todavía;
* no ejecuta NLP todavía.

Estas limitaciones son aceptadas porque esta fase busca construir una adquisición segura, trazable y reproducible.

---

## 33. Relación con el módulo IA integrado

Google Places y Google Places Reviews son la vía natural para pasar del prototipo Yelp al caso real de Sevilla.

El módulo IA ya validado con Yelp permite el flujo:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

En Google Reviews, la diferencia es que las reseñas sí están enlazadas a locales reales de Sevilla:

```text
Google Review
→ review
→ place
→ place_neighborhood_assignment
→ neighborhood / district
```

Por tanto, el siguiente paso natural será exportar reviews reales desde `hidden_gems.review` mediante un script específico, analizar volumen/idioma y aplicar una versión adaptada del flujo IA.

El ranking productivo esperado no será `yelp_prototype`, sino:

```text
ranking_scope = sevilla_neighborhood
is_production_ready = true
neighborhood_id IS NOT NULL
```

---

## 34. Próximas mejoras posibles

No forman parte de esta fase, pero quedan identificadas:

* incorporar Nearby Search con estrategia espacial controlada;
* añadir paginación limitada para Text Search si es necesario;
* crear enriquecimiento selectivo con Place Details para más campos;
* solicitar rating y número de reseñas solo para locales consolidados;
* ampliar tandas de reviews de forma controlada;
* crear análisis de cobertura por barrio;
* mejorar alias de barrios según resultados reales;
* integrar métricas BI para calidad de fuente;
* crear `export_reviews_for_ai.py` para generar corpus IA desde `hidden_gems.review`;
* analizar idioma y volumen de Google Reviews locales;
* adaptar la detección de platos y sentimiento a español/multilingüe;
* calcular señales y ranking por barrio sobre datos reales de Sevilla.

---

## 35. Estado final de la fuente

La fuente Google Places queda integrada en estado operativo inicial:

```text
[OK] API key configurada localmente
[OK] source_system activado
[OK] conector implementado
[OK] Text Search operativo
[OK] raw trazable
[OK] check raw
[OK] transformación a NormalizedPlaceCandidate
[OK] check staging
[OK] deduplicación intra-fuente
[OK] check deduplicación
[OK] importación canónica
[OK] check post-importación
[OK] orquestador individual
[OK] batch por barrios
[OK] aliases/search_name por barrio
[OK] check global de batch
[OK] piloto de cinco barrios validado
[OK] Place Details Reviews operativo
[OK] reviews importadas en hidden_gems.review
[OK] batch de reviews validado
```

La fuente queda preparada para seguir alimentando el modelo canónico de Hidden Gems de forma incremental y controlada, y para aportar reseñas locales reales a la aplicación futura del módulo IA sobre Sevilla.

