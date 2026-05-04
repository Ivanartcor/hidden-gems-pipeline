# 25. Catálogo de entidades: gobierno y trazabilidad

## 1. Introducción

Este documento describe las entidades responsables del **gobierno técnico y la trazabilidad** dentro del modelo de datos de Hidden Gems.

El proyecto no se limita a almacenar locales, reseñas o geometrías. También necesita registrar de forma controlada:

- de qué fuente procede cada dato
- cuándo se ejecutó una ingesta
- qué archivos raw se generaron
- cuántos registros se extrajeron
- qué errores o advertencias aparecieron
- qué artefactos permiten reproducir o auditar el proceso

Las entidades incluidas en este catálogo son:

- `source_system`
- `source_run`
- `raw_asset`

Estas entidades convierten el pipeline en un sistema trazable y auditable, no en una colección de scripts aislados.

---

## 2. Visión general del bloque de gobierno y trazabilidad

El bloque se organiza de la siguiente manera:

```text
source_system
└── source_run
    └── raw_asset
````

La interpretación es:

* `source_system` identifica la fuente.
* `source_run` identifica una ejecución del pipeline sobre esa fuente.
* `raw_asset` identifica los artefactos raw generados o descargados durante esa ejecución.

---

## 3. Decisiones principales del bloque

## 3.1. Toda fuente debe estar registrada

No se deben usar nombres de fuente dispersos o hardcodeados en distintos puntos del sistema.

Cada fuente debe existir en `source_system` antes de ser utilizada por el pipeline.

---

## 3.2. No debe existir ingesta silenciosa

Toda ejecución relevante debe quedar registrada en `source_run`.

Esto permite saber cuándo se ejecutó el pipeline, con qué fuente, con qué tipo de carga y con qué resultado.

---

## 3.3. El raw debe ser auditable

Cada archivo o artefacto raw importante debe registrarse en `raw_asset`.

El objetivo es que el sistema pueda responder:

* dónde está el raw
* a qué ejecución pertenece
* qué formato tiene
* qué checksum lo identifica
* si sigue disponible

---

## 4. Entidad `source_system`

## 4.1. Propósito

`source_system` representa una **fuente de datos reconocida por el sistema**.

No representa una ejecución ni un archivo concreto, sino el origen lógico de los datos.

Ejemplos:

* Google Places
* OSM / Overpass
* Sevilla Geo
* Yelp Open Dataset

---

## 4.2. Naturaleza de la entidad

| Propiedad           | Valor                 |
| ------------------- | --------------------- |
| Tipo                | Catálogo técnico      |
| Nivel               | Fuente de datos       |
| Origen              | Configuración interna |
| Persistencia        | Sí                    |
| Entidad de gobierno | Sí                    |

---

## 4.3. Campos principales

| Campo                  | Descripción                                |
| ---------------------- | ------------------------------------------ |
| `source_system_id`     | Identificador interno de la fuente         |
| `source_code`          | Código técnico único de la fuente          |
| `source_name`          | Nombre legible de la fuente                |
| `source_type`          | Tipo de fuente                             |
| `description`          | Descripción funcional                      |
| `base_url`             | URL base si aplica                         |
| `auth_type`            | Tipo de autenticación                      |
| `data_format_default`  | Formato habitual de respuesta              |
| `refresh_mode_default` | Modo típico de actualización               |
| `supports_incremental` | Indica si admite actualización incremental |
| `is_active`            | Indica si la fuente está habilitada        |
| `notes`                | Observaciones                              |
| `created_at`           | Fecha de creación                          |
| `updated_at`           | Fecha de actualización                     |

---

## 4.4. Valores habituales

Ejemplos de `source_code` definidos o esperados:

* `google_places`
* `osm_overpass`
* `sevilla_geo`
* `yelp_open_dataset`

Ejemplos de `source_type`:

* `api`
* `bulk_dataset`
* `geo_dataset`
* `manual_import`

---

## 4.5. Reglas de negocio

* Toda fuente debe estar registrada antes de usarse.
* `source_code` debe ser único.
* `source_code` debe ser estable.
* Una fuente puede desactivarse sin eliminarse.
* La configuración específica de la fuente debe apoyarse en esta entidad.

---

## 4.6. Qué no debe guardar `source_system`

No debe guardar:

* ejecuciones concretas
* archivos raw concretos
* registros de negocio
* métricas de una ejecución específica
* errores de validación concretos

Esto pertenece a otras entidades.

---

## 4.7. Relaciones

| Relación                             | Cardinalidad | Descripción                                            |
| ------------------------------------ | ------------ | ------------------------------------------------------ |
| `source_system` → `source_run`       | 1:N          | Una fuente puede tener muchas ejecuciones              |
| `source_system` → `raw_asset`        | 1:N          | Una fuente puede generar muchos assets raw             |
| `source_system` → `place_source_ref` | 1:N          | Una fuente puede aportar muchas referencias de locales |
| `source_system` → `review`           | 1:N          | Una fuente puede aportar muchas reseñas                |
| `source_system` → `place_category`   | 1:N opcional | Una fuente puede informar asignaciones de categoría    |

---

## 4.8. Validaciones relevantes

* `source_code` es obligatorio.
* `source_code` debe seguir formato `snake_case`.
* `source_name` es obligatorio.
* `source_type` es obligatorio.
* `is_active` es obligatorio.

---

## 5. Entidad `source_run`

## 5.1. Propósito

`source_run` representa una **ejecución concreta del pipeline** sobre una fuente.

Cada vez que el sistema realiza una ingesta, importación, actualización o carga relevante, debe quedar registrada una fila en esta entidad.

---

## 5.2. Naturaleza de la entidad

| Propiedad         | Valor                  |
| ----------------- | ---------------------- |
| Tipo              | Trazabilidad operativa |
| Nivel             | Ejecución técnica      |
| Origen            | Sistema interno        |
| Persistencia      | Sí                     |
| Entidad histórica | Sí                     |

---

## 5.3. Campos principales

| Campo                     | Descripción                           |
| ------------------------- | ------------------------------------- |
| `source_run_id`           | Identificador interno de la ejecución |
| `run_code`                | Código legible y único del run        |
| `source_system_id`        | FK a la fuente ejecutada              |
| `run_type`                | Tipo de ejecución                     |
| `trigger_type`            | Forma en la que se lanzó              |
| `status`                  | Estado del run                        |
| `started_at`              | Inicio de ejecución                   |
| `finished_at`             | Fin de ejecución                      |
| `duration_seconds`        | Duración en segundos                  |
| `records_extracted_count` | Registros extraídos                   |
| `records_staged_count`    | Registros aceptados a staging         |
| `records_rejected_count`  | Registros rechazados                  |
| `raw_asset_count`         | Número de assets generados            |
| `error_count`             | Número de errores                     |
| `warning_count`           | Número de advertencias                |
| `config_snapshot_hash`    | Hash de configuración usada           |
| `request_summary`         | Resumen de parámetros de consulta     |
| `notes`                   | Observaciones                         |
| `parent_run_id`           | Run padre si es retry o derivado      |
| `created_at`              | Fecha de creación                     |
| `updated_at`              | Fecha de actualización                |

---

## 5.4. Tipos de ejecución

Valores previstos para `run_type`:

* `seed`
* `incremental`
* `full_refresh`
* `backfill`
* `manual_import`

Estos valores permiten diferenciar una carga inicial de una carga incremental o una recarga completa.

---

## 5.5. Tipos de disparador

Valores previstos para `trigger_type`:

* `manual`
* `scheduled`
* `cli`
* `api`
* `retry`

Esto permite saber cómo se inició la ejecución.

---

## 5.6. Estados de ejecución

Valores previstos para `status`:

* `pending`
* `running`
* `completed`
* `completed_with_warnings`
* `failed`
* `cancelled`

Estos estados permiten seguir el ciclo de vida del run.

---

## 5.7. Reglas de negocio

* Toda ejecución relevante debe registrarse.
* Un `source_run` pertenece a una única fuente.
* Un run finalizado debe tratarse como histórico.
* Un retry puede referenciar un run anterior mediante `parent_run_id`.
* Los contadores deben reflejar el resultado real de la ejecución.
* Si el estado es final, debería existir `finished_at`.

---

## 5.8. Qué no debe guardar `source_run`

No debe guardar:

* payloads completos
* datos de negocio
* geometrías
* textos de reseñas
* archivos raw embebidos

Eso pertenece a `raw_asset` o a las tablas de dominio.

---

## 5.9. Relaciones

| Relación                          | Cardinalidad | Descripción                               |
| --------------------------------- | ------------ | ----------------------------------------- |
| `source_run` → `source_system`    | N:1          | Cada run pertenece a una fuente           |
| `source_run` → `raw_asset`        | 1:N          | Un run puede generar varios assets        |
| `source_run` → `validation_issue` | 1:N          | Un run puede generar incidencias          |
| `source_run` → `source_run`       | N:1 opcional | Un run puede ser retry o derivado de otro |

---

## 5.10. Validaciones relevantes

* `run_code` es obligatorio y único.
* `source_system_id` es obligatorio.
* `run_type` es obligatorio.
* `trigger_type` es obligatorio.
* `status` es obligatorio.
* Los contadores deben ser mayores o iguales que 0.
* `finished_at` no debe ser anterior a `started_at`.

---

## 5.11. Papel en el pipeline

`source_run` es la columna vertebral operativa del pipeline.

Cada vertical de adquisición debe crear y actualizar un run:

1. se crea el run en estado `pending` o `running`
2. se ejecuta la adquisición
3. se generan assets raw
4. se actualizan contadores
5. se marca el run como completado, completado con avisos o fallido

---

## 6. Entidad `raw_asset`

## 6.1. Propósito

`raw_asset` representa un **artefacto raw almacenado** durante una ejecución del pipeline.

Puede ser:

* una respuesta JSON de API
* un fichero GeoJSON
* un archivo comprimido
* un resultado de consulta Overpass
* un snapshot de dataset externo

---

## 6.2. Naturaleza de la entidad

| Propiedad         | Valor               |
| ----------------- | ------------------- |
| Tipo              | Trazabilidad física |
| Nivel             | Artefacto raw       |
| Origen            | Sistema interno     |
| Persistencia      | Sí                  |
| Contenido mutable | No                  |

---

## 6.3. Campos principales

| Campo                    | Descripción                          |
| ------------------------ | ------------------------------------ |
| `raw_asset_id`           | Identificador interno del asset      |
| `asset_code`             | Código único y legible del asset     |
| `source_system_id`       | FK a la fuente                       |
| `source_run_id`          | FK al run que lo generó              |
| `asset_name`             | Nombre lógico del asset              |
| `asset_type`             | Tipo de asset                        |
| `storage_path`           | Ruta o URI de almacenamiento         |
| `file_format`            | Formato del archivo                  |
| `compression_type`       | Tipo de compresión                   |
| `mime_type`              | Tipo MIME si aplica                  |
| `file_size_bytes`        | Tamaño en bytes                      |
| `record_count_estimated` | Número estimado de registros         |
| `checksum_sha256`        | Hash SHA-256 del contenido           |
| `query_name`             | Nombre de query o endpoint lógico    |
| `request_signature_hash` | Hash de parámetros de solicitud      |
| `content_created_at`     | Momento de creación del contenido    |
| `retention_class`        | Política de retención                |
| `is_available`           | Indica si el archivo sigue accesible |
| `notes`                  | Observaciones                        |
| `created_at`             | Fecha de creación                    |
| `updated_at`             | Fecha de actualización               |

---

## 6.4. Tipos de asset

Valores previstos para `asset_type`:

* `api_response`
* `bulk_file`
* `geo_file`
* `query_result`
* `raw_export`

Estos tipos permiten distinguir artefactos procedentes de APIs, ficheros geográficos, datasets bulk o exportaciones.

---

## 6.5. Política de raw inmutable

El contenido raw se considera inmutable.

Esto significa que:

* no se debe modificar un raw ya almacenado
* si se vuelve a descargar, se registra como nuevo asset
* si se reprocesa, se genera salida en otra capa
* si el archivo deja de estar disponible, se marca con `is_available = false`

---

## 6.6. Reglas de negocio

* Todo artefacto raw relevante debe registrarse.
* Todo `raw_asset` pertenece a un `source_run`.
* Todo `raw_asset` pertenece a un `source_system`.
* Debe existir una ruta o URI de almacenamiento.
* El checksum permite verificar integridad.
* La entidad puede permanecer aunque el archivo físico no esté disponible.

---

## 6.7. Qué no debe guardar `raw_asset`

No debe guardar:

* datos normalizados
* entidades de negocio
* resultados analíticos
* resultados NLP
* métricas agregadas finales

Su función es documentar el artefacto raw, no interpretarlo.

---

## 6.8. Relaciones

| Relación                         | Cardinalidad | Descripción                                    |
| -------------------------------- | ------------ | ---------------------------------------------- |
| `raw_asset` → `source_system`    | N:1          | Cada asset procede de una fuente               |
| `raw_asset` → `source_run`       | N:1          | Cada asset pertenece a una ejecución           |
| `raw_asset` → `place_source_ref` | 1:N opcional | Puede servir como origen de referencias fuente |
| `raw_asset` → `validation_issue` | 1:N opcional | Puede estar asociado a incidencias             |

---

## 6.9. Validaciones relevantes

* `asset_code` es obligatorio y único.
* `source_system_id` es obligatorio.
* `source_run_id` es obligatorio.
* `storage_path` es obligatorio.
* `file_format` es obligatorio.
* `file_size_bytes`, si existe, debe ser mayor o igual que 0.
* `record_count_estimated`, si existe, debe ser mayor o igual que 0.
* `checksum_sha256`, si existe, debe tener formato SHA-256.

---

## 6.10. Papel en verticales actuales

### Sevilla Geo

La vertical Sevilla Geo genera assets como:

* GeoJSON original de barrios
* GeoJSON original de distritos
* artefactos de perfil o QA

### OSM / Overpass

La vertical OSM / Overpass genera assets como:

* consulta OverpassQL
* respuesta JSON raw
* artefactos QA
* perfiles de ejecución

---

## 7. Decisiones generales del bloque de gobierno

Las decisiones principales son:

1. Toda fuente debe estar registrada en `source_system`.
2. Toda ejecución debe registrarse en `source_run`.
3. Todo artefacto raw relevante debe registrarse en `raw_asset`.
4. El raw es inmutable.
5. Los contadores de ejecución se almacenan en el run.
6. La disponibilidad física del asset se controla con `is_available`.
7. La integridad del asset puede verificarse con checksum.
8. Los errores estructurados se registran aparte en `validation_issue`.

---

## 8. Conclusión

El bloque de gobierno y trazabilidad proporciona la base operativa del pipeline.

Gracias a `source_system`, `source_run` y `raw_asset`, el sistema puede reconstruir el recorrido del dato desde la fuente original hasta su integración en el modelo.

Este bloque es fundamental para que Hidden Gems no sea solo una base de datos, sino un sistema de adquisición reproducible, auditable y mantenible.

