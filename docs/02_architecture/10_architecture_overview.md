# 10. Visión de la arquitectura

## 1. Finalidad de la arquitectura

La arquitectura de **Hidden Gems Pipeline** está diseñada para soportar un procesamiento de datos gastronómicos **modular, reproducible, trazable, extensible y preparado para inteligencia artificial aplicada**.

Su función no es solo descargar información desde varias fuentes, sino transformar progresivamente datos heterogéneos hasta convertirlos en:

- una base canónica de locales, fuentes, reseñas, geografía y categorías;
- una capa derivada de IA capaz de detectar platos, normalizarlos, estimar sentimiento por mención y generar señales local-plato;
- rankings explicables de candidatos Hidden Gems;
- exports y dashboards para explotación analítica.

El proyecto ha evolucionado desde una arquitectura de adquisición hacia una plataforma completa de datos + IA + ranking + dashboard, manteniendo siempre la separación entre dato fuente, dato canónico, dato derivado y artefactos de explotación.

---

## 2. Principios de diseño

### 2.1. Trazabilidad primero

Cada ejecución del pipeline debe poder reconstruirse. Para ello se registran:

- el sistema fuente;
- la ejecución concreta (`source_run`);
- el asset raw generado (`raw_asset`);
- las incidencias detectadas (`validation_issue`);
- las ejecuciones de IA (`ai_pipeline_run`);
- las versiones de modelos, reglas o métodos IA (`ai_model_version`);
- los artefactos derivados de ranking, comparación y dashboard.

La trazabilidad ya no se limita a la ingesta. También alcanza a la capa IA, a los modelos entrenados, a los rankings generados y a los exports de dashboard.

---

### 2.2. Separación por capas

No se mezclan descarga, transformación, consolidación, análisis IA, ranking y explotación en una sola fase.

El sistema trabaja con capas diferenciadas:

```text
raw
→ staging
→ reference
→ canonical / business
→ AI derived layer
→ model inference artifacts
→ ranking artifacts
→ dashboard exports
→ query / views
→ operations / QA
```

Esta separación permite depurar, reejecutar y evolucionar cada parte sin romper el resto.

---

### 2.3. No perder el raw

La información original descargada desde la fuente se conserva antes de aplicar limpieza o normalización. El raw actúa como evidencia auditable y permite reconstruir transformaciones posteriores.

---

### 2.4. Modelo canónico interno

Las fuentes externas no son el modelo final. La entidad central del sistema es `place`, mientras que `place_source_ref` conserva la representación específica de cada fuente.

Esto permite integrar datos de:

- OSM / Overpass;
- Google Places;
- Google Places Reviews;
- Yelp Open Dataset como corpus/prototipo IA;
- futuras fuentes.

---

### 2.5. Capa IA derivada, no invasiva

Los resultados IA no se incrustan directamente en `place` ni sustituyen al core del modelo. La arquitectura añade una capa derivada formada por:

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

El proyecto usa dos niveles complementarios:

1. **Versionado en PostgreSQL**, mediante `ai_model_version` y `ai_pipeline_run`, para resultados cargados.
2. **Versionado por artefactos**, mediante carpetas, summaries JSON, modelos locales y exports, para la fase IA v2 y dashboards.

Este principio se aplica a:

- prototipo Yelp;
- piloto Sevilla v1;
- fase Sevilla IA v2;
- comparaciones entre rankings;
- exports de dashboard.

---

### 2.7. Verticales completas

El proyecto se construye por verticales de fuente o módulo. Cada vertical debe recorrer un flujo completo:

```text
adquisición / preparación
→ raw o input controlado
→ transformación
→ persistencia o artefacto estable
→ check
→ documentación
```

Esto se ha seguido tanto en las fuentes de datos como en la integración IA, dashboards y fase Sevilla IA v2.

---

### 2.8. Extensibilidad

La arquitectura está planteada para soportar nuevas fuentes, nuevos modelos, nuevas reglas de ranking, una futura capa de API y dashboards adicionales sin rediseñar el núcleo del sistema.

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
→ reviews
→ capa IA derivada
→ modelos entrenados / inferencia local
→ señales local-plato
→ ranking Hidden Gems
→ comparación de versiones
→ dashboard / explotación analítica
```

La arquitectura distingue cuatro grandes familias de flujo:

1. **Flujos de referencia**, para geografía y datos estructurales.
2. **Flujos de negocio**, para locales, categorías, fuentes y reseñas.
3. **Flujos IA derivados**, para platos, menciones, sentimiento, señales y ranking.
4. **Flujos de explotación**, para consultas, exports y dashboards.

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
→ views / artifacts / dashboard
```

Actualmente existen tres aplicaciones principales de este flujo:

1. **Yelp prototype**, usado para validar arquitectura e integración IA con corpus externo.
2. **Sevilla pilot v1**, usado para validar el flujo local con reviews reales de Google Places Sevilla.
3. **Sevilla IA v2**, usado como fase avanzada con modelos entrenados, inferencia local, ranking v2, comparación v1/v2 y dashboard final.

---

## 3.4. Flujos de explotación analítica

El proyecto no se queda en la persistencia de datos. También genera outputs consultables:

```text
ranking artifacts
→ dashboard export
→ Streamlit dashboard
→ análisis territorial / platos / locales / reseñas
```

Dashboards actuales:

```text
dashboard/streamlit_app.py              → dashboard Sevilla v1
dashboard/streamlit_yelp_app.py         → dashboard Yelp
dashboard/streamlit_sevilla_v2_app.py   → dashboard Sevilla IA v2
```

---

## 4. Capas principales

## 4.1. Capa raw

Primera capa persistente del pipeline. Almacena la descarga original de cada fuente sin transformaciones destructivas.

Responsabilidades:

- descargar o leer la fuente;
- persistir el asset raw en disco;
- registrar metadata en `raw_asset`;
- vincularlo con `source_run`.

---

## 4.2. Capa staging

Capa intermedia de trabajo. Aquí se realizan:

- validaciones estructurales;
- limpieza básica;
- normalización intermedia;
- derivación de candidatos;
- deduplicación;
- artefactos auxiliares de perfilado y control.

---

## 4.3. Capa reference

Almacena datos de referencia relativamente estables.

Ejemplo principal:

- barrios y distritos de Sevilla.

---

## 4.4. Capa canónica / de negocio

Representación consolidada del dominio.

Entidades principales:

- `place`;
- `place_source_ref`;
- `review`;
- `place_category`;
- `place_neighborhood_assignment`.

---

## 4.5. Capa IA derivada

Almacena resultados de análisis inteligente sobre las reseñas.

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

## 4.6. Capa de inferencia IA v2

En la fase Sevilla IA v2 se añade una capa de inferencia local basada en modelos entrenados. Estos modelos no se suben al repositorio, pero se usan localmente desde `models/`.

Modelos principales:

```text
models/sevilla_dish_ner_beto_v1_2/
models/sevilla_dish_normalization_reranker_beto_v1/
models/sevilla_mention_sentiment_absa_beto_v1/
```

Flujo:

```text
reviews / mentions
→ NER v1.2
→ hybrid + NER candidates v2
→ normalization reranker v1
→ ABSA sentiment v1
→ place-dish signals v2
→ ranking v2
```

---

## 4.7. Capa query / views

Expone vistas SQL preparadas para consulta y demo.

Se define principalmente en:

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

## 4.8. Capa artifacts / ops

Incluye artefactos operativos que ayudan a ejecutar, revisar y validar el sistema.

Ejemplos:

- logs;
- perfiles de datos;
- resúmenes de transformación;
- resultados de deduplicación;
- resultados de importación;
- checks de IA;
- reports JSON de carga;
- outputs de ranking;
- exports de dashboard;
- comparaciones v1/v2.

---

## 4.9. Capa dashboard

Capa de explotación visual con Streamlit.

Incluye:

- KPIs del ranking;
- top global;
- análisis territorial;
- mapas con coordenadas;
- análisis por plato y local;
- evidencias y calidad;
- comparación v1/v2;
- detalle de menciones y reseñas;
- explicación de scoring.

---

## 5. Componentes principales del sistema

### 5.1. Configuración

Se centraliza en `src/config/`.

Define:

- settings del entorno;
- rutas de datos;
- endpoints de fuentes;
- claves de acceso;
- parámetros compartidos del sistema.

---

### 5.2. Conectores

Se encuentran en `src/connectors/`.

Responsables de:

- construir consultas;
- descargar respuestas;
- registrar `source_run`;
- persistir raw.

---

### 5.3. Transformadores y normalización

Se ubican en módulos como `src/geo/` y `src/normalization/`.

Adaptan la lógica específica de cada fuente a estructuras comunes.

---

### 5.4. Deduplicación y matching

Reduce ruido, agrupa duplicados probables y prepara la consolidación multi-fuente.

---

### 5.5. Importadores y loaders

Convierten resultados transformados en escritura controlada sobre el modelo canónico, de referencia o IA.

Ejemplos:

- importador geográfico de Sevilla Geo;
- importador de candidatos Overpass;
- importador de Google Places;
- importador de Google Places Reviews;
- loaders IA de catálogo, menciones, sentimiento, señales y ranking;
- loader específico del piloto IA Sevilla.

---

### 5.6. Base de datos

La persistencia principal se apoya en **PostgreSQL + PostGIS**.

Se eligió porque permite:

- modelo relacional robusto;
- soporte geoespacial nativo;
- integridad referencial;
- índices espaciales, textuales y analíticos;
- persistencia tanto del core como de la capa IA derivada.

---

### 5.7. Notebooks IA

La fase IA se desarrolló inicialmente en notebooks para exploración, entrenamiento y validación.

#### Prototipo Yelp

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

#### Piloto Sevilla v1

```text
12_sevilla_reviews_ai_exploration
13_sevilla_dish_candidate_detection
14_sevilla_dish_normalization_and_catalog
15_sevilla_mention_sentiment
16_sevilla_place_dish_signal_aggregation
17_sevilla_hidden_gems_ranking_pilot
```

#### Sevilla IA v2

```text
NER v1.2 training
normalization/entity linking reranker training
mention sentiment ABSA training
local inference scripts
ranking v2
dashboard v2
```

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
- `scripts/` → puntos de entrada operativos, loaders, checks, consultas demo e inferencia IA;
- `dashboard/` → dashboards Streamlit;
- `models/` → modelos locales no versionados.

### Datos

- `data/raw/` → assets originales;
- `data/staging/` → salidas intermedias;
- `data/reference/` → datasets de referencia;
- `data/artifacts/` → logs, checks y resultados operativos;
- `data/artifacts/ai/` → artefactos IA, informes de carga, checks y demos;
- `data/artifacts/ai/sevilla/` → artefactos específicos de Sevilla, incluyendo v1 y v2.

### Persistencia SQL

- `db/ddl/` → scripts de creación del schema y vistas;
- `db/queries/` → consultas auxiliares;
- `db/seeds/` → seeds y cargas base.

---

## 7. Decisiones arquitectónicas importantes

### 7.1. `place` como entidad canónica

No se usa una fuente externa como representación final del local. `place` es la entidad interna estable.

---

### 7.2. `place_source_ref` como capa de representación fuente

Cada local puede tener múltiples referencias por fuente. Esto evita mezclar directamente datos de OSM, Google o Yelp.

---

### 7.3. `review` ligada a fuente

Las reseñas son source-bound. No se fusionan automáticamente entre fuentes.

---

### 7.4. Geografía separada del local

La asignación de barrio se maneja mediante `place_neighborhood_assignment`, no como columna fija dentro de `place`.

---

### 7.5. Calidad como entidad explícita

Las incidencias relevantes se modelan en `validation_issue`, no solo en logs.

---

### 7.6. IA separada del core

Las tablas IA son derivadas y versionadas. No contaminan el core del dominio y pueden recalcularse.

---

### 7.7. Yelp como prototipo IA

Yelp Open Dataset se utiliza como corpus y prototipo para validar el módulo IA completo.

El ranking cargado se marca como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

No representa ranking final por barrios de Sevilla.

---

### 7.8. Sevilla pilot como primera ejecución local real

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

### 7.9. Sevilla IA v2 como fase avanzada de modelos

La fase IA v2 no sustituye al piloto v1, sino que lo amplía.

Se entrena y aplica una cadena especializada:

```text
NER de platos
→ normalización/entity linking
→ sentimiento por mención ABSA
→ señales place-dish
→ ranking v2
```

El resultado se mantiene como experimental:

```text
is_production_ready_v2 = false
```

pero ya se explota en dashboard como MVP analítico final para entrega académica.

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

### Piloto IA Sevilla v1

- exportación de reviews reales desde PostgreSQL;
- exploración del corpus;
- detección de candidatos de platos en español;
- normalización y catálogo local;
- sentimiento por mención;
- agregación local-plato;
- ranking `sevilla_pilot`;
- carga en PostgreSQL;
- check completo sin errores ni warnings;
- script demo de consulta Sevilla;
- dashboard/export inicial.

### Sevilla IA v2

- entrenamiento de modelos específicos en Kaggle;
- inferencia local con modelos guardados en `models/`;
- combinación híbrida + NER;
- normalización con reranker;
- sentimiento ABSA;
- señales local-plato v2;
- ranking Hidden Gems Sevilla v2;
- comparación v1 vs v2;
- export dashboard v2;
- dashboard Streamlit Sevilla IA v2.

Resultados principales del ranking v2:

```text
candidatos puntuados: 2.335
candidatos seleccionados: 268
locales seleccionados: 198
platos seleccionados: 40
barrios seleccionados: 67
distritos seleccionados: 11
```

---

## 9. Evolución prevista

La arquitectura queda cerrada para entrega académica como MVP técnico avanzado. A partir de este punto, las siguientes líneas pertenecen a una fase futura de producto/producción:

- validación humana del top ranking;
- mejora del catálogo y aliases de platos;
- ajuste de penalización para platos demasiado genéricos;
- descarga automática de modelos desde Drive u otro repositorio privado;
- tests automáticos más completos;
- API mínima con FastAPI;
- despliegue del dashboard;
- automatización programada de la cadena completa;
- posible promoción controlada a ranking productivo tras validación.

---

## 10. Conclusión

La arquitectura de Hidden Gems se ha diseñado para equilibrar cinco necesidades principales:

- trazabilidad;
- control de calidad;
- flexibilidad ante múltiples fuentes;
- construcción progresiva de un modelo canónico útil;
- explotación inteligente mediante una capa IA derivada.

El estado final de entrega ya no es únicamente un piloto: el proyecto contiene una arquitectura completa de datos + IA + ranking + dashboard, con Yelp como prototipo externo, Sevilla v1 como baseline local y Sevilla IA v2 como MVP analítico final asistido por modelos.
