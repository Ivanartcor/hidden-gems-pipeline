# 41. Vertical OSM / Overpass

## 1. Introducción

La vertical **OSM / Overpass** es la vertical encargada de obtener puntos de interés gastronómicos desde OpenStreetMap mediante consultas Overpass.

Su función principal es incorporar una fuente abierta de locales y puntos de interés relacionados con comida, bebida y restauración, complementando otras fuentes como Google Places o Yelp Open Dataset.

Esta vertical permite construir una primera base abierta de locales potencialmente relevantes para Hidden Gems.

La pregunta que esta vertical permite responder es:

> ¿Qué puntos de interés gastronómicos abiertos existen en el área de Sevilla y cómo se relacionan con los barrios oficiales?

---

## 2. Objetivo de la vertical

El objetivo de la vertical OSM / Overpass es adquirir, almacenar, normalizar e integrar POIs gastronómicos procedentes de OpenStreetMap.

Concretamente, la vertical debe:

- construir consultas Overpass para el área de Sevilla
- obtener POIs gastronómicos según etiquetas OSM
- conservar la consulta y la respuesta raw
- registrar la ejecución de ingesta
- transformar nodos, ways y relaciones en registros procesables
- crear o actualizar `place`
- crear referencias en `place_source_ref`
- clasificar locales mediante `category` y `place_category`
- asignar locales a barrios mediante `place_neighborhood_assignment`
- registrar incidencias de calidad cuando corresponda

---

## 3. Papel dentro de Hidden Gems

OSM / Overpass cumple un papel estratégico dentro de Hidden Gems porque aporta una fuente abierta y reutilizable de puntos de interés.

Aunque no ofrece reseñas como fuente principal, aporta valor en:

- cobertura inicial de locales
- datos abiertos y trazables
- coordenadas
- categorías mediante tags
- contraste con fuentes comerciales
- enriquecimiento geográfico
- pruebas del modelo multisource

Esta vertical es especialmente útil para validar el diseño del modelo `place` + `place_source_ref`.

---

## 4. Fuente de datos

La fuente utilizada es OpenStreetMap consultado mediante Overpass API.

### Fuente lógica en el sistema

```text
source_code = osm_overpass
````

### Tipo de fuente

```text
source_type = api
```

### Modo de actualización

```text
refresh_mode = full_refresh / incremental técnico limitado
```

En la fase actual, la vertical puede ejecutarse como una extracción por área o bounding box.

---

## 5. Entidades del modelo afectadas

## 5.1. Gobierno y trazabilidad

| Entidad            | Uso                                                 |
| ------------------ | --------------------------------------------------- |
| `source_system`    | Registra la fuente `osm_overpass`                   |
| `source_run`       | Registra cada ejecución Overpass                    |
| `raw_asset`        | Registra query OverpassQL y respuesta raw           |
| `validation_issue` | Registra problemas de calidad, matching o geografía |

## 5.2. Núcleo de negocio

| Entidad            | Uso                                      |
| ------------------ | ---------------------------------------- |
| `place`            | Representa el local canónico interno     |
| `place_source_ref` | Representa el POI OSM vinculado al place |

## 5.3. Clasificación

| Entidad          | Uso                                                 |
| ---------------- | --------------------------------------------------- |
| `category`       | Catálogo interno de categorías                      |
| `place_category` | Clasificación del local según tags OSM normalizados |

## 5.4. Geografía

| Entidad                         | Uso                                   |
| ------------------------------- | ------------------------------------- |
| `place_neighborhood_assignment` | Asignación del local a barrio oficial |
| `neighborhood`                  | Referencia para operación espacial    |
| `district`                      | Contexto territorial derivado         |

---

## 6. Flujo general de la vertical

```text
Definición de área / bbox de Sevilla
        ↓
Construcción de consulta OverpassQL
        ↓
Ejecución contra Overpass API
        ↓
Registro de source_run
        ↓
Almacenamiento de query y respuesta raw
        ↓
Parseo de elementos OSM
        ↓
Normalización de POIs
        ↓
Creación / actualización de place
        ↓
Creación / actualización de place_source_ref
        ↓
Mapeo de categorías
        ↓
Asignación a barrio
        ↓
Registro de incidencias
```

---

## 7. Entrada de datos

La entrada principal es una consulta OverpassQL que recupera elementos OSM relacionados con restauración.

### Tipos de elementos OSM esperados

* `node`
* `way`
* `relation`

### Tags relevantes

La vertical puede buscar elementos con etiquetas como:

* `amenity=restaurant`
* `amenity=cafe`
* `amenity=bar`
* `amenity=fast_food`
* `amenity=pub`

También pueden considerarse otros tags complementarios:

* `name`
* `cuisine`
* `addr:street`
* `addr:housenumber`
* `phone`
* `website`
* `opening_hours`

---

## 8. Raw esperado

La vertical debe conservar tanto la query como la respuesta original.

Ejemplo conceptual:

```text
data/raw/osm_overpass/YYYY/MM/DD/<run_code>/query.overpassql
data/raw/osm_overpass/YYYY/MM/DD/<run_code>/response.json.gz
```

Ambos artefactos deben poder registrarse en `raw_asset`.

### Assets esperados

| Asset                 | Tipo                          | Descripción                         |
| --------------------- | ----------------------------- | ----------------------------------- |
| `query.overpassql`    | `query_result` o `raw_export` | Query usada para la extracción      |
| `response.json.gz`    | `api_response`                | Respuesta raw de Overpass           |
| `quality_report.json` | `raw_export`                  | Reporte QA si se genera             |
| `manifest.json`       | `raw_export`                  | Metadatos de ejecución si se genera |

---

## 9. Registro de ejecución

Cada ejecución debe crear un registro en `source_run`.

### Valores recomendados

```text
source_system = osm_overpass
run_type = seed / full_refresh / incremental
trigger_type = cli / manual / scheduled
status = running / completed / completed_with_warnings / failed
```

### Contadores relevantes

| Campo                     | Significado                    |
| ------------------------- | ------------------------------ |
| `records_extracted_count` | Número de elementos OSM leídos |
| `records_staged_count`    | Número de POIs aceptados       |
| `records_rejected_count`  | Número de POIs rechazados      |
| `raw_asset_count`         | Número de assets generados     |
| `error_count`             | Número de errores              |
| `warning_count`           | Número de advertencias         |

---

## 10. Normalización de elementos OSM

Los elementos OSM deben transformarse en registros compatibles con el modelo interno.

### 10.1. Identificador externo

El identificador externo debe construirse de forma estable combinando tipo e ID OSM.

Ejemplos:

```text
node/123456789
way/987654321
relation/555555
```

Este valor se almacena en:

```text
place_source_ref.source_record_id
```

El tipo puede almacenarse en:

```text
place_source_ref.source_entity_type
```

Ejemplos:

```text
osm_node
osm_way
osm_relation
```

---

## 10.2. Nombre

El tag `name` se utiliza como nombre raw principal.

Se almacena en:

```text
place_source_ref.source_name_raw
```

Después se genera una versión normalizada para `place.normalized_name`.

---

## 10.3. Coordenadas

Para nodos, la coordenada suele venir directamente como lat/lon.

Para ways o relations, puede ser necesario calcular o extraer un centroide aproximado, según cómo venga la respuesta de Overpass.

El resultado se utiliza para:

* `place.geom_point`
* `place_source_ref.source_geom_point`

---

## 10.4. Dirección

La dirección puede construirse a partir de tags como:

* `addr:street`
* `addr:housenumber`
* `addr:postcode`
* `addr:city`

Si no existe, puede quedar nula sin bloquear necesariamente el registro si hay coordenadas válidas.

---

## 10.5. Categoría

La categoría se obtiene principalmente desde tags OSM, especialmente `amenity`.

Ejemplo:

```text
amenity=restaurant → category=restaurant
amenity=cafe       → category=cafe
amenity=bar        → category=bar
```

El valor raw puede conservarse en `place_source_ref.source_primary_category_raw` o `source_categories_raw`.

La categoría interna se asigna mediante `place_category`.

---

## 11. Carga en `place`

La vertical puede crear un nuevo `place` cuando no exista un local canónico equivalente.

### Campos principales cargados

| Campo                | Fuente / cálculo                    |
| -------------------- | ----------------------------------- |
| `canonical_name`     | Tag `name` o nombre normalizado     |
| `normalized_name`    | Nombre normalizado                  |
| `address_text`       | Dirección construida desde tags     |
| `address_normalized` | Dirección normalizada               |
| `geom_point`         | Coordenada OSM normalizada          |
| `website_url`        | Tag `website` si existe             |
| `phone_number`       | Tag `phone` si existe               |
| `place_confidence`   | Confianza de creación/consolidación |
| `is_active`          | `true` por defecto                  |

---

## 12. Carga en `place_source_ref`

Cada POI OSM aceptado debe tener una referencia fuente.

### Campos principales cargados

| Campo                         | Fuente / cálculo                       |
| ----------------------------- | -------------------------------------- |
| `place_id`                    | Place creado o encontrado              |
| `source_system_id`            | Fuente `osm_overpass`                  |
| `source_run_id`               | Ejecución actual                       |
| `raw_asset_id`                | Respuesta raw asociada                 |
| `source_entity_type`          | Tipo OSM: node, way, relation          |
| `source_record_id`            | ID externo estable                     |
| `source_name_raw`             | Tag `name`                             |
| `source_address_raw`          | Dirección raw construida               |
| `source_geom_point`           | Coordenada fuente                      |
| `source_primary_category_raw` | Tag principal, por ejemplo amenity     |
| `source_categories_raw`       | Tags relevantes en JSON                |
| `source_payload_hash`         | Hash del elemento OSM                  |
| `match_method`                | Método usado para vincular con `place` |
| `match_confidence`            | Confianza del matching                 |
| `first_seen_run_id`           | Primer run en que aparece              |
| `last_seen_run_id`            | Último run en que aparece              |
| `is_current`                  | `true` si sigue vigente                |

---

## 13. Carga en `category` y `place_category`

La vertical debe mapear los tags OSM a categorías internas.

### Ejemplo conceptual

| OSM tag              | Category interna |
| -------------------- | ---------------- |
| `amenity=restaurant` | `restaurant`     |
| `amenity=cafe`       | `cafe`           |
| `amenity=bar`        | `bar`            |
| `amenity=fast_food`  | `fast_food`      |
| `amenity=pub`        | `pub`            |

### Asignación en `place_category`

Valores recomendados:

```text
assignment_method = source_raw / normalized
source_system = osm_overpass
assignment_confidence = 1.0 si el mapping es directo
```

---

## 14. Asignación geográfica a barrio

Una vez creado el `place`, la vertical puede asignarlo a un barrio usando su `geom_point`.

La estrategia principal es:

```text
point_in_polygon
```

Es decir:

```text
place.geom_point dentro de neighborhood.geometry
```

El resultado se almacena en:

```text
place_neighborhood_assignment
```

### Campos relevantes

| Campo                   | Valor esperado                           |
| ----------------------- | ---------------------------------------- |
| `place_id`              | Local asignado                           |
| `neighborhood_id`       | Barrio detectado                         |
| `district_id`           | Distrito del barrio                      |
| `assignment_method`     | `point_in_polygon`                       |
| `assignment_confidence` | Alta si el punto cae dentro del polígono |
| `source_geometry_used`  | `canonical_place_point` o similar        |
| `is_current`            | `true`                                   |
| `is_manually_verified`  | `false` inicialmente                     |

---

## 15. Validaciones de calidad

La vertical debe validar los elementos OSM antes y durante la integración.

### Validaciones mínimas

* el elemento tiene identificador OSM
* el elemento tiene tipo válido
* el elemento tiene coordenadas o geometría aprovechable
* el elemento tiene nombre útil
* la categoría puede mapearse o registrarse como no mapeada
* el punto puede asignarse a un barrio o registrarse la incidencia

### Validaciones recomendadas

* detectar posibles duplicados por nombre + distancia
* comprobar coordenadas dentro del área de trabajo
* comprobar tags mínimos
* validar que el raw se ha guardado correctamente
* validar que el hash del payload se genera correctamente

---

## 16. Incidencias posibles

| issue_code               | issue_type   | severity sugerida | Descripción                             |
| ------------------------ | ------------ | ----------------- | --------------------------------------- |
| `source_request_failed`  | `schema`     | `critical`        | Error al consultar Overpass             |
| `schema_mismatch`        | `schema`     | `error`           | Respuesta raw inesperada                |
| `missing_coordinates`    | `geospatial` | `error`           | Elemento sin coordenadas utilizables    |
| `empty_name`             | `quality`    | `warning`         | Elemento sin nombre válido              |
| `unmapped_category`      | `quality`    | `warning`         | Tag OSM sin mapeo a categoría interna   |
| `neighborhood_not_found` | `geospatial` | `warning`         | No se pudo asignar barrio               |
| `duplicate_candidate`    | `matching`   | `warning`         | Posible duplicado por nombre y cercanía |
| `invalid_geometry`       | `geospatial` | `error`           | Geometría no válida                     |
| `raw_asset_missing`      | `validation` | `critical`        | No se encontró el asset raw esperado    |

---

## 17. Matching y deduplicación

En esta fase, el matching puede ser conservador.

### Estrategias previstas

* coincidencia por identificador fuente para actualizaciones del mismo POI
* creación de nuevo `place` si no existe candidato claro
* matching básico por nombre normalizado + proximidad geográfica
* registro de `duplicate_candidate` cuando haya duda

### Métodos de matching posibles

| Método           | Uso                                   |
| ---------------- | ------------------------------------- |
| `exact_id`       | Mismo identificador externo           |
| `exact_name_geo` | Nombre igual y cercanía geográfica    |
| `fuzzy_geo`      | Nombre parecido y cercanía geográfica |
| `manual`         | Revisión manual                       |

El método y confianza se almacenan en `place_source_ref`.

---

## 18. Salidas de la vertical

### En base de datos

* `source_run`
* `raw_asset`
* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`
* `validation_issue`

### En sistema de ficheros

* query OverpassQL
* respuesta JSON raw
* manifest de ejecución
* reporte de calidad
* logs

---

## 19. Criterio de éxito

La vertical se considera correcta si:

* el source system `osm_overpass` existe
* se registra un `source_run`
* se guardan query y respuesta raw como assets
* se parsean correctamente elementos OSM
* se crean referencias en `place_source_ref`
* se crean o vinculan `place`
* se asignan categorías internas
* se asignan barrios cuando es posible
* se registran incidencias cuando hay problemas
* los contadores del run reflejan la ejecución real

---

## 20. Estado actual

La vertical OSM / Overpass ya ha sido implementada como una de las primeras verticales del proyecto.

Su papel actual es proporcionar una primera fuente abierta de locales gastronómicos y probar la integración entre:

* adquisición raw
* trazabilidad
* modelo multisource
* geografía oficial
* categorías internas
* incidencias de calidad

---

## 21. Próximas mejoras

Posibles mejoras futuras:

* mejorar matching con Google Places
* añadir deduplicación más robusta por proximidad
* ampliar taxonomía de tags OSM
* incorporar tags `cuisine` como señales gastronómicas
* generar métricas de cobertura por barrio
* crear vistas de locales OSM enriquecidos
* comparar cobertura OSM frente a Google Places
* mejorar gestión de ways y relations complejas

---

## 22. Conclusión

La vertical OSM / Overpass aporta una base abierta, trazable y georreferenciada de locales gastronómicos.

Su integración permite probar el modelo central de Hidden Gems y conectar adquisición, geografía, clasificación y calidad.

Aunque no aporta reseñas como fuente principal, es fundamental para construir cobertura espacial, validar barrios y preparar el sistema para integraciones posteriores con fuentes más ricas como Google Places.

---

## 23. Actualización final: papel de Overpass tras Sevilla IA v2

La fase Sevilla IA v2 no convierte Overpass en una fuente textual ni en una fuente directa de sentimiento, porque Overpass no aporta reseñas. Sin embargo, su valor dentro del repositorio sigue siendo importante.

Overpass aporta:

- una base abierta de locales gastronómicos;
- contraste frente a fuentes comerciales como Google Places;
- validación del modelo `place` + `place_source_ref`;
- cobertura geográfica inicial;
- categorías y tags abiertos;
- posibilidad futura de comparar cobertura OSM vs Google por barrio.

### 23.1. Relación con IA v2

El ranking Sevilla IA v2 se construyó principalmente sobre reviews reales de Google Places, porque la IA necesita texto. Por tanto, Overpass no participa directamente en:

```text
NER de platos
normalización de menciones
sentimiento ABSA
ranking basado en reseñas
```

Aun así, Overpass sigue siendo parte de la arquitectura multisource del proyecto y puede ayudar en futuras fases a:

- detectar locales presentes en OSM pero ausentes en Google;
- enriquecer cobertura territorial;
- validar si un local es estable o aparece en varias fuentes;
- reforzar señales de confianza de locales mediante presencia multisource;
- comparar densidad gastronómica por barrio.

### 23.2. Estado final para entrega

Para la entrega académica, la vertical queda cerrada como fuente funcional y documentada:

```text
[OK] Ingesta Overpass implementada
[OK] Raw y trazabilidad disponibles
[OK] Transformación a candidato común
[OK] Deduplicación intra-fuente
[OK] Importación canónica
[OK] Asignación territorial
[OK] Documentación actualizada
```

No es necesario ampliar Overpass para cerrar el PI. Las posibles mejoras pertenecen a una fase futura de producción o enriquecimiento multisource.

