# 08 - Resultados y validación del módulo de IA

## 1. Objetivo del documento

Este documento resume los resultados obtenidos durante el desarrollo del módulo de inteligencia artificial de Hidden Gems.

La finalidad es concentrar en un único archivo:

- métricas principales;
- artefactos generados;
- validaciones realizadas;
- conclusiones por módulo;
- limitaciones observadas;
- estado final del prototipo IA.

El módulo IA desarrollado cubre el flujo completo:

```text
reviews gastronómicas
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems v1
```

---

## 2. Resumen ejecutivo de resultados

La cadena IA se completó correctamente hasta ranking v1.

| Fase | Resultado principal |
|---|---|
| Detección NER | Modelo Transformer entrenado con `entity F1 = 0,9381` en test. |
| Inferencia NER | 95.061 menciones detectadas sobre 79.270 reviews. |
| Normalización | 94.932 menciones normalizadas y 9.937 platos canónicos semilla. |
| Sentimiento por mención | 94.932 menciones con sentimiento híbrido v1.1. |
| Agregación | 31.036 pares negocio-plato agregados. |
| Scoring preliminar | 3.841 candidatos listos para ranking. |
| Ranking final | 622 candidatos Hidden Gems seleccionados. |

---

## 3. Resultados del detector de platos

### 3.1. Modelo entrenado

El detector de platos se entrenó como un modelo de NER con etiquetas BIO:

```text
O
B-DISH
I-DISH
```

Modelo base:

```text
distilbert-base-uncased
```

Configuración principal:

| Parámetro | Valor |
|---|---:|
| Épocas | 2 |
| Learning rate | 2e-5 |
| Weight decay | 0,01 |
| Max length | 256 |
| Train batch size | 16 |
| Eval batch size | 32 |
| Class weights | Sí |
| `label_all_tokens` | False |

---

### 3.2. Métricas de validación

| Métrica | Valor |
|---|---:|
| Entity precision | 0,9095 |
| Entity recall | 0,9667 |
| Entity F1 | 0,9372 |
| Entity accuracy | 0,9965 |
| Token macro F1 | 0,9201 |
| Token weighted F1 | 0,9968 |

---

### 3.3. Métricas de test

| Métrica | Valor |
|---|---:|
| Entity precision | 0,9094 |
| Entity recall | 0,9687 |
| Entity F1 | 0,9381 |
| Entity accuracy | 0,9966 |
| Token macro F1 | 0,9211 |
| Token weighted F1 | 0,9968 |

Estas métricas muestran que el modelo detecta muy bien las entidades de tipo plato dentro del dataset weak-supervised construido.

---

### 3.4. Análisis de errores del NER

Resumen de errores en test:

| Métrica | Valor |
|---|---:|
| Documentos test | 4.477 |
| Documentos con error de entidad | 666 |
| Porcentaje de docs con error | 14,88 % |
| True positives de entidades | 8.628 |
| False positives de entidades | 860 |
| False negatives de entidades | 279 |

Interpretación:

- el recall es alto, por lo que el modelo detecta la mayoría de platos;
- la precisión es buena, pero algunos falsos positivos llegan a fases posteriores;
- por ello se añadieron normalización, flags y filtros de calidad posteriores.

---

## 4. Resultados de inferencia NER

El modelo entrenado se aplicó sobre el corpus Yelp filtrado.

| Métrica | Valor |
|---|---:|
| Reviews procesadas | 79.270 |
| Menciones detectadas | 95.061 |
| Reviews con menciones | 42.471 |
| Reviews sin menciones | 36.799 |
| Reviews truncadas | 8.279 |
| Media menciones/review | 1,20 |
| Media menciones/review con menciones | 2,24 |
| Confianza media | 0,9752 |
| Confianza mediana | 0,9991 |

### 4.1. Top menciones detectadas

| Mención | Conteo aproximado |
|---|---:|
| pizza | 8.682 |
| burger | 5.756 |
| fries | 4.848 |
| sushi | 4.461 |
| shrimp | 4.398 |
| tacos | 2.912 |
| steak | 2.789 |
| ice cream | 2.371 |
| burgers | 2.334 |
| wings | 2.213 |

La distribución es coherente con un corpus gastronómico en inglés.

---

## 5. Resultados de normalización de platos

La normalización convirtió menciones textuales en platos canónicos.

### 5.1. Comparativa v1 vs v2

| Métrica | v1 | v2 |
|---|---:|---:|
| Menciones normalizadas | 94.303 | 94.932 |
| Pendientes/excluidas | 758 | 129 |
| Surface forms | 10.258 | 10.258 |
| Platos canónicos semilla | 9.401 | 9.937 |
| Aliases | 9.692 | 10.235 |
| Duplicados candidatos | - | 6.984 |
| Menciones con flags de revisión | - | 300 |

La v2 fue mejor porque corrigió errores de singularización agresiva.

### 5.2. Ejemplos de correcciones v2

| v1 incorrecto | v2 corregido |
|---|---|
| `hummu` | `hummus` |
| `crab cak` | `crab cakes` |
| `wing` | `wings` |
| `rib` | `ribs` |
| `nacho` | `nachos` |
| `mashed potato` | `mashed potatoes` |
| `french fries` | `fries` |
| `taco` | `tacos` |
| `omelette` | `omelet` |

### 5.3. Top platos normalizados

| Plato | Menciones |
|---|---:|
| pizza | 8.751 |
| burger | 8.095 |
| fries | 5.375 |
| sushi | 4.470 |
| tacos | 4.436 |
| shrimp | 4.421 |
| steak | 2.794 |
| ice cream | 2.411 |
| wings | 2.215 |
| donut | 2.175 |

---

## 6. Resultados del sentimiento por mención

El sentimiento por mención se construyó con un enfoque híbrido weak-supervised.

La versión final utilizada fue:

```text
hybrid_context_lexicon_v1_1
```

### 6.1. Distribución final de etiquetas

| Etiqueta | Conteo |
|---|---:|
| Neutral | 45.366 |
| Positive | 43.142 |
| Negative | 6.424 |
| Total | 94.932 |

### 6.2. Reliability tiers

| Tier | Conteo |
|---|---:|
| Low | 44.426 |
| Medium | 25.495 |
| High | 25.011 |

### 6.3. Candidatos para entrenamiento futuro

| Valor | Conteo |
|---|---:|
| Candidatos high reliability para entrenamiento | 25.011 |
| No candidatos | 69.921 |

Estos 25.011 ejemplos pueden servir como dataset weak-supervised inicial para entrenar un futuro modelo ABSA.

### 6.4. Motivos de asignación

| Motivo | Conteo |
|---|---:|
| `target_context_primary` | 50.956 |
| `review_prior_fallback` | 43.976 |

La existencia de muchos casos fallback confirma que el contexto local no siempre contiene una señal explícita de sentimiento.

### 6.5. Validación cualitativa

Se revisaron ejemplos de:

- positivos de alta confianza;
- negativos de alta confianza;
- neutrales ambiguos;
- desacuerdos entre rating general y sentimiento de la mención;
- casos mixtos;
- baja confianza.

La versión v1.1 redujo el exceso de positivos de la v1 y fue más prudente.

Comparativa:

| Versión | Positive | Neutral | Negative |
|---|---:|---:|---:|
| v1 | 55.325 | 31.752 | 7.855 |
| v1.1 | 43.142 | 45.366 | 6.424 |

---

## 7. Resultados de agregación de señales

La agregación toma las menciones con sentimiento y produce tablas por plato y negocio-plato.

### 7.1. Input de agregación

| Métrica | Valor |
|---|---:|
| Menciones | 94.932 |
| Reviews únicas | 42.461 |
| Negocios únicos | 4.088 |
| Platos únicos | 9.937 |
| Neutral | 45.366 |
| Positive | 43.142 |
| Negative | 6.424 |
| High reliability | 25.011 |
| Medium reliability | 25.495 |
| Low reliability | 44.426 |

---

### 7.2. Agregación global por plato

| Métrica | Valor |
|---|---:|
| Platos globales | 9.937 |
| Platos high quality | 60 |
| Platos medium quality | 95 |
| Platos low quality | 9.782 |

### 7.3. Top platos por menciones

| Plato | Menciones | Reviews | Negocios | Sentimiento ponderado |
|---|---:|---:|---:|---:|
| pizza | 8.751 | 4.599 | 856 | 0,5269 |
| burger | 8.095 | 4.478 | 863 | 0,5225 |
| fries | 5.375 | 4.094 | 1.093 | 0,4953 |
| sushi | 4.470 | 2.482 | 266 | 0,5511 |
| tacos | 4.436 | - | - | - |

---

### 7.4. Agregación por negocio-plato

| Métrica | Valor |
|---|---:|
| Pares negocio-plato | 31.036 |
| Ranking ready v1 | 3.841 |
| Strong candidates | 645 |
| Promising candidates | 1.021 |
| Weak candidates | 1.223 |
| Not ready | 28.147 |
| Pares ruidosos detectados | 806 |
| Posibles bebidas detectadas | 359 |

### 7.5. Evidence tiers negocio-plato

| Evidence tier | Pares |
|---|---:|
| Weak | 27.194 |
| Emerging | 1.440 |
| Solid | 1.406 |
| Strong | 996 |

---

## 8. Resultados del ranking Hidden Gems v1

El ranking final selecciona los mejores candidatos negocio-plato.

| Métrica | Valor |
|---|---:|
| Pares evaluados | 31.036 |
| Candidatos base rankable | 3.841 |
| Candidatos seleccionados | 622 |
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 50 |
| `promising_hidden_gem` | 182 |
| `exploratory_hidden_gem` | 388 |
| `not_selected` | 30.414 |
| Score máximo | 82,93 |
| Score medio seleccionados | 66,87 |
| Score mediano seleccionados | 65,74 |

### 8.1. Top 10 ranking v1

| Rank | Tier | Negocio | Ciudad | Plato | Menciones | Reviews | Score |
|---:|---|---|---|---|---:|---:|---:|
| 1 | `top_hidden_gem` | Sushi Ushi | Valrico | sushi | 53 | 28 | 82,93 |
| 2 | `top_hidden_gem` | Taqueria Cuernavaca | Santa Barbara | tacos | 73 | 45 | 82,04 |
| 3 | `strong_hidden_gem` | Blues City Deli | Saint Louis | sandwich | 108 | 87 | 81,98 |
| 4 | `strong_hidden_gem` | Surrey's Café & Juice Bar | New Orleans | shrimp | 159 | 120 | 81,90 |
| 5 | `strong_hidden_gem` | Three Muses | New Orleans | steak | 32 | 26 | 81,74 |
| 6 | `strong_hidden_gem` | HipCityVeg - University City | Philadelphia | fries | 37 | 31 | 81,32 |
| 7 | `strong_hidden_gem` | Kei Sushi | Reno | sushi | 64 | 31 | 81,24 |
| 8 | `strong_hidden_gem` | The Garden Brunch Cafe | Nashville | pancake | 75 | 52 | 80,03 |
| 9 | `strong_hidden_gem` | SPOT Gourmet Burgers | Philadelphia | burger | 105 | 42 | 79,91 |
| 10 | `strong_hidden_gem` | Muriel's Jackson Square | New Orleans | shrimp | 99 | 73 | 79,84 |

---

## 9. Validaciones realizadas

### 9.1. Validación del NER

Se validó mediante:

- métricas entity-level con `seqeval`;
- matriz de confusión token-level;
- test set separado;
- smoke test inicial;
- predicciones manuales;
- análisis de errores de entidades.

### 9.2. Validación de normalización

Se validó mediante:

- revisión de top surface forms;
- detección de errores de singularización;
- corrección v2;
- candidatos de duplicados;
- muestras de revisión manual;
- flags de normalización.

### 9.3. Validación de sentimiento

Se validó mediante:

- distribución de etiquetas;
- comparación v1 vs v1.1;
- crosstabs rating vs sentimiento de mención;
- casos de desacuerdo review/mención;
- muestras high confidence;
- muestras low confidence;
- muestras mixed evidence.

### 9.4. Validación de agregación

Se validó mediante:

- conteos por plato;
- conteos por negocio-plato;
- tiers de evidencia;
- detección de ruido;
- detección de posibles bebidas;
- revisión de candidatos preliminares.

### 9.5. Validación del ranking

Se validó mediante:

- distribución de tiers finales;
- top candidatos;
- score medio y mediano;
- ranking por ciudad;
- ranking por estado;
- explicación textual de candidatos;
- muestras por tier.

---

## 10. Artefactos principales validados

| Fase | Artefacto |
|---|---|
| NER training | `dish_ner_transformer_metrics_full.json` |
| NER inference | `dish_mentions_model_v1_full.jsonl` |
| Normalización | `dish_mentions_normalized_v2.jsonl` |
| Normalización | `dish_catalog_seed_v2.csv` |
| Sentimiento | `dish_mentions_with_sentiment_hybrid_v1.jsonl` |
| Sentimiento | `dish_mention_sentiment_summary_hybrid_v1.json` |
| Agregación | `dish_business_ranking_candidates_v1.csv` |
| Agregación | `dish_signal_scoring_summary_v1.json` |
| Ranking | `hidden_gems_selected_candidates_v1.csv` |
| Ranking | `hidden_gems_ranking_summary_v1.json` |

---

## 11. Conclusiones de validación

### 11.1. Lo que funciona bien

- El detector NER alcanza métricas altas y permite extraer menciones útiles.
- La normalización v2 reduce errores claros de singularización.
- El sentimiento v1.1 es más prudente que la v1 inicial.
- La agregación evita trabajar directamente con menciones aisladas.
- El scoring preliminar filtra gran parte de los pares poco fiables.
- El ranking final produce una lista razonable, explicable y conservadora.

### 11.2. Lo que todavía debe mejorarse

- La normalización no está revisada manualmente.
- El sentimiento por mención no es un gold standard.
- Las etiquetas de sentimiento son weak-supervised.
- El ranking no tiene validación humana.
- Los datos proceden de Yelp en inglés.
- No hay todavía integración con barrios de Sevilla.
- Los pesos del ranking son heurísticos.

---

## 12. Estado final del módulo IA

El módulo IA ya cuenta con una primera versión funcional completa:

```text
texto → platos → normalización → sentimiento → agregación → ranking
```

El resultado final no debe interpretarse como producto terminado, sino como **prototipo validado de la lógica IA central**.

Este prototipo demuestra que Hidden Gems puede pasar de reseñas no estructuradas a candidatos explicables de platos destacados.

---

## 13. Próximo paso recomendado

El siguiente paso no debería ser añadir más complejidad al ranking Yelp, sino conectar esta lógica con el pipeline real de Hidden Gems:

```text
Google Places + OSM + barrios de Sevilla
→ locales reales
→ asignación geográfica
→ reseñas/textos disponibles
→ detección y scoring de platos
→ ranking por barrio
```

En paralelo, se puede preparar una fase futura de mejora IA:

- modelo ABSA entrenado;
- normalización por embeddings;
- adaptación al español;
- validación humana;
- learning-to-rank.
