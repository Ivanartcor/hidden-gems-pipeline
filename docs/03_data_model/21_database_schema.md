# 21. Esquema de base de datos

## 1. Introducción

El esquema de base de datos de Hidden Gems se ha implementado sobre **PostgreSQL + PostGIS**.

La elección de PostgreSQL responde a la necesidad de contar con una base relacional sólida, con soporte para integridad referencial, constraints, índices avanzados y consultas analíticas. PostGIS se incorpora porque el proyecto necesita trabajar con geometrías oficiales, coordenadas de locales y asignación espacial de puntos a barrios.

El esquema principal se denomina:

```sql
hidden_gems
```

Dentro de este esquema se agrupan todas las tablas del modelo principal, incluyendo el core canónico, la geografía, la trazabilidad, la calidad, las reseñas, la capa IA y las vistas de consulta.

---

## 2. Organización de scripts SQL

El schema se ha dividido en scripts separados para facilitar su ejecución, revisión y mantenimiento.

La división definida es la siguiente:

| Script | Contenido principal |
|---|---|
| `00_foundation.sql` | Extensiones, schema, tipos enumerados y funciones comunes |
| `01_governance.sql` | Tablas de fuentes, ejecuciones y artefactos raw |
| `02_geo_reference.sql` | Tablas geográficas oficiales de distritos y barrios |
| `03_core_places.sql` | Núcleo de locales, referencias fuente y reseñas |
| `04_classification_and_geo_assignment.sql` | Categorías, clasificación y asignación geográfica |
| `05_validation.sql` | Incidencias de validación y calidad |
| `06_review_enrichment.sql` | Enriquecimiento de `review` para trazabilidad y NLP |
| `07_ai_module.sql` | Tablas persistentes del módulo IA y ranking |
| `08_ai_views.sql` | Vistas de consulta para explotación del ranking IA |

Esta separación permite ejecutar el modelo por bloques y mantener una dependencia clara entre las partes del schema.

---

## 3. Extensiones utilizadas

El script base activa las extensiones necesarias para el funcionamiento del modelo.

### 3.1. PostGIS

Se utiliza para soportar tipos y operaciones geoespaciales.

Permite almacenar:

- puntos de locales;
- polígonos/multipolígonos de barrios y distritos;
- centroides;
- índices espaciales;
- cálculos de área y operaciones de intersección.

### 3.2. pgcrypto

Se utiliza para generar UUIDs mediante `gen_random_uuid()` y para crear hashes SHA-256 en procesos técnicos.

### 3.3. pg_trgm

Se utiliza para mejorar búsquedas y comparaciones textuales aproximadas, especialmente sobre nombres de locales, referencias fuente, platos y aliases.

Esto es útil para matching, deduplicación, normalización y revisión de catálogo.

---

## 4. Convenciones generales del schema

El modelo sigue una serie de convenciones comunes.

### 4.1. Nombres en snake_case

Todas las tablas, columnas, constraints e índices siguen nomenclatura `snake_case`.

Ejemplos:

- `place_source_ref`;
- `source_system_id`;
- `dish_place_signal`;
- `hidden_gem_candidate`;
- `created_at`;
- `updated_at`.

### 4.2. Identificadores UUID

Las claves primarias principales utilizan `UUID`.

Esto evita depender de identificadores externos y permite generar IDs internos estables e independientes de la fuente.

### 4.3. Timestamps de auditoría

La mayoría de entidades incluyen:

- `created_at`;
- `updated_at`.

Además, se define una función común `set_updated_at()` para actualizar automáticamente `updated_at` antes de cada modificación.

### 4.4. Uso de booleanos de estado

Varias entidades utilizan campos como:

- `is_active`;
- `is_current`;
- `is_available`;
- `is_deleted_in_source`;
- `is_manually_verified`;
- `is_training_eligible`;
- `is_operational_review`;
- `is_rankable_candidate`;
- `is_selected`;
- `is_production_ready`.

Esto permite controlar vigencia, disponibilidad, estado fuente, revisión manual, elegibilidad para IA y preparación para producción sin eliminar registros físicamente.

### 4.5. Uso de constraints

El modelo incorpora constraints para proteger la calidad mínima del dato:

- campos no vacíos;
- rangos de puntuaciones;
- rangos de coordenadas;
- fechas coherentes;
- hashes con formato válido;
- geometrías no vacías y válidas;
- scores entre 0 y 100;
- confianzas y ratios entre 0 y 1;
- contadores no negativos;
- valores controlados para tiers, scopes y estados.

### 4.6. Uso de índices especializados

Se han definido índices para optimizar:

- joins por claves foráneas;
- búsquedas por estado;
- consultas temporales;
- matching textual;
- operaciones espaciales;
- consulta de señales IA;
- rankings por score.

Tipos de índice utilizados:

- B-tree;
- GIST;
- GIN con trigramas;
- GIN para full text search simple;
- GIN sobre campos JSONB cuando es útil.

---

## 5. Tipos enumerados y checks

El modelo define varios tipos enumerados para limitar valores de columnas críticas en las capas más estables.

Entre ellos:

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

Para la capa IA se ha optado principalmente por `VARCHAR + CHECK`, en lugar de crear muchos enums nuevos. Esta decisión permite evolucionar modelos, tipos de ranking, estados de revisión y métodos híbridos sin hacer migraciones demasiado rígidas en una fase todavía experimental.

---

## 6. Bloque de gobierno y trazabilidad

Este bloque se crea principalmente en `01_governance.sql`.

Incluye:

- `source_system`;
- `source_run`;
- `raw_asset`.

### 6.1. `source_system`

Representa las fuentes reconocidas por el sistema.

Ejemplos:

- Google Places;
- OSM / Overpass;
- Sevilla Geo;
- Yelp Open Dataset.

Decisión clave:

> Toda fuente debe estar registrada antes de ser utilizada por el pipeline.

### 6.2. `source_run`

Representa una ejecución concreta del pipeline sobre una fuente.

Decisión clave:

> No debe existir ingesta silenciosa. Toda ejecución relevante debe quedar registrada.

### 6.3. `raw_asset`

Representa un artefacto raw generado o descargado en una ejecución.

Decisión clave:

> El raw debe ser trazable, verificable y considerado inmutable.

---

## 7. Bloque geográfico

Este bloque se crea en `02_geo_reference.sql`.

Incluye:

- `district`;
- `neighborhood`.

### 7.1. `district`

Representa un distrito oficial de Sevilla.

La geometría se almacena como:

```sql
GEOMETRY(MultiPolygon, 4326)
```

### 7.2. `neighborhood`

Representa un barrio oficial de Sevilla.

Decisión clave:

> El barrio es el nivel geográfico principal de análisis, pero no se almacena directamente dentro de `place`.

### 7.3. Triggers geográficos

Se define una función para derivar automáticamente:

- `centroid_point`;
- `area_m2`.

Esto evita mantener manualmente campos derivados de la geometría.

---

## 8. Bloque núcleo de negocio

Este bloque se crea en `03_core_places.sql`.

Incluye:

- `place`;
- `place_source_ref`;
- `review`.

### 8.1. `place`

Representa el local canónico interno.

La geometría se almacena como:

```sql
GEOMETRY(Point, 4326)
```

Decisión clave:

> `place` no contiene IDs externos ni categorías raw ni barrio directo.

### 8.2. `place_source_ref`

Representa la aparición de un `place` en una fuente concreta.

Constraint clave:

```sql
UNIQUE (source_system_id, source_entity_type, source_record_id)
```

Decisión clave:

> La integración multisource se resuelve en `place_source_ref`, no en `place`.

### 8.3. `review`

Representa una reseña textual individual.

Decisión clave:

> Las reseñas son source-bound y no se fusionan automáticamente entre fuentes.

### 8.4. Triggers técnicos

El bloque define funciones para:

- construir `geom_point` desde latitud/longitud;
- derivar latitud/longitud desde `geom_point`;
- calcular longitud de texto de reseñas;
- calcular hash del autor de la reseña.

---

## 9. Enriquecimiento de reviews para IA

Este bloque se crea en `06_review_enrichment.sql`.

Su objetivo es preparar `review` para funcionar como entrada del módulo IA y como entidad trazable dentro de procesos de NLP.

Campos añadidos o reforzados:

- `raw_asset_id`;
- `source_place_record_id`;
- `source_payload_hash`;
- `is_operational_review`;
- `is_training_eligible`.

Esta ampliación permite distinguir entre:

- reviews operativas procedentes de fuentes reales como Google Places;
- reviews importadas para corpus o entrenamiento, como Yelp Open Dataset;
- reviews elegibles para entrenamiento o procesamiento IA;
- reviews trazables hasta su raw original.

---

## 10. Bloque de clasificación y asignación geográfica

Este bloque se crea en `04_classification_and_geo_assignment.sql`.

Incluye:

- `category`;
- `place_category`;
- `place_neighborhood_assignment`.

### 10.1. `category`

Representa la taxonomía interna de categorías.

Decisión clave:

> La categoría final del sistema es interna y no depende directamente de la nomenclatura raw de una fuente.

### 10.2. `place_category`

Representa la relación entre un local y una categoría.

Decisión clave:

> Un local puede tener varias categorías, pero solo una categoría principal activa.

### 10.3. `place_neighborhood_assignment`

Representa la asignación de un local a un barrio.

Constraint relevante:

```sql
UNIQUE parcial sobre place_id WHERE is_current = TRUE
```

Esto garantiza una única asignación vigente por local.

---

## 11. Bloque de calidad

Este bloque se crea en `05_validation.sql`.

Incluye:

- `validation_issue`.

### 11.1. `validation_issue`

Representa incidencias de calidad, validación o consistencia detectadas por el sistema.

Decisión clave:

> La relación con la entidad afectada es polimórfica y se representa mediante `entity_type` + `entity_id`.

El DDL de la capa IA amplía los tipos admitidos para permitir registrar incidencias sobre entidades como:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

---

## 12. Bloque IA y ranking

Este bloque se crea en `07_ai_module.sql`.

Incluye:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

### 12.1. `ai_model_version`

Registra versiones de modelos, reglas, métodos híbridos, agregadores y rankings.

Ejemplos:

- `dish_ner_transformer_v1`;
- `dish_normalization_rule_based_v2`;
- `mention_sentiment_hybrid_v1_1`;
- `signal_aggregation_v1`;
- `hidden_gems_ranking_v1`.

### 12.2. `ai_pipeline_run`

Registra ejecuciones concretas del módulo IA.

No sustituye a `source_run`. `source_run` representa ingesta de fuente; `ai_pipeline_run` representa procesamiento derivado.

### 12.3. `dish`

Catálogo canónico de platos.

Ejemplos:

- `pizza`;
- `burger`;
- `sushi`;
- `tacos`;
- `fried chicken`.

### 12.4. `dish_alias`

Variantes textuales o aliases de un plato.

Ejemplos:

- `burger`;
- `burgers`;
- `cheeseburger`;
- `burger with bacon`.

### 12.5. `dish_mention`

Mención concreta de un plato dentro de una review.

Se relaciona con:

- `review`;
- `place`;
- `dish`;
- `dish_alias` cuando aplica;
- `ai_pipeline_run`;
- `ai_model_version`.

### 12.6. `dish_mention_sentiment`

Sentimiento calculado para una mención concreta.

Permite recalcular sentimiento con nuevos métodos sin duplicar la mención.

### 12.7. `dish_place_signal`

Agregación de señales por local y plato.

Equivale conceptualmente a:

```text
place + dish → señales agregadas
```

Incluye conteos, ratios, sentimiento ponderado, tiers de evidencia y flags de calidad.

### 12.8. `hidden_gem_candidate`

Resultado del ranking Hidden Gems.

Incluye score final, tier, explicación, componentes del score, penalizaciones, scope y estado de preparación para producción.

Para la integración actual de Yelp se usa:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 13. Vistas de consulta IA

Este bloque se crea en `08_ai_views.sql`.

Incluye vistas para explotar la capa IA sin tener que consultar directamente las tablas internas.

Vistas principales:

- `vw_ai_pipeline_run_summary`;
- `vw_ai_dish_place_signals`;
- `vw_ai_hidden_gem_candidate_detail`;
- `vw_ai_hidden_gems_yelp_top`;
- `vw_ai_hidden_gems_place_summary`;
- `vw_ai_hidden_gems_dish_summary`;
- `vw_ai_hidden_gems_city_summary`;
- `vw_ai_dish_mentions_with_sentiment`.

La vista principal para una demo rápida es:

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_yelp_top
LIMIT 20;
```

La vista principal para auditar menciones concretas es:

```sql
SELECT *
FROM hidden_gems.vw_ai_dish_mentions_with_sentiment
WHERE place_name = 'Sushi Ushi'
  AND dish_name = 'sushi'
ORDER BY sentiment_confidence DESC
LIMIT 25;
```

---

## 14. Índices principales

El schema incorpora índices para mejorar el rendimiento en varios tipos de consulta.

### 14.1. Índices relacionales

Se crean índices sobre claves foráneas y campos de estado.

Ejemplos:

- `source_system_id`;
- `source_run_id`;
- `place_id`;
- `category_id`;
- `neighborhood_id`;
- `dish_id`;
- `ai_pipeline_run_id`;
- `is_active`;
- `is_current`.

### 14.2. Índices espaciales

Se utilizan índices `GIST` sobre geometrías.

Ejemplos:

- `place.geom_point`;
- `district.geometry`;
- `neighborhood.geometry`;
- `place_source_ref.source_geom_point`.

Estos índices son esenciales para consultas espaciales y asignaciones por barrio.

### 14.3. Índices textuales

Se utilizan índices `GIN` con trigramas sobre nombres.

Ejemplos:

- `place.normalized_name`;
- `place.canonical_name`;
- `place_source_ref.source_name_raw`;
- `dish.normalized_name`;
- `dish_alias.alias_normalized`.

Estos índices ayudan en procesos de matching, deduplicación, normalización y revisión de catálogo.

### 14.4. Full text search básico

Se define un índice `GIN` sobre el texto raw de reseñas mediante `to_tsvector('simple', review_text_raw)`.

Esto permite consultas textuales iniciales sin necesidad de una infraestructura externa.

### 14.5. Índices de ranking

La capa IA incorpora índices orientados a consultas de explotación:

- candidatos por `ranking_scope`;
- candidatos seleccionados;
- score descendente;
- relación `place + dish`;
- señales rankeables;
- tiers de evidencia;
- relaciones con `dish_place_signal`.

---

## 15. Triggers y funciones

El schema incorpora triggers para mantener campos derivados y timestamps.

### 15.1. `set_updated_at()`

Actualiza automáticamente `updated_at` antes de cada modificación.

### 15.2. `set_geo_derived_fields()`

Calcula automáticamente:

- centroide;
- área en metros cuadrados.

### 15.3. `set_place_geo_fields()`

Mantiene sincronizados:

- `geom_point`;
- `latitude`;
- `longitude`.

### 15.4. `set_place_source_ref_geo_fields()`

Mantiene sincronizados:

- `source_geom_point`;
- `source_latitude`;
- `source_longitude`.

### 15.5. `set_review_derived_fields()`

Calcula campos técnicos de reseñas, como:

- longitud del texto;
- hash del autor.

### 15.6. Triggers de la capa IA

Las tablas IA incorporan triggers `updated_at` para mantener auditoría temporal homogénea:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

---

## 16. Constraints de calidad

El modelo incluye constraints para prevenir datos inválidos desde la propia base.

Ejemplos:

- nombres obligatorios no vacíos;
- coordenadas en rango válido;
- puntuaciones entre 0 y 5;
- confianzas entre 0 y 1;
- scores entre 0 y 100;
- contadores no negativos;
- fechas coherentes;
- hashes SHA-256 válidos;
- geometrías no vacías y válidas;
- sentiment labels controlados;
- ranking scopes controlados;
- tiers de evidencia y ranking controlados.

Estos controles no sustituyen la validación del pipeline, pero proporcionan una capa de seguridad adicional.

---

## 17. Relación con las verticales ya implementadas

El schema ya está preparado para soportar las verticales desarrolladas hasta el momento.

### 17.1. Vertical Sevilla Geo

La vertical de Sevilla Geo alimenta principalmente:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `district`;
- `neighborhood`;
- `validation_issue`.

Esta vertical proporciona la base territorial oficial del sistema.

### 17.2. Vertical OSM / Overpass

La vertical de Overpass alimenta principalmente:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`;
- `validation_issue`.

Esta vertical permite incorporar puntos de interés gastronómicos abiertos y asignarlos geográficamente.

### 17.3. Vertical Google Places

La vertical Google Places alimenta principalmente:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`;
- `validation_issue`.

Esta vertical aporta descubrimiento y enriquecimiento operativo de locales reales.

### 17.4. Vertical Google Places Reviews

La vertical Google Places Reviews alimenta principalmente:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `review`.

Las reviews de Google son la entrada natural para aplicar el módulo IA sobre datos operativos reales.

### 17.5. Vertical Yelp Open Dataset

Yelp Open Dataset tiene dos usos:

1. corpus experimental para entrenamiento y validación IA;
2. prototipo importado a PostgreSQL para validar la cadena completa `review → dish → sentiment → signals → ranking`.

Yelp se carga con `source_code = yelp_open_dataset` y los rankings generados se marcan como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 18. Decisiones de diseño destacadas

Las principales decisiones implementadas en el schema son:

- usar `UUID` como clave primaria principal;
- separar `place` y `place_source_ref`;
- tratar `review` como entidad dependiente de fuente;
- enriquecer `review` para NLP y trazabilidad;
- modelar barrios y distritos como referencia oficial;
- separar la asignación geográfica en `place_neighborhood_assignment`;
- separar categoría y asignación de categoría;
- registrar fuentes, ejecuciones y artefactos raw;
- estructurar incidencias de calidad en `validation_issue`;
- usar PostGIS para geometría;
- usar índices espaciales y textuales;
- mantener campos derivados mediante triggers;
- separar catálogo de platos, menciones y sentimiento;
- separar señales agregadas y ranking final;
- versionar modelos y ejecuciones IA;
- tratar Yelp como prototipo IA y no como ranking productivo de Sevilla;
- exponer vistas SQL para demo y auditoría.

---

## 19. Estado actual del schema

El schema principal ya se encuentra creado en PostgreSQL/PostGIS y ha sido utilizado como base para las verticales y para la integración IA.

En este momento, el modelo permite:

- registrar fuentes y ejecuciones;
- almacenar artefactos raw;
- cargar geografía oficial;
- integrar puntos de interés gastronómicos;
- clasificar locales;
- asignar locales a barrios;
- cargar y enriquecer reviews;
- registrar versiones y ejecuciones IA;
- almacenar catálogo de platos y aliases;
- almacenar menciones de platos detectadas en reviews;
- almacenar sentimiento por mención;
- agregar señales por local y plato;
- guardar candidatos Hidden Gems;
- consultar rankings y evidencias mediante vistas SQL.

Estado validado de la integración IA:

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |

La validación final confirma que no existen huérfanos en menciones, sentimientos, señales ni candidatos.

---

## 20. Conclusión

El esquema de base de datos de Hidden Gems proporciona una base robusta y extensible para el pipeline de adquisición, procesamiento e inteligencia aplicada.

Su diseño prioriza la trazabilidad, la separación de responsabilidades, la integridad geográfica, la calidad de los datos, el versionado de resultados IA y la capacidad de explotación analítica.

Gracias a esta estructura, el proyecto puede seguir avanzando hacia nuevas verticales de datos, adaptación a reviews reales de Sevilla, ranking por barrio, validación humana, API y futuras capas de producto sin rediseñar la base desde cero.
