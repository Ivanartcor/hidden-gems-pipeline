# 26. Catálogo de entidades: calidad

## 1. Introducción

Este documento describe el bloque de entidades encargado del **control de calidad, validación e incidencias** dentro del modelo de datos de Hidden Gems.

Un pipeline de datos no solo debe almacenar información. También debe ser capaz de registrar los problemas encontrados durante la adquisición, integración, validación, enriquecimiento, procesamiento IA y explotación analítica.

La entidad principal de calidad estructurada es:

- `validation_issue`.

Además, tras la integración IA, el proyecto cuenta con scripts de comprobación específicos que generan reportes de calidad sobre el catálogo de platos, el mapeo de artefactos IA, la carga de menciones, la carga de señales y la consulta del ranking.

---

## 2. Visión general del bloque de calidad

El bloque de calidad se conecta principalmente con las entidades de gobierno y trazabilidad.

```text
source_run
└── validation_issue

raw_asset
└── validation_issue
```

Además, `validation_issue` puede apuntar conceptualmente a cualquier entidad del sistema mediante:

```text
entity_type + entity_id
```

Esto permite registrar incidencias sobre locales, reseñas, referencias fuente, categorías, geometrías, assets raw, entidades IA o candidatos de ranking.

Con la capa IA integrada, el control de calidad también cubre:

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

---

## 3. Decisiones principales del bloque de calidad

### 3.1. Registrar incidencias estructuradas

Las incidencias relevantes no deben quedar únicamente en logs de texto.

Los logs son útiles para depuración, pero no son suficientes para explotación posterior, reporting o análisis de calidad.

Por eso el modelo incorpora `validation_issue` como entidad estructurada.

---

### 3.2. Vincular cada incidencia a una ejecución

Toda incidencia debe estar asociada a un `source_run` cuando procede de una vertical de adquisición o carga de fuente.

En procesos IA, las incidencias pueden estar relacionadas conceptualmente con un `ai_pipeline_run`, aunque la entidad `validation_issue` mantiene como eje formal `source_run`. Cuando sea necesario, la relación con procesos IA puede documentarse mediante:

- `entity_type`;
- `entity_id`;
- `issue_code`;
- `message`;
- artefactos JSON de checks;
- métricas en `ai_pipeline_run.metrics_json`.

---

### 3.3. Permitir relación polimórfica con entidades afectadas

Una incidencia puede afectar a distintos tipos de entidades:

- `place`;
- `place_source_ref`;
- `review`;
- `category`;
- `neighborhood`;
- `raw_asset`;
- `dish`;
- `dish_mention`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

Crear una FK directa para cada posible entidad haría el modelo rígido y complejo.

Por ello se utiliza una relación polimórfica mediante:

```text
entity_type + entity_id
```

La consistencia de esta relación se controla desde la lógica del pipeline y mediante catálogos permitidos de `entity_type`.

---

### 3.4. No cargar resultados IA sin mapeo canónico

Una regla de calidad clave para la integración IA es no insertar resultados huérfanos.

No se deben cargar:

- menciones sin `review`;
- menciones sin `place`;
- menciones sin `dish`;
- sentimientos sin `dish_mention`;
- señales sin `place` o `dish`;
- candidatos de ranking sin `dish_place_signal`.

Esta decisión evita que la capa IA se desconecte del modelo canónico.

---

### 3.5. Diferenciar prototipo y producción

El ranking actual procedente de Yelp se considera prototipo IA.

Por eso se almacena con:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

Un ranking productivo de Sevilla deberá cumplir criterios adicionales:

- `ranking_scope = sevilla_neighborhood`;
- `is_production_ready = true`;
- `neighborhood_id` no nulo;
- `district_id` no nulo;
- datos procedentes de fuentes operativas reales;
- validación adicional de idioma, volumen y calidad textual.

---

## 4. Entidad `validation_issue`

## 4.1. Propósito

`validation_issue` representa una **incidencia de calidad, validación, consistencia, matching, geografía, esquema o procesamiento** detectada por el sistema.

Su objetivo es dejar evidencia estructurada de los problemas encontrados durante el procesamiento.

---

## 4.2. Naturaleza de la entidad

| Propiedad | Valor |
|---|---|
| Tipo | Calidad / auditoría |
| Nivel | Incidencia estructurada |
| Origen | Sistema interno |
| Persistencia | Sí |
| Relación polimórfica | Sí |

---

## 4.3. Campos principales

| Campo | Descripción |
|---|---|
| `validation_issue_id` | Identificador interno de la incidencia |
| `source_run_id` | Ejecución donde se detectó la incidencia |
| `raw_asset_id` | Asset raw relacionado si aplica |
| `entity_type` | Tipo de entidad afectada |
| `entity_id` | ID de la entidad afectada |
| `issue_code` | Código técnico de la incidencia |
| `issue_type` | Tipo general del problema |
| `severity` | Severidad |
| `message` | Mensaje legible |
| `field_name` | Campo afectado si aplica |
| `received_value` | Valor recibido o problemático |
| `expected_rule` | Regla esperada o incumplida |
| `status` | Estado de la incidencia |
| `resolution_notes` | Notas de resolución |
| `detected_at` | Fecha de detección |
| `resolved_at` | Fecha de resolución |
| `created_at` | Fecha de creación |
| `updated_at` | Fecha de actualización |

---

## 4.4. Tipos de incidencia

Valores previstos para `issue_type`:

- `validation`;
- `quality`;
- `matching`;
- `geospatial`;
- `schema`.

Estos tipos permiten agrupar problemas según su naturaleza.

### Ejemplos

| Tipo | Ejemplo |
|---|---|
| `validation` | Campo obligatorio ausente |
| `quality` | Texto demasiado corto o poco útil |
| `matching` | Duplicado potencial entre fuentes |
| `geospatial` | Local fuera de barrios oficiales |
| `schema` | Estructura inesperada en una respuesta raw |

---

## 4.5. Severidades

Valores previstos para `severity`:

- `info`;
- `warning`;
- `error`;
- `critical`.

### Interpretación recomendada

| Severidad | Significado |
|---|---|
| `info` | Incidencia informativa que no bloquea el proceso |
| `warning` | Problema menor que permite continuar |
| `error` | Problema que afecta al registro o etapa concreta |
| `critical` | Problema grave que puede invalidar una ejecución o vertical |

---

## 4.6. Estados

Valores previstos para `status`:

- `open`;
- `resolved`;
- `ignored`.

### Interpretación recomendada

| Estado | Significado |
|---|---|
| `open` | La incidencia sigue pendiente |
| `resolved` | La incidencia fue corregida o gestionada |
| `ignored` | La incidencia se acepta y no requiere acción |

---

## 4.7. Entity types permitidos

El schema permite registrar incidencias sobre las entidades principales del modelo.

Valores del modelo base:

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

Valores añadidos para la capa IA:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

Esto permite que el sistema registre incidencias de forma homogénea sin multiplicar tablas específicas.

---

## 4.8. Ejemplos de `issue_code`

Los códigos de incidencia deben ser técnicos, estables y en formato `snake_case`.

Ejemplos generales:

| Código | Descripción |
|---|---|
| `missing_coordinates` | El registro no tiene coordenadas |
| `invalid_geometry` | La geometría no es válida |
| `empty_name` | El nombre está vacío |
| `duplicate_candidate` | Posible duplicado detectado |
| `unmapped_category` | Categoría fuente sin mapeo interno |
| `missing_required_field` | Falta un campo obligatorio |
| `review_text_empty` | Reseña sin texto útil |
| `neighborhood_not_found` | No se pudo asignar barrio |
| `schema_mismatch` | La estructura del raw no coincide con lo esperado |

Ejemplos específicos de IA:

| Código | Descripción |
|---|---|
| `dish_alias_duplicate` | Alias duplicado o ambiguo entre varios platos |
| `dish_without_alias` | Plato sin alias asociado |
| `missing_review_mapping` | Una mención no puede mapearse a `review` |
| `missing_place_mapping` | Un business externo no puede mapearse a `place` |
| `missing_dish_mapping` | Una mención o señal no puede mapearse a `dish` |
| `invalid_sentiment_label` | Sentimiento fuera de valores esperados |
| `invalid_ranking_score` | Score de ranking fuera de rango |
| `orphan_dish_mention` | Mención sin relación válida |
| `orphan_hidden_gem_candidate` | Candidato sin señal agregada válida |
| `production_candidate_without_neighborhood` | Candidato productivo sin barrio asignado |

---

## 4.9. Reglas de negocio

- Toda incidencia debe estar asociada a un `source_run` cuando procede de una vertical de adquisición.
- Una incidencia puede estar asociada a un `raw_asset`.
- Una incidencia debe indicar el tipo de entidad afectada.
- Una incidencia debe tener código técnico.
- Una incidencia debe tener tipo, severidad y estado.
- Una incidencia no debe eliminarse sin criterio.
- Lo normal es resolverla, ignorarla justificadamente o dejarla abierta.
- En IA, los checks deben impedir cargas con mapeos incompletos cuando afecten a integridad referencial.

---

## 4.10. Qué no debe guardar `validation_issue`

No debe guardar:

- payloads raw completos;
- filas completas de negocio;
- archivos embebidos;
- reportes agregados completos;
- lógica completa de validación;
- outputs completos de modelos.

Debe registrar la incidencia de forma estructurada y suficiente para poder entenderla y tratarla.

---

## 4.11. Relaciones

| Relación | Cardinalidad | Descripción |
|---|---:|---|
| `validation_issue` → `source_run` | N:1 | Toda incidencia pertenece a una ejecución fuente |
| `validation_issue` → `raw_asset` | N:1 opcional | Puede relacionarse con un artefacto raw |
| `validation_issue` → entidad afectada | Polimórfica | Se representa con `entity_type` + `entity_id` |

---

## 4.12. Validaciones relevantes

- `source_run_id` es obligatorio.
- `entity_type` es obligatorio.
- `issue_code` es obligatorio.
- `issue_code` debe estar en formato `snake_case`.
- `issue_type` es obligatorio.
- `severity` es obligatorio.
- `message` es obligatorio.
- `status` es obligatorio.
- `resolved_at`, si existe, no puede ser anterior a `detected_at`.
- Si `status = resolved`, debe existir `resolved_at`.

---

## 4.13. Índices relevantes

El schema define índices sobre:

- `source_run_id`;
- `raw_asset_id`;
- `entity_type`;
- `(entity_type, entity_id)`;
- `issue_code`;
- `issue_type`;
- `severity`;
- `status`;
- `detected_at`.

Estos índices permiten consultar incidencias por ejecución, entidad afectada, severidad, estado o fecha.

---

## 5. Relación con verticales actuales

## 5.1. Vertical Sevilla Geo

La vertical Sevilla Geo puede registrar incidencias como:

- geometría inválida;
- barrio sin distrito;
- nombre oficial vacío;
- geometría vacía;
- error al descargar o leer el GeoJSON.

Estas incidencias se asociarían al `source_run` correspondiente y, si aplica, al `raw_asset` geográfico.

---

## 5.2. Vertical OSM / Overpass

La vertical OSM / Overpass puede registrar incidencias como:

- POI sin nombre;
- POI sin coordenadas;
- categoría no mapeada;
- posible duplicado;
- local fuera de la geometría de barrios;
- respuesta raw incompleta;
- error de esquema en el JSON de Overpass.

Estas incidencias permiten medir la calidad de la ingesta y priorizar mejoras.

---

## 5.3. Vertical Google Places

La vertical Google Places puede registrar incidencias como:

- respuesta sin `places`;
- local sin coordenadas;
- local sin nombre;
- categoría Google no mapeada;
- duplicado potencial con OSM;
- error de API;
- local sin asignación geográfica.

---

## 5.4. Vertical Google Places Reviews

La vertical Google Reviews puede registrar incidencias como:

- local sin `place_source_ref` válida;
- respuesta sin reviews;
- review sin texto útil;
- rating fuera de rango;
- idioma inesperado;
- payload duplicado;
- review no elegible para IA.

---

## 5.5. Vertical Yelp Open Dataset

Yelp Open Dataset puede registrar incidencias como:

- negocio gastronómico sin coordenadas;
- review sin texto mínimo;
- negocio sin categorías útiles;
- business_id sin mapeo a `place`;
- review_id sin mapeo a `review`;
- problemas al procesar JSON Lines;
- registros no elegibles para corpus IA.

En la integración actual, Yelp se utiliza como prototipo IA y no como fuente productiva de Sevilla.

---

## 6. Calidad específica de la capa IA

La capa IA tiene controles adicionales porque depende de varios mapeos entre artefactos y entidades canónicas.

### 6.1. Catálogo de platos

El catálogo de platos se valida con checks como:

- número total de platos;
- número total de aliases;
- platos sin alias;
- aliases duplicados;
- aliases compartidos entre varios platos;
- existencia de alias canónico;
- distribución por idioma y tipo de alias.

Script asociado:

```powershell
python -m scripts.check_ai_dish_catalog
```

---

### 6.2. Preparación para cargas posteriores

Antes de cargar menciones, señales y ranking, se comprueba que los artefactos puedan mapearse contra la base.

Checks principales:

- `review_id` del artefacto contra `review.source_review_id`;
- `business_id` del artefacto contra `place_source_ref.source_record_id`;
- nombres de platos contra `dish.normalized_name`;
- existencia de tablas IA;
- existencia de modelos y runs esperados.

Script asociado:

```powershell
python -m scripts.check_ai_downstream_import_readiness
```

Este check impide avanzar si no existe el puente:

```text
Yelp business_id → place_source_ref → place_id
Yelp review_id   → review.source_review_id → review_id interno
```

---

### 6.3. Carga de menciones y sentimiento

El loader de menciones y sentimiento valida:

- líneas JSONL válidas;
- campos obligatorios;
- mapeo a `review`;
- mapeo a `place`;
- mapeo a `dish`;
- etiquetas de sentimiento válidas;
- consistencia business-review;
- ausencia de skips relevantes.

Script asociado:

```powershell
python -m scripts.load_ai_mentions_and_sentiment
```

Resultado validado:

| Métrica | Valor |
|---|---:|
| Menciones cargadas | 94.932 |
| Sentimientos cargados | 94.932 |
| Líneas inválidas | 0 |
| Registros saltados por falta de mapping | 0 |

---

### 6.4. Carga de señales y ranking

El loader de señales y ranking valida:

- mapeo `business_id → place_id`;
- mapeo `canonical_dish_name_v2 → dish_id`;
- existencia de señal para cada candidato;
- scores válidos;
- tiers válidos;
- ranking marcado como prototipo cuando procede.

Script asociado:

```powershell
python -m scripts.load_ai_signals_and_ranking
```

Resultado validado:

| Métrica | Valor |
|---|---:|
| Señales local-plato cargadas | 31.036 |
| Candidatos Hidden Gems cargados | 622 |
| Registros saltados por falta de mapping | 0 |
| Ranking scope | `yelp_prototype` |
| Producción Sevilla | No |

---

### 6.5. Check final del ranking cargado

El check final valida:

- conteos de todas las tablas IA;
- distribución de sentimiento;
- señales agregadas;
- tiers de ranking;
- top candidatos;
- integridad referencial;
- ausencia de huérfanos;
- estado `ready_for_querying_ai_ranking`.

Script asociado:

```powershell
python -m scripts.check_ai_ranking_loaded
```

Resultado final validado:

| Elemento | Resultado |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |
| Huérfanos detectados | 0 |
| `ready_for_querying_ai_ranking` | `true` |

---

## 7. Relación con reporting de calidad

`validation_issue` y los reportes JSON generados por los checks pueden alimentar reportes de calidad como:

- número de incidencias por fuente;
- número de incidencias por run;
- incidencias abiertas por severidad;
- porcentaje de registros rechazados;
- problemas geográficos frecuentes;
- categorías sin mapear;
- duplicados potenciales;
- cobertura del catálogo IA;
- porcentaje de menciones con sentimiento de alta fiabilidad;
- candidatos con baja evidencia;
- rankings por scope y estado productivo.

Esto convierte la calidad en un elemento medible y no solo en una revisión manual informal.

---

## 8. Decisiones generales del bloque de calidad

Las decisiones principales son:

1. Las incidencias relevantes se estructuran en base de datos.
2. Toda incidencia pertenece a una ejecución cuando procede de ingesta fuente.
3. Una incidencia puede vincularse a un raw asset.
4. La entidad afectada se representa de forma polimórfica.
5. Las incidencias tienen tipo, severidad y estado.
6. Los códigos de incidencia deben ser estables y en `snake_case`.
7. La tabla sirve para auditoría, reporting y mejora continua del pipeline.
8. La capa IA no debe cargarse si no hay mapeo completo con `review`, `place` y `dish`.
9. Yelp se valida como prototipo IA, no como ranking productivo de Sevilla.
10. Los checks deben generar reportes reproducibles para dejar evidencia del estado del sistema.

---

## 9. Conclusión

El bloque de calidad permite que Hidden Gems controle y documente los problemas detectados durante el pipeline.

Gracias a `validation_issue`, el sistema puede auditar errores, advertencias y problemas de consistencia de forma estructurada.

Gracias a los checks específicos de IA, también puede validar que los resultados inteligentes no queden desconectados del modelo canónico y que el ranking cargado sea consultable con garantías.

Esta entidad y los scripts de calidad asociados son fundamentales para mantener la confianza en los datos y orientar las siguientes fases de normalización, adaptación a Sevilla, ranking por barrio y explotación analítica.
