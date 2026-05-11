# 00 - AI Integration Index

## Propósito

Este bloque documenta la integración real del módulo de IA de **Hidden Gems** dentro del repositorio y de la base de datos PostgreSQL/PostGIS.

El bloque `docs/10_ai_module/` describe el desarrollo experimental de IA en notebooks, especialmente sobre Yelp:

```text
reviews de Yelp
→ detección de platos
→ normalización
→ sentimiento por mención
→ agregación
→ ranking Hidden Gems v1
```

Este bloque `docs/11_ai_integration/` documenta el paso posterior:

```text
artefactos IA
→ PostgreSQL
→ tablas versionadas
→ vistas SQL
→ scripts de consulta
→ base lista para explotación y demo
```

Actualmente cubre dos integraciones relacionadas:

1. **Yelp prototype**, usado para validar la arquitectura IA de extremo a extremo.
2. **Sevilla pilot**, usado para cargar y consultar el primer ranking piloto local generado desde Google Places Reviews.

La IA se mantiene como capa derivada: no sustituye al modelo canónico de datos, sino que se apoya sobre `place`, `review`, `neighborhood` y `district`.

---

## Documentos de este bloque

| Archivo | Contenido |
|---|---|
| `00_ai_integration_index.md` | Índice y visión general del bloque de integración. |
| `01_ai_database_schema.md` | Diseño físico de la capa IA en PostgreSQL. |
| `02_ai_loaders_and_checks.md` | Scripts de carga y verificación de artefactos IA. |
| `03_ai_query_layer.md` | Vistas SQL y scripts de demo para consultar rankings y señales IA. |
| `04_current_status_and_next_steps.md` | Estado actual validado, limitaciones y siguientes fases. |

El detalle específico del piloto local de Sevilla se documenta en:

```text
docs/12_sevilla_ai_pilot/
```

---

## Archivos implementados para integración IA general / Yelp

```text
db/ddl/07_ai_module.sql
db/ddl/08_ai_views.sql

scripts/load_ai_dish_catalog.py
scripts/check_ai_dish_catalog.py
scripts/check_ai_downstream_import_readiness.py
scripts/load_yelp_ai_core_reviews.py
scripts/load_ai_mentions_and_sentiment.py
scripts/load_ai_signals_and_ranking.py
scripts/check_ai_ranking_loaded.py
scripts/query_ai_ranking_demo.py
```

---

## Archivos implementados para integración Sevilla pilot

```text
scripts/export_reviews_for_ai.py
scripts/check_ai_review_export.py
scripts/load_sevilla_ai_pilot_outputs.py
scripts/check_sevilla_ai_pilot_loaded.py
scripts/query_sevilla_hidden_gems_demo.py
```

Notebooks asociados:

```text
notebooks/12_sevilla_reviews_exploration.ipynb
notebooks/13_sevilla_dish_detection.ipynb
notebooks/14_sevilla_dish_normalization_and_catalog.ipynb
notebooks/15_sevilla_mention_sentiment.ipynb
notebooks/16_sevilla_place_dish_signal_aggregation.ipynb
notebooks/17_sevilla_hidden_gems_ranking_pilot.ipynb
```

---

## Flujo general de integración Yelp prototype

```text
1. Crear schema IA
   db/ddl/07_ai_module.sql

2. Cargar catálogo de platos
   dish_catalog_seed_v2.csv
   dish_aliases_seed_v2.csv
   → dish
   → dish_alias

3. Cargar núcleo Yelp para prototipo IA
   food_businesses.jsonl
   food_reviews.jsonl
   → place
   → place_source_ref
   → review

4. Cargar menciones y sentimiento
   dish_mentions_with_sentiment_hybrid_v1.jsonl
   → dish_mention
   → dish_mention_sentiment

5. Cargar señales y ranking
   dish_business_ranking_candidates_v1.csv
   hidden_gems_selected_candidates_v1.csv
   → dish_place_signal
   → hidden_gem_candidate

6. Crear vistas de consulta
   db/ddl/08_ai_views.sql

7. Validar y consultar resultados
   check_ai_ranking_loaded.py
   query_ai_ranking_demo.py
```

---

## Flujo general de integración Sevilla pilot

```text
1. Recolectar locales y reviews Google Places Sevilla
   → place
   → place_source_ref
   → review

2. Exportar reviews para IA
   export_reviews_for_ai.py
   → reviews_for_ai_google_places.jsonl

3. Ejecutar notebooks 12-17
   reviews locales
   → candidatos de platos
   → catálogo local
   → sentimiento por mención
   → señales place+dish
   → ranking sevilla_pilot

4. Cargar outputs del piloto
   load_sevilla_ai_pilot_outputs.py
   → dish
   → dish_alias
   → dish_mention
   → dish_mention_sentiment
   → dish_place_signal
   → hidden_gem_candidate

5. Validar carga
   check_sevilla_ai_pilot_loaded.py

6. Consultar demo
   query_sevilla_hidden_gems_demo.py
```

---

## Estado validado: Yelp prototype

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |

Estado:

```text
ranking_scope = yelp_prototype
is_production_ready = false
ready_for_querying_ai_ranking = true
```

---

## Estado validado: Sevilla pilot

| Elemento | Registros |
|---|---:|
| `dish` local Sevilla | 190 |
| `dish_alias` Sevilla | 243 |
| `dish_mention` Sevilla | 2.979 |
| `dish_mention_sentiment` Sevilla | 2.979 |
| `dish_place_signal` Sevilla | 2.212 |
| `hidden_gem_candidate` Sevilla | 256 |
| candidatos seleccionados | 150 |

Cobertura:

```text
selected_places = 122
selected_dishes = 38
selected_neighborhoods = 55
selected_districts = 11
```

Estado:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
ready_for_sevilla_pilot_queries = true
```

El uso de `db_ranking_scope = other` se debe a la restricción actual del DDL, que todavía no incluye `sevilla_pilot` como valor nativo de `ranking_scope`.

---

## Decisiones principales cerradas

1. La IA se integra como **capa derivada**, no como modificación directa de `place`.
2. El eje del sistema es `place_id`, no IDs externos como `business_id` o Google Place ID.
3. `review` es la entrada oficial para detección de menciones.
4. `dish` y `dish_alias` forman el catálogo canónico de platos.
5. `dish_mention` almacena apariciones concretas de platos en reviews.
6. `dish_mention_sentiment` separa el sentimiento para permitir recalculados futuros.
7. `dish_place_signal` almacena agregaciones por local y plato.
8. `hidden_gem_candidate` almacena el ranking final.
9. Todo queda versionado mediante `ai_model_version` y `ai_pipeline_run`.
10. Yelp queda como `yelp_prototype`.
11. Sevilla queda como `sevilla_pilot`, no producción.
12. Ningún resultado IA debe cargarse si queda huérfano respecto a `review`, `place` o `dish`.

---

## Relación con el objetivo final de Hidden Gems

La integración actual demuestra que Hidden Gems puede pasar de:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
→ vistas SQL / demo
```

El objetivo final seguirá siendo producir rankings fiables por barrio en Sevilla. El piloto `sevilla_pilot` es el primer resultado local real, pero todavía no se marca como producción.
