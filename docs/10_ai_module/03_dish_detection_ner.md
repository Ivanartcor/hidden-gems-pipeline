# 03 - Detección de platos con Dish NER

## 1. Objetivo del módulo

El objetivo de este bloque es construir el primer detector automático de menciones de platos para Hidden Gems.

Dentro del proyecto, el ranking final no debe girar alrededor de restaurantes genéricos, sino alrededor de platos concretos mencionados en reseñas gastronómicas. Por tanto, antes de normalizar platos, calcular sentimiento o construir rankings, es necesario resolver una tarea previa:

```text
review gastronómica
→ detección de menciones de platos
→ entidades DISH
```

Ejemplo:

```text
The crab legs were amazing, but the fries were cold.
```

Salida esperada:

```text
DISH: crab legs
DISH: fries
```

Este módulo construye esa capacidad usando un modelo de NER entrenado con etiquetas BIO.

---

## 2. Papel dentro del flujo de IA

La detección de platos es el primer módulo central de la cadena inteligente de Hidden Gems:

```text
reviews
→ Dish NER
→ menciones de platos
→ normalización
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

Sin este paso, el sistema no podría saber qué platos aparecen en una reseña. Además, si la extracción de platos es mala, todos los módulos posteriores heredan ese error.

Por eso se decidió construir un detector específico de platos, en lugar de depender únicamente de expresiones regulares o listas cerradas.

---

## 3. Notebooks implicados

Este bloque agrupa cuatro notebooks principales:

| Notebook | Función |
|---|---|
| `04_dish_detection_dataset_exploration.ipynb` | Exploración inicial de candidatos de platos y generación de señales débiles. |
| `05_dish_ner_dataset_builder.ipynb` | Construcción del dataset BIO para entrenamiento NER. |
| `06_dish_ner_transformer_training.ipynb` | Entrenamiento y evaluación del modelo Transformer NER. |
| `07_dish_ner_inference_and_mentions.ipynb` | Aplicación del modelo entrenado al corpus y generación de menciones oficiales. |

---

## 4. Enfoque general

El problema se abordó como una tarea de **Named Entity Recognition**, usando etiquetas BIO:

```text
O       → token fuera de una entidad
B-DISH  → inicio de una mención de plato
I-DISH  → continuación de una mención de plato
```

Ejemplo simplificado:

```text
The crab legs were amazing
O   B-DISH I-DISH O    O
```

Este enfoque permite detectar menciones de una o varias palabras, por ejemplo:

```text
pizza
burger
crab legs
mac and cheese
fried chicken
pumpkin pie
```

---

## 5. Dataset de entrenamiento

El dataset se generó a partir de reseñas gastronómicas filtradas desde la vertical de Yelp.

La idea fue construir un dataset weak-supervised, es decir, un conjunto de entrenamiento generado mediante reglas, candidatos y validaciones automáticas, no mediante etiquetado manual completo.

La versión final usada para el entrenamiento completo fue el dataset `high_quality`.

### 5.1. Dataset BIO high quality

Resumen del dataset BIO usado en el entrenamiento completo:

| Split | Documentos | Documentos con entidades | Documentos sin entidades |
|---|---:|---:|---:|
| Train | 34.182 | 32.682 | 1.500 |
| Validation | 4.502 | 4.093 | 409 |
| Test | 4.477 | 4.070 | 407 |
| Total | 43.161 | 40.845 | 2.316 |

Distribución media de entidades:

| Métrica | Valor |
|---|---:|
| Media de entidades por documento | 2,27 |
| Mediana | 2 |
| Máximo | 37 |

### 5.2. Distribución token-level

El dataset presenta un fuerte desbalance natural: la mayoría de tokens no son platos.

Distribución aproximada en train:

| Etiqueta | Tokens | Porcentaje supervisado |
|---|---:|---:|
| `O` | 3.836.691 | 97,64 % |
| `B-DISH` | 72.137 | 1,84 % |
| `I-DISH` | 20.778 | 0,53 % |

Este desbalance se tuvo en cuenta durante el entrenamiento mediante pesos de clase.

---

## 6. Entrenamiento del modelo

El modelo se entrenó como un Transformer para clasificación de tokens.

Características del entrenamiento:

- tarea: token classification;
- etiquetas: `O`, `B-DISH`, `I-DISH`;
- entrenamiento con pesos de clase;
- evaluación con métricas token-level y entity-level;
- uso de `seqeval` para medir entidades completas;
- entrenamiento ejecutado en Kaggle con GPU.

El entrenamiento completo se realizó durante 2 épocas sobre el dataset `high_quality`.

### 6.1. Resultado del entrenamiento completo

Métricas finales sobre validation:

| Métrica | Valor |
|---|---:|
| Entity Precision | 0,9095 |
| Entity Recall | 0,9667 |
| Entity F1 | 0,9372 |
| Entity Accuracy | 0,9965 |
| Token Macro F1 | 0,9201 |
| Token Weighted F1 | 0,9968 |

Métricas finales sobre test:

| Métrica | Valor |
|---|---:|
| Entity Precision | 0,9094 |
| Entity Recall | 0,9687 |
| Entity F1 | 0,9381 |
| Entity Accuracy | 0,9966 |
| Token Macro F1 | 0,9211 |
| Token Weighted F1 | 0,9968 |

Estas métricas indican que el detector es especialmente fuerte en recall, lo cual es adecuado para esta fase del pipeline: es preferible capturar la mayoría de platos y depurar después mediante normalización, filtros y scoring.

---

## 7. Matriz de confusión token-level

Resultado token-level sobre test:

| Real / Predicho | `O` | `B-DISH` | `I-DISH` |
|---|---:|---:|---:|
| `O` | 493.365 | 474 | 1.059 |
| `B-DISH` | 34 | 8.775 | 98 |
| `I-DISH` | 40 | 24 | 2.437 |

Classification report token-level:

| Etiqueta | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `O` | 0,9999 | 0,9969 | 0,9984 | 494.898 |
| `B-DISH` | 0,9463 | 0,9852 | 0,9653 | 8.907 |
| `I-DISH` | 0,6781 | 0,9744 | 0,7997 | 2.501 |

El modelo recupera muy bien los inicios de entidades (`B-DISH`) y tiene un recall alto en continuaciones (`I-DISH`). La precisión de `I-DISH` es menor, lo cual es esperable en menciones largas o variantes compuestas.

---

## 8. Evaluación entity-level

Evaluación con `seqeval` sobre test:

| Entidad | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `DISH` | 0,9094 | 0,9687 | 0,9381 | 8.907 |

A nivel de entidad completa, el resultado es sólido para una primera versión entrenada con weak labels.

---

## 9. Análisis de errores

En el test final se procesaron 4.477 documentos.

| Métrica | Valor |
|---|---:|
| Total documentos test | 4.477 |
| Documentos con error de entidad | 666 |
| Porcentaje de documentos con error | 14,88 % |
| True Positive entities | 8.628 |
| False Positive entities | 860 |
| False Negative entities | 279 |

Lectura del resultado:

- el número de falsos negativos es bajo;
- el modelo tiende a detectar muchas entidades, lo cual favorece recall;
- algunos falsos positivos se corrigen posteriormente con normalización, filtros de ruido y agregación;
- la tasa de documentos con algún error es aceptable para una primera versión no supervisada manualmente.

---

## 10. Pruebas manuales del modelo

Se realizaron pruebas manuales para comprobar la salida del modelo sobre frases nuevas.

Ejemplo 1:

```text
The crab legs were amazing, but the fries were cold.
```

Entidades detectadas:

```text
crab legs
fries
```

Ejemplo 2:

```text
I ordered the burger with bacon and the mac and cheese.
```

Entidades detectadas:

```text
burger with bacon
mac and cheese
```

Ejemplo 3:

```text
Their fried chicken and mashed potatoes were fantastic.
```

Entidades detectadas:

```text
fried chicken
mashed potatoes
```

Ejemplo 4:

```text
I would come back just for the ice cream and the pumpkin pie.
```

Entidades detectadas:

```text
ice cream
pumpkin pie
```

Estas pruebas muestran que el modelo detecta correctamente platos simples y compuestos.

---

## 11. Inferencia sobre el corpus completo

Una vez entrenado el modelo, se aplicó sobre el corpus Yelp para generar la tabla oficial de menciones.

Notebook:

```text
07_dish_ner_inference_and_mentions.ipynb
```

Entrada principal:

```text
yelp_food_reviews_corpus_sample_100k_lines.jsonl
```

Modelo usado:

```text
dish_ner_transformer_full
```

Resultado de la inferencia:

| Métrica | Valor |
|---|---:|
| Reviews procesadas | 79.270 |
| Menciones detectadas | 95.061 |
| Reviews con menciones | 42.471 |
| Reviews sin menciones | 36.799 |
| Media menciones por review | 1,20 |
| Media menciones por review con menciones | 2,24 |
| Confianza media | 0,9752 |
| Confianza mediana | 0,9991 |
| Reviews truncadas | 8.279 |

---

## 12. Postprocesado de entidades

Después de la inferencia se aplicó un postprocesado ligero:

1. fusión de entidades DISH adyacentes;
2. normalización textual básica;
3. cálculo de confianza media, mínima y máxima por entidad;
4. generación de identificadores únicos de mención;
5. conservación de metadatos de review y negocio.

Ejemplo de mejora:

```text
[DISH:tuna][DISH:tacos]
→ tuna tacos
```

Este postprocesado no intenta resolver todas las variantes, ya que esa responsabilidad se delega al módulo de normalización.

---

## 13. Archivo principal generado

El artefacto principal producido por este bloque es:

```text
dish_mentions_model_v1_full.jsonl
```

Este archivo contiene una fila por cada mención de plato detectada.

Campos principales:

| Campo | Descripción |
|---|---|
| `mention_id` | Identificador único de la mención. |
| `review_id` | Identificador de la review. |
| `business_id` | Identificador del negocio. |
| `dish_mention_text` | Texto original detectado como plato. |
| `dish_mention_normalized` | Versión normalizada básica de la mención. |
| `start_char` / `end_char` | Posición de la mención en el texto. |
| `start_token` / `end_token` | Posición token-level. |
| `confidence_mean` | Confianza media de la entidad. |
| `rating_value` | Rating general de la review. |
| `sentiment_label` | Sentimiento general derivado del rating. |
| `review_text` | Texto completo de la review. |
| `model_name` | Modelo NER usado. |
| `normalization_status` | Estado inicial de normalización. |

---

## 14. Otros artefactos generados

Además del archivo principal, se generaron artefactos auxiliares:

```text
dish_ner_transformer_metrics_full.json
dish_ner_entity_error_analysis_full.json
dish_ner_test_predictions_readable_full.jsonl
dish_ner_manual_predictions_full.jsonl
dish_ner_inference_summary_full.json
dish_mentions_sample_random_full.jsonl
dish_mentions_sample_low_confidence_full.jsonl
dish_mentions_sample_top_mentions_full.jsonl
```

Uso de cada artefacto:

| Artefacto | Uso |
|---|---|
| `dish_ner_transformer_metrics_full.json` | Métricas completas de entrenamiento y evaluación. |
| `dish_ner_entity_error_analysis_full.json` | Análisis de errores por entidad. |
| `dish_ner_test_predictions_readable_full.jsonl` | Predicciones legibles sobre test. |
| `dish_ner_manual_predictions_full.jsonl` | Pruebas manuales del modelo. |
| `dish_ner_inference_summary_full.json` | Resumen de inferencia completa. |
| `dish_mentions_sample_random_full.jsonl` | Muestra aleatoria de menciones. |
| `dish_mentions_sample_low_confidence_full.jsonl` | Menciones de menor confianza para revisión. |
| `dish_mentions_sample_top_mentions_full.jsonl` | Menciones frecuentes para auditoría. |

---

## 15. Decisiones técnicas importantes

### 15.1. Usar NER en lugar de reglas puras

Se decidió entrenar un modelo NER porque las menciones de platos son variables y contextuales.

Ejemplos:

```text
burger
bacon burger
burger with bacon
mac and cheese
fried green tomatoes
```

Un sistema basado solo en diccionarios perdería muchas variantes o produciría demasiados falsos positivos.

### 15.2. Mantener weak supervision

No se creó un gold dataset manual completo porque habría sido costoso. En su lugar, se generó un dataset de alta calidad mediante reglas, candidatos y validaciones.

Esta decisión permitió construir una primera versión funcional del detector y reservar la revisión manual para etapas más avanzadas.

### 15.3. Priorizar recall

Para Hidden Gems, es preferible que el detector capture la mayoría de platos y que los módulos posteriores filtren o normalicen ruido.

Por eso el resultado con recall entity-level de 0,9687 es especialmente útil.

### 15.4. Separar detección y normalización

El NER solo detecta menciones. No intenta decidir si:

```text
burger
burgers
cheeseburger
burger with bacon
```

deben pertenecer al mismo plato o a platos distintos.

Esa decisión se realiza después en el módulo de normalización.

---

## 16. Limitaciones del módulo

Aunque los resultados son sólidos, esta primera versión tiene limitaciones:

1. **Dataset weak-supervised**: las etiquetas de entrenamiento no son gold standard manual.
2. **Idioma inglés**: el entrenamiento principal se realizó con Yelp en inglés.
3. **No está adaptado todavía a reseñas reales de Sevilla en español**.
4. **Puede detectar menciones demasiado largas** como `burger with bacon`.
5. **Puede separar componentes de un plato compuesto** en algunos casos.
6. **Puede detectar bebidas o elementos genéricos**, que se filtran después.
7. **Las reviews largas pueden truncarse** por límite de tokens.

Estas limitaciones no invalidan el módulo, pero deben tenerse en cuenta al interpretar resultados.

---

## 17. Papel en los módulos posteriores

La salida de este módulo alimenta directamente al normalizador:

```text
dish_mentions_model_v1_full.jsonl
→ 08_dish_normalization_and_catalog_builder.ipynb
```

A partir de ahí, cada mención detectada se convierte en:

```text
mención textual
→ plato canónico
→ alias
→ dish_id
```

Por tanto, este módulo es la base de toda la cadena de IA.

---

## 18. Resumen final

El módulo Dish NER v1 cumple su objetivo principal: detectar automáticamente menciones de platos en reseñas gastronómicas.

Resultados principales:

| Elemento | Resultado |
|---|---:|
| Dataset BIO high quality | 43.161 documentos |
| Entity F1 test | 0,9381 |
| Entity Precision test | 0,9094 |
| Entity Recall test | 0,9687 |
| Reviews procesadas en inferencia | 79.270 |
| Menciones detectadas | 95.061 |
| Reviews con menciones | 42.471 |
| Confianza media de inferencia | 0,9752 |

Este resultado permite continuar de forma sólida hacia la normalización de platos, el cálculo de sentimiento por mención y el ranking Hidden Gems.
