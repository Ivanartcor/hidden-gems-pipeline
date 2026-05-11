# 01 - AI Database Schema

## Objetivo

Este documento describe el diseño de base de datos utilizado para integrar el módulo IA de Hidden Gems en PostgreSQL/PostGIS.

La implementación principal está en:

```text
db/ddl/07_ai_module.sql
```

Y se apoya en el schema existente:

```text
hidden_gems
```

La decisión fue mantener un único schema para todo el proyecto, evitando crear un schema separado como `hidden_gems_ai`. Esto facilita las relaciones directas con entidades existentes como `place`, `review`, `source_run`, `raw_asset`, `district` y `neighborhood`.

---

## Principio de diseño

La capa IA se modela como una capa derivada sobre el modelo canónico.

No se añaden columnas de IA directamente a `place` como:

```text
best_dish
hidden_gem_score
main_dish
```

En su lugar, se crean tablas específicas:

```text
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Esto permite:

- mantener limpio el core del pipeline;
- recalcular resultados IA sin modificar entidades canónicas;
- versionar modelos y ejecuciones;
- conservar histórico de rankings;
- auditar cada salida;
- cargar prototipos y pilotos sin confundirlos con producción.

---

## Entidades principales

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Todas las tablas usan `UUID` como clave primaria.

---

# 1. `ai_model_version`

## Responsabilidad

Registra modelos, reglas o métodos IA versionados.

Puede representar:

- modelos transformer;
- reglas de normalización;
- métodos híbridos de sentimiento;
- agregadores de señales;
- fórmulas de ranking;
- procesos manuales versionados.

Ejemplos:

```text
dish_ner_transformer_v1
dish_normalization_rule_based_v2
mention_sentiment_hybrid_v1_1
signal_aggregation_v1
hidden_gems_ranking_v1
sevilla_dish_detection_hybrid_v1
sevilla_hidden_gems_ranking_pilot_v1
```

---

# 2. `ai_pipeline_run`

## Responsabilidad

Registra ejecuciones concretas de procesos IA.

No sustituye a `source_run`:

```text
source_run = adquisición desde una fuente externa
ai_pipeline_run = procesamiento IA derivado
```

Ejemplos:

```text
ai_run_yelp_mention_sentiment_hybrid_v1
ai_run_yelp_hidden_gems_ranking_v1
ai_run_sevilla_dish_detection_v1
ai_run_sevilla_hidden_gems_ranking_pilot_v1
```

Los campos `input_artifacts_json`, `output_artifacts_json`, `config_json` y `metrics_json` permiten reconstruir qué se ejecutó y con qué resultados.

---

# 3. `dish`

## Responsabilidad

Catálogo canónico de platos.

Representa conceptos de plato, no menciones concretas.

Ejemplos Yelp:

```text
pizza
burger
sushi
tacos
fried chicken
```

Ejemplos Sevilla:

```text
croqueta
ensaladilla
carrillada
solomillo al whisky
tarta de queso
churros
bacalao
```

La base usa:

```text
dish_id = UUID
```

Los IDs externos de notebooks o semillas se conservan como metadata/código de origen cuando procede, pero no sustituyen a la PK real.

---

# 4. `dish_alias`

## Responsabilidad

Guarda variantes textuales asociadas a un plato canónico.

Ejemplo:

```text
dish = croqueta
aliases:
- croqueta
- croquetas
- croquetas caseras
```

Es una tabla clave para normalizar menciones nuevas y para adaptar el sistema a español/localismos.

---

# 5. `dish_mention`

## Responsabilidad

Representa cada aparición concreta de un plato dentro de una review.

Relaciones:

| Relación | Significado |
|---|---|
| `review_id → review` | Review donde aparece la mención. |
| `place_id → place` | Local asociado a la review. |
| `dish_id → dish` | Plato normalizado. |
| `dish_alias_id → dish_alias` | Alias usado cuando aplica. |
| `ai_pipeline_run_id → ai_pipeline_run` | Ejecución que generó la mención. |
| `model_version_id → ai_model_version` | Modelo/regla utilizada. |

Aunque `place_id` podría obtenerse mediante `review`, se almacena también para acelerar agregaciones y checks.

Regla lógica:

```text
dish_mention.place_id debe coincidir con review.place_id
```

---

# 6. `dish_mention_sentiment`

## Responsabilidad

Guarda el sentimiento calculado para una mención concreta.

Se separa de `dish_mention` para poder recalcular sentimiento sin duplicar la mención.

Valores principales:

```text
positive
neutral
negative
```

Además puede almacenar:

- score;
- confianza;
- método;
- contexto usado;
- flags de ambigüedad;
- términos positivos/negativos detectados.

---

# 7. `dish_place_signal`

## Responsabilidad

Guarda señales agregadas por local y plato.

Conceptualmente:

```text
place + dish → señales agregadas
```

Incluye:

- `mention_count`;
- `review_count`;
- ratios positivos/neutros/negativos;
- sentimiento ponderado;
- confianza media;
- evidencias locales;
- tiers de calidad;
- flags de ruido;
- elegibilidad para ranking.

Esta tabla es el puente entre menciones individuales y ranking final.

---

# 8. `hidden_gem_candidate`

## Responsabilidad

Guarda candidatos finales del ranking Hidden Gems.

Incluye:

| Campo | Significado |
|---|---|
| `hidden_gem_score` | Score final. |
| `hidden_gem_tier` | Tier del candidato. |
| `hidden_gem_rank` | Ranking global. |
| `hidden_gem_selected_rank` | Ranking entre seleccionados. |
| `ranking_explanation` | Explicación textual del candidato. |
| `ranking_scope` | Alcance del ranking en DB. |
| `is_production_ready` | Indica si se considera producción. |
| `neighborhood_id` | Barrio asociado cuando existe. |
| `district_id` | Distrito asociado cuando existe. |

Estados actuales:

```text
Yelp prototype:
ranking_scope = yelp_prototype
is_production_ready = false
```

```text
Sevilla pilot:
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
is_production_ready = false
```

El uso de `other` para Sevilla se debe a la constraint actual del DDL. El valor lógico `sevilla_pilot` se conserva en `ranking_config_json`.

---

## Relaciones principales

```text
source_system
  ↓
source_run
  ↓
raw_asset
  ↓
place_source_ref
  ↓
place
  ↓
review
  ↓
dish_mention
  ↓
dish_mention_sentiment
  ↓
dish_place_signal
  ↓
hidden_gem_candidate
```

En paralelo:

```text
dish
  ↓
dish_alias
  ↓
dish_mention
```

---

## Integridad validada

Yelp prototype:

```text
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

Sevilla pilot:

```text
no_missing_review_mapping = true
no_missing_place_mapping = true
no_missing_dish_mapping = true
no_invalid_sentiment = true
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

---

## Conteos actuales relevantes

### Yelp prototype

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
```

### Sevilla pilot

```text
dish local = 190
dish_alias local = 243
dish_mention = 2.979
dish_mention_sentiment = 2.979
dish_place_signal = 2.212
hidden_gem_candidate = 256
selected_hidden_gem_candidates = 150
selected_neighborhoods = 55
selected_districts = 11
```

---

## Ampliación de `validation_issue`

La capa IA puede aparecer en incidencias de validación:

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Ejemplos:

```text
dish_alias ambiguo
dish_mention sin normalizar
sentimiento dudoso
candidato con evidencia insuficiente
ranking inconsistente
```

---

## Decisiones de diseño cerradas

1. Schema único `hidden_gems`.
2. UUID como PK en tablas IA.
3. `place_id` como eje del sistema.
4. IDs externos quedan en `place_source_ref` o metadata.
5. `dish` se separa de `dish_mention`.
6. `dish_mention_sentiment` se separa de `dish_mention`.
7. `dish_place_signal` se separa de `hidden_gem_candidate`.
8. Todos los resultados se versionan mediante modelos y runs.
9. Yelp queda como prototipo.
10. Sevilla queda como piloto local, no producción.
11. La capa queda preparada para añadir `sevilla_pilot` como scope nativo en una futura migración.
