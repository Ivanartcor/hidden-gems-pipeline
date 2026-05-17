# Nota de actualización


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
sevilla_dish_ner_beto_v1_2
sevilla_dish_normalization_reranker_beto_v1
sevilla_mention_sentiment_absa_beto_v1
sevilla_place_dish_signals_v2
sevilla_hidden_gems_ranking_v2
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
ai_run_sevilla_hybrid_ner_candidates_v2
ai_run_sevilla_normalization_reranker_v1
ai_run_sevilla_sentiment_absa_v1
ai_run_sevilla_place_dish_signals_v2
ai_run_sevilla_hidden_gems_ranking_v2
ai_run_sevilla_dashboard_export_v2
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


```text
Sevilla IA v2:
ranking_scope lógico = sevilla_ai_v2
artifact family = model_inference/ranking_v2
dashboard family = dashboard_v2
is_production_ready = false
```

En la fase v2, el ranking principal se explota desde artefactos CSV/JSONL y dashboard. Si se decide cargar v2 en PostgreSQL, la tabla `hidden_gem_candidate` puede reutilizarse manteniendo los componentes específicos de v2 en campos JSON como `score_components_json`, `ranking_config_json` o `quality_flags_json`.

Para evitar depender de `ranking_scope = other`, se recomienda una migración futura que añada valores nativos como:

```text
sevilla_pilot
sevilla_ai_v2
```

o que sustituya el enum/check rígido por una tabla catálogo de scopes versionados.

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
12. La fase Sevilla IA v2 puede mapearse al mismo modelo físico, pero actualmente debe distinguirse del piloto porque usa NER BETO, reranker de normalización, ABSA y scoring v2.
13. Los campos específicos de v2 deben conservarse en JSON o en columnas auxiliares antes de decidir una ampliación física del DDL.
14. `production_ready = false` sigue siendo obligatorio para v2 hasta que exista validación humana y criterios productivos.


---

# 9. Compatibilidad del schema con Sevilla IA v2

La fase Sevilla IA v2 introduce más señales que el piloto v1:

```text
source_strategy_v2
normalization_confidence_v1
normalization_status_v1
absa_sentiment_label_v1
absa_confidence_v1
weighted_sentiment_score_v2
evidence_tier_v2
aggregate_quality_tier_v2
hidden_gem_score_v2
quality_tier_v2
production_ready_count_v2
```

No todas requieren columnas nuevas obligatorias. La estrategia recomendada es:

1. mantener las tablas IA actuales como núcleo estable;
2. guardar métricas y componentes específicos de v2 en JSON;
3. crear vistas específicas `vw_ai_hidden_gems_sevilla_v2_*` si se carga en DB;
4. mantener los artefactos `dashboard_v2` como contrato de explotación visual;
5. añadir migraciones solo cuando se consolide qué columnas serán estables.

## Riesgo a vigilar

La documentación del schema no debe dar a entender que el ranking v2 ya está necesariamente cargado en PostgreSQL si solo se dispone de los artefactos `model_inference/` y `dashboard_v2/`.

Por tanto, el estado correcto queda así:

```text
Yelp prototype → cargado y consultable en PostgreSQL
Sevilla pilot v1 → cargado y consultable en PostgreSQL
Sevilla IA v2 → generado como artefactos + dashboard; candidato a integración PostgreSQL posterior
```
