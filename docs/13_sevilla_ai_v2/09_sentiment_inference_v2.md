# 09. Inferencia de sentimiento por mención / ABSA v2

## 1. Propósito del documento

Este documento describe la fase de inferencia de sentimiento por mención dentro de **Sevilla IA v2**.

El objetivo es asignar un sentimiento específico a cada mención de plato normalizada:

```text
mención de plato + contexto de reseña + plato normalizado
→ positive / neutral / negative
→ confianza
→ score continuo de sentimiento
```

Esta fase permite diferenciar el sentimiento hacia un plato concreto del sentimiento general de la reseña.

---

## 2. Problema que resuelve

En una reseña puede haber sentimientos distintos hacia platos diferentes:

```text
Las croquetas estaban increíbles, pero el arroz fue decepcionante.
```

La reseña completa podría parecer positiva o mixta, pero Hidden Gems necesita saber:

```text
croquetas → positive
arroz → negative
```

Por eso se entrena y aplica un modelo de tipo **ABSA** (*Aspect-Based Sentiment Analysis*), donde el aspecto es la mención de plato.

---

## 3. Lugar en el pipeline IA v2

La inferencia ABSA se ejecuta después de la normalización:

```text
Hybrid + NER candidates v2
→ Normalization reranker v1
→ Mention Sentiment ABSA v1
→ Place-dish signals v2
→ Ranking Hidden Gems v2
```

Su salida se utiliza para calcular métricas agregadas por local y plato:

```text
positive_count
neutral_count
negative_count
positive_ratio
negative_ratio
weighted_sentiment_score
avg_absa_confidence
```

---

## 4. Modelo utilizado

Modelo local:

```text
models/sevilla_mention_sentiment_absa_beto_v1/
```

Modelo base:

```text
dccuchile/bert-base-spanish-wwm-cased
```

Tipo de tarea:

```text
Sequence Classification multiclase
```

Clases:

```text
negative
neutral
positive
```

---

## 5. Entrada conceptual del modelo

La entrada del modelo combina:

```text
- mención detectada;
- plato normalizado;
- contexto local;
- rating de la reseña, si está disponible;
- nombre del local, si está disponible.
```

Ejemplo:

```text
Mención: croquetas
[SEP]
Plato normalizado: croqueta
[SEP]
Contexto local: Las croquetas estaban increíbles, pero el arroz fue decepcionante.
[SEP]
Rating: 5
[SEP]
Local: Bar ejemplo
```

Salida:

```text
positive / neutral / negative
```

con probabilidades por clase.

---

## 6. Script de inferencia

Script principal:

```text
scripts/run_sevilla_mention_sentiment_absa_v1.py
```

Este script:

```text
1. Lee las menciones normalizadas.
2. Carga el modelo ABSA.
3. Construye el input para cada mención.
4. Predice sentimiento y probabilidades.
5. Calcula confianza, margen y score continuo.
6. Marca filas de baja confianza o revisión.
7. Genera una capa lista para agregación place-dish.
```

---

## 7. Entrada de la etapa

Entrada principal:

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
└── sevilla_dish_mentions_normalized_reranker_v1.jsonl
```

Granularidad:

```text
una fila por mención normalizada
```

Campos relevantes:

```text
review_id
place_id
place_name
dish_id
dish_display_name
selected_mention_text_v2
context_sentence
review_text_raw
rating_value
normalization_status
normalization_confidence
needs_manual_review
```

---

## 8. Salida de la etapa

Carpeta de salida:

```text
data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
```

Archivos generados:

```text
sevilla_dish_mentions_with_absa_sentiment_v1.csv
sevilla_dish_mentions_with_absa_sentiment_v1.jsonl
sevilla_absa_sentiment_low_confidence_v1.csv
sevilla_absa_sentiment_not_ready_v1.csv
sevilla_absa_sentiment_summary_v1.json
recommended_next_steps.md
```

Granularidad de la salida principal:

```text
una fila por mención normalizada con sentimiento predicho
```

---

## 9. Columnas principales generadas

La inferencia añade columnas como:

```text
absa_sentiment_label_v1
absa_confidence_v1
absa_margin_v1
prob_negative_v1
prob_neutral_v1
prob_positive_v1
sentiment_score_continuous_v1
sentiment_status_v1
ready_for_downstream_sentiment
absa_needs_manual_review
absa_review_reasons
```

El `sentiment_score_continuous_v1` permite pasar de una etiqueta discreta a una señal numérica útil para ranking:

```text
positive → valor positivo
neutral → valor cercano a 0
negative → valor negativo
```

---

## 10. Resultados obtenidos

Resultado general:

```text
input_rows: 2.965
predicted_rows: 2.880
not_ready_rows: 85
ready_for_downstream_sentiment: 2.561
needs_manual_review: 404
unique_reviews: 1.473
unique_places: 639
unique_dishes: 197
```

Distribución de sentimiento:

```text
positive: 2.388
negative: 343
neutral: 149
```

Esta distribución es coherente con el sesgo habitual de reseñas públicas, donde predominan las valoraciones positivas.

---

## 11. Confianza del modelo

La confianza del modelo fue elevada:

```text
mean confidence: 0.9623
median confidence: 0.9712
min confidence: 0.3813
```

Esto indica que la mayoría de predicciones son claras. Aun así, se conservan los indicadores de baja confianza para evitar sobreinterpretar casos dudosos.

---

## 12. Estados finales de sentimiento

Distribución de estados:

```text
predicted: 2.561
predicted_needs_review: 289
not_ready_for_sentiment: 85
low_confidence: 30
```

Interpretación:

| Estado | Significado |
|---|---|
| `predicted` | Predicción válida y lista para downstream. |
| `predicted_needs_review` | Predicción generada, pero la fila arrastra señales revisables. |
| `low_confidence` | El modelo no tiene confianza suficiente. |
| `not_ready_for_sentiment` | La mención no tenía condiciones suficientes para inferencia. |

---

## 13. Motivos de revisión

Los principales motivos de revisión no provienen siempre del modelo ABSA, sino de etapas anteriores:

```text
normalization_needs_review + experimental_ner_only
normalization_needs_review + likely_fragment
normalization_status_linked_needs_review
```

Esto significa que muchas filas se marcan como revisables por dudas de extracción o normalización, no necesariamente por dudas de sentimiento.

---

## 14. Uso en las señales place-dish

La salida ABSA se usa para agregar señales por:

```text
place_id + dish_id
```

A partir de las menciones se calculan:

```text
positive_count
neutral_count
negative_count
positive_ratio
negative_ratio
avg_absa_confidence
weighted_sentiment_score
weighted_mention_count
ready_for_ranking
```

El sentimiento por mención permite que el ranking v2 sea más preciso que el ranking v1, que dependía en mayor medida de reglas y señales más débiles.

---

## 15. Ventajas frente al enfoque v1

El enfoque ABSA v2 mejora sobre el enfoque piloto porque:

```text
- clasifica el sentimiento hacia el plato, no hacia la reseña completa;
- distingue opiniones mixtas dentro de la misma reseña;
- puede detectar menciones negativas aunque el rating general sea alto;
- permite calcular ratios positivos/negativos por plato;
- genera confianza y margen de predicción;
- permite excluir o penalizar casos dudosos.
```

---

## 16. Decisión técnica

La capa se da por válida como:

```text
sevilla_mention_sentiment_absa_v1
```

y se considera entrada válida para:

```text
place_dish_signals_v2
```

La decisión se basa en:

```text
- inferencia completa sobre 2.880 menciones;
- alta confianza media;
- distribución razonable de etiquetas;
- salida compatible con agregación;
- trazabilidad de baja confianza y revisión.
```

---

## 17. Limitaciones

Limitaciones conocidas:

1. El modelo fue entrenado con mezcla de etiquetas manuales y weak labels.
2. Las reseñas públicas están sesgadas hacia lo positivo.
3. Algunos textos son ambiguos o irónicos.
4. El rating puede introducir sesgo si el contexto local es escaso.
5. Las predicciones dependen de que la mención y la normalización sean correctas.
6. Una predicción con alta confianza puede seguir siendo incorrecta en casos complejos.

---

## 18. Próximas mejoras

Mejoras recomendadas:

```text
- revisar errores en weak labels;
- añadir más ejemplos manuales de clase neutral y negative;
- calibrar umbrales por clase;
- comparar ABSA contra reglas híbridas anteriores;
- añadir evaluación humana sobre top candidatos;
- entrenar una versión v1.1 si se amplía el dataset.
```

---

## 19. Conclusión

La inferencia ABSA v2 aporta una mejora importante al pipeline Hidden Gems, porque transforma menciones normalizadas en señales de sentimiento específicas por plato.

Gracias a esta etapa, el ranking v2 puede priorizar platos con evidencia positiva real y penalizar señales con negatividad, baja confianza o revisión pendiente.
