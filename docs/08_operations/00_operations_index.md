# 00. Operations Index

## 1. Propósito del bloque `08_operations`

Este bloque documenta la **operación práctica** del proyecto **Hidden Gems Pipeline**.

El objetivo no es volver a explicar la arquitectura, el modelo de datos o el diseño de cada vertical, sino dejar una guía clara para ejecutar, validar, mantener y depurar el sistema en un entorno real de desarrollo.

En otras palabras:

```text
README.md                 → entrada general al proyecto
docs/01_context/          → contexto, problema y alcance
docs/02_architecture/     → diseño general del sistema
docs/03_data_model/       → modelo de datos y esquema SQL
docs/04_sources/          → fuentes de datos
docs/05_verticals/        → detalle técnico por vertical
docs/10_ai_module/        → desarrollo experimental IA
docs/11_ai_integration/   → integración IA en PostgreSQL
docs/12_sevilla_ai_pilot/ → piloto IA Sevilla end-to-end

docs/08_operations/       → cómo ejecutar y mantener el sistema
```

Este bloque debe servir como manual de trabajo para una persona que ya tiene el repositorio y necesita saber:

- cómo preparar el entorno;
- qué scripts ejecutar;
- en qué orden ejecutarlos;
- cómo validar cada fase;
- qué artefactos se generan;
- qué errores son habituales;
- qué datos no deben subirse a Git;
- cómo consultar el estado final del piloto.

---

## 2. Estado operativo actual del proyecto

A fecha de esta documentación, el proyecto cuenta con varias piezas operativas ya implementadas y validadas:

```text
Sevilla Geo
→ carga de barrios y distritos oficiales
→ validación geográfica

OSM / Overpass
→ ingesta de POIs gastronómicos
→ transformación
→ deduplicación
→ importación canónica
→ asignación de barrio

Google Places
→ Text Search controlado
→ batch por barrios/distritos
→ importación canónica de locales
→ check global de batch

Google Places Reviews
→ Place Details sobre locales ya consolidados
→ reviews reales en hidden_gems.review
→ batch de reviews
→ check global de reviews

Yelp Open Dataset
→ corpus externo IA/NLP
→ prototipo IA validado
→ ranking yelp_prototype cargado en PostgreSQL

Piloto IA Sevilla
→ export de reviews reales de Google
→ notebooks 12–17
→ ranking sevilla_pilot
→ carga en PostgreSQL
→ checks correctos
→ demo de consulta
```

El estado del piloto Sevilla queda resumido como:

```text
Google Places Sevilla: 800+ locales
Google Places Reviews: 4.000+ reviews
Menciones IA Sevilla: 2.979
Señales local-plato: 2.212
Candidatos rankeados: 256
Candidatos seleccionados: 150
ready_for_sevilla_pilot_queries = true
is_production_ready = false
```

El ranking `sevilla_pilot` es un piloto local real y trazable, pero todavía no se marca como producción.

---

## 3. Documentos de este bloque

La carpeta `docs/08_operations/` se organiza como un conjunto de runbooks.

| Archivo | Propósito |
|---|---|
| `00_operations_index.md` | Índice operativo general y mapa de documentos. |
| `01_environment_and_database_runbook.md` | Preparación del entorno local, base de datos, DDL y checks iniciales. |
| `02_data_ingestion_runbook.md` | Ejecución práctica de las verticales de ingesta y carga de datos. |
| `03_google_places_operations.md` | Operación segura de Google Places y Google Places Reviews. |
| `04_ai_pipeline_operations.md` | Operación de la capa IA: Yelp prototype y Sevilla pilot. |
| `05_checks_and_validation_runbook.md` | Catálogo de checks y cómo interpretar sus resultados. |
| `06_artifacts_logs_and_data_management.md` | Gestión de raw, staging, artifacts, logs y datos que no deben versionarse. |
| `07_troubleshooting.md` | Errores frecuentes y soluciones aplicadas durante el proyecto. |
| `08_git_and_delivery_workflow.md` | Flujo recomendado de Git, commits y preparación de entregas. |

Más adelante, cuando exista dashboard, se añadirá:

```text
09_dashboard_operations.md
```

---

## 4. Cómo usar esta documentación

### Si se parte de cero

Consultar en este orden:

```text
01_environment_and_database_runbook.md
02_data_ingestion_runbook.md
05_checks_and_validation_runbook.md
```

### Si se va a ejecutar Google Places

Consultar:

```text
03_google_places_operations.md
02_data_ingestion_runbook.md
05_checks_and_validation_runbook.md
```

### Si se va a trabajar con IA

Consultar:

```text
04_ai_pipeline_operations.md
11_ai_integration/
12_sevilla_ai_pilot/
05_checks_and_validation_runbook.md
```

### Si algo falla

Consultar:

```text
07_troubleshooting.md
```

### Si se va a subir al repositorio

Consultar:

```text
06_artifacts_logs_and_data_management.md
08_git_and_delivery_workflow.md
```

---

## 5. Principio operativo general

La regla principal para operar Hidden Gems es:

```text
No se ejecuta una fase grande sin haber validado antes la fase anterior.
```

El patrón habitual es:

```text
1. Ejecutar en modo dry-run cuando exista.
2. Ejecutar una muestra pequeña.
3. Revisar logs y artifacts.
4. Ejecutar el check correspondiente.
5. Validar que no hay errors ni warnings críticos.
6. Escalar progresivamente.
7. Guardar report JSON si aplica.
```

Esto aplica especialmente a:

- Google Places, por coste y cuota;
- Google Places Reviews, por llamadas a Place Details;
- cargas IA, por dependencia de mapeos `review`, `place` y `dish`;
- checks pesados sobre PostgreSQL;
- generación de artefactos grandes.

---

## 6. Convención de comandos en Windows PowerShell

El entorno habitual del proyecto es Windows con PowerShell.

Para comandos multilínea se utiliza el backtick:

```powershell
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Regla importante:

```text
El backtick debe ser el último carácter de la línea.
No debe haber espacios después del backtick.
```

Si un comando falla de forma extraña en PowerShell, revisar primero los backticks, comillas y saltos de línea.

---

## 7. Tipos de scripts del repositorio

Los scripts se pueden agrupar por función operativa:

### Preparación y base

```text
check_db_connection.py
check_schema.py
seed_source_systems.py
```

### Sevilla Geo

```text
run_sevilla_geo_ingestion.py
load_sevilla_geo_reference.py
check_sevilla_geo_load.py
```

### OSM / Overpass

```text
run_overpass_ingestion.py
profile_overpass_raw.py
transform_overpass_candidates.py
check_overpass_staging.py
deduplicate_overpass_candidates.py
import_overpass_places.py
check_overpass_import.py
load_overpass_pipeline.py
```

### Google Places

```text
run_google_places_text_search.py
check_google_places_raw.py
transform_google_places_candidates.py
check_google_places_staging.py
deduplicate_google_places_candidates.py
check_google_places_deduplication.py
import_google_places_places.py
check_google_places_import.py
load_google_places_pipeline.py
run_google_places_neighborhood_batch.py
check_google_places_batch.py
run_google_places_place_details.py
```

### Google Places Reviews

```text
transform_google_places_reviews.py
check_google_places_reviews_staging.py
import_google_places_reviews.py
check_google_places_reviews_import.py
load_google_places_reviews_pipeline.py
run_google_places_reviews_batch.py
check_google_places_reviews_batch.py
```

### Yelp Open Dataset

```text
profile_yelp_tar.py
extract_yelp_selected_files.py
profile_yelp_jsonl_files.py
build_yelp_food_business_subset.py
build_yelp_food_review_subset.py
build_yelp_nlp_corpus.py
check_yelp_nlp_corpus.py
```

### Integración IA general / Yelp prototype

```text
load_ai_dish_catalog.py
check_ai_dish_catalog.py
load_yelp_ai_core_reviews.py
check_ai_downstream_import_readiness.py
load_ai_mentions_and_sentiment.py
load_ai_signals_and_ranking.py
check_ai_ranking_loaded.py
query_ai_ranking_demo.py
```

### Piloto IA Sevilla

Estos scripts forman parte de la fase posterior del piloto Sevilla y pueden no aparecer en ramas antiguas si no se han subido todavía:

```text
export_reviews_for_ai.py
check_ai_review_export.py
load_sevilla_ai_pilot_outputs.py
check_sevilla_ai_pilot_loaded.py
query_sevilla_hidden_gems_demo.py
```

---

## 8. Artefactos y reports esperados

El sistema produce artefactos en distintas rutas:

```text
data/raw/        → payloads fuente originales
data/staging/    → transformaciones intermedias
data/artifacts/  → reports, checks, summaries, demos, logs
data/external/   → datasets externos grandes no versionados
```

Los reports importantes suelen guardarse como JSON:

```text
batch_check.json
reviews_batch_check.json
load_*_report.json
check_*_report.json
*_summary.json
```

En operación, un report es correcto cuando contiene señales como:

```text
errors = []
warnings = []
checks principales = true
ready_for_querying = true
ready_for_sevilla_pilot_queries = true
```

---

## 9. Qué no debe hacerse directamente

No se recomienda:

```text
- lanzar toda Sevilla de golpe con Google Places;
- usar FieldMask: *;
- pedir Place Details masivos sin tandas;
- subir .env a Git;
- subir raw/staging/reviews completas al repositorio;
- insertar resultados IA sin checks de mapeo;
- tratar yelp_prototype como ranking real de Sevilla;
- marcar sevilla_pilot como production_ready sin validación posterior;
- modificar manualmente datos canónicos sin registrar trazabilidad.
```

---

## 10. Estado de producción

El sistema dispone de un piloto completo, pero todavía no se considera producción final.

Estado actual recomendado:

```text
Yelp prototype:
  ranking_scope = yelp_prototype
  is_production_ready = false

Sevilla pilot:
  artifact_ranking_scope = sevilla_pilot
  db_ranking_scope = other
  is_production_ready = false
```

El salto a producción requerirá:

```text
- más validación manual;
- criterios de aceptación más estrictos;
- posible mejora de modelos/reglas;
- dashboard o API;
- control de versiones de ranking;
- decisión explícita sobre ranking_scope productivo.
```

---

## 11. Próximo bloque operativo

Después de estos primeros documentos, la operación debe completarse con:

```text
03_google_places_operations.md
04_ai_pipeline_operations.md
05_checks_and_validation_runbook.md
06_artifacts_logs_and_data_management.md
07_troubleshooting.md
08_git_and_delivery_workflow.md
```

El objetivo es que cualquier ejecución importante del proyecto tenga una ruta operativa clara y reproducible.
