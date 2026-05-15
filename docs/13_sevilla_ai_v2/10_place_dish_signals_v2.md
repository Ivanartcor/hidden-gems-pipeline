# 10. Señales place-dish v2

## 1. Propósito del documento

Este documento describe la construcción de la capa **place-dish signals v2**, que agrega menciones normalizadas y sentimiento ABSA a nivel de:

```text
place_id + dish_id
```

Esta capa es el puente entre los modelos de IA y el ranking Hidden Gems v2.

---

## 2. Objetivo de la capa

El objetivo es transformar menciones individuales en señales agregadas por local y plato.

Entrada:

```text
menciones de platos normalizadas con sentimiento ABSA
```

Salida:

```text
señales agregadas por local-plato
```

Ejemplo conceptual:

```text
Review 1 → croquetas en Bar X → positive
Review 2 → croquetas en Bar X → positive
Review 3 → croquetas en Bar X → neutral

→ Señal agregada:
Bar X + croquetas
mention_count = 3
review_count = 3
positive_ratio = 0.67
neutral_ratio = 0.33
negative_ratio = 0.00
weighted_sentiment_score = ...
```

---

## 3. Lugar en el pipeline IA v2

La capa se encuentra después de ABSA y antes del ranking:

```text
Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
→ Hidden Gems ranking v2
```

---

## 4. Script principal

Script:

```text
scripts/build_sevilla_place_dish_signals_v2.py
```

Este script:

```text
1. Lee menciones con sentimiento ABSA.
2. Filtra menciones usables.
3. Agrupa por place_id + dish_id.
4. Calcula métricas de evidencia, sentimiento, confianza y calidad.
5. Asigna tiers de evidencia y calidad.
6. Marca señales listas o no listas para ranking.
7. Genera salidas para análisis y ranking.
```

---

## 5. Entrada de la etapa

Archivo de entrada:

```text
data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
└── sevilla_dish_mentions_with_absa_sentiment_v1.jsonl
```

Granularidad:

```text
una fila por mención normalizada con sentimiento
```

Campos relevantes:

```text
review_id
place_id
place_name
dish_id
dish_display_name
district_id
district_name
neighborhood_id
neighborhood_name
selected_mention_text_v2
absa_sentiment_label_v1
absa_confidence_v1
sentiment_score_continuous_v1
normalization_confidence
source_strategy_v2
needs_manual_review
ready_for_downstream_sentiment
```

---

## 6. Salida de la etapa

Carpeta de salida:

```text
data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/
```

Archivos generados:

```text
sevilla_place_dish_signals_v2.csv
sevilla_place_dish_signals_v2.jsonl
sevilla_top_place_dish_signals_v2.csv
sevilla_place_dish_signals_by_district_v2.csv
sevilla_place_dish_signals_by_neighborhood_v2.csv
sevilla_place_dish_signals_by_dish_v2.csv
sevilla_place_dish_signals_manual_review_v2.csv
sevilla_place_dish_signal_tier_summary_v2.csv
sevilla_place_dish_signal_summary_v2.json
recommended_next_steps.md
```

Granularidad principal:

```text
una fila por combinación place_id + dish_id
```

---

## 7. Métricas calculadas

La capa genera métricas como:

```text
mention_count_v2
review_count_v2
weighted_mention_count_v2
positive_count_v2
neutral_count_v2
negative_count_v2
positive_ratio_v2
neutral_ratio_v2
negative_ratio_v2
weighted_sentiment_score_v2
avg_absa_confidence_v2
avg_normalization_confidence_v2
source_strategy_mix_json
normalization_quality
sentiment_quality
evidence_tier_v2
aggregate_quality_tier_v2
ready_for_ranking_v2
ranking_eligibility_reasons_v2
```

Estas métricas permiten que el ranking no dependa solo de una mención positiva aislada.

---

## 8. Pesos de calidad

El script pondera las menciones en función de su calidad.

Factores positivos:

```text
- estrategia hybrid_and_ner;
- alta confianza de normalización;
- alta confianza ABSA;
- varias reviews distintas;
- sentimiento positivo consistente;
- baja negatividad.
```

Factores penalizadores:

```text
- estrategia ner_only experimental;
- normalización con revisión;
- baja confianza ABSA;
- fragmentos dudosos;
- mención genérica o ambigua;
- ratio negativo alto;
- evidencia insuficiente.
```

---

## 9. Tiers de evidencia

La capa asigna un `evidence_tier_v2` según la cantidad y solidez de evidencia disponible.

| Tier | Interpretación |
|---|---|
| `weak` | Evidencia muy limitada. |
| `emerging` | Señal emergente, útil pero todavía no fuerte. |
| `solid` | Evidencia suficiente para ranking experimental. |
| `strong` | Evidencia relativamente robusta dentro del piloto. |

---

## 10. Tiers de calidad agregada

También se asigna `aggregate_quality_tier_v2`.

| Tier | Interpretación |
|---|---|
| `low` | Señal con baja calidad o muchas advertencias. |
| `medium` | Señal usable, pero no plenamente robusta. |
| `high` | Señal con buena confianza y consistencia. |
| `weak` | Señal insuficiente para ranking fuerte. |

Este tier combina confianza de modelos, revisión pendiente, evidencia y calidad del agregado.

---

## 11. Resultados obtenidos

Resultado general:

```text
input_rows: 2.965
usable_mention_rows: 2.880
place_dish_signals: 2.335
ready_for_ranking_signals: 276
not_ready_for_ranking_signals: 2.059
manual_review_rows: 2.075
unique_reviews: 1.461
unique_places: 638
unique_dishes: 182
districts: 12
neighborhoods: 95
```

La capa genera muchas señales, pero solo una parte se considera suficientemente sólida para ranking.

---

## 12. Distribución de evidencia

Distribución observada:

```text
weak: 1.969
emerging: 304
solid: 56
strong: 6
```

Esto confirma que gran parte del universo de señales tiene poca evidencia, lo cual es esperable en un piloto con número limitado de reseñas por local.

---

## 13. Calidad agregada

Distribución observada:

```text
weak: 2.021
medium: 229
high: 48
low: 37
```

La mayoría de señales quedan como `weak`, pero hay un conjunto suficiente de señales `medium` y `high` para construir el ranking v2.

---

## 14. Sentimiento agregado

La distribución de sentimiento en menciones fue:

```text
positive: 2.388
negative: 343
neutral: 149
```

El `weighted_sentiment_score_v2` tuvo una media positiva:

```text
mean: 0.6722
median: 0.9549
min: -0.9846
max: 0.9662
```

Esto refleja el sesgo positivo de las reseñas, por lo que el ranking debe equilibrar sentimiento con evidencia y calidad.

---

## 15. Señales destacadas

Algunas señales candidatas iniciales fueron:

```text
La Tontona Abacería → chicharrones
Taberna Juncal Tapas → torrija
La Taperia de Paco → ensaladilla
Taberna de Torneo → solomillo al whisky
Bar Los Compadres pool → churros
Deleite Sevilla → croqueta / pulpo / calamares
Casa Manolo Tapas Bar Sevillano → solomillo al whisky
```

Estas señales muestran que el sistema puede descubrir platos concretos asociados a locales y barrios, no solo restaurantes populares.

---

## 16. Criterios de preparación para ranking

Una señal puede marcarse como `ready_for_ranking_v2` si cumple condiciones como:

```text
- tener local y plato normalizados;
- tener suficiente evidencia mínima;
- no superar umbrales de negatividad;
- tener confianza suficiente;
- no depender únicamente de señales experimentales;
- no estar marcada como revisión crítica.
```

Las señales que no cumplen estos criterios siguen siendo útiles para análisis, pero no para ranking fuerte.

---

## 17. Relación con el ranking v2

El ranking Hidden Gems v2 usa esta capa como entrada directa:

```text
sevilla_place_dish_signals_v2.jsonl
→ build_sevilla_hidden_gems_ranking_v2.py
→ sevilla_hidden_gems_ranking_v2
```

La calidad del ranking depende de esta capa, porque aquí se decide qué evidencia existe para cada combinación local-plato.

---

## 18. Limitaciones

Limitaciones conocidas:

1. Muchas señales tienen poca evidencia.
2. Algunas señales se basan en solo dos reseñas.
3. El sentimiento de Google Reviews está sesgado hacia positivo.
4. La calidad depende de etapas anteriores: NER, normalización y ABSA.
5. Hay platos genéricos que pueden acumular señales fácilmente.
6. Algunas señales con buena puntuación todavía no deben considerarse producción.

---

## 19. Próximas mejoras

Mejoras recomendadas:

```text
- revisar señales weak con alto score;
- añadir umbrales más estrictos para producción;
- diferenciar platos genéricos de platos específicos;
- aumentar evidencia con más fuentes;
- introducir evaluación humana sobre señales top;
- añadir pesos por fiabilidad de fuente;
- mejorar deduplicación de reviews similares.
```

---

## 20. Conclusión

La capa `place_dish_signals_v2` convierte las predicciones de los modelos en señales agregadas listas para ranking.

Es una pieza fundamental porque permite pasar de menciones individuales a conocimiento explotable:

```text
qué plato destaca
en qué local
en qué barrio
con cuánta evidencia
con qué sentimiento
y con qué nivel de calidad.
```
