# `docs/44_vertical_yelp_open_dataset.md`

# Vertical Yelp Open Dataset

## 1. Objetivo de la vertical

La vertical **Yelp Open Dataset** tiene como objetivo construir un corpus externo de reseñas gastronómicas para las futuras fases de NLP de Hidden Gems.

A diferencia de Google Places y Google Places Reviews, esta vertical no busca alimentar directamente el modelo operativo de locales de Sevilla. Su finalidad es preparar un dataset amplio, trazable y controlado para tareas de procesamiento de lenguaje natural.

El uso principal de esta vertical es:

- crear un corpus de entrenamiento para extracción de platos;
- disponer de reseñas gastronómicas extensas y variadas;
- preparar ejemplos para análisis de sentimiento;
- generar una base de entrenamiento para sentimiento general de reseñas;
- preparar una futura aproximación a sentimiento por plato;
- disponer de datos para experimentación NLP antes de aplicar modelos a Google Reviews locales;
- separar claramente corpus externo de entrenamiento y datos operativos de la aplicación.

La salida principal de esta vertical es un archivo JSONL de corpus NLP:

```text
data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

---

## 2. Papel de Yelp dentro de Hidden Gems

La estrategia global del proyecto diferencia claramente entre datos operativos y datos de entrenamiento:

```text
Google Places
→ locales reales de Sevilla
→ place / place_source_ref / barrio / distrito
```

```text
Google Places Reviews
→ comentarios reales asociados a locales de Sevilla
→ hidden_gems.review
→ review → place → barrio
```

```text
Yelp Open Dataset
→ corpus externo amplio
→ entrenamiento y evaluación NLP
→ no vinculado inicialmente a place de Sevilla
```

Por tanto, Yelp no se utiliza en esta fase para crear locales canónicos ni para generar rankings operativos por barrio.

La relación conceptual es:

```text
Yelp Open Dataset
→ corpus NLP
→ entrenamiento / experimentación
→ modelos o reglas aplicables después sobre Google Reviews locales
```

---

## 3. Decisión clave: Yelp no se importa en `hidden_gems.review`

La tabla `hidden_gems.review` está orientada a reseñas operativas vinculadas a un local real del sistema.

En Google Reviews, cada reseña queda vinculada a:

```text
review.place_id
review.place_source_ref_id
review.source_place_record_id
```

En Yelp Open Dataset, las reseñas pertenecen a negocios externos del dataset, no necesariamente a locales de Sevilla ni a locales ya consolidados en `hidden_gems.place`.

Por ese motivo, esta vertical no inserta Yelp en:

```text
hidden_gems.review
```

En su lugar, construye un corpus separado:

```text
data/artifacts/nlp_corpus/*.jsonl
```

Esto evita:

- crear locales falsos;
- permitir reviews huérfanas en el modelo operativo;
- mezclar datos locales con corpus externo;
- contaminar futuros rankings por barrio;
- romper la trazabilidad entre `review`, `place` y `neighborhood`.

La decisión queda así:

```text
Google Reviews
→ review operativo con place_id

Yelp Reviews
→ corpus externo para NLP
```

---

## 4. Restricciones de uso y tratamiento del dataset

El Yelp Open Dataset se trata como un recurso local para uso académico y experimental.

Reglas adoptadas en el proyecto:

```text
1. No subir el dataset al repositorio.
2. No compartir el dataset con terceros.
3. No exponer públicamente reviews individuales.
4. No usarlo como fuente comercial.
5. No construir listados operativos de locales a partir de Yelp.
6. Usarlo únicamente como corpus de entrenamiento/evaluación NLP.
7. Mantener los ficheros grandes fuera de Git.
8. Trabajar mediante subsets y artefactos controlados.
```

Por tanto, los ficheros grandes se colocan en:

```text
data/external/yelp_open_dataset/
```

y deben quedar ignorados por Git.

---

## 5. Estructura local de carpetas

Para esta vertical se utiliza la siguiente estructura:

```text
data/
├── external/
│   └── yelp_open_dataset/
│       ├── yelp_dataset-001.tar
│       └── extracted/
│           ├── yelp_academic_dataset_business.json
│           └── yelp_academic_dataset_review.json
│
├── staging/
│   └── yelp_open_dataset/
│       ├── food_businesses.jsonl
│       ├── food_business_ids.txt
│       ├── food_businesses_summary.json
│       ├── food_reviews.jsonl
│       └── food_reviews_summary.json
│
└── artifacts/
    ├── yelp_open_dataset_qa/
    │   ├── yelp_dataset-001_tar_profile.json
    │   ├── yelp_dataset-001_selected_extract_manifest.json
    │   ├── yelp_jsonl_profile.json
    │   ├── food_businesses_summary.json
    │   ├── food_reviews_summary.json
    │   ├── yelp_food_reviews_corpus_sample_100k_lines_summary.json
    │   └── yelp_food_reviews_corpus_sample_100k_lines_check.json
    │
    └── nlp_corpus/
        ├── yelp_food_reviews_corpus_sample_100k_lines.jsonl
        └── yelp_food_reviews_corpus_sample_100k_lines_summary.json
```

---

## 6. Reglas de `.gitignore`

Se recomienda ignorar los ficheros grandes del dataset y los JSONL derivados de gran volumen.

Bloque recomendado:

```gitignore
# Yelp Open Dataset - local large files
data/external/yelp_open_dataset/
data/staging/yelp_open_dataset/*.jsonl
data/staging/yelp_open_dataset/*.txt
data/staging/yelp_open_dataset/*.json
data/artifacts/nlp_corpus/*.jsonl
```

Los scripts, documentación y summaries pequeños sí pueden versionarse si se considera útil.

---

## 7. Ficheros del TAR original

El dataset se recibió como un archivo TAR local:

```text
data/external/yelp_open_dataset/yelp_dataset-001.tar
```

El perfilado del TAR detectó seis miembros:

| Fichero | Tipo detectado | Tamaño aproximado |
|---|---:|---:|
| `Dataset_User_Agreement.pdf` | documentación | 0.077 MB |
| `yelp_academic_dataset_business.json` | business | 113.357 MB |
| `yelp_academic_dataset_checkin.json` | checkin | 273.665 MB |
| `yelp_academic_dataset_review.json` | review | 5094.403 MB |
| `yelp_academic_dataset_tip.json` | tip | 172.238 MB |
| `yelp_academic_dataset_user.json` | user | 3207.520 MB |

Para esta vertical se extraen únicamente:

```text
yelp_academic_dataset_business.json
yelp_academic_dataset_review.json
```

No se extraen inicialmente:

```text
user.json
checkin.json
tip.json
```

porque no son necesarios para construir el primer corpus de reseñas gastronómicas.

---

## 8. Naturaleza JSON Lines del dataset

Los ficheros del Yelp Open Dataset se tratan como **JSON Lines**:

```text
1 línea = 1 objeto JSON
```

Por tanto, no se deben cargar con:

```python
json.load(file)
```

porque eso intentaría cargar el fichero completo en memoria.

El patrón correcto es:

```python
for line in file:
    row = json.loads(line)
```

Esta decisión es fundamental porque `review.json` pesa más de 5 GB.

---

## 9. Scripts implementados

La vertical se ha dividido en scripts pequeños y reproducibles.

| Script | Propósito |
|---|---|
| `scripts/profile_yelp_tar.py` | Perfilar el `.tar` sin extraerlo completo |
| `scripts/extract_yelp_selected_files.py` | Extraer de forma segura solo `business.json` y `review.json` |
| `scripts/profile_yelp_jsonl_files.py` | Perfilar `business.json` y una muestra de `review.json` |
| `scripts/build_yelp_food_business_subset.py` | Filtrar negocios gastronómicos |
| `scripts/build_yelp_food_review_subset.py` | Filtrar reviews asociadas a negocios gastronómicos |
| `scripts/build_yelp_nlp_corpus.py` | Construir corpus NLP final |
| `scripts/check_yelp_nlp_corpus.py` | Validar el corpus NLP generado |

---

## 10. Paso 1 — Perfilado del TAR

Script:

```text
scripts/profile_yelp_tar.py
```

Comando utilizado:

```powershell
python -m scripts.profile_yelp_tar `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

Objetivo:

- inspeccionar el TAR sin extraer todos los ficheros;
- detectar nombres exactos;
- clasificar miembros;
- calcular tamaños;
- verificar que existen `business` y `review`.

Resultado real:

```text
member_file_count = 6
total_size_gb = 8.654
business = true
review = true
user = true
checkin = true
tip = true
photo = false
```

Artefacto generado:

```text
data/artifacts/yelp_open_dataset_qa/yelp_dataset-001_tar_profile.json
```

---

## 11. Paso 2 — Extracción controlada

Script:

```text
scripts/extract_yelp_selected_files.py
```

Comando utilizado:

```powershell
python -m scripts.extract_yelp_selected_files `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

Objetivo:

- extraer solo los ficheros necesarios;
- evitar extracción completa del TAR;
- evitar path traversal;
- calcular `sha256`;
- registrar tamaño y ruta;
- generar manifest de extracción.

Ficheros extraídos:

```text
data/external/yelp_open_dataset/extracted/yelp_academic_dataset_business.json
data/external/yelp_open_dataset/extracted/yelp_academic_dataset_review.json
```

Resultado real:

```text
business.json size = 118.863.795 bytes
business.json sha256 = 392280627d83ecdcbff8006bba5db289f8436ef147d5a103b1ace5b54186727f

review.json size = 5.341.868.833 bytes
review.json sha256 = a4edc050d14eec25373a75e7ee211d42f49f14f47230837d8c7849eb9c5f2f96
```

Checks:

```text
all_requested_types_extracted = true
has_business = true
has_review = true
```

Artefacto generado:

```text
data/artifacts/yelp_open_dataset_qa/yelp_dataset-001_selected_extract_manifest.json
```

---

## 12. Paso 3 — Perfilado de JSONL

Script:

```text
scripts/profile_yelp_jsonl_files.py
```

Comando utilizado:

```powershell
python -m scripts.profile_yelp_jsonl_files `
  --save-artifact
```

Este script realiza:

```text
business.json → escaneo completo
review.json   → primeras 100.000 líneas
```

Objetivo:

- comprobar que los JSONL son válidos;
- revisar campos;
- obtener ejemplos;
- perfilar categorías;
- perfilar ratings;
- revisar fechas;
- revisar longitud de reviews.

Checks validados:

```text
business_file_exists = true
review_file_exists = true
business_has_records = true
review_has_records = true
business_invalid_json_is_zero = true
review_invalid_json_is_zero = true
business_has_business_id_field = true
business_has_categories_field = true
review_has_review_id_field = true
review_has_business_id_field = true
review_has_text_field = true
```

Artefacto generado:

```text
data/artifacts/yelp_open_dataset_qa/yelp_jsonl_profile.json
```

---

## 13. Paso 4 — Filtrado de negocios gastronómicos

Script:

```text
scripts/build_yelp_food_business_subset.py
```

Comando utilizado:

```powershell
python -m scripts.build_yelp_food_business_subset `
  --min-review-count 1 `
  --save-artifact
```

Objetivo:

```text
business.json
→ food_businesses.jsonl
→ food_business_ids.txt
```

El filtrado utiliza categorías de Yelp para identificar negocios gastronómicos.

Categorías de inclusión relevantes:

```text
Restaurants
Food
Bars
Cafes
Coffee & Tea
Breakfast & Brunch
Bakeries
Pizza
Mexican
Italian
Spanish
Mediterranean
Tapas Bars
Sushi Bars
Seafood
Burgers
Sandwiches
Food Trucks
Diners
Delis
```

También se aplicaron exclusiones para evitar falsos positivos como:

```text
Doctors
Traditional Chinese Medicine
Health & Medical
Barbers
Drugstores
Beauty & Spas
Auto Repair
Real Estate
```

La primera versión del filtro era demasiado permisiva porque detectaba `Chinese` dentro de `Traditional Chinese Medicine`. El filtro fue endurecido para usar coincidencias exactas de categorías normalizadas.

Resultado validado:

```text
processed_count = 150.346
invalid_json_count = 0
food_candidate_count = 66.770
kept_count = 66.770
unique_business_id_count = 66.770
```

Checks validados:

```text
input_file_exists = true
processed_records = true
invalid_json_is_zero = true
has_food_businesses = true
business_ids_are_unique = true
output_food_businesses_exists = true
output_food_business_ids_exists = true
```

Salidas:

```text
data/staging/yelp_open_dataset/food_businesses.jsonl
data/staging/yelp_open_dataset/food_business_ids.txt
data/staging/yelp_open_dataset/food_businesses_summary.json
```

Artefacto:

```text
data/artifacts/yelp_open_dataset_qa/food_businesses_summary.json
```

---

## 14. Paso 5 — Filtrado de reviews gastronómicas

Script:

```text
scripts/build_yelp_food_review_subset.py
```

Comando de prueba utilizado:

```powershell
python -m scripts.build_yelp_food_review_subset `
  --max-lines 100000 `
  --min-text-length 40 `
  --save-artifact
```

Objetivo:

```text
review.json
→ conservar reviews cuyo business_id esté en food_business_ids.txt
→ food_reviews.jsonl
```

Este script lee `review.json` en streaming y conserva solo reviews asociadas a negocios gastronómicos filtrados previamente.

Resultado real sobre las primeras 100.000 líneas:

```text
food_business_id_count = 66.770
business_metadata_count = 66.770
processed_lines = 100.000
invalid_json_count = 0
matched_business_count = 79.922
kept_review_count = 79.882
unique_review_id_count = 79.882
unique_business_ids_with_reviews = 5.150
skipped_missing_text_count = 0
skipped_short_text_count = 40
skipped_missing_business_metadata_count = 0
```

Distribución de ratings:

```text
5.0 = 33.523
4.0 = 21.822
3.0 = 9.888
1.0 = 7.834
2.0 = 6.815
```

Rango temporal:

```text
min_date = 2005-03-01 17:47:15
max_date = 2018-10-04 18:20:00
```

Principales categorías:

```text
Restaurants
Food
Nightlife
Bars
American (New)
American (Traditional)
Breakfast & Brunch
Sandwiches
Seafood
Coffee & Tea
Pizza
Burgers
Mexican
Italian
Cafes
Cocktail Bars
Salad
Sushi Bars
Bakeries
Japanese
Desserts
Chinese
```

Checks validados:

```text
review_file_exists = true
food_business_ids_loaded = true
business_metadata_loaded = true
processed_lines = true
invalid_json_is_zero = true
has_matched_reviews = true
has_kept_reviews = true
review_ids_are_unique = true
business_metadata_complete_for_kept_reviews = true
output_food_reviews_exists = true
```

Salidas:

```text
data/staging/yelp_open_dataset/food_reviews.jsonl
data/staging/yelp_open_dataset/food_reviews_summary.json
```

Artefacto:

```text
data/artifacts/yelp_open_dataset_qa/food_reviews_summary.json
```

---

## 15. Paso 6 — Construcción del corpus NLP

Script:

```text
scripts/build_yelp_nlp_corpus.py
```

Comando utilizado:

```powershell
python -m scripts.build_yelp_nlp_corpus `
  --corpus-name yelp_food_reviews_corpus_sample_100k_lines `
  --min-text-length 80 `
  --max-text-length 5000 `
  --save-artifact
```

Objetivo:

```text
food_reviews.jsonl
→ yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

El corpus NLP añade:

- ID de documento estable;
- split determinista;
- etiqueta débil de sentimiento derivada del rating;
- idioma asumido;
- metadatos del negocio;
- métricas fuente;
- flags de calidad;
- scopes de tarea NLP.

---

## 16. Estructura del documento del corpus

Cada documento del corpus tiene una estructura similar a:

```json
{
  "corpus_document_id": "yelp_2fbfd094613536a7b8c9231b",
  "source_system_code": "yelp_open_dataset",
  "source_dataset": "yelp_open_dataset",
  "source_entity_type": "yelp_review",
  "source_review_id": "KU_O5udG6zpxOg-VcAEodg",
  "source_business_id": "XQfwVwDr-v0ZS3_CbbE5Xw",
  "source_user_id": "...",
  "text": "If you decide to eat here...",
  "text_normalized": "If you decide to eat here...",
  "language": "en",
  "rating_value": 3.0,
  "sentiment_label_from_rating": "neutral",
  "review_date": "2018-07-07 22:09:11",
  "corpus_split": "train",
  "task_scope": [
    "dish_extraction",
    "review_sentiment",
    "dish_sentiment",
    "recommendation_signal"
  ],
  "is_training_eligible": true,
  "quality_flags": {
    "has_text": true,
    "has_rating": true,
    "has_business_metadata": true,
    "text_length_chars": 511,
    "label_is_weak": true,
    "label_source": "rating_value"
  },
  "business_metadata": {
    "business_name": "Turning Point of North Wales",
    "city": "North Wales",
    "state": "PA",
    "categories_list": [],
    "food_category_tags": []
  },
  "source_metrics": {
    "useful_count": 0,
    "funny_count": 0,
    "cool_count": 0
  }
}
```

---

## 17. Split determinista

El corpus utiliza split determinista basado en hash de `source_review_id`.

Regla:

```text
80% train
10% validation
10% test
```

Esto permite regenerar el corpus manteniendo asignaciones estables.

Distribución real:

```text
train = 63.540
validation = 7.849
test = 7.881
```

---

## 18. Etiqueta débil de sentimiento

La etiqueta de sentimiento se deriva del rating:

```text
rating >= 4 → positive
rating = 3  → neutral
rating <= 2 → negative
```

Esta etiqueta se considera **weak label**, no anotación humana.

Distribución real:

```text
positive = 54.857
neutral = 9.835
negative = 14.578
```

Distribución de rating:

```text
5.0 = 33.241
4.0 = 21.616
3.0 = 9.835
1.0 = 7.790
2.0 = 6.788
```

---

## 19. Resultado del corpus NLP inicial

Resultado validado:

```text
processed_count = 79.882
invalid_json_count = 0
skipped_missing_required_count = 0
skipped_short_text_count = 612
skipped_long_text_count = 0
kept_count = 79.270
unique_document_id_count = 79.270
unique_review_id_count = 79.270
unique_business_id_count = 5.141
```

Rango de fechas:

```text
2005-2018
```

Idioma:

```text
language = en
```

Longitud textual:

```text
min = 80
max = 4.999
avg = 534.7568
```

Salidas:

```text
data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl
data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines_summary.json
```

Artefacto QA:

```text
data/artifacts/yelp_open_dataset_qa/yelp_food_reviews_corpus_sample_100k_lines_summary.json
```

---

## 20. Paso 7 — Check final del corpus NLP

Script:

```text
scripts/check_yelp_nlp_corpus.py
```

Comando utilizado:

```powershell
python -m scripts.check_yelp_nlp_corpus `
  --corpus-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl `
  --summary-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines_summary.json `
  --save-artifact
```

Objetivo:

- validar estructura JSONL;
- comprobar campos obligatorios;
- comprobar IDs únicos;
- comprobar splits;
- comprobar labels de sentimiento;
- comprobar idioma;
- comprobar metadata de negocio;
- comprobar ausencia de warnings y errores;
- comprobar coherencia con el summary.

Resultado real:

```text
processed_count = 79.270
invalid_json_count = 0
unique_document_id_count = 79.270
unique_review_id_count = 79.270
unique_business_id_count = 5.141
duplicate_document_id_count = 0
duplicate_review_id_count = 0
```

Checks validados:

```text
corpus_file_exists = true
processed_documents = true
invalid_json_is_zero = true
document_ids_are_unique = true
review_ids_are_unique = true
has_business_ids = true
has_train_split = true
has_validation_split = true
has_test_split = true
has_positive_examples = true
has_neutral_examples = true
has_negative_examples = true
has_language = true
has_no_error_issues = true
has_no_warning_issues = true
matches_summary_kept_count_when_full_scan = true
```

Artefacto:

```text
data/artifacts/yelp_open_dataset_qa/yelp_food_reviews_corpus_sample_100k_lines_check.json
```

---

## 21. Estado final de la vertical

La primera versión funcional de la vertical Yelp Open Dataset queda cerrada con éxito:

```text
[OK] TAR local perfilado
[OK] Extracción selectiva business/review
[OK] JSONL perfilados
[OK] Negocios gastronómicos filtrados
[OK] Reviews gastronómicas filtradas
[OK] Corpus NLP generado
[OK] Split train/validation/test
[OK] Etiquetas débiles de sentimiento derivadas de rating
[OK] Check final del corpus
[OK] Sin JSON inválidos
[OK] Sin duplicados
[OK] Sin errores ni warnings en el check final
```

Resultado principal:

```text
79.270 documentos NLP válidos
5.141 negocios gastronómicos con reviews en la muestra
3 splits de entrenamiento
3 clases de sentimiento
corpus listo para fase NLP
```

---

## 22. Qué queda fuera de alcance

Esta vertical no incluye:

- entrenamiento de modelos NLP;
- extracción de platos;
- análisis de sentimiento real por texto;
- análisis de sentimiento por plato;
- generación de ranking por barrio;
- importación del corpus a PostgreSQL;
- linking con `hidden_gems.place`;
- linking con Google Places;
- uso de Yelp como fuente operativa de locales;
- exposición pública del dataset o sus reviews.

Estas tareas pertenecen a fases posteriores.

---

## 23. Relación con Google Reviews locales

Tras esta vertical, el proyecto dispone de dos fuentes textuales complementarias:

```text
Google Places Reviews
→ reseñas locales de Sevilla
→ vinculadas a place y barrio
→ útiles para evaluación local y ranking futuro
```

```text
Yelp Open Dataset
→ corpus amplio externo en inglés
→ útil para entrenamiento y experimentación NLP
→ no vinculado a barrio
```

La estrategia posterior recomendada es:

```text
1. Entrenar/probar reglas NLP con Yelp.
2. Evaluar manualmente ejemplos de Google Reviews locales.
3. Adaptar diccionarios y patrones al español.
4. Aplicar extracción de platos sobre reviews locales.
5. Calcular scoring y rankings por barrio.
```

---

## 24. Próximos pasos recomendados

Una vez cerrada esta vertical, los siguientes pasos del proyecto serían:

```text
1. Documentar `34_yelp_source.md`.
2. Hacer commit de scripts y documentación.
3. Crear una primera fase NLP de exploración textual.
4. Diseñar catálogo inicial de platos y términos gastronómicos.
5. Crear baseline de extracción de platos con reglas.
6. Comparar comportamiento en Yelp y Google Reviews.
7. Preparar tablas futuras: dish, dish_mention, place_dish_score, neighborhood_dish_ranking.
```

---

## 25. Resumen ejecutivo de la vertical

La vertical Yelp Open Dataset permite transformar un snapshot local masivo de Yelp en un corpus NLP limpio, controlado y validado.

El flujo construido es:

```text
Yelp TAR
→ extracción selectiva
→ profiling
→ food businesses
→ food reviews
→ NLP corpus
→ corpus check
```

La salida final contiene:

```text
79.270 documentos válidos
0 JSON inválidos
0 duplicados
train/validation/test
positive/neutral/negative
metadata gastronómica asociada
```

Esta vertical deja preparada la base para comenzar la fase NLP de Hidden Gems sin comprometer el modelo operativo de locales y reseñas reales de Sevilla.
