# Sección para README principal — Módulo IA

> Este archivo contiene una sección preparada para copiar y pegar en el `README.md` principal del repositorio.

---

## Módulo de Inteligencia Artificial

Hidden Gems incluye un módulo de IA diseñado para transformar reseñas gastronómicas no estructuradas en candidatos de platos destacados.

El objetivo no es recomendar restaurantes de forma genérica, sino identificar **qué platos concretos destacan en qué locales**.

> **Alcance de esta sección**  
> Esta sección resume la IA v1 basada en Yelp. Sirve para explicar la cadena técnica completa y sus resultados principales. Si el README principal también incluye una capa posterior de Sevilla / IA v2, ambas partes deben convivir: la IA v1 explica la validación NLP original y la capa Sevilla explica la integración territorial final.

La cadena IA desarrollada sigue este flujo:

```text
reviews gastronómicas
→ detección de menciones de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

### Estado actual de IA v1

La primera versión funcional del módulo IA ya está completada hasta ranking prototipo:

| Fase | Estado |
|---|---|
| Exploración de candidatos de platos | Completada |
| Dataset BIO para NER | Completada |
| Entrenamiento Dish NER Transformer | Completado |
| Inferencia y generación de menciones | Completada |
| Normalización de platos | Completada |
| Sentimiento por mención | Completado |
| Agregación de señales | Completada |
| Ranking Hidden Gems v1 | Completado |

### Resultados principales

| Módulo | Resultado |
|---|---:|
| Modelo Dish NER | Entity F1 test: 0,9381 |
| Reviews procesadas en inferencia | 79.270 |
| Menciones de platos detectadas | 95.061 |
| Menciones normalizadas v2 | 94.932 |
| Platos canónicos semilla | 9.937 |
| Menciones con sentimiento | 94.932 |
| Pares negocio-plato agregados | 31.036 |
| Candidatos listos para ranking | 3.841 |
| Candidatos Hidden Gems seleccionados | 622 |

### Ranking Hidden Gems v1

El ranking v1 selecciona candidatos negocio-plato combinando:

- sentimiento local del plato;
- evidencia disponible;
- confianza de las señales;
- balance positivo/negativo;
- rareza o diferenciación local;
- penalizaciones por ruido, bebida o baja evidencia.

Distribución final del ranking:

| Tier | Candidatos |
|---|---:|
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 50 |
| `promising_hidden_gem` | 182 |
| `exploratory_hidden_gem` | 388 |

Ejemplos del top final:

| Rank | Negocio | Ciudad | Plato | Score |
|---:|---|---|---|---:|
| 1 | Sushi Ushi | Valrico | sushi | 82,93 |
| 2 | Taqueria Cuernavaca | Santa Barbara | tacos | 82,04 |
| 3 | Blues City Deli | Saint Louis | sandwich | 81,98 |
| 4 | Surrey's Café & Juice Bar | New Orleans | shrimp | 81,90 |
| 5 | Three Muses | New Orleans | steak | 81,74 |

### Documentación del módulo IA

La documentación completa del módulo se encuentra en:

```text
docs/10_ai_module/
```

Documentos incluidos:

| Documento | Descripción |
|---|---|
| `00_ai_module_index.md` | Índice del bloque IA. |
| `01_ai_module_overview.md` | Visión general del módulo IA. |
| `02_ai_data_flow_and_artifacts.md` | Flujo de datos y artefactos. |
| `03_dish_detection_ner.md` | Detector de platos con NER. |
| `04_dish_normalization.md` | Normalización de platos y catálogo semilla. |
| `05_mention_sentiment.md` | Sentimiento por mención de plato. |
| `06_signal_aggregation.md` | Agregación de señales. |
| `07_hidden_gems_ranking.md` | Ranking Hidden Gems v1. |
| `08_results_and_validation.md` | Resultados y validación. |
| `09_limitations_and_future_work.md` | Limitaciones y trabajo futuro. |

### Artefactos principales

Algunos de los artefactos más importantes generados por la cadena IA son:

```text
dish_ner_transformer_full/
dish_mentions_model_v1_full.jsonl
dish_mentions_normalized_v2.jsonl
dish_mentions_with_sentiment_hybrid_v1.jsonl
dish_business_ranking_candidates_v1.csv
hidden_gems_selected_candidates_v1.csv
hidden_gems_ranking_summary_v1.json
```

### Nota importante

El ranking descrito en esta sección es un **prototipo basado en Yelp**.

No debe presentarse como ranking gastronómico final de Sevilla. Su objetivo es validar la lógica IA central del sistema: detectar platos, normalizarlos, estimar sentimiento, agregar señales y construir un ranking explicable.

La evolución territorial del proyecto debe incorporar o documentar:

- Google Places;
- OSM / Overpass;
- dataset oficial de barrios/distritos de Sevilla;
- asignación geográfica con PostGIS;
- datos reales o textos disponibles de locales sevillanos;
- validación humana;
- artefactos finales de Sevilla / IA v2, si existen en el repositorio.

En el README principal, esta sección puede convivir con una sección posterior de Sevilla IA v2. La primera explica el prototipo IA; la segunda debe explicar la integración final sobre el contexto real del proyecto.
