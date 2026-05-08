# 06 - Agregación de señales gastronómicas

## 1. Objetivo del módulo

El objetivo de este módulo es transformar menciones individuales de platos en señales agregadas útiles para ranking.

Hasta este punto, el sistema ya dispone de menciones con:

- plato detectado;
- plato normalizado;
- negocio asociado;
- sentimiento por mención;
- score de sentimiento;
- confianza del NER;
- confianza del sentimiento;
- tier de fiabilidad.

La agregación convierte esa información granular en métricas por:

```text
plato global
plato + negocio
```

Estas tablas son la base directa del ranking Hidden Gems.

---

## 2. Papel dentro del flujo de IA

La agregación se sitúa entre el sentimiento por mención y el ranking final:

```text
reviews
→ Dish NER
→ normalización
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

Sin esta fase, el ranking tendría que trabajar con menciones individuales, lo cual sería ruidoso e inestable. La agregación resume la evidencia acumulada.

---

## 3. Notebook implicado

| Notebook | Función |
|---|---|
| `10_dish_signal_aggregation.ipynb` | Agrega señales por plato y por negocio-plato, aplica pesos de fiabilidad y genera candidatos preliminares para ranking. |

---

## 4. Entrada del módulo

El input principal es:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

Este archivo procede del módulo de sentimiento híbrido.

Resumen del input:

| Métrica | Valor |
|---|---:|
| Menciones totales | 94.932 |
| Positive | 43.142 |
| Neutral | 45.366 |
| Negative | 6.424 |
| High reliability | 25.011 |
| Medium reliability | 25.495 |
| Low reliability | 44.426 |

---

## 5. Pesos de fiabilidad

No todas las menciones tienen la misma calidad. Por eso se asignó un peso según el tier de fiabilidad del módulo anterior:

| Reliability tier | Peso |
|---|---:|
| `high` | 1,00 |
| `medium` | 0,65 |
| `low` | 0,25 |

Este peso se combina con:

- confianza del sentimiento;
- confianza del NER;
- score de sentimiento.

La fórmula conceptual es:

```text
signal_weight = reliability_weight × sentiment_confidence × ner_confidence
```

Y la contribución ponderada de sentimiento:

```text
weighted_sentiment_contribution = weighted_sentiment_value × signal_weight
```

---

## 6. Señal de sentimiento ponderada

La señal final combina dos elementos:

1. etiqueta discreta de sentimiento:

```text
positive → 1
neutral  → 0
negative → -1
```

2. score continuo del módulo de sentimiento, normalizado a `[-1, 1]`.

La combinación usada fue:

```text
weighted_sentiment_value = 0.65 × sentiment_label_score + 0.35 × sentiment_score_normalized
```

Esto permite que la etiqueta tenga más peso, pero que la intensidad del score también influya.

---

## 7. Agregación global por plato

La primera tabla agregada resume señales a nivel de plato global.

Archivo generado:

```text
dish_global_signals_v1.csv
```

Esta tabla permite responder preguntas como:

- ¿qué platos aparecen más?
- ¿qué platos tienen mejor balance positivo/negativo?
- ¿qué platos tienen más cobertura de negocios?
- ¿qué platos tienen mayor evidencia global?

### 7.1. Métricas globales calculadas

Por cada `dish_id_v2` se calculan:

| Métrica | Descripción |
|---|---|
| `mention_count` | Número total de menciones del plato. |
| `review_count` | Número de reviews únicas donde aparece. |
| `business_count` | Número de negocios donde aparece. |
| `positive_mentions` | Menciones positivas. |
| `neutral_mentions` | Menciones neutrales. |
| `negative_mentions` | Menciones negativas. |
| `positive_ratio` | Proporción de menciones positivas. |
| `negative_ratio` | Proporción de menciones negativas. |
| `avg_ner_confidence` | Confianza media del detector NER. |
| `avg_sentiment_confidence` | Confianza media del sentimiento. |
| `avg_signal_weight` | Peso medio de señal. |
| `total_signal_weight` | Suma de pesos de señal. |
| `confidence_weighted_sentiment` | Sentimiento medio ponderado por confianza. |
| `aggregate_quality_tier` | Tier de calidad de la agregación. |

### 7.2. Resultados globales

| Métrica | Valor |
|---|---:|
| Platos globales agregados | 9.937 |
| Platos globales high quality | 60 |
| Platos globales medium quality | 95 |

La mayoría de platos globales tienen evidencia baja, lo cual es esperable en un catálogo amplio con muchas menciones poco frecuentes.

---

## 8. Agregación por negocio + plato

La segunda tabla es la más importante para el ranking.

Archivo generado:

```text
dish_business_signals_v1.csv
```

Agrupa por:

```text
business_id + dish_id_v2
```

Esta tabla permite detectar casos como:

```text
Sushi Ushi + sushi
Taqueria Cuernavaca + tacos
Three Muses + steak
```

### 8.1. Métricas por negocio-plato

Se calculan métricas similares a las globales, pero a nivel de negocio:

| Métrica | Descripción |
|---|---|
| `business_id` | Identificador del negocio. |
| `business_name` | Nombre del negocio. |
| `city` | Ciudad. |
| `state` | Estado. |
| `dish_id_v2` | Identificador del plato normalizado. |
| `canonical_dish_name_v2` | Nombre canónico del plato. |
| `mention_count` | Menciones del plato en ese negocio. |
| `review_count` | Reviews únicas donde aparece el plato en ese negocio. |
| `positive_ratio` | Ratio positivo local. |
| `negative_ratio` | Ratio negativo local. |
| `confidence_weighted_sentiment` | Sentimiento local ponderado. |
| `total_signal_weight` | Suma de peso de señal. |
| `aggregate_quality_tier` | Calidad de la agregación. |

### 8.2. Resultados negocio-plato

| Métrica | Valor |
|---|---:|
| Pares negocio-plato agregados | 31.036 |
| Pares high quality | 119 |
| Pares medium quality | 698 |
| Candidatos rankeables iniciales | 6.375 |

La primera versión de candidatos rankeables era amplia. Después se aplicó una capa adicional de scoring conservador.

---

## 9. Control de calidad de nombres

Durante la agregación se detectó que algunos nombres de platos seguían siendo ruidosos o poco útiles.

Ejemplos de ruido potencial:

```text
#
up
salad : the size was
food
meal
ordered
```

Por eso se añadieron reglas de calidad de nombre.

### 9.1. Flags de calidad

Ejemplos de flags:

```text
empty_name
exact_noise_name
too_short_name
too_long_name
too_many_words
suspicious_punctuation
contains_digit
bad_start_word
bad_end_word
contains_suspicious_words
possible_beverage
```

### 9.2. Resultados de control de calidad

| Métrica | Valor |
|---|---:|
| Pares ruidosos detectados | 806 |
| Posibles bebidas detectadas | 359 |

Las bebidas no se eliminan necesariamente, pero reciben penalización ligera porque el foco de Hidden Gems son platos.

---

## 10. Tiers de evidencia

Se definieron tiers para clasificar la cantidad y calidad de evidencia.

### 10.1. Tiers negocio-plato

| Tier | Criterio conceptual |
|---|---|
| `strong` | Muchas menciones, varias reviews, señal suficiente y alta fiabilidad. |
| `solid` | Evidencia intermedia robusta. |
| `emerging` | Evidencia mínima suficiente para ranking exploratorio. |
| `weak` | Evidencia insuficiente. |

Distribución final:

| Evidence tier | Pares |
|---|---:|
| Weak | 27.194 |
| Emerging | 1.440 |
| Solid | 1.406 |
| Strong | 996 |

---

## 11. Scoring conservador para ranking

Después de la agregación base se añadió una capa de scoring conservador para evitar que pares con poca evidencia aparezcan demasiado arriba.

El scoring incluye:

- sentimiento bayesiano con prior neutral;
- score de evidencia;
- score de volumen;
- score de peso de señal;
- ratio de alta fiabilidad;
- penalización por negativos;
- penalización por ruido;
- penalización ligera por bebidas.

### 11.1. Sentimiento bayesiano

Para evitar que dos menciones perfectas dominen el ranking, se aplicó un prior neutral:

```text
bayesian_sentiment_score =
    (confidence_weighted_sentiment × total_signal_weight + neutral_prior × prior_weight)
    / (total_signal_weight + prior_weight)
```

Esto suaviza scores extremos cuando hay poca evidencia.

### 11.2. Score preliminar

La fórmula conceptual del `preliminary_ranking_score_v1` combina:

- sentimiento bayesiano;
- balance positivo/negativo;
- evidencia;
- volumen;
- peso de señal;
- ratio de menciones high reliability;
- penalizaciones.

---

## 12. Resultados del scoring preliminar

Archivo generado:

```text
dish_business_ranking_candidates_v1.csv
```

Resumen:

| Métrica | Valor |
|---|---:|
| Pares negocio-plato totales | 31.036 |
| Ranking ready v1 | 3.841 |
| Strong candidates | 645 |
| Promising candidates | 1.021 |
| Weak candidates | 1.223 |
| Not ready | 28.147 |
| Score máximo | 88,81 |

Distribución por evidence tier y candidate tier:

| Evidence tier | Not ready | Promising | Strong | Weak | Total |
|---|---:|---:|---:|---:|---:|
| Emerging | 498 | 197 | 0 | 745 | 1.440 |
| Solid | 393 | 519 | 148 | 346 | 1.406 |
| Strong | 62 | 305 | 497 | 132 | 996 |
| Weak | 27.194 | 0 | 0 | 0 | 27.194 |
| Total | 28.147 | 1.021 | 645 | 1.223 | 31.036 |

---

## 13. Ejemplos de candidatos preliminares

Los primeros candidatos del scoring preliminar incluyen combinaciones con alta evidencia y sentimiento positivo:

| Negocio | Ciudad | Plato | Menciones | Reviews | Evidence | Score preliminar |
|---|---|---|---:|---:|---|---:|
| The Little Lamb | Clearwater | burger | 15 | 13 | strong | 88,81 |
| East Beach Grill | Santa Barbara | pancake | 24 | 14 | strong | 88,77 |
| Three Muses | New Orleans | steak | 32 | 26 | strong | 88,06 |
| Sushi Ushi | Valrico | sushi | 53 | 28 | strong | 87,58 |
| 4 Rivers Smokehouse | Tampa Bay | brisket | 16 | 13 | strong | 87,56 |

Este ranking preliminar aún no es el ranking final Hidden Gems, pero sirve como entrada directa al notebook 11.

---

## 14. Artefactos generados

### 14.1. Señales base

| Archivo | Descripción |
|---|---|
| `dish_global_signals_v1.csv` | Señales agregadas por plato global. |
| `dish_business_signals_v1.csv` | Señales agregadas por negocio-plato. |
| `dish_signal_aggregation_summary_v1.json` | Resumen de la agregación base. |

### 14.2. Scoring preliminar

| Archivo | Descripción |
|---|---|
| `dish_business_ranking_candidates_v1.csv` | Candidatos negocio-plato con scoring preliminar. |
| `dish_global_ranking_signals_v1.csv` | Señales globales enriquecidas con scoring. |
| `dish_signal_scoring_summary_v1.json` | Resumen del scoring preliminar. |

### 14.3. Muestras de revisión

| Archivo | Descripción |
|---|---|
| `dish_business_ranking_ready_sample_v1.csv` | Muestra de candidatos listos para ranking. |
| `dish_business_strong_candidates_sample_v1.csv` | Muestra de strong candidates. |
| `dish_business_promising_candidates_sample_v1.csv` | Muestra de promising candidates. |
| `dish_business_emerging_candidates_sample_v1.csv` | Muestra de emerging candidates. |
| `dish_business_noise_rejected_sample_v1.csv` | Muestra de pares rechazados por ruido. |
| `dish_global_scored_sample_v1.csv` | Muestra de señales globales scoreadas. |

---

## 15. Decisiones de diseño

### 15.1. Separar agregación global y negocio-plato

El ranking Hidden Gems necesita saber qué plato destaca en qué negocio. Por eso la tabla global no se usa como ranking principal.

La tabla global aporta contexto:

- popularidad general del plato;
- presencia en muchos negocios;
- sentimiento global medio;
- rareza relativa.

La tabla negocio-plato aporta la señal accionable.

### 15.2. Penalizar evidencia baja

Un plato con 2 menciones positivas no debe superar automáticamente a otro con 50 menciones sólidas. Por eso se aplican:

- thresholds mínimos;
- priors bayesianos;
- tiers de evidencia;
- total signal weight;
- review_count mínimo.

### 15.3. No eliminar bebidas de forma absoluta

Algunos términos como `latte`, `coffee` o `smoothie` pueden aparecer en reseñas gastronómicas. Se marcan como posibles bebidas y se penalizan ligeramente, pero no se eliminan por completo en esta fase.

---

## 16. Limitaciones

Limitaciones actuales:

- los datos siguen procediendo de Yelp, no de Sevilla;
- no hay todavía asignación por barrio;
- el sentimiento por mención es weak-supervised;
- algunos nombres de platos siguen siendo ruidosos;
- el scoring preliminar es heurístico;
- los pesos no están aprendidos con feedback humano;
- no existe aún validación manual del ranking.

---

## 17. Relación con el ranking Hidden Gems

El archivo principal de salida es:

```text
dish_business_ranking_candidates_v1.csv
```

Este archivo alimenta el módulo final de ranking:

```text
dish_business_ranking_candidates_v1.csv
+ dish_global_ranking_signals_v1.csv
→ 11_hidden_gems_ranking_v1.ipynb
```

A partir de esta fase, cada candidato negocio-plato ya tiene suficiente información para calcular un score final:

- evidencia local;
- sentimiento local;
- confianza;
- calidad del nombre;
- contexto global del plato;
- rareza;
- penalizaciones.
