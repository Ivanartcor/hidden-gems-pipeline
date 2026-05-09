# 44. Vertical Yelp Open Dataset

## 1. Objetivo de la vertical

La vertical **Yelp Open Dataset** tiene como objetivo transformar un snapshot local de Yelp en un corpus gastronómico útil para las fases de IA de Hidden Gems.

En la primera etapa, la vertical construyó un corpus externo de reseñas gastronómicas en formato JSONL para entrenamiento, validación y experimentación NLP.

En una segunda etapa, ese corpus se utilizó para desarrollar e integrar el módulo IA de Hidden Gems en PostgreSQL, incluyendo:

```text
detección de platos
normalización de platos
sentimiento por mención
señales agregadas por local + plato
ranking prototipo de Hidden Gems
```

La decisión clave se mantiene: **Yelp no representa datos productivos de Sevilla**. Su función es servir como corpus amplio y prototipo IA. Los resultados cargados en base de datos se marcan como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 2. Papel de Yelp dentro de Hidden Gems

La estrategia global diferencia entre fuente operativa local y corpus externo:

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
→ entrenamiento, validación e integración prototipo IA
→ no producción Sevilla
```

Por tanto, Yelp tiene dos usos controlados:

| Uso | Resultado | Naturaleza |
|---|---|---|
| Corpus NLP | JSONL de reviews gastronómicas | Entrenamiento / experimentación |
| Prototipo IA integrado | Tablas IA en PostgreSQL | Validación técnica de extremo a extremo |

---

## 3. Decisión actual: Yelp sí se importa, pero solo como prototipo IA

La documentación inicial de la vertical definía Yelp como un corpus externo no importado en PostgreSQL. Esa decisión fue correcta para la primera fase de construcción del corpus.

Tras desarrollar el módulo IA, se tomó una decisión adicional: importar un subconjunto controlado de Yelp en PostgreSQL para poder conectar los resultados IA con las entidades reales del modelo:

```text
Yelp business_id
→ place_source_ref
→ place

Yelp review_id
→ review.source_review_id
→ review
```

Esta importación **no convierte Yelp en fuente productiva de Sevilla**. Su finalidad es permitir que las tablas IA no queden huérfanas y validar el flujo completo:

```text
review
→ dish_mention
→ dish_mention_sentiment
→ dish_place_signal
→ hidden_gem_candidate
```

Reglas aplicadas:

```text
1. Yelp se carga como prototipo IA, no como producción Sevilla.
2. Yelp no debe usarse para ranking real por barrio de Sevilla.
3. Los candidatos derivados se marcan como yelp_prototype.
4. Los candidatos no son production_ready.
5. La adaptación productiva deberá hacerse después con Google Reviews locales.
```

---

## 4. Restricciones de uso y tratamiento del dataset

El Yelp Open Dataset se trata como recurso local para uso académico y experimental.

Reglas adoptadas:

```text
1. No subir el dataset original al repositorio.
2. No compartir ficheros originales.
3. No exponer públicamente reviews individuales.
4. No usar Yelp como fuente comercial.
5. No usar Yelp como sustituto de Google Places para Sevilla.
6. Mantener ficheros grandes fuera de Git.
7. Trabajar mediante subsets, summaries y artefactos controlados.
8. Marcar cualquier ranking derivado como prototipo.
```

---

## 5. Estructura local de carpetas

Estructura usada para la vertical y la integración IA:

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
    ├── nlp_corpus/
    │   ├── yelp_food_reviews_corpus_sample_100k_lines.jsonl
    │   └── yelp_food_reviews_corpus_sample_100k_lines_summary.json
    │
    ├── yelp_open_dataset_qa/
    │   └── checks y summaries de la vertical
    │
    └── ai/
        ├── normalization/
        ├── sentiment/
        ├── aggregation/
        ├── ranking/
        └── checks/
```

---

## 6. Reglas de `.gitignore`

Los ficheros grandes deben quedar fuera de Git:

```gitignore
# Yelp Open Dataset - local large files
data/external/yelp_open_dataset/
data/staging/yelp_open_dataset/*.jsonl
data/staging/yelp_open_dataset/*.txt
data/staging/yelp_open_dataset/*.json
data/artifacts/nlp_corpus/*.jsonl

# AI large artifacts
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
```

Los scripts, documentación y summaries pequeños pueden versionarse cuando no contengan contenido sensible ni reviews completas.

---

## 7. Ficheros del TAR original

El dataset local se recibió como:

```text
data/external/yelp_open_dataset/yelp_dataset-001.tar
```

Miembros principales detectados:

| Fichero | Tipo | Tamaño aproximado |
|---|---:|---:|
| `Dataset_User_Agreement.pdf` | documentación | 0.077 MB |
| `yelp_academic_dataset_business.json` | business | 113.357 MB |
| `yelp_academic_dataset_checkin.json` | checkin | 273.665 MB |
| `yelp_academic_dataset_review.json` | review | 5094.403 MB |
| `yelp_academic_dataset_tip.json` | tip | 172.238 MB |
| `yelp_academic_dataset_user.json` | user | 3207.520 MB |

Para esta vertical se utilizaron únicamente:

```text
yelp_academic_dataset_business.json
yelp_academic_dataset_review.json
```

---

## 8. Naturaleza JSON Lines del dataset

Los ficheros de Yelp se tratan como **JSON Lines**:

```text
1 línea = 1 objeto JSON
```

Por tanto, la lectura debe hacerse en streaming:

```python
for line in file:
    row = json.loads(line)
```

No debe usarse `json.load(file)` sobre `review.json`, porque el fichero pesa varios GB.

---

## 9. Scripts de la vertical de datos Yelp

La vertical original de datos se divide en scripts reproducibles:

| Script | Propósito |
|---|---|
| `scripts/profile_yelp_tar.py` | Perfilar el `.tar` sin extraerlo completo |
| `scripts/extract_yelp_selected_files.py` | Extraer de forma segura `business.json` y `review.json` |
| `scripts/profile_yelp_jsonl_files.py` | Perfilar JSONL de business/review |
| `scripts/build_yelp_food_business_subset.py` | Filtrar negocios gastronómicos |
| `scripts/build_yelp_food_review_subset.py` | Filtrar reviews gastronómicas |
| `scripts/build_yelp_nlp_corpus.py` | Construir corpus NLP final |
| `scripts/check_yelp_nlp_corpus.py` | Validar el corpus NLP generado |

---

## 10. Flujo de construcción del corpus

El flujo construido es:

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

Resultado principal:

```text
data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

---

## 11. Resultados del corpus NLP inicial

Resultado validado:

```text
processed_count = 79.882
invalid_json_count = 0
skipped_short_text_count = 612
kept_count = 79.270
unique_document_id_count = 79.270
unique_review_id_count = 79.270
unique_business_id_count = 5.141
```

Splits:

```text
train = 63.540
validation = 7.849
test = 7.881
```

Etiquetas débiles derivadas desde rating:

```text
positive = 54.857
neutral = 9.835
negative = 14.578
```

Idioma:

```text
language = en
```

---

## 12. Estructura del documento del corpus

Cada documento contiene campos como:

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
    "label_is_weak": true,
    "label_source": "rating_value"
  },
  "business_metadata": {},
  "source_metrics": {}
}
```

---

## 13. Etiqueta débil de sentimiento

La etiqueta inicial de sentimiento se deriva de `rating_value`:

```text
rating >= 4 → positive
rating = 3  → neutral
rating <= 2 → negative
```

Esta etiqueta no es anotación humana. Se utiliza como señal débil para entrenamiento o baseline.

---

## 14. Fase IA desarrollada sobre Yelp

Después de construir el corpus, se desarrolló una fase IA completa con notebooks y artefactos derivados.

Módulos principales:

```text
1. Sentimiento general de review
2. Dataset de detección de platos
3. Entrenamiento NER de platos
4. Inferencia de menciones de platos
5. Normalización de platos
6. Sentimiento por mención
7. Agregación de señales por negocio + plato
8. Ranking Hidden Gems prototipo
```

Resultados principales:

```text
dish_catalog_seed_v2.csv
dish_aliases_seed_v2.csv
dish_mentions_with_sentiment_hybrid_v1.jsonl
dish_business_ranking_candidates_v1.csv
hidden_gems_selected_candidates_v1.csv
```

---

## 15. Integración IA en PostgreSQL

Para validar el flujo de extremo a extremo, se creó una capa IA en PostgreSQL mediante:

```text
db/ddl/07_ai_module.sql
db/ddl/08_ai_views.sql
```

Tablas principales:

```text
ai_model_version
ai_pipeline_run
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Vistas principales:

```text
vw_ai_hidden_gems_yelp_top
vw_ai_hidden_gem_candidate_detail
vw_ai_dish_mentions_with_sentiment
vw_ai_hidden_gems_place_summary
vw_ai_hidden_gems_dish_summary
vw_ai_hidden_gems_city_summary
```

---

## 16. Scripts de integración IA relacionados con Yelp

Scripts principales:

| Script | Propósito |
|---|---|
| `scripts/load_ai_dish_catalog.py` | Cargar catálogo de platos y aliases |
| `scripts/check_ai_dish_catalog.py` | Validar catálogo IA cargado |
| `scripts/load_yelp_ai_core_reviews.py` | Cargar businesses/reviews Yelp como puente prototipo |
| `scripts/check_ai_downstream_import_readiness.py` | Validar mapeos review/place/dish antes de cargar IA downstream |
| `scripts/load_ai_mentions_and_sentiment.py` | Cargar menciones y sentimiento por mención |
| `scripts/load_ai_signals_and_ranking.py` | Cargar señales y ranking prototipo |
| `scripts/check_ai_ranking_loaded.py` | Validar integridad final del ranking IA |
| `scripts/query_ai_ranking_demo.py` | Consultar vistas IA de demo |

---

## 17. Carga prototipo de Yelp en base de datos

Para evitar resultados IA huérfanos, se cargó el núcleo Yelp usado por el corpus:

```text
food_businesses.jsonl → place + place_source_ref
food_reviews.jsonl    → review
```

Esta carga permite resolver:

```text
business_id → place_id
review_id   → review_id interno
canonical_dish_name → dish_id
```

Después de esta carga, los checks confirmaron que era seguro importar:

```text
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

---

## 18. Resultados IA integrados

La integración final en PostgreSQL dejó cargado:

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
```

El ranking está listo para consulta como prototipo:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

No hay candidatos productivos de Sevilla todavía.

---

## 19. Consulta de demo

Tras crear `08_ai_views.sql`, el ranking puede consultarse con:

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_yelp_top
LIMIT 20;
```

También se puede usar el script:

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

O consultar un caso concreto:

```powershell
python -m scripts.query_ai_ranking_demo `
  --place-name "Sushi Ushi" `
  --dish-name "sushi" `
  --include-mentions
```

---

## 20. Relación con Google Reviews locales

Yelp ya ha cumplido su función de corpus amplio y prototipo IA.

La siguiente fase no consiste en seguir ampliando Yelp, sino en adaptar el flujo a datos locales:

```text
Google Places Reviews
→ reviews reales de Sevilla
→ export_reviews_for_ai.py
→ detección de platos
→ sentimiento por mención
→ señales por place + dish
→ ranking por barrio
```

La diferencia clave será:

| Aspecto | Yelp Prototype | Sevilla Production |
|---|---|---|
| Fuente | Yelp Open Dataset | Google Places Reviews |
| Idioma dominante | Inglés | Español |
| Geografía Sevilla | No | Sí |
| Barrio / distrito | No productivo | Sí |
| Ranking scope | `yelp_prototype` | `sevilla_neighborhood` |
| Production ready | No | Futuro |

---

## 21. Fuera de alcance actual

No forma parte de esta vertical:

```text
1. Usar Yelp como ranking real de Sevilla.
2. Usar Yelp como sustituto de Google Places.
3. Publicar reviews individuales.
4. Marcar candidatos Yelp como producción.
5. Vincular Yelp a barrios sevillanos.
6. Entrenar el modelo final español de producción.
7. Desplegar API pública o dashboard final.
```

---

## 22. Estado actual

La vertical Yelp y su integración IA quedan cerradas en estado validado:

```text
[OK] TAR perfilado
[OK] Extracción selectiva business/review
[OK] JSONL profiling
[OK] Food businesses subset
[OK] Food reviews subset
[OK] Corpus NLP generado
[OK] Corpus NLP validado
[OK] Modelos y artefactos IA generados
[OK] Catálogo dish/dish_alias cargado
[OK] Core Yelp prototype cargado en PostgreSQL
[OK] Menciones y sentimiento cargados
[OK] Señales y ranking cargados
[OK] Vistas IA creadas
[OK] Demo de consultas funcional
[OK] Ranking marcado como yelp_prototype
[OK] Sin production_ready candidates
```

---

## 23. Próximos pasos recomendados

Los siguientes pasos ya no pertenecen a Yelp, sino a la adaptación local:

```text
1. Crear export_reviews_for_ai.py.
2. Exportar Google Reviews locales desde hidden_gems.review.
3. Analizar idioma, volumen y calidad de reseñas de Sevilla.
4. Adaptar reglas y modelos al español.
5. Procesar reviews locales con la capa IA.
6. Calcular dish_place_signal para Sevilla.
7. Generar hidden_gem_candidate con ranking_scope = sevilla_neighborhood.
8. Marcar candidatos productivos solo tras validación manual y técnica.
```

---

## 24. Conclusión

La vertical Yelp Open Dataset ha pasado de ser un flujo de construcción de corpus a convertirse en la base experimental completa del módulo IA de Hidden Gems.

Su valor principal ha sido permitir desarrollar, probar e integrar el flujo completo:

```text
reviews gastronómicas
→ detección de platos
→ normalización
→ sentimiento por mención
→ señales agregadas
→ ranking Hidden Gems
→ consultas SQL
```

El resultado no debe interpretarse como ranking real de Sevilla, sino como una validación técnica sólida de la arquitectura IA.

La siguiente fase del proyecto será trasladar este flujo a Google Reviews locales para producir rankings reales por barrio dentro de Sevilla.
