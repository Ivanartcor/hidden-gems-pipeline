# docs/03_data_model/24_classification_entities.md

````md
# 24. Catálogo de entidades: clasificación

## 1. Introducción

Este documento describe el catálogo de entidades encargado de la **clasificación de locales** dentro del modelo de datos de Hidden Gems.

El proyecto trabaja con fuentes heterogéneas que no comparten una misma taxonomía. Google Places, OSM / Overpass y Yelp pueden clasificar un mismo local de formas diferentes, con nombres, etiquetas y niveles de detalle distintos.

Por este motivo, el modelo incorpora una capa de clasificación interna que permite transformar categorías externas en una estructura común y controlada.

Las entidades incluidas en este catálogo son:

- `category`
- `place_category`

La decisión principal de este bloque es separar la **taxonomía interna del sistema** de la **asignación concreta de categorías a locales**.

---

## 2. Visión general del bloque de clasificación

El bloque de clasificación se organiza de la siguiente forma:

```text
category
└── place_category
````

La relación conceptual es:

* `category` define la categoría canónica interna.
* `place_category` relaciona un local con una o varias categorías.

Esto permite que Hidden Gems no dependa directamente de las categorías raw de una fuente externa.

---

## 3. Decisiones principales del bloque de clasificación

## 3.1. Usar una taxonomía interna

La categoría final utilizada por el sistema no debe depender literalmente de Google, OSM o Yelp.

Cada fuente puede utilizar nombres distintos para conceptos similares. Por ejemplo:

* Google puede usar tipos como `restaurant`, `bar`, `cafe`.
* OSM puede usar etiquetas como `amenity=restaurant`, `amenity=bar`, `amenity=cafe`.
* Yelp puede usar categorías comerciales o gastronómicas más específicas.

La entidad `category` permite traducir esas diferencias hacia un catálogo interno común.

---

## 3.2. Separar categoría y asignación

Una cosa es que exista una categoría interna y otra distinta que un local esté asociado a ella.

Por eso el modelo separa:

* `category`: catálogo canónico de categorías.
* `place_category`: relación entre un `place` y una `category`.

Esta separación permite que un local tenga varias categorías, que exista una categoría principal y que la asignación tenga método y confianza.

---

## 3.3. No guardar categorías raw como categoría final

Las categorías raw procedentes de fuentes externas no deben convertirse directamente en la categoría final del sistema.

El modelo conserva información raw cuando es necesario, por ejemplo en `place_source_ref.source_categories_raw`, pero la categoría interna se gestiona en `category` y `place_category`.

---

## 4. Entidad `category`

## 4.1. Propósito

`category` representa una **categoría canónica interna** del sistema.

Su función es crear una taxonomía común para clasificar locales gastronómicos y permitir que distintas fuentes se integren bajo una misma lógica.

---

## 4.2. Naturaleza de la entidad

| Propiedad             | Valor                      |
| --------------------- | -------------------------- |
| Tipo                  | Referencia / clasificación |
| Nivel                 | Canónico interno           |
| Dependencia de fuente | No directa                 |
| Persistencia          | Sí                         |
| Jerarquía opcional    | Sí                         |

---

## 4.3. Decisión de diseño principal

La categoría del sistema es interna y estable.

Esto significa que no se crea una categoría simplemente porque una fuente externa la traiga. Primero debe pasar por una lógica de normalización o aceptación dentro de la taxonomía del proyecto.

---

## 4.4. Campos principales

| Campo                | Descripción                                 |
| -------------------- | ------------------------------------------- |
| `category_id`        | Identificador interno de la categoría       |
| `category_code`      | Código técnico único en formato estable     |
| `category_name`      | Nombre canónico de la categoría             |
| `normalized_name`    | Nombre normalizado para matching y búsqueda |
| `display_name`       | Nombre de presentación                      |
| `description`        | Descripción semántica de la categoría       |
| `parent_category_id` | Categoría padre si se usa jerarquía         |
| `category_level`     | Nivel jerárquico                            |
| `is_food_related`    | Indica si pertenece al dominio gastronómico |
| `is_active`          | Indica si la categoría está activa          |
| `sort_order`         | Orden lógico de presentación                |
| `created_at`         | Fecha de creación                           |
| `updated_at`         | Fecha de última actualización               |

---

## 4.5. Jerarquía de categorías

La entidad permite una relación jerárquica mediante `parent_category_id`.

Esto hace posible representar categorías generales y específicas.

Ejemplo conceptual:

```text
food_and_drink
├── restaurant
├── bar
├── cafe
└── bakery
```

La jerarquía no es imprescindible para el funcionamiento inicial del pipeline, pero deja el modelo preparado para evolución futura.

---

## 4.6. Reglas de negocio

* `category_code` debe ser único.
* `category_name` debe representar una categoría interna estable.
* Una categoría puede tener una categoría padre.
* Una categoría no puede ser padre de sí misma.
* Las categorías pueden desactivarse sin eliminarse físicamente.
* La categoría no debe depender literalmente de un nombre raw externo.

---

## 4.7. Qué no debe guardar `category`

No debe guardar:

* locales concretos
* IDs de categorías externas
* categorías raw de fuentes
* métricas analíticas
* ranking
* resultados NLP

La relación con locales se realiza mediante `place_category`.

---

## 4.8. Relaciones

| Relación                      | Cardinalidad | Descripción                                         |
| ----------------------------- | ------------ | --------------------------------------------------- |
| `category` → `place_category` | 1:N          | Una categoría puede estar asociada a muchos locales |
| `category` → `category`       | 1:N opcional | Una categoría puede tener subcategorías             |

---

## 4.9. Validaciones relevantes

* `category_code` no debe estar vacío.
* `category_code` debe seguir formato `snake_case`.
* `category_name` no debe estar vacío.
* `normalized_name` no debe estar vacío.
* `category_level`, si existe, debe ser mayor o igual que 0.
* `parent_category_id` no puede apuntar a la propia categoría.

---

## 4.10. Índices relevantes

El schema define índices sobre:

* `category_code`, como único.
* `normalized_name`, como único.
* `parent_category_id`.
* `is_active`.
* `is_food_related`.

Estos índices facilitan búsqueda, normalización y explotación de la taxonomía.

---

## 5. Entidad `place_category`

## 5.1. Propósito

`place_category` representa la **relación entre un local y una categoría interna**.

Es una entidad puente que permite que un mismo local tenga varias categorías.

---

## 5.2. Naturaleza de la entidad

| Propiedad             | Valor               |
| --------------------- | ------------------- |
| Tipo                  | Relación / puente   |
| Nivel                 | Relación de negocio |
| Dependencia de fuente | Parcial             |
| Persistencia          | Sí                  |
| Soporta confianza     | Sí                  |

---

## 5.3. Decisión de diseño principal

La clasificación de un local no se almacena como texto libre dentro de `place`.

Se almacena mediante una relación controlada con `category`.

Esto permite:

* varias categorías por local
* categoría principal
* confianza de asignación
* método de asignación
* origen de la fuente cuando aplica

---

## 5.4. Campos principales

| Campo                   | Descripción                                   |
| ----------------------- | --------------------------------------------- |
| `place_category_id`     | Identificador interno de la relación          |
| `place_id`              | FK al local canónico                          |
| `category_id`           | FK a la categoría interna                     |
| `source_system_id`      | Fuente que originó o apoyó la asignación      |
| `assignment_method`     | Método de asignación                          |
| `is_primary`            | Indica si es la categoría principal del local |
| `assignment_confidence` | Confianza de la asignación                    |
| `is_active`             | Indica si la relación está activa             |
| `notes`                 | Observaciones                                 |
| `created_at`            | Fecha de creación                             |
| `updated_at`            | Fecha de última actualización                 |

---

## 5.5. Métodos de asignación previstos

La asignación de categoría puede proceder de varias estrategias:

* `source_raw`: viene directamente de una fuente.
* `normalized`: resultado de una normalización interna.
* `manual`: revisión o decisión manual.
* `rule_based`: regla definida por el sistema.

El método permite entender cómo se generó la relación entre local y categoría.

---

## 5.6. Reglas de negocio

* Un `place` puede tener varias categorías.
* Una `category` puede estar asociada a muchos locales.
* Una relación debe indicar el método de asignación.
* Puede existir una categoría principal por local.
* La confianza de asignación, si existe, debe estar entre 0 y 1.
* La relación puede desactivarse sin eliminarse físicamente.

---

## 5.7. Constraint principal

El schema limita que un local tenga varias categorías principales activas al mismo tiempo.

Conceptualmente:

```text
Un place solo puede tener una category principal activa.
```

Esto permite mantener claridad en consultas y explotación posterior.

---

## 5.8. Qué no debe guardar `place_category`

No debe guardar:

* descripción completa del local
* texto raw extenso de la fuente
* categoría raw completa si ya se conserva en `place_source_ref`
* resultados analíticos
* rankings

Solo representa la relación entre local y categoría.

---

## 5.9. Relaciones

| Relación                           | Cardinalidad | Descripción                                    |
| ---------------------------------- | ------------ | ---------------------------------------------- |
| `place_category` → `place`         | N:1          | Cada asignación pertenece a un local           |
| `place_category` → `category`      | N:1          | Cada asignación pertenece a una categoría      |
| `place_category` → `source_system` | N:1 opcional | Puede indicar fuente que originó la asignación |

---

## 5.10. Validaciones relevantes

* `place_id` es obligatorio.
* `category_id` es obligatorio.
* `assignment_method` es obligatorio.
* `is_primary` es obligatorio.
* `is_active` es obligatorio.
* `assignment_confidence`, si existe, debe estar entre 0 y 1.

---

## 5.11. Índices relevantes

El schema define índices sobre:

* `place_id`
* `category_id`
* `source_system_id`
* `is_primary`
* `is_active`

También define una restricción única sobre la combinación de local, categoría y método de asignación.

---

## 6. Relación con verticales actuales y futuras

## 6.1. Vertical OSM / Overpass

OSM / Overpass puede aportar etiquetas como `amenity`, `cuisine` u otras claves útiles.

Estas señales pueden transformarse en categorías internas mediante reglas o normalización.

La vertical puede alimentar:

* `category`
* `place_category`

## 6.2. Vertical Google Places

Google Places puede aportar tipos de lugar y categorías asociadas.

Estas categorías deberán mapearse a la taxonomía interna antes de crear relaciones en `place_category`.

## 6.3. Vertical Yelp Open Dataset

Yelp puede aportar categorías comerciales más descriptivas.

En esta fase se plantea principalmente como apoyo para experimentación, validación textual y normalización.

---

## 7. Decisiones generales del bloque de clasificación

Las decisiones principales son:

1. La taxonomía del sistema es interna.
2. Las categorías raw no se usan directamente como categoría final.
3. Un local puede tener varias categorías.
4. Un local puede tener una categoría principal activa.
5. La asignación de categoría debe tener método y, si procede, confianza.
6. Las relaciones se pueden desactivar sin borrar físicamente.
7. El modelo queda preparado para mappings más avanzados entre fuentes.

---

## 8. Conclusión

El bloque de clasificación permite unificar la forma en la que Hidden Gems entiende los tipos de locales.

Gracias a la separación entre `category` y `place_category`, el sistema puede integrar categorías procedentes de distintas fuentes sin perder control semántico ni trazabilidad.

Esta estructura será especialmente importante cuando se incorporen nuevas fuentes y cuando se avance hacia fases de normalización y análisis gastronómico más específicas.

````

---

# docs/03_data_model/25_governance_traceability_entities.md


