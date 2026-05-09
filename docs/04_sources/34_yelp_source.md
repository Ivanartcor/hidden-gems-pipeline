# Fuente de datos: Yelp Open Dataset

## 1. Descripción general

**Yelp Open Dataset** se incorpora a Hidden Gems como una fuente externa de apoyo para el desarrollo de capacidades de análisis textual, reseñas e inteligencia artificial.

A diferencia de Sevilla Geo, Overpass y Google Places, Yelp no se utiliza como fuente productiva para descubrir locales de Sevilla ni como fuente directa para el ranking final por barrio. Su valor principal está en aportar un volumen amplio de negocios y reseñas gastronómicas para construir, entrenar, validar y prototipar el módulo IA de Hidden Gems.

La decisión actual del proyecto es tratar Yelp como:

```text
Yelp Open Dataset
→ dataset externo local
→ extracción controlada
→ subset gastronómico
→ corpus NLP
→ entrenamiento y evaluación IA
→ prototipo IA integrado en PostgreSQL
```

Y no como:

```text
Yelp Open Dataset
→ ranking productivo de Sevilla
```

Esta separación mantiene limpio el modelo operativo de Sevilla y, al mismo tiempo, permite aprovechar Yelp para construir la inteligencia textual del sistema.

---

## 2. Rol dentro del pipeline

Yelp actúa como una **fuente de corpus textual gastronómico** y como **fuente prototipo para validar la integración IA**.

Su papel actual es:

1. aportar negocios con categorías gastronómicas;
2. aportar reseñas asociadas a esos negocios;
3. permitir filtrar reseñas de contexto gastronómico;
4. generar un corpus JSONL preparado para NLP;
5. servir como base amplia para extracción de platos, análisis de sentimiento y señales textuales;
6. alimentar notebooks de entrenamiento y prototipado IA;
7. permitir cargar resultados IA en PostgreSQL de forma trazable;
8. validar el flujo completo `review → dish_mention → sentiment → signals → ranking`.

### Usos realizados

- limpieza y normalización textual;
- clasificación de sentimiento general desde rating como baseline;
- entrenamiento de un modelo transformer de sentimiento general;
- detección de platos mediante NER;
- normalización de nombres de platos;
- sentimiento por mención de plato;
- agregación de señales por negocio/plato;
- ranking Hidden Gems v1;
- integración del ranking prototipo en PostgreSQL.

---

## 3. Diferencia respecto a las otras fuentes

| Fuente | Rol principal | Uso operativo en Sevilla | Uso IA/NLP |
|---|---|---:|---:|
| Sevilla Geo | Referencia territorial oficial | Sí | No |
| Overpass / OSM | POIs gastronómicos abiertos | Sí | No directo |
| Google Places | Descubrimiento y enriquecimiento de locales | Sí | Parcial |
| Google Places Reviews | Reviews reales vinculadas a locales de Sevilla | Sí | Sí, corpus local futuro |
| Yelp Open Dataset | Corpus externo y prototipo IA | No producción | Sí |

La diferencia clave es que Google Reviews queda enlazado naturalmente a:

```text
review → place → barrio → distrito
```

Mientras que Yelp se usa como:

```text
yelp_food_reviews_corpus
→ IA experimental
→ prototipo yelp_prototype en PostgreSQL
```

---

## 4. Restricciones de uso y tratamiento del dataset

Yelp Open Dataset se utiliza bajo un contexto académico y local del proyecto.

Reglas aplicadas en Hidden Gems:

- no subir el dataset original al repositorio;
- no compartir los ficheros originales;
- no publicar reseñas completas en documentación pública;
- no usar Yelp como fuente comercial de listados;
- no utilizar Yelp como sustituto de Google Places para locales de Sevilla;
- mantener el dataset en `data/external/`, excluido por `.gitignore`;
- mantener JSONL pesados fuera de Git;
- documentar solo métricas, perfiles, summaries y artefactos derivados no sensibles;
- marcar los resultados importados en IA como prototipo, no producción.

---

## 5. Fichero fuente disponible

El dataset se recibió localmente como un archivo TAR:

```text
data/external/yelp_open_dataset/yelp_dataset-001.tar
```

El perfilado inicial del TAR detectó 6 miembros:

| Tipo | Fichero | Tamaño aproximado |
|---|---|---:|
| acuerdo de uso | `Dataset_User_Agreement.pdf` | 0,077 MB |
| negocios | `yelp_academic_dataset_business.json` | 113,357 MB |
| check-ins | `yelp_academic_dataset_checkin.json` | 273,665 MB |
| reviews | `yelp_academic_dataset_review.json` | 5.094,403 MB |
| tips | `yelp_academic_dataset_tip.json` | 172,238 MB |
| usuarios | `yelp_academic_dataset_user.json` | 3.207,520 MB |

Tamaño total aproximado del contenido:

```text
8,654 GB
```

---

## 6. Archivos utilizados

Para la primera versión de la vertical se utilizan:

```text
yelp_academic_dataset_business.json
yelp_academic_dataset_review.json
```

No se utilizan todavía:

```text
yelp_academic_dataset_user.json
yelp_academic_dataset_checkin.json
yelp_academic_dataset_tip.json
```

Motivos:

- `business.json` permite identificar negocios gastronómicos;
- `review.json` aporta el texto necesario para NLP;
- `user.json` no es necesario para extracción de platos;
- `checkin.json` no aporta texto de reseñas;
- `tip.json` puede ser útil más adelante, pero se deja fuera del primer corpus para reducir alcance.

---

## 7. Formato de los archivos

Los archivos de Yelp se tratan como **JSON Lines**:

```text
un objeto JSON por línea
```

Por tanto, deben leerse en streaming:

```python
for line in file:
    row = json.loads(line)
```

No se debe usar:

```python
json.load(file)
```

porque `review.json` tiene varios GB y puede saturar memoria.

---

## 8. Ubicación local recomendada

Estructura usada para la fuente Yelp:

```text
data/external/yelp_open_dataset/
  yelp_dataset-001.tar
  extracted/
    yelp_academic_dataset_business.json
    yelp_academic_dataset_review.json

data/staging/yelp_open_dataset/
  food_businesses.jsonl
  food_business_ids.txt
  food_businesses_summary.json
  food_reviews.jsonl
  food_reviews_summary.json

data/artifacts/yelp_open_dataset_qa/
  yelp_dataset-001_tar_profile.json
  yelp_dataset-001_selected_extract_manifest.json
  yelp_jsonl_profile.json
  food_businesses_summary.json
  food_reviews_summary.json
  yelp_food_reviews_corpus_sample_100k_lines_summary.json
  yelp_food_reviews_corpus_sample_100k_lines_check.json

data/artifacts/nlp_corpus/
  yelp_food_reviews_corpus_sample_100k_lines.jsonl
  yelp_food_reviews_corpus_sample_100k_lines_summary.json

data/artifacts/ai/
  normalization/
  sentiment/
  aggregation/
  ranking/
  checks/
```

---

## 9. `.gitignore`

Los datos externos y artefactos pesados deben estar excluidos de Git.

Reglas recomendadas:

```gitignore
# Yelp Open Dataset - local large files
data/external/yelp_open_dataset/
data/staging/yelp_open_dataset/*.jsonl
data/staging/yelp_open_dataset/*.txt
data/staging/yelp_open_dataset/*.json
data/artifacts/nlp_corpus/*.jsonl
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
```

La documentación, scripts y summaries ligeros pueden versionarse si no contienen contenido sensible o excesivo.

---

## 10. Source system

La fuente se identifica como:

```text
source_code = yelp_open_dataset
```

Definición conceptual:

```json
{
  "source_code": "yelp_open_dataset",
  "source_name": "Yelp Open Dataset",
  "source_type": "bulk_dataset",
  "description": "Dataset académico de Yelp usado como corpus externo y prototipo IA gastronómico.",
  "base_url": "https://business.yelp.com/data/resources/open-dataset/",
  "auth_type": "none",
  "data_format_default": "jsonl",
  "refresh_mode_default": "snapshot",
  "supports_incremental": false,
  "is_active": true,
  "notes": "No se usa como fuente productiva Sevilla; se usa como corpus yelp_prototype para IA."
}
```

En la fase actual, Yelp sí se ha importado parcialmente a PostgreSQL, pero con un objetivo muy concreto: crear el puente necesario para validar el módulo IA completo.

---

## 11. Tipo de información aportada

### 11.1. Negocios

`business.json` aporta información como:

- `business_id`;
- nombre;
- dirección;
- ciudad;
- estado;
- código postal;
- latitud;
- longitud;
- rating medio;
- número de reseñas;
- estado abierto/cerrado;
- categorías;
- atributos;
- horarios.

### 11.2. Reviews

`review.json` aporta información como:

- `review_id`;
- `business_id`;
- `user_id`;
- `stars`;
- texto;
- fecha;
- votos `useful`;
- votos `funny`;
- votos `cool`.

### 11.3. Otros ficheros no usados inicialmente

- `tip.json`: textos cortos tipo recomendación;
- `checkin.json`: patrones de actividad;
- `user.json`: metadata de usuarios.

Estos ficheros se dejan fuera del primer MVP de la vertical.

---

## 12. Decisión de integración actual

La decisión inicial fue no transformar Yelp directamente en fuente operativa de Sevilla.

Tras desarrollar el módulo IA, se añadió una segunda decisión más precisa:

> Yelp puede importarse de forma controlada como **corpus/prototipo IA**, pero no como producción Sevilla.

Esto significa que se permite cargar:

```text
Yelp business → place + place_source_ref
Yelp review   → review
```

siempre que el objetivo sea conectar artefactos IA y validar el flujo completo.

Pero esos datos no deben interpretarse como datos operativos de Sevilla ni como ranking final de barrios.

El ranking derivado de Yelp se marca como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 13. Encaje con el modelo de datos

Yelp se conecta con dos partes del modelo.

### 13.1. Capa core/prototipo

Para poder cargar menciones, sentimiento y señales IA, se importa el núcleo mínimo:

```text
business_id → place_source_ref.source_record_id → place_id
review_id   → review.source_review_id → review_id interno
```

Tablas usadas:

- `source_system`
- `source_run`
- `raw_asset`
- `place`
- `place_source_ref`
- `review`

### 13.2. Capa IA derivada

Los resultados del módulo IA se cargan en:

- `ai_model_version`
- `ai_pipeline_run`
- `dish`
- `dish_alias`
- `dish_mention`
- `dish_mention_sentiment`
- `dish_place_signal`
- `hidden_gem_candidate`

Esto permite consultar el ranking prototipo desde PostgreSQL sin contaminar la lógica productiva de Sevilla.

---

## 14. Flujo implementado de fuente Yelp

La vertical se ha implementado primero como un flujo por archivos y artefactos:

```text
Yelp TAR
→ profile TAR
→ extract selected files
→ profile JSONL
→ build food business subset
→ build food review subset
→ build NLP corpus
→ check NLP corpus
```

Después se añadió la integración IA:

```text
food_businesses.jsonl + food_reviews.jsonl
→ load_yelp_ai_core_reviews.py
→ place / place_source_ref / review
→ check_ai_downstream_import_readiness.py
→ load_ai_mentions_and_sentiment.py
→ dish_mention / dish_mention_sentiment
→ load_ai_signals_and_ranking.py
→ dish_place_signal / hidden_gem_candidate
→ check_ai_ranking_loaded.py
→ query_ai_ranking_demo.py
```

---

## 15. Scripts implementados de la vertical Yelp

### 15.1. Perfilado del TAR

```text
scripts/profile_yelp_tar.py
```

Comando:

```powershell
python -m scripts.profile_yelp_tar `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

---

### 15.2. Extracción controlada

```text
scripts/extract_yelp_selected_files.py
```

Comando:

```powershell
python -m scripts.extract_yelp_selected_files `
  --tar-path "data/external/yelp_open_dataset/yelp_dataset-001.tar" `
  --save-artifact
```

---

### 15.3. Perfilado de JSONL

```text
scripts/profile_yelp_jsonl_files.py
```

Comando:

```powershell
python -m scripts.profile_yelp_jsonl_files `
  --save-artifact
```

---

### 15.4. Subset de negocios gastronómicos

```text
scripts/build_yelp_food_business_subset.py
```

Comando:

```powershell
python -m scripts.build_yelp_food_business_subset `
  --min-review-count 1 `
  --save-artifact
```

---

### 15.5. Subset de reviews gastronómicas

```text
scripts/build_yelp_food_review_subset.py
```

Comando usado para la primera muestra:

```powershell
python -m scripts.build_yelp_food_review_subset `
  --max-lines 100000 `
  --min-text-length 40 `
  --save-artifact
```

---

### 15.6. Construcción del corpus NLP

```text
scripts/build_yelp_nlp_corpus.py
```

Comando:

```powershell
python -m scripts.build_yelp_nlp_corpus `
  --corpus-name yelp_food_reviews_corpus_sample_100k_lines `
  --min-text-length 80 `
  --max-text-length 5000 `
  --save-artifact
```

---

### 15.7. Check del corpus NLP

```text
scripts/check_yelp_nlp_corpus.py
```

Comando:

```powershell
python -m scripts.check_yelp_nlp_corpus `
  --corpus-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl `
  --save-artifact
```

---

## 16. Scripts implementados de integración IA con Yelp

### 16.1. Carga del núcleo Yelp para IA

```text
scripts/load_yelp_ai_core_reviews.py
```

Carga:

```text
food_businesses.jsonl → place + place_source_ref
food_reviews.jsonl    → review
```

Ejemplo:

```powershell
python -m scripts.load_yelp_ai_core_reviews `
  --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
  --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl
```

---

### 16.2. Check de preparación downstream

```text
scripts/check_ai_downstream_import_readiness.py
```

Verifica que:

- los `business_id` mapean a `place_id`;
- los `review_id` mapean a `review_id` interno;
- los nombres de platos mapean a `dish`;
- se puede cargar menciones, señales y ranking.

---

### 16.3. Carga de menciones y sentimiento

```text
scripts/load_ai_mentions_and_sentiment.py
```

Carga:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
→ dish_mention
→ dish_mention_sentiment
```

Resultado validado:

```text
mentions_upserted = 94.932
sentiments_upserted = 94.932
```

---

### 16.4. Carga de señales y ranking

```text
scripts/load_ai_signals_and_ranking.py
```

Carga:

```text
dish_business_ranking_candidates_v1.csv
→ dish_place_signal

hidden_gems_selected_candidates_v1.csv
→ hidden_gem_candidate
```

Resultado validado:

```text
signals_upserted = 31.036
hidden_gem_candidates_upserted = 622
```

---

### 16.5. Check final de ranking IA

```text
scripts/check_ai_ranking_loaded.py
```

Resultado validado:

```text
ready_for_querying_ai_ranking = true
orphan rows = 0
production_ready_candidates = 0
candidates_with_neighborhood = 0
```

---

### 16.6. Demo de consulta

```text
scripts/query_ai_ranking_demo.py
```

Permite consultar:

- top Hidden Gems prototipo;
- top candidatos por ciudad;
- top platos seleccionados;
- detalle de un candidato;
- menciones justificativas.

---

## 17. Resultados obtenidos de la vertical fuente

### 17.1. TAR

Perfilado inicial:

```text
member_file_count = 6
total_size_gb = 8.654
business = true
review = true
```

Archivos principales:

```text
business.json = 113.357 MB
review.json = 5094.403 MB
```

---

### 17.2. Subset de negocios gastronómicos

Resultado tras ajustar el filtro:

```text
processed_count = 150346
invalid_json_count = 0
kept_count = 66770
unique_business_id_count = 66770
```

El filtro inicial era demasiado permisivo y se ajustó para evitar falsos positivos como:

```text
Traditional Chinese Medicine
Doctors
Health & Medical
Barbers
Drugstores
```

---

### 17.3. Subset de reviews gastronómicas

Prueba sobre las primeras 100.000 líneas de `review.json`:

```text
processed_lines = 100000
invalid_json_count = 0
matched_business_count = 79922
kept_review_count = 79882
unique_review_id_count = 79882
unique_business_ids_with_reviews = 5150
skipped_missing_text_count = 0
skipped_short_text_count = 40
skipped_missing_business_metadata_count = 0
```

---

### 17.4. Corpus NLP final de muestra

Corpus generado:

```text
data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

Resultado validado:

```text
processed_count = 79270
invalid_json_count = 0
unique_document_id_count = 79270
unique_review_id_count = 79270
unique_business_id_count = 5141
duplicate_document_id_count = 0
duplicate_review_id_count = 0
```

Splits:

```text
train = 63540
validation = 7849
test = 7881
```

Labels derivados desde rating:

```text
positive = 54857
neutral = 9835
negative = 14578
```

Idioma:

```text
en = 79270
```

---

## 18. Resultados obtenidos de la integración IA

Tras la integración IA en PostgreSQL, el estado validado es:

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
```

Resumen de menciones:

```text
reviews_with_mentions = 42.461
places_with_mentions = 4.088
dishes_mentioned = 9.937
avg_ner_confidence = 0.97571
```

Resumen de ranking:

```text
ranking_scope = yelp_prototype
ranking_version = hidden_gems_ranking_v1
total_candidates = 622
selected_candidates = 622
min_score = 60.00283
avg_score = 66.86828
max_score = 82.92816
production_ready_rows = 0
```

La ausencia de candidatos productivos es intencionada, porque Yelp no representa Sevilla.

---

## 19. Estructura del documento NLP final

Cada línea del corpus final tiene una estructura como:

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

## 20. Sentimiento derivado desde rating

La etiqueta de sentimiento es una etiqueta débil derivada desde la puntuación:

| Rating | Label |
|---:|---|
| 4-5 | `positive` |
| 3 | `neutral` |
| 1-2 | `negative` |

Esta etiqueta se marca como débil:

```json
"label_is_weak": true,
"label_source": "rating_value"
```

No debe interpretarse como sentimiento lingüístico perfecto, sino como una señal inicial útil para entrenamiento o baseline.

---

## 21. Split determinista

El corpus usa split determinista a partir de `source_review_id`:

```text
80% train
10% validation
10% test
```

Esto permite regenerar el corpus y mantener la misma asignación de documentos sin depender de aleatoriedad.

---

## 22. Relación con el módulo IA

Yelp ha servido como base para desarrollar los módulos:

```text
Detector de platos
Normalizador de platos
Sentimiento por mención
Agregador de señales
Ranking Hidden Gems v1
```

El flujo validado es:

```text
Yelp reviews
→ dish NER
→ dish normalization
→ mention sentiment
→ dish-place signals
→ hidden_gem_candidate
→ vistas SQL
→ query demo
```

La documentación detallada del módulo IA está en:

```text
docs/10_ai_module/
docs/11_ai_integration/
```

---

## 23. Relación con Google Reviews

Google Reviews y Yelp no compiten; se complementan.

| Aspecto | Google Reviews | Yelp Open Dataset |
|---|---|---|
| Locales Sevilla | Sí | No |
| Enlace a `place` | Sí | Sí, pero prototipo externo |
| Enlace a barrio | Sí | No productivo |
| Uso operativo | Sí | No producción |
| Corpus IA | Sí, pequeño/local | Sí, amplio/externo |
| Idioma principal actual | Español | Inglés |
| Tabla destino | `review` operativa | `review` prototipo + corpus JSONL |
| Ranking | Futuro `sevilla_neighborhood` | Actual `yelp_prototype` |

Uso recomendado:

```text
Yelp corpus
→ entrenamiento amplio / baseline / prototipo

Google Reviews locales
→ adaptación, validación local y producción Sevilla
```

---

## 24. Consideraciones de volumen

Yelp tiene un volumen alto, por lo que la vertical se diseñó con lectura streaming y límites explícitos.

Reglas aplicadas:

- no cargar `review.json` completo en memoria;
- escanear por líneas;
- empezar con `--max-lines 100000`;
- construir un corpus de muestra antes de procesar millones de reviews;
- usar JSONL como formato intermedio;
- validar por summaries antes de escalar;
- cargar a PostgreSQL solo los subconjuntos necesarios para el prototipo IA.

---

## 25. Calidad y validación

La vertical valida:

### En el TAR

- existencia de ficheros esperados;
- tamaños;
- clasificación de miembros;
- extracción selectiva.

### En businesses

- JSON válido;
- `business_id`;
- categorías;
- filtrado gastronómico;
- IDs únicos.

### En reviews

- JSON válido;
- `review_id`;
- `business_id`;
- texto no vacío;
- longitud mínima;
- metadata de negocio completa;
- IDs únicos.

### En corpus NLP

- estructura de documento;
- campos requeridos;
- texto normalizado;
- idioma;
- rating;
- sentimiento derivado;
- split;
- elegibilidad de entrenamiento;
- metadata de negocio;
- ausencia de duplicados;
- ausencia de errores y warnings.

### En integración IA

- catálogo de platos cargado;
- modelos y runs IA registrados;
- mapping `business_id → place_id`;
- mapping `review_id → review_id interno`;
- mapping `canonical_dish_name_v2 → dish_id`;
- ausencia de huérfanos;
- ranking consultable;
- scope prototipo correcto.

---

## 26. Riesgos y limitaciones

### Riesgos

- Yelp no representa Sevilla;
- corpus mayoritariamente en inglés;
- posible sesgo geográfico hacia ciudades del dataset;
- sentimiento derivado desde rating es una etiqueta débil;
- categorías pueden ser mixtas;
- volumen elevado;
- no se deben publicar reseñas completas;
- el ranking actual puede parecer producto final si no se marca correctamente.

### Mitigaciones

- separar Yelp del ranking productivo de Sevilla;
- marcar `ranking_scope = yelp_prototype`;
- marcar `is_production_ready = false`;
- mantener JSONL local ignorado por Git;
- validar categories y filtros;
- usar muestras controladas;
- diferenciar Yelp de Google Reviews locales;
- documentar `label_is_weak`;
- documentar limitaciones del prototipo.

---

## 27. Estado actual

La fuente Yelp y su integración IA están implementadas y validadas.

Estado de la vertical fuente:

```text
[OK] TAR perfilado
[OK] Extracción selectiva business/review
[OK] JSONL profiling
[OK] Subset de negocios gastronómicos
[OK] Ajuste de filtros para reducir falsos positivos
[OK] Subset de reviews gastronómicas
[OK] Corpus NLP inicial
[OK] Check final del corpus
[OK] 79.270 documentos NLP válidos
[OK] 0 duplicados
[OK] 0 JSON inválidos
[OK] splits train/validation/test
[OK] labels positive/neutral/negative
[OK] metadata de negocio incluida
```

Estado de integración IA:

```text
[OK] Catálogo de platos cargado
[OK] Aliases de platos cargados
[OK] Núcleo Yelp para IA cargado en PostgreSQL
[OK] Menciones de platos cargadas
[OK] Sentimiento por mención cargado
[OK] Señales negocio/plato cargadas como dish_place_signal
[OK] Ranking yelp_prototype cargado como hidden_gem_candidate
[OK] Vistas SQL creadas
[OK] Script de demo de consultas funcional
[OK] Checks finales sin huérfanos
```

---

## 28. Fuera de alcance actual

No forma parte de esta fase:

- tratar Yelp como producción Sevilla;
- vincular Yelp con barrios de Sevilla como ranking final;
- marcar candidatos Yelp como `is_production_ready = true`;
- usar Yelp para sustituir Google Reviews locales;
- publicar reseñas completas;
- usar `tip.json`, `user.json` o `checkin.json`;
- crear API pública sobre ranking Yelp como si fuera producto final.

---

## 29. Próximos pasos

Siguientes pasos recomendados:

```text
1. Mantener documentación Yelp y docs/10_ai_module + docs/11_ai_integration actualizadas.
2. Crear export_reviews_for_ai.py para generar corpus IA desde hidden_gems.review.
3. Ejecutar piloto sobre Google Places Reviews reales de Sevilla.
4. Analizar idioma, volumen y calidad textual de reviews locales.
5. Decidir estrategia de adaptación a español/multilingüe.
6. Aplicar detección de platos y sentimiento a corpus local.
7. Generar señales por place + dish sobre Sevilla.
8. Activar ranking_scope = sevilla_neighborhood cuando haya datos suficientes.
```

---

## 30. Conclusión

Yelp Open Dataset queda integrado como fuente de apoyo IA dentro de Hidden Gems.

Su función no es alimentar directamente el ranking operativo de Sevilla, sino proporcionar un corpus amplio, estructurado y validado para desarrollar la inteligencia textual del proyecto.

El resultado actual no solo es un corpus NLP, sino una integración completa del prototipo IA en PostgreSQL:

```text
Yelp corpus
→ modelos/procesos IA
→ resultados persistidos
→ vistas SQL
→ demo consultable
```

Esta fase valida que Hidden Gems puede pasar de reseñas textuales a platos detectados, sentimientos, señales y ranking explicable. El siguiente reto es aplicar esa misma arquitectura a las reviews reales de Sevilla.
