# 06. Gestión de artefactos, logs y datos locales




## 1. Objetivo del documento

Este documento define cómo debe gestionarse la información generada por el pipeline de **Hidden Gems** durante la ejecución de ingestas, transformaciones, checks, notebooks, cargas IA y demos.

El proyecto no se apoya únicamente en PostgreSQL. También genera y consume muchos artefactos en disco:

```text
data/raw/
data/staging/
data/reference/
data/external/
data/artifacts/
data/artifacts/ai/
data/artifacts/logs/
```

El objetivo operativo es que estos artefactos estén organizados, sean trazables y no contaminen el repositorio Git con datos pesados, claves, reseñas completas o salidas temporales.

---

## 2. Principio general

La regla principal es:

```text
El repositorio debe contener código, documentación, DDL, notebooks y configuraciones públicas.
Los datos raw, staging, reviews completas, JSONL pesados, CSV grandes y outputs temporales deben permanecer fuera de Git.
```

Esto permite mantener el proyecto:

- limpio;
- reproducible;
- seguro;
- fácil de clonar;
- sin exposición accidental de datos sensibles o claves;
- sin archivos pesados innecesarios.

---

## 3. Tipos de contenido del proyecto

Dentro de Hidden Gems hay varios tipos de contenido que conviene distinguir.

| Tipo | Ejemplos | ¿Versionar en Git? |
|---|---|---:|
| Código fuente | `src/`, `scripts/` | Sí |
| DDL | `db/ddl/*.sql` | Sí |
| Documentación | `docs/**/*.md`, `README.md` | Sí |
| Notebooks de trabajo | `notebooks/*.ipynb` | Sí, si no contienen salidas pesadas |
| Configuración pública | `.env.example`, YAML sin secretos | Sí |
| Configuración privada | `.env` | No |
| Raw API/datasets | `data/raw/`, `data/external/` | No |
| Staging | `data/staging/` | No |
| Artefactos pesados IA | JSONL/CSV completos | No |
| Reports pequeños | summaries/checks ligeros | Opcional |
| Logs | `data/artifacts/logs/*.log` | No |

---

## 4. Carpeta `data/raw/`

## 4.1. Propósito

`data/raw/` contiene respuestas originales de fuentes externas.

Ejemplos:

```text
data/raw/google_places/...
data/raw/osm_overpass/...
data/raw/sevilla_geo/...
```

En esta capa se conservan los datos tal como llegaron desde la fuente, sin reinterpretarlos como entidades finales.

---

## 4.2. Reglas operativas

Los datos raw deben tratarse como evidencia de ejecución.

Reglas:

```text
1. No editar manualmente archivos raw.
2. Si se repite una descarga, se genera un nuevo raw_asset.
3. Mantener checksum y ruta registrados en PostgreSQL.
4. No subir raw a Git.
5. No compartir raw si contiene textos completos, identificadores o datos sujetos a restricciones.
```

---

## 4.3. Relación con la base de datos

Cada raw importante debe estar registrado en:

```text
hidden_gems.raw_asset
```

Y asociado a:

```text
source_system
source_run
```

Esto permite reconstruir:

```text
fuente → ejecución → raw → staging → importación
```

---

## 5. Carpeta `data/staging/`

## 5.1. Propósito

`data/staging/` contiene datos intermedios ya transformados o perfilados, pero todavía no considerados resultado final.

Ejemplos:

```text
data/staging/google_places/<raw_asset_id>/accepted_candidates.json
data/staging/google_places/<raw_asset_id>/deduplication/unique_candidates.json
data/staging/google_places_reviews/<raw_asset_id>/accepted_reviews.json
data/staging/yelp_open_dataset/food_reviews.jsonl
```

---

## 5.2. Reglas operativas

```text
1. Staging puede regenerarse desde raw si el pipeline es reproducible.
2. No editar staging manualmente salvo inspección puntual.
3. No subir staging completo a Git.
4. Usar summaries y checks para documentar resultados.
5. Si un staging se usa para carga crítica, conservarlo localmente hasta validar el proceso.
```

---

## 6. Carpeta `data/reference/`

## 6.1. Propósito

`data/reference/` puede contener referencias auxiliares ligeras usadas por el pipeline.

Ejemplos posibles:

```text
catálogos pequeños
mapeos manuales
listas de alias
referencias territoriales derivadas
```

---

## 6.2. Regla de versionado

Solo deberían versionarse archivos de referencia si:

```text
- son pequeños;
- no contienen datos sensibles;
- son necesarios para reproducir el pipeline;
- no contienen reviews completas ni payloads raw.
```

Si son grandes o generados automáticamente, deben quedar fuera de Git.

---

## 7. Carpeta `data/external/`

## 7.1. Propósito

`data/external/` almacena datasets externos descargados manualmente o recibidos como ficheros grandes.

Ejemplo principal:

```text
data/external/yelp_open_dataset/
```

---

## 7.2. Reglas obligatorias

```text
1. No subir datasets externos a Git.
2. No compartir snapshots originales.
3. No publicar reseñas completas.
4. Documentar solo summaries y perfiles.
5. Mantener la ruta local reproducible en la documentación.
```

En el caso de Yelp, el TAR y los JSONL originales deben permanecer siempre en local.

---

## 8. Carpeta `data/artifacts/`

## 8.1. Propósito

`data/artifacts/` contiene salidas generadas por scripts, checks, notebooks y demos.

Ejemplos:

```text
data/artifacts/google_places_batches/
data/artifacts/google_places_reviews_batches/
data/artifacts/ai/sevilla/
data/artifacts/ai/ranking/
data/artifacts/ai/query_demo/
data/artifacts/logs/
```

---

## 8.2. Tipos de artefactos

| Tipo | Ejemplo | Uso |
|---|---|---|
| Planes de batch | `plan.json` | Saber qué se iba a ejecutar |
| Resultados de batch | `results.json` | Saber qué se ejecutó realmente |
| Summaries | `batch_summary.json` | Resumen operativo |
| Checks | `*_check.json` | Validación técnica |
| Reports de carga | `*_report.json` | Auditoría de loaders |
| CSV demo | `sevilla_demo_top_global.csv` | Dashboard/demo |
| JSONL IA | `sevilla_dish_mentions_with_sentiment_v1.jsonl` | Entrada/salida IA |
| Logs | `pipeline.log` | Depuración |

---

## 8.3. Qué artefactos pueden versionarse

Se pueden versionar de forma selectiva:

```text
- summaries pequeños;
- reports JSON sin textos completos;
- ejemplos anonimizados o reducidos;
- artefactos necesarios para documentación académica;
- capturas o tablas resumidas sin datos sensibles.
```

No se deben versionar:

```text
- reviews completas;
- raw API responses;
- JSONL completos de corpus;
- CSV grandes con textos;
- logs extensos;
- ficheros con API keys;
- dumps de base de datos.
```

---

## 9. Artefactos de Google Places

## 9.1. Text Search

Rutas habituales:

```text
data/raw/google_places/...
data/staging/google_places/<raw_asset_id>/
data/artifacts/google_places_batches/<batch_name>/
```

Artefactos relevantes:

```text
plan.json
results.json
batch_summary.json
batch_check.json
pipeline_summary.json
```

Uso operativo:

```text
- plan.json permite revisar lo planificado;
- results.json permite revisar cada ejecución;
- batch_summary.json resume totales;
- batch_check.json confirma consistencia.
```

---

## 9.2. Google Places Reviews

Rutas habituales:

```text
data/raw/google_places/...
data/staging/google_places_reviews/<raw_asset_id>/
data/artifacts/google_places_reviews_batches/<batch_name>/
```

Artefactos relevantes:

```text
accepted_reviews.json
rejected_reviews.json
issues.json
import_summary.json
pipeline_summary.json
reviews_batch_check.json
```

Regla importante:

```text
accepted_reviews.json puede contener textos completos de reviews. No debe subirse a Git.
```

---

## 10. Artefactos IA Yelp

Rutas habituales:

```text
data/artifacts/ai/normalization/
data/artifacts/ai/sentiment/
data/artifacts/ai/aggregation/
data/artifacts/ai/ranking/
data/artifacts/ai/checks/
```

Ejemplos:

```text
dish_catalog_seed_v2.csv
dish_aliases_seed_v2.csv
dish_mentions_with_sentiment_hybrid_v1.jsonl
dish_business_ranking_candidates_v1.csv
hidden_gems_selected_candidates_v1.csv
check_ai_ranking_loaded_report.json
```

Reglas:

```text
1. JSONL y CSV pesados deben quedar fuera de Git.
2. Reports pequeños pueden conservarse localmente y documentarse.
3. Yelp sigue siendo prototipo IA, no producción Sevilla.
```

---

## 11. Artefactos IA Sevilla

Rutas principales:

```text
data/artifacts/ai/sevilla/reviews_export/
data/artifacts/ai/sevilla/dish_detection/
data/artifacts/ai/sevilla/dish_normalization/
data/artifacts/ai/sevilla/sentiment/
data/artifacts/ai/sevilla/aggregation/
data/artifacts/ai/sevilla/ranking/
data/artifacts/ai/sevilla/query_demo/
```

Artefactos principales del piloto:

```text
reviews_for_ai_google_places.jsonl
sevilla_dish_mentions_with_sentiment_v1.jsonl
sevilla_place_dish_signals_v1.jsonl
sevilla_hidden_gems_selected_candidates_v1.jsonl
sevilla_hidden_gems_ranking_summary_v1.json
load_sevilla_ai_pilot_outputs_report.json
check_sevilla_ai_pilot_loaded_report.json
sevilla_hidden_gems_query_demo_report.json
```

Reglas:

```text
1. Los JSONL con reviews, menciones o textos completos no deben subirse.
2. Los summaries pueden usarse para documentación si no contienen texto sensible.
3. Los CSV demo se pueden generar localmente para dashboard.
4. El ranking actual es sevilla_pilot, no producción final.
```

---

## 12. Logs

## 12.1. Ubicación

El log principal se escribe en:

```text
data/artifacts/logs/pipeline.log
```

Además, algunos scripts imprimen salida en consola y generan reports JSON específicos.

---

## 12.2. Uso recomendado

Los logs sirven para:

```text
- depurar errores;
- comprobar orden de ejecución;
- revisar tiempos;
- localizar raw_asset_id o source_run_id;
- entender fallos de API o base de datos.
```

---

## 12.3. Reglas

```text
1. No subir logs completos a Git.
2. Revisar que no incluyan API keys.
3. Limpiar logs antiguos si crecen demasiado.
4. Para documentación, copiar solo fragmentos relevantes y anonimizados.
```

---

## 13. Naming de batches y artefactos

## 13.1. Principio

Los nombres deben ser:

```text
claros + cortos + únicos + trazables
```

Evitar nombres excesivamente largos, especialmente en Windows, porque pueden provocar errores por rutas largas.

---

## 13.2. Ejemplos recomendados

Google Places:

```text
gp_sevilla_ai_pilot_01_import
gp_sevilla_ai_pilot_02_import
gp_distrito_triana_import_v1
gp_pilot_5_barrios_import_v1
```

Google Reviews:

```text
gp_reviews_ai_pilot_01_import
gp_reviews_ai_pilot_02_import
gp_reviews_santa_cruz_import_v1
```

IA Sevilla:

```text
sevilla_ai_pilot_v1
sevilla_hidden_gems_ranking_pilot_v1
```

---

## 14. Limpieza de artefactos

## 14.1. Qué se puede limpiar

Se pueden limpiar con precaución:

```text
- outputs temporales fallidos;
- logs antiguos;
- staging regenerable;
- artefactos duplicados de pruebas;
- batches dry-run antiguos.
```

---

## 14.2. Qué conviene conservar

Conviene conservar:

```text
- raw asociados a cargas importantes;
- summaries de batches relevantes;
- reports de checks finales;
- reports de loaders reales;
- artefactos finales usados para documentación o dashboard;
- notebooks finales ejecutados.
```

---

## 14.3. Recomendación práctica

Antes de borrar:

```text
1. Confirmar que la carga está validada en PostgreSQL.
2. Confirmar que existe un report JSON final.
3. Confirmar que no se necesita reproducir el error.
4. No borrar raw de ejecuciones importantes si aún no se ha hecho backup o documentación.
```

---

## 15. Reglas de `.gitignore`

El `.gitignore` debe proteger al menos:

```gitignore
.env
.venv/
__pycache__/
.ipynb_checkpoints/

# Datos locales
data/raw/
data/staging/
data/external/
data/artifacts/logs/

# Corpus y artefactos pesados
data/artifacts/nlp_corpus/*.jsonl
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv

# Datasets externos
data/external/yelp_open_dataset/
```

Si se desea versionar algún summary concreto, debe añadirse explícitamente o copiarse a una carpeta de documentación como ejemplo reducido.

---

## 16. Protección de claves y credenciales

Nunca deben aparecer en Git:

```text
GOOGLE_MAPS_API_KEY
PGPASSWORD real
cualquier token externo
credenciales de servicios
URLs privadas con secretos
```

La clave de Google debe estar solo en `.env` local.

`.env.example` debe contener la variable vacía:

```env
GOOGLE_MAPS_API_KEY=
```

---

## 17. Protección de textos de reseñas

Las reviews pueden contener texto de usuarios.

Por tanto:

```text
1. No publicar dumps completos de reviews.
2. No subir JSONL completos de reviews a Git.
3. Evitar incluir textos largos de reviews en documentación.
4. Para ejemplos, usar fragmentos breves o datos sintéticos.
5. Para dashboards públicos, valorar anonimización o agregación.
```

En este proyecto, la documentación debe centrarse en métricas, conteos, checks y ejemplos controlados.

---

## 18. Reports recomendados para conservar

Para tener evidencia operativa del estado del proyecto, conviene conservar localmente estos reports:

```text
check_google_places_batch.json
reviews_batch_check.json
check_ai_review_export_report.json
load_sevilla_ai_pilot_outputs_report.json
check_sevilla_ai_pilot_loaded_report.json
sevilla_hidden_gems_query_demo_report.json
```

Y para Yelp prototype:

```text
check_ai_dish_catalog_report.json
check_ai_downstream_import_readiness_report.json
load_ai_mentions_and_sentiment_report.json
load_ai_signals_and_ranking_report.json
check_ai_ranking_loaded_report.json
```

---

## 19. Relación con dashboard

El futuro dashboard no debería leer directamente artefactos raw ni staging.

Opciones recomendadas:

```text
Opción rápida:
query_sevilla_hidden_gems_demo.py
→ CSV/JSON limpios en data/artifacts/ai/sevilla/query_demo/
→ dashboard Streamlit
```

```text
Opción más estable:
PostgreSQL views
→ script export_sevilla_dashboard_data.py
→ dashboard
```

El dashboard debe consumir salidas ya filtradas, sin textos completos innecesarios.

---

## 20. Checklist operativo

Antes de cerrar una fase de datos:

```text
[ ] El script terminó sin error.
[ ] Existe report JSON.
[ ] El check correspondiente pasó.
[ ] errors = [] o equivalente.
[ ] warnings revisadas.
[ ] No hay artefactos pesados preparados para commit.
[ ] No hay claves en outputs.
[ ] Los datos importantes están respaldados localmente.
[ ] La documentación refleja el estado real.
```

---

## 21. Conclusión

La gestión de artefactos, logs y datos locales es una parte esencial de la operación de Hidden Gems.

El proyecto genera muchos archivos intermedios, pero no todos tienen el mismo valor ni el mismo nivel de seguridad.

La regla final es:

```text
Trazabilidad sí.
Git limpio también.
```

Mantener esta separación permite que Hidden Gems siga creciendo sin que el repositorio se vuelva pesado, inseguro o difícil de operar.

---

## 22. Artefactos Sevilla IA v2

La fase Sevilla IA v2 añade una nueva capa de artefactos:

```text
data/artifacts/ai/sevilla/model_inference/
├── ner_v1_2/
├── ner_v1_2_cleaned/
├── hybrid_ner_v2/
├── normalization_reranker_v1/
├── sentiment_absa_v1/
├── place_dish_signals_v2/
├── ranking_v2/
└── ranking_v2_comparison/
```

Export de dashboard:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Archivos principales de dashboard v2:

```text
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
mention_examples.csv
place_coordinates.csv
comparison/
```

`mention_examples.csv` puede contener texto completo si se generó con `--include-full-review-text`; no debe versionarse.

---

## 23. Modelos entrenados locales

Los modelos de la fase v2 se guardan en:

```text
models/
```

Reglas:

```text
1. No subir models/ a Git.
2. Mantener los modelos localmente para ejecutar inferencia.
3. Documentar nombre, función y versión.
4. En producción futura, implementar descarga automática si no existen.
```

Añadir a `.gitignore`:

```gitignore
models/
```

---

## 24. Regla de entrega académica

Versionar:

```text
README.md
docs/**/*.md
scripts/*.py
dashboard/*.py
requirements.txt
.env.example
.gitignore
db/ddl/*.sql
```

Mantener fuera de Git:

```text
models/
data/raw/
data/staging/
data/external/
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
data/artifacts/ai/sevilla/dashboard_v2/*.csv
```
