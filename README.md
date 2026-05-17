# Hidden Gems Pipeline

Pipeline inteligente de adquisición, validación, normalización, enriquecimiento, integración IA, ranking y dashboard para **Hidden Gems**, un proyecto orientado a descubrir **platos destacados por local y barrio**, con foco inicial en Sevilla.

> Estado de entrega académica: **MVP avanzado / prototipo analítico funcional cerrado para Proyecto Integrado**.  
> Estado de producción: **no productivo todavía**. La fase IA v2 está validada como ranking experimental asistido por modelos, pendiente de validación humana, escalado y automatización si el proyecto continúa hacia producción.

---

## Índice rápido

1. [¿Qué es este proyecto?](#1-qué-es-este-proyecto)
2. [Objetivo actual de la entrega](#2-objetivo-actual-de-la-entrega)
3. [Problema que resuelve](#3-problema-que-resuelve)
4. [Fuentes de datos](#4-fuentes-de-datos)
5. [Google, Yelp y alcance productivo](#5-google-yelp-y-alcance-productivo)
6. [Arquitectura general](#6-arquitectura-general)
7. [Stack tecnológico](#7-stack-tecnológico)
8. [Modelo de datos](#8-modelo-de-datos)
9. [Estado actual del proyecto](#9-estado-actual-del-proyecto)
10. [Estructura del repositorio](#10-estructura-del-repositorio)
11. [Configuración inicial](#11-configuración-inicial)
12. [Ejecuciones principales](#12-ejecuciones-principales)
13. [Yelp Open Dataset](#13-yelp-open-dataset)
14. [Módulo IA e integración PostgreSQL](#14-módulo-ia-e-integración-postgresql)
15. [Fase Sevilla IA v2](#15-fase-sevilla-ia-v2)
16. [Dashboards](#16-dashboards)
17. [Capas y artefactos principales](#17-capas-y-artefactos-principales)
18. [Reglas importantes de Git](#18-reglas-importantes-de-git)
19. [Principios de diseño](#19-principios-de-diseño)
20. [Documentación detallada](#20-documentación-detallada)
21. [Roadmap](#21-roadmap)
22. [Estado final de entrega](#22-estado-final-de-entrega)

---

## 1. ¿Qué es este proyecto?

**Hidden Gems Pipeline** es el núcleo de procesamiento de datos e IA del proyecto Hidden Gems.

El objetivo de este repositorio no es construir directamente una aplicación final de cara al usuario, sino desarrollar una infraestructura central, reutilizable, trazable y extensible que permita:

- adquirir datos desde distintas fuentes;
- conservar una capa **raw** auditable;
- validar y limpiar datos de entrada;
- normalizar información heterogénea en un modelo común;
- enriquecer geográficamente los registros;
- consolidar locales gastronómicos en una entidad canónica `place`;
- asociar referencias externas mediante `place_source_ref`;
- enriquecer locales con reseñas reales cuando sea posible;
- construir corpus y artefactos para tareas NLP/IA;
- detectar menciones de platos en reseñas;
- normalizar variantes de platos en un catálogo canónico;
- calcular sentimiento asociado a menciones de platos;
- agregar señales por local y plato;
- generar rankings explicables de candidatos Hidden Gems;
- exportar resultados limpios para dashboards;
- comparar versiones del ranking y documentar las mejoras.

En otras palabras, este repositorio implementa la **infraestructura de datos, automatización, IA aplicada y explotación analítica** sobre la que se apoyará el resto del sistema Hidden Gems.

---

## 2. Objetivo actual de la entrega

El enfoque final de esta entrega es:

> **Pipeline inteligente de adquisición y procesamiento de datos gastronómicos para descubrir platos destacados por barrio mediante IA y ranking explicable.**

La entrega académica incluye:

```text
fuentes externas
→ conectores
→ raw trazable
→ staging
→ validación / limpieza
→ normalización
→ enriquecimiento geográfico
→ deduplicación / matching
→ persistencia canónica
→ reviews
→ datasets IA
→ modelos entrenados
→ inferencia local
→ señales por local y plato
→ ranking Hidden Gems Sevilla v2
→ comparación v1 vs v2
→ dashboard final
→ documentación técnica
```

El resultado final no se presenta como producto en producción, sino como un **MVP avanzado** con una cadena funcional de datos e IA de extremo a extremo.

---

## 3. Problema que resuelve

En el dominio gastronómico, la información útil suele estar dispersa, incompleta y en formatos distintos según la fuente.

Problemas habituales:

- cada fuente aporta datos con estructuras diferentes;
- los mismos locales pueden aparecer duplicados entre fuentes;
- hay registros incompletos, inconsistentes o ruidosos;
- la información geográfica no siempre viene preparada para trabajar por barrio;
- las reseñas no siempre están asociadas de forma clara a una entidad canónica;
- los datos no suelen estar listos directamente para análisis, NLP o ranking;
- las reseñas hablan de locales completos, pero Hidden Gems necesita extraer información más fina: platos concretos, menciones, sentimiento y señales agregadas.

Este pipeline resuelve ese problema creando un flujo reproducible para:

- capturar datos de fuentes abiertas y externas;
- trazar cada ejecución y cada asset descargado;
- transformar datos heterogéneos a un formato común;
- asignar localización geográfica útil dentro de Sevilla;
- construir entidades canónicas (`place`) separadas de sus representaciones por fuente (`place_source_ref`);
- enriquecer locales con reviews operativas cuando están disponibles;
- construir una capa IA derivada sobre `place` y `review`;
- generar señales y rankings explicables de platos destacados.

---

## 4. Fuentes de datos

Las fuentes definidas para el pipeline son:

| Fuente | Rol dentro del proyecto | Estado |
|---|---|---|
| Sevilla Geo | Barrios y distritos oficiales de Sevilla | Implementada |
| OSM / Overpass | Fuente abierta de POIs gastronómicos | Implementada |
| Google Places Text Search | Fuente dinámica para descubrimiento/enriquecimiento de locales | Implementada |
| Google Places Reviews | Reviews reales asociadas a locales ya consolidados | Implementada |
| Yelp Open Dataset | Corpus externo para entrenamiento, validación e integración prototipo IA | Implementada como corpus/prototipo IA |

---

## 5. Google, Yelp y alcance productivo

El proyecto diferencia claramente entre datos **operativos**, datos de **entrenamiento/validación IA** y datos de **prototipo**.

### Google Places / Google Reviews

Google se usa como fuente operativa local:

```text
Google Places Text Search
→ place
→ place_source_ref
```

```text
Google Places Reviews
→ review
→ place
→ barrio
```

Las reviews de Google se guardan cuando el local ya existe en el modelo canónico y tiene una referencia válida en `place_source_ref`.

### Yelp Open Dataset

Yelp se usa con dos roles controlados:

1. **Corpus externo para IA**: entrenamiento, validación y experimentación NLP sobre reseñas gastronómicas.
2. **Prototipo integrado en PostgreSQL**: carga controlada de negocios/reviews Yelp como datos prototipo para validar la capa IA completa.

Flujo Yelp actual:

```text
Yelp business + Yelp review
→ subset gastronómico
→ corpus IA
→ Dish NER / normalización / sentimiento / ranking
→ carga prototipo en PostgreSQL
```

Yelp **no representa datos productivos de Sevilla**. Los resultados asociados a Yelp se marcan como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

Esto permite validar de extremo a extremo el sistema IA sin confundirlo con el ranking final por barrios de Sevilla.

---

## 6. Arquitectura general

El proyecto sigue una arquitectura por capas, modular y reproducible.

### Capas principales

- **raw**: conservación trazable de datos fuente sin transformar;
- **staging**: transformación intermedia, validación y artefactos derivados;
- **reference**: datos de referencia estructurales, como geografía oficial;
- **canonical / business**: entidades centrales del dominio, como `place`, `place_source_ref` y `review`;
- **AI derived layer**: entidades derivadas de IA como platos, menciones, sentimiento, señales y ranking;
- **model inference artifacts**: salidas locales de modelos entrenados y capas intermedias v2;
- **dashboard exports**: datasets limpios para explotación visual;
- **artifacts / ops**: logs, perfiles, resúmenes y resultados de comprobación;
- **views / query layer**: vistas SQL y scripts de consulta para explotar resultados.

### Flujo conceptual general

```text
Fuentes externas
→ conectores
→ raw
→ validación / limpieza
→ normalización
→ enriquecimiento geográfico
→ deduplicación / matching
→ persistencia canónica
→ reviews
→ procesamiento IA
→ señales
→ ranking
→ vistas / dashboard / demo de consulta
```

### Flujo final Sevilla IA v2

```text
Google Reviews Sevilla
→ exportación / datasets de anotación
→ Modelo 1: NER de platos
→ Hybrid + NER mention candidates v2
→ Modelo 3: normalización / entity linking reranker
→ Modelo 2: sentimiento por mención / ABSA
→ place-dish signals v2
→ ranking Hidden Gems Sevilla v2
→ comparación v1 vs v2
→ dashboard Sevilla IA v2
```

---

## 7. Stack tecnológico

### Lenguaje y librerías base

- Python
- pandas
- requests / httpx
- SQLAlchemy
- psycopg2-binary
- pydantic
- pydantic-settings
- RapidFuzz
- pytest
- logging
- Jupyter / notebooks

### IA / NLP

- Hugging Face Transformers
- PyTorch
- Datasets
- BETO (`dccuchile/bert-base-spanish-wwm-cased`)
- Token Classification para NER de platos
- Sequence Classification para normalización / reranking
- Sequence Classification para sentimiento por mención / ABSA
- Reglas, aliases y limpieza textual para soporte híbrido
- Agregación de señales
- Ranking explicable basado en scoring

### Persistencia y geodatos

- PostgreSQL
- PostGIS

### Visualización y explotación

- Streamlit
- Plotly
- pandas

### Exposición futura

- FastAPI

---

## 8. Modelo de datos

El pipeline se apoya en un modelo relacional diseñado para separar claramente:

- entidades canónicas del dominio;
- referencias por fuente;
- geografía oficial;
- clasificación;
- trazabilidad;
- calidad;
- reviews operativas;
- corpus y resultados derivados de IA.

### Núcleo de negocio

- `place`
- `place_source_ref`
- `review`

### Geografía

- `district`
- `neighborhood`
- `place_neighborhood_assignment`

### Clasificación

- `category`
- `place_category`

### Gobierno y trazabilidad

- `source_system`
- `source_run`
- `raw_asset`

### Calidad

- `validation_issue`

### Capa IA integrada

- `ai_model_version`
- `ai_pipeline_run`
- `dish`
- `dish_alias`
- `dish_mention`
- `dish_mention_sentiment`
- `dish_place_signal`
- `hidden_gem_candidate`

### Vistas IA

- `vw_ai_pipeline_run_summary`
- `vw_ai_dish_place_signals`
- `vw_ai_hidden_gem_candidate_detail`
- `vw_ai_hidden_gems_yelp_top`
- `vw_ai_hidden_gems_place_summary`
- `vw_ai_hidden_gems_dish_summary`
- `vw_ai_hidden_gems_city_summary`
- `vw_ai_dish_mentions_with_sentiment`

---

## 9. Estado actual del proyecto

El proyecto cuenta con una base estructural montada en PostgreSQL/PostGIS, verticales funcionales, una integración IA inicial sobre Yelp y una fase avanzada Sevilla IA v2 basada en modelos entrenados.

### Verticales implementadas

#### Sevilla Geo

- ingesta raw;
- transformación y validación geográfica;
- importación de distritos y barrios;
- comprobaciones de carga.

#### OSM / Overpass

- ingesta raw desde Overpass;
- perfilado del dataset;
- transformación a candidato común de local;
- deduplicación intra-fuente;
- importación canónica a `place`, `place_source_ref`, `place_category` y `place_neighborhood_assignment`;
- checks post-importación.

#### Google Places Text Search

- conexión con Google Places API New;
- ejecución de Text Search;
- raw trazable por query;
- transformación a candidatos normalizados;
- deduplicación;
- importación canónica;
- batch por barrio/distrito;
- check global de batch.

#### Google Places Reviews

- ejecución de Place Details sobre locales ya existentes;
- extracción de reviews reales;
- raw trazable;
- staging de reviews;
- importación en `hidden_gems.review`;
- check post-importación;
- orquestador individual;
- batch controlado de reviews;
- check global de batch.

Primer batch validado:

```text
5 locales → 25 reviews
0 errores
0 validation issues
reviews vinculadas a place/place_source_ref/barrio
```

#### Yelp Open Dataset

- dataset `.tar` descargado localmente;
- perfilado del `.tar`;
- extracción controlada de `business.json` y `review.json`;
- perfilado JSON Lines;
- subset de negocios gastronómicos;
- subset de reviews gastronómicas;
- construcción de corpus IA/NLP;
- carga prototipo de negocios y reviews Yelp en PostgreSQL;
- uso como base experimental para el módulo IA completo.

### Módulo IA integrado sobre Yelp

Se ha construido e integrado una cadena IA completa:

```text
reviews Yelp
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems v1
→ carga en PostgreSQL
→ vistas SQL
→ consultas demo
```

Estado final de carga IA Yelp:

```text
dish: 9.937
dish_alias: 10.235
dish_mention: 94.932
dish_mention_sentiment: 94.932
dish_place_signal: 31.036
hidden_gem_candidate: 622
```

El ranking IA cargado está marcado como prototipo:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

### Fase Sevilla IA v2 cerrada

La fase Sevilla IA v2 incorpora modelos entrenados específicamente para mejorar el ranking sobre datos reales/prototipo de Sevilla:

```text
NER v1.2
→ Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
→ Hidden Gems Ranking Sevilla v2
→ Dashboard Sevilla IA v2
```

Resultados principales:

```text
candidatos puntuados v2: 2.335
candidatos seleccionados v2: 268
locales seleccionados: 198
platos seleccionados: 40
barrios seleccionados: 67
distritos seleccionados: 11
coincidencias v1/v2: 119
cobertura de v1 dentro de v2: 79,3 %
```

---

## 10. Estructura del repositorio

```text
hidden-gems-pipeline/
│   .env
│   .env.example
│   .gitignore
│   main.py
│   README.md
│   requirements.txt
│
├───dashboard/
│   ├───streamlit_app.py
│   ├───streamlit_yelp_app.py
│   └───streamlit_sevilla_v2_app.py
│
├───data/
│   ├───artifacts/
│   │   ├───ai/
│   │   │   ├───sevilla/
│   │   │   │   ├───dashboard/
│   │   │   │   ├───dashboard_v2/
│   │   │   │   └───model_inference/
│   │   │   └───yelp/
│   │   ├───google_places_batches/
│   │   ├───google_places_reviews_batches/
│   │   ├───google_places_reviews_import/
│   │   ├───google_places_reviews_import_qa/
│   │   ├───google_places_reviews_pipeline/
│   │   ├───google_places_reviews_staging_qa/
│   │   ├───logs/
│   │   ├───nlp_corpus/
│   │   └───yelp_open_dataset_qa/
│   ├───external/
│   │   └───yelp_open_dataset/
│   ├───raw/
│   ├───reference/
│   └───staging/
│       ├───google_places/
│       ├───google_places_reviews/
│       └───yelp_open_dataset/
│
├───db/
│   ├───ddl/
│   │   ├───00_foundation.sql
│   │   ├───01_geo_governance.sql
│   │   ├───02_geo_reference.sql
│   │   ├───03_core_places.sql
│   │   ├───04_classification_and_geo_assignment.sql
│   │   ├───05_validation.sql
│   │   ├───06_review_enrichment.sql
│   │   ├───07_ai_module.sql
│   │   └───08_ai_views.sql
│   ├───queries/
│   └───seeds/
│
├───docs/
│   ├───01_context/
│   ├───02_architecture/
│   ├───03_data_model/
│   ├───04_sources/
│   ├───05_verticals/
│   ├───08_operations/
│   ├───10_ai_module/
│   ├───11_ai_integration/
│   ├───12_sevilla_ai_pilot/
│   └───13_sevilla_ai_v2/
│
├───models/
│   ├───sevilla_dish_ner_beto_v1_2/
│   ├───sevilla_dish_normalization_reranker_beto_v1/
│   └───sevilla_mention_sentiment_absa_beto_v1/
│
├───notebooks/
├───scripts/
├───src/
│   ├───config/
│   ├───connectors/
│   ├───db/
│   ├───geo/
│   ├───ingestion/
│   ├───nlp/
│   ├───normalization/
│   └───utils/
│
└───tests/
```

> Nota: `models/`, `.env`, `.venv`, `data/` y artefactos grandes no deben subirse al repositorio.

---

## 11. Configuración inicial

### Crear entorno virtual

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configurar variables de entorno

Crear `.env` a partir de `.env.example`.

Variables principales:

```text
APP_ENV=dev
PGHOST=localhost
PGPORT=5433
PGDATABASE=hidden_gems
PGUSER=...
PGPASSWORD=...
GOOGLE_MAPS_API_KEY=...
```

También se pueden configurar rutas de datos si se quiere cambiar la estructura por defecto.

### Verificar conexión

```powershell
python -m scripts.check_db_connection
python -m scripts.check_schema
```

---

## 12. Ejecuciones principales

### Sevilla Geo

Carga de referencia geográfica:

```powershell
python -m scripts.load_sevilla_geo_reference --source-version 2026_04
```

Comprobación:

```powershell
python -m scripts.check_sevilla_geo_load --source-version 2026_04
```

---

### OSM / Overpass

Ejecución del pipeline Overpass:

```powershell
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Comprobación del import:

```powershell
python -m scripts.check_overpass_import
```

---

### Google Places Text Search individual

```powershell
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_text_search_test `
  --max-result-count 3
```

---

### Google Places por barrios / distritos

Dry-run:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_dry_run_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --dry-run
```

Batch sin importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_no_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --skip-import `
  --max-errors 10
```

Batch con importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_alias_import_v1 `
  --neighborhood "TRIANA CASCO ANTIGUO" `
  --neighborhood "NERVION" `
  --queries-per-neighborhood 2 `
  --max-result-count 5 `
  --max-errors 10
```

Check de batch:

```powershell
python -m scripts.check_google_places_batch `
  --batch-name gp_alias_import_v1 `
  --save-artifact
```

---

### Google Places Reviews individual

Place Details sin importación:

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_no_import `
  --skip-import
```

Place Details con importación:

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --place-source-ref-id <PLACE_SOURCE_REF_ID> `
  --query-name gp_reviews_pipeline_import
```

Automático sobre primer local disponible:

```powershell
python -m scripts.load_google_places_reviews_pipeline `
  --limit-first `
  --query-name gp_reviews_pipeline_limit_first_test
```

---

### Google Places Reviews batch

Dry-run:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_dry_run_v1 `
  --limit-places 5 `
  --dry-run
```

Batch sin importación:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_no_import_v1 `
  --limit-places 5 `
  --skip-import `
  --max-total-places 5 `
  --max-errors 5
```

Batch con importación:

```powershell
python -m scripts.run_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --limit-places 5 `
  --max-total-places 5 `
  --max-errors 5
```

Check global:

```powershell
python -m scripts.check_google_places_reviews_batch `
  --batch-name gp_reviews_batch_import_v1 `
  --save-artifact
```

---

## 13. Yelp Open Dataset

La vertical Yelp trabaja con el dataset descargado localmente en formato `.tar`.

Yelp se usa como corpus externo para IA/NLP y como prototipo controlado de integración IA. No se considera fuente productiva de Sevilla.

### Ubicación local recomendada

```text
data/external/yelp_open_dataset/yelp_dataset-001.tar
```

### Perfilado del TAR

```powershell
python -m scripts.profile_yelp_tar `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

### Extracción controlada

Extrae solo `business.json` y `review.json`:

```powershell
python -m scripts.extract_yelp_selected_files `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

### Perfilado JSON Lines

```powershell
python -m scripts.profile_yelp_jsonl_files `
  --save-artifact
```

### Subset de negocios gastronómicos

```powershell
python -m scripts.build_yelp_food_business_subset `
  --min-review-count 1 `
  --save-artifact
```

### Subset de reviews gastronómicas

Prueba inicial sobre 100.000 líneas:

```powershell
python -m scripts.build_yelp_food_review_subset `
  --max-lines 100000 `
  --min-text-length 40 `
  --save-artifact
```

Construcción controlada de un subset por número de reviews:

```powershell
python -m scripts.build_yelp_food_review_subset `
  --max-reviews 100000 `
  --min-text-length 40 `
  --save-artifact
```

### Corpus IA/NLP Yelp

```powershell
python -m scripts.build_yelp_nlp_corpus `
  --corpus-name yelp_food_reviews_corpus_sample_100k_lines `
  --min-text-length 80 `
  --max-text-length 5000 `
  --save-artifact
```

### Carga del núcleo Yelp para prototipo IA

Carga negocios y reviews Yelp en el modelo canónico para poder conectar artefactos IA con `place` y `review`.

```powershell
python -m scripts.load_yelp_ai_core_reviews `
  --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
  --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl
```

---

## 14. Módulo IA e integración PostgreSQL

La cadena IA se ha desarrollado primero en notebooks y después se ha integrado en PostgreSQL mediante tablas, loaders, checks, vistas y consultas demo.

### Notebooks principales del módulo IA inicial

```text
04_dish_detection_dataset_exploration.ipynb
05_dish_ner_dataset_builder.ipynb
06_dish_ner_transformer_training.ipynb
07_dish_ner_inference_and_mentions.ipynb
08_dish_normalization_and_catalog_builder.ipynb
09_dish_mention_sentiment_hybrid_v1.ipynb
10_dish_signal_aggregation.ipynb
11_hidden_gems_ranking_v1.ipynb
```

### DDL IA

```powershell
# Ejecutar desde cliente SQL / pgAdmin / DBeaver
# db/ddl/07_ai_module.sql
# db/ddl/08_ai_views.sql
```

### Carga del catálogo IA

```powershell
python -m scripts.load_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv `
  --summary-path data/artifacts/ai/normalization/dish_normalization_summary_v2.json
```

Check:

```powershell
python -m scripts.check_ai_dish_catalog `
  --catalog-path data/artifacts/ai/normalization/dish_catalog_seed_v2.csv `
  --aliases-path data/artifacts/ai/normalization/dish_aliases_seed_v2.csv
```

### Check de preparación downstream

```powershell
python -m scripts.check_ai_downstream_import_readiness `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/checks/check_ai_downstream_import_readiness_report.json
```

### Carga de menciones y sentimiento

```powershell
python -m scripts.load_ai_mentions_and_sentiment `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --report-path data/artifacts/ai/sentiment/load_ai_mentions_and_sentiment_report.json
```

### Carga de señales y ranking

```powershell
python -m scripts.load_ai_signals_and_ranking `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/ranking/load_ai_signals_and_ranking_report.json
```

### Check final de ranking cargado

```powershell
python -m scripts.check_ai_ranking_loaded `
  --report-path data/artifacts/ai/ranking/check_ai_ranking_loaded_report.json
```

### Demo de consulta

Top general:

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

Detalle con menciones justificativas:

```powershell
python -m scripts.query_ai_ranking_demo `
  --place-name "Sushi Ushi" `
  --dish-name "sushi" `
  --include-mentions `
  --mentions-top-n 25
```

Exportación de resultados:

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 50 `
  --export-dir data/artifacts/ai/query_demo
```

---

## 15. Fase Sevilla IA v2

La fase Sevilla IA v2 es la fase final de la entrega académica. Su objetivo fue mejorar el ranking Sevilla piloto mediante modelos entrenados y una capa de inferencia local.

### Modelos entrenados

| Modelo | Tarea | Enfoque | Resultado principal |
|---|---|---|---|
| Modelo 1 | Detección de menciones de platos | NER BIO con BETO | Detecta menciones de platos en reseñas |
| Modelo 3 | Normalización / entity linking | Cross-encoder reranker con BETO | Enlaza menciones a `dish_id` canónico |
| Modelo 2 | Sentimiento por mención / ABSA | Clasificación negative / neutral / positive | Estima sentimiento hacia cada plato concreto |

> La numeración Modelo 2 / Modelo 3 se conserva porque fue la planificación original de la fase, aunque en el flujo técnico la normalización se aplica antes del sentimiento ABSA.

### Flujo de scripts IA v2

```powershell
# 1. Combinar capa híbrida previa con NER entrenado
python -m scripts.build_sevilla_hybrid_ner_mention_candidates_v2 `
  --ner-path data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/sevilla_dish_mentions_ner_model_v1_2.jsonl `
  --output-dir data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2 `
  --strict
```

```powershell
# 2. Normalización / entity linking con reranker
python -m scripts.run_sevilla_dish_normalization_reranker_v1 `
  --input-path data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl `
  --model-dir models/sevilla_dish_normalization_reranker_beto_v1 `
  --output-dir data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1 `
  --strict
```

```powershell
# 3. Sentimiento ABSA por mención
python -m scripts.run_sevilla_mention_sentiment_absa_v1 `
  --input-path data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/sevilla_dish_mentions_normalized_reranker_v1.jsonl `
  --model-dir models/sevilla_mention_sentiment_absa_beto_v1 `
  --output-dir data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1 `
  --strict
```

```powershell
# 4. Agregación de señales por local y plato
python -m scripts.build_sevilla_place_dish_signals_v2 `
  --input-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --output-dir data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2 `
  --strict
```

```powershell
# 5. Ranking Hidden Gems Sevilla v2
python -m scripts.build_sevilla_hidden_gems_ranking_v2 `
  --input-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --output-dir data/artifacts/ai/sevilla/model_inference/ranking_v2 `
  --strict
```

```powershell
# 6. Comparación ranking v1 vs v2
python -m scripts.compare_sevilla_ranking_v1_vs_v2 `
  --v1-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --v2-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --output-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --strict
```

```powershell
# 7. Export para dashboard v2
python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --include-mentions `
  --examples-per-candidate 5 `
  --include-full-review-text `
  --strict
```

### Resultados finales v2

```text
ranking_rows: 2.335
selected_rows: 268
selected_places: 198
selected_dishes: 40
selected_neighborhoods: 67
selected_districts: 11
mentions_selected: 651
reviews_selected: 627
```

Distribución por tier:

```text
top_hidden_gem: 16
strong_hidden_gem: 77
promising_hidden_gem: 139
exploratory_hidden_gem: 36
```

Comparación con v1:

```text
v1_selected_unique: 150
v2_selected_unique: 268
matched_candidates: 119
v1_coverage_in_v2: 0.793333
jaccard_overlap: 0.397993
selected_places_delta_v2_minus_v1: +76
selected_neighborhoods_delta_v2_minus_v1: +12
```

---

## 16. Dashboards

El proyecto incluye dashboards Streamlit para consultar los resultados de forma visual.

### Dashboard Sevilla v1

```powershell
streamlit run dashboard/streamlit_app.py
```

Dashboard inicial basado en el ranking Sevilla piloto.

### Dashboard Yelp

```powershell
streamlit run dashboard/streamlit_yelp_app.py
```

Dashboard para explorar el prototipo Yelp y los resultados del corpus externo.

### Dashboard Sevilla IA v2

```powershell
streamlit run dashboard/streamlit_sevilla_v2_app.py
```

Dashboard final de la entrega, basado en:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Incluye:

- resumen ejecutivo;
- KPIs principales;
- ranking IA v2;
- filtros por distrito, barrio, plato, local, tier, evidencia y calidad;
- análisis territorial;
- mapa con coordenadas reales cuando están disponibles;
- análisis de platos y locales;
- evidencia y calidad;
- comparación v1 vs v2;
- explicación de la puntuación `hidden_gem_score_v2`;
- detalle de menciones y reseñas;
- contrato de datos y artefactos.

---

## 17. Capas y artefactos principales

### Raw

```text
data/raw/
```

Contiene respuestas y assets fuente trazables.

### Staging

```text
data/staging/
```

Contiene datos transformados, candidatos, deduplicación y subsets intermedios.

Ejemplos:

```text
data/staging/google_places/
data/staging/google_places_reviews/
data/staging/yelp_open_dataset/
```

### External

```text
data/external/
```

Contiene datasets locales grandes no versionados, como Yelp Open Dataset.

### Artifacts

```text
data/artifacts/
```

Contiene perfiles, checks, summaries, logs y artefactos IA.

### AI artifacts

```text
data/artifacts/ai/
```

Contiene salidas del módulo IA:

```text
normalization/
sentiment/
aggregation/
ranking/
checks/
query_demo/
yelp/
sevilla/
```

### Sevilla dashboard v2

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Archivos principales:

```text
dashboard_metadata.json
kpi_summary.json
ranking_detail.csv
selected_candidates.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
district_summary.csv
neighborhood_summary.csv
dish_summary.csv
place_summary.csv
tier_summary.csv
evidence_summary.csv
quality_summary.csv
filter_options.json
data_contract.json
mention_examples.csv
place_coordinates.csv
comparison/
```

### NLP corpus

```text
data/artifacts/nlp_corpus/
```

Contiene corpus preparados para tareas de NLP.

### Modelos locales

```text
models/
```

Contiene modelos descargados de Kaggle o entrenados localmente. Esta carpeta debe estar ignorada por Git.

---

## 18. Reglas importantes de Git

No deben subirse al repositorio:

```text
.env
.venv/
models/
data/external/yelp_open_dataset/
data/raw/
data/staging/**/*.jsonl
data/staging/**/*.txt
data/artifacts/nlp_corpus/*.jsonl
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
```

Sí se pueden versionar:

```text
scripts/
src/
docs/
db/
dashboard/
README.md
requirements.txt
.env.example
summaries pequeños si se decide conservarlos
```

---

## 19. Principios de diseño

El desarrollo del pipeline sigue estas reglas:

- trazabilidad primero;
- no perder raw;
- transformar antes de consolidar;
- no fusionar fuentes directamente;
- construir `place` como entidad canónica interna;
- mantener separación clara entre representación fuente y entidad negocio;
- usar `place_id` como eje interno, no `business_id` externo;
- hacer verticales completas, no piezas aisladas;
- validar cada paso con checks reproducibles;
- escalar por tandas pequeñas;
- separar datos operativos de corpus IA/NLP;
- no guardar reviews huérfanas;
- no insertar menciones IA sin `review_id` canónico;
- no insertar señales IA sin `place_id` y `dish_id` resueltos;
- versionar modelos, reglas y ejecuciones IA;
- mantener Yelp como prototipo IA, no como producción Sevilla;
- mantener el ranking Sevilla separado del ranking `yelp_prototype`;
- marcar los rankings asistidos por modelos como experimentales mientras no haya validación humana suficiente.

---

## 20. Documentación detallada

La documentación extensa del proyecto está organizada en [`docs/`](docs/).

### Índice de carpetas principales

| Carpeta | Contenido |
|---|---|
| [`docs/01_context/`](docs/01_context/) | Contexto, problema, objetivos, alcance y límites. |
| [`docs/02_architecture/`](docs/02_architecture/) | Arquitectura del pipeline, flujo general, estructura del proyecto y configuración. |
| [`docs/03_data_model/`](docs/03_data_model/) | Entidades, relaciones, trazabilidad, calidad y decisiones de schema. |
| [`docs/04_sources/`](docs/04_sources/) | Fuentes de datos: Sevilla Geo, Overpass, Google Places, Yelp. |
| [`docs/05_verticals/`](docs/05_verticals/) | Verticales operativas y flujo específico por fuente. |
| [`docs/08_operations/`](docs/08_operations/) | Operaciones, ejecución de scripts, checks, logs, errores y dashboards. |
| [`docs/10_ai_module/`](docs/10_ai_module/) | Módulo IA inicial: detección, normalización, sentimiento, ranking v1. |
| [`docs/11_ai_integration/`](docs/11_ai_integration/) | Integración de la capa IA en PostgreSQL: schema, loaders, checks y vistas. |
| [`docs/12_sevilla_ai_pilot/`](docs/12_sevilla_ai_pilot/) | Piloto Sevilla previo a la fase v2. |
| [`docs/13_sevilla_ai_v2/`](docs/13_sevilla_ai_v2/) | Fase final IA v2: modelos entrenados, inferencia, ranking, comparación y dashboard. |

### Documentación de la fase Sevilla IA v2

| Documento | Contenido |
|---|---|
| [`00_index.md`](docs/13_sevilla_ai_v2/00_index.md) | Índice de la fase IA v2. |
| [`01_phase_overview.md`](docs/13_sevilla_ai_v2/01_phase_overview.md) | Resumen ejecutivo de la fase IA v2. |
| [`02_v2_pipeline_overview.md`](docs/13_sevilla_ai_v2/02_v2_pipeline_overview.md) | Flujo técnico completo de IA v2. |
| [`03_datasets_and_annotation.md`](docs/13_sevilla_ai_v2/03_datasets_and_annotation.md) | Datasets, anotación, weak labels y formatos. |
| [`04_model_1_dish_ner.md`](docs/13_sevilla_ai_v2/04_model_1_dish_ner.md) | Modelo 1: NER de platos. |
| [`05_model_3_dish_normalization_reranker.md`](docs/13_sevilla_ai_v2/05_model_3_dish_normalization_reranker.md) | Modelo 3: normalización/entity linking con reranker. |
| [`06_model_2_mention_sentiment_absa.md`](docs/13_sevilla_ai_v2/06_model_2_mention_sentiment_absa.md) | Modelo 2: sentimiento por mención / ABSA. |
| [`07_hybrid_ner_candidates_v2.md`](docs/13_sevilla_ai_v2/07_hybrid_ner_candidates_v2.md) | Capa Hybrid + NER candidates v2. |
| [`08_normalization_inference_v2.md`](docs/13_sevilla_ai_v2/08_normalization_inference_v2.md) | Inferencia de normalización v2. |
| [`09_sentiment_inference_v2.md`](docs/13_sevilla_ai_v2/09_sentiment_inference_v2.md) | Inferencia ABSA v2. |
| [`10_place_dish_signals_v2.md`](docs/13_sevilla_ai_v2/10_place_dish_signals_v2.md) | Señales agregadas por local y plato. |
| [`11_hidden_gems_ranking_v2.md`](docs/13_sevilla_ai_v2/11_hidden_gems_ranking_v2.md) | Ranking Hidden Gems Sevilla v2. |
| [`12_ranking_v1_vs_v2_comparison.md`](docs/13_sevilla_ai_v2/12_ranking_v1_vs_v2_comparison.md) | Comparación ranking v1 vs v2. |
| [`13_dashboard_v2.md`](docs/13_sevilla_ai_v2/13_dashboard_v2.md) | Dashboard Sevilla IA v2. |
| [`14_artifacts_and_data_contracts.md`](docs/13_sevilla_ai_v2/14_artifacts_and_data_contracts.md) | Artefactos, contratos de datos y granularidad. |
| [`15_limitations_and_risks.md`](docs/13_sevilla_ai_v2/15_limitations_and_risks.md) | Limitaciones, riesgos y decisiones prudentes. |
| [`16_next_steps.md`](docs/13_sevilla_ai_v2/16_next_steps.md) | Próximos pasos si el proyecto avanza a producción. |

### Archivo auxiliar

- [`docs/barrios_google_place.txt`](docs/barrios_google_place.txt): listado auxiliar de barrios usado durante la preparación de queries Google Places.

---

## 21. Roadmap

### Ya implementado

- base PostgreSQL/PostGIS;
- modelo relacional principal;
- vertical Sevilla Geo;
- vertical OSM / Overpass;
- vertical Google Places Text Search;
- batch de Google Places por barrios/distritos;
- vertical Google Places Reviews;
- batch y check global de reviews;
- primera tanda real de reviews importadas;
- perfilado y extracción de Yelp Open Dataset;
- subset de negocios gastronómicos de Yelp;
- subset de reviews gastronómicas de Yelp;
- corpus IA/NLP Yelp;
- entrenamiento y evaluación inicial de Dish NER;
- normalización de platos;
- sentimiento híbrido por mención;
- agregación de señales;
- ranking Hidden Gems v1;
- schema IA en PostgreSQL;
- carga de catálogo, menciones, sentimiento, señales y ranking;
- vistas SQL de consulta IA;
- script demo de consulta IA;
- dashboard Sevilla v1;
- dashboard Yelp;
- export de datasets de anotación IA Sevilla;
- entrenamiento de NER Sevilla v1.2;
- entrenamiento de normalización / entity linking reranker;
- entrenamiento de sentimiento por mención / ABSA;
- inferencia local de modelos IA v2;
- señales local-plato v2;
- ranking Hidden Gems Sevilla v2;
- comparación ranking v1 vs v2;
- export dashboard v2;
- dashboard Sevilla IA v2;
- documentación completa de la fase IA v2.

### Cerrado para entrega académica

La entrega del Proyecto Integrado se considera cerrada en este punto:

```text
pipeline de datos + IA + ranking + dashboard + documentación
```

### Posibles próximos pasos si el proyecto continúa

- validación humana del top ranking;
- revisión de candidatos low confidence / no candidate;
- mejora del catálogo de platos y aliases;
- penalización o tratamiento especial de platos demasiado genéricos;
- descarga automática de modelos desde Drive u otro storage externo;
- automatización completa de la cadena IA v2;
- integración de ranking v2 en PostgreSQL como capa persistida;
- API con FastAPI;
- despliegue de dashboard;
- frontend público;
- monitorización de costes Google Places;
- evaluación periódica de calidad y drift de modelos.

---

## 22. Estado final de entrega

El proyecto queda en el siguiente estado:

```text
Datos operativos Sevilla / Google / OSM
→ base canónica place/review/geografía

Yelp prototype corpus
→ módulo IA experimental inicial
→ resultados cargados en PostgreSQL
→ ranking yelp_prototype consultable

Sevilla IA v2
→ modelos entrenados
→ inferencia local
→ señales place-dish
→ ranking Hidden Gems Sevilla v2
→ comparación v1/v2
→ dashboard final
```

El ranking IA v2 no se marca como producción:

```text
is_production_ready = false
```

Esto es una decisión deliberada. El sistema demuestra el funcionamiento técnico completo, pero antes de considerarlo productivo harían falta validación humana, más datos, control de calidad continuo y automatización operativa.

Resumen final:

```text
Estado del PI: cerrado para entrega académica.
Estado técnico: MVP avanzado / prototipo analítico funcional.
Estado producción: no producción, pendiente de validación humana y escalado.
```


Realizado por Iván Arteaga Cordero
