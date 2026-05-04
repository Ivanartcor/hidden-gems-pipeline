# 21. Esquema de base de datos

## 1. Introducción

El esquema de base de datos de Hidden Gems se ha implementado sobre **PostgreSQL + PostGIS**.

La elección de PostgreSQL responde a la necesidad de contar con una base relacional sólida, con soporte para integridad referencial, constraints, índices avanzados y consultas analíticas. PostGIS se incorpora porque el proyecto necesita trabajar con geometrías oficiales, coordenadas de locales y asignación espacial de puntos a barrios.

El esquema principal se denomina:

```sql
hidden_gems
````

Dentro de este esquema se agrupan todas las tablas del modelo principal.

---

## 2. Organización de scripts SQL

El schema se ha dividido en scripts separados para facilitar su ejecución, revisión y mantenimiento.

La división definida es la siguiente:

| Script                                     | Contenido principal                                       |
| ------------------------------------------ | --------------------------------------------------------- |
| `00_foundation.sql`                        | Extensiones, schema, tipos enumerados y funciones comunes |
| `01_governance.sql`                        | Tablas de fuentes, ejecuciones y artefactos raw           |
| `02_geo_reference.sql`                     | Tablas geográficas oficiales de distritos y barrios       |
| `03_core_places.sql`                       | Núcleo de locales, referencias fuente y reseñas           |
| `04_classification_and_geo_assignment.sql` | Categorías, clasificación y asignación geográfica         |
| `05_validation.sql`                        | Incidencias de validación y calidad                       |

Esta separación permite ejecutar el modelo por bloques y mantener una dependencia clara entre las partes del schema.

---

## 3. Extensiones utilizadas

El script base activa las extensiones necesarias para el funcionamiento del modelo.

### 3.1. PostGIS

Se utiliza para soportar tipos y operaciones geoespaciales.

Permite almacenar:

* puntos de locales
* polígonos/multipolígonos de barrios y distritos
* centroides
* índices espaciales
* cálculos de área y operaciones de intersección

### 3.2. pgcrypto

Se utiliza para generar UUIDs mediante `gen_random_uuid()` y para crear hashes SHA-256 en procesos técnicos.

### 3.3. pg_trgm

Se utiliza para mejorar búsquedas y comparaciones textuales aproximadas, especialmente sobre nombres de locales y referencias fuente.

Esto será útil para matching, deduplicación y normalización.

---

## 4. Convenciones generales del schema

El modelo sigue una serie de convenciones comunes.

### 4.1. Nombres en snake_case

Todas las tablas, columnas, constraints e índices siguen nomenclatura `snake_case`.

Ejemplos:

* `place_source_ref`
* `source_system_id`
* `created_at`
* `updated_at`

### 4.2. Identificadores UUID

Las claves primarias principales utilizan `UUID`.

Esto evita depender de identificadores externos y permite generar IDs internos estables e independientes de la fuente.

### 4.3. Timestamps de auditoría

La mayoría de entidades incluyen:

* `created_at`
* `updated_at`

Además, se define una función común `set_updated_at()` para actualizar automáticamente `updated_at` antes de cada modificación.

### 4.4. Uso de booleanos de estado

Varias entidades utilizan campos como:

* `is_active`
* `is_current`
* `is_available`
* `is_deleted_in_source`
* `is_manually_verified`

Esto permite controlar vigencia, disponibilidad, estado fuente y revisión manual sin eliminar registros físicamente.

### 4.5. Uso de constraints

El modelo incorpora constraints para proteger la calidad mínima del dato:

* campos no vacíos
* rangos de puntuaciones
* rangos de coordenadas
* fechas coherentes
* hashes con formato válido
* geometrías no vacías y válidas

### 4.6. Uso de índices especializados

Se han definido índices para optimizar:

* joins por claves foráneas
* búsquedas por estado
* consultas temporales
* matching textual
* operaciones espaciales

Tipos de índice utilizados:

* B-tree
* GIST
* GIN con trigramas
* GIN para full text search simple

---

## 5. Tipos enumerados

El modelo define varios tipos enumerados para limitar valores de columnas críticas.

Entre ellos:

* `source_type_enum`
* `auth_type_enum`
* `refresh_mode_enum`
* `run_type_enum`
* `run_trigger_enum`
* `run_status_enum`
* `asset_type_enum`
* `retention_class_enum`
* `assignment_method_enum`
* `validation_issue_type_enum`
* `validation_severity_enum`
* `validation_status_enum`

Estos enums ayudan a evitar valores inconsistentes y documentan explícitamente los estados soportados por el sistema.

---

## 6. Bloque de gobierno y trazabilidad

Este bloque se crea en `01_governance.sql`.

Incluye:

* `source_system`
* `source_run`
* `raw_asset`

### 6.1. `source_system`

Representa las fuentes reconocidas por el sistema.

Ejemplos:

* Google Places
* OSM / Overpass
* Sevilla Geo
* Yelp Open Dataset

Campos destacados:

* `source_system_id`
* `source_code`
* `source_name`
* `source_type`
* `auth_type`
* `refresh_mode_default`
* `supports_incremental`
* `is_active`

Decisión clave:

> Toda fuente debe estar registrada antes de ser utilizada por el pipeline.

### 6.2. `source_run`

Representa una ejecución concreta del pipeline sobre una fuente.

Campos destacados:

* `source_run_id`
* `run_code`
* `source_system_id`
* `run_type`
* `trigger_type`
* `status`
* `started_at`
* `finished_at`
* contadores de registros
* contadores de errores y avisos

Decisión clave:

> No debe existir ingesta silenciosa. Toda ejecución relevante debe quedar registrada.

### 6.3. `raw_asset`

Representa un artefacto raw generado o descargado en una ejecución.

Campos destacados:

* `raw_asset_id`
* `asset_code`
* `source_system_id`
* `source_run_id`
* `storage_path`
* `file_format`
* `checksum_sha256`
* `is_available`

Decisión clave:

> El raw debe ser trazable, verificable y considerado inmutable.

---

## 7. Bloque geográfico

Este bloque se crea en `02_geo_reference.sql`.

Incluye:

* `district`
* `neighborhood`

### 7.1. `district`

Representa un distrito oficial de Sevilla.

Campos destacados:

* `district_id`
* `official_code`
* `official_name`
* `normalized_name`
* `geometry`
* `centroid_point`
* `area_m2`
* `source_version`
* `is_active`

La geometría se almacena como:

```sql
GEOMETRY(MultiPolygon, 4326)
```

### 7.2. `neighborhood`

Representa un barrio oficial de Sevilla.

Campos destacados:

* `neighborhood_id`
* `district_id`
* `official_code`
* `official_name`
* `normalized_name`
* `geometry`
* `centroid_point`
* `area_m2`
* `source_version`
* `is_active`

Decisión clave:

> El barrio es el nivel geográfico principal de análisis, pero no se almacena directamente dentro de `place`.

### 7.3. Triggers geográficos

Se define una función para derivar automáticamente:

* `centroid_point`
* `area_m2`

Esto evita mantener manualmente campos derivados de la geometría.

---

## 8. Bloque núcleo de negocio

Este bloque se crea en `03_core_places.sql`.

Incluye:

* `place`
* `place_source_ref`
* `review`

### 8.1. `place`

Representa el local canónico interno.

Campos destacados:

* `place_id`
* `canonical_name`
* `normalized_name`
* `display_name`
* `address_text`
* `geom_point`
* `latitude`
* `longitude`
* `website_url`
* `phone_number`
* `place_confidence`
* `is_active`

La geometría se almacena como:

```sql
GEOMETRY(Point, 4326)
```

Decisión clave:

> `place` no contiene IDs externos ni categorías raw ni barrio directo.

### 8.2. `place_source_ref`

Representa la aparición de un `place` en una fuente concreta.

Campos destacados:

* `place_source_ref_id`
* `place_id`
* `source_system_id`
* `source_record_id`
* `source_name_raw`
* `source_address_raw`
* `source_geom_point`
* `source_rating`
* `source_review_count`
* `match_method`
* `match_confidence`
* `first_seen_run_id`
* `last_seen_run_id`
* `is_current`
* `is_deleted_in_source`

Constraint clave:

```sql
UNIQUE (source_system_id, source_entity_type, source_record_id)
```

Decisión clave:

> La integración multisource se resuelve en `place_source_ref`, no en `place`.

### 8.3. `review`

Representa una reseña textual individual.

Campos destacados:

* `review_id`
* `place_id`
* `place_source_ref_id`
* `source_system_id`
* `source_review_id`
* `rating_value`
* `review_text_raw`
* `review_text_normalized`
* `review_language`
* `review_created_at`
* `author_name_hash`
* `is_active`
* `is_deleted_in_source`

Decisión clave:

> Las reseñas son source-bound y no se fusionan automáticamente entre fuentes.

### 8.4. Triggers técnicos

El bloque define funciones para:

* construir `geom_point` desde latitud/longitud
* derivar latitud/longitud desde `geom_point`
* calcular longitud de texto de reseñas
* calcular hash del autor de la reseña

---

## 9. Bloque de clasificación y asignación geográfica

Este bloque se crea en `04_classification_and_geo_assignment.sql`.

Incluye:

* `category`
* `place_category`
* `place_neighborhood_assignment`

### 9.1. `category`

Representa la taxonomía interna de categorías.

Campos destacados:

* `category_id`
* `category_code`
* `category_name`
* `normalized_name`
* `parent_category_id`
* `category_level`
* `is_food_related`
* `is_active`

Decisión clave:

> La categoría final del sistema es interna y no depende directamente de la nomenclatura raw de una fuente.

### 9.2. `place_category`

Representa la relación entre un local y una categoría.

Campos destacados:

* `place_category_id`
* `place_id`
* `category_id`
* `source_system_id`
* `assignment_method`
* `is_primary`
* `assignment_confidence`
* `is_active`

Decisión clave:

> Un local puede tener varias categorías, pero solo una categoría principal activa.

### 9.3. `place_neighborhood_assignment`

Representa la asignación de un local a un barrio.

Campos destacados:

* `place_neighborhood_assignment_id`
* `place_id`
* `neighborhood_id`
* `district_id`
* `assignment_method`
* `assignment_confidence`
* `source_geometry_used`
* `distance_to_centroid_m`
* `is_current`
* `is_manually_verified`
* `valid_from`
* `valid_to`

Decisión clave:

> La asignación geográfica es derivada, trazable y puede cambiar con el tiempo.

Constraint relevante:

```sql
UNIQUE parcial sobre place_id WHERE is_current = TRUE
```

Esto garantiza una única asignación vigente por local.

---

## 10. Bloque de calidad

Este bloque se crea en `05_validation.sql`.

Incluye:

* `validation_issue`

### 10.1. `validation_issue`

Representa incidencias de calidad, validación o consistencia detectadas por el sistema.

Campos destacados:

* `validation_issue_id`
* `source_run_id`
* `raw_asset_id`
* `entity_type`
* `entity_id`
* `issue_code`
* `issue_type`
* `severity`
* `message`
* `field_name`
* `received_value`
* `expected_rule`
* `status`
* `detected_at`
* `resolved_at`

Decisión clave:

> La relación con la entidad afectada es polimórfica y se representa mediante `entity_type` + `entity_id`.

Esto permite registrar incidencias sobre distintas entidades sin crear una FK específica para cada una.

---

## 11. Índices principales

El schema incorpora índices para mejorar el rendimiento en varios tipos de consulta.

### 11.1. Índices relacionales

Se crean índices sobre claves foráneas y campos de estado.

Ejemplos:

* `source_system_id`
* `source_run_id`
* `place_id`
* `category_id`
* `neighborhood_id`
* `is_active`
* `is_current`

### 11.2. Índices espaciales

Se utilizan índices `GIST` sobre geometrías.

Ejemplos:

* `place.geom_point`
* `district.geometry`
* `neighborhood.geometry`
* `place_source_ref.source_geom_point`

Estos índices son esenciales para consultas espaciales y asignaciones por barrio.

### 11.3. Índices textuales

Se utilizan índices `GIN` con trigramas sobre nombres.

Ejemplos:

* `place.normalized_name`
* `place.canonical_name`
* `place_source_ref.source_name_raw`

Estos índices ayudan en procesos de matching y deduplicación.

### 11.4. Full text search básico

Se define un índice `GIN` sobre el texto raw de reseñas mediante `to_tsvector('simple', review_text_raw)`.

Esto permite consultas textuales iniciales sin necesidad de una infraestructura externa.

---

## 12. Triggers y funciones

El schema incorpora triggers para mantener campos derivados y timestamps.

### 12.1. `set_updated_at()`

Actualiza automáticamente `updated_at` antes de cada modificación.

### 12.2. `set_geo_derived_fields()`

Calcula automáticamente:

* centroide
* área en metros cuadrados

para entidades geográficas.

### 12.3. `set_place_geo_fields()`

Mantiene sincronizados:

* `geom_point`
* `latitude`
* `longitude`

para `place`.

### 12.4. `set_place_source_ref_geo_fields()`

Mantiene sincronizados:

* `source_geom_point`
* `source_latitude`
* `source_longitude`

para `place_source_ref`.

### 12.5. `set_review_derived_fields()`

Calcula campos técnicos de reseñas, como:

* longitud del texto
* hash del autor

---

## 13. Constraints de calidad

El modelo incluye constraints para prevenir datos inválidos desde la propia base.

Ejemplos:

* nombres obligatorios no vacíos
* coordenadas en rango válido
* puntuaciones entre 0 y 5
* confianzas entre 0 y 1
* contadores no negativos
* fechas coherentes
* hashes SHA-256 válidos
* geometrías no vacías y válidas

Estos controles no sustituyen la validación del pipeline, pero proporcionan una capa de seguridad adicional.

---

## 14. Relación con las verticales ya implementadas

El schema ya está preparado para soportar las verticales desarrolladas hasta el momento.

### 14.1. Vertical Sevilla Geo

La vertical de Sevilla Geo alimenta principalmente:

* `source_system`
* `source_run`
* `raw_asset`
* `district`
* `neighborhood`
* `validation_issue`

Esta vertical proporciona la base territorial oficial del sistema.

### 14.2. Vertical OSM / Overpass

La vertical de Overpass alimenta principalmente:

* `source_system`
* `source_run`
* `raw_asset`
* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`
* `validation_issue`

Esta vertical permite incorporar puntos de interés gastronómicos abiertos y asignarlos geográficamente.

---

## 15. Decisiones de diseño destacadas

Las principales decisiones implementadas en el schema son:

* usar `UUID` como clave primaria principal
* separar `place` y `place_source_ref`
* tratar `review` como entidad dependiente de fuente
* modelar barrios y distritos como referencia oficial
* separar la asignación geográfica en `place_neighborhood_assignment`
* separar categoría y asignación de categoría
* registrar fuentes, ejecuciones y artefactos raw
* estructurar incidencias de calidad en `validation_issue`
* usar PostGIS para geometría
* usar índices espaciales y textuales
* mantener campos derivados mediante triggers

---

## 16. Estado actual del schema

El schema principal ya se encuentra creado en PostgreSQL/PostGIS y ha sido utilizado como base para las primeras verticales del proyecto.

En este momento, el modelo permite:

* registrar fuentes y ejecuciones
* almacenar artefactos raw
* cargar geografía oficial
* integrar puntos de interés gastronómicos
* clasificar locales
* asignar locales a barrios
* registrar incidencias de calidad

Quedan para fases posteriores las capas analíticas avanzadas, como detección de platos, sentimiento, embeddings y ranking.

---

## 17. Conclusión

El esquema de base de datos de Hidden Gems proporciona una base robusta y extensible para el pipeline de adquisición y procesamiento.

Su diseño prioriza la trazabilidad, la separación de responsabilidades, la integridad geográfica y la capacidad de evolución.

Gracias a esta estructura, el proyecto puede seguir avanzando hacia nuevas verticales de datos, normalización avanzada, control de calidad y futuras capas de inteligencia analítica sin tener que rediseñar la base desde cero.

```

