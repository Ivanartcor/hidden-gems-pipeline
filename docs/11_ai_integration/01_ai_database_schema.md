# 01 - AI Database Schema

## Objetivo

Este documento describe el diseño de base de datos utilizado para integrar el módulo IA de Hidden Gems en PostgreSQL/PostGIS.

La implementación se encuentra en:

```text
db/ddl/07_ai_module.sql
```

Y se apoya en el schema existente:

```text
hidden_gems
```

La decisión fue mantener un único schema para todo el proyecto, evitando crear un schema separado como `hidden_gems_ai`. Esto facilita las relaciones directas con entidades ya existentes como `place`, `review`, `source_run`, `raw_asset`, `district` y `neighborhood`.

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
- auditar cada salida.

---

## Entidades nuevas

El script `07_ai_module.sql` crea estas tablas principales:

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

Todas las tablas usan `UUID` como clave primaria, siguiendo el estilo general de la base.

---

# 1. `ai_model_version`

## Responsabilidad

Registra modelos, métodos o lógicas IA versionadas.

No todos los registros representan modelos entrenados. También pueden representar reglas, sistemas híbridos, agregaciones o fórmulas de ranking.

Ejemplos registrados:

```text
dish_ner_transformer_v1
dish_normalization_rule_based_v2
mention_sentiment_hybrid_v1_1
signal_aggregation_v1
hidden_gems_ranking_v1
```

## Uso

Esta tabla permite saber qué versión generó cada resultado.

Por ejemplo:

```text
dish_mention → model_version_id = dish_ner_transformer_v1
dish_mention_sentiment → model_version_id = mention_sentiment_hybrid_v1_1
hidden_gem_candidate → ranking_version = hidden_gems_ranking_v1
```

## Campos conceptuales principales

| Campo | Propósito |
|---|---|
| `model_code` | Identificador estable de la versión. |
| `model_name` | Nombre legible. |
| `model_type` | Tipo: transformer, rule_based, hybrid, aggregation, ranking. |
| `task_name` | Tarea: dish_detection, dish_normalization, mention_sentiment, etc. |
| `version_label` | Versión funcional. |
| `framework_name` | Framework usado cuando aplica. |
| `base_model_name` | Modelo base cuando aplica. |
| `metrics_json` | Métricas asociadas. |
| `config_json` | Configuración usada. |
| `is_active` | Indica si la versión está activa. |

---

# 2. `ai_pipeline_run`

## Responsabilidad

Registra ejecuciones de procesos IA.

Es diferente a `source_run`:

```text
source_run = ejecución de adquisición desde una fuente externa
ai_pipeline_run = ejecución de procesamiento IA derivado
```

## Ejemplos

```text
ai_run_yelp_dish_normalization_v2_catalog_import
ai_run_yelp_mention_sentiment_hybrid_v1
ai_run_yelp_signal_aggregation_v1
ai_run_yelp_hidden_gems_ranking_v1
```

## Campos conceptuales principales

| Campo | Propósito |
|---|---|
| `run_code` | Identificador estable de la ejecución. |
| `run_type` | Tipo de ejecución IA. |
| `status` | Estado de la ejecución. |
| `started_at` / `finished_at` | Tiempos de ejecución. |
| `parent_ai_run_id` | Permite encadenar ejecuciones. |
| `source_run_id` | Relación opcional con adquisición externa. |
| `input_artifacts_json` | Artefactos de entrada. |
| `output_artifacts_json` | Artefactos generados. |
| `config_json` | Configuración de ejecución. |
| `metrics_json` | Resumen de métricas. |

---

# 3. `dish`

## Responsabilidad

Catálogo canónico de platos.

Representa conceptos de plato, no menciones concretas.

Ejemplos:

```text
pizza
burger
sushi
tacos
fried chicken
pad thai
brisket ramen
```

## Origen actual

Se carga desde:

```text
dish_catalog_seed_v2.csv
```

## Decisión importante

El identificador del notebook, por ejemplo `dish_seed_v2_000004`, no se usa como PK real.

La base usa:

```text
dish_id = UUID
```

Y el catálogo se resuelve principalmente por nombre normalizado/código interno.

---

# 4. `dish_alias`

## Responsabilidad

Guarda variantes textuales asociadas a un plato canónico.

Ejemplo:

```text
dish = burger
aliases:
- burger
- burgers
- cheeseburger
- burger with bacon
```

## Origen actual

Se carga desde:

```text
dish_aliases_seed_v2.csv
```

## Utilidad futura

Esta tabla será fundamental para normalizar menciones nuevas cuando se apliquen los modelos a datos de Sevilla o Google Places.

---

# 5. `dish_mention`

## Responsabilidad

Representa cada aparición concreta de un plato dentro de una review.

Ejemplo:

```text
review_id = X
dish_id = sushi
mention_text = "sushi"
start_char = 35
end_char = 40
ner_confidence_mean = 0.99
```

## Relaciones

| Relación | Significado |
|---|---|
| `review_id → review` | Review donde aparece la mención. |
| `place_id → place` | Local asociado a la review. |
| `dish_id → dish` | Plato normalizado. |
| `dish_alias_id → dish_alias` | Alias usado cuando aplica. |
| `ai_pipeline_run_id → ai_pipeline_run` | Ejecución que generó la mención. |
| `model_version_id → ai_model_version` | Modelo NER utilizado. |

## Decisión importante

Aunque `place_id` podría obtenerse mediante `review`, se almacena también en `dish_mention` por eficiencia en agregaciones.

La regla de integridad lógica es:

```text
dish_mention.place_id debe coincidir con el place_id de la review asociada
```

---

# 6. `dish_mention_sentiment`

## Responsabilidad

Guarda el sentimiento calculado para una mención concreta.

Se separa de `dish_mention` para poder recalcular sentimiento en el futuro sin duplicar la mención.

Ejemplo:

```text
dish_mention_id = X
sentiment_label = positive
sentiment_score = 0.72
sentiment_confidence = 0.81
sentiment_reliability_tier = high
sentiment_method = hybrid_context_lexicon_v1_1
```

## Origen actual

Se carga desde:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

## Valores principales

```text
sentiment_label:
- positive
- neutral
- negative

sentiment_reliability_tier:
- high
- medium
- low
```

---

# 7. `dish_place_signal`

## Responsabilidad

Guarda señales agregadas por local y plato.

Equivale a la versión persistida de:

```text
dish_business_ranking_candidates_v1.csv
```

Pero usando `place_id`, no `business_id`.

## Ejemplo conceptual

```text
place = Sushi Ushi
dish = sushi
mention_count = 53
review_count = 28
positive_ratio = 0.7169
negative_ratio = 0.0
bayesian_sentiment_score = 0.6945
evidence_tier = strong
```

## Uso

Esta tabla es el puente entre menciones individuales y ranking final.

Permite responder:

```text
¿Qué platos destacan en este local?
¿Qué locales tienen mejor señal para este plato?
¿Qué candidatos tienen evidencia suficiente para ranking?
```

---

# 8. `hidden_gem_candidate`

## Responsabilidad

Guarda los candidatos finales del ranking Hidden Gems.

Equivale a la versión persistida de:

```text
hidden_gems_selected_candidates_v1.csv
```

## Estado actual

El ranking actual se carga como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

Esto respeta la decisión de que Yelp valida el sistema, pero no representa todavía el ranking productivo de Sevilla.

## Campos clave

| Campo | Significado |
|---|---|
| `hidden_gem_score` | Score final de ranking. |
| `hidden_gem_tier` | top, strong, promising o exploratory. |
| `hidden_gem_rank` | Ranking global. |
| `hidden_gem_selected_rank` | Ranking entre seleccionados. |
| `ranking_explanation` | Explicación generada del candidato. |
| `ranking_scope` | Alcance del ranking. |
| `is_production_ready` | Indica si el candidato es producción real. |

---

## Relaciones principales

La cadena completa queda así:

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

Y en paralelo:

```text
dish
  ↓
dish_alias
  ↓
dish_mention
```

---

## Integridad validada

El check final confirma que no existen huérfanos:

```text
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

---

## Ampliación de `validation_issue`

El diseño también contempla que las entidades IA puedan aparecer en incidencias de validación.

Esto permite registrar problemas como:

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
2. UUID como PK en todas las tablas IA.
3. `place_id` como eje del sistema.
4. `business_id` de Yelp queda solo como identificador fuente.
5. `dish` se separa de `dish_mention`.
6. `dish_mention_sentiment` se separa de `dish_mention`.
7. `dish_place_signal` se separa de `hidden_gem_candidate`.
8. Todos los resultados se versionan mediante modelos y runs.
9. El ranking Yelp actual se marca como prototipo.
10. La base queda preparada para un futuro ranking por barrio de Sevilla.
