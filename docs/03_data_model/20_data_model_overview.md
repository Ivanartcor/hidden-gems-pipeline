# 20. Visión general del modelo de datos

## 1. Introducción

El modelo de datos de Hidden Gems ha sido diseñado para soportar un pipeline de adquisición, integración, validación, normalización, enriquecimiento geográfico e inteligencia aplicada sobre datos gastronómicos procedentes de múltiples fuentes.

Su objetivo principal no es almacenar datos de forma aislada, sino construir una base estructurada, trazable y preparada para:

- consolidar locales gastronómicos de distintas fuentes;
- conservar el origen y la trazabilidad de cada dato;
- trabajar con geografía oficial de barrios y distritos;
- importar y explotar reseñas reales cuando estén disponibles;
- generar corpus y señales para procesamiento de lenguaje natural;
- detectar platos mencionados en reseñas;
- normalizar variantes de platos;
- calcular sentimiento por mención;
- agregar señales por local y plato;
- generar candidatos Hidden Gems consultables desde PostgreSQL.

El modelo responde a una decisión central del proyecto: separar claramente el dato fuente, el dato canónico, el dato geográfico, el dato derivado, las capas de inteligencia y los elementos de gobierno técnico del pipeline.

De esta forma, el sistema puede responder a preguntas como:

- de qué fuente procede un dato;
- en qué ejecución fue adquirido;
- qué archivo raw lo contenía;
- qué local real representa;
- cómo aparece ese local en cada fuente;
- a qué barrio pertenece;
- qué reseñas alimentan el análisis;
- qué platos se mencionan;
- qué sentimiento tiene cada mención;
- qué señales agregadas tiene un plato en un local;
- qué candidatos Hidden Gems se han generado;
- con qué versión de modelo, regla o ranking se produjo cada resultado;
- qué incidencias de calidad se detectaron.

---

## 2. Principios de diseño del modelo

El modelo se ha construido siguiendo una serie de principios que guían todas las decisiones estructurales.

### 2.1. Separar realidad, fuente y proceso

Uno de los principios más importantes es no mezclar conceptos distintos dentro de una misma tabla.

No es lo mismo:

- un local real consolidado por el sistema;
- la representación de ese local en Google Places, OSM o Yelp;
- una reseña textual asociada a una fuente;
- una ejecución del pipeline;
- un archivo raw descargado;
- una mención de plato detectada por IA;
- una señal agregada local-plato;
- un candidato final de ranking.

Por ello, el modelo separa entidades de negocio, entidades fuente, entidades operativas y entidades derivadas de IA.

### 2.2. Mantener una entidad canónica interna

El sistema no usa como identificador principal ningún ID externo de Google, OSM, Yelp u otra fuente.

La entidad `place` representa el local canónico interno del sistema. Esta entidad actúa como punto de integración de distintas referencias externas.

Esto permite que un mismo local pueda estar representado por:

- un `place_id` interno;
- un `google_place_id` dentro de `place_source_ref`;
- un identificador OSM dentro de `place_source_ref`;
- un identificador Yelp dentro de `place_source_ref`.

La identidad real del sistema pertenece a `place`, no a las fuentes externas.

### 2.3. Conservar trazabilidad completa

El modelo debe permitir reconstruir el origen de los datos y de los resultados derivados.

Para ello se incorporan entidades específicas de gobierno y trazabilidad:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `validation_issue`;
- `ai_model_version`;
- `ai_pipeline_run`.

Las primeras trazan la adquisición y los artefactos fuente. Las dos últimas trazan la ejecución y versionado de modelos, reglas, procesos híbridos, agregaciones y rankings.

### 2.4. Separar dato original y dato interpretado

El dato raw no se sobrescribe ni se transforma directamente.

Las decisiones del sistema, como asignar un barrio, clasificar un local, consolidar referencias de varias fuentes o generar un candidato Hidden Gem, se representan en entidades separadas.

Ejemplos:

- la categoría interna de un local se almacena mediante `place_category`;
- la asignación barrio-local se almacena mediante `place_neighborhood_assignment`;
- la representación fuente de un local se almacena mediante `place_source_ref`;
- las menciones de platos se almacenan mediante `dish_mention`;
- el sentimiento por mención se almacena mediante `dish_mention_sentiment`;
- las señales agregadas se almacenan mediante `dish_place_signal`;
- los candidatos finales se almacenan mediante `hidden_gem_candidate`.

### 2.5. Tratar la IA como capa derivada, no como sustitución del core

La capa IA no modifica directamente `place` ni `review` para introducir campos como `best_dish`, `hidden_gem_score` o `dish_sentiment`.

En su lugar, el modelo mantiene una separación explícita:

```text
core operacional:
place + place_source_ref + review + neighborhood

capa IA derivada:
dish + dish_alias + dish_mention + dish_mention_sentiment + dish_place_signal + hidden_gem_candidate
```

Esto permite recalcular modelos, cambiar reglas, generar nuevos rankings o comparar versiones sin contaminar las entidades canónicas.

### 2.6. Versionar todo resultado IA

Cada resultado IA debe saber con qué método, modelo o configuración se generó.

Por eso se incorporan:

- `ai_model_version`: registra versiones de modelos, reglas, métodos híbridos, agregadores y rankings.
- `ai_pipeline_run`: registra ejecuciones concretas de procesos IA.

Ejemplos de versiones registrables:

- `dish_ner_transformer_v1`;
- `dish_normalization_rule_based_v2`;
- `mention_sentiment_hybrid_v1_1`;
- `signal_aggregation_v1`;
- `hidden_gems_ranking_v1`.

---

## 3. Bloques principales del modelo

El modelo se organiza en seis grandes bloques funcionales.

## 3.1. Núcleo de negocio

Este bloque representa las entidades principales del dominio gastronómico.

Entidades incluidas:

- `place`;
- `place_source_ref`;
- `review`.

### Función del bloque

El núcleo de negocio permite representar locales, sus apariciones en distintas fuentes y las reseñas asociadas.

La decisión más importante de este bloque es la separación entre:

- `place`: local canónico interno;
- `place_source_ref`: representación de ese local en una fuente concreta;
- `review`: reseña textual dependiente de una fuente.

Esta separación es esencial para trabajar con datos multisource sin perder consistencia.

---

## 3.2. Geografía

Este bloque representa la estructura territorial oficial utilizada por Hidden Gems.

Entidades incluidas:

- `district`;
- `neighborhood`;
- `place_neighborhood_assignment`.

### Función del bloque

El análisis de Hidden Gems se apoya en el concepto de barrio. Por ello, el modelo incorpora entidades geográficas oficiales y una entidad derivada para asignar locales a barrios.

La decisión clave es que el barrio no se guarda directamente dentro de `place`. En su lugar, la relación se representa mediante `place_neighborhood_assignment`.

Esto permite:

- recalcular asignaciones;
- almacenar confianza;
- marcar revisiones manuales;
- conservar histórico;
- separar geografía oficial de resultados derivados.

---

## 3.3. Clasificación

Este bloque gestiona la taxonomía interna de categorías y su relación con los locales.

Entidades incluidas:

- `category`;
- `place_category`.

### Función del bloque

Las fuentes externas usan sistemas de categorías diferentes. Google Places, OSM y Yelp no clasifican los locales de la misma manera.

Por ello, el modelo define una taxonomía interna mediante `category`, y una relación entre locales y categorías mediante `place_category`.

Esto permite:

- unificar categorías entre fuentes;
- asignar varias categorías a un mismo local;
- marcar una categoría principal;
- registrar el método y la confianza de asignación.

---

## 3.4. Gobierno y trazabilidad

Este bloque permite auditar el origen y el recorrido técnico de los datos.

Entidades incluidas:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `ai_model_version`;
- `ai_pipeline_run`.

### Función del bloque

Estas entidades permiten responder a preguntas operativas fundamentales:

- qué fuente se usó;
- cuándo se ejecutó la ingesta;
- qué tipo de ejecución fue;
- qué archivos raw se generaron;
- cuántos registros fueron extraídos o rechazados;
- qué modelos, reglas o métodos IA se usaron;
- qué configuración y métricas tuvo cada ejecución IA;
- qué artefactos están disponibles.

Este bloque convierte el pipeline en un sistema reproducible y auditable.

---

## 3.5. Calidad

Este bloque registra incidencias detectadas durante el pipeline.

Entidad incluida:

- `validation_issue`.

### Función del bloque

El sistema no solo almacena datos, sino también los problemas detectados durante su adquisición, validación, integración, enriquecimiento o explotación IA.

`validation_issue` permite registrar incidencias como:

- coordenadas ausentes;
- geometría inválida;
- duplicados potenciales;
- categorías no mapeadas;
- reseñas sin texto útil;
- errores de esquema;
- problemas de matching;
- menciones de platos sin review asociada;
- platos sin alias canónico;
- candidatos de ranking sin señal agregada;
- problemas de carga de artefactos IA.

Esta entidad es clave para controlar la calidad del pipeline.

---

## 3.6. Capa IA y ranking

Este bloque representa las entidades derivadas generadas por el módulo IA.

Entidades incluidas:

- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

### Función del bloque

La capa IA permite convertir reseñas textuales en señales gastronómicas explotables.

El flujo conceptual es:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

En paralelo, el catálogo de platos se estructura como:

```text
dish
→ dish_alias
→ dish_mention
```

Esta capa permite responder a preguntas como:

- qué platos se mencionan en las reseñas de un local;
- qué variantes textuales apuntan al mismo plato;
- qué sentimiento tiene cada mención;
- qué platos tienen mejor señal en cada local;
- qué candidatos Hidden Gems se han generado;
- qué ranking es prototipo y cuál podría ser producción Sevilla.

---

## 4. Resumen de entidades

| Bloque | Entidades | Propósito |
|---|---|---|
| Núcleo de negocio | `place`, `place_source_ref`, `review` | Representar locales, referencias fuente y reseñas |
| Geografía | `district`, `neighborhood`, `place_neighborhood_assignment` | Modelar territorio oficial y asignación espacial |
| Clasificación | `category`, `place_category` | Unificar categorías y clasificar locales |
| Gobierno y trazabilidad | `source_system`, `source_run`, `raw_asset`, `ai_model_version`, `ai_pipeline_run` | Auditar fuentes, ejecuciones, artefactos y procesos IA |
| Calidad | `validation_issue` | Registrar problemas de validación y calidad |
| IA y ranking | `dish`, `dish_alias`, `dish_mention`, `dish_mention_sentiment`, `dish_place_signal`, `hidden_gem_candidate` | Detectar platos, calcular sentimiento, agregar señales y generar ranking |

---

## 5. Relaciones principales

Las relaciones fundamentales del modelo base son:

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
```

Las relaciones de la capa IA son:

```text
ai_model_version 1 ─── N dish
ai_model_version 1 ─── N dish_alias
ai_model_version 1 ─── N dish_mention
ai_model_version 1 ─── N dish_mention_sentiment

ai_pipeline_run 1 ─── N dish
ai_pipeline_run 1 ─── N dish_alias
ai_pipeline_run 1 ─── N dish_mention
ai_pipeline_run 1 ─── N dish_mention_sentiment
ai_pipeline_run 1 ─── N dish_place_signal
ai_pipeline_run 1 ─── N hidden_gem_candidate

review 1 ─── N dish_mention
place  1 ─── N dish_mention
dish   1 ─── N dish_mention
dish   1 ─── N dish_alias

dish_mention 1 ─── N dish_mention_sentiment

place 1 ─── N dish_place_signal
dish  1 ─── N dish_place_signal

dish_place_signal 1 ─── N hidden_gem_candidate
place             1 ─── N hidden_gem_candidate
dish              1 ─── N hidden_gem_candidate
neighborhood      1 ─── N hidden_gem_candidate
district          1 ─── N hidden_gem_candidate
```

Estas relaciones reflejan la separación entre fuente, ejecución, entidad canónica, geografía, clasificación, calidad, extracción textual, sentimiento, agregación y ranking.

---

## 6. Entidad central del modelo

La entidad central del modelo sigue siendo `place`.

A partir de ella se conectan:

- las referencias externas mediante `place_source_ref`;
- las reseñas mediante `review`;
- las categorías mediante `place_category`;
- la asignación territorial mediante `place_neighborhood_assignment`;
- las menciones de platos mediante `dish_mention`;
- las señales agregadas mediante `dish_place_signal`;
- los candidatos Hidden Gems mediante `hidden_gem_candidate`.

Esto convierte a `place` en el punto de integración del dominio gastronómico y de la capa IA.

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

### 7.6. No insertar resultados IA huérfanos

Las menciones, sentimientos, señales y rankings deben enlazar con entidades canónicas existentes.

Por ejemplo:

- `dish_mention` debe enlazar con `review`, `place` y, cuando sea posible, `dish`;
- `dish_place_signal` debe enlazar con `place` y `dish`;
- `hidden_gem_candidate` debe enlazar con `place`, `dish` y la señal que lo justifica.

### 7.7. Tratar Yelp como prototipo IA, no como producción Sevilla

Yelp Open Dataset se ha importado como corpus/prototipo IA para validar la cadena completa de detección de platos, normalización, sentimiento, agregación y ranking.

Los candidatos generados desde Yelp se almacenan con:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

La versión productiva de Sevilla deberá usar `ranking_scope = sevilla_neighborhood`, `neighborhood_id` no nulo y datos operativos reales.

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
9. Se registran versiones IA en `ai_model_version`.
10. Se registran ejecuciones IA en `ai_pipeline_run`.
11. Se carga o genera el catálogo de platos en `dish` y `dish_alias`.
12. Se detectan menciones de platos en `dish_mention`.
13. Se calcula sentimiento por mención en `dish_mention_sentiment`.
14. Se agregan señales por local y plato en `dish_place_signal`.
15. Se generan candidatos de ranking en `hidden_gem_candidate`.
16. Se exponen vistas de consulta para demo, auditoría y análisis.

Este flujo permite que el modelo no sea solo una base de datos estática, sino una representación estructurada de la operación real del pipeline y de sus capas inteligentes.

---

## 9. Estado actual del modelo

El modelo ya ha sido materializado en PostgreSQL + PostGIS mediante scripts SQL separados por bloques:

- `00_foundation.sql`;
- `01_governance.sql`;
- `02_geo_reference.sql`;
- `03_core_places.sql`;
- `04_classification_and_geo_assignment.sql`;
- `05_validation.sql`;
- `06_review_enrichment.sql`;
- `07_ai_module.sql`;
- `08_ai_views.sql`.

Los scripts `07_ai_module.sql` y `08_ai_views.sql` incorporan la capa IA persistida y una capa de vistas preparada para consulta.

Estado validado tras la integración IA:

| Elemento | Resultado |
|---|---:|
| Platos canónicos (`dish`) | 9.937 |
| Aliases de platos (`dish_alias`) | 10.235 |
| Menciones de platos (`dish_mention`) | 94.932 |
| Sentimientos por mención (`dish_mention_sentiment`) | 94.932 |
| Señales local-plato (`dish_place_signal`) | 31.036 |
| Candidatos Hidden Gems (`hidden_gem_candidate`) | 622 |
| Places totales | 7.230 |
| Reviews totales | 80.037 |

La integración actual está marcada como prototipo Yelp para explotación y validación interna, no como ranking productivo de Sevilla.

---

## 10. Conclusión

El modelo de datos de Hidden Gems está diseñado para ser robusto, modular y preparado para evolución futura.

Su principal fortaleza es la separación clara entre:

- dato canónico;
- dato fuente;
- dato geográfico;
- dato derivado;
- trazabilidad técnica;
- control de calidad;
- resultados IA;
- rankings consultables.

Esta estructura permite que el sistema pueda crecer hacia fases posteriores de adaptación a Sevilla, ranking por barrio, validación humana, API y explotación analítica sin perder consistencia ni trazabilidad.
