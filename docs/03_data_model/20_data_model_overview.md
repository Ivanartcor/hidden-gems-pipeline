# 20. Visión general del modelo de datos

## 1. Introducción

El modelo de datos de Hidden Gems ha sido diseñado para soportar un pipeline de adquisición, integración, validación y preparación de datos gastronómicos procedentes de múltiples fuentes.

Su objetivo principal no es almacenar datos de forma aislada, sino construir una base estructurada, trazable y preparada para fases posteriores de normalización, análisis textual, enriquecimiento geográfico y generación de señales analíticas.

Este modelo responde a una decisión central del proyecto: separar claramente el dato fuente, el dato canónico, el dato geográfico, el dato derivado y los elementos de gobierno técnico del pipeline.

De esta forma, el sistema puede responder a preguntas como:

- de qué fuente procede un dato
- en qué ejecución fue adquirido
- qué archivo raw lo contenía
- qué local real representa
- cómo aparece ese local en cada fuente
- a qué barrio pertenece
- qué incidencias de calidad se detectaron
- qué información queda preparada para fases posteriores

---

## 2. Principios de diseño del modelo

El modelo se ha construido siguiendo una serie de principios que guían todas las decisiones estructurales.

### 2.1. Separar realidad, fuente y proceso

Uno de los principios más importantes es no mezclar conceptos distintos dentro de una misma tabla.

No es lo mismo:

- un local real consolidado por el sistema
- la representación de ese local en Google Places, OSM o Yelp
- una reseña textual asociada a una fuente
- una ejecución del pipeline
- un archivo raw descargado
- una incidencia detectada durante la validación

Por ello, el modelo separa entidades de negocio, entidades fuente y entidades operativas.

### 2.2. Mantener una entidad canónica interna

El sistema no usa como identificador principal ningún ID externo de Google, OSM, Yelp u otra fuente.

La entidad `place` representa el local canónico interno del sistema. Esta entidad actúa como punto de integración de distintas referencias externas.

Esto permite que un mismo local pueda estar representado por:

- un `place_id` interno
- un `google_place_id` dentro de `place_source_ref`
- un identificador OSM dentro de `place_source_ref`
- un identificador Yelp dentro de `place_source_ref`

La identidad real del sistema pertenece a `place`, no a las fuentes externas.

### 2.3. Conservar trazabilidad completa

El modelo debe permitir reconstruir el origen de los datos.

Para ello se incorporan entidades específicas de gobierno y trazabilidad:

- `source_system`
- `source_run`
- `raw_asset`
- `validation_issue`

Estas entidades permiten saber qué fuente fue utilizada, cuándo se ejecutó el pipeline, qué artefactos raw se generaron y qué problemas se detectaron.

### 2.4. Separar dato original y dato interpretado

El dato raw no se sobrescribe ni se transforma directamente.

Las decisiones del sistema, como asignar un barrio, clasificar un local o consolidar referencias de varias fuentes, se representan en entidades separadas.

Ejemplos:

- la categoría interna de un local se almacena mediante `place_category`
- la asignación barrio-local se almacena mediante `place_neighborhood_assignment`
- la representación fuente de un local se almacena mediante `place_source_ref`
- los errores de calidad se almacenan mediante `validation_issue`

### 2.5. Preparar el modelo para evolución futura

El modelo actual se centra en la adquisición y estructuración del dato. Sin embargo, está preparado para crecer hacia fases posteriores del proyecto.

En fases futuras podrán añadirse entidades o capas derivadas como:

- menciones de platos
- análisis de sentimiento
- embeddings de reseñas
- puntuaciones de calidad textual
- rankings por barrio
- métricas agregadas por zona

Estas capas no forman parte del núcleo inicial, pero el modelo actual deja preparada la base para incorporarlas sin romper la arquitectura.

---

## 3. Bloques principales del modelo

El modelo se organiza en cinco grandes bloques funcionales.

## 3.1. Núcleo de negocio

Este bloque representa las entidades principales del dominio gastronómico.

Entidades incluidas:

- `place`
- `place_source_ref`
- `review`

### Función del bloque

El núcleo de negocio permite representar locales, sus apariciones en distintas fuentes y las reseñas asociadas.

La decisión más importante de este bloque es la separación entre:

- `place`: local canónico interno
- `place_source_ref`: representación de ese local en una fuente concreta
- `review`: reseña textual dependiente de una fuente

Esta separación es esencial para trabajar con datos multisource sin perder consistencia.

---

## 3.2. Geografía

Este bloque representa la estructura territorial oficial utilizada por Hidden Gems.

Entidades incluidas:

- `district`
- `neighborhood`
- `place_neighborhood_assignment`

### Función del bloque

El análisis de Hidden Gems se apoya en el concepto de barrio. Por ello, el modelo incorpora entidades geográficas oficiales y una entidad derivada para asignar locales a barrios.

La decisión clave es que el barrio no se guarda directamente dentro de `place`. En su lugar, la relación se representa mediante `place_neighborhood_assignment`.

Esto permite:

- recalcular asignaciones
- almacenar confianza
- marcar revisiones manuales
- conservar histórico
- separar geografía oficial de resultados derivados

---

## 3.3. Clasificación

Este bloque gestiona la taxonomía interna de categorías y su relación con los locales.

Entidades incluidas:

- `category`
- `place_category`

### Función del bloque

Las fuentes externas usan sistemas de categorías diferentes. Google Places, OSM y Yelp no clasifican los locales de la misma manera.

Por ello, el modelo define una taxonomía interna mediante `category`, y una relación entre locales y categorías mediante `place_category`.

Esto permite:

- unificar categorías entre fuentes
- asignar varias categorías a un mismo local
- marcar una categoría principal
- registrar el método y la confianza de asignación

---

## 3.4. Gobierno y trazabilidad

Este bloque permite auditar el origen y el recorrido técnico de los datos.

Entidades incluidas:

- `source_system`
- `source_run`
- `raw_asset`

### Función del bloque

Estas entidades permiten responder a preguntas operativas fundamentales:

- qué fuente se usó
- cuándo se ejecutó la ingesta
- qué tipo de ejecución fue
- qué archivos raw se generaron
- cuántos registros fueron extraídos o rechazados
- qué artefactos están disponibles

Este bloque convierte el pipeline en un sistema reproducible y auditable.

---

## 3.5. Calidad

Este bloque registra incidencias detectadas durante el pipeline.

Entidad incluida:

- `validation_issue`

### Función del bloque

El sistema no solo almacena datos, sino también los problemas detectados durante su adquisición, validación, integración o enriquecimiento.

`validation_issue` permite registrar incidencias como:

- coordenadas ausentes
- geometría inválida
- duplicados potenciales
- categorías no mapeadas
- reseñas sin texto útil
- errores de esquema
- problemas de matching

Esta entidad es clave para controlar la calidad del pipeline.

---

## 4. Resumen de entidades

| Bloque | Entidades | Propósito |
|---|---|---|
| Núcleo de negocio | `place`, `place_source_ref`, `review` | Representar locales, referencias fuente y reseñas |
| Geografía | `district`, `neighborhood`, `place_neighborhood_assignment` | Modelar territorio oficial y asignación espacial |
| Clasificación | `category`, `place_category` | Unificar categorías y clasificar locales |
| Gobierno y trazabilidad | `source_system`, `source_run`, `raw_asset` | Auditar fuentes, ejecuciones y artefactos raw |
| Calidad | `validation_issue` | Registrar problemas de validación y calidad |

---

## 5. Relaciones principales

Las relaciones fundamentales del modelo son:

```text
source_system 1 ─── N source_run
source_run    1 ─── N raw_asset

place         1 ─── N place_source_ref
place         1 ─── N review
place         1 ─── N place_category
place         1 ─── N place_neighborhood_assignment

category      1 ─── N place_category

district      1 ─── N neighborhood
neighborhood  1 ─── N place_neighborhood_assignment

source_run    1 ─── N validation_issue
raw_asset     1 ─── N validation_issue
````

Estas relaciones reflejan la separación entre fuente, ejecución, entidad canónica, geografía, clasificación y calidad.

---

## 6. Entidad central del modelo

La entidad central del modelo es `place`.

A partir de ella se conectan:

* las referencias externas mediante `place_source_ref`
* las reseñas mediante `review`
* las categorías mediante `place_category`
* la asignación territorial mediante `place_neighborhood_assignment`

Esto convierte a `place` en el punto de integración del dominio gastronómico.

---

## 7. Decisiones clave del modelo

### 7.1. No usar IDs externos como clave principal

Los identificadores externos se almacenan en `place_source_ref`, nunca como clave principal de `place`.

### 7.2. No guardar el barrio directamente en `place`

La asignación a barrio se modela como una relación derivada mediante `place_neighborhood_assignment`.

### 7.3. No guardar categorías como texto libre en `place`

Las categorías se normalizan en `category` y se relacionan mediante `place_category`.

### 7.4. No fusionar reseñas entre fuentes

Las reseñas son dependientes de su fuente. Cada `review` conserva su origen y su texto raw.

### 7.5. No mezclar validaciones con logs sueltos

Las incidencias relevantes se estructuran en `validation_issue`, no quedan únicamente en logs de texto.

---

## 8. Relación con el pipeline

El modelo está diseñado para acompañar el flujo del pipeline:

1. Se registra la fuente en `source_system`.
2. Se crea una ejecución en `source_run`.
3. Se almacenan artefactos raw en `raw_asset`.
4. Se integran locales en `place` y `place_source_ref`.
5. Se cargan reseñas en `review`.
6. Se clasifican locales con `category` y `place_category`.
7. Se asignan locales a barrios con `place_neighborhood_assignment`.
8. Se registran incidencias en `validation_issue`.

Este flujo permite que el modelo no sea solo una base de datos estática, sino una representación estructurada de la operación real del pipeline.

---

## 9. Estado actual del modelo

El modelo ya ha sido materializado en PostgreSQL + PostGIS mediante scripts SQL separados por bloques:

* `00_foundation.sql`
* `01_governance.sql`
* `02_geo_reference.sql`
* `03_core_places.sql`
* `04_classification_and_geo_assignment.sql`
* `05_validation.sql`

Estos scripts crean el esquema principal, las extensiones necesarias, los tipos enumerados, las tablas, relaciones, restricciones, índices y triggers definidos para esta fase.

---

## 10. Conclusión

El modelo de datos de Hidden Gems está diseñado para ser robusto, modular y preparado para evolución futura.

Su principal fortaleza es la separación clara entre:

* dato canónico
* dato fuente
* dato geográfico
* dato derivado
* trazabilidad técnica
* control de calidad

Esta estructura permite que el sistema pueda crecer hacia fases posteriores de normalización, NLP, ranking y explotación analítica sin perder consistencia ni trazabilidad.

