# docs/04_sources/30_data_sources_overview.md

# Data Sources Overview

## 1. Finalidad del bloque de fuentes de datos

El bloque de fuentes de datos documenta el origen, función y tratamiento de cada fuente utilizada o prevista dentro de **Hidden Gems Pipeline**.

El proyecto no trabaja con una única fuente homogénea, sino con un ecosistema de datos formado por fuentes abiertas, datasets geográficos oficiales, APIs externas y datasets de apoyo para procesamiento textual.

Por ello, es importante documentar:

* qué aporta cada fuente
* qué tipo de datos proporciona
* cómo entra en el pipeline
* qué limitaciones tiene
* qué papel cumple dentro del modelo global
* qué verticales están ya implementadas y cuáles quedan pendientes

Este bloque sirve como referencia para entender por qué se ha elegido cada fuente y cómo se integra en el sistema.

---

## 2. Enfoque general de adquisición de datos

La estrategia del proyecto se basa en combinar varias fuentes con roles complementarios.

No todas las fuentes tienen la misma función. Algunas son estructurales, otras aportan locales gastronómicos, otras servirán para enriquecer información de negocio y otras serán útiles para NLP y análisis de reseñas.

### Principio clave

El pipeline no trata las fuentes externas como verdad única. Cada fuente se incorpora de forma trazable y se adapta progresivamente al modelo interno.

Esto implica que:

* la información original se conserva en raw
* cada ejecución queda registrada en `source_run`
* cada asset queda registrado en `raw_asset`
* cada representación fuente se vincula a `place_source_ref`
* la entidad canónica interna sigue siendo `place`

---

## 3. Fuentes contempladas en el diseño

Las fuentes principales del proyecto son:

1. **Sevilla Geo**
2. **OSM / Overpass**
3. **Google Places**
4. **Yelp Open Dataset**

Cada una cumple un papel distinto dentro de Hidden Gems Pipeline.

---

## 4. Sevilla Geo

### Tipo de fuente

Dataset geográfico de referencia.

### Rol dentro del sistema

Aporta la base territorial de Sevilla, especialmente barrios y distritos.

### Uso principal

Se utiliza para construir las tablas:

* `district`
* `neighborhood`

Y posteriormente para asignar locales gastronómicos a barrios mediante:

* `place_neighborhood_assignment`

### Estado actual

La vertical está implementada y funcionando de extremo a extremo.

### Por qué es importante

Hidden Gems está orientado a descubrir información gastronómica por barrio. Por tanto, la geografía oficial no es una capa secundaria, sino una pieza central del sistema.

Sin esta fuente, los locales podrían tener coordenadas, pero no estarían conectados con unidades territoriales útiles para análisis, ranking o visualización.

---

## 5. OSM / Overpass

### Tipo de fuente

Fuente abierta de puntos de interés geolocalizados.

### Rol dentro del sistema

Aporta una primera base real de locales gastronómicos usando datos de OpenStreetMap consultados mediante Overpass.

### Uso principal

Permite obtener POIs gastronómicos dentro de un bounding box de Sevilla a partir de valores como:

* `restaurant`
* `bar`
* `cafe`
* `fast_food`
* `pub`

### Estado actual

La vertical está implementada y funcionando de extremo a extremo.

Actualmente el flujo incluye:

* ingesta raw
* perfilado
* transformación a `NormalizedPlaceCandidate`
* QA sobre staging
* deduplicación intra-fuente
* importación canónica
* comprobación post-importación

### Tablas afectadas

* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`
* `validation_issue`

### Por qué es importante

OSM / Overpass permite avanzar con una fuente libre, gratuita y geolocalizada antes de incorporar fuentes externas con restricciones o claves API, como Google Places.

---

## 6. Google Places

### Tipo de fuente

API externa dinámica.

### Rol previsto dentro del sistema

Google Places está previsto como una fuente de enriquecimiento y consolidación de locales gastronómicos.

### Uso esperado

Permitirá mejorar datos como:

* nombre comercial
* dirección
* coordenadas
* teléfono
* web
* estado operativo
* categoría
* rating
* número de reseñas

### Estado actual

Vertical pendiente de implementación.

### Consideración importante

Por coste, límites y necesidad de API key, se ha decidido no comenzar por Google Places. Primero se han implementado fuentes libres y estructurales para validar la arquitectura del pipeline.

---

## 7. Yelp Open Dataset

### Tipo de fuente

Dataset abierto de apoyo.

### Rol previsto dentro del sistema

Yelp se contempla como fuente de apoyo para análisis textual, reviews y experimentación con NLP.

### Uso esperado

Podrá servir para:

* trabajar con reseñas
* preparar extracción de platos
* ensayar análisis de texto gastronómico
* alimentar fases de ranking o scoring en fases futuras

### Estado actual

Vertical pendiente de implementación.

### Consideración importante

El rol de Yelp no es necesariamente sustituir a las fuentes locales de Sevilla, sino proporcionar una base de apoyo útil para NLP y análisis de reseñas.

---

## 8. Clasificación de fuentes por función

Las fuentes pueden clasificarse según su función principal dentro del pipeline.

| Fuente            | Función principal               | Tipo de dato                      | Estado       |
| ----------------- | ------------------------------- | --------------------------------- | ------------ |
| Sevilla Geo       | Referencia territorial          | Barrios, distritos, geometrías    | Implementada |
| OSM / Overpass    | POIs gastronómicos              | Locales, coordenadas, tags        | Implementada |
| Google Places     | Enriquecimiento y consolidación | Locales, contacto, rating, estado | Pendiente    |
| Yelp Open Dataset | Apoyo NLP / reviews             | Negocios y reseñas                | Pendiente    |

---

## 9. Estrategia de integración multi-fuente

La integración de varias fuentes se basa en una regla fundamental:

**las fuentes no se fusionan directamente entre sí.**

En su lugar, cada fuente produce su propia representación y se vincula al modelo interno mediante entidades específicas.

### 9.1. Raw independiente

Cada fuente conserva su payload original en `data/raw/`.

### 9.2. Transformación específica

Cada fuente tiene su propio transformer o proceso de normalización.

### 9.3. Candidato común

Las fuentes de negocio deben adaptarse progresivamente al contrato común `NormalizedPlaceCandidate`.

### 9.4. Entidad canónica

La entidad interna consolidada es `place`.

### 9.5. Referencias por fuente

Cada aparición de un local en una fuente se conserva en `place_source_ref`.

---

## 10. Diferencia entre fuentes de referencia y fuentes de negocio

Dentro del pipeline existen dos grandes tipos de fuentes.

## 10.1. Fuentes de referencia

Son fuentes que no crean directamente locales gastronómicos, sino datos estructurales necesarios para contextualizar el sistema.

Ejemplo:

* Sevilla Geo

Estas fuentes alimentan tablas como:

* `district`
* `neighborhood`

## 10.2. Fuentes de negocio

Son fuentes que contienen información sobre locales, reseñas o datos gastronómicos.

Ejemplos:

* OSM / Overpass
* Google Places
* Yelp

Estas fuentes alimentan, directa o indirectamente:

* `place`
* `place_source_ref`
* `review`
* `place_category`
* `place_neighborhood_assignment`

---

## 11. Criterios de selección de fuentes

Las fuentes se han elegido teniendo en cuenta varios criterios:

### 11.1. Utilidad para el dominio

Deben aportar información relevante para descubrir locales, platos o zonas gastronómicas.

### 11.2. Disponibilidad

Se priorizan fuentes accesibles para prototipado y desarrollo inicial.

### 11.3. Trazabilidad

Deben poder integrarse en un flujo donde sea posible registrar qué se ha descargado, cuándo y desde dónde.

### 11.4. Complementariedad

No se busca que todas las fuentes aporten lo mismo. El valor aparece al combinar fuentes con roles distintos.

### 11.5. Viabilidad técnica

Se ha priorizado una estrategia realista para avanzar por fases, empezando por fuentes libres y datasets estructurales.

---

## 12. Estado actual de integración

Actualmente el proyecto ha validado la arquitectura con dos verticales completas.

### Sevilla Geo

* carga de referencia territorial completada
* barrios y distritos disponibles en base de datos
* preparada para enriquecimiento geográfico de locales

### OSM Overpass

* POIs gastronómicos extraídos y normalizados
* candidatos deduplicados
* locales importados al modelo canónico
* asignación de categoría y barrio aplicada

Esto demuestra que el pipeline ya es capaz de integrar tanto una fuente geográfica de referencia como una fuente de negocio geolocalizada.

---

## 13. Riesgos y limitaciones generales

Cada fuente tiene limitaciones propias.

### Sevilla Geo

* depende del dataset geográfico disponible
* requiere mantener consistencia de geometrías
* puede requerir actualización si cambian límites administrativos

### OSM / Overpass

* datos colaborativos, no siempre completos
* tags muy heterogéneos
* nombres o direcciones ausentes en algunos registros
* posibilidad de duplicados técnicos

### Google Places

* uso sujeto a API key, cuotas y costes
* dependencia externa
* posible necesidad de control de gasto

### Yelp

* dataset no necesariamente centrado en Sevilla
* utilidad mayor para NLP que para cobertura local directa

---

## 14. Conclusión

La estrategia de fuentes de Hidden Gems Pipeline se basa en combinar datos de naturaleza distinta para construir una base gastronómica más rica y útil.

Las fuentes no se incorporan de forma aislada ni se mezclan directamente. Cada una pasa por un flujo controlado de adquisición, raw, transformación, validación y persistencia.

Con Sevilla Geo y OSM Overpass ya implementadas, el proyecto cuenta con una primera base sólida: territorio oficial y locales gastronómicos reales. Las siguientes fuentes, Google Places y Yelp, permitirán enriquecer y ampliar esa base en fases posteriores.