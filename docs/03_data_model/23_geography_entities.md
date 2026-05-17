# 23. Catálogo de entidades: geografía

## 1. Introducción

Este documento describe el catálogo de entidades geográficas del modelo de datos de Hidden Gems.

La geografía es una parte central del proyecto porque Hidden Gems no busca únicamente trabajar con locales gastronómicos aislados, sino relacionarlos con unidades territoriales concretas, especialmente barrios.

El análisis futuro del sistema se apoyará en la pregunta:

> ¿Qué señales gastronómicas relevantes aparecen en cada barrio?

Para poder responder a esa pregunta, el modelo necesita una base geográfica oficial y una forma trazable de asignar locales a barrios.

Las entidades incluidas en este catálogo son:

- `district`
- `neighborhood`
- `place_neighborhood_assignment`

---

## 2. Visión general del bloque geográfico

El bloque geográfico se organiza de la siguiente forma:

```text
district
└── neighborhood
    └── place_neighborhood_assignment
````

La jerarquía principal es:

* un distrito contiene varios barrios
* un barrio puede recibir varios locales asignados
* un local se asigna a un barrio mediante una entidad derivada

La decisión clave es que la geografía oficial y la asignación geográfica del pipeline se separan en entidades distintas.

---

## 3. Decisiones principales del modelo geográfico

## 3.1. Usar geografía oficial como referencia

Los distritos y barrios no se infieren desde fuentes comerciales ni desde texto.

Deben proceder de una fuente geográfica oficial o controlada. Esto permite mantener consistencia territorial y evitar que el modelo dependa de nombres ambiguos o no normalizados.

---

## 3.2. No guardar el barrio directamente en `place`

Aunque cada local pueda estar asociado a un barrio, esa relación no se almacena como una columna directa en `place`.

En su lugar, se utiliza `place_neighborhood_assignment`.

Esto permite:

* recalcular asignaciones
* registrar el método utilizado
* almacenar confianza
* marcar revisiones manuales
* conservar histórico
* corregir errores sin alterar la entidad `place`

---

## 3.3. Utilizar PostGIS para operaciones espaciales

Las entidades geográficas usan tipos `geometry` de PostGIS.

Esto permite:

* almacenar geometrías oficiales
* indexar espacialmente barrios y distritos
* calcular centroides
* calcular áreas
* asignar locales mediante operaciones punto-polígono
* realizar validaciones geográficas

---

## 4. Entidad `district`

## 4.1. Propósito

`district` representa un **distrito oficial de Sevilla**.

Es el nivel territorial superior dentro del modelo geográfico y permite agrupar barrios bajo una estructura administrativa común.

Aunque el análisis principal de Hidden Gems se centra en barrios, el distrito aporta contexto, jerarquía y capacidad de agregación.

---

## 4.2. Naturaleza de la entidad

| Propiedad                 | Valor                     |
| ------------------------- | ------------------------- |
| Tipo                      | Dato maestro geográfico   |
| Nivel                     | Territorial superior      |
| Dependencia de fuente     | Fuente geográfica oficial |
| Persistencia              | Sí                        |
| Entidad analítica directa | No principal              |

---

## 4.3. Campos principales

| Campo             | Descripción                                |
| ----------------- | ------------------------------------------ |
| `district_id`     | Identificador interno del distrito         |
| `official_code`   | Código oficial si la fuente lo proporciona |
| `official_name`   | Nombre oficial del distrito                |
| `normalized_name` | Nombre normalizado                         |
| `display_name`    | Nombre de presentación                     |
| `geometry`        | Geometría oficial del distrito             |
| `centroid_point`  | Centroide derivado de la geometría         |
| `area_m2`         | Área del distrito en metros cuadrados      |
| `alias_names`     | Variantes o alias del nombre               |
| `source_version`  | Versión de la fuente geográfica            |
| `is_active`       | Indica si el distrito está activo          |
| `created_at`      | Fecha de creación interna                  |
| `updated_at`      | Fecha de última actualización              |

---

## 4.4. Geometría

La geometría del distrito se almacena como:

```sql
GEOMETRY(MultiPolygon, 4326)
```

El uso de `MultiPolygon` permite representar correctamente entidades territoriales aunque estén formadas por una o varias geometrías.

El sistema calcula automáticamente:

* `centroid_point`
* `area_m2`

mediante triggers definidos en el schema.

---

## 4.5. Reglas de negocio

* Un `district` representa un distrito oficial.
* Un `district` puede contener muchos barrios.
* Un `district` no debe contener directamente locales ni reseñas.
* Un `district` no debe almacenar rankings ni métricas gastronómicas finales.
* Si la cartografía oficial cambia, debe poder versionarse o actualizarse de forma controlada.

---

## 4.6. Qué no debe guardar `district`

No debe guardar:

* locales
* reseñas
* platos
* rankings
* categorías
* puntuaciones analíticas
* datos procedentes de fuentes comerciales

Su función es exclusivamente geográfica y de referencia territorial.

---

## 4.7. Relaciones

| Relación                                     | Cardinalidad | Descripción                                          |
| -------------------------------------------- | ------------ | ---------------------------------------------------- |
| `district` → `neighborhood`                  | 1:N          | Un distrito contiene varios barrios                  |
| `district` → `place_neighborhood_assignment` | 1:N opcional | Se conserva como FK útil para consultas y validación |

---

## 4.8. Validaciones relevantes

* `official_name` no debe estar vacío.
* `normalized_name` no debe estar vacío.
* `geometry` debe ser válida.
* `geometry` no debe estar vacía.
* `area_m2`, si existe, debe ser mayor que 0.

---

## 4.9. Índices relevantes

El schema define índices sobre:

* `normalized_name`
* `official_name`
* `is_active`
* `geometry`, mediante GIST
* `centroid_point`, mediante GIST

---

## 5. Entidad `neighborhood`

## 5.1. Propósito

`neighborhood` representa un **barrio oficial de Sevilla**.

Es la entidad geográfica más importante para el producto Hidden Gems, ya que el análisis posterior se realizará principalmente a nivel de barrio.

---

## 5.2. Naturaleza de la entidad

| Propiedad                      | Valor                                    |
| ------------------------------ | ---------------------------------------- |
| Tipo                           | Dato maestro geográfico                  |
| Nivel                          | Unidad principal de análisis territorial |
| Dependencia de fuente          | Fuente geográfica oficial                |
| Persistencia                   | Sí                                       |
| Entidad clave para Hidden Gems | Sí                                       |

---

## 5.3. Campos principales

| Campo             | Descripción                                |
| ----------------- | ------------------------------------------ |
| `neighborhood_id` | Identificador interno del barrio           |
| `district_id`     | FK al distrito al que pertenece            |
| `official_code`   | Código oficial si la fuente lo proporciona |
| `official_name`   | Nombre oficial del barrio                  |
| `normalized_name` | Nombre normalizado                         |
| `display_name`    | Nombre de presentación                     |
| `geometry`        | Geometría oficial del barrio               |
| `centroid_point`  | Centroide derivado                         |
| `area_m2`         | Área del barrio en metros cuadrados        |
| `alias_names`     | Variantes o alias del nombre               |
| `source_version`  | Versión de la fuente geográfica            |
| `is_active`       | Indica si el barrio está activo            |
| `created_at`      | Fecha de creación interna                  |
| `updated_at`      | Fecha de última actualización              |

---

## 5.4. Geometría

La geometría del barrio se almacena como:

```sql
GEOMETRY(MultiPolygon, 4326)
```

El uso de geometrías oficiales permite asignar locales a barrios mediante operaciones espaciales.

La operación principal esperada es:

```text
punto del local dentro del polígono del barrio
```

En términos PostGIS, esta asignación podrá apoyarse en operaciones como `ST_Contains`, `ST_Intersects` o equivalentes según la estrategia final.

---

## 5.5. Reglas de negocio

* Un `neighborhood` pertenece a un único `district`.
* Un `neighborhood` puede recibir muchos locales asignados.
* Un `neighborhood` no almacena directamente locales.
* Un `neighborhood` no almacena rankings ni métricas finales.
* La geometría del barrio es la referencia oficial para asignación territorial.
* Si cambia la cartografía, debe poder gestionarse mediante actualización controlada o versionado.

---

## 5.6. Qué no debe guardar `neighborhood`

No debe guardar:

* locales embebidos
* reseñas
* platos destacados
* rankings
* puntuaciones agregadas
* categorías gastronómicas

El barrio es una referencia geográfica, no una entidad analítica final.

---

## 5.7. Relaciones

| Relación                                         | Cardinalidad | Descripción                                    |
| ------------------------------------------------ | ------------ | ---------------------------------------------- |
| `neighborhood` → `district`                      | N:1          | Cada barrio pertenece a un distrito            |
| `neighborhood` → `place_neighborhood_assignment` | 1:N          | Un barrio puede tener muchos locales asignados |

---

## 5.8. Validaciones relevantes

* `district_id` es obligatorio.
* `official_name` no debe estar vacío.
* `normalized_name` no debe estar vacío.
* `geometry` debe ser válida.
* `geometry` no debe estar vacía.
* `area_m2`, si existe, debe ser mayor que 0.
* El nombre normalizado debe ser único dentro de su distrito.

---

## 5.9. Índices relevantes

El schema define índices sobre:

* `district_id`
* `normalized_name`
* `official_name`
* `is_active`
* `geometry`, mediante GIST
* `centroid_point`, mediante GIST

---

## 5.10. Papel en el pipeline

La entidad `neighborhood` se alimenta desde la vertical Sevilla Geo.

Una vez cargada la geografía oficial, los barrios se utilizan como referencia para asignar espacialmente los locales procedentes de otras verticales, como OSM / Overpass o Google Places.

---

## 6. Entidad `place_neighborhood_assignment`

## 6.1. Propósito

`place_neighborhood_assignment` representa la **asignación de un local a un barrio**.

No representa el barrio en sí, sino el resultado del proceso de georreferenciación o asignación espacial.

---

## 6.2. Naturaleza de la entidad

| Propiedad             | Valor                                 |
| --------------------- | ------------------------------------- |
| Tipo                  | Relación geográfica derivada          |
| Nivel                 | Puente entre `place` y `neighborhood` |
| Dependencia de fuente | Indirecta                             |
| Persistencia          | Sí                                    |
| Soporta histórico     | Sí                                    |

---

## 6.3. Decisión de diseño principal

El barrio no se guarda directamente en `place`.

La asignación se almacena en una entidad separada porque:

* se calcula automáticamente
* puede cambiar
* puede tener confianza
* puede revisarse manualmente
* puede depender de la geometría utilizada
* puede necesitar histórico

---

## 6.4. Campos principales

| Campo                              | Descripción                            |
| ---------------------------------- | -------------------------------------- |
| `place_neighborhood_assignment_id` | Identificador interno de la asignación |
| `place_id`                         | FK al local canónico                   |
| `neighborhood_id`                  | FK al barrio asignado                  |
| `district_id`                      | FK opcional al distrito asociado       |
| `assignment_method`                | Método de asignación                   |
| `assignment_confidence`            | Confianza de la asignación             |
| `source_geometry_used`             | Geometría usada para la asignación     |
| `distance_to_centroid_m`           | Distancia al centroide del barrio      |
| `is_current`                       | Indica si es la asignación vigente     |
| `is_manually_verified`             | Indica si fue revisada manualmente     |
| `valid_from`                       | Inicio de vigencia                     |
| `valid_to`                         | Fin de vigencia                        |
| `notes`                            | Observaciones                          |
| `created_at`                       | Fecha de creación                      |
| `updated_at`                       | Fecha de última actualización          |

---

## 6.5. Métodos de asignación previstos

El campo `assignment_method` permite diferenciar cómo se obtuvo la asignación.

Valores previstos:

* `point_in_polygon`
* `nearest_polygon`
* `manual_review`
* `fallback_rule`

También puede compartir catálogo técnico con otros métodos de asignación usados en el modelo.

---

## 6.6. Reglas de negocio

* Un `place` debe poder tener una asignación vigente.
* Un `place` no debería tener dos asignaciones vigentes conflictivas.
* La asignación debe indicar el método utilizado.
* La asignación puede tener una confianza asociada.
* La asignación puede marcarse como revisada manualmente.
* La asignación puede conservar histórico mediante `valid_from` y `valid_to`.

---

## 6.7. Constraint principal

El schema aplica una restricción parcial para permitir una sola asignación vigente por local:

```sql
UNIQUE parcial sobre place_id WHERE is_current = TRUE
```

Esto impide que un mismo local tenga dos barrios actuales al mismo tiempo.

---

## 6.8. Coherencia entre barrio y distrito

El modelo incluye una relación adicional para reforzar la coherencia entre `neighborhood_id` y `district_id`.

Esto evita asignaciones inconsistentes del tipo:

```text
local → barrio A → distrito incorrecto
```

Aunque el distrito podría derivarse desde el barrio, mantener `district_id` en la asignación facilita consultas y validaciones.

---

## 6.9. Qué no debe guardar `place_neighborhood_assignment`

No debe guardar:

* geometría completa del barrio
* geometría completa del local
* información textual del local
* métricas agregadas
* rankings
* resultados analíticos finales

Solo representa la relación geográfica derivada entre local y barrio.

---

## 6.10. Relaciones

| Relación                                         | Cardinalidad | Descripción                                          |
| ------------------------------------------------ | ------------ | ---------------------------------------------------- |
| `place_neighborhood_assignment` → `place`        | N:1          | Cada asignación pertenece a un local                 |
| `place_neighborhood_assignment` → `neighborhood` | N:1          | Cada asignación pertenece a un barrio                |
| `place_neighborhood_assignment` → `district`     | N:1 opcional | Cada asignación puede conservar el distrito asociado |

---

## 6.11. Validaciones relevantes

* `place_id` es obligatorio.
* `neighborhood_id` es obligatorio.
* `assignment_method` es obligatorio.
* `assignment_confidence`, si existe, debe estar entre 0 y 1.
* `distance_to_centroid_m`, si existe, debe ser mayor o igual que 0.
* `valid_to` no debe ser anterior a `valid_from`.

---

## 6.12. Índices relevantes

El schema define índices sobre:

* `place_id`
* `neighborhood_id`
* `district_id`
* `assignment_method`
* `is_current`
* `is_manually_verified`

Estos índices facilitan consultas por local, barrio, distrito y estado de asignación.

---

## 6.13. Papel en el pipeline

Esta entidad se alimenta después de que existan:

* locales en `place`
* barrios en `neighborhood`

En la vertical OSM / Overpass y en la vertical Google Places, una vez cargados los puntos de interés, se puede usar la geometría del local para calcular el barrio correspondiente y crear una asignación en `place_neighborhood_assignment`.

En las fases IA, esta asignación es esencial para que las señales y rankings puedan agregarse por barrio y distrito.

---

## 7. Relación con verticales actuales

## 7.1. Vertical Sevilla Geo

La vertical Sevilla Geo alimenta:

* `district`
* `neighborhood`

También genera trazabilidad en:

* `source_system`
* `source_run`
* `raw_asset`

Y puede registrar problemas en:

* `validation_issue`

---

## 7.2. Vertical OSM / Overpass

La vertical OSM / Overpass utiliza la geografía oficial para asignar los POIs gastronómicos a barrios.

Puede alimentar:

* `place_neighborhood_assignment`

La relación depende de que existan previamente:

* `place`
* `neighborhood`
* `district`

---

## 8. Decisiones generales del bloque geográfico

Las decisiones principales son:

1. Usar geografía oficial para barrios y distritos.
2. Representar distritos y barrios como datos maestros.
3. No guardar el barrio directamente dentro de `place`.
4. Usar `place_neighborhood_assignment` como relación derivada.
5. Mantener método, confianza y revisión manual en la asignación.
6. Permitir histórico de asignaciones.
7. Usar PostGIS para geometrías, índices y operaciones espaciales.

---

## 10. Estado actual y uso en ranking/dashboard v2

La capa geográfica ya se utiliza de forma directa en la explotación final del proyecto. En el ranking Sevilla IA v2, cada candidato seleccionado conserva distrito y barrio normalizados para permitir análisis territorial.

Resultados del dashboard v2:

| Métrica | Valor |
|---|---:|
| Distritos con candidatos seleccionados | 11 |
| Barrios con candidatos seleccionados | 67 |
| Locales seleccionados | 198 |
| Candidatos seleccionados | 268 |

La geografía también alimenta:

- filtros por distrito y barrio en dashboard;
- resúmenes `district_summary.csv` y `neighborhood_summary.csv`;
- mapa territorial del dashboard Sevilla IA v2;
- comparación de cobertura territorial entre v1 y v2.

La comparación v1/v2 muestra una mejora territorial clara:

| Métrica | Resultado |
|---|---:|
| Barrios seleccionados v1 | 55 |
| Barrios seleccionados v2 | 67 |
| Delta v2 - v1 | +12 |

Para el mapa del dashboard v2, el export puede usar coordenadas reales de locales cuando están disponibles (`latitude_std`, `longitude_std`) y, si faltan, apoyarse en centroides aproximados por distrito/barrio como fallback visual. La fuente geográfica oficial sigue siendo la referencia para asignación territorial.

---

## 9. Conclusión

El bloque geográfico del modelo proporciona la base territorial necesaria para que Hidden Gems pueda trabajar a nivel de barrio.

La separación entre `district`, `neighborhood` y `place_neighborhood_assignment` permite distinguir claramente entre geografía oficial y resultados derivados del pipeline.

Esta estructura facilita la asignación espacial de locales, la validación territorial y el futuro desarrollo de análisis gastronómicos por barrio.