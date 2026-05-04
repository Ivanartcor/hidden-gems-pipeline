## 1. Descripción general

**Yelp Open Dataset** está previsto como una fuente de apoyo para el desarrollo de capacidades de análisis textual, reviews y NLP dentro de Hidden Gems Pipeline.

A diferencia de Sevilla Geo, que aporta geografía, y de Overpass o Google Places, que se orientan a locales geolocalizados, Yelp tiene un valor especialmente relevante por su estructura de negocios y reseñas.

Su integración está pensada principalmente para apoyar fases futuras relacionadas con extracción de platos, análisis de opiniones y construcción de señales de ranking.

---

## 2. Rol previsto dentro del pipeline

Yelp actuará como una **fuente de negocio y texto**.

Su papel será doble:

1. aportar datos estructurados de negocios
2. aportar reseñas útiles para experimentación NLP

### Usos previstos

* análisis de reseñas gastronómicas
* extracción de menciones de platos
* pruebas de limpieza textual
* entrenamiento o validación de heurísticas NLP
* generación de señales de popularidad o satisfacción
* apoyo a rankings futuros

---

## 3. Diferencia respecto a las otras fuentes

Yelp no cumple exactamente el mismo rol que Overpass o Google Places.

| Fuente        | Rol principal                                |
| ------------- | -------------------------------------------- |
| Sevilla Geo   | Referencia territorial                       |
| Overpass      | POIs gastronómicos abiertos y geolocalizados |
| Google Places | Enriquecimiento dinámico de negocio          |
| Yelp          | Reviews, negocios y apoyo NLP                |

La utilidad principal de Yelp está menos centrada en la cobertura local inmediata de Sevilla y más en el tratamiento de reseñas y señales textuales.

---

## 4. Tipo de información esperada

El dataset de Yelp puede aportar información como:

### Negocios

* identificador de negocio
* nombre
* dirección
* ciudad
* coordenadas
* categorías
* rating
* número de reseñas
* estado abierto/cerrado

### Reviews

* identificador de review
* identificador de negocio
* identificador de usuario
* puntuación
* texto de la reseña
* fecha

### Otros datos posibles

* tips
* atributos del negocio
* horarios
* metadata complementaria

---

## 5. Encaje con el modelo de datos

Yelp puede integrarse en varias partes del modelo.

### Negocios

Los negocios de Yelp pueden transformarse en `NormalizedPlaceCandidate` y posteriormente enlazarse con:

* `place`
* `place_source_ref`
* `place_category`
* `place_neighborhood_assignment`

### Reviews

Las reseñas deben cargarse en:

* `review`

### Decisión importante

Las reviews son **source-bound**.

Esto significa que una reseña de Yelp no se fusiona con reseñas de Google u otra fuente. Cada review conserva su origen y su vinculación a la fuente que la proporciona.

---

## 6. Estrategia prevista de integración

La integración de Yelp debería dividirse en dos líneas.

## 6.1. Línea de negocios

Objetivo:

* transformar negocios Yelp a candidatos comunes
* enlazarlos con `place`
* guardar representación en `place_source_ref`

Flujo previsto:

1. leer dataset de negocios
2. guardar raw
3. perfilar estructura
4. transformar a `NormalizedPlaceCandidate`
5. aplicar matching
6. importar a modelo canónico

## 6.2. Línea de reviews

Objetivo:

* cargar reseñas asociadas a negocios
* conservar texto y metadata
* preparar base para NLP

Flujo previsto:

1. leer dataset de reviews
2. guardar raw o particiones raw
3. validar estructura
4. asociar review con negocio fuente
5. importar a `review`
6. generar artefactos para análisis NLP

---

## 7. Relación con NLP

Yelp será especialmente útil para fases posteriores de procesamiento de lenguaje natural.

### Posibles tareas NLP

* limpieza de texto
* detección de idioma
* extracción de nombres de platos
* análisis de sentimiento
* detección de términos gastronómicos
* clustering de menciones culinarias
* ranking de platos por frecuencia y valoración

### Relación con Hidden Gems

El objetivo final de Hidden Gems no es solo listar locales, sino descubrir platos destacados por barrio. Para eso se necesitará analizar texto de reseñas y menciones gastronómicas.

Yelp puede servir como una fuente inicial para desarrollar y validar esa lógica.

---

## 8. Encaje con `NormalizedPlaceCandidate`

La parte de negocios de Yelp deberá mapearse al contrato común.

### Campos esperados

* `source_system_code`: `yelp`
* `source_entity_type`: `business`
* `source_record_id`: identificador de negocio Yelp
* `source_name_raw`
* `normalized_name`
* `source_address_raw`
* `latitude`
* `longitude`
* `source_primary_category_raw`
* `source_categories_raw`
* `source_rating`
* `source_review_count`
* `source_payload`

Esto permitirá que Yelp participe en el mismo flujo de matching y consolidación que el resto de fuentes de negocio.

---

## 9. Encaje con `review`

Las reseñas de Yelp deben mantener su identidad propia.

### Campos esperados en la lógica de importación

* fuente
* identificador externo de review
* identificador externo de negocio
* rating
* texto
* fecha
* payload fuente

### Principio aplicado

Las reviews no se fusionan entre fuentes.

Esto permite mantener la trazabilidad textual y evita mezclar opiniones que pertenecen a contextos distintos.

---

## 10. Flujo previsto

La vertical Yelp debería seguir un flujo por fases.

### Fase 1. Ingesta raw

* leer ficheros del dataset
* conservar copia raw o referencia de origen
* registrar ejecución

### Fase 2. Perfilado

* analizar estructura
* contar negocios
* contar reviews
* revisar categorías
* revisar idiomas y campos textuales

### Fase 3. Transformación de negocios

* convertir negocios a `NormalizedPlaceCandidate`
* normalizar nombre, dirección y categorías
* validar coordenadas

### Fase 4. Importación de negocios

* crear o actualizar `place_source_ref`
* enlazar con `place`
* asignar categorías y geografía si aplica

### Fase 5. Transformación de reviews

* validar estructura textual
* limpiar campos mínimos
* preparar carga en `review`

### Fase 6. Importación de reviews

* insertar reseñas asociadas a la fuente
* mantener trazabilidad del origen

### Fase 7. Artefactos NLP

* generar datasets preparados para análisis textual posterior

---

## 11. Diferencias respecto a Overpass

| Aspecto                   | Overpass              | Yelp                            |
| ------------------------- | --------------------- | ------------------------------- |
| Tipo principal            | POIs geolocalizados   | Negocios y reseñas              |
| Texto largo               | No                    | Sí                              |
| Reviews                   | No                    | Sí                              |
| Cobertura local           | Depende de OSM        | Depende del dataset             |
| Utilidad principal actual | Base de locales       | NLP y análisis textual          |
| Importación inicial       | `place` y referencias | `place`, referencias y `review` |

---

## 12. Consideraciones de volumen

El dataset de Yelp puede tener mayor volumen que otras fuentes, especialmente en la parte de reviews.

Esto implica que la vertical debe diseñarse teniendo en cuenta:

* lectura eficiente
* posible procesamiento por lotes
* control de memoria
* particionado de raw o staging
* importación incremental
* validación por fases

---

## 13. Calidad y validación prevista

La vertical deberá validar al menos:

### En negocios

* identificador externo
* nombre
* coordenadas
* categorías
* rating
* número de reviews

### En reviews

* identificador de review
* identificador de negocio
* rating
* texto no vacío
* fecha válida

Las incidencias deberán registrarse en `validation_issue`.

---

## 14. Riesgos y limitaciones

### Riesgos principales

* dataset grande
* posible desalineación geográfica con Sevilla
* categorías diferentes a las usadas por otras fuentes
* textos con ruido
* idiomas variados
* reviews no directamente comparables entre fuentes

### Mitigación

* perfilado previo
* transformación separada de negocios y reviews
* uso de `NormalizedPlaceCandidate` para negocios
* reviews ligadas a fuente
* limpieza textual en fases NLP posteriores
* procesamiento por lotes si el volumen lo requiere

---

## 15. Estado actual

La vertical Yelp está pendiente de implementación.

Actualmente el proyecto ya tiene elementos que facilitarán su integración futura:

* modelo `place` / `place_source_ref`
* entidad `review`
* contrato `NormalizedPlaceCandidate`
* sistema de raw y staging
* trazabilidad con `source_run` y `raw_asset`
* experiencia previa con Overpass como vertical de negocio

---

## 16. Conclusión

Yelp Open Dataset será una fuente importante para ampliar Hidden Gems Pipeline hacia análisis textual y extracción de conocimiento gastronómico desde reseñas.

Su valor principal no está solo en aportar negocios, sino en permitir trabajar con opiniones, menciones de platos y señales textuales que serán necesarias para fases posteriores del proyecto.

Cuando se implemente, deberá seguir el mismo enfoque arquitectónico del resto del sistema: raw trazable, transformación controlada, modelo común para negocios, reviews ligadas a fuente y validaciones explícitas de calidad.
