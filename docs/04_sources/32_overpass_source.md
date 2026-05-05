# OSM Overpass Source

## 1. Descripción general

**OSM Overpass** es la fuente abierta utilizada por Hidden Gems Pipeline para obtener una primera base real de locales gastronómicos geolocalizados.

La fuente se apoya en datos de **OpenStreetMap** y se consulta mediante la API de **Overpass**, permitiendo extraer elementos etiquetados como puntos de interés gastronómicos dentro de una zona concreta.

En la fase actual del proyecto, Overpass cumple un papel esencial porque permite avanzar con una fuente gratuita, abierta y suficientemente rica antes de incorporar fuentes dinámicas más restrictivas, como Google Places.

---

## 2. Rol dentro del pipeline

OSM Overpass actúa como una **fuente de negocio geolocalizada**.

A diferencia de Sevilla Geo, que alimenta la capa territorial, Overpass aporta candidatos reales de locales gastronómicos que pueden convertirse en entidades canónicas dentro del modelo.

### Tablas principales que alimenta

* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`
* `validation_issue`

### Entidades intermedias utilizadas

Antes de llegar a base de datos, los elementos de Overpass se transforman en:

* `NormalizedPlaceCandidate`

Esta estructura común permite que Overpass, Google Places y Yelp puedan alinearse en una representación intermedia compartida.

---

## 3. Tipo de datos obtenidos

Overpass devuelve elementos OSM de distintos tipos:

* `node`
* `way`
* `relation`

Cada elemento puede contener:

* identificador OSM
* tipo de elemento
* coordenadas directas o centroide
* conjunto de tags
* nombre del local
* categoría `amenity`
* tipo de cocina `cuisine`
* dirección
* teléfono
* web
* horario
* marca
* atributos como terraza, accesibilidad o comida para llevar

---

## 4. Consulta utilizada

La consulta actual se centra en locales gastronómicos dentro de un bounding box de Sevilla.

### Amenities principales

Los valores utilizados por defecto son:

* `restaurant`
* `bar`
* `cafe`
* `fast_food`
* `pub`

Estos valores permiten capturar una base amplia de establecimientos potencialmente relevantes para Hidden Gems.

---

## 5. Ejemplo de estructura raw

Un elemento tipo `node` puede tener una estructura como:

```json
{
  "type": "node",
  "id": 303570057,
  "lat": 37.382913,
  "lon": -5.9724153,
  "tags": {
    "addr:city": "Sevilla",
    "addr:postcode": "41018",
    "addr:street": "Eduardo Dato",
    "amenity": "restaurant",
    "name": "Jaque Mate Tapas",
    "outdoor_seating": "yes",
    "wheelchair": "yes"
  }
}
```

Un elemento tipo `way` o `relation` puede traer coordenadas a través de `center`:

```json
{
  "type": "way",
  "id": 576107315,
  "center": {
    "lat": 37.3435481,
    "lon": -5.9763044
  },
  "tags": {
    "amenity": "restaurant",
    "name": "De Lonja Sevilla",
    "cuisine": "spanish"
  }
}
```

---

## 6. Resultado real obtenido en la primera vertical

En la primera ejecución relevante de Overpass sobre Sevilla se obtuvo un volumen aproximado de más de dos mil elementos gastronómicos.

La distribución observada fue mayoritariamente de `node`, con una cantidad menor de `way` y una presencia muy reducida de `relation`.

Esto confirmó que la estrategia de extracción debía contemplar:

* coordenadas directas para `node`
* coordenadas desde `center` para `way` y `relation`
* tags heterogéneos y de distinta calidad

---

## 7. Campos y tags relevantes

El perfilado del raw permitió detectar un conjunto amplio de tags.

### Tags principales

* `amenity`
* `name`
* `official_name`
* `brand`
* `cuisine`
* `addr:street`
* `addr:housenumber`
* `addr:postcode`
* `addr:city`
* `phone`
* `website`
* `opening_hours`
* `wheelchair`
* `takeaway`
* `delivery`
* `outdoor_seating`
* `indoor_seating`

### Decisión tomada

No todos los tags se modelan como columnas específicas.

La estrategia seguida es:

* extraer y normalizar un núcleo común de campos relevantes
* conservar el conjunto completo de tags en `source_attributes`
* conservar el elemento raw completo en `source_payload`

Esto evita perder información sin sobredimensionar el modelo relacional.

---

## 8. Flujo implementado

La vertical Overpass está implementada de extremo a extremo.

### 8.1. Ingesta raw

El conector ejecuta una query Overpass y guarda el resultado en `data/raw/osm_overpass/`.

También registra:

* `source_run`
* `raw_asset`
* metadata de ejecución

### 8.2. Perfilado

Se analiza el raw para conocer:

* campos top-level
* tags disponibles
* frecuencia de categorías
* presencia de nombre
* presencia de dirección
* presencia de teléfono, web y horario

### 8.3. Transformación

Los elementos OSM se transforman en `NormalizedPlaceCandidate`.

Durante esta fase se extraen:

* identidad fuente
* nombre
* dirección
* coordenadas
* categoría
* información de negocio
* señales de calidad
* payload fuente

### 8.4. QA de staging

Se revisan los candidatos generados para detectar:

* candidatos aceptados
* candidatos que requieren revisión
* carencias frecuentes
* duplicados potenciales
* distribución de categorías y marcas

### 8.5. Deduplicación intra-fuente

Se agrupan candidatos de Overpass que probablemente representan el mismo local.

La deduplicación se apoya en señales como:

* nombre normalizado
* distancia geográfica
* teléfono
* web
* categoría
* marca
* dirección

Actualmente esta fase está operativa, aunque existe margen futuro para afinar algunos casos concretos de direcciones poco específicas.

### 8.6. Importación canónica

Los candidatos únicos se importan al modelo canónico.

Se crean o actualizan:

* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`

### 8.7. Comprobación post-importación

Se valida el resultado final en base de datos mediante un script específico.

---

## 9. Componentes implementados

### Conector

```text
src/connectors/overpass.py
```

Responsable de:

* construir y ejecutar consultas Overpass
* recibir el payload
* guardar raw
* registrar trazabilidad

### Transformer

```text
src/normalization/osm_overpass_transformer.py
```

Responsable de:

* recorrer `elements`
* validar estructura
* extraer coordenadas
* normalizar nombre, dirección y categoría
* construir `NormalizedPlaceCandidate`

### Deduplicador

```text
src/normalization/osm_overpass_deduplicator.py
```

Responsable de:

* detectar duplicados probables dentro de Overpass
* agrupar candidatos
* elegir representantes
* generar evidencias de deduplicación

### Importer

```text
src/normalization/osm_overpass_importer.py
```

Responsable de:

* importar candidatos únicos a la base canónica
* crear o actualizar `place`
* crear o actualizar `place_source_ref`
* asignar categoría primaria
* asignar barrio y distrito

### Scripts operativos

```text
scripts/run_overpass_ingestion.py
scripts/profile_overpass_raw.py
scripts/transform_overpass_candidates.py
scripts/check_overpass_staging.py
scripts/deduplicate_overpass_candidates.py
scripts/import_overpass_places.py
scripts/check_overpass_import.py
scripts/load_overpass_pipeline.py
```

---

## 10. Script principal de ejecución completa

La vertical completa se ejecuta con:

```bash
python -m scripts.load_overpass_pipeline \
  --south 37.3400 \
  --west -6.0400 \
  --north 37.4300 \
  --east -5.9200 \
  --query-name sevilla_gastronomy_bbox
```

Este script orquesta:

1. ingesta raw
2. transformación
3. deduplicación
4. importación canónica
5. generación de artefactos
6. resumen final

---

## 11. Scripts por fase

Además del script completo, la vertical puede ejecutarse por fases.

### Ingesta raw

```bash
python -m scripts.run_overpass_ingestion \
  --south 37.3400 \
  --west -6.0400 \
  --north 37.4300 \
  --east -5.9200 \
  --query-name sevilla_gastronomy_bbox
```

### Perfilado raw

```bash
python -m scripts.profile_overpass_raw --raw-asset-id <raw_asset_id> --save-artifact
```

### Transformación

```bash
python -m scripts.transform_overpass_candidates --raw-asset-id <raw_asset_id>
```

### QA staging

```bash
python -m scripts.check_overpass_staging --raw-asset-id <raw_asset_id> --save-artifact
```

### Deduplicación

```bash
python -m scripts.deduplicate_overpass_candidates --raw-asset-id <raw_asset_id>
```

### Importación canónica

```bash
python -m scripts.import_overpass_places --raw-asset-id <raw_asset_id>
```

### Comprobación final

```bash
python -m scripts.check_overpass_import
```

---

## 12. Artefactos generados

La vertical Overpass genera artefactos en varias capas.

### Raw

```text
data/raw/osm_overpass/YYYY/MM/DD/<run_code>/...
```

### Staging

```text
data/staging/osm_overpass/<raw_asset_id>/
```

Contiene:

* `summary.json`
* `accepted_candidates.json`
* `needs_review_candidates.json`
* `rejected_candidates.json`
* `issues.json`

### Deduplicación

```text
data/staging/osm_overpass/<raw_asset_id>/deduplication/
```

Contiene:

* `dedup_summary.json`
* `unique_candidates.json`
* `duplicate_groups.json`
* `pair_evidences.json`

### Importación

```text
data/staging/osm_overpass/<raw_asset_id>/deduplication/import/
```

Contiene:

* `import_summary.json`

### Artifacts

```text
data/artifacts/overpass_profiles/
data/artifacts/overpass_qa/
data/artifacts/logs/
```

---

## 13. Tratamiento de coordenadas

La extracción de coordenadas depende del tipo de elemento.

### `node`

Se utilizan directamente:

* `lat`
* `lon`

### `way` y `relation`

Se utiliza:

* `center.lat`
* `center.lon`

Si no existen coordenadas utilizables, el candidato no debe pasar a importación automática.

---

## 14. Tratamiento de nombres

La prioridad para resolver el nombre del local es:

1. `name`
2. `official_name`
3. `brand`

A partir de ese valor se genera:

* `source_name_raw`
* `display_name`
* `normalized_name`

Los candidatos sin nombre pueden mantenerse como `needs_review`, pero no forman parte del import automático inicial.

---

## 15. Tratamiento de categorías

La categoría principal fuente se deriva desde:

* `amenity`

La información de cocina se extrae desde:

* `cuisine`

La estrategia actual es:

* usar `amenity` como categoría primaria fuente
* conservar `cuisine` como señal complementaria
* crear o reutilizar categorías internas en `category`
* asignar categoría primaria en `place_category`

---

## 16. Tratamiento de dirección y contacto

Cuando están disponibles, se extraen:

* calle
* número
* código postal
* ciudad
* teléfono
* web
* email
* horario

Sin embargo, muchos registros OSM no contienen toda esta información. Por eso el pipeline calcula señales de completitud y conserva siempre el payload completo para posibles mejoras posteriores.

---

## 17. Deduplicación intra-fuente

La deduplicación de Overpass busca reducir duplicados técnicos antes de crear o actualizar entidades canónicas.

### Señales utilizadas

* mismo nombre normalizado
* proximidad geográfica
* mismo teléfono
* misma web
* misma categoría
* misma marca
* misma dirección

### Decisión importante

No se deduplica solo por nombre, porque cadenas como `McDonald's`, `Burger King`, `Starbucks` o `100 Montaditos` pueden aparecer varias veces en la ciudad y representar locales distintos.

---

## 18. Limitaciones conocidas

OSM / Overpass es una fuente muy útil, pero tiene limitaciones:

* datos colaborativos y heterogéneos
* campos incompletos
* direcciones ausentes en muchos registros
* tags con formatos variados
* posibilidad de duplicados técnicos
* posibilidad de locales cerrados o desactualizados
* categorías no siempre homogéneas

Estas limitaciones se mitigan mediante:

* perfilado
* staging
* señales de calidad
* deduplicación
* trazabilidad raw
* comprobaciones post-importación

---

## 19. Estado actual

La vertical OSM Overpass está implementada y operativa.

Actualmente cubre:

* adquisición
* raw storage
* profiling
* transformación a candidato común
* QA staging
* deduplicación
* importación canónica
* comprobación

Es la primera vertical de negocio completa del proyecto.

---

## 20. Conclusión

OSM Overpass proporciona a Hidden Gems Pipeline una fuente abierta, geolocalizada y útil para construir una primera base real de locales gastronómicos.

Aunque sus datos no son perfectos, la arquitectura del pipeline permite tratarlos de forma controlada, conservando raw, normalizando información útil, separando candidatos dudosos y cargando solo datos suficientemente fiables en el modelo canónico.

Esta vertical demuestra que el sistema ya puede pasar de una fuente externa real a entidades internas utilizables para análisis por barrio.

