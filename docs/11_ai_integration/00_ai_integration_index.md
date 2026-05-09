# 00 - AI Integration Index

## Propósito

Este bloque documenta la integración real del módulo de IA de **Hidden Gems** dentro del repositorio y de la base de datos PostgreSQL/PostGIS.

La documentación anterior del bloque `docs/10_ai_module/` describe el desarrollo experimental de IA en notebooks:

```text
reviews de Yelp
→ detección de platos
→ normalización
→ sentimiento por mención
→ agregación
→ ranking Hidden Gems v1
```

Este nuevo bloque documenta el paso posterior:

```text
artefactos IA
→ PostgreSQL
→ tablas versionadas
→ vistas SQL
→ scripts de consulta
→ base lista para explotación y demo
```

La integración mantiene la decisión arquitectónica principal del proyecto: la IA no sustituye al modelo canónico de datos, sino que se apoya sobre él.

---

## Documentos de este bloque

| Archivo | Contenido |
|---|---|
| `00_ai_integration_index.md` | Índice y visión general del bloque de integración. |
| `01_ai_database_schema.md` | Diseño físico de la capa IA en PostgreSQL: tablas, relaciones, responsabilidades y decisiones. |
| `02_ai_loaders_and_checks.md` | Scripts de carga y verificación utilizados para llevar los artefactos IA a la base de datos. |
| `03_ai_query_layer.md` | Vistas SQL y script de demo para consultar el ranking y las señales IA desde PostgreSQL. |
| `04_current_status_and_next_steps.md` | Estado actual validado, limitaciones y siguientes fases recomendadas. |

---

## Archivos implementados en el repositorio

Durante la integración se han añadido o utilizado los siguientes archivos:

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

## Flujo general de integración

El flujo completado queda organizado así:

```text
1. Crear schema IA
   db/ddl/07_ai_module.sql

2. Cargar catálogo de platos
   dish_catalog_seed_v2.csv
   dish_aliases_seed_v2.csv
   → dish
   → dish_alias

3. Comprobar readiness inicial
   check_ai_downstream_import_readiness.py

4. Cargar núcleo Yelp para prototipo IA
   food_businesses.jsonl
   food_reviews.jsonl
   → place
   → place_source_ref
   → review

5. Cargar menciones y sentimiento
   dish_mentions_with_sentiment_hybrid_v1.jsonl
   → dish_mention
   → dish_mention_sentiment

6. Cargar señales y ranking
   dish_business_ranking_candidates_v1.csv
   hidden_gems_selected_candidates_v1.csv
   → dish_place_signal
   → hidden_gem_candidate

7. Crear vistas de consulta
   db/ddl/08_ai_views.sql

8. Validar y consultar resultados
   check_ai_ranking_loaded.py
   query_ai_ranking_demo.py
```

---

## Estado validado tras la integración

La integración final queda validada con estos conteos:

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |
| `place` | 7.230 |
| `review` | 80.037 |

Además, el check final confirma:

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

## Decisiones principales cerradas

1. La IA se integra como **capa derivada**, no como modificación directa de `place`.
2. El eje del sistema es `place_id`, no `business_id` de Yelp.
3. `review` es la entrada oficial para detección de menciones.
4. `dish` y `dish_alias` forman el catálogo canónico de platos.
5. `dish_mention` almacena apariciones concretas de platos en reviews.
6. `dish_mention_sentiment` separa el sentimiento de la mención para permitir recalculados futuros.
7. `dish_place_signal` almacena agregaciones por local y plato.
8. `hidden_gem_candidate` almacena el ranking final.
9. Todo queda versionado mediante `ai_model_version` y `ai_pipeline_run`.
10. El ranking actual se marca como `yelp_prototype` y `is_production_ready = false`.

---

## Relación con el objetivo final de Hidden Gems

La integración actual valida el sistema completo sobre Yelp como corpus de prototipo.

El objetivo final del producto seguirá siendo Sevilla:

```text
Google Places / OSM / Sevilla Geo
→ place + review + neighborhood
→ IA de platos
→ señales por local y plato
→ ranking por barrio
```

Por tanto, el estado actual no es todavía el ranking productivo de Sevilla, pero sí demuestra que la cadena completa de IA puede persistirse, consultarse y auditarse desde PostgreSQL.
