# 26. Catálogo de entidades: calidad

## 1. Introducción

Este documento describe el bloque encargado del **control de calidad, validación e incidencias** dentro del modelo de datos de Hidden Gems.

Un pipeline de datos no solo debe almacenar información. También debe registrar y comprobar los problemas encontrados durante:

- adquisición;
- integración;
- validación;
- enriquecimiento geográfico;
- procesamiento IA;
- carga de artefactos;
- ranking;
- consulta analítica.

La entidad principal de calidad estructurada es:

- `validation_issue`.

Además, el proyecto cuenta con scripts de check que generan reportes JSON para validar:

- verticales de fuente;
- catálogo de platos;
- mapeo de artefactos IA;
- carga de menciones;
- carga de sentimiento;
- carga de señales;
- carga de ranking;
- vistas y consultas demo.

---

## 2. Visión general del bloque de calidad

Bloque básico:

```text
source_run
└── validation_issue

raw_asset
└── validation_issue
```

Relación polimórfica:

```text
entity_type + entity_id
```

Esto permite registrar incidencias sobre:

- fuentes;
- runs;
- raw assets;
- locales;
- referencias fuente;
- reviews;
- categorías;
- geografía;
- entidades IA;
- señales;
- candidatos de ranking.

---

## 3. Decisiones principales

### 3.1. Registrar incidencias estructuradas

Las incidencias relevantes no deben quedar únicamente en logs.

`validation_issue` permite explotación posterior, reporting y mejora continua.

### 3.2. Vincular incidencias a ejecuciones

Toda incidencia procedente de adquisición debe poder relacionarse con un `source_run`.

En procesos IA, la relación se conserva mediante:

- `entity_type`;
- `entity_id`;
- `issue_code`;
- reportes JSON;
- `ai_pipeline_run.metrics_json`.

### 3.3. Permitir relación polimórfica

Una incidencia puede afectar a muchas entidades distintas. Por eso se usa `entity_type + entity_id` en lugar de una FK por cada tabla.

### 3.4. No cargar resultados IA huérfanos

Regla clave:

- no cargar menciones sin `review`, `place` o `dish`;
- no cargar sentimientos sin `dish_mention`;
- no cargar señales sin `place` y `dish`;
- no cargar ranking sin `dish_place_signal`.

### 3.5. Diferenciar prototipo, piloto y producción

Estados actuales:

```text
yelp_prototype
→ prototipo IA amplio
→ is_production_ready = false
```

```text
sevilla_pilot
→ piloto local real sobre Google Reviews Sevilla
→ db_ranking_scope = other
→ artifact_ranking_scope = sevilla_pilot
→ is_production_ready = false
```

Una futura versión productiva deberá tener criterios más estrictos:

- scope nativo local;
- revisión manual;
- cobertura suficiente;
- `is_production_ready = true` solo para candidatos validados;
- trazabilidad completa de fuente y artefactos.

---

## 4. Entidad `validation_issue`

### Propósito

Representa una incidencia de calidad, validación, consistencia, matching, geografía, esquema o procesamiento.

### Campos principales

| Campo | Descripción |
|---|---|
| `validation_issue_id` | Identificador interno |
| `source_run_id` | Ejecución donde se detectó |
| `raw_asset_id` | Asset relacionado si aplica |
| `entity_type` | Tipo de entidad afectada |
| `entity_id` | ID de entidad afectada |
| `issue_code` | Código técnico |
| `issue_type` | Tipo general |
| `severity` | Severidad |
| `message` | Mensaje legible |
| `field_name` | Campo afectado |
| `received_value` | Valor recibido |
| `expected_rule` | Regla esperada |
| `status` | Estado |
| `resolution_notes` | Resolución |
| `detected_at` | Fecha de detección |
| `resolved_at` | Fecha de resolución |

### Tipos de incidencia

- `validation`;
- `quality`;
- `matching`;
- `geospatial`;
- `schema`.

### Severidades

- `info`;
- `warning`;
- `error`;
- `critical`.

### Estados

- `open`;
- `resolved`;
- `ignored`.

---

## 5. Entity types permitidos

Base:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `place`;
- `place_source_ref`;
- `review`;
- `category`;
- `place_category`;
- `district`;
- `neighborhood`;
- `place_neighborhood_assignment`.

IA:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

---

## 6. Ejemplos de `issue_code`

Generales:

| Código | Descripción |
|---|---|
| `missing_coordinates` | Falta coordenada |
| `invalid_geometry` | Geometría inválida |
| `empty_name` | Nombre vacío |
| `duplicate_candidate` | Posible duplicado |
| `unmapped_category` | Categoría no mapeada |
| `missing_required_field` | Campo obligatorio ausente |
| `review_text_empty` | Reseña sin texto útil |
| `neighborhood_not_found` | Barrio no resuelto |
| `schema_mismatch` | Estructura inesperada |

IA:

| Código | Descripción |
|---|---|
| `dish_alias_duplicate` | Alias duplicado o ambiguo |
| `dish_without_alias` | Plato sin alias |
| `missing_review_mapping` | Mención sin mapping a `review` |
| `missing_place_mapping` | Mención/señal sin mapping a `place` |
| `missing_dish_mapping` | Mención/señal sin mapping a `dish` |
| `invalid_sentiment_label` | Sentimiento inválido |
| `invalid_ranking_score` | Score fuera de rango |
| `orphan_dish_mention` | Mención huérfana |
| `orphan_hidden_gem_candidate` | Candidato sin señal válida |
| `production_candidate_without_neighborhood` | Producción sin barrio |
| `wrong_artifact_scope` | Scope de artefacto incorrecto |
| `wrong_db_ranking_scope` | Scope DB incorrecto |

---

## 7. Calidad por vertical

### 7.1. Sevilla Geo

Incidencias posibles:

- geometría inválida;
- barrio sin distrito;
- nombre oficial vacío;
- error al descargar/leer GeoJSON.

### 7.2. OSM / Overpass

Incidencias posibles:

- POI sin nombre;
- POI sin coordenadas;
- categoría no mapeada;
- posible duplicado;
- local fuera de geometría oficial;
- JSON Overpass incompleto.

### 7.3. Google Places

Incidencias posibles:

- respuesta sin `places`;
- local sin coordenadas;
- local sin nombre;
- categoría Google no mapeada;
- duplicado potencial;
- error de API;
- local sin barrio.

### 7.4. Google Places Reviews

Incidencias posibles:

- local sin `place_source_ref` válida;
- respuesta sin reviews;
- review sin texto útil;
- rating fuera de rango;
- idioma inesperado;
- payload duplicado;
- review no elegible para IA.

### 7.5. Yelp Open Dataset

Incidencias posibles:

- negocio sin coordenadas;
- review sin texto mínimo;
- `business_id` sin mapping;
- `review_id` sin mapping;
- problema JSON Lines;
- registros no elegibles para corpus.

---

## 8. Calidad específica de la capa IA

### 8.1. Catálogo de platos

Checks:

- número total de platos;
- número total de aliases;
- platos sin alias;
- aliases duplicados;
- aliases compartidos;
- idioma;
- elegibilidad para ranking.

Scripts:

```powershell
python -m scripts.check_ai_dish_catalog
```

Para Sevilla, el catálogo local validado contiene:

```text
dish_catalog = 190
dish_alias = 243
```

---

### 8.2. Preparación downstream

Antes de cargar IA se comprueba que los artefactos puedan mapearse contra la base:

```text
source review id → review interno
source place id  → place_source_ref → place
dish name        → dish
```

Scripts generales:

```powershell
python -m scripts.check_ai_downstream_import_readiness
```

---

### 8.3. Carga de menciones y sentimiento

Checks principales:

- JSONL válido;
- campos obligatorios;
- mapeo a `review`;
- mapeo a `place`;
- mapeo a `dish`;
- sentimiento válido;
- ausencia de huérfanos.

Resultados Sevilla:

```text
dish_mention = 2.979
dish_mention_sentiment = 2.979
missing_review_mapping = 0
missing_place_mapping = 0
missing_dish_mapping = 0
invalid_sentiment = 0
```

---

### 8.4. Carga de señales y ranking

Checks principales:

- mapeo `place_id`;
- mapeo `dish_id`;
- existencia de señal para cada ranking;
- score 0–100;
- tiers válidos;
- barrio y distrito presentes en seleccionados;
- producción desactivada en piloto.

Resultados Sevilla:

```text
dish_place_signal = 2.212
hidden_gem_candidate = 256
hidden_gem_selected = 150
ranking_without_scoped_signal = 0
ranking_score_out_of_range = 0
selected_without_neighborhood = 0
selected_without_district = 0
selected_marked_production_ready = 0
```

---

### 8.5. Check final del piloto Sevilla

Script:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded
```

Resultado final:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

Checks destacados:

```text
required_tables_exist = true
required_model_versions_exist = true
required_ai_runs_exist = true
all_ai_runs_completed = true
no_orphan_mentions_review = true
no_orphan_mentions_place = true
no_orphan_mentions_dish = true
no_mentions_without_sentiment = true
no_ranking_without_scoped_signal = true
score_in_0_100 = true
selected_consistency_ok = true
selected_not_production_ready = true
selected_have_neighborhood = true
selected_have_district = true
selected_have_explanation = true
artifact_scope_ok = true
db_ranking_scope_ok = true
selected_global_ranks_unique = true
```

---

## 9. Reporting de calidad

`validation_issue` y los reportes JSON permiten construir métricas como:

- incidencias por fuente;
- incidencias por run;
- incidencias abiertas por severidad;
- registros rechazados;
- problemas geográficos;
- categorías sin mapear;
- cobertura de catálogo IA;
- fiabilidad de sentimiento;
- candidatos por tier;
- rankings por scope;
- candidatos seleccionados por distrito/barrio/plato.

---

## 10. Decisiones generales

1. Las incidencias relevantes se estructuran en base de datos.
2. Los checks generan reportes JSON reproducibles.
3. La capa IA no debe cargarse si hay mapeos incompletos.
4. Yelp se valida como prototipo IA.
5. Sevilla pilot se valida como piloto local real, pero no producción.
6. `is_production_ready = true` solo debe usarse tras validación posterior.
7. La calidad debe ser medible y consultable, no solo revisada manualmente.

---

## 11. Conclusión

El bloque de calidad permite que Hidden Gems controle y documente problemas del pipeline y de la capa IA.

La validación actual confirma que tanto el prototipo Yelp como el piloto Sevilla pueden cargarse y consultarse sin huérfanos críticos.

El siguiente paso natural es utilizar estos reportes como base para dashboard, revisión manual de candidatos y futuras mejoras del ranking.
