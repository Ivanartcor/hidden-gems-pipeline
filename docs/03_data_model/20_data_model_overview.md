# 20. Visión general del modelo de datos

## 1. Introducción

El modelo de datos de **Hidden Gems Pipeline** está diseñado para soportar un flujo completo de adquisición, integración, validación, normalización, enriquecimiento geográfico e inteligencia aplicada sobre datos gastronómicos procedentes de múltiples fuentes.

Su objetivo no es almacenar datos de forma aislada, sino construir una base estructurada, trazable y preparada para:

- consolidar locales gastronómicos de distintas fuentes;
- conservar el origen y la trazabilidad de cada dato;
- trabajar con geografía oficial de barrios y distritos;
- importar y explotar reseñas reales cuando estén disponibles;
- generar corpus y artefactos para procesamiento de lenguaje natural;
- detectar platos mencionados en reseñas;
- normalizar variantes de platos en catálogos canónicos;
- calcular sentimiento por mención de plato;
- agregar señales por local y plato;
- generar candidatos Hidden Gems explicables;
- consultar rankings desde PostgreSQL mediante vistas y scripts demo.

El modelo responde a una decisión central del proyecto: separar claramente **dato fuente**, **dato raw**, **dato canónico**, **dato geográfico**, **dato derivado**, **capa IA**, **trazabilidad** y **calidad**.

Actualmente el modelo ya soporta dos escenarios IA diferenciados:

```text
Yelp Open Dataset
→ corpus/prototipo IA amplio
→ ranking_scope = yelp_prototype
→ is_production_ready = false
```

```text
Google Places Reviews Sevilla
→ piloto local real sobre Sevilla
→ artifact_ranking_scope = sevilla_pilot
→ db_ranking_scope = other
→ is_production_ready = false
```

El segundo escenario representa el avance más reciente del proyecto: un piloto end-to-end sobre reseñas reales de Google Places Sevilla, con detección de platos, normalización, sentimiento, agregación, ranking, carga en PostgreSQL, validación y demo de consulta.

---

## 2. Principios de diseño del modelo

### 2.1. Separar realidad, fuente y proceso

No es lo mismo:

- un local real consolidado por el sistema;
- la representación de ese local en Google Places, OSM o Yelp;
- una reseña textual dependiente de una fuente;
- una ejecución de adquisición;
- un archivo raw descargado;
- una ejecución IA;
- una mención de plato detectada;
- una señal agregada local-plato;
- un candidato Hidden Gem.

Por ello, el modelo separa entidades de negocio, entidades fuente, entidades operativas y entidades derivadas de IA.

### 2.2. Mantener una entidad canónica interna

La entidad `place` representa el local canónico interno del sistema.

El sistema no usa como clave principal ningún ID externo de Google, OSM, Yelp u otra fuente. Los identificadores externos se almacenan en `place_source_ref`.

Esto permite que un mismo local pueda tener:

- un `place_id` interno;
- una referencia Google Places;
- una referencia OSM;
- una referencia Yelp, cuando se usa como prototipo IA;
- futuras referencias de otras fuentes.

### 2.3. Conservar trazabilidad completa

El modelo permite reconstruir el origen de los datos y de los resultados derivados mediante:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `validation_issue`;
- `ai_model_version`;
- `ai_pipeline_run`.

Las primeras entidades trazan adquisición y artefactos fuente. Las dos últimas trazan modelos, reglas, métodos híbridos, agregaciones y rankings.

### 2.4. Separar dato original y dato interpretado

El dato raw no se sobrescribe ni se transforma directamente. Las decisiones del sistema se representan en entidades separadas:

- categoría interna: `place_category`;
- asignación territorial: `place_neighborhood_assignment`;
- representación fuente: `place_source_ref`;
- mención textual de plato: `dish_mention`;
- sentimiento de mención: `dish_mention_sentiment`;
- señal agregada local-plato: `dish_place_signal`;
- candidato final: `hidden_gem_candidate`.

### 2.5. Tratar la IA como capa derivada

La capa IA no modifica directamente `place` ni `review` para introducir campos como `best_dish`, `hidden_gem_score` o `dish_sentiment`.

La separación es:

```text
core operacional:
place + place_source_ref + review + neighborhood

capa IA derivada:
dish + dish_alias + dish_mention + dish_mention_sentiment + dish_place_signal + hidden_gem_candidate
```

Esto permite recalcular modelos, cambiar reglas, comparar versiones y generar nuevos rankings sin contaminar el core.

### 2.6. Versionar todo resultado IA

Cada resultado IA debe saber con qué método o configuración se generó.

Por eso se registran:

- `ai_model_version`: versiones de modelos, reglas, métodos híbridos, agregadores o rankings;
- `ai_pipeline_run`: ejecuciones concretas de procesamiento IA.

En el piloto Sevilla se registran versiones para:

- detección de platos en español;
- normalización de platos local Sevilla;
- sentimiento por mención;
- agregación local-plato;
- ranking Hidden Gems piloto.

---

## 3. Bloques principales del modelo

## 3.1. Núcleo de negocio

Entidades:

- `place`;
- `place_source_ref`;
- `review`.

Este bloque representa locales, apariciones por fuente y reseñas asociadas.

La decisión clave es separar:

```text
place             → entidad canónica interna
place_source_ref  → representación de fuente
review            → reseña source-bound
```

---

## 3.2. Geografía

Entidades:

- `district`;
- `neighborhood`;
- `place_neighborhood_assignment`.

El barrio no se guarda directamente dentro de `place`. Se modela como una asignación derivada, con método y posibilidad de recalcularla.

Esto es fundamental para Hidden Gems, porque el ranking se interpreta por barrio y distrito.

---

## 3.3. Clasificación

Entidades:

- `category`;
- `place_category`.

Las fuentes usan categorías distintas. El modelo crea una taxonomía interna que permite unificar categorías de Google Places, OSM, Yelp u otras fuentes.

---

## 3.4. Gobierno y trazabilidad

Entidades:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `ai_model_version`;
- `ai_pipeline_run`.

Permiten auditar:

- fuente usada;
- ejecución;
- raw generado;
- configuración;
- contadores;
- modelo o regla IA utilizada;
- métricas y artefactos del proceso.

---

## 3.5. Calidad

Entidad:

- `validation_issue`.

Registra incidencias de adquisición, validación, matching, geografía, esquema, carga o IA.

Además, los scripts de checks generan reportes JSON para validar integridad de cargas y consultas.

---

## 3.6. Capa IA y ranking

Entidades:

- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

Flujo conceptual:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

Esta capa permite responder:

- qué platos se mencionan;
- qué variantes apuntan al mismo plato;
- qué sentimiento tiene cada mención;
- qué platos tienen mejor señal en un local;
- qué candidatos Hidden Gems se han generado;
- con qué scope y versión se produjo cada ranking.

---

## 4. Resumen de entidades

| Bloque | Entidades | Propósito |
|---|---|---|
| Núcleo de negocio | `place`, `place_source_ref`, `review` | Locales, referencias fuente y reseñas |
| Geografía | `district`, `neighborhood`, `place_neighborhood_assignment` | Territorio oficial y asignación espacial |
| Clasificación | `category`, `place_category` | Taxonomía interna de locales |
| Gobierno y trazabilidad | `source_system`, `source_run`, `raw_asset`, `ai_model_version`, `ai_pipeline_run` | Auditar fuentes, ejecuciones, artefactos y procesos IA |
| Calidad | `validation_issue` | Registrar problemas de validación y calidad |
| IA y ranking | `dish`, `dish_alias`, `dish_mention`, `dish_mention_sentiment`, `dish_place_signal`, `hidden_gem_candidate` | Extraer platos, sentimiento, señales y ranking |

---

## 5. Relaciones principales

Relaciones base:

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

Relaciones IA:

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

---

## 6. Entidad central del modelo

La entidad central sigue siendo `place`.

A partir de ella se conectan:

- referencias externas mediante `place_source_ref`;
- reseñas mediante `review`;
- categorías mediante `place_category`;
- asignación territorial mediante `place_neighborhood_assignment`;
- menciones de platos mediante `dish_mention`;
- señales agregadas mediante `dish_place_signal`;
- candidatos Hidden Gems mediante `hidden_gem_candidate`.

---

## 7. Decisiones clave del modelo

### 7.1. No usar IDs externos como clave principal

Los IDs externos se almacenan en `place_source_ref`, nunca como clave principal de `place`.

### 7.2. No guardar el barrio directamente en `place`

El barrio se modela mediante `place_neighborhood_assignment` para permitir recalcular asignaciones.

### 7.3. No fusionar reseñas entre fuentes

Las reseñas son dependientes de su fuente. Cada `review` conserva su origen y texto raw.

### 7.4. No insertar resultados IA huérfanos

Las menciones, sentimientos, señales y rankings deben enlazar con entidades existentes:

- `dish_mention` con `review`, `place` y `dish`;
- `dish_mention_sentiment` con `dish_mention`;
- `dish_place_signal` con `place` y `dish`;
- `hidden_gem_candidate` con `dish_place_signal`, `place`, `dish`, `neighborhood` y `district` cuando aplique.

### 7.5. Diferenciar scopes IA

El modelo permite convivir con distintos scopes:

```text
yelp_prototype      → prototipo IA amplio sobre Yelp
sevilla_pilot       → piloto local real sobre Google Reviews Sevilla, conservado en config/artifact scope
sevilla_neighborhood → futuro scope productivo si se actualiza DDL y se valida producción
```

Actualmente, por restricción del DDL, el piloto Sevilla se guarda en base con:

```text
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
is_production_ready = false
```

---

## 8. Relación con el pipeline

El modelo acompaña el flujo completo:

1. Registrar fuente en `source_system`.
2. Crear ejecución en `source_run`.
3. Almacenar raw en `raw_asset`.
4. Integrar locales en `place` y `place_source_ref`.
5. Cargar reseñas en `review`.
6. Clasificar locales con `category` y `place_category`.
7. Asignar locales a barrios con `place_neighborhood_assignment`.
8. Registrar incidencias en `validation_issue`.
9. Registrar versiones IA en `ai_model_version`.
10. Registrar ejecuciones IA en `ai_pipeline_run`.
11. Cargar o generar catálogo de platos en `dish` y `dish_alias`.
12. Detectar menciones en `dish_mention`.
13. Calcular sentimiento en `dish_mention_sentiment`.
14. Agregar señales en `dish_place_signal`.
15. Generar candidatos en `hidden_gem_candidate`.
16. Consultar mediante vistas SQL y scripts demo.

---

## 9. Estado actual del modelo

El modelo está materializado en PostgreSQL/PostGIS mediante:

- `00_foundation.sql`;
- `01_governance.sql`;
- `02_geo_reference.sql`;
- `03_core_places.sql`;
- `04_classification_and_geo_assignment.sql`;
- `05_validation.sql`;
- `06_review_enrichment.sql`;
- `07_ai_module.sql`;
- `08_ai_views.sql`.

### 9.1. Integración IA Yelp validada

| Elemento | Resultado |
|---|---:|
| Platos canónicos (`dish`) | 9.937 |
| Aliases de platos (`dish_alias`) | 10.235 |
| Menciones (`dish_mention`) | 94.932 |
| Sentimientos (`dish_mention_sentiment`) | 94.932 |
| Señales (`dish_place_signal`) | 31.036 |
| Candidatos (`hidden_gem_candidate`) | 622 |

Scope:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

### 9.2. Piloto IA Sevilla validado

El piloto local Sevilla se ha ejecutado sobre reviews reales de Google Places y se ha cargado en PostgreSQL.

Estado validado:

| Elemento | Resultado |
|---|---:|
| Catálogo Sevilla (`dish`) | 190 |
| Aliases Sevilla (`dish_alias`) | 243 |
| Menciones Sevilla (`dish_mention`) | 2.979 |
| Sentimientos Sevilla (`dish_mention_sentiment`) | 2.979 |
| Señales local-plato (`dish_place_signal`) | 2.212 |
| Candidatos ranking (`hidden_gem_candidate`) | 256 |
| Candidatos seleccionados | 150 |

Cobertura del ranking seleccionado:

| Métrica | Valor |
|---|---:|
| Locales seleccionados | 122 |
| Platos seleccionados | 38 |
| Barrios seleccionados | 55 |
| Distritos seleccionados | 11 |
| Candidatos production ready | 0 |

La validación final confirma:

```text
errors = []
warnings = []
ready_for_sevilla_pilot_queries = true
```

---

## 10. Conclusión

El modelo de datos de Hidden Gems es robusto, modular y preparado para evolución.

Su principal fortaleza es la separación clara entre:

- dato canónico;
- dato fuente;
- dato geográfico;
- dato derivado;
- trazabilidad técnica;
- control de calidad;
- resultados IA;
- rankings consultables.

El modelo ya no solo valida el prototipo IA con Yelp. También soporta un piloto local real de Sevilla basado en Google Places Reviews, cargado, validado y consultable.

El siguiente salto natural del modelo será decidir si se amplía el constraint de `ranking_scope` para aceptar `sevilla_pilot` o `sevilla_neighborhood` como valores nativos, y si se promueve una futura versión validada manualmente a `is_production_ready = true`.
