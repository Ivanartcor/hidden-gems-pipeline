# Data Sources Overview

## 1. Finalidad del bloque de fuentes de datos

El bloque de fuentes de datos documenta el origen, función y tratamiento de cada fuente utilizada dentro de **Hidden Gems Pipeline**.

El proyecto no trabaja con una única fuente homogénea, sino con un ecosistema formado por fuentes abiertas, datasets geográficos oficiales, APIs externas, reviews reales y datasets de apoyo para inteligencia artificial.

Por ello, este bloque documenta:

- qué aporta cada fuente;
- qué tipo de datos proporciona;
- cómo entra en el pipeline;
- qué tablas o artefactos alimenta;
- qué limitaciones tiene;
- qué papel cumple dentro del modelo global;
- qué verticales están implementadas;
- qué fuentes se usan como datos operativos y cuáles como corpus/prototipo IA.

Este bloque sirve como referencia para entender por qué se ha elegido cada fuente y cómo se integra en el sistema Hidden Gems.

---

## 2. Enfoque general de adquisición de datos

La estrategia del proyecto se basa en combinar varias fuentes con roles complementarios.

No todas las fuentes tienen la misma función. Algunas son estructurales, otras aportan locales gastronómicos, otras aportan reseñas reales, y otras se utilizan para entrenar, validar o prototipar módulos de IA.

### Principio clave

El pipeline no trata las fuentes externas como verdad única. Cada fuente se incorpora de forma trazable y se adapta progresivamente al modelo interno.

Esto implica que:

- la información original se conserva en raw;
- cada ejecución queda registrada en `source_run` o, en el caso de procesos IA derivados, en `ai_pipeline_run`;
- cada asset fuente queda registrado en `raw_asset` cuando corresponde;
- cada representación fuente se vincula mediante `place_source_ref`;
- la entidad canónica interna sigue siendo `place`;
- las reseñas se guardan en `review` cuando existe relación clara con un `place`;
- los resultados IA derivados se almacenan en tablas separadas como `dish_mention`, `dish_place_signal` y `hidden_gem_candidate`.

---

## 3. Fuentes contempladas en el diseño

Las fuentes principales del proyecto son:

1. **Sevilla Geo**
2. **OSM / Overpass**
3. **Google Places**
4. **Google Places Reviews**
5. **Yelp Open Dataset**

Cada una cumple un papel distinto dentro de Hidden Gems Pipeline.

---

## 4. Sevilla Geo

### Tipo de fuente

Dataset geográfico de referencia.

### Rol dentro del sistema

Aporta la base territorial de Sevilla, especialmente barrios y distritos.

### Uso principal

Se utiliza para construir las tablas:

- `district`
- `neighborhood`

Y posteriormente para asignar locales gastronómicos a barrios mediante:

- `place_neighborhood_assignment`

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

- `restaurant`
- `bar`
- `cafe`
- `fast_food`
- `pub`

### Estado actual

La vertical está implementada y funcionando de extremo a extremo.

Actualmente el flujo incluye:

- ingesta raw;
- perfilado;
- transformación a `NormalizedPlaceCandidate`;
- QA sobre staging;
- deduplicación intra-fuente;
- importación canónica;
- comprobación post-importación.

### Tablas afectadas

- `place`
- `place_source_ref`
- `category`
- `place_category`
- `place_neighborhood_assignment`
- `validation_issue`

### Por qué es importante

OSM / Overpass permite avanzar con una fuente libre, gratuita y geolocalizada. Sirve como primera base de locales de Sevilla y como referencia abierta complementaria frente a fuentes dinámicas externas.

---

## 6. Google Places Text Search

### Tipo de fuente

API externa dinámica.

### Rol dentro del sistema

Google Places actúa como fuente dinámica principal para descubrimiento y enriquecimiento de locales gastronómicos.

### Uso principal

Permite mejorar o ampliar datos como:

- nombre comercial;
- dirección;
- coordenadas;
- Google Place ID;
- tipos/categorías de origen;
- estado operativo;
- URL de Google Maps;
- referencias externas en `place_source_ref`.

### Estado actual

La vertical está implementada y validada en modo controlado.

Incluye:

- conector `GooglePlacesConnector`;
- ingesta raw de Text Search;
- staging de candidatos;
- deduplicación intra-fuente;
- importación canónica;
- batch por barrios/distritos;
- checks de raw, staging, deduplicación, importación y batch.

### Tablas afectadas

- `source_system`
- `source_run`
- `raw_asset`
- `place`
- `place_source_ref`
- `category`
- `place_category`
- `place_neighborhood_assignment`
- `validation_issue`

### Consideración importante

Google Places requiere API key, facturación activa, control de cuotas y ejecución por tandas pequeñas. Por ello, el proyecto usa FieldMask limitado, `max_result_count` bajo, sin paginación masiva y sin `FieldMask: *`.

---

## 7. Google Places Reviews

### Tipo de fuente

Subvertical de Google Places basada en Place Details.

### Rol dentro del sistema

Aporta reseñas reales asociadas a locales ya consolidados en el modelo canónico.

### Uso principal

Las reviews de Google alimentan:

- `review`
- corpus local futuro para IA/NLP;
- análisis textual real de Sevilla;
- futura detección de platos y sentimiento por mención en datos locales.

### Estado actual

La subvertical está implementada y validada con batches controlados.

Incluye:

- Place Details sobre locales con `place_source_ref` de Google;
- raw trazable;
- staging de reviews;
- importación en `hidden_gems.review`;
- checks post-importación;
- batch de reviews.

### Tablas afectadas

- `source_system`
- `source_run`
- `raw_asset`
- `review`
- `validation_issue`

### Decisión clave

Las reviews de Google se consideran operativas porque están enlazadas a:

```text
review → place → place_neighborhood_assignment → neighborhood / district
```

Por tanto, son la fuente natural para el futuro ranking productivo de Sevilla.

---

## 8. Yelp Open Dataset

### Tipo de fuente

Dataset externo de apoyo para IA/NLP y prototipo.

### Rol dentro del sistema

Yelp se utiliza como corpus externo amplio para entrenar, validar y prototipar la inteligencia textual de Hidden Gems.

En la fase actual tiene dos usos complementarios:

1. **Corpus de entrenamiento y evaluación IA**: generación de datasets para detección de platos, normalización, sentimiento por mención y ranking experimental.
2. **Prototipo IA integrado en PostgreSQL**: importación controlada de negocios y reviews Yelp como corpus prototipo para conectar resultados IA con `place`, `review`, `dish_mention`, `dish_place_signal` y `hidden_gem_candidate`.

### Estado actual

La vertical Yelp y la integración IA están implementadas.

Se han completado:

- perfilado del TAR;
- extracción controlada de `business.json` y `review.json`;
- perfilado JSONL;
- subset de negocios gastronómicos;
- subset de reviews gastronómicas;
- corpus NLP Yelp;
- entrenamiento/prototipado IA;
- importación prototipo de Yelp en PostgreSQL;
- carga de catálogo de platos;
- carga de menciones y sentimiento;
- carga de señales y ranking;
- vistas SQL y script de demo de consultas.

### Tablas afectadas

En la parte de corpus/prototipo:

- `source_system`
- `source_run`
- `raw_asset`
- `place`
- `place_source_ref`
- `review`

En la capa IA:

- `ai_model_version`
- `ai_pipeline_run`
- `dish`
- `dish_alias`
- `dish_mention`
- `dish_mention_sentiment`
- `dish_place_signal`
- `hidden_gem_candidate`

### Consideración importante

Yelp no se considera producción Sevilla. Los resultados cargados se marcan como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

Su función es validar el pipeline IA completo y dejar preparada la arquitectura para aplicar el flujo a datos reales de Sevilla.

---

## 9. Clasificación de fuentes por función

| Fuente | Función principal | Tipo de dato | Estado |
|---|---|---|---|
| Sevilla Geo | Referencia territorial | Barrios, distritos, geometrías | Implementada |
| OSM / Overpass | POIs gastronómicos abiertos | Locales, coordenadas, tags | Implementada |
| Google Places Text Search | Descubrimiento/enriquecimiento de locales | Locales, coordenadas, tipos, estado | Implementada |
| Google Places Reviews | Reviews operativas locales | Reseñas enlazadas a `place` | Implementada |
| Yelp Open Dataset | Corpus IA/NLP y prototipo | Negocios, reviews, corpus, señales IA | Implementada como corpus/prototipo IA |

---

## 10. Estrategia de integración multi-fuente

La integración de varias fuentes se basa en una regla fundamental:

**las fuentes no se fusionan directamente entre sí.**

En su lugar, cada fuente produce su propia representación y se vincula al modelo interno mediante entidades específicas.

### 10.1. Raw independiente

Cada fuente conserva su payload original en `data/raw/` o, en el caso de datasets externos grandes, en `data/external/` y artefactos derivados controlados.

### 10.2. Transformación específica

Cada fuente tiene su propio transformer o proceso de normalización.

### 10.3. Candidato común

Las fuentes de negocio deben adaptarse progresivamente al contrato común `NormalizedPlaceCandidate` cuando alimentan `place` y `place_source_ref`.

### 10.4. Entidad canónica

La entidad interna consolidada es `place`.

### 10.5. Referencias por fuente

Cada aparición de un local en una fuente se conserva en `place_source_ref`.

### 10.6. Reviews source-bound

Las reseñas son dependientes de su fuente y no se fusionan entre fuentes.

### 10.7. Capa IA derivada

Los resultados de inteligencia artificial no se insertan directamente en `place`, sino en tablas derivadas:

- `dish`
- `dish_alias`
- `dish_mention`
- `dish_mention_sentiment`
- `dish_place_signal`
- `hidden_gem_candidate`

---

## 11. Diferencia entre fuentes de referencia, fuentes de negocio, reviews y corpus IA

Dentro del pipeline existen cuatro grandes tipos de fuente o uso.

### 11.1. Fuentes de referencia

No crean locales gastronómicos, sino datos estructurales necesarios para contextualizar el sistema.

Ejemplo:

- Sevilla Geo

Tablas principales:

- `district`
- `neighborhood`

### 11.2. Fuentes de negocio

Contienen información sobre locales gastronómicos.

Ejemplos:

- OSM / Overpass
- Google Places
- Yelp, solo en modo prototipo IA

Tablas principales:

- `place`
- `place_source_ref`
- `place_category`
- `place_neighborhood_assignment`

### 11.3. Fuentes de reviews operativas

Aportan reseñas enlazadas a locales canónicos.

Ejemplo:

- Google Places Reviews

Tabla principal:

- `review`

### 11.4. Fuentes de corpus IA/NLP

Aportan texto para entrenar, validar o prototipar modelos.

Ejemplo:

- Yelp Open Dataset

Artefactos y tablas principales:

- corpus JSONL;
- `review` en modo prototipo;
- tablas IA derivadas.

---

## 12. Criterios de selección de fuentes

Las fuentes se han elegido teniendo en cuenta varios criterios.

### 12.1. Utilidad para el dominio

Deben aportar información relevante para descubrir locales, platos o zonas gastronómicas.

### 12.2. Disponibilidad

Se priorizan fuentes accesibles para prototipado y desarrollo inicial.

### 12.3. Trazabilidad

Deben poder integrarse en un flujo donde sea posible registrar qué se ha descargado, cuándo y desde dónde.

### 12.4. Complementariedad

No se busca que todas las fuentes aporten lo mismo. El valor aparece al combinar fuentes con roles distintos.

### 12.5. Viabilidad técnica

Se ha priorizado una estrategia realista para avanzar por fases, empezando por fuentes libres y datasets estructurales, y escalando después a APIs y módulos IA.

---

## 13. Estado actual de integración

Actualmente el proyecto ha validado varias verticales y una capa IA completa.

### Sevilla Geo

- carga de referencia territorial completada;
- barrios y distritos disponibles en base de datos;
- preparada para enriquecimiento geográfico de locales.

### OSM Overpass

- POIs gastronómicos extraídos y normalizados;
- candidatos deduplicados;
- locales importados al modelo canónico;
- asignación de categoría y barrio aplicada.

### Google Places

- Text Search operativo;
- batch por barrios/distritos;
- importación canónica;
- checks de batch y de importación.

### Google Places Reviews

- Place Details Reviews operativo;
- reviews reales importadas en `review`;
- batch de reviews validado.

### Yelp Open Dataset

- corpus NLP generado y validado;
- prototipo IA desarrollado;
- datos Yelp mínimos importados como corpus/prototipo;
- resultados IA cargados en PostgreSQL;
- ranking `yelp_prototype` consultable mediante vistas.

---

## 14. Riesgos y limitaciones generales

Cada fuente tiene limitaciones propias.

### Sevilla Geo

- depende del dataset geográfico disponible;
- requiere mantener consistencia de geometrías;
- puede requerir actualización si cambian límites administrativos.

### OSM / Overpass

- datos colaborativos, no siempre completos;
- tags muy heterogéneos;
- nombres o direcciones ausentes en algunos registros;
- posibilidad de duplicados técnicos.

### Google Places

- uso sujeto a API key, cuotas y costes;
- dependencia externa;
- posible necesidad de control de gasto;
- Google no devuelve necesariamente todas las reseñas históricas;
- escalado controlado por batches.

### Yelp Open Dataset

- no representa Sevilla;
- corpus mayoritariamente en inglés;
- posible sesgo geográfico;
- no debe usarse como ranking productivo local;
- resultados actuales son prototipo IA, no producción.

---

## 15. Relación de fuentes con la IA de Hidden Gems

La capa IA se ha construido inicialmente sobre Yelp porque aporta volumen suficiente para desarrollar y validar los módulos:

```text
reviews Yelp
→ detección de platos
→ normalización
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems v1
```

Los resultados se han integrado en PostgreSQL como prototipo trazable.

El siguiente salto será aplicar el flujo a reviews reales de Sevilla, principalmente Google Places Reviews:

```text
Google Reviews Sevilla
→ export_reviews_for_ai
→ adaptación IA/multilingüe
→ señales por place + dish
→ ranking por barrio
```

---

## 16. Conclusión

La estrategia de fuentes de Hidden Gems Pipeline se basa en combinar datos de naturaleza distinta para construir una base gastronómica más rica y útil.

Las fuentes no se incorporan de forma aislada ni se mezclan directamente. Cada una pasa por un flujo controlado de adquisición, raw, transformación, validación, persistencia y comprobación.

Con Sevilla Geo, OSM Overpass, Google Places, Google Places Reviews y Yelp Open Dataset ya integrados en distintos niveles, el proyecto cuenta con una base sólida para pasar del prototipo IA validado al futuro ranking operativo por barrios de Sevilla.
