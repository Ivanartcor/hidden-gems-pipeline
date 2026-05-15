# 00. Índice de la fase Sevilla IA v2

## 1. Propósito de esta carpeta

Esta carpeta documenta la fase **Sevilla IA v2** del proyecto **Hidden Gems Pipeline**. El objetivo de esta fase ha sido evolucionar el ranking piloto inicial hacia un flujo más robusto basado en modelos entrenados, manteniendo trazabilidad completa desde las reseñas originales hasta el dashboard final.

La fase IA v2 introduce tres capacidades principales:

1. **Detección mejorada de menciones de platos** mediante un modelo NER entrenado.
2. **Normalización / entity linking** de menciones hacia un catálogo de platos mediante un reranker entrenado.
3. **Sentimiento por mención / ABSA** para valorar el sentimiento hacia cada plato concreto, no hacia la reseña completa.

El resultado final es un nuevo ranking experimental:

```text
sevilla_hidden_gems_ranking_v2
```

Este ranking se explota mediante un nuevo dashboard Streamlit:

```text
dashboard/streamlit_sevilla_v2_app.py
```

---

## 2. Documentos de la fase

| Archivo | Tema principal | Descripción |
|---|---|---|
| `00_index.md` | Índice | Navegación general de la fase IA v2. |
| `01_phase_overview.md` | Resumen ejecutivo | Explica qué se ha hecho, por qué y qué resultados se han obtenido. |
| `02_v2_pipeline_overview.md` | Arquitectura del flujo v2 | Describe el pipeline completo desde reseñas hasta dashboard. |
| `03_datasets_and_annotation.md` | Datasets y anotación | Documenta los datasets extendidos usados para entrenar NER, normalización y ABSA. |
| `04_model_1_dish_ner.md` | Modelo 1: NER de platos | Entrenamiento y uso del modelo de detección de menciones de platos. |
| `05_model_3_dish_normalization_reranker.md` | Modelo 3: normalización / entity linking | Entrenamiento y uso del reranker para enlazar menciones con `dish_id`. |
| `06_model_2_mention_sentiment_absa.md` | Modelo 2: ABSA | Entrenamiento y uso del modelo de sentimiento por mención. |
| `07_hybrid_ner_candidates_v2.md` | Capa Hybrid + NER v2 | Combinación de menciones híbridas y menciones detectadas por NER. |
| `08_normalization_inference_v2.md` | Inferencia de normalización | Aplicación local del reranker de normalización. |
| `09_sentiment_inference_v2.md` | Inferencia ABSA | Aplicación local del modelo de sentimiento por mención. |
| `10_place_dish_signals_v2.md` | Señales place-dish | Agregación de menciones por `place_id + dish_id`. |
| `11_hidden_gems_ranking_v2.md` | Ranking Hidden Gems v2 | Cálculo del `hidden_gem_score_v2` y selección final. |
| `12_ranking_v1_vs_v2_comparison.md` | Comparación v1 vs v2 | Análisis de solapamiento, mejoras y candidatos nuevos. |
| `13_dashboard_v2.md` | Dashboard Sevilla IA v2 | Funcionamiento del dashboard y sus pestañas. |
| `14_artifacts_and_data_contracts.md` | Artefactos y contratos | Entradas, salidas y granularidad de los ficheros generados. |
| `15_limitations_and_risks.md` | Limitaciones | Riesgos técnicos, sesgos y cautelas de interpretación. |
| `16_next_steps.md` | Próximos pasos | Roadmap posterior a la fase IA v2. |

---

## 3. Resumen rápido de la fase

La fase IA v2 parte del trabajo previo de Sevilla IA piloto, pero sustituye varias reglas débiles por modelos entrenados y capas intermedias más trazables.

Flujo simplificado:

```text
Reseñas Sevilla
→ extracción híbrida inicial
→ Modelo NER de platos
→ Hybrid + NER candidates v2
→ Normalización / entity linking con reranker
→ Sentimiento por mención / ABSA
→ Señales place-dish v2
→ Ranking Hidden Gems Sevilla v2
→ Comparación v1 vs v2
→ Dashboard Sevilla IA v2
```

Resultado principal del ranking v2:

| Métrica | Valor |
|---|---:|
| Candidatos puntuados | 2.335 |
| Candidatos seleccionados | 268 |
| Locales seleccionados | 198 |
| Platos seleccionados | 40 |
| Barrios seleccionados | 67 |
| Distritos seleccionados | 11 |
| Menciones usadas en seleccionados | 651 |
| Reviews usadas en seleccionados | 627 |

---

## 4. Comparación rápida con el ranking v1

La fase v2 no sustituye el ranking v1 de forma ciega. Se ha comparado contra el ranking piloto anterior para medir continuidad y mejora.

| Métrica | Valor |
|---|---:|
| Candidatos únicos seleccionados v1 | 150 |
| Candidatos únicos seleccionados v2 | 268 |
| Candidatos coincidentes | 119 |
| Candidatos solo v1 | 31 |
| Candidatos solo v2 | 149 |
| Cobertura de v1 dentro de v2 | 79,3 % |
| Solapamiento Jaccard | 39,8 % |
| Incremento de locales seleccionados | +76 |
| Incremento de barrios seleccionados | +12 |

Interpretación:

- El v2 conserva gran parte del ranking piloto v1.
- El v2 amplía notablemente la cobertura de locales y barrios.
- El v2 debe interpretarse como una versión experimental asistida por modelos, no como ranking de producción.

---

## 5. Principales artefactos generados

Los artefactos de la fase se concentran en:

```text
data/artifacts/ai/sevilla/model_inference/
```

y en:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Carpetas principales:

| Carpeta | Contenido |
|---|---|
| `hybrid_ner_v2/` | Candidatos de menciones combinando sistema híbrido + NER. |
| `normalization_reranker_v1/` | Menciones normalizadas con `dish_id`. |
| `sentiment_absa_v1/` | Menciones con sentimiento ABSA. |
| `place_dish_signals_v2/` | Señales agregadas por `place_id + dish_id`. |
| `ranking_v2/` | Ranking IA v2 completo y candidatos seleccionados. |
| `ranking_v2_comparison/` | Comparación entre ranking v1 y ranking v2. |
| `dashboard_v2/` | Export limpio preparado para Streamlit. |

---

## 6. Scripts principales de la fase

| Script | Función |
|---|---|
| `scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py` | Combina menciones híbridas y menciones NER. |
| `scripts/run_sevilla_dish_normalization_reranker_v1.py` | Aplica el modelo de normalización / entity linking. |
| `scripts/run_sevilla_mention_sentiment_absa_v1.py` | Aplica el modelo ABSA por mención. |
| `scripts/build_sevilla_place_dish_signals_v2.py` | Agrega menciones por local y plato. |
| `scripts/build_sevilla_hidden_gems_ranking_v2.py` | Calcula el ranking IA v2. |
| `scripts/compare_sevilla_ranking_v1_vs_v2.py` | Compara ranking v1 contra ranking v2. |
| `scripts/export_sevilla_dashboard_data_v2.py` | Exporta datos limpios para el dashboard v2. |

---

## 7. Dashboard asociado

El dashboard de esta fase se encuentra en:

```text
dashboard/streamlit_sevilla_v2_app.py
```

Ejecución:

```powershell
streamlit run dashboard/streamlit_sevilla_v2_app.py
```

El dashboard consume por defecto:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Incluye:

- resumen ejecutivo;
- ranking IA v2;
- análisis territorial;
- mapa con coordenadas reales cuando están disponibles;
- análisis de platos y locales;
- evidencia y calidad;
- comparación v1 vs v2;
- detalle de menciones y reseñas;
- explicación de la puntuación;
- contrato de datos y artefactos.

---

## 8. Estado de madurez

El ranking IA v2 debe presentarse como:

```text
ranking experimental asistido por modelos
```

No debe presentarse como ranking de producción porque:

- todos los candidatos seleccionados siguen marcados como no productivos;
- muchas señales tienen evidencia `emerging`;
- las reseñas públicas tienden a estar sesgadas hacia valoraciones positivas;
- todavía quedan casos revisables de normalización y menciones experimentales;
- el catálogo de platos puede seguir ampliándose.

Aun así, la fase es válida como avance técnico porque demuestra un pipeline completo de IA aplicada al dominio Hidden Gems.
