# 10. Visión de la arquitectura

## 1. Finalidad de la arquitectura

La arquitectura de **Hidden Gems** está diseñada para soportar un procesamiento de datos gastronómicos **modular, reproducible, trazable, extensible y preparado para inteligencia artificial**.

Su función no es solo descargar información desde varias fuentes, sino transformarla progresivamente hasta convertirla en una base canónica y una capa derivada de señales inteligentes capaz de alimentar análisis, ranking, consulta técnica y futuras funcionalidades de producto.

Desde el principio se buscó una arquitectura que permitiera trabajar con datos heterogéneos sin perder control del flujo ni trazabilidad sobre lo que ocurre en cada ejecución. Por eso el sistema se apoya en:

- capas de datos bien diferenciadas;
- un modelo relacional orientado a dominio;
- trazabilidad de fuentes, ejecuciones y artefactos;
- separación entre datos operativos y datos derivados;
- módulos independientes para adquisición, normalización, geografía, calidad, IA y consulta;
- notebooks para prototipado IA;
- scripts de carga, validación y demo para estabilizar resultados en PostgreSQL.

El resultado actual no es una colección de scripts sueltos, sino una arquitectura de datos completa sobre la que puede evolucionar el proyecto Hidden Gems.

---

## 2. Principios de diseño

La arquitectura del proyecto se apoya en varios principios clave.

### 2.1. Trazabilidad primero

Cada ejecución del pipeline debe poder reconstruirse. Para ello se registran:

- el sistema fuente;
- la ejecución concreta (`source_run`);
- el asset raw generado (`raw_asset`);
- las incidencias detectadas (`validation_issue`);
- las ejecuciones de IA (`ai_pipeline_run`);
- las versiones de modelos, reglas o métodos IA (`ai_model_version`).

La trazabilidad ya no se limita a la ingesta. También alcanza a la capa derivada de IA y a los rankings generados.

---

### 2.2. Separación por capas

No se mezclan descarga, transformación, consolidación, análisis IA y ranking en una sola fase.

Cada capa tiene una responsabilidad concreta:

```text
raw
→ staging
→ reference
→ canonical / business
→ ai derived layer
→ query / views
→ artifacts / ops
→ demo / dashboard futuro
```

Esta separación permite depurar, reejecutar y evolucionar cada parte sin romper el resto.

---

### 2.3. No perder el raw

La información original descargada desde la fuente se conserva siempre antes de aplicar limpieza o normalización.

El raw actúa como evidencia auditable y permite reconstruir transformaciones posteriores.

---

### 2.4. Modelo canónico interno

Las fuentes externas no se consideran el modelo final.

La entidad central del sistema es `place`, mientras que `place_source_ref` conserva la representación específica de cada fuente.

Esto permite integrar datos de:

- OSM / Overpass;
- Google Places;
- Google Places Reviews;
- Yelp Open Dataset como prototipo IA;
- futuras fuentes.

---

### 2.5. Capa IA derivada, no invasiva

Los resultados IA no se incrustan directamente en `place` ni sustituyen al core del modelo.

La arquitectura añade una capa derivada formada por:

- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

Esto mantiene clara la diferencia entre:

```text
dato canónico → qué locales y reseñas existen
dato IA       → qué platos se detectan, cómo se valoran y cómo se rankean
```

---

### 2.6. Versionado de modelos y métodos IA

Todo resultado IA debe saber con qué modelo, regla o método fue generado.

Por eso la arquitectura incluye:

- `ai_model_version`, para registrar modelos, reglas o métodos IA;
- `ai_pipeline_run`, para registrar ejecuciones concretas de importación, inferencia, agregación o ranking.

Este principio se aplica tanto al prototipo Yelp como al piloto Sevilla.

---

### 2.7. Verticales completas

El proyecto se construye por verticales de fuente o módulo.

Cada vertical debe recorrer un flujo completo:

```text
adquisición / preparación
→ raw o input controlado
→ transformación
→ persistencia
→ check
→ documentación
```

Esto se ha seguido tanto en las fuentes de datos como en la integración IA.

---

### 2.8. Extensibilidad

La arquitectura está planteada para soportar nuevas fuentes, nuevos modelos, nuevas reglas de ranking, una futura capa de API y un dashboard sin rediseñar el núcleo del sistema.

---

## 3. Vista general de la arquitectura

A alto nivel, el sistema sigue esta secuencia:

```text
fuentes externas
→ conectores / loaders
→ raw / staging
→ validación y limpieza
→ normalización
→ enriquecimiento geográfico
→ deduplicación / matching
→ persistencia canónica
→ capa IA derivada
→ vistas de consulta
→ scripts demo
→ dashboard / API futura
```

Esta arquitectura permite distinguir tres grandes familias de flujo.

---

## 3.1. Flujos de referencia

Son fuentes estructurales que sirven de base al sistema.

Ejemplo:

```text
Sevilla Geo
→ district
→ neighborhood
```

Estos datos permiten trabajar después por barrio y distrito.

---

## 3.2. Flujos de negocio

Son fuentes que producen locales, referencias externas, categorías, reseñas o enriquecimiento operativo.

Ejemplos:

```text
OSM / Overpass
→ place
→ place_source_ref
→ place_category
→ place_neighborhood_assignment
```

```text
Google Places Text Search
→ place
→ place_source_ref
→ place_category
→ place_neighborhood_assignment
```

```text
Google Places Reviews
→ review
```

---

## 3.3. Flujos IA derivados

Son procesos que parten de reseñas y generan información analítica de platos.

Flujo general:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
→ views de consulta
```

Actualmente existen dos aplicaciones de este flujo:

1. **Yelp prototype**, usado para validar arquitectura e integración IA con corpus externo.
2. **Sevilla pilot**, usado para validar el flujo local con reviews reales de Google Places Sevilla.

---

## 4. Capas principales

## 4.1. Capa raw

Es la primera capa persistente del pipeline.

Aquí se almacena la descarga original de cada fuente sin transformaciones destructivas.

Responsabilidades:

- descargar o leer la fuente;
- persistir el asset raw en disco;
- registrar metadata en `raw_asset`;
- vincularlo con `source_run`.

---

## 4.2. Capa staging

Es la capa intermedia de trabajo.

Aquí se realizan:

- validaciones estructurales;
- limpieza básica;
- normalización intermedia;
- derivación de candidatos;
- deduplicación;
- artefactos auxiliares de perfilado y control.

Ejemplos:

- candidatos normalizados de locales desde Overpass;
- staging de Google Places;
- staging de Google Places Reviews;
- subsets de Yelp Open Dataset.

---

## 4.3. Capa reference

Esta capa almacena datos de referencia relativamente estables.

Ejemplo principal:

- barrios y distritos de Sevilla.

Estos datos sirven como soporte estructural para enriquecimiento geográfico y segmentación territorial.

---

## 4.4. Capa canónica / de negocio

Es la capa donde vive la representación consolidada del dominio.

Entidades principales:

- `place`;
- `place_source_ref`;
- `review`;
- `place_category`;
- `place_neighborhood_assignment`.

Aquí ya no se trabaja con la forma exacta en la que cada fuente entrega sus datos, sino con una estructura interna coherente.

---

## 4.5. Capa IA derivada

Esta capa almacena resultados de análisis inteligente sobre las reseñas.

Entidades principales:

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

Su objetivo es convertir texto de reseñas en señales explotables:

```text
plato detectado
→ sentimiento por mención
→ señales por local y plato
→ ranking Hidden Gems
```

---

## 4.6. Capa query / views

Esta capa expone vistas SQL preparadas para consulta y demo.

Se define en:

```text
db/ddl/08_ai_views.sql
```

Incluye vistas como:

- `vw_ai_pipeline_run_summary`;
- `vw_ai_dish_place_signals`;
- `vw_ai_hidden_gem_candidate_detail`;
- `vw_ai_hidden_gems_place_summary`;
- `vw_ai_hidden_gems_dish_summary`;
- `vw_ai_dish_mentions_with_sentiment`.

Estas vistas permiten consultar el ranking IA sin trabajar directamente con las tablas internas.

---

## 4.7. Capa artifacts / ops

Incluye todos los artefactos operativos que ayudan a ejecutar, revisar y validar el sistema.

Ejemplos:

- logs;
- perfiles de datos;
- resúmenes de transformación;
- resultados de deduplicación;
- resultados de importación;
- checks de IA;
- informes JSON de carga;
- exports de demo.

---

## 5. Componentes principales del sistema

## 5.1. Configuración

Se centraliza en `src/config/`.

Aquí se definen:

- settings del entorno;
- rutas de datos;
- endpoints de fuentes;
- claves de acceso;
- parámetros compartidos del sistema.

---

## 5.2. Conectores

Se encuentran en `src/connectors/`.

Son responsables de la interacción directa con la fuente:

- construir consultas;
- descargar respuestas;
- registrar `source_run`;
- persistir raw.

Ejemplos:

- Sevilla Geo;
- Overpass;
- Google Places.

---

## 5.3. Transformadores y normalización

Se ubican en módulos como `src/geo/` y `src/normalization/`.

Aquí se adapta la lógica específica de cada fuente a estructuras comunes del proyecto.

---

## 5.4. Deduplicación y matching

Esta parte reduce ruido, agrupa duplicados probables y prepara la consolidación multi-fuente.

Actualmente existe deduplicación intra-fuente y se deja preparado el camino para matching más avanzado entre OSM, Google Places y otras fuentes.

---

## 5.5. Importadores y loaders

Los importadores convierten resultados transformados en escritura controlada sobre el modelo canónico, de referencia o IA.

Ejemplos:

- importador geográfico de Sevilla Geo;
- importador de candidatos Overpass;
- importador de Google Places;
- importador de Google Places Reviews;
- loaders IA de catálogo, menciones, sentimiento, señales y ranking;
- loader específico del piloto IA Sevilla.

---

## 5.6. Base de datos

La persistencia principal del proyecto se apoya en **PostgreSQL + PostGIS**.

Se eligió porque permite:

- modelo relacional robusto;
- soporte geoespacial nativo;
- integridad referencial;
- índices espaciales, textuales y analíticos;
- persistencia tanto del core como de la capa IA derivada.

---

## 5.7. Notebooks IA

La fase IA se desarrolló inicialmente mediante notebooks para exploración, entrenamiento y validación.

### Prototipo Yelp

```text
04_dish_detection_dataset_exploration
05_dish_ner_dataset_builder
06_dish_ner_transformer_training
07_dish_ner_inference_and_mentions
08_dish_normalization_and_catalog_builder
09_dish_mention_sentiment_hybrid_v1
10_dish_signal_aggregation
11_hidden_gems_ranking_v1
```

### Piloto Sevilla

```text
12_sevilla_reviews_ai_exploration
13_sevilla_dish_candidate_detection
14_sevilla_dish_normalization_and_catalog
15_sevilla_mention_sentiment
16_sevilla_place_dish_signal_aggregation
17_sevilla_hidden_gems_ranking_pilot
```

Posteriormente, sus artefactos se integraron en PostgreSQL mediante loaders controlados.

---

## 6. Relación entre arquitectura lógica y estructura física

La arquitectura lógica se refleja directamente en la estructura del repositorio.

### Código

- `src/config/` → configuración;
- `src/connectors/` → adquisición;
- `src/geo/` → lógica geográfica;
- `src/normalization/` → normalización, candidatos, deduplicación e importación;
- `src/nlp/` → soporte previsto para evolución NLP/IA;
- `src/db/` → conexión y utilidades de base de datos;
- `src/utils/` → logging y soporte transversal;
- `scripts/` → puntos de entrada operativos, loaders, checks y consultas demo.

### Datos

- `data/raw/` → assets originales;
- `data/staging/` → salidas intermedias;
- `data/reference/` → datasets de referencia;
- `data/artifacts/` → logs, checks y resultados operativos;
- `data/artifacts/ai/` → artefactos IA, informes de carga, checks y demos;
- `data/artifacts/ai/sevilla/` → artefactos específicos del piloto Sevilla.

### Persistencia SQL

- `db/ddl/` → scripts de creación del schema y vistas;
- `db/queries/` → consultas auxiliares;
- `db/seeds/` → seeds y cargas base.

---

## 7. Decisiones arquitectónicas importantes

## 7.1. `place` como entidad canónica

No se usa una fuente externa como representación final del local. `place` es la entidad interna estable del sistema.

---

## 7.2. `place_source_ref` como capa de representación fuente

Cada local puede tener múltiples referencias por fuente. Esto evita mezclar directamente datos de OSM, Google o Yelp.

---

## 7.3. `review` ligada a fuente

Las reseñas son source-bound. No se fusionan automáticamente entre fuentes.

---

## 7.4. Geografía separada del local

La asignación de barrio se maneja mediante `place_neighborhood_assignment`, no como columna fija dentro de `place`.

---

## 7.5. Calidad como entidad explícita

Las incidencias relevantes se modelan en `validation_issue`, no solo en logs.

---

## 7.6. IA separada del core

Las tablas IA son derivadas y versionadas. No contaminan el core del dominio y pueden recalcularse con nuevas versiones.

---

## 7.7. Yelp como prototipo IA

Yelp Open Dataset se utiliza como corpus y prototipo para validar el módulo IA completo.

El ranking cargado se marca como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

No representa ranking final por barrios de Sevilla.

---

## 7.8. Sevilla pilot como primera ejecución local real

Las reviews de Google Places Sevilla se usan para validar el flujo local real.

El piloto se identifica como:

```text
artifact_ranking_scope = sevilla_pilot
is_production_ready = false
```

Por una restricción actual del DDL, se almacena en base con:

```text
db_ranking_scope = other
```

pero conserva la traza `sevilla_pilot` en `ranking_config_json`.

---

## 8. Estado actual de la arquitectura

Actualmente la arquitectura ya está operativa en varios bloques completos.

### Sevilla Geo

- ingesta raw;
- transformación geográfica;
- importación de referencia;
- comprobación de resultados.

### OSM / Overpass

- ingesta raw;
- perfilado;
- transformación a candidato común;
- deduplicación intra-fuente;
- importación canónica;
- comprobación.

### Google Places Text Search

- conexión con Places API;
- raw trazable;
- transformación;
- deduplicación;
- importación canónica;
- batch por barrios/distritos;
- checks.

### Google Places Reviews

- extracción de reviews reales mediante Place Details;
- raw y staging;
- importación en `review`;
- checks individuales y batch.

### Yelp Open Dataset e IA

- preparación de corpus gastronómico;
- entrenamiento y validación del módulo IA;
- integración en PostgreSQL;
- vistas SQL de consulta;
- script demo de ranking.

### Piloto IA Sevilla

- exportación de reviews reales desde PostgreSQL;
- exploración del corpus;
- detección de candidatos de platos en español;
- normalización y catálogo local;
- sentimiento por mención;
- agregación local-plato;
- ranking `sevilla_pilot`;
- carga en PostgreSQL;
- check completo sin errores ni warnings;
- script demo de consulta Sevilla.

---

## 9. Evolución prevista

La arquitectura está preparada para incorporar próximamente:

- consolidación de scripts demo finales;
- contrato de datos para dashboard;
- dashboard piloto, preferiblemente con Streamlit;
- revisión visual y funcional de resultados;
- posible API mínima con FastAPI;
- mejora de reglas IA;
- posible entrenamiento o adaptación de modelos en español/multilingües;
- promoción controlada hacia ranking productivo cuando haya validación suficiente.

---

## 10. Conclusión

La arquitectura de Hidden Gems se ha diseñado para equilibrar cinco necesidades principales:

- trazabilidad;
- control de calidad;
- flexibilidad ante múltiples fuentes;
- construcción progresiva de un modelo canónico útil;
- explotación inteligente mediante una capa IA derivada.

La arquitectura ya no solo prepara el terreno para NLP y ranking: actualmente contiene una integración IA completa validada con Yelp como prototipo y una primera ejecución local real sobre Sevilla con Google Places Reviews, ranking piloto cargado, validado y consultable.
