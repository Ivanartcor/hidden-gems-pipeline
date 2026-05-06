# Hidden Gems Pipeline

Pipeline inteligente de adquisición, validación, normalización y enriquecimiento de datos gastronómicos para **Hidden Gems**, un proyecto orientado a descubrir locales y, en fases posteriores, platos destacados por barrio a partir de múltiples fuentes de datos.

---

## 1. ¿Qué es este proyecto?

**Hidden Gems Pipeline** es el núcleo de procesamiento de datos del proyecto Hidden Gems.

El objetivo de este repositorio no es construir directamente una aplicación final de cara al usuario, sino desarrollar una infraestructura de datos central, reutilizable y trazable que permita:

- adquirir datos desde distintas fuentes;
- conservar una capa **raw** auditable;
- validar y limpiar los datos de entrada;
- normalizar información heterogénea en un modelo común;
- enriquecer geográficamente los registros;
- consolidar locales gastronómicos en una entidad canónica `place`;
- asociar referencias externas mediante `place_source_ref`;
- enriquecer locales con reseñas reales cuando sea posible;
- preparar datasets y corpus para futuras fases de NLP, extracción de platos y ranking por barrio.

En otras palabras, este repositorio implementa la **infraestructura de datos y automatización inteligente** sobre la que se apoyará el resto del sistema Hidden Gems.

---

## 2. Idea general del proyecto

El enfoque actual del proyecto es:

> **Pipeline inteligente de adquisición y procesamiento de datos gastronómicos para Hidden Gems**

La idea no es desarrollar toda la aplicación Hidden Gems en esta fase, sino construir el módulo central de datos que permita:

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
→ corpus NLP / análisis posterior
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
- los datos no suelen estar listos directamente para análisis, NLP o ranking.

Este pipeline resuelve ese problema creando un flujo reproducible para:

- capturar datos de fuentes abiertas y externas;
- trazar cada ejecución y cada asset descargado;
- transformar datos heterogéneos a un formato común;
- asignar localización geográfica útil dentro de Sevilla;
- construir entidades canónicas (`place`) separadas de sus representaciones por fuente (`place_source_ref`);
- enriquecer locales con reviews operativas cuando están disponibles;
- generar datasets preparados para fases futuras de NLP.

---

## 4. Fuentes de datos del proyecto

Las fuentes definidas para el pipeline son:

| Fuente | Rol dentro del proyecto | Estado |
|---|---|---|
| Sevilla Geo | Barrios y distritos oficiales de Sevilla | Implementada |
| OSM / Overpass | Fuente abierta de POIs gastronómicos | Implementada |
| Google Places Text Search | Fuente dinámica para descubrimiento/enriquecimiento de locales | Implementada |
| Google Places Reviews | Reviews reales asociadas a locales ya consolidados | Implementada |
| Yelp Open Dataset | Corpus externo para entrenamiento NLP gastronómico | En desarrollo |

---

## 5. Principio clave sobre Google y Yelp

El proyecto diferencia claramente entre datos **operativos** y datos de **entrenamiento NLP**.

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

Las reviews de Google solo se guardan si el local ya existe en el modelo canónico y tiene una referencia válida en `place_source_ref`.

### Yelp Open Dataset

Yelp se usa como corpus externo para NLP:

```text
Yelp business + Yelp review
→ subset gastronómico
→ corpus NLP
```

Yelp no se importa inicialmente como `place` ni como `review` operativo, porque no está vinculado a locales reales de Sevilla. Su objetivo es servir como base amplia para entrenamiento y experimentación en NLP.

---

## 6. Arquitectura general

El proyecto sigue una arquitectura por capas, modular y reproducible.

### Capas principales

- **raw**: conservación trazable de datos fuente sin transformar;
- **staging**: transformación intermedia, validación y artefactos derivados;
- **reference**: datos de referencia estructurales, como geografía oficial;
- **canonical / business**: entidades centrales del dominio, como `place`;
- **artifacts / ops**: logs, perfiles, resúmenes y resultados de comprobación;
- **nlp_corpus**: datasets preparados para futuras tareas de procesamiento de lenguaje natural.

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
→ comprobaciones
→ corpus / análisis posterior
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
- Jupyter

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
- corpus externo para NLP.

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

### NLP / corpus externo

En la fase Yelp se trabaja inicialmente con ficheros JSONL de corpus, no con importación masiva directa a tablas operativas.

---

## 9. Estado actual del proyecto

El proyecto ya cuenta con una base estructural montada en PostgreSQL/PostGIS y varias verticales funcionales.

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

### Vertical en desarrollo

#### Yelp Open Dataset

- dataset `.tar` descargado localmente;
- perfilado del `.tar`;
- extracción controlada de `business.json` y `review.json`;
- perfilado JSON Lines;
- subset de negocios gastronómicos;
- subset inicial de reviews gastronómicas;
- construcción de corpus NLP en curso.

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
│   └───09_roadmap/
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

Yelp se usa como corpus externo para NLP, no como fuente operativa de locales de Sevilla.

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

### Corpus NLP Yelp

```powershell
python -m scripts.build_yelp_nlp_corpus `
  --corpus-name yelp_food_reviews_corpus_sample_100k_lines `
  --min-text-length 80 `
  --max-text-length 5000 `
  --save-artifact
```

---

## 14. Capas y artefactos principales

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

Contiene perfiles, checks, summaries y logs.

### NLP corpus

```text
data/artifacts/nlp_corpus/
```

Contiene corpus preparados para futuras fases de NLP.

---

## 15. Reglas importantes de Git

No deben subirse al repositorio:

```text
data/external/yelp_open_dataset/
data/raw/
data/staging/**/*.jsonl
data/staging/**/*.txt
data/artifacts/nlp_corpus/*.jsonl
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

## 16. Principios de diseño seguidos

El desarrollo del pipeline sigue estas reglas:

- trazabilidad primero;
- no perder raw;
- transformar antes de consolidar;
- no fusionar fuentes directamente;
- construir `place` como entidad canónica interna;
- mantener separación clara entre representación fuente y entidad negocio;
- hacer verticales completas, no piezas aisladas;
- validar cada paso con checks reproducibles;
- escalar por tandas pequeñas;
- separar datos operativos de corpus NLP;
- no guardar reviews huérfanas;
- no usar Yelp como fuente operativa de Sevilla en esta fase.

---

## 17. Documentación detallada

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

---

## 18. Roadmap resumido

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
- subset inicial de reviews gastronómicas de Yelp.

### En curso

- construcción de corpus NLP Yelp;
- checks específicos del corpus;
- documentación de la vertical Yelp.

### Próximos pasos

- cerrar vertical Yelp Open Dataset;
- diseñar módulo NLP inicial;
- extracción básica de platos;
- sentimiento general de review;
- sentimiento asociado a menciones de platos;
- diseño de `dish_mention`, `place_dish_score` y ranking por barrio;
- exposición mínima con FastAPI.

---

## 19. Estado del proyecto

Este repositorio se encuentra en una fase activa de desarrollo, con una base de datos ya montada, varias verticales cerradas y una vertical Yelp en construcción para preparar el futuro módulo NLP.

El objetivo no es solo obtener datos, sino construir un pipeline sólido, trazable y extensible que sirva como base real para descubrir, analizar y rankear platos destacados por barrio en fases posteriores de Hidden Gems.
