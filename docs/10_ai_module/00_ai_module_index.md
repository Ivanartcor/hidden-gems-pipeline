# 00 — Índice del módulo de IA

## Propósito de este bloque documental

Este directorio documenta la parte de inteligencia artificial desarrollada para **Hidden Gems**.

El módulo de IA no se plantea como un único modelo aislado, sino como una cadena completa de procesamiento inteligente capaz de transformar reseñas gastronómicas en candidatos de platos destacados:

```text
reviews gastronómicas
→ detección de menciones de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

La documentación está pensada para complementar el `README.md` principal del repositorio y explicar con detalle qué se ha construido, qué artefactos genera cada fase, qué resultados se han obtenido y qué limitaciones existen.

> **Nota de actualización del repositorio**  
> Este bloque `docs/10_ai_module/` debe leerse como la documentación técnica completa de la **IA v1 basada en Yelp**. La lógica aquí descrita sigue siendo importante porque valida la cadena NLP central: detección de platos, normalización, sentimiento por mención, agregación y ranking.  
>  
> El repositorio contiene una capa posterior de Sevilla / IA v2, esa capa debe interpretarse como evolución e integración territorial de esta base, no como sustitución de este bloque. Por eso se conservan los resultados Yelp v1 y se matizan las frases que antes podían sonar como estado final absoluto del proyecto.

---

## Estructura de documentos

```text
docs/10_ai_module/
├── 00_ai_module_index.md
├── 01_ai_module_overview.md
├── 02_ai_data_flow_and_artifacts.md
├── 03_dish_detection_ner.md
├── 04_dish_normalization.md
├── 05_mention_sentiment.md
├── 06_signal_aggregation.md
├── 07_hidden_gems_ranking.md
├── 08_results_and_validation.md
├── 09_limitations_and_future_work.md
└── 10_ai_module_readme_section.md
```

---

## Descripción rápida de cada documento

### `00_ai_module_index.md`

Documento índice del bloque de IA. Sirve como punto de entrada para navegar por toda la documentación del módulo.

### `01_ai_module_overview.md`

Explica la visión general del módulo IA:

- objetivo del bloque de IA;
- problema que resuelve;
- división en submódulos;
- relación con el pipeline principal de Hidden Gems;
- estado actual del prototipo.

### `02_ai_data_flow_and_artifacts.md`

Describe el flujo de datos completo y los artefactos generados por cada notebook.

Incluye las entradas y salidas de:

- `04_dish_detection_dataset_exploration.ipynb`
- `05_dish_ner_dataset_builder.ipynb`
- `06_dish_ner_transformer_training.ipynb`
- `07_dish_ner_inference_and_mentions.ipynb`
- `08_dish_normalization_and_catalog_builder.ipynb`
- `09_dish_mention_sentiment_hybrid_v1.ipynb`
- `10_dish_signal_aggregation.ipynb`
- `11_hidden_gems_ranking_v1.ipynb`

### `03_dish_detection_ner.md`

Documenta el detector de platos basado en NER.

Cubre:

- construcción del dataset BIO;
- weak supervision;
- entrenamiento del modelo Transformer;
- métricas de validation/test;
- inferencia sobre corpus Yelp;
- generación de menciones detectadas.

### `04_dish_normalization.md`

Documenta el normalizador de platos.

Explica cómo se pasa de menciones textuales sueltas a un catálogo inicial de platos normalizados:

```text
burgers
burger
cheeseburger
burger with bacon
→ burger / cheeseburger / bacon burger
```

### `05_mention_sentiment.md`

Documenta el módulo de sentimiento por mención de plato.

Explica por qué no basta con usar el rating general de la review y cómo se construyó una versión híbrida centrada en contexto local.

### `06_signal_aggregation.md`

Documenta la agregación de señales.

Explica cómo las menciones individuales se convierten en métricas agregadas por:

- plato global;
- plato + negocio.

### `07_hidden_gems_ranking.md`

Documenta el ranking Hidden Gems v1.

Explica el cálculo de:

- `hidden_gem_score_v1`;
- componentes del score;
- penalizaciones;
- tiers finales;
- rankings globales, por ciudad y por estado.

### `08_results_and_validation.md`

Resume resultados y validación de todo el módulo IA.

Incluye las principales métricas del NER, inferencia, normalización, sentimiento, agregación y ranking.

### `09_limitations_and_future_work.md`

Describe limitaciones y trabajo futuro del módulo IA v1, además de la transición hacia la integración territorial posterior.

Incluye:

- uso de Yelp en inglés como base experimental de IA v1;
- ausencia de barrios de Sevilla dentro del ranking Yelp v1;
- relación con la evolución posterior hacia Sevilla / IA v2;
- sentimiento weak-supervised;
- necesidad de validación humana;
- futura adaptación robusta a español;
- futuro modelo ABSA;
- futuro learning-to-rank.

### `10_ai_module_readme_section.md`

Bloque preparado para copiar y pegar en el `README.md` principal del repositorio.

Resume brevemente el módulo IA y enlaza al resto de documentación.

---

## Estado actual del módulo IA

La primera versión funcional de la cadena IA ya está completada hasta ranking:

```text
04 → exploración de candidatos de platos
05 → dataset BIO para NER
06 → entrenamiento Dish NER Transformer
07 → inferencia y generación de menciones
08 → normalización de platos
09 → sentimiento por mención híbrido
10 → agregación de señales
11 → ranking Hidden Gems v1
```

El ranking v1 descrito en esta carpeta es un **prototipo basado en Yelp** y no debe confundirse con la evolución territorial posterior del proyecto. Su papel dentro del repositorio es servir como base técnica y experimental de la lógica IA.

La evolución hacia datos reales de Sevilla, asignación por barrios, integración geográfica y posibles salidas de Sevilla IA v2 debe documentarse en la capa correspondiente del repositorio. Este bloque mantiene valor propio porque conserva la trazabilidad completa de cómo se validó la cadena IA original.

---

## Artefactos principales del bloque IA

Los artefactos más importantes generados por la cadena son:

```text
dish_ner_transformer_full/
dish_mentions_model_v1_full.jsonl
dish_mentions_normalized_v2.jsonl
dish_mentions_with_sentiment_hybrid_v1.jsonl
dish_business_ranking_candidates_v1.csv
hidden_gems_selected_candidates_v1.csv
hidden_gems_ranking_summary_v1.json
```

Estos archivos representan el recorrido completo desde el modelo detector de platos hasta el ranking final de candidatos Hidden Gems.

---

## Nota sobre versionado

Los archivos pesados de datos, modelos y predicciones no deberían subirse directamente al repositorio si exceden un tamaño razonable.

Se recomienda versionar en GitHub:

- documentación `.md`;
- notebooks;
- scripts ligeros;
- muestras pequeñas;
- `.json` de resumen;
- `.csv` finales si su tamaño es asumible.

Los modelos entrenados y datasets pesados deberían conservarse en Kaggle, Google Drive, Hugging Face, almacenamiento externo o releases controladas.
