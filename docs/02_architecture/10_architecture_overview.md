# Visión de la arquitectura

## 1. Finalidad de la arquitectura

La arquitectura de **Hidden Gems Pipeline** está diseñada para soportar un procesamiento de datos gastronómicos **modular, reproducible, trazable y extensible**. Su función no es solo descargar información desde varias fuentes, sino transformarla progresivamente hasta convertirla en una base canónica preparada para análisis, enriquecimiento geográfico, matching multi-fuente y explotación posterior.

Desde el principio se buscó una arquitectura que permitiera trabajar con datos heterogéneos sin perder control del flujo ni trazabilidad sobre lo que ocurre en cada ejecución. Por eso el sistema se apoya en capas bien diferenciadas, un modelo relacional orientado a negocio y una organización del código pensada para separar claramente adquisición, transformación, calidad, geografía y persistencia.

---

## 2. Principios de diseño

La arquitectura del proyecto se apoya en varios principios clave:

### 2.1. Trazabilidad primero

Cada ejecución del pipeline debe poder reconstruirse. Para ello se registran:

* el sistema fuente
* la ejecución concreta (`source_run`)
* el asset raw generado (`raw_asset`)
* las incidencias detectadas (`validation_issue`)

### 2.2. Separación por capas

No se mezclan descarga, transformación y consolidación en una sola fase. Cada paso tiene una responsabilidad concreta.

### 2.3. No perder el raw

La información original descargada desde la fuente se conserva siempre antes de aplicar limpieza o normalización.

### 2.4. Modelo canónico interno

Las fuentes externas no se consideran el modelo final. La entidad central del sistema es `place`, mientras que `place_source_ref` conserva la representación específica de cada fuente.

### 2.5. Verticales completas

El proyecto se construye por verticales de fuente. Cada vertical recorre el flujo completo: adquisición, validación, transformación, persistencia y comprobación.

### 2.6. Extensibilidad

La arquitectura está planteada para soportar nuevas fuentes y nuevas fases sin rediseñar el núcleo del sistema.

---

## 3. Vista general de la arquitectura

A alto nivel, el pipeline sigue esta secuencia:

**fuentes externas → conectores → raw → staging / transformación → deduplicación / matching → persistencia canónica → comprobación**

Cada fuente entra por su propio conector, genera una ejecución trazable y pasa por una transformación específica de fuente. Después, los datos se adaptan a un modelo común o se cargan como referencia geográfica según el caso.

Esto permite distinguir dos grandes tipos de flujo:

### 3.1. Flujos de referencia

Son fuentes estructurales que sirven de base al sistema, como la geografía oficial de Sevilla.

Ejemplo:

* Sevilla Geo → `district` + `neighborhood`

### 3.2. Flujos de negocio

Son fuentes que producen candidatos de locales gastronómicos que más tarde pueden consolidarse en `place`.

Ejemplo:

* OSM Overpass → `place`, `place_source_ref`, `place_category`, `place_neighborhood_assignment`

---

## 4. Capas principales

## 4.1. Capa raw

Es la primera capa persistente del pipeline.

Aquí se almacena la descarga original de cada fuente sin transformaciones destructivas. El objetivo es conservar una copia fiel del input real del sistema.

Responsabilidades:

* descargar o leer la fuente
* persistir el asset raw en disco
* registrar metadata en `raw_asset`
* vincularlo con `source_run`

Beneficios:

* reproducibilidad
* auditoría
* depuración
* trazabilidad completa

---

## 4.2. Capa staging

Es la capa intermedia de trabajo.

Aquí se realizan:

* validaciones estructurales
* limpieza básica
* normalización intermedia
* derivación de candidatos
* artefactos auxiliares de perfilado y control

No representa todavía el modelo de negocio final, pero sí deja los datos listos para ser tratados de forma consistente.

Ejemplos:

* candidatos normalizados de locales desde Overpass
* resultados de deduplicación intra-fuente
* artefactos JSON de transformación y QA

---

## 4.3. Capa reference

Esta capa almacena datos de referencia relativamente estables que sirven de apoyo a otras fases del pipeline.

Ejemplo principal:

* barrios y distritos de Sevilla

Estos datos no se usan como representación de negocio, sino como soporte estructural para enriquecimiento geográfico y segmentación territorial.

---

## 4.4. Capa canónica / de negocio

Es la capa donde vive la representación consolidada del dominio.

Sus entidades principales son:

* `place`
* `place_source_ref`
* `place_category`
* `place_neighborhood_assignment`

Aquí ya no se trabaja con la forma exacta en la que cada fuente entrega sus datos, sino con una estructura interna coherente.

---

## 4.5. Capa artifacts / ops

Incluye todos los artefactos operativos que ayudan a ejecutar, revisar y validar el sistema.

Ejemplos:

* logs
* perfiles de datos
* resúmenes de transformación
* resultados de deduplicación
* resultados de importación
* scripts de comprobación

---

## 5. Componentes principales del sistema

## 5.1. Configuración

Se centraliza en `src/config/`.

Aquí se definen:

* settings del entorno
* rutas de datos
* endpoints de fuentes
* claves de acceso futuras
* parámetros compartidos del sistema

Esto permite mantener el proyecto parametrizable sin hardcodear lógica en los scripts.

---

## 5.2. Conectores

Se encuentran en `src/connectors/`.

Son responsables de la interacción directa con la fuente:

* construir consultas
* descargar respuestas
* registrar `source_run`
* persistir raw

Ejemplos:

* `SevillaGeoConnector`
* `OverpassConnector`

---

## 5.3. Transformadores y normalización

Se ubican en módulos como `src/geo/` y `src/normalization/`.

Aquí se adapta la lógica específica de cada fuente a estructuras comunes del proyecto.

Ejemplos:

* transformación del GeoJSON de barrios
* transformación de elementos de Overpass a `NormalizedPlaceCandidate`

---

## 5.4. Deduplicación y matching

Esta parte se encarga de reducir ruido, agrupar duplicados probables y preparar la consolidación multi-fuente.

Actualmente ya existe deduplicación intra-fuente en Overpass.
Más adelante esta parte crecerá para soportar matching entre OSM, Google Places y Yelp.

---

## 5.5. Importadores

Los importadores convierten resultados transformados en escritura controlada sobre el modelo canónico o de referencia.

Ejemplos:

* importador geográfico de Sevilla Geo
* importador de candidatos Overpass a `place` y entidades relacionadas

---

## 5.6. Base de datos

La persistencia principal del proyecto se apoya en **PostgreSQL + PostGIS**.

Se eligió porque permite:

* modelo relacional robusto
* soporte geoespacial nativo
* buenas capacidades de integridad
* soporte adecuado para índices y consultas espaciales

---

## 6. Relación entre arquitectura lógica y estructura física

La arquitectura lógica se refleja directamente en la estructura del repositorio.

### Código

* `src/config/` → configuración
* `src/connectors/` → adquisición
* `src/geo/` → lógica geográfica
* `src/normalization/` → normalización, candidatos, deduplicación, importación
* `src/db/` → conexión y utilidades de base de datos
* `src/utils/` → logging y soporte transversal

### Datos

* `data/raw/` → assets originales
* `data/staging/` → salidas intermedias
* `data/reference/` → datasets de referencia
* `data/artifacts/` → logs y resultados operativos

### Persistencia SQL

* `db/ddl/` → scripts de creación del schema
* `db/queries/` → consultas auxiliares
* `db/seeds/` → seeds y cargas base

---

## 7. Decisiones arquitectónicas importantes

## 7.1. `place` como entidad canónica

No se usa una fuente externa como representación final del local. `place` es la entidad interna estable del sistema.

## 7.2. `place_source_ref` como capa de representación fuente

Cada local puede tener múltiples referencias por fuente. Esto evita mezclar directamente datos de OSM, Google o Yelp y permite trazabilidad completa.

## 7.3. `review` ligada a fuente

Las reseñas no se fusionan entre sí. Se consideran dependientes de la fuente que las aporta.

## 7.4. Geografía separada del local

La asignación de barrio no se embebe de forma rígida en el modelo del local, sino que se maneja mediante `place_neighborhood_assignment`, lo que permite flexibilidad, trazabilidad y revisión.

## 7.5. Calidad como entidad explícita

Las incidencias no se tratan solo en logs: se modelan en `validation_issue` para poder auditarlas y explotarlas.

---

## 8. Estado actual de la arquitectura

Actualmente la arquitectura ya está operativa en dos verticales completas:

### Sevilla Geo

* conector
* ingesta raw
* transformación geográfica
* importación de referencia
* comprobación de resultados

### OSM Overpass

* conector
* ingesta raw
* perfilado
* transformación a candidato común
* deduplicación intra-fuente
* importación canónica
* comprobación

Esto valida que la arquitectura no es solo teórica, sino que ya se ha probado en flujos reales de extremo a extremo.

---

## 9. Evolución prevista

La arquitectura está preparada para incorporar próximamente:

* Google Places
* Yelp Open Dataset
* matching multi-fuente más avanzado
* consolidación canónica más rica
* enriquecimiento adicional para NLP y ranking gastronómico

El diseño actual ya deja ese camino preparado sin necesidad de rehacer la base del sistema.

---

## 10. Conclusión

La arquitectura de Hidden Gems Pipeline se ha diseñado para equilibrar cuatro necesidades principales:

* trazabilidad
* control de calidad
* flexibilidad ante múltiples fuentes
* construcción progresiva de un modelo canónico útil

No se trata de una arquitectura improvisada para hacer scrapers sueltos, sino de una base de datos y un pipeline concebidos como núcleo real del proyecto Hidden Gems.
