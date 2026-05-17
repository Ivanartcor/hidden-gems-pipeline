# Fuente de datos: Google Places

## 1. Propósito de la fuente

Google Places se incorpora a **Hidden Gems** como la fuente dinámica principal para descubrir, enriquecer y consolidar locales gastronómicos.

Su función es:

- obtener locales gastronómicos actuales;
- enriquecer locales existentes procedentes de OSM / Overpass;
- añadir identificadores externos mediante Google Place ID;
- mejorar direcciones, coordenadas, categorías y estado operativo;
- obtener reseñas reales mediante Place Details;
- alimentar el piloto IA local de Sevilla.

Google Places se integra mediante API oficial, no mediante scraping.

Flujo general:

```text
Google Places API
→ source_run
→ raw_asset
→ staging
→ normalización
→ deduplicación
→ importación canónica
→ checks
→ reviews
→ export IA
→ sevilla_pilot
```

---

## 2. Rol dentro de Hidden Gems

| Fuente | Rol |
|---|---|
| Sevilla Geo | Geometría oficial de barrios/distritos |
| OSM / Overpass | Base abierta inicial de locales |
| Google Places | Descubrimiento, enriquecimiento y reviews locales |
| Yelp Open Dataset | Corpus externo/prototipo IA |

En el modelo, Google Places se representa mediante:

- `source_system`, con `source_code = google_places`;
- `source_run`;
- `raw_asset`;
- `place_source_ref`;
- `review`;
- `validation_issue`.

Google Places no escribe de forma directa ni descontrolada. Pasa por raw, staging, validación, deduplicación e importación.

---

## 3. Tipo de fuente

```text
source_type = api
auth_type = api_key
data_format_default = json
refresh_mode_default = incremental
supports_incremental = true
```

No se crea una fuente distinta para reviews. Las reviews pertenecen a `google_places`, diferenciadas por el propósito del run y los scripts usados.

---

## 4. Configuración externa necesaria

Requisitos:

1. Proyecto en Google Cloud.
2. Facturación activa.
3. Places API habilitada.
4. API key creada.
5. Restricción de la key a Places API.
6. Presupuestos y alertas.
7. Cuotas bajas para desarrollo.
8. Clave fuera de Git.

Reglas de coste/seguridad:

- no usar `FieldMask: *`;
- usar `max_result_count` bajo;
- no paginar masivamente;
- pedir reviews solo de locales consolidados;
- ejecutar batches pequeños;
- revisar consumo en Google Cloud.

---

## 5. Variables de entorno

`.env`:

```env
GOOGLE_MAPS_API_KEY=tu_clave_real
```

`.env.example`:

```env
GOOGLE_MAPS_API_KEY=
```

La clave real no debe incluirse en Git, documentación, scripts, notebooks, logs o capturas.

---

## 6. Modos de uso

| Modo | Endpoint | Objetivo | Resultado |
|---|---|---|---|
| Text Search | `POST /places:searchText` | Descubrir locales | `place`, `place_source_ref`, categoría, barrio |
| Place Details Reviews | `GET /places/{GOOGLE_PLACE_ID}` | Obtener reviews | `review` enlazada a `place` |

---

## 7. Text Search

Endpoint:

```text
POST https://places.googleapis.com/v1/places:searchText
```

Body típico:

```json
{
  "textQuery": "restaurantes en Sevilla, España",
  "maxResultCount": 5,
  "languageCode": "es",
  "regionCode": "ES"
}
```

FieldMask usado:

```text
places.id
places.displayName
places.formattedAddress
places.location
places.types
places.businessStatus
places.googleMapsUri
```

Campos no solicitados en Text Search base:

- reviews;
- teléfono;
- web;
- horarios;
- precio;
- atributos avanzados.

---

## 8. Place Details para reviews

Endpoint:

```text
GET https://places.googleapis.com/v1/places/{GOOGLE_PLACE_ID}
```

FieldMask mínimo:

```text
id,displayName,reviews
```

Opcionalmente:

```text
rating,userRatingCount
```

Las reviews se solicitan solo cuando existe:

```text
place_source_ref.source_record_id = GOOGLE_PLACE_ID
```

---

## 9. Mapeo de reviews

| Campo Google | Campo Hidden Gems |
|---|---|
| `id` | `review.source_place_record_id` |
| `reviews[].name` | identidad externa de review |
| `reviews[].rating` | `review.rating_value` |
| `reviews[].text.text` | `review.review_text_raw` |
| `reviews[].text.languageCode` | `review.review_language` |
| `reviews[].authorAttribution.displayName` | `review.author_name_raw` |
| `reviews[].authorAttribution.uri` | `review.author_uri` |
| `reviews[].publishTime` | `review.review_created_at` |
| `reviews[].googleMapsUri` | `review.source_review_url` |

Una review Google importada se marca como:

```text
is_operational_review = true
is_training_eligible = true
```

---

## 10. Componentes implementados

Conector:

```text
src/connectors/google_places.py
```

Transformación:

```text
src/normalization/google_places_transformer.py
```

Deduplicación:

```text
src/normalization/google_places_deduplicator.py
```

Importación:

```text
src/normalization/google_places_importer.py
src/normalization/base_place_candidate_importer.py
```

Configuración de búsquedas:

```text
src/config/google_places_query_plan.yaml
```

---

## 11. Scripts principales de locales

- `scripts/load_google_places_pipeline.py`;
- `scripts/check_google_places_raw.py`;
- `scripts/transform_google_places_candidates.py`;
- `scripts/check_google_places_staging.py`;
- `scripts/deduplicate_google_places_candidates.py`;
- `scripts/check_google_places_deduplication.py`;
- `scripts/import_google_places_places.py`;
- `scripts/check_google_places_import.py`;
- `scripts/run_google_places_neighborhood_batch.py`;
- `scripts/check_google_places_batch.py`.

---

## 12. Scripts principales de reviews

- `scripts/run_google_places_place_details.py`;
- `scripts/transform_google_places_reviews.py`;
- `scripts/check_google_places_reviews_staging.py`;
- `scripts/import_google_places_reviews.py`;
- `scripts/check_google_places_reviews_import.py`;
- `scripts/load_google_places_reviews_pipeline.py`;
- `scripts/run_google_places_reviews_batch.py`;
- `scripts/check_google_places_reviews_batch.py`.

---

## 13. Batch por barrios

Script:

```text
scripts/run_google_places_neighborhood_batch.py
```

Permite:

- seleccionar barrios;
- seleccionar distritos;
- limitar consultas;
- limitar resultados;
- ejecutar dry-run;
- ejecutar con o sin importación;
- controlar errores;
- pausar entre llamadas;
- guardar plan, resultados y resumen.

Ejemplo:

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

## 14. Batch de reviews

Script:

```text
scripts.run_google_places_reviews_batch
```

Ejemplo:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_ai_pilot_03_import `
  --limit-places 100 `
  --max-errors 10
```

Check:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_ai_pilot_03_import `
  --save-artifact
```

---

## 15. Resultados operativos obtenidos

Durante la fase de piloto serio se consolidó una muestra suficiente de Google Places Sevilla:

```text
800+ locales Google Places
4.000+ reviews Google Places
0 locales pendientes sin review en el lote final usado
```

La exportación para IA generó un corpus local aproximado de:

```text
4.110 reviews
831 locales
96 barrios
11 distritos
```

Esto permitió pasar de fuente operativa a procesamiento IA real sobre Sevilla.

---

## 16. Relación con el piloto IA Sevilla

Google Places Reviews alimentó el flujo:

```text
review Google Sevilla
→ export_reviews_for_ai
→ 12_sevilla_reviews_exploration
→ 13_sevilla_dish_candidate_detection
→ 14_sevilla_dish_normalization_and_catalog
→ 15_sevilla_mention_sentiment
→ 16_sevilla_place_dish_signal_aggregation
→ 17_sevilla_hidden_gems_ranking_pilot
→ load_sevilla_ai_pilot_outputs
→ check_sevilla_ai_pilot_loaded
→ query_sevilla_hidden_gems_demo
```

Resultados del piloto:

```text
menciones ranking-ready = 2.979
señales local-plato = 2.212
candidatos ranking = 256
candidatos seleccionados = 150
locales seleccionados = 122
platos seleccionados = 38
barrios seleccionados = 55
distritos seleccionados = 11
ready_for_sevilla_pilot_queries = true
```

---

## 17. Estado de ranking

El piloto se considera local y real, pero todavía no productivo:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
```

Esto se debe a que el DDL actual no tiene `sevilla_pilot` como valor nativo de `ranking_scope`.

---

## 18. Limitaciones actuales

- Google no devuelve todas las reviews históricas.
- El número de reviews por local es limitado.
- Las reviews pueden ser breves.
- El corpus tiene sesgo positivo.
- El sentimiento por mención usa enfoque híbrido, no un modelo final entrenado en español.
- El ranking está marcado como piloto, no producción.
- La API tiene coste y cuota.

---

## 19. Estado final de la fuente

Estado actual:

```text
[OK] API key configurada localmente
[OK] source_system activado
[OK] Text Search operativo
[OK] raw trazable
[OK] staging y deduplicación
[OK] importación canónica
[OK] batch por barrios/distritos
[OK] Place Details Reviews operativo
[OK] reviews importadas en review
[OK] export reviews para IA
[OK] piloto IA Sevilla generado
[OK] piloto cargado en PostgreSQL
[OK] check final sin errores
[OK] query demo funcional
```

---

## 20. Próximas mejoras

- ampliar cobertura de reviews si es necesario;
- mejorar análisis de cobertura por barrio;
- revisar manualmente top candidatos;
- ajustar ranking para dashboard;
- añadir `sevilla_pilot` / `sevilla_neighborhood` al constraint de `ranking_scope`;
- crear dashboard Streamlit;
- evaluar si merece la pena entrenar modelos específicos en español.

---

## 21. Conclusión

Google Places ya no es solo una fuente preparada para alimentar IA futura.

Actualmente ha alimentado un piloto IA real sobre Sevilla, con datos operativos de Google Reviews, ranking `sevilla_pilot`, carga en PostgreSQL, checks correctos y demo de consulta.

La fuente queda como eje operativo principal para seguir evolucionando Hidden Gems hacia dashboard, API y una futura versión de ranking validada para producción.


---

## 21. Actualización: Google Places como base de Sevilla IA v2

Tras el piloto `sevilla_pilot`, Google Places Reviews ha pasado a ser también la base de la fase **Sevilla IA v2**.

La diferencia entre la fase piloto y la fase v2 es que en v2 ya no se usa solo una cadena híbrida/reglas, sino modelos entrenados y aplicados localmente:

```text
Google Places Reviews Sevilla
→ Hybrid + NER v2
→ normalización con reranker BETO
→ sentimiento por mención ABSA BETO
→ señales place-dish v2
→ ranking Hidden Gems Sevilla v2
→ dashboard_v2
```

Resultados finales relacionados con Google Places Reviews y Sevilla IA v2:

| Métrica | Valor |
|---|---:|
| Candidatos puntuados v2 | 2.335 |
| Candidatos seleccionados v2 | 268 |
| Locales seleccionados v2 | 198 |
| Platos seleccionados v2 | 40 |
| Barrios seleccionados v2 | 67 |
| Distritos seleccionados v2 | 11 |
| Menciones seleccionadas v2 | 651 |
| Reviews seleccionadas v2 | 627 |

El ranking v2 sigue estando marcado como no producción:

```text
is_production_ready = false
```

pero ya es el resultado principal para la entrega académica y se explota mediante el dashboard Sevilla IA v2.

---

## 22. Artefactos derivados actuales

A partir de Google Places Reviews se han generado, entre otros, los siguientes artefactos relevantes:

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/
data/artifacts/ai/sevilla/model_inference/ranking_v2/
data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison/
data/artifacts/ai/sevilla/dashboard_v2/
```

Estos artefactos no son fuente primaria, sino resultados derivados. Aun así, son esenciales para la explotación del valor obtenido a partir de Google Places Reviews.

---

## 23. Limitaciones actualizadas

Las limitaciones de Google Places se mantienen:

- coste y cuotas;
- dependencia de API externa;
- número limitado de reviews recuperables;
- sesgo positivo frecuente en reseñas;
- textos breves o poco descriptivos;
- necesidad de controlar FieldMask y batches.

La diferencia es que la fase v2 mitiga parcialmente algunas limitaciones analíticas mediante modelos específicos:

- NER para detectar menciones de platos;
- reranker para normalizar menciones a catálogo;
- ABSA para estimar sentimiento por plato, no solo por reseña completa;
- evidence tier y quality tier para evitar sobreafirmar señales débiles.

---

## 24. Estado final actualizado de Google Places

Estado actual para la entrega:

```text
[OK] API key configurada localmente
[OK] source_system activado
[OK] Text Search operativo
[OK] raw trazable
[OK] staging y deduplicación
[OK] importación canónica
[OK] batch por barrios/distritos
[OK] Place Details Reviews operativo
[OK] reviews importadas en review
[OK] export reviews para IA
[OK] piloto IA Sevilla v1 generado
[OK] ranking Sevilla IA v2 generado
[OK] comparación v1 vs v2 generada
[OK] dashboard_v2 exportado
[OK] dashboard Streamlit Sevilla IA v2 funcional
```

Google Places queda como la fuente operativa principal de la entrega académica.
