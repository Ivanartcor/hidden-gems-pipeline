# 26. Catálogo de entidades: calidad

## 1. Introducción

Este documento describe el bloque de entidades encargado del **control de calidad, validación e incidencias** dentro del modelo de datos de Hidden Gems.

Un pipeline de datos no solo debe almacenar información. También debe ser capaz de registrar los problemas encontrados durante la adquisición, integración, validación y enriquecimiento.

La entidad incluida en este catálogo es:

- `validation_issue`

Esta entidad permite documentar de forma estructurada cualquier incidencia relevante detectada durante el funcionamiento del sistema.

---

## 2. Visión general del bloque de calidad

El bloque de calidad se conecta principalmente con las entidades de gobierno y trazabilidad.

```text
source_run
└── validation_issue

raw_asset
└── validation_issue
````

Además, `validation_issue` puede apuntar conceptualmente a cualquier entidad del sistema mediante:

* `entity_type`
* `entity_id`

Esto permite registrar incidencias sobre locales, reseñas, referencias fuente, categorías, geometrías, assets raw o cualquier otra entidad relevante.

---

## 3. Decisiones principales del bloque de calidad

## 3.1. Registrar incidencias estructuradas

Las incidencias relevantes no deben quedar únicamente en logs de texto.

Los logs son útiles para depuración, pero no son suficientes para explotación posterior, reporting o análisis de calidad.

Por eso el modelo incorpora `validation_issue` como entidad estructurada.

---

## 3.2. Vincular cada incidencia a una ejecución

Toda incidencia debe estar asociada a un `source_run`.

Esto permite saber en qué ejecución se detectó el problema y analizar la calidad por fuente, fecha o vertical.

---

## 3.3. Permitir relación polimórfica con entidades afectadas

Una incidencia puede afectar a distintos tipos de entidades:

* `place`
* `place_source_ref`
* `review`
* `category`
* `neighborhood`
* `raw_asset`
* etc.

Crear una FK directa para cada posible entidad haría el modelo rígido y complejo.

Por ello se utiliza una relación polimórfica mediante:

```text
entity_type + entity_id
```

La consistencia de esta relación se controla desde la lógica del pipeline y mediante catálogos permitidos de `entity_type`.

---

## 4. Entidad `validation_issue`

## 4.1. Propósito

`validation_issue` representa una **incidencia de calidad, validación, consistencia, matching, geografía o esquema** detectada por el sistema.

Su objetivo es dejar evidencia estructurada de los problemas encontrados durante el procesamiento.

---

## 4.2. Naturaleza de la entidad

| Propiedad            | Valor                   |
| -------------------- | ----------------------- |
| Tipo                 | Calidad / auditoría     |
| Nivel                | Incidencia estructurada |
| Origen               | Sistema interno         |
| Persistencia         | Sí                      |
| Relación polimórfica | Sí                      |

---

## 4.3. Campos principales

| Campo                 | Descripción                              |
| --------------------- | ---------------------------------------- |
| `validation_issue_id` | Identificador interno de la incidencia   |
| `source_run_id`       | Ejecución donde se detectó la incidencia |
| `raw_asset_id`        | Asset raw relacionado si aplica          |
| `entity_type`         | Tipo de entidad afectada                 |
| `entity_id`           | ID de la entidad afectada                |
| `issue_code`          | Código técnico de la incidencia          |
| `issue_type`          | Tipo general del problema                |
| `severity`            | Severidad                                |
| `message`             | Mensaje legible                          |
| `field_name`          | Campo afectado si aplica                 |
| `received_value`      | Valor recibido o problemático            |
| `expected_rule`       | Regla esperada o incumplida              |
| `status`              | Estado de la incidencia                  |
| `resolution_notes`    | Notas de resolución                      |
| `detected_at`         | Fecha de detección                       |
| `resolved_at`         | Fecha de resolución                      |
| `created_at`          | Fecha de creación                        |
| `updated_at`          | Fecha de actualización                   |

---

## 4.4. Tipos de incidencia

Valores previstos para `issue_type`:

* `validation`
* `quality`
* `matching`
* `geospatial`
* `schema`

Estos tipos permiten agrupar problemas según su naturaleza.

### Ejemplos

| Tipo         | Ejemplo                                    |
| ------------ | ------------------------------------------ |
| `validation` | Campo obligatorio ausente                  |
| `quality`    | Texto demasiado corto o poco útil          |
| `matching`   | Duplicado potencial entre fuentes          |
| `geospatial` | Local fuera de barrios oficiales           |
| `schema`     | Estructura inesperada en una respuesta raw |

---

## 4.5. Severidades

Valores previstos para `severity`:

* `info`
* `warning`
* `error`
* `critical`

### Interpretación recomendada

| Severidad  | Significado                                                 |
| ---------- | ----------------------------------------------------------- |
| `info`     | Incidencia informativa que no bloquea el proceso            |
| `warning`  | Problema menor que permite continuar                        |
| `error`    | Problema que afecta al registro o etapa concreta            |
| `critical` | Problema grave que puede invalidar una ejecución o vertical |

---

## 4.6. Estados

Valores previstos para `status`:

* `open`
* `resolved`
* `ignored`

### Interpretación recomendada

| Estado     | Significado                                  |
| ---------- | -------------------------------------------- |
| `open`     | La incidencia sigue pendiente                |
| `resolved` | La incidencia fue corregida o gestionada     |
| `ignored`  | La incidencia se acepta y no requiere acción |

---

## 4.7. Entity types permitidos

El schema permite registrar incidencias sobre las entidades principales del modelo.

Valores previstos:

* `source_system`
* `source_run`
* `raw_asset`
* `place`
* `place_source_ref`
* `review`
* `category`
* `place_category`
* `district`
* `neighborhood`
* `place_neighborhood_assignment`

Esto permite que el sistema registre incidencias de forma homogénea sin multiplicar tablas específicas.

---

## 4.8. Ejemplos de `issue_code`

Los códigos de incidencia deben ser técnicos, estables y en formato `snake_case`.

Ejemplos:

| Código                   | Descripción                                       |
| ------------------------ | ------------------------------------------------- |
| `missing_coordinates`    | El registro no tiene coordenadas                  |
| `invalid_geometry`       | La geometría no es válida                         |
| `empty_name`             | El nombre está vacío                              |
| `duplicate_candidate`    | Posible duplicado detectado                       |
| `unmapped_category`      | Categoría fuente sin mapeo interno                |
| `missing_required_field` | Falta un campo obligatorio                        |
| `review_text_empty`      | Reseña sin texto útil                             |
| `neighborhood_not_found` | No se pudo asignar barrio                         |
| `schema_mismatch`        | La estructura del raw no coincide con lo esperado |

---

## 4.9. Reglas de negocio

* Toda incidencia debe estar asociada a un `source_run`.
* Una incidencia puede estar asociada a un `raw_asset`.
* Una incidencia debe indicar el tipo de entidad afectada.
* Una incidencia debe tener código técnico.
* Una incidencia debe tener tipo, severidad y estado.
* Una incidencia no debe eliminarse sin criterio.
* Lo normal es resolverla, ignorarla justificadamente o dejarla abierta.

---

## 4.10. Qué no debe guardar `validation_issue`

No debe guardar:

* payloads raw completos
* filas completas de negocio
* archivos embebidos
* reportes agregados completos
* lógica completa de validación

Debe registrar la incidencia de forma estructurada y suficiente para poder entenderla y tratarla.

---

## 4.11. Relaciones

| Relación                              | Cardinalidad | Descripción                                   |
| ------------------------------------- | ------------ | --------------------------------------------- |
| `validation_issue` → `source_run`     | N:1          | Toda incidencia pertenece a una ejecución     |
| `validation_issue` → `raw_asset`      | N:1 opcional | Puede relacionarse con un artefacto raw       |
| `validation_issue` → entidad afectada | Polimórfica  | Se representa con `entity_type` + `entity_id` |

---

## 4.12. Validaciones relevantes

* `source_run_id` es obligatorio.
* `entity_type` es obligatorio.
* `issue_code` es obligatorio.
* `issue_code` debe estar en formato `snake_case`.
* `issue_type` es obligatorio.
* `severity` es obligatorio.
* `message` es obligatorio.
* `status` es obligatorio.
* `resolved_at`, si existe, no puede ser anterior a `detected_at`.
* Si `status = resolved`, debe existir `resolved_at`.

---

## 4.13. Índices relevantes

El schema define índices sobre:

* `source_run_id`
* `raw_asset_id`
* `entity_type`
* `(entity_type, entity_id)`
* `issue_code`
* `issue_type`
* `severity`
* `status`
* `detected_at`

Estos índices permiten consultar incidencias por ejecución, entidad afectada, severidad, estado o fecha.

---

## 5. Relación con verticales actuales

## 5.1. Vertical Sevilla Geo

La vertical Sevilla Geo puede registrar incidencias como:

* geometría inválida
* barrio sin distrito
* nombre oficial vacío
* geometría vacía
* error al descargar o leer el GeoJSON

Estas incidencias se asociarían al `source_run` correspondiente y, si aplica, al `raw_asset` geográfico.

---

## 5.2. Vertical OSM / Overpass

La vertical OSM / Overpass puede registrar incidencias como:

* POI sin nombre
* POI sin coordenadas
* categoría no mapeada
* posible duplicado
* local fuera de la geometría de barrios
* respuesta raw incompleta
* error de esquema en el JSON de Overpass

Estas incidencias permiten medir la calidad de la ingesta y priorizar mejoras.

---

## 6. Relación con reporting de calidad

`validation_issue` puede alimentar reportes de calidad como:

* número de incidencias por fuente
* número de incidencias por run
* incidencias abiertas por severidad
* porcentaje de registros rechazados
* problemas geográficos frecuentes
* categorías sin mapear
* duplicados potenciales

Esto convierte la calidad en un elemento medible y no solo en una revisión manual informal.

---

## 7. Decisiones generales del bloque de calidad

Las decisiones principales son:

1. Las incidencias relevantes se estructuran en base de datos.
2. Toda incidencia pertenece a una ejecución.
3. Una incidencia puede vincularse a un raw asset.
4. La entidad afectada se representa de forma polimórfica.
5. Las incidencias tienen tipo, severidad y estado.
6. Los códigos de incidencia deben ser estables y en `snake_case`.
7. La tabla sirve para auditoría, reporting y mejora continua del pipeline.

---

## 8. Conclusión

El bloque de calidad permite que Hidden Gems controle y documente los problemas detectados durante el pipeline.

Gracias a `validation_issue`, el sistema puede auditar errores, advertencias y problemas de consistencia de forma estructurada.

Esta entidad es fundamental para mantener la confianza en los datos y para orientar las siguientes fases de normalización, depuración y mejora del sistema.

