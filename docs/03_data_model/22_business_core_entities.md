# docs/03_data_model/22_business_core_entities.md

````md
# 22. Catálogo de entidades: núcleo de negocio

## 1. Introducción

Este documento describe el catálogo de entidades que forman el **núcleo de negocio** del modelo de datos de Hidden Gems.

Este bloque representa los elementos principales del dominio gastronómico sobre los que se construye el resto del sistema:

- locales consolidados
- referencias de esos locales en fuentes externas
- reseñas textuales asociadas a los locales

Las entidades incluidas en este catálogo son:

- `place`
- `place_source_ref`
- `review`

La decisión principal de este bloque es separar claramente el **local canónico interno** de sus **representaciones externas**. Esto permite trabajar con varias fuentes sin perder trazabilidad ni mezclar identificadores externos con la identidad interna del sistema.

---

## 2. Visión general del núcleo de negocio

El núcleo de negocio se organiza alrededor de la entidad `place`.

```text
place
├── place_source_ref
└── review
````

La relación conceptual es la siguiente:

* `place` representa el local real consolidado por Hidden Gems.
* `place_source_ref` representa cómo aparece ese local en Google Places, OSM, Yelp u otra fuente.
* `review` representa una reseña textual asociada a un local y procedente de una fuente concreta.

Esta separación evita depender de una fuente externa como identificador principal y permite evolucionar el sistema hacia procesos de deduplicación, normalización, NLP y análisis posterior.

---

## 3. Entidad `place`

## 3.1. Propósito

`place` representa el **local canónico interno** del sistema.

No representa “el local según Google”, “el local según OSM” o “el local según Yelp”, sino el lugar real que Hidden Gems reconoce como una entidad única dentro de su modelo.

Esta entidad es el centro del dominio gastronómico y actúa como punto de integración para las referencias externas, reseñas, categorías y asignaciones geográficas.

---

## 3.2. Naturaleza de la entidad

| Propiedad             | Valor              |
| --------------------- | ------------------ |
| Tipo                  | Núcleo del dominio |
| Nivel                 | Canónico / interno |
| Dependencia de fuente | No directa         |
| Persistencia          | Sí                 |
| Entidad central       | Sí                 |

---

## 3.3. Decisión de diseño principal

La entidad `place` utiliza un identificador interno propio (`place_id`) y no depende de ningún identificador externo.

Esto significa que no se usa como clave principal:

* `google_place_id`
* `osm_id`
* `yelp_business_id`
* cualquier otro identificador de fuente externa

Los identificadores externos se almacenan en `place_source_ref`.

---

## 3.4. Campos principales

| Campo                | Descripción                                         |
| -------------------- | --------------------------------------------------- |
| `place_id`           | Identificador interno único del local               |
| `canonical_name`     | Nombre canónico elegido por el sistema              |
| `normalized_name`    | Nombre normalizado para matching y deduplicación    |
| `display_name`       | Nombre de presentación opcional                     |
| `address_text`       | Dirección textual consolidada                       |
| `address_normalized` | Dirección normalizada                               |
| `geom_point`         | Punto geográfico canónico del local                 |
| `latitude`           | Latitud derivada del punto geométrico               |
| `longitude`          | Longitud derivada del punto geométrico              |
| `website_url`        | Sitio web consolidado                               |
| `phone_number`       | Teléfono consolidado                                |
| `is_active`          | Indica si el local está activo en el sistema        |
| `place_confidence`   | Confianza del sistema en la consolidación del local |
| `created_at`         | Fecha de creación interna                           |
| `updated_at`         | Fecha de última actualización                       |

---

## 3.5. Reglas de negocio

* Un `place` representa un único local real.
* Un `place` puede estar relacionado con varias fuentes.
* Un `place` puede tener varias reseñas.
* Un `place` puede tener varias categorías.
* Un `place` puede tener una asignación geográfica vigente y, opcionalmente, histórico de asignaciones.
* Un `place` no debe almacenar datos raw específicos de una fuente concreta.
* Un `place` no debe almacenar directamente el barrio, las categorías raw o resultados analíticos.

---

## 3.6. Qué no debe guardar `place`

La entidad `place` no debe guardar:

* IDs externos de fuentes
* rating específico de Google, Yelp u otra fuente
* número de reseñas específico de una fuente
* categorías raw externas
* barrio directo
* sentimiento
* platos detectados
* puntuaciones de ranking
* resultados NLP

Estos elementos pertenecen a otras entidades o capas posteriores.

---

## 3.7. Relaciones

| Relación                                  | Cardinalidad | Descripción                                   |
| ----------------------------------------- | ------------ | --------------------------------------------- |
| `place` → `place_source_ref`              | 1:N          | Un local puede aparecer en varias fuentes     |
| `place` → `review`                        | 1:N          | Un local puede tener muchas reseñas           |
| `place` → `place_category`                | 1:N          | Un local puede tener varias categorías        |
| `place` → `place_neighborhood_assignment` | 1:N          | Un local puede tener asignaciones geográficas |

---

## 3.8. Validaciones relevantes

* `canonical_name` no debe estar vacío.
* `normalized_name` no debe estar vacío.
* `geom_point` debe ser un punto válido.
* `latitude` debe estar entre -90 y 90.
* `longitude` debe estar entre -180 y 180.
* `place_confidence`, si existe, debe estar entre 0 y 1.

---

## 3.9. Índices relevantes

El schema incorpora índices sobre:

* `geom_point`, mediante índice espacial GIST
* `normalized_name`, mediante trigramas
* `canonical_name`, mediante trigramas
* `is_active`
* `updated_at`

Estos índices permiten consultas espaciales, búsqueda textual aproximada y operaciones de deduplicación.

---

## 3.10. Papel en el pipeline

`place` se alimenta después de procesar registros procedentes de una fuente externa.

En una ingesta típica:

1. se obtiene un registro fuente
2. se almacena el raw
3. se crea o actualiza una referencia en `place_source_ref`
4. se crea o consolida un `place`
5. se asigna categoría y barrio en entidades separadas

---

## 4. Entidad `place_source_ref`

## 4.1. Propósito

`place_source_ref` representa la **aparición de un local en una fuente externa concreta**.

Es la entidad que conecta el mundo interno de Hidden Gems con el mundo externo de Google Places, OSM, Yelp u otras fuentes.

---

## 4.2. Naturaleza de la entidad

| Propiedad             | Valor                   |
| --------------------- | ----------------------- |
| Tipo                  | Integración multisource |
| Nivel                 | Representación fuente   |
| Dependencia de fuente | Sí                      |
| Persistencia          | Sí                      |
| Entidad puente        | Sí                      |

---

## 4.3. Decisión de diseño principal

La integración multisource se resuelve en `place_source_ref`, no en `place`.

Esto permite que un mismo local canónico pueda estar asociado a varios identificadores externos.

Ejemplo:

```text
place_id = 123
├── Google Places: ChIJxxxx
├── OSM: node/123456
└── Yelp: business_abc
```

---

## 4.4. Campos principales

| Campo                         | Descripción                                   |
| ----------------------------- | --------------------------------------------- |
| `place_source_ref_id`         | Identificador interno de la referencia fuente |
| `place_id`                    | FK al local canónico                          |
| `source_system_id`            | FK a la fuente de origen                      |
| `source_run_id`               | Ejecución que creó o actualizó la referencia  |
| `raw_asset_id`                | Artefacto raw asociado                        |
| `source_entity_type`          | Tipo de entidad en la fuente                  |
| `source_record_id`            | Identificador externo del registro fuente     |
| `source_name_raw`             | Nombre tal como viene de la fuente            |
| `source_address_raw`          | Dirección tal como viene de la fuente         |
| `source_geom_point`           | Punto geográfico según la fuente              |
| `source_latitude`             | Latitud fuente                                |
| `source_longitude`            | Longitud fuente                               |
| `source_url`                  | URL de referencia en la fuente                |
| `source_rating`               | Rating bruto de la fuente                     |
| `source_review_count`         | Número de reseñas reportado por la fuente     |
| `source_primary_category_raw` | Categoría principal raw                       |
| `source_categories_raw`       | Categorías raw en JSON                        |
| `source_status_raw`           | Estado raw en la fuente                       |
| `source_payload_hash`         | Hash técnico del payload fuente               |
| `match_method`                | Método usado para vincular con `place`        |
| `match_confidence`            | Confianza del matching                        |
| `first_seen_run_id`           | Primera ejecución en la que apareció          |
| `last_seen_run_id`            | Última ejecución en la que apareció           |
| `is_current`                  | Indica si la referencia sigue vigente         |
| `is_deleted_in_source`        | Indica si dejó de aparecer en la fuente       |
| `created_at`                  | Fecha de creación                             |
| `updated_at`                  | Fecha de última actualización                 |

---

## 4.5. Reglas de negocio

* Una referencia externa pertenece a un único `place`.
* Un `place` puede tener muchas referencias fuente.
* Cada registro externo debe ser único dentro de su fuente.
* La relación con `place` debe guardar método y confianza de matching.
* `first_seen_run_id` no debe cambiar una vez fijado.
* `last_seen_run_id` se actualiza cuando el registro vuelve a aparecer.
* La referencia puede marcarse como no vigente sin eliminarse físicamente.

---

## 4.6. Constraint principal

La unicidad de una referencia fuente se garantiza mediante:

```sql
UNIQUE (source_system_id, source_entity_type, source_record_id)
```

Esto evita duplicar el mismo registro externo en el sistema.

---

## 4.7. Qué no debe guardar `place_source_ref`

No debe guardar:

* barrio definitivo
* categoría interna final como única verdad
* ranking
* sentimiento
* platos detectados
* resultados analíticos finales

Su función es conservar la representación fuente y la relación con el `place` canónico.

---

## 4.8. Relaciones

| Relación                             | Cardinalidad | Descripción                                               |
| ------------------------------------ | ------------ | --------------------------------------------------------- |
| `place_source_ref` → `place`         | N:1          | Cada referencia pertenece a un local canónico             |
| `place_source_ref` → `source_system` | N:1          | Cada referencia procede de una fuente                     |
| `place_source_ref` → `source_run`    | N:1 opcional | Puede vincularse a la ejecución de carga                  |
| `place_source_ref` → `raw_asset`     | N:1 opcional | Puede vincularse al artefacto raw                         |
| `review` → `place_source_ref`        | N:1 opcional | Una reseña puede vincularse a la referencia fuente exacta |

---

## 4.9. Validaciones relevantes

* `source_entity_type` no debe estar vacío.
* `source_record_id` no debe estar vacío.
* `source_name_raw` no debe estar vacío.
* `source_rating`, si existe, debe estar entre 0 y 5.
* `source_review_count`, si existe, debe ser mayor o igual que 0.
* `match_confidence`, si existe, debe estar entre 0 y 1.
* `source_payload_hash`, si existe, debe tener formato SHA-256.

---

## 4.10. Papel en el pipeline

`place_source_ref` es clave en las verticales de adquisición.

En una vertical como OSM / Overpass, cada POI detectado puede generar una referencia fuente. El sistema decide si esa referencia crea un nuevo `place` o se vincula a uno existente.

En futuras verticales como Google Places, la misma entidad permitirá unir registros de Google con locales ya detectados por OSM.

---

## 5. Entidad `review`

## 5.1. Propósito

`review` representa una **reseña textual individual** asociada a un local.

Esta entidad es la base para futuras fases de procesamiento textual, extracción de señales gastronómicas, análisis de sentimiento y detección de menciones de platos.

---

## 5.2. Naturaleza de la entidad

| Propiedad             | Valor                            |
| --------------------- | -------------------------------- |
| Tipo                  | Núcleo textual del dominio       |
| Nivel                 | Dato fuente textual estructurado |
| Dependencia de fuente | Sí                               |
| Persistencia          | Sí                               |
| Preparada para NLP    | Sí                               |

---

## 5.3. Decisión de diseño principal

Las reseñas son **source-bound**.

Esto significa que una reseña conserva su relación con la fuente de origen y no se fusiona automáticamente con reseñas de otras fuentes.

Cada reseña mantiene:

* fuente
* texto raw
* texto normalizado
* rating asociado
* fecha fuente si existe
* vínculo al local canónico

---

## 5.4. Campos principales

| Campo                    | Descripción                               |
| ------------------------ | ----------------------------------------- |
| `review_id`              | Identificador interno de la reseña        |
| `place_id`               | FK al local canónico                      |
| `place_source_ref_id`    | FK opcional a la referencia fuente exacta |
| `source_system_id`       | FK a la fuente de origen                  |
| `source_run_id`          | Ejecución de ingesta asociada             |
| `source_review_id`       | Identificador externo de la reseña        |
| `author_name_raw`        | Nombre raw del autor                      |
| `author_name_hash`       | Hash del autor                            |
| `rating_value`           | Valoración numérica de la reseña          |
| `review_title`           | Título de la reseña si existe             |
| `review_text_raw`        | Texto original de la reseña               |
| `review_text_normalized` | Texto normalizado para procesamiento      |
| `review_language`        | Idioma de la reseña                       |
| `review_created_at`      | Fecha de publicación en origen            |
| `review_updated_at`      | Fecha de actualización en origen          |
| `source_review_url`      | URL de la reseña si existe                |
| `helpful_count`          | Métrica de utilidad si existe             |
| `translated_text`        | Traducción si se genera o viene dada      |
| `text_length_chars`      | Longitud del texto                        |
| `is_active`              | Indica si la reseña sigue activa          |
| `is_deleted_in_source`   | Indica si desapareció de la fuente        |
| `created_at`             | Fecha de creación interna                 |
| `updated_at`             | Fecha de última actualización             |

---

## 5.5. Reglas de negocio

* Una `review` pertenece a un único `place`.
* Una `review` pertenece a una única `source_system`.
* Una `review` puede estar vinculada a una `place_source_ref` concreta.
* El texto original nunca debe ser sobrescrito por el texto normalizado.
* Las reviews no se fusionan automáticamente entre fuentes.
* Una review puede desactivarse sin eliminarse físicamente.
* Las reviews son la base textual para NLP futuro.

---

## 5.6. Qué no debe guardar `review`

No debe guardar directamente:

* sentimiento final
* menciones de platos
* embeddings
* score de utilidad del modelo
* contribución al ranking
* resultados analíticos complejos

Estos elementos se añadirán en capas futuras o entidades derivadas.

---

## 5.7. Relaciones

| Relación                      | Cardinalidad | Descripción                                    |
| ----------------------------- | ------------ | ---------------------------------------------- |
| `review` → `place`            | N:1          | Cada reseña pertenece a un local               |
| `review` → `source_system`    | N:1          | Cada reseña procede de una fuente              |
| `review` → `source_run`       | N:1 opcional | Puede vincularse a la ejecución de carga       |
| `review` → `place_source_ref` | N:1 opcional | Puede vincularse a la referencia fuente exacta |

---

## 5.8. Validaciones relevantes

* `review_text_raw` es obligatorio y no debe estar vacío.
* `rating_value`, si existe, debe estar entre 0 y 5.
* `helpful_count`, si existe, debe ser mayor o igual que 0.
* `text_length_chars`, si existe, debe ser mayor o igual que 0.
* `review_updated_at` no debe ser anterior a `review_created_at`.
* `author_name_hash`, si existe, debe tener formato SHA-256.

---

## 5.9. Índices relevantes

El schema incorpora índices sobre:

* `place_id`
* `place_source_ref_id`
* `source_system_id`
* `source_run_id`
* `review_created_at`
* `review_language`
* `is_active`

También se define un índice de búsqueda textual básica sobre `review_text_raw`.

---

## 5.10. Papel en el pipeline

`review` será especialmente importante en futuras verticales como Google Places y Yelp Open Dataset.

En la fase actual, el modelo ya está preparado para recibir reseñas, conservar su origen y dejar el texto listo para procesos posteriores de normalización y NLP.

---

## 6. Decisiones generales del núcleo de negocio

Las decisiones más importantes de este catálogo son:

1. `place` es la entidad canónica interna.
2. `place_source_ref` conserva los IDs y datos raw de cada fuente.
3. `review` conserva texto raw y normalizado.
4. Las reseñas no se fusionan entre fuentes.
5. Los resultados NLP quedan fuera del núcleo inicial.
6. La integración multisource se basa en matching documentado y trazable.
7. La geografía y la clasificación se resuelven en entidades separadas.

---

## 7. Relación con verticales actuales y futuras

### 7.1. Vertical OSM / Overpass

La vertical de Overpass alimenta principalmente:

* `place`
* `place_source_ref`

También puede alimentar, mediante procesos posteriores:

* `category`
* `place_category`
* `place_neighborhood_assignment`

### 7.2. Vertical Google Places

La vertical de Google Places alimentará principalmente:

* `place`
* `place_source_ref`
* `review`

### 7.3. Vertical Yelp Open Dataset

La vertical de Yelp servirá como apoyo para:

* `place_source_ref`
* `review`
* pruebas de procesamiento textual
* validación de estrategias NLP

---

## 8. Conclusión

El núcleo de negocio del modelo de datos proporciona una base sólida para representar locales, referencias externas y reseñas.

La separación entre `place`, `place_source_ref` y `review` es una de las decisiones arquitectónicas más importantes del proyecto, ya que permite trabajar con múltiples fuentes sin perder trazabilidad, consistencia ni capacidad de evolución.
