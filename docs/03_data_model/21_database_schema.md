# 21. Esquema de base de datos

## 1. Introducción

El esquema de base de datos de Hidden Gems está implementado sobre **PostgreSQL + PostGIS**.

La elección de PostgreSQL responde a la necesidad de contar con una base relacional sólida, con integridad referencial, constraints, índices avanzados y consultas analíticas. PostGIS se utiliza para trabajar con geometrías oficiales, coordenadas de locales y asignación espacial de puntos a barrios.

El esquema principal se denomina:

```sql
hidden_gems
```

Dentro de este esquema se agrupan las tablas del core canónico, geografía, trazabilidad, calidad, reseñas, capa IA y vistas de consulta.

---

## 2. Organización de scripts SQL

| Script | Contenido principal |
|---|---|
| `00_foundation.sql` | Extensiones, schema, tipos enumerados y funciones comunes |
| `01_governance.sql` | Fuentes, ejecuciones y artefactos raw |
| `02_geo_reference.sql` | Distritos y barrios oficiales |
| `03_core_places.sql` | Locales, referencias fuente y reseñas |
| `04_classification_and_geo_assignment.sql` | Categorías y asignación geográfica |
| `05_validation.sql` | Incidencias de validación y calidad |
| `06_review_enrichment.sql` | Enriquecimiento de `review` para trazabilidad y NLP |
| `07_ai_module.sql` | Tablas persistentes del módulo IA y ranking |
| `08_ai_views.sql` | Vistas de consulta para explotación IA |

---

## 3. Extensiones utilizadas

### 3.1. PostGIS

Permite almacenar puntos de locales, polígonos/multipolígonos de barrios y distritos, centroides, índices espaciales y operaciones geográficas.

### 3.2. pgcrypto

Se utiliza para UUIDs y hashes técnicos.

### 3.3. pg_trgm

Se utiliza para búsquedas y comparaciones textuales aproximadas sobre nombres de locales, referencias fuente, platos y aliases.

---

## 4. Convenciones generales

- nombres en `snake_case`;
- claves primarias UUID;
- timestamps `created_at` y `updated_at`;
- función común `set_updated_at()`;
- booleanos de estado (`is_active`, `is_current`, `is_selected`, `is_production_ready`, etc.);
- constraints de rango para ratings, scores, ratios, coordenadas y confianzas;
- índices B-tree, GIST y GIN según el tipo de consulta.

---

## 5. Tipos enumerados y checks

El modelo define enums para la parte estable:

- `source_type_enum`;
- `auth_type_enum`;
- `refresh_mode_enum`;
- `run_type_enum`;
- `run_trigger_enum`;
- `run_status_enum`;
- `asset_type_enum`;
- `retention_class_enum`;
- `assignment_method_enum`;
- `validation_issue_type_enum`;
- `validation_severity_enum`;
- `validation_status_enum`.

Para la capa IA se utilizan principalmente `VARCHAR + CHECK`, porque los métodos, tiers, scopes y versiones todavía evolucionan.

### Nota actual sobre `ranking_scope`

El DDL actual no incluye todavía `sevilla_pilot` como valor nativo de `hidden_gem_candidate.ranking_scope`. Por ese motivo, el piloto Sevilla se ha cargado con:

```text
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
```

y conserva el scope real dentro de `ranking_config_json` / configuración de ranking.

Esto permite cargar y consultar el piloto sin romper constraints, pero queda como mejora futura añadir `sevilla_pilot` y/o `sevilla_neighborhood` al constraint.

---

## 6. Gobierno y trazabilidad

Tablas principales:

- `source_system`;
- `source_run`;
- `raw_asset`.

Estas tablas registran fuentes, ejecuciones y artefactos raw.

Decisiones clave:

- toda fuente debe estar registrada;
- toda ejecución relevante debe generar `source_run`;
- todo raw importante debe registrarse como `raw_asset`;
- el raw se considera inmutable;
- los procesos IA se trazan aparte mediante `ai_pipeline_run`.

---

## 7. Geografía

Tablas:

- `district`;
- `neighborhood`.

La geometría se almacena con SRID 4326 y PostGIS. También se derivan centroides y áreas.

El barrio es la unidad principal de análisis territorial para Hidden Gems.

---

## 8. Núcleo de negocio

Tablas:

- `place`;
- `place_source_ref`;
- `review`.

### 8.1. `place`

Representa el local canónico interno. No contiene IDs externos ni barrio directo.

### 8.2. `place_source_ref`

Representa la aparición del local en una fuente concreta.

Constraint clave:

```sql
UNIQUE (source_system_id, source_entity_type, source_record_id)
```

### 8.3. `review`

Representa una reseña textual individual. Las reseñas son dependientes de fuente y no se fusionan automáticamente.

---

## 9. Enriquecimiento de reviews para IA

`06_review_enrichment.sql` refuerza `review` con campos útiles para NLP y trazabilidad:

- `raw_asset_id`;
- `source_place_record_id`;
- `source_payload_hash`;
- `is_operational_review`;
- `is_training_eligible`;
- campos de autor, URL y metadatos cuando aplica.

Esto permite diferenciar:

```text
Google Reviews operativas Sevilla
Yelp reviews prototipo/corpus
reviews elegibles para entrenamiento o inferencia IA
```

---

## 10. Clasificación y asignación geográfica

Tablas:

- `category`;
- `place_category`;
- `place_neighborhood_assignment`.

`place_neighborhood_assignment` mantiene la relación vigente local-barrio y evita guardar el barrio como columna fija en `place`.

---

## 11. Calidad

Tabla:

- `validation_issue`.

Permite registrar incidencias sobre entidades core y entidades IA mediante `entity_type` + `entity_id`.

La capa IA amplía los tipos admitidos para incluir:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

---

## 12. Capa IA y ranking

Creada en `07_ai_module.sql`.

Tablas:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

### 12.1. `ai_model_version`

Registra modelos, reglas, métodos híbridos, agregadores y rankings.

Ejemplos:

- `dish_ner_transformer_v1`;
- `sevilla_dish_detection_hybrid_v1`;
- `sevilla_mention_sentiment_hybrid_v1`;
- `sevilla_signal_aggregation_v1`;
- `sevilla_hidden_gems_ranking_pilot_v1`.

### 12.2. `ai_pipeline_run`

Registra ejecuciones concretas IA.

Ejemplos actuales del piloto Sevilla:

- `ai_run_sevilla_dish_catalog_v1`;
- `ai_run_sevilla_dish_mentions_v1`;
- `ai_run_sevilla_mention_sentiment_v1`;
- `ai_run_sevilla_signal_aggregation_v1`;
- `ai_run_sevilla_hidden_gems_ranking_pilot_v1`.

### 12.3. `dish` y `dish_alias`

Catálogo de platos y variantes textuales.

### 12.4. `dish_mention`

Mención concreta de un plato dentro de una review. Se relaciona con `review`, `place`, `dish`, `ai_pipeline_run` y `ai_model_version`.

### 12.5. `dish_mention_sentiment`

Sentimiento calculado para una mención concreta.

### 12.6. `dish_place_signal`

Agregación por local + plato:

```text
place + dish → señales agregadas
```

Incluye conteos, ratios, sentimiento, tiers de evidencia y calidad.

### 12.7. `hidden_gem_candidate`

Resultado del ranking Hidden Gems.

Incluye score final, tier, explicación, componentes del score, penalizaciones, scope y estado de producción.

---

## 13. Vistas de consulta IA

Creadas en `08_ai_views.sql`.

Vistas principales:

- `vw_ai_pipeline_run_summary`;
- `vw_ai_dish_place_signals`;
- `vw_ai_hidden_gem_candidate_detail`;
- `vw_ai_hidden_gems_yelp_top`;
- `vw_ai_hidden_gems_place_summary`;
- `vw_ai_hidden_gems_dish_summary`;
- `vw_ai_hidden_gems_city_summary`;
- `vw_ai_dish_mentions_with_sentiment`.

Las vistas se usan tanto para el prototipo Yelp como para el piloto Sevilla.

Para Sevilla, la vista principal operativa de consulta es:

```text
vw_ai_hidden_gem_candidate_detail
```

filtrando por:

```text
artifact_ranking_scope = sevilla_pilot
```

cuando el script demo lo expone desde configuración/ranking JSON.

---

## 14. Índices principales

El schema incorpora:

- índices relacionales sobre claves foráneas;
- índices espaciales GIST sobre geometrías;
- índices GIN trigram sobre nombres y aliases;
- full text search básico sobre reseñas;
- índices de ranking por scope, selección y score;
- índices por `place + dish` para señales.

---

## 15. Triggers y funciones

Incluye triggers para:

- `updated_at`;
- campos geográficos derivados;
- sincronización latitud/longitud con geometría;
- longitud/hash de reviews;
- auditoría temporal de tablas IA.

---

## 16. Constraints de calidad

El schema protege datos mínimos:

- nombres no vacíos;
- coordenadas válidas;
- ratings entre 0 y 5;
- confianzas entre 0 y 1;
- scores entre 0 y 100;
- contadores no negativos;
- geometrías válidas;
- etiquetas de sentimiento controladas;
- tiers y scopes de ranking controlados.

---

## 17. Relación con verticales implementadas

### 17.1. Sevilla Geo

Alimenta:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `district`;
- `neighborhood`;
- `validation_issue`.

### 17.2. OSM / Overpass

Alimenta:

- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`.

### 17.3. Google Places

Alimenta:

- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`.

### 17.4. Google Places Reviews

Alimenta:

- `review`.

En el piloto Sevilla, estas reviews son la entrada real para:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

### 17.5. Yelp Open Dataset

Alimenta un prototipo externo:

```text
Yelp business/review
→ place/place_source_ref/review
→ capa IA
→ ranking_scope = yelp_prototype
```

---

## 18. Estado actual del schema

### 18.1. IA Yelp validada

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |

### 18.2. IA Sevilla pilot validada

| Entidad | Registros |
|---|---:|
| `dish_catalog` | 190 |
| `dish_alias` | 243 |
| `dish_mention` | 2.979 |
| `dish_mention_sentiment` | 2.979 |
| `dish_place_signal` | 2.212 |
| `hidden_gem_candidate` | 256 |
| `hidden_gem_selected` | 150 |

Checks finales del piloto:

```text
required_tables_exist = true
required_model_versions_exist = true
required_ai_runs_exist = true
all_ai_runs_completed = true
score_in_0_100 = true
selected_have_neighborhood = true
selected_have_district = true
selected_have_explanation = true
selected_global_ranks_unique = true
errors = []
warnings = []
ready_for_sevilla_pilot_queries = true
```

---

## 19. Decisiones pendientes

La principal decisión futura de schema es si se amplía el constraint de `hidden_gem_candidate.ranking_scope` para aceptar valores explícitos como:

```text
sevilla_pilot
sevilla_neighborhood
```

Actualmente no es imprescindible, porque el piloto queda trazado mediante `ranking_config_json`, pero sería deseable antes de una fase más cercana a producto.

---

## 20. Conclusión

El esquema de base de datos ya soporta adquisición, geografía, reseñas, calidad, IA y ranking.

El proyecto ha pasado de una integración IA prototipo sobre Yelp a un piloto real sobre Google Places Reviews Sevilla, cargado y validado en PostgreSQL.

La siguiente evolución del schema no requiere rediseño, sino ajustes puntuales de constraints, vistas o índices para soportar mejor scopes locales, dashboard y futuras APIs.
