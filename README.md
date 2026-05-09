# Hidden Gems Pipeline

Pipeline inteligente de adquisición, validación, normalización, enriquecimiento e integración IA de datos gastronómicos para **Hidden Gems**, un proyecto orientado a descubrir locales y platos destacados, con objetivo final de ranking por barrio.

---

## 1. ¿Qué es este proyecto?

**Hidden Gems Pipeline** es el núcleo de procesamiento de datos del proyecto Hidden Gems.

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
- generar rankings explicables de candidatos Hidden Gems.

En otras palabras, este repositorio implementa la **infraestructura de datos, automatización e integración IA** sobre la que se apoyará el resto del sistema Hidden Gems.

---

## 2. Idea general del proyecto

El enfoque actual del proyecto es:

> **Pipeline inteligente de adquisición y procesamiento de datos gastronómicos para Hidden Gems**

La idea no es desarrollar toda la aplicación Hidden Gems en esta fase, sino construir el módulo central de datos e IA que permita pasar de fuentes externas heterogéneas a resultados consultables y trazables.

Flujo general actual:

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
→ corpus IA
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems prototipo
→ vistas SQL / consultas demo
```

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
- las reseñas hablan de locales, pero Hidden Gems necesita extraer información más fina: platos concretos, menciones, sentimiento y señales agregadas.

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

## 4. Fuentes de datos del proyecto

Las fuentes definidas para el pipeline son:

| Fuente | Rol dentro del proyecto | Estado |
|---|---|---|
| Sevilla Geo | Barrios y distritos oficiales de Sevilla | Implementada |
| OSM / Overpass | Fuente abierta de POIs gastronómicos | Implementada |
| Google Places Text Search | Fuente dinámica para descubrimiento/enriquecimiento de locales | Implementada |
| Google Places Reviews | Reviews reales asociadas a locales ya consolidados | Implementada |
| Yelp Open Dataset | Corpus externo para entrenamiento, validación e integración prototipo IA | Implementada como corpus/prototipo IA |

---

## 5. Principio clave sobre Google y Yelp

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
- **artifacts / ops**: logs, perfiles, resúmenes y resultados de comprobación;
- **views / query layer**: vistas SQL y scripts de consulta para explotar resultados.

### Flujo conceptual

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
→ vistas / demo de consulta
```

---

## 7. Stack tecnológico

### Lenguaje y librerías

- Python
- pandas
- requests / httpx
- SQLAlchemy
- psycopg2-binary
- pydantic
- pydantic-settings
- spaCy
- RapidFuzz
- pytest
- logging
- Jupyter / notebooks

### IA / NLP

- Transformers para detección de platos mediante NER
- Dataset BIO para entrenamiento NER
- Normalización híbrida basada en reglas, aliases y limpieza textual
- Sentimiento híbrido por mención
- Agregación de señales
- Ranking explicable basado en scoring

### Persistencia y geodatos

- PostgreSQL
- PostGIS

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

El proyecto ya cuenta con una base estructural montada en PostgreSQL/PostGIS, varias verticales funcionales y una primera integración IA completa sobre corpus Yelp.

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

### Módulo IA integrado

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

Estado final de carga IA:

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
├───data/
│   ├───artifacts/
│   │   ├───ai/
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
│   ├───06_normalization/
│   ├───07_quality/
│   ├───08_operations/
│   ├───09_roadmap/
│   ├───10_ai_module/
│   └───11_ai_integration/
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

### Notebooks principales del módulo IA

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

## 15. Capas y artefactos principales

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
```

### NLP corpus

```text
data/artifacts/nlp_corpus/
```

Contiene corpus preparados para tareas de NLP.

---

## 16. Reglas importantes de Git

No deben subirse al repositorio:

```text
data/external/yelp_open_dataset/
data/raw/
data/staging/**/*.jsonl
data/staging/**/*.txt
data/artifacts/nlp_corpus/*.jsonl
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
.env
```

Sí se pueden versionar:

```text
scripts/
src/
docs/
db/
README.md
requirements.txt
.env.example
summaries pequeños si se decide conservarlos
```

---

## 17. Principios de diseño seguidos

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
- mantener el ranking Sevilla futuro separado del ranking `yelp_prototype`.

---

## 18. Documentación detallada

La documentación extensa del proyecto está organizada en `docs/`.

### Contexto

```text
docs/01_context/
```

Incluye visión general, problema, objetivos, alcance y límites.

### Arquitectura

```text
docs/02_architecture/
```

Incluye arquitectura del pipeline, flujo general, estructura del proyecto y configuración.

### Modelo de datos

```text
docs/03_data_model/
```

Incluye entidades, relaciones, trazabilidad, calidad y decisiones de schema.

### Fuentes

```text
docs/04_sources/
```

Incluye descripción y rol de cada fuente:

- Sevilla Geo;
- OSM / Overpass;
- Google Places;
- Yelp Open Dataset.

### Verticales

```text
docs/05_verticals/
```

Incluye verticales operativas:

- Sevilla Geo;
- Overpass;
- Google Places;
- Google Places Reviews;
- Yelp Open Dataset.

### Módulo IA

```text
docs/10_ai_module/
```

Documenta la fase experimental IA:

- detección de platos;
- normalización;
- sentimiento por mención;
- agregación;
- ranking Hidden Gems v1;
- resultados y limitaciones.

### Integración IA

```text
docs/11_ai_integration/
```

Documenta la integración real de la capa IA en PostgreSQL:

- schema IA;
- loaders;
- checks;
- vistas SQL;
- estado actual;
- próximos pasos.

---

## 19. Roadmap resumido

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
- entrenamiento y evaluación de Dish NER;
- normalización de platos;
- sentimiento híbrido por mención;
- agregación de señales;
- ranking Hidden Gems v1;
- schema IA en PostgreSQL;
- carga de catálogo, menciones, sentimiento, señales y ranking;
- vistas SQL de consulta IA;
- script demo de consulta IA.

### En curso / siguiente fase

- actualización de documentación general del repositorio;
- preparación de flujo IA desde reviews reales exportadas desde PostgreSQL;
- piloto con reviews de Google Places Sevilla;
- evaluación de idioma, volumen y calidad textual;
- diseño de adaptación del módulo IA a español / multilingüe.

### Próximos pasos

- crear `export_reviews_for_ai.py`;
- crear checks de exportación IA desde `review`;
- probar la cadena IA sobre reviews reales de Google Places;
- incorporar `neighborhood_id` y `district_id` al ranking productivo;
- generar ranking `sevilla_neighborhood`;
- marcar candidatos Sevilla como `is_production_ready = true` solo cuando estén validados;
- exponer resultados mínimos con FastAPI o dashboard.

---

## 20. Estado del proyecto

Este repositorio se encuentra en una fase activa de desarrollo, con una base de datos ya montada, varias verticales cerradas y una primera capa IA integrada de extremo a extremo.

El estado actual puede resumirse así:

```text
Datos operativos Sevilla / Google / OSM
→ base canónica place/review/geografía

Yelp prototype corpus
→ módulo IA experimental
→ resultados cargados en PostgreSQL
→ ranking yelp_prototype consultable
```

El ranking IA actual no es todavía el ranking final de Sevilla por barrios. Es un prototipo validado sobre Yelp que demuestra que la arquitectura funciona:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
→ vistas SQL
→ consultas demo
```

El siguiente objetivo del proyecto es adaptar esta cadena a reviews reales de Sevilla y producir rankings por barrio con:

```text
ranking_scope = sevilla_neighborhood
is_production_ready = true
neighborhood_id != null
```
