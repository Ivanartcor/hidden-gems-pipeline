# 06. Modelo 2: sentimiento por mención / ABSA

## 1. Objetivo del modelo

El **Modelo 2** de la fase Sevilla IA v2 tiene como objetivo clasificar el sentimiento hacia una mención concreta de plato dentro de una reseña.

Esta tarea se conoce como **ABSA** (*Aspect-Based Sentiment Analysis*), porque no se analiza el sentimiento global de la reseña, sino el sentimiento hacia un aspecto específico: el plato mencionado.

Ejemplo:

```text
Reseña: "Las croquetas estaban increíbles, pero el arroz fue decepcionante."
```

Salida esperada:

| Mención | Sentimiento |
|---|---|
| croquetas | positive |
| arroz | negative |

Esto es mucho más útil para Hidden Gems que una clasificación global de reseña, porque una reseña puede hablar positivamente de un plato y negativamente de otro.

---

## 2. Problema que resuelve

En versiones previas, el sentimiento podía inferirse de forma débil mediante reglas, rating global o palabras cercanas. Esa aproximación tenía limitaciones:

- el rating general del restaurante no siempre refleja el plato concreto;
- una reseña puede contener sentimientos mixtos;
- algunas menciones son neutras o descriptivas;
- las reglas no capturan bien negaciones, matices o contraste;
- frases como "no estaba mal" son difíciles con reglas simples.

El modelo ABSA permite estimar el sentimiento específico de cada mención normalizada.

---

## 3. Clases de salida

El modelo clasifica cada mención en una de tres clases:

| Clase | Significado |
|---|---|
| `negative` | La mención expresa una valoración negativa del plato. |
| `neutral` | La mención es descriptiva, ambigua o sin valoración clara. |
| `positive` | La mención expresa una valoración positiva del plato. |

Además, en inferencia se calculan probabilidades y confianza para poder filtrar o ponderar señales de baja seguridad.

---

## 4. Modelo base

Se utilizó el mismo modelo base que en el resto de modelos de texto de la fase:

```text
dccuchile/bert-base-spanish-wwm-cased
```

La tarea se configuró como **sequence classification** con tres clases.

Entrada conceptual:

```text
Mención: croquetas de jamón [SEP]
Plato normalizado: croqueta de jamón [SEP]
Contexto local: Las croquetas de jamón estaban espectaculares. [SEP]
Rating: 5
```

Salida:

```text
positive
```

---

## 5. Dataset de entrenamiento

Se utilizó el dataset extendido:

```text
sevilla_mention_sentiment_annotation_dataset_v1_extended.jsonl
```

Resumen:

| Métrica | Valor |
|---|---:|
| Filas totales | 5.200 |
| Filas usables | 5.200 |

Distribución global de etiquetas:

| Clase | Filas |
|---|---:|
| `positive` | 3.105 |
| `negative` | 1.104 |
| `neutral` | 991 |

Fuentes de etiqueta:

| Fuente | Filas |
|---|---:|
| `weak_hybrid` | 2.911 |
| `manual_gold` | 2.289 |

El dataset combina etiquetas débiles y etiquetas manuales. Las etiquetas manuales tienen mayor fiabilidad, mientras que las etiquetas débiles permiten ampliar cobertura.

---

## 6. Construcción del input

Para cada fila se construyó un texto de entrada con información contextual:

```text
Mención: <texto de la mención>
[SEP] Plato normalizado: <plato canónico>
[SEP] Contexto local: <frase o ventana de contexto>
[SEP] Rating: <valor si está disponible>
[SEP] Local: <nombre del local>
```

El objetivo era que el modelo aprendiera a interpretar el sentimiento local de la mención, pero sin depender exclusivamente del rating general.

Se priorizó el contexto cercano a la mención, porque el texto completo de la reseña puede introducir ruido.

---

## 7. Estrategia de split

El split de entrenamiento se hizo agrupando por `review_id` para evitar fuga de información.

Esto significa que menciones de una misma reseña no se reparten entre train, validation y test.

Motivo:

```text
Si una reseña aparece parcialmente en train y parcialmente en test, el modelo podría memorizar contexto.
```

Agrupar por reseña produce una evaluación más realista.

---

## 8. Entrenamiento

Elementos principales:

| Elemento | Valor |
|---|---|
| Modelo base | `dccuchile/bert-base-spanish-wwm-cased` |
| Tipo de tarea | Sequence classification |
| Clases | negative, neutral, positive |
| Entorno | Kaggle Notebook con GPU |
| Métrica principal | Macro F1 |
| Pérdida | Cross entropy ponderada |
| Pesos | Pesos por clase + pesos por fuente de etiqueta |

Se utilizaron pesos para compensar el desbalance de clases y para dar mayor importancia a las etiquetas manuales frente a las débiles.

---

## 9. Resultados del entrenamiento

Resultados principales en test:

| Métrica | Valor |
|---|---:|
| Accuracy | 0,9472 |
| Macro precision | 0,9404 |
| Macro recall | 0,9310 |
| Macro F1 | 0,9353 |
| Weighted F1 | 0,9470 |

Resultados por clase:

| Clase | F1 |
|---|---:|
| `negative` | 0,9259 |
| `neutral` | 0,9158 |
| `positive` | 0,9643 |

La clase `neutral`, que suele ser la más difícil, obtuvo un resultado sólido.

---

## 10. Matriz de confusión

Matriz de confusión en test:

| Gold / Pred | negative | neutral | positive |
|---|---:|---:|---:|
| `gold_negative` | 100 | 1 | 6 |
| `gold_neutral` | 4 | 87 | 7 |
| `gold_positive` | 5 | 4 | 297 |

Interpretación:

- Los positivos se detectan con mucha fiabilidad.
- Los negativos se detectan bien.
- Los neutrales también se comportan correctamente.
- Los errores se concentran en fronteras semánticas normales: neutral vs positive, negative vs positive y matices suaves.

---

## 11. Evaluación por fuente de etiqueta

El modelo tuvo un rendimiento especialmente alto sobre etiquetas manuales.

Resumen cualitativo:

| Fuente | Interpretación |
|---|---|
| `manual_gold` | Muy alta fiabilidad. |
| `weak_hybrid` | Métricas inferiores por ruido en las etiquetas débiles. |

En varios errores sobre `weak_hybrid`, el modelo parecía corregir una etiqueta débil discutible.

Ejemplo conceptual:

```text
Texto: "El tataki de atún estaba riquísimo."
Etiqueta débil: negative
Predicción modelo: positive
```

En estos casos, la predicción del modelo puede ser más razonable que la etiqueta débil.

---

## 12. Inferencia local

El modelo se aplica localmente mediante:

```text
scripts/run_sevilla_mention_sentiment_absa_v1.py
```

Entrada principal:

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
└── sevilla_dish_mentions_normalized_reranker_v1.jsonl
```

Salida principal:

```text
data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
├── sevilla_dish_mentions_with_absa_sentiment_v1.csv
├── sevilla_dish_mentions_with_absa_sentiment_v1.jsonl
├── sevilla_absa_sentiment_low_confidence_v1.csv
├── sevilla_absa_sentiment_not_ready_v1.csv
└── sevilla_absa_sentiment_summary_v1.json
```

---

## 13. Resultados de inferencia

Al aplicar el modelo sobre las menciones normalizadas se obtuvo:

| Métrica | Valor |
|---|---:|
| Filas de entrada | 2.965 |
| Filas predichas | 2.880 |
| Filas no listas | 85 |
| Listas para downstream | 2.561 |
| Reviews únicas | 1.473 |
| Locales únicos | 639 |
| Platos únicos | 197 |

Distribución de sentimiento predicho:

| Sentimiento | Filas |
|---|---:|
| `positive` | 2.388 |
| `negative` | 343 |
| `neutral` | 149 |

La distribución positiva es esperable en reseñas públicas, especialmente en reseñas de Google, pero ahora la señal está calculada por mención concreta y no solo por rating global.

---

## 14. Uso en señales place-dish

La salida del modelo ABSA se utiliza para construir métricas agregadas por local y plato:

```text
place_id + dish_id
```

Métricas derivadas:

```text
positive_count
neutral_count
negative_count
positive_ratio
negative_ratio
avg_absa_confidence
weighted_sentiment_score_v2
```

Estas métricas alimentan el ranking Hidden Gems v2.

---

## 15. Limitaciones

Limitaciones principales:

- las reseñas públicas suelen estar sesgadas hacia positivo;
- algunas etiquetas débiles pueden ser ruidosas;
- la clase neutral puede ser ambigua;
- el modelo depende de que la mención y la normalización sean correctas;
- no debe usarse para valorar el restaurante completo;
- una predicción de sentimiento no equivale a evidencia suficiente para ranking.

---

## 16. Decisión final

El modelo ABSA se considera válido como:

```text
Modelo 2 — Mention Sentiment / ABSA v1
```

Su papel dentro del pipeline es:

```text
mención normalizada
→ sentimiento hacia el plato
→ señal ponderada local-plato
→ ranking Hidden Gems v2
```

La decisión final fue integrarlo como fuente principal de sentimiento en la fase IA v2, manteniendo filtros de confianza y revisión para evitar sobreinterpretar señales débiles.
