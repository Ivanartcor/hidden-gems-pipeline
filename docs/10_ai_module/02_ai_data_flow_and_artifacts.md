# 02 — Flujo de datos y artefactos del módulo IA

## Objetivo del documento

Este documento describe el flujo completo de datos del módulo de IA de Hidden Gems.

El propósito es dejar claro:

- qué notebook ejecuta cada fase;
- qué entrada necesita;
- qué salida genera;
- qué artefactos son imprescindibles;
- qué archivos sirven solo para auditoría o revisión;
- cómo se encadenan los resultados.

---

## Flujo general

El flujo completo del módulo IA es:

```text
04_dish_detection_dataset_exploration
→ 05_dish_ner_dataset_builder
→ 06_dish_ner_transformer_training
→ 07_dish_ner_inference_and_mentions
→ 08_dish_normalization_and_catalog_builder
→ 09_dish_mention_sentiment_hybrid_v1
→ 10_dish_signal_aggregation
→ 11_hidden_gems_ranking_v1
```

Vista conceptual:

```text
Yelp food reviews
→ candidatos de platos
→ dataset BIO
→ modelo NER
→ menciones detectadas
→ menciones normalizadas
→ sentimiento por mención
→ señales agregadas
→ ranking Hidden Gems
```

---

## 1. Corpus base de reseñas

### Archivo de entrada principal

```text
yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

### Columnas relevantes

El corpus usado contiene columnas como:

```text
corpus_document_id
source_system_code
source_dataset
source_entity_type
source_review_id
source_business_id
source_user_id
text
text_normalized
language
rating_value
sentiment_label_from_rating
review_date
corpus_split
task_scope
is_training_eligible
quality_flags
business_metadata
source_metrics
created_at
```

### Distribución usada inicialmente

```text
train:      63.540
validation: 7.849
test:       7.881
```

Distribución de sentimiento general por rating:

```text
positive: 54.857
negative: 14.578
neutral:   9.835
```

---

## 2. Notebook 04 — Exploración de candidatos de platos

### Notebook

```text
04_dish_detection_dataset_exploration.ipynb
```

### Objetivo

Explorar el corpus y generar candidatos débiles de platos para construir un dataset de entrenamiento.

### Funciones principales

- analizar reseñas gastronómicas;
- extraer posibles menciones de platos;
- aplicar reglas de filtrado;
- identificar candidatos de alta calidad;
- preparar material para dataset BIO.

### Artefacto principal

```text
weak_dish_candidates_v2.jsonl
```

Este archivo contiene candidatos débiles de menciones de platos y se usa como entrada para construir el dataset BIO.

---

## 3. Notebook 05 — Construcción del dataset NER

### Notebook

```text
05_dish_ner_dataset_builder.ipynb
```

### Objetivo

Construir un dataset token-level en formato BIO para entrenar un modelo NER que detecte entidades `DISH`.

### Etiquetas

```text
O
B-DISH
I-DISH
```

### Versiones generadas

#### Smoke test

```text
Total documentos: 1.200
train: 900
validation: 150
test: 150
```

#### High quality

```text
Total documentos: 43.161
train: 34.182
validation: 4.502
test: 4.477
```

### Distribución aproximada de entidades en high quality

```text
media de entidades por documento: 2,27
docs con entidades train: 32.682
docs sin entidades train: 1.500
```

### Artefactos principales

```text
dish_ner_dataset_high_quality/
dish_ner_dataset_smoke_test/
```

---

## 4. Notebook 06 — Entrenamiento del modelo Dish NER Transformer

### Notebook

```text
06_dish_ner_transformer_training.ipynb
```

### Objetivo

Entrenar un modelo Transformer para detectar menciones de platos en reseñas.

### Entrada

```text
dataset BIO high quality
```

### Salida principal

```text
dish_ner_transformer_full/
```

Carpeta de modelo Hugging Face con archivos como:

```text
config.json
model.safetensors
tokenizer.json
tokenizer_config.json
vocab.txt
special_tokens_map.json
training_args.bin
```

### Métricas finales en test

```text
Entity precision: 0,9094
Entity recall:    0,9687
Entity F1:        0,9381
Token macro F1:   0,9211
Token weighted F1:0,9968
```

### Artefactos generados

```text
dish_ner_transformer_metrics_full.json
dish_ner_entity_error_analysis_full.json
dish_ner_test_predictions_readable_full.jsonl
dish_ner_manual_predictions_full.jsonl
dish_ner_transformer_full/
```

---

## 5. Notebook 07 — Inferencia NER y generación de menciones

### Notebook

```text
07_dish_ner_inference_and_mentions.ipynb
```

### Objetivo

Aplicar el modelo `Dish NER v1` sobre el corpus de reviews y generar una tabla estructurada de menciones de platos.

### Entradas

```text
dish_ner_transformer_full/
yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

### Salida principal

```text
dish_mentions_model_v1_full.jsonl
```

### Resultados de inferencia

```text
Reviews procesadas:       79.270
Menciones detectadas:     95.061
Reviews con menciones:    42.471
Reviews sin menciones:    36.799
Media menciones/review:   1,20
Confianza media:          0,9752
Reviews truncadas:        8.279
```

### Artefactos generados

```text
dish_mentions_model_v1_full.jsonl
dish_ner_inference_summary_full.json
dish_mentions_sample_random_full.jsonl
dish_mentions_sample_low_confidence_full.jsonl
dish_mentions_sample_top_mentions_full.jsonl
dish_ner_review_predictions_model_v1_full.jsonl
```

### Nota sobre archivo pesado

```text
dish_ner_review_predictions_model_v1_full.jsonl
```

puede ocupar alrededor de 500 MB. Es útil para auditoría profunda, pero no es imprescindible para las fases siguientes.

---

## 6. Notebook 08 — Normalización y catálogo de platos

### Notebook

```text
08_dish_normalization_and_catalog_builder.ipynb
```

### Objetivo

Convertir menciones textuales en platos normalizados y construir un catálogo semilla.

### Entrada

```text
dish_mentions_model_v1_full.jsonl
```

### Salida principal

```text
dish_mentions_normalized_v2.jsonl
```

### Versión v1

Resultados iniciales:

```text
Menciones totales:     95.061
Menciones normalizadas:94.303
Pendientes/excluidas:  758
Platos canónicos:      9.401
Aliases:               9.692
```

### Problemas detectados en v1

Ejemplos de singularización incorrecta:

```text
hummus → hummu
crab cakes → crab cak
wings → wing
ribs → rib
nachos → nacho
mashed potatoes → mashed potato
```

### Versión v2

La v2 corrigió estos problemas con overrides controlados.

Resultados:

```text
Menciones totales:       95.061
Menciones normalizadas:  94.932
Pendientes/excluidas:    129
Platos canónicos v2:     9.937
Aliases v2:              10.235
```

### Artefactos generados

```text
dish_mentions_normalized_v2.jsonl
dish_catalog_seed_v2.csv
dish_aliases_seed_v2.csv
dish_surface_forms_v2.csv
dish_normalization_summary_v2.json
dish_normalization_duplicate_candidates_v2.csv
```

---

## 7. Notebook 09 — Sentimiento por mención híbrido

### Notebook

```text
09_dish_mention_sentiment_hybrid_v1.ipynb
```

### Objetivo

Asignar sentimiento a cada mención normalizada de plato.

### Entrada

```text
dish_mentions_normalized_v2.jsonl
```

### Por qué no usar solo el rating

Una review puede mezclar opiniones:

```text
The service was terrible, but the pasta was delicious.
```

El rating general puede ser negativo o neutral, pero el plato `pasta` tiene sentimiento positivo.

### Enfoque utilizado

Se construyó un sistema híbrido:

- contexto local;
- frase donde aparece el plato;
- cláusula objetivo;
- léxico positivo/negativo;
- negaciones;
- conectores de contraste;
- rating como fallback;
- tiers de fiabilidad.

### Resultado final

```text
Menciones procesadas: 94.932
Positive:             43.142
Neutral:              45.366
Negative:              6.424
High reliability:     25.011
Medium reliability:   25.495
Low reliability:      44.426
Training candidates:  25.011
```

### Artefactos generados

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
dish_mention_sentiment_summary_hybrid_v1.json
dish_mention_sentiment_training_candidates_v1.jsonl
dish_mention_sentiment_sample_high_confidence_v1.jsonl
dish_mention_sentiment_sample_low_confidence_v1.jsonl
dish_mention_sentiment_sample_review_disagreement_v1.jsonl
dish_mention_sentiment_sample_mixed_evidence_v1.jsonl
dish_mention_sentiment_sample_random_v1.jsonl
```

---

## 8. Notebook 10 — Agregación de señales

### Notebook

```text
10_dish_signal_aggregation.ipynb
```

### Objetivo

Convertir menciones individuales con sentimiento en señales agregadas.

### Entrada

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

### Salidas principales

```text
dish_global_signals_v1.csv
dish_business_signals_v1.csv
dish_business_ranking_candidates_v1.csv
dish_global_ranking_signals_v1.csv
dish_signal_aggregation_summary_v1.json
dish_signal_scoring_summary_v1.json
```

### Agregaciones generadas

#### Global por plato

```text
dish_id_v2
canonical_dish_name_v2
mention_count
review_count
business_count
positive_ratio
negative_ratio
confidence_weighted_sentiment
```

#### Negocio + plato

```text
business_id
dish_id_v2
canonical_dish_name_v2
mention_count
review_count
positive_ratio
negative_ratio
confidence_weighted_sentiment
bayesian_sentiment_score
total_signal_weight
business_dish_evidence_tier
preliminary_ranking_score_v1
```

### Resultados

```text
Pares negocio-plato totales: 31.036
Ranking-ready v1:            3.841
Strong candidates:             645
Promising candidates:         1.021
Weak candidates:              1.223
Not ready:                   28.147
Pares ruidosos detectados:      806
Posibles bebidas:               359
```

---

## 9. Notebook 11 — Ranking Hidden Gems v1

### Notebook

```text
11_hidden_gems_ranking_v1.ipynb
```

### Objetivo

Construir el ranking final Hidden Gems v1 a partir de candidatos negocio-plato.

### Entradas

```text
dish_business_ranking_candidates_v1.csv
dish_global_ranking_signals_v1.csv
dish_signal_scoring_summary_v1.json
```

### Salidas principales

```text
hidden_gems_ranking_v1.csv
hidden_gems_selected_candidates_v1.csv
hidden_gems_top_candidates_v1.csv
hidden_gems_top_by_city_v1.csv
hidden_gems_top_by_state_v1.csv
hidden_gems_ranking_summary_v1.json
```

### Resultados finales

```text
Pares negocio-plato totales:          31.036
Candidatos base rankable:              3.841
Candidatos Hidden Gems seleccionados:    622
top_hidden_gem:                            2
strong_hidden_gem:                        50
promising_hidden_gem:                    182
exploratory_hidden_gem:                  388
```

### Top candidatos

```text
1. Sushi Ushi → sushi → 82,93
2. Taqueria Cuernavaca → tacos → 82,04
3. Blues City Deli → sandwich → 81,98
4. Surrey's Café & Juice Bar → shrimp → 81,90
5. Three Muses → steak → 81,74
```

---

## Cadena de artefactos principales

Resumen de artefactos imprescindibles:

```text
weak_dish_candidates_v2.jsonl
→ dish_ner_dataset_high_quality/
→ dish_ner_transformer_full/
→ dish_mentions_model_v1_full.jsonl
→ dish_mentions_normalized_v2.jsonl
→ dish_mentions_with_sentiment_hybrid_v1.jsonl
→ dish_business_ranking_candidates_v1.csv
→ hidden_gems_selected_candidates_v1.csv
```

---

## Artefactos que conviene conservar

### Modelos

```text
dish_ner_transformer_full/
```

### Datasets procesados

```text
dish_mentions_model_v1_full.jsonl
dish_mentions_normalized_v2.jsonl
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

### Resultados finales

```text
dish_business_ranking_candidates_v1.csv
hidden_gems_ranking_v1.csv
hidden_gems_selected_candidates_v1.csv
hidden_gems_top_candidates_v1.csv
hidden_gems_ranking_summary_v1.json
```

### Auditoría

```text
dish_ner_entity_error_analysis_full.json
dish_normalization_duplicate_candidates_v2.csv
dish_mention_sentiment_sample_low_confidence_v1.jsonl
dish_mention_sentiment_sample_review_disagreement_v1.jsonl
hidden_gems_sample_not_selected_high_score_v1.csv
```

---

## Recomendación de almacenamiento

No todos los artefactos deberían estar versionados en GitHub.

### Sí versionar

```text
notebooks
documentación
resúmenes JSON
CSV finales ligeros
muestras pequeñas
```

### No versionar directamente si son pesados

```text
modelos completos
predicciones token-level completas
datasets JSONL grandes
archivos de cientos de MB
```

Para artefactos pesados se recomienda usar:

- Kaggle Datasets;
- Google Drive;
- Hugging Face Hub;
- releases externas;
- almacenamiento cloud.
