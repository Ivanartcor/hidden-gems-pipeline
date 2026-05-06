# `docs/34_yelp_source.md`

# Fuente de datos: Yelp Open Dataset

## 1. Descripción general

**Yelp Open Dataset** se incorpora a Hidden Gems Pipeline como una fuente externa de apoyo para el desarrollo de capacidades de análisis textual, reseñas y NLP.

A diferencia de Sevilla Geo, Overpass y Google Places, Yelp no se utiliza en esta fase como fuente operativa para descubrir locales de Sevilla ni como fuente directa para alimentar rankings finales por barrio. Su valor principal está en aportar un volumen amplio de negocios y reseñas gastronómicas para construir un **corpus de entrenamiento y validación NLP**.

La decisión actual del proyecto es tratar Yelp como:

```text
Yelp Open Dataset
→ dataset académico local
→ extracción controlada
→ subset gastronómico
→ corpus NLP
→ entrenamiento/evaluación futura
```

Y no como:

```text
Yelp Open Dataset
→ place operativo de Sevilla
→ review operativa vinculada a barrio
```

Esta separación mantiene limpio el modelo canónico de Hidden Gems y evita mezclar datos externos no locales con los datos operativos procedentes de Google Places y Google Reviews.

---

## 2. Rol dentro del pipeline

Yelp actúa como una **fuente de corpus textual gastronómico**.

Su papel actual es:

1. aportar negocios con categorías gastronómicas;
2. aportar reseñas asociadas a esos negocios;
3. permitir filtrar reseñas de contexto gastronómico;
4. generar un corpus JSONL preparado para NLP;
5. servir como base amplia para extracción de platos, análisis de sentimiento y señales textuales.

### Usos previstos

- limpieza y normalización textual;
- extracción de menciones de platos;
- análisis de sentimiento general;
- análisis de sentimiento asociado a platos;
- detección de recomendaciones;
- generación de datasets de entrenamiento, validación y test;
- comparación posterior con Google Reviews locales;
- pruebas iniciales con spaCy, reglas, diccionarios o modelos multilingües.

---

## 3. Diferencia respecto a las otras fuentes

| Fuente | Rol principal | Uso operativo en Sevilla | Uso NLP |
|---|---|---:|---:|
| Sevilla Geo | Referencia territorial oficial | Sí | No |
| Overpass / OSM | POIs gastronómicos abiertos | Sí | No directo |
| Google Places | Descubrimiento y enriquecimiento de locales | Sí | Parcial |
| Google Places Reviews | Reviews reales vinculadas a locales de Sevilla | Sí | Sí, corpus local |
| Yelp Open Dataset | Corpus externo de entrenamiento | No inicialmente | Sí |

La diferencia clave es que Google Reviews queda enlazado a:

```text
review → place → barrio → distrito
```

Mientras que Yelp queda inicialmente como:

```text
yelp_food_reviews_corpus → NLP training/evaluation
```

---

## 4. Restricciones de uso y tratamiento del dataset

Yelp Open Dataset se utiliza bajo un contexto académico y local del proyecto.

Reglas aplicadas en Hidden Gems Pipeline:

- no subir el dataset al repositorio;
- no compartir los ficheros originales;
- no publicar reseñas completas en documentación pública;
- no usar Yelp como fuente comercial de listados;
- no utilizar Yelp como sustituto de Google Places para locales de Sevilla;
- mantener el dataset en `data/external/`, excluido por `.gitignore`;
- documentar solo métricas, perfiles, summaries y artefactos derivados no sensibles.

Por este motivo, los ficheros grandes del dataset se tratan como **datos externos locales**, no como código ni como documentación versionable.

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

## 6. Archivos utilizados en esta fase

Para la primera versión de la vertical solo se utilizan:

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
```

La documentación, scripts y summaries ligeros pueden versionarse si no contienen contenido sensible o excesivo.

---

## 10. Source system recomendado

La fuente se identifica como:

```text
source_code = yelp_open_dataset
```

Definición conceptual:

```json
{
  "source_code": "yelp_open_dataset",
  "source_name": "Yelp Open Dataset",
  "source_type": "file_dataset",
  "description": "Dataset académico de Yelp usado como corpus externo para entrenamiento NLP gastronómico.",
  "base_url": "https://business.yelp.com/data/resources/open-dataset/",
  "auth_type": "none",
  "data_format_default": "jsonl",
  "refresh_mode_default": "snapshot",
  "supports_incremental": false,
  "is_active": true,
  "notes": "No se usa inicialmente como fuente operativa de locales de Sevilla; se usa para corpus NLP."
}
```

En esta primera fase se ha trabajado principalmente a nivel de archivos y artefactos, sin necesidad de importar masivamente el corpus a PostgreSQL.

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

La decisión actual es **no transformar Yelp Business en `place`** y **no insertar Yelp Reviews en `hidden_gems.review`**.

Motivo:

```text
hidden_gems.review está orientada a reseñas operativas vinculadas a place_id.
```

Google Reviews sí cumple esta condición:

```text
Google Review → place_source_ref Google → place → barrio
```

Yelp no debe forzar esta relación, porque sus negocios no representan locales de Sevilla ni están vinculados al modelo territorial oficial del proyecto.

Por tanto:

```text
Google Reviews → hidden_gems.review
Yelp Reviews → yelp_food_reviews_corpus.jsonl
```

Esta decisión evita crear `place` falsos o permitir reviews huérfanas dentro del modelo operativo.

---

## 13. Encaje con el modelo de datos

Yelp se mantiene como fuente externa de entrenamiento.

No obstante, sus documentos conservan trazabilidad mediante campos propios del corpus:

```text
source_system_code
source_dataset
source_entity_type
source_review_id
source_business_id
source_user_id
```

El corpus final incluye también metadata del negocio:

```text
business_name
city
state
stars_business
review_count_business
is_open
categories_list
food_category_tags
food_confidence
```

Esto permite usar Yelp para tareas NLP sin contaminar el modelo canónico de locales.

---

## 14. Flujo implementado

La vertical se ha implementado como un flujo por archivos y artefactos:

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

Cada fase genera summaries y checks para mantener trazabilidad y reproducibilidad.

---

## 15. Scripts implementados

### 15.1. Perfilado del TAR

```text
scripts/profile_yelp_tar.py
```

Objetivo:

- inspeccionar el TAR sin extraerlo completo;
- listar miembros;
- clasificar tipos de fichero;
- calcular tamaños;
- comprobar existencia de `business` y `review`.

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

Objetivo:

- extraer solo `business.json` y `review.json`;
- evitar path traversal;
- no extraer `user`, `checkin` ni `tip`;
- generar manifest con SHA-256 y tamaños.

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

Objetivo:

- perfilar `business.json` completo;
- perfilar una muestra de `review.json`;
- revisar campos, tipos, categorías, ratings, fechas y ejemplos;
- validar que los ficheros se leen correctamente.

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

Objetivo:

- leer `business.json`;
- filtrar negocios con categorías gastronómicas;
- generar `food_businesses.jsonl`;
- generar `food_business_ids.txt`;
- evitar falsos positivos claros como medicina, doctores, acupuntura o peluquerías;
- generar summary.

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

Objetivo:

- leer `review.json` en streaming;
- conservar solo reviews cuyo `business_id` esté en `food_business_ids.txt`;
- aplicar longitud mínima;
- enriquecer cada review con metadata del negocio;
- generar `food_reviews.jsonl`.

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

Objetivo:

- convertir `food_reviews.jsonl` en documentos NLP;
- limpiar texto;
- asignar idioma;
- derivar sentimiento débil desde rating;
- generar split determinista `train/validation/test`;
- incluir metadata de negocio;
- generar `yelp_food_reviews_corpus_sample_100k_lines.jsonl`.

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

Objetivo:

- validar estructura del corpus;
- verificar IDs únicos;
- comprobar splits;
- comprobar labels;
- comprobar ratings;
- comprobar idioma;
- comprobar metadata de negocio;
- comprobar ausencia de warnings y errores.

Comando:

```powershell
python -m scripts.check_yelp_nlp_corpus `
  --corpus-path data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl `
  --save-artifact
```

---

## 16. Resultados obtenidos

### 16.1. TAR

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

### 16.2. Subset de negocios gastronómicos

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

Tras el ajuste, los ejemplos y categorías quedaron alineados con negocios gastronómicos.

---

### 16.3. Subset de reviews gastronómicas

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

Esto confirmó que la mayoría de las primeras reviews pertenecen a negocios gastronómicos filtrados y que el proceso de matching por `business_id` funciona correctamente.

---

### 16.4. Corpus NLP final de muestra

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

Ratings:

```text
5.0 = 33241
4.0 = 21616
3.0 = 9835
2.0 = 6788
1.0 = 7790
```

Idioma:

```text
en = 79270
```

Longitud textual:

```text
min = 80
max = 4999
avg = 534.7568
```

Checks finales:

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

---

## 17. Estructura del documento NLP final

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
    "categories_list": [...],
    "food_category_tags": [...]
  },
  "source_metrics": {
    "useful_count": 0,
    "funny_count": 0,
    "cool_count": 0
  }
}
```

---

## 18. Sentimiento derivado desde rating

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

## 19. Split determinista

El corpus usa split determinista a partir de `source_review_id`:

```text
80% train
10% validation
10% test
```

Esto permite regenerar el corpus y mantener la misma asignación de documentos sin depender de aleatoriedad.

---

## 20. Relación con NLP futuro

Yelp queda preparado para las siguientes tareas:

```text
review text
→ limpieza
→ extracción de platos
→ sentimiento general
→ sentimiento por plato
→ señal de recomendación
```

Uso recomendado:

```text
Yelp corpus
→ entrenamiento amplio / baseline

Google Reviews locales
→ adaptación, validación local y aplicación operativa futura
```

---

## 21. Relación con Google Reviews

Google Reviews y Yelp no compiten; se complementan.

| Aspecto | Google Reviews | Yelp Open Dataset |
|---|---|---|
| Locales Sevilla | Sí | No |
| Enlace a `place` | Sí | No inicialmente |
| Enlace a barrio | Sí | No |
| Uso operativo | Sí | No inicialmente |
| Corpus NLP | Sí, pequeño/local | Sí, amplio/externo |
| Idioma principal actual | Español | Inglés |
| Tabla destino | `hidden_gems.review` | JSONL NLP corpus |

---

## 22. Consideraciones de volumen

Yelp tiene un volumen alto, por lo que la vertical se diseñó con lectura streaming y límites explícitos.

Reglas aplicadas:

- no cargar `review.json` completo en memoria;
- escanear por líneas;
- empezar con `--max-lines 100000`;
- construir un corpus de muestra antes de procesar millones de reviews;
- usar JSONL como formato intermedio;
- validar por summaries antes de escalar.

La primera versión validada trabaja con una muestra controlada de 100.000 líneas de `review.json`, de las que se obtuvieron 79.270 documentos NLP finales.

---

## 23. Calidad y validación

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

---

## 24. Riesgos y limitaciones

### Riesgos

- Yelp no representa Sevilla;
- corpus mayoritariamente en inglés;
- posible sesgo geográfico hacia ciudades del dataset;
- sentimiento derivado desde rating es una etiqueta débil;
- categorías pueden ser mixtas;
- volumen elevado;
- no se deben publicar reseñas completas.

### Mitigaciones

- separar Yelp del modelo operativo;
- trabajar como corpus NLP externo;
- mantener JSONL local ignorado por Git;
- validar categories y filtros;
- usar muestras controladas;
- diferenciar Yelp de Google Reviews locales;
- documentar `label_is_weak`.

---

## 25. Estado actual

La fuente Yelp ya no está pendiente de implementación inicial.

Estado actual:

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

---

## 26. Fuera de alcance actual

No forma parte de esta fase:

- importar Yelp masivamente a PostgreSQL;
- crear `place` canónicos desde Yelp;
- vincular Yelp con barrios de Sevilla;
- insertar Yelp en `hidden_gems.review`;
- entrenar modelos NLP;
- extraer platos automáticamente;
- calcular ranking por barrio;
- usar `tip.json`, `user.json` o `checkin.json`.

---

## 27. Próximos pasos

Siguientes pasos recomendados:

```text
1. Documentar la vertical Yelp en docs/44_vertical_yelp_open_dataset.md.
2. Hacer commit de scripts, summaries ligeros y documentación.
3. Mantener fuera de Git los JSONL pesados.
4. Diseñar la fase NLP 1.
5. Crear baseline de extracción de platos sobre el corpus Yelp.
6. Comparar después con Google Reviews locales en español.
```

---

## 28. Conclusión

Yelp Open Dataset queda integrado como fuente de apoyo NLP dentro de Hidden Gems Pipeline.

Su función no es alimentar directamente la aplicación ni el ranking operativo de Sevilla, sino proporcionar un corpus amplio, estructurado y validado para desarrollar la inteligencia textual del proyecto.

El resultado actual es un corpus inicial de 79.270 reviews gastronómicas, con splits de entrenamiento, validación y test, labels derivados de rating, metadata de negocio y checks completos.

Este corpus deja preparada la siguiente fase del proyecto:

```text
Yelp NLP corpus
→ limpieza textual
→ extracción de platos
→ sentimiento
→ señales de recomendación
→ transferencia/evaluación con Google Reviews locales
```
