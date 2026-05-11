# 25. Catálogo de entidades: gobierno y trazabilidad

## 1. Introducción

Este documento describe las entidades responsables del **gobierno técnico y la trazabilidad** dentro del modelo de datos de Hidden Gems.

El proyecto no se limita a almacenar locales, reseñas, geometrías o resultados IA. También registra:

- de qué fuente procede cada dato;
- cuándo se ejecutó una ingesta;
- qué archivos raw se generaron;
- cuántos registros se extrajeron;
- qué errores o advertencias aparecieron;
- qué artefactos permiten reproducir o auditar el proceso;
- qué modelo, regla o método IA generó cada resultado;
- qué ejecución IA produjo un catálogo, una mención, una señal o un ranking.

Las entidades principales de gobierno de fuentes son:

- `source_system`;
- `source_run`;
- `raw_asset`.

Con la capa IA se incorporan:

- `ai_model_version`;
- `ai_pipeline_run`.

Estas entidades convierten el pipeline en un sistema trazable y auditable, no en una colección de scripts aislados.

---

## 2. Visión general del bloque

Bloque fuente:

```text
source_system
└── source_run
    └── raw_asset
```

Bloque IA:

```text
ai_model_version
└── ai_pipeline_run
    ├── dish
    ├── dish_alias
    ├── dish_mention
    ├── dish_mention_sentiment
    ├── dish_place_signal
    └── hidden_gem_candidate
```

Interpretación:

- `source_system` identifica la fuente;
- `source_run` identifica una ejecución sobre esa fuente;
- `raw_asset` identifica artefactos raw;
- `ai_model_version` identifica una versión de modelo, regla, método híbrido, agregador o ranking;
- `ai_pipeline_run` identifica una ejecución concreta de procesamiento IA.

---

## 3. Decisiones principales

### 3.1. Toda fuente debe estar registrada

Cada fuente debe existir en `source_system` antes de ser utilizada.

### 3.2. No debe existir ingesta silenciosa

Toda ejecución relevante debe registrarse en `source_run`.

### 3.3. El raw debe ser auditable

Cada raw relevante se registra en `raw_asset` con ruta, formato, tamaño, checksum y relación al run.

### 3.4. Todo resultado IA debe estar versionado

Los resultados IA pueden cambiar si cambian reglas, modelos, pesos, thresholds o corpus.

Por eso, los resultados derivados deben relacionarse con `ai_model_version` y `ai_pipeline_run`.

### 3.5. Separar ingesta fuente y procesamiento IA

`source_run` y `ai_pipeline_run` no representan lo mismo.

| Entidad | Representa | Ejemplo |
|---|---|---|
| `source_run` | Ejecución de adquisición o importación desde una fuente | batch Google Places, batch Google Reviews |
| `ai_pipeline_run` | Ejecución de procesamiento inteligente derivado | detección de platos, normalización, sentimiento, ranking |

---

## 4. Entidad `source_system`

### Propósito

Representa una fuente de datos reconocida por el sistema.

Ejemplos:

- `google_places`;
- `osm_overpass`;
- `sevilla_geo`;
- `yelp_open_dataset`.

### Campos principales

| Campo | Descripción |
|---|---|
| `source_system_id` | Identificador interno |
| `source_code` | Código técnico único |
| `source_name` | Nombre legible |
| `source_type` | Tipo de fuente |
| `base_url` | URL base si aplica |
| `auth_type` | Tipo de autenticación |
| `data_format_default` | Formato habitual |
| `refresh_mode_default` | Modo típico de actualización |
| `supports_incremental` | Soporte incremental |
| `is_active` | Fuente activa |

### Reglas

- `source_code` debe ser único y estable.
- Una fuente puede desactivarse sin eliminarse.
- No almacena ejecuciones, payloads ni resultados IA.

---

## 5. Entidad `source_run`

### Propósito

Representa una ejecución concreta del pipeline sobre una fuente.

### Campos principales

| Campo | Descripción |
|---|---|
| `source_run_id` | Identificador interno |
| `run_code` | Código legible del run |
| `source_system_id` | FK a la fuente |
| `run_type` | Tipo de ejecución |
| `trigger_type` | Forma de lanzamiento |
| `status` | Estado |
| `started_at` | Inicio |
| `finished_at` | Fin |
| `duration_seconds` | Duración |
| `records_extracted_count` | Registros extraídos |
| `records_staged_count` | Registros staged |
| `records_rejected_count` | Registros rechazados |
| `raw_asset_count` | Assets generados |
| `error_count` | Errores |
| `warning_count` | Advertencias |
| `request_summary` | Resumen de petición/configuración |

### Papel actual

Se utiliza en verticales como:

- Sevilla Geo;
- OSM / Overpass;
- Google Places Text Search;
- Google Places Reviews;
- Yelp Open Dataset como carga de fuente/corpus.

---

## 6. Entidad `raw_asset`

### Propósito

Representa un artefacto raw almacenado durante una ejecución.

Puede ser:

- respuesta JSON de API;
- GeoJSON;
- archivo bulk;
- resultado de consulta;
- export raw.

### Campos principales

| Campo | Descripción |
|---|---|
| `raw_asset_id` | Identificador interno |
| `asset_code` | Código del asset |
| `source_system_id` | Fuente |
| `source_run_id` | Run asociado |
| `asset_name` | Nombre lógico |
| `asset_type` | Tipo de asset |
| `storage_path` | Ruta física/URI |
| `file_format` | Formato |
| `file_size_bytes` | Tamaño |
| `checksum_sha256` | Hash |
| `query_name` | Nombre de consulta |
| `request_signature_hash` | Hash de parámetros |
| `is_available` | Disponibilidad |

### Regla clave

El raw se considera inmutable. Si se vuelve a descargar, se crea un nuevo asset.

---

## 7. Entidad `ai_model_version`

### Propósito

Registra cualquier modelo, regla o método IA versionado.

No se limita a modelos entrenados. También representa:

- reglas de normalización;
- métodos híbridos de sentimiento;
- agregadores de señales;
- fórmulas de ranking;
- procesos manuales versionados.

### Campos principales

| Campo | Descripción |
|---|---|
| `ai_model_version_id` | Identificador interno |
| `model_code` | Código único |
| `model_name` | Nombre legible |
| `model_type` | Tipo de modelo/método |
| `task_name` | Tarea |
| `version_label` | Versión |
| `language_scope` | Idioma/alcance |
| `training_dataset_name` | Dataset si aplica |
| `metrics_json` | Métricas |
| `config_json` | Configuración |
| `is_active` | Estado |

### Versiones actuales relevantes

Prototipo Yelp:

- `dish_ner_transformer_v1`;
- `dish_normalization_rule_based_v2`;
- `mention_sentiment_hybrid_v1_1`;
- `signal_aggregation_v1`;
- `hidden_gems_ranking_v1`.

Piloto Sevilla:

- `sevilla_dish_detection_hybrid_v1`;
- `sevilla_dish_normalization_hybrid_v1`;
- `sevilla_mention_sentiment_hybrid_v1`;
- `sevilla_signal_aggregation_v1`;
- `sevilla_hidden_gems_ranking_pilot_v1`.

---

## 8. Entidad `ai_pipeline_run`

### Propósito

Representa una ejecución concreta de procesamiento IA.

Ejemplos:

- importación de catálogo;
- detección de menciones;
- normalización de platos;
- sentimiento por mención;
- agregación de señales;
- ranking Hidden Gems.

### Campos principales

| Campo | Descripción |
|---|---|
| `ai_pipeline_run_id` | Identificador interno |
| `run_code` | Código único |
| `run_type` | Tipo de ejecución IA |
| `status` | Estado |
| `started_at` | Inicio |
| `finished_at` | Fin |
| `source_run_id` | Run fuente relacionado si aplica |
| `input_artifacts_json` | Entradas |
| `output_artifacts_json` | Salidas |
| `config_json` | Configuración |
| `metrics_json` | Métricas |

### Runs Sevilla validados

- `ai_run_sevilla_dish_catalog_v1`;
- `ai_run_sevilla_dish_mentions_v1`;
- `ai_run_sevilla_mention_sentiment_v1`;
- `ai_run_sevilla_signal_aggregation_v1`;
- `ai_run_sevilla_hidden_gems_ranking_pilot_v1`.

Todos se validaron como `completed` en el check del piloto Sevilla.

---

## 9. Relación entre gobierno fuente e IA

Flujo general:

```text
source_system
→ source_run
→ raw_asset
→ place / review
→ ai_pipeline_run
→ dish_mention / sentiment / signals / ranking
```

Ejemplo Yelp:

```text
yelp_open_dataset
→ source_run carga core Yelp
→ place + place_source_ref + review
→ ai_pipeline_run IA Yelp
→ ranking_scope = yelp_prototype
```

Ejemplo Sevilla:

```text
google_places
→ source_run Text Search / Reviews
→ place + place_source_ref + review
→ export_reviews_for_ai
→ notebooks 12–17
→ ai_pipeline_run Sevilla
→ artifact_ranking_scope = sevilla_pilot
→ db_ranking_scope = other
```

---

## 10. Papel en verticales actuales

### Sevilla Geo

Genera `source_run` y `raw_asset` para los datasets geográficos.

### OSM / Overpass

Genera trazabilidad para consultas Overpass, raw JSON y artefactos QA.

### Google Places Text Search

Genera trazabilidad para búsquedas, raw, importación canónica y batches.

### Google Places Reviews

Genera trazabilidad para Place Details, raw de reviews y carga en `review`.

En el piloto Sevilla, esas reviews son el origen real del flujo IA local.

### Yelp Open Dataset

Genera trazabilidad como corpus/prototipo IA, no como producción Sevilla.

---

## 11. Decisiones generales del bloque

1. Toda fuente debe registrarse en `source_system`.
2. Toda ejecución de adquisición debe registrarse en `source_run`.
3. Todo raw relevante debe registrarse en `raw_asset`.
4. El raw es inmutable.
5. Los errores estructurados se registran en `validation_issue`.
6. Todo modelo, regla o método IA debe registrarse en `ai_model_version`.
7. Toda ejecución IA relevante debe registrarse en `ai_pipeline_run`.
8. Los resultados IA deben ser reproducibles mediante versión, run, configuración y métricas.
9. Yelp se mantiene como `yelp_prototype`.
10. Sevilla pilot se mantiene como `sevilla_pilot` en artefactos/configuración, pero en DB usa `ranking_scope = other` por constraint actual.

---

## 12. Conclusión

El bloque de gobierno y trazabilidad permite reconstruir el recorrido del dato desde la fuente original hasta los rankings consultables.

Gracias a `source_system`, `source_run` y `raw_asset`, el sistema audita la adquisición.

Gracias a `ai_model_version` y `ai_pipeline_run`, el sistema audita cómo se generaron detecciones de platos, normalizaciones, sentimientos, señales y rankings.

El bloque ya soporta tanto el prototipo Yelp como el piloto local Sevilla, dejando el sistema preparado para dashboard, API y futuras iteraciones de IA.
