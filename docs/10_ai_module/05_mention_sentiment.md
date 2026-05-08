# 05 - Sentimiento por mención de plato

## 1. Objetivo del módulo

El objetivo de este módulo es asignar una señal de sentimiento a cada mención de plato normalizada.

Hasta este punto, el sistema sabe qué platos aparecen en cada review y cómo agruparlos. Sin embargo, todavía necesita saber si la mención del plato es positiva, negativa o neutral.

Ejemplo:

```text
The service was terrible, but the pasta was delicious.
```

El sentimiento general de la review podría ser neutral o incluso negativo, pero el sentimiento concreto de `pasta` es positivo.

Por tanto, no basta con usar el rating general de la review. Hidden Gems necesita una señal más cercana al plato.

---

## 2. Papel dentro del flujo de IA

El módulo de sentimiento aparece después de la normalización:

```text
reviews
→ Dish NER
→ menciones de platos
→ normalización
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

Su salida principal es una tabla donde cada mención contiene:

- plato detectado;
- plato normalizado;
- contexto textual;
- etiqueta de sentimiento;
- score de sentimiento;
- confianza;
- tier de fiabilidad;
- flags de ambigüedad;
- marca de candidato para entrenamiento futuro.

---

## 3. Notebook implicado

| Notebook | Función |
|---|---|
| `09_dish_mention_sentiment_hybrid_v1.ipynb` | Asigna sentimiento por mención usando un enfoque híbrido contextual y explicable. |

---

## 4. Entrada del módulo

El input principal es:

```text
dish_mentions_normalized_v2.jsonl
```

Resumen del input:

| Métrica | Valor |
|---|---:|
| Menciones recibidas | 95.061 |
| Menciones válidas para sentimiento | 94.932 |
| Menciones descartadas | 129 |
| Reviews únicas | 42.461 |
| Negocios únicos | 4.088 |
| Platos únicos | 9.937 |
| Confianza media del NER | 0,9757 |
| Confianza mediana del NER | 0,9991 |

Distribución por rating de la review:

| Rating | Menciones |
|---|---:|
| 1.0 | 7.363 |
| 2.0 | 9.032 |
| 3.0 | 13.904 |
| 4.0 | 29.471 |
| 5.0 | 35.162 |

Distribución del sentimiento general de review:

| Sentimiento general | Menciones |
|---|---:|
| Positive | 64.633 |
| Negative | 16.395 |
| Neutral | 13.904 |

---

## 5. Por qué no se usó directamente el rating

El rating de una review es una señal útil, pero demasiado global.

Problemas principales:

### 5.1. Reviews mixtas

```text
The burger was dry and overpriced, but the fries were great.
```

En la misma review:

```text
burger → negative
fries  → positive
```

### 5.2. Críticas al servicio pero elogio al plato

```text
The service was terrible, but the sushi was amazing.
```

El rating puede ser bajo, pero el plato mencionado puede estar bien valorado.

### 5.3. Review positiva con un plato concreto negativo

```text
Everything was excellent except the pasta, which was cold and bland.
```

El rating general podría ser alto, pero `pasta` debe recibir una señal negativa.

Por eso se diseñó un enfoque local, centrado en el contexto de la mención.

---

## 6. Enfoque aplicado

Se construyó una versión híbrida, explicable y weak-supervised.

La decisión fue no entrenar todavía un modelo específico de aspect-based sentiment porque no existía un dataset gold etiquetado manualmente por mención.

El enfoque usa:

- contexto local alrededor del plato;
- frase donde aparece la mención;
- cláusula concreta de la mención;
- léxico positivo y negativo;
- frases positivas y negativas;
- negaciones;
- conectores de contraste;
- rating general como fallback;
- confianza del NER;
- flags de ambigüedad.

---

## 7. Extracción de contexto

Para cada mención se generaron varios contextos:

| Contexto | Descripción |
|---|---|
| `sentence_context` | Frase aproximada donde aparece el plato. |
| `window_context` | Ventana amplia alrededor de la mención. |
| `left_context` | Texto inmediatamente anterior. |
| `right_context` | Texto inmediatamente posterior. |
| `target_clause_context_v11` | Cláusula específica centrada en la mención. |
| `near_mention_context_v11` | Contexto corto alrededor de la mención. |

Resumen de longitudes:

| Contexto | Media | Mediana | Máximo |
|---|---:|---:|---:|
| `sentence_context` | 87,55 caracteres | 76 | 1.034 |
| `window_context` | 218,59 caracteres | 244 | 302 |

---

## 8. Léxico y señales locales

Se definieron léxicos positivos y negativos orientados a reseñas gastronómicas.

Ejemplos de términos positivos:

```text
amazing
excellent
delicious
tasty
fresh
crispy
tender
juicy
flavorful
perfect
loved
recommended
```

Ejemplos de términos negativos:

```text
bad
terrible
bland
cold
dry
soggy
burnt
overcooked
undercooked
stale
rubbery
tasteless
flavorless
disappointing
```

También se añadieron frases positivas y negativas:

```text
perfectly cooked
highly recommend
full of flavor
not good
not worth
nothing special
would not recommend
left a lot to be desired
```

---

## 9. Versión v1

La primera versión combinó:

- score de frase;
- score de ventana;
- contexto izquierdo y derecho;
- rating prior;
- review sentiment prior.

Resultado v1:

| Etiqueta | Menciones |
|---|---:|
| Positive | 55.325 |
| Neutral | 31.752 |
| Negative | 7.855 |

La v1 funcionó, pero se detectó un problema: a veces tomaba palabras positivas o negativas de la frase aunque esas palabras describieran otro plato.

Ejemplo problemático:

```text
The curds were very good but the pizza wasn't knock-your-socks-off.
```

La v1 podía marcar `pizza` como positivo por `very good`, aunque esa valoración correspondía a `curds`.

---

## 10. Refinamiento v1.1

Para corregir ese problema se creó una versión v1.1 más centrada en el aspecto.

La v1.1 prioriza:

- cláusula donde aparece el plato;
- contexto inmediato;
- patrones directos del tipo `pizza was delicious`, `burger was dry`, `fries were cold`;
- menor peso del rating general;
- resolución más conservadora de casos mixtos.

### 10.1. Resultados v1.1

| Etiqueta | Menciones |
|---|---:|
| Neutral | 45.366 |
| Positive | 43.142 |
| Negative | 6.424 |
| Total | 94.932 |

Comparación v1 vs v1.1:

| Versión | Positive | Neutral | Negative |
|---|---:|---:|---:|
| v1 | 55.325 | 31.752 | 7.855 |
| v1.1 | 43.142 | 45.366 | 6.424 |

La v1.1 es más conservadora, reduce el exceso de positivos y aumenta los casos neutrales cuando no hay evidencia local clara.

### 10.2. Cambios entre v1 y v1.1

| Cambio | Casos |
|---|---:|
| Negative → Negative | 5.335 |
| Negative → Neutral | 2.430 |
| Negative → Positive | 90 |
| Neutral → Negative | 1.043 |
| Neutral → Neutral | 28.930 |
| Neutral → Positive | 1.779 |
| Positive → Negative | 46 |
| Positive → Neutral | 14.006 |
| Positive → Positive | 41.273 |

---

## 11. Razones y flags

La v1.1 clasifica cada predicción según la fuente principal de la señal.

| Reason | Menciones |
|---|---:|
| `target_context_primary` | 50.956 |
| `review_prior_fallback` | 43.976 |

Los flags permiten identificar casos de menor fiabilidad o mayor ambigüedad.

Ejemplos de flags:

```text
contrast_marker_nearby
mixed_target_evidence
weak_target_sentiment_signal
used_review_prior_fallback
low_ner_confidence
direct_positive_pattern
direct_negative_pattern
ambiguous_mixed_resolved_as_neutral
```

---

## 12. Score y confianza

Para cada mención se generaron tres salidas principales:

```text
mention_sentiment_label_final
mention_sentiment_score_final
mention_sentiment_confidence_final
```

La confianza final no pretende ser una probabilidad calibrada, sino una señal útil para ponderar la agregación posterior.

Resumen de confianza v1.1:

| Métrica | Valor |
|---|---:|
| Mínimo | 0,1660 |
| Media | 0,5512 |
| Mediana | 0,6141 |
| Máximo | 0,9500 |

---

## 13. Reliability tier

Se añadió un nivel de fiabilidad para que la agregación posterior pueda ponderar cada mención.

| Tier | Menciones |
|---|---:|
| High | 25.011 |
| Medium | 25.495 |
| Low | 44.426 |

Interpretación:

- `high`: señal local clara y alta confianza;
- `medium`: señal útil, pero con alguna ambigüedad;
- `low`: señal débil, dependiente del prior o con baja confianza.

---

## 14. Candidatos para entrenamiento futuro

El módulo marca ejemplos de alta fiabilidad para un futuro dataset weak-supervised de aspect-based sentiment.

| Campo | Valor |
|---|---:|
| Candidatos de entrenamiento futuro | 25.011 |

Estos ejemplos no son etiquetas gold manuales, pero pueden servir como punto de partida para:

- revisar una muestra manual;
- crear un seed dataset;
- entrenar un transformer específico de sentimiento por mención;
- comparar reglas híbridas vs modelo entrenado.

---

## 15. Artefactos generados

### 15.1. Artefactos principales

| Archivo | Descripción |
|---|---|
| `dish_mentions_with_sentiment_hybrid_v1.jsonl` | Menciones normalizadas con sentimiento final v1.1. |
| `dish_mention_sentiment_summary_hybrid_v1.json` | Resumen de métricas del módulo. |
| `dish_mention_sentiment_training_candidates_v1.jsonl` | Menciones high reliability para entrenamiento futuro. |

### 15.2. Muestras de revisión

| Archivo | Descripción |
|---|---|
| `dish_mention_sentiment_sample_random_v1.jsonl` | Muestra aleatoria de predicciones. |
| `dish_mention_sentiment_sample_high_confidence_v1.jsonl` | Muestra de alta confianza. |
| `dish_mention_sentiment_sample_low_confidence_v1.jsonl` | Muestra de baja confianza. |
| `dish_mention_sentiment_sample_review_disagreement_v1.jsonl` | Casos donde el sentimiento de mención difiere del sentimiento general de review. |
| `dish_mention_sentiment_sample_mixed_evidence_v1.jsonl` | Casos con evidencia positiva y negativa mezclada. |

---

## 16. Decisiones de diseño

### 16.1. No entrenar todavía un modelo ABSA

Se decidió no entrenar un modelo de sentimiento por aspecto en esta fase porque:

- no existe un dataset gold manual por mención;
- entrenar con etiquetas débiles sin validación puede propagar ruido;
- la versión híbrida es explicable y controlable;
- el ranking v1 necesitaba una señal funcional, no necesariamente definitiva;
- los high reliability candidates permiten entrenar un modelo más adelante.

### 16.2. Usar el rating solo como fallback

El rating general no desaparece, pero no domina la predicción cuando hay evidencia local clara.

Esto evita errores como etiquetar negativamente un plato bien valorado dentro de una review general negativa.

### 16.3. Ser conservador

La v1.1 prefiere marcar neutral cuando la evidencia local es débil o mixta. Para ranking, esto es preferible a inflar artificialmente los positivos.

---

## 17. Limitaciones

Limitaciones actuales:

- el sentimiento es weak-supervised;
- no hay validación manual completa;
- el léxico está orientado a inglés;
- algunas expresiones sarcásticas o complejas no se capturan;
- las negaciones largas pueden fallar;
- la confianza no está calibrada probabilísticamente;
- las etiquetas high reliability siguen sin ser gold labels.

---

## 18. Relación con fases posteriores

La salida principal:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
```

alimenta el módulo de agregación:

```text
dish_mentions_with_sentiment_hybrid_v1.jsonl
→ 10_dish_signal_aggregation.ipynb
```

A partir de este punto, cada mención ya aporta:

- plato normalizado;
- negocio;
- score de sentimiento;
- confianza del sentimiento;
- fiabilidad;
- confianza del NER;
- contexto textual.

Esto permite agregar señales por plato y por negocio-plato.
