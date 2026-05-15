# 05. Modelo 3: normalización / entity linking mediante reranker

## 1. Objetivo del modelo

El **Modelo 3** de la fase Sevilla IA v2 resuelve el problema de **normalización de menciones de platos**. Su objetivo es convertir una mención textual detectada en una reseña en un plato canónico del catálogo del sistema.

Ejemplo:

```text
Mención en reseña: "las croquetas de cola de toro"
Plato normalizado: croquetas de cola de toro
Dish ID: <uuid del catálogo>
```

Esta fase es imprescindible porque el modelo NER solo detecta texto, pero el ranking Hidden Gems necesita agrupar menciones equivalentes bajo un identificador común.

Sin normalización, estas variantes podrían quedar separadas:

```text
croquetas
croqueta
croquetas caseras
croquetas de jamón
croquetas de cola de toro
```

El objetivo no es solo limpiar texto, sino enlazar correctamente cada mención con el plato adecuado del catálogo.

---

## 2. Por qué se usa un reranker

Inicialmente se valoró entrenar un clasificador multiclase cerrado, donde cada clase fuera un plato del catálogo. Sin embargo, esa estrategia tiene un problema importante: el catálogo de platos puede crecer.

Por ese motivo, se eligió un enfoque de **reranking / entity linking**.

La idea es:

```text
mención + contexto + plato candidato
→ modelo
→ score de compatibilidad
```

El sistema primero genera varios candidatos de catálogo y el modelo decide cuál encaja mejor.

Ejemplo:

```text
Mención: "ensaladilla de gambas"
Contexto: "Pedimos ensaladilla de gambas y estaba espectacular."

Candidatos:
- ensaladilla
- gambas
- ensaladilla de gambas
- salpicón

Modelo reranker:
- ensaladilla de gambas → score alto
- ensaladilla → score medio
- gambas → score bajo
- salpicón → score bajo
```

Esta arquitectura es más flexible que un clasificador cerrado porque permite añadir nuevos platos y aliases al catálogo sin reentrenar inmediatamente el modelo.

---

## 3. Tipo de problema

La tarea se plantea como **clasificación binaria de pares**.

Entrada A:

```text
Mención: croquetas de cola de toro | Contexto: Las croquetas de cola de toro estaban increíbles.
```

Entrada B:

```text
Plato candidato: croquetas de cola de toro
```

Salida:

```text
match / not_match
```

Durante inferencia, el modelo se aplica a varios candidatos por mención y se elige el candidato con mayor score, siempre que supere ciertos umbrales de confianza.

---

## 4. Modelo base

El modelo base utilizado fue:

```text
dccuchile/bert-base-spanish-wwm-cased
```

La arquitectura final es una clasificación de secuencias con dos clases:

| Clase | Significado |
|---|---|
| `0` | El plato candidato no corresponde a la mención. |
| `1` | El plato candidato corresponde a la mención. |

Se eligió BETO por su rendimiento en español y porque permite evaluar conjuntamente el texto de la mención y el texto del plato candidato.

---

## 5. Dataset de entrenamiento

Se utilizó el dataset extendido de normalización:

```text
sevilla_dish_normalization_annotation_dataset_v1_extended.jsonl
```

El dataset tenía:

| Métrica | Valor |
|---|---:|
| Filas totales | 4.411 |
| Filas usables | 4.291 |

La versión extendida incorporó diferentes fuentes de etiqueta:

| Fuente | Uso |
|---|---|
| `weak_current_dish` | Etiqueta débil derivada de la normalización previa. |
| `manual_existing_dish` | Corrección manual hacia un plato existente. |
| `manual_new_dish` | Caso donde la mención indica un plato nuevo o no cubierto previamente. |

La presencia de correcciones manuales fue clave para que el modelo no aprendiera únicamente a confirmar la normalización anterior.

---

## 6. Generación de pares positivos y negativos

Para entrenar el reranker, cada fila del dataset se transformó en varios pares:

```text
mención/contexto + candidato correcto → label 1
mención/contexto + candidato incorrecto → label 0
```

Los negativos se generaron principalmente como **negativos duros**, es decir, candidatos parecidos al correcto.

Ejemplo:

```text
Mención: tarta de queso
Positivo: tarta de queso
Negativos duros:
- tarta de chocolate
- tarta de manzana
- queso
- postre
```

Esto obliga al modelo a aprender diferencias finas, no solo coincidencias triviales.

---

## 7. Resultados del entrenamiento

El entrenamiento con el dataset extendido obtuvo resultados muy altos.

Métricas por pares en test:

| Métrica | Valor |
|---|---:|
| Accuracy | 0,9991 |
| Precision | 0,9977 |
| Recall | 0,9977 |
| F1 | 0,9977 |
| AUC | 0,99999 |
| AUPRC | 0,99999 |

Métricas de ranking por mención:

| Métrica | Valor |
|---|---:|
| Accuracy@1 | 1,0000 |
| Accuracy@3 | 1,0000 |
| MRR | 1,0000 |

Interpretación:

```text
Cuando el candidato correcto está presente en la lista de candidatos, el reranker lo ordena correctamente con una fiabilidad muy alta.
```

---

## 8. Interpretación realista

Aunque las métricas son muy altas, es importante interpretar correctamente el alcance del modelo.

El modelo no hace esto:

```text
mención → descubre cualquier plato posible del mundo
```

Hace esto:

```text
mención + candidatos generados → ordena el mejor candidato
```

Por tanto, depende de que el sistema de generación de candidatos incluya el plato correcto entre las opciones.

Si el catálogo no contiene el plato o si el generador de candidatos no lo recupera, el reranker no puede enlazarlo correctamente.

---

## 9. Inferencia local

El modelo se aplica localmente mediante el script:

```text
scripts/run_sevilla_dish_normalization_reranker_v1.py
```

Entrada principal:

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
└── sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl
```

Salida principal:

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
├── sevilla_dish_mentions_normalized_reranker_v1.csv
├── sevilla_dish_mentions_normalized_reranker_v1.jsonl
├── sevilla_dish_normalization_low_confidence_v1.csv
├── sevilla_dish_normalization_no_candidate_v1.csv
└── sevilla_dish_normalization_summary_v1.json
```

---

## 10. Resultados de inferencia

Al aplicar el modelo sobre la capa Hybrid + NER v2 se obtuvo:

| Métrica | Valor |
|---|---:|
| Filas de entrada | 2.965 |
| Filas normalizadas | 2.965 |
| `linked` | 2.586 |
| `linked_needs_review` | 294 |
| `low_confidence` | 58 |
| `no_candidate` | 27 |
| Listas para sentimiento | 2.880 |

La mayoría de menciones quedaron enlazadas correctamente y pudieron pasar al modelo ABSA.

---

## 11. Estados de normalización

La capa de normalización genera varios estados:

| Estado | Significado |
|---|---|
| `linked` | La mención se enlazó con confianza suficiente. |
| `linked_needs_review` | Existe enlace, pero conviene revisar o ponderar con menor peso. |
| `low_confidence` | El mejor candidato no supera el umbral de confianza. |
| `no_candidate` | No se generó ningún candidato adecuado desde el catálogo. |

Estos estados permiten que las fases posteriores no traten todas las señales como equivalentes.

---

## 12. Decisión de diseño

La decisión final fue usar el modelo de normalización como **reranker experimental de alta precisión**, manteniendo trazabilidad y revisión:

```text
mención detectada
→ generación de candidatos por catálogo/aliases
→ reranker BETO
→ dish_id final o estado de revisión
```

Esto mejora la agrupación de menciones por plato sin convertir el sistema en una caja negra completa.

---

## 13. Limitaciones

Limitaciones principales:

- depende del catálogo de platos;
- depende de la generación inicial de candidatos;
- puede fallar en platos no catalogados;
- los casos `no_candidate` requieren ampliación de catálogo;
- los casos `linked_needs_review` deben ponderarse con cautela;
- el modelo no decide si un plato es relevante para ranking, solo lo enlaza.

---

## 14. Papel dentro de Hidden Gems v2

Este modelo es una pieza central de la fase IA v2 porque permite pasar de texto libre a entidades comparables:

```text
Texto de reseña
→ mención de plato
→ dish_id normalizado
→ sentimiento ABSA
→ señal local-plato
→ ranking
```

Sin esta normalización, el ranking tendría señales fragmentadas y sería mucho menos robusto.
