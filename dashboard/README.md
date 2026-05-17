# Hidden Gems Dashboards

Este directorio contiene los dashboards Streamlit del proyecto **Hidden Gems**.

Actualmente existen tres dashboards diferenciados:

```text
Dashboard Sevilla IA v2
→ dashboard/streamlit_sevilla_v2_app.py
→ ranking experimental asistido por modelos
→ NER + normalización reranker + ABSA + comparación v1/v2
→ dashboard principal recomendado para la fase actual
```

```text
Dashboard Sevilla Pilot v1
→ dashboard/streamlit_app.py
→ datos reales de Google Places Reviews Sevilla
→ primera aplicación local del concepto Hidden Gems
→ baseline histórico frente a Sevilla IA v2
```

```text
Dashboard Yelp Prototype
→ dashboard/streamlit_yelp_app.py
→ corpus Yelp Open Dataset
→ benchmark/prototipo IA a gran escala
```

La separación es intencionada:

- **Sevilla IA v2** es el dashboard principal de la fase actual. Explota el ranking experimental generado con modelos entrenados y comparación contra el piloto v1.
- **Sevilla Pilot v1** se conserva como baseline local histórico, útil para comparar y entender la evolución del proyecto.
- **Yelp Prototype** se mantiene como benchmark técnico del módulo IA sobre un corpus externo grande.

Ningún dashboard debe interpretarse todavía como producto final de producción.

---

## 1. Dashboard Sevilla IA v2

### Objetivo

Visualizar la fase **Sevilla IA v2**, en la que Hidden Gems evoluciona desde el piloto híbrido/reglado hacia un ranking experimental asistido por modelos.

Flujo conceptual:

```text
Google Places Reviews Sevilla
→ extracción híbrida inicial de menciones
→ NER de platos
→ Hybrid + NER candidates v2
→ normalización / entity linking con reranker
→ sentimiento por mención / ABSA
→ señales place-dish v2
→ ranking Hidden Gems Sevilla v2
→ comparación v1 vs v2
→ dashboard Streamlit Sevilla IA v2
```

Este dashboard permite explorar:

- KPIs principales del ranking IA v2;
- ranking global de candidatos `place + dish`;
- candidatos por distrito;
- candidatos por barrio;
- candidatos por plato;
- candidatos por local;
- mapa territorial con coordenadas reales cuando están disponibles;
- fallback visual por centroides de distrito cuando faltan coordenadas;
- detalle de candidato;
- componentes conceptuales del score;
- evidencia textual con menciones y reseñas;
- distribución de evidencia y calidad;
- comparación entre ranking v1 y ranking v2;
- candidatos nuevos de v2;
- candidatos que estaban en v1 y no en v2;
- contrato de datos del export.

### Estado actual

```text
ranking = sevilla_hidden_gems_ranking_v2
scope lógico = sevilla_ai_v2 / ranking_v2
is_production_ready = false
uso recomendado = análisis, demo, validación y presentación técnica
```

El ranking v2 debe presentarse como:

```text
ranking experimental asistido por modelos
```

No debe presentarse como ranking final de producción porque:

- los candidatos siguen requiriendo revisión humana;
- una parte importante de señales tiene evidencia `emerging`;
- las reseñas públicas pueden estar sesgadas hacia valoraciones positivas;
- el ranking depende de modelos entrenados, catálogo, normalización y umbrales experimentales;
- los scores v2 no son directamente comparables con los scores v1.

### Resultados esperados del export v2

Resumen de la fase IA v2:

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
| Score medio seleccionado | 80,58 |
| Score máximo seleccionado | 91,65 |
| Filas production-ready | 0 |

Comparación esperada con el ranking v1:

| Métrica | Valor |
|---|---:|
| Candidatos únicos v1 | 150 |
| Candidatos únicos v2 | 268 |
| Coincidencias v1/v2 | 119 |
| Solo v1 | 31 |
| Solo v2 | 149 |
| Cobertura de v1 dentro de v2 | 79,3 % |
| Jaccard overlap | 39,8 % |
| Incremento de locales | +76 |
| Incremento de barrios | +12 |

### Generar datos del dashboard Sevilla IA v2

Desde la raíz del repositorio:

```powershell
python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --include-mentions `
  --examples-per-candidate 5 `
  --include-full-review-text `
  --strict
```

Si no se quieren exportar reseñas completas:

```powershell
python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --strict
```

El parámetro `--coordinates-path` permite reutilizar coordenadas del dashboard Sevilla Pilot v1 cuando el export v2 no trae coordenadas completas en sus artefactos principales.

### Ejecutar dashboard Sevilla IA v2

```powershell
streamlit run dashboard/streamlit_sevilla_v2_app.py
```

El dashboard espera por defecto:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

También permite cambiar la carpeta de datos desde la barra lateral.

### Scripts principales asociados a Sevilla IA v2

Los scripts de la fase v2 se dividen en pipeline, comparación, revisión y dashboard.

#### Pipeline IA v2

| Script | Función |
|---|---|
| `scripts/run_sevilla_dish_ner_inference.py` | Ejecuta inferencia del modelo NER de platos sobre reseñas Sevilla. |
| `scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py` | Combina menciones híbridas y menciones NER en una capa unificada. |
| `scripts/run_sevilla_dish_normalization_reranker_v1_fast_progress.py` | Aplica el reranker de normalización/entity linking optimizado para ejecución local. |
| `scripts/run_sevilla_mention_sentiment_absa_v1.py` | Aplica el modelo ABSA para sentimiento por mención. |
| `scripts/build_sevilla_place_dish_signals_v2.py` | Agrega menciones con sentimiento por `place_id + dish_id`. |
| `scripts/build_sevilla_hidden_gems_ranking_v2.py` | Calcula el ranking Hidden Gems Sevilla v2. |

#### Comparación y export

| Script | Función |
|---|---|
| `scripts/compare_sevilla_ranking_v1_vs_v2.py` | Compara ranking Sevilla Pilot v1 contra ranking IA v2. |
| `scripts/export_sevilla_dashboard_data_v2.py` | Genera el contrato limpio para `dashboard_v2`. |

#### Datasets y revisión manual

| Script | Función |
|---|---|
| `scripts/export_sevilla_ner_annotation_dataset.py` | Exporta dataset de anotación NER. |
| `scripts/export_sevilla_dish_normalization_annotation_dataset.py` | Exporta dataset de anotación para normalización/entity linking. |
| `scripts/export_sevilla_mention_sentiment_annotation_dataset.py` | Exporta dataset de anotación para ABSA. |
| `scripts/export_sevilla_ai_manual_review_sample.py` | Genera muestras para revisión manual. |
| `scripts/analyze_sevilla_ai_manual_review_results.py` | Analiza resultados de revisión manual. |

### Orden recomendado si se regenera la fase v2

```text
1. run_sevilla_dish_ner_inference.py
2. build_sevilla_hybrid_ner_mention_candidates_v2.py
3. run_sevilla_dish_normalization_reranker_v1_fast_progress.py
4. run_sevilla_mention_sentiment_absa_v1.py
5. build_sevilla_place_dish_signals_v2.py
6. build_sevilla_hidden_gems_ranking_v2.py
7. compare_sevilla_ranking_v1_vs_v2.py
8. export_sevilla_dashboard_data_v2.py
9. streamlit_sevilla_v2_app.py
```

---

## 2. Dashboard Sevilla Pilot v1

### Objetivo

Visualizar el piloto IA local inicial de Sevilla:

```text
Google Places Reviews Sevilla
→ detección híbrida de platos
→ sentimiento por mención basado en reglas/fallback
→ señales local-plato
→ ranking Hidden Gems Sevilla Pilot v1
→ dashboard Streamlit
```

Este dashboard permite explorar:

- ranking global de Hidden Gems Sevilla Pilot v1;
- candidatos por distrito;
- candidatos por barrio;
- candidatos por plato;
- candidatos por local;
- mapa de candidatos con coordenadas;
- detalle de candidato;
- componentes del score;
- menciones y reseñas asociadas;
- calidad y limitaciones del piloto.

### Estado actual

```text
ranking_scope lógico = sevilla_pilot
ranking_version = sevilla_hidden_gems_ranking_pilot_v1
db_ranking_scope = other
is_production_ready = false
```

El uso de `db_ranking_scope = other` se debe a la restricción actual del DDL. El scope real del artefacto queda conservado en `ranking_config_json` como `artifact_ranking_scope = sevilla_pilot`.

Este dashboard se conserva como:

```text
baseline local histórico y referencia comparativa frente a Sevilla IA v2
```

### Generar datos del dashboard Sevilla Pilot v1

Desde la raíz del repositorio:

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --include-mentions `
  --mention-candidates 150 `
  --examples-per-candidate 5 `
  --include-full-review-text `
  --strict
```

Si no se quieren exportar reseñas completas:

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --strict
```

### Ejecutar dashboard Sevilla Pilot v1

```powershell
streamlit run dashboard/streamlit_app.py
```

---

## 3. Dashboard Yelp Prototype

### Objetivo

Visualizar el prototipo IA construido sobre Yelp Open Dataset:

```text
Yelp Open Dataset
→ reviews gastronómicas
→ detección de platos
→ normalización
→ sentimiento por mención
→ señales local-plato
→ ranking yelp_prototype
→ dashboard Streamlit
```

Este dashboard sirve como benchmark del módulo IA. No representa Sevilla ni debe interpretarse como ranking operativo local.

Permite explorar:

- ranking global Yelp Prototype;
- candidatos por estado;
- candidatos por ciudad;
- candidatos por plato;
- candidatos por local;
- distribución por tier;
- mapa de candidatos;
- componentes del score;
- menciones y reseñas asociadas;
- calidad y limitaciones del prototipo IA.

### Estado actual

```text
ranking_scope = yelp_prototype
ranking_version = hidden_gems_ranking_v1
is_production_ready = false
```

Conteos validados del export actual:

```text
candidates = 622
selected_candidates = 622
selected_places = 430
selected_dishes = 69
selected_cities = 140
selected_states = 39
mention_examples = 300
```

### Generar datos del dashboard Yelp

Desde la raíz del repositorio:

```powershell
python -m scripts.export_yelp_dashboard_data `
  --output-dir data/artifacts/ai/yelp/dashboard `
  --expected-selected 622 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --include-mentions `
  --mention-candidates 100 `
  --examples-per-candidate 3 `
  --include-full-review-text `
  --strict
```

Sin reseñas completas:

```powershell
python -m scripts.export_yelp_dashboard_data `
  --output-dir data/artifacts/ai/yelp/dashboard `
  --expected-selected 622 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --strict
```

### Ejecutar dashboard Yelp

```powershell
streamlit run dashboard/streamlit_yelp_app.py
```

---

## 4. Requisitos

Los dashboards usan principalmente:

```text
streamlit
plotly
pandas
numpy
sqlalchemy
```

Instalación desde el entorno virtual:

```powershell
pip install -r requirements.txt
```

Si falta Streamlit:

```powershell
pip install streamlit
```

Si faltan gráficas Plotly:

```powershell
pip install plotly
```

---

## 5. Estructura esperada de datos

### Sevilla IA v2

```text
data/artifacts/ai/sevilla/dashboard_v2/
├── dashboard_metadata.json
├── kpi_summary.json
├── ranking_detail.csv
├── selected_candidates.csv
├── top_global.csv
├── top_by_district.csv
├── top_by_neighborhood.csv
├── top_by_dish.csv
├── district_summary.csv
├── neighborhood_summary.csv
├── dish_summary.csv
├── place_summary.csv
├── tier_summary.csv
├── evidence_summary.csv
├── quality_summary.csv
├── filter_options.json
├── data_contract.json
├── dashboard_export_summary.json
├── mention_examples.csv
├── place_coordinates.csv
└── comparison/
    ├── sevilla_ranking_v1_vs_v2_summary.json
    ├── ranking_overlap.csv
    ├── v2_only_candidates.csv
    ├── v1_only_candidates.csv
    ├── score_shift_comparison.csv
    ├── tier_shift_summary.csv
    ├── top_district_shift.csv
    ├── top_neighborhood_shift.csv
    └── top_dish_shift.csv
```

### Sevilla Pilot v1

```text
data/artifacts/ai/sevilla/dashboard/
├── dashboard_metadata.json
├── kpi_summary.json
├── candidates_detail.csv
├── candidates_all.csv
├── top_global.csv
├── top_by_district.csv
├── top_by_neighborhood.csv
├── top_by_dish.csv
├── district_summary.csv
├── neighborhood_summary.csv
├── dish_summary.csv
├── place_summary.csv
├── tier_summary.csv
├── quality_summary.csv
├── filter_options.json
├── data_contract.json
├── dashboard_export_summary.json
└── mention_examples.csv
```

### Yelp Prototype

```text
data/artifacts/ai/yelp/dashboard/
├── dashboard_metadata.json
├── kpi_summary.json
├── candidates_detail.csv
├── candidates_all.csv
├── top_global.csv
├── top_by_city.csv
├── top_by_state.csv
├── top_by_dish.csv
├── city_summary.csv
├── state_summary.csv
├── dish_summary.csv
├── place_summary.csv
├── tier_summary.csv
├── quality_summary.csv
├── filter_options.json
├── data_contract.json
├── dashboard_export_summary.json
└── mention_examples.csv
```

---

## 6. Seguridad de datos y Git

Los dashboards pueden funcionar con `mention_examples.csv` que, si se exporta con `--include-full-review-text`, contiene reseñas completas.

No subir a GitHub:

```text
data/artifacts/ai/sevilla/dashboard/*.csv
data/artifacts/ai/sevilla/dashboard/*.json
data/artifacts/ai/sevilla/dashboard_v2/*.csv
data/artifacts/ai/sevilla/dashboard_v2/*.json
data/artifacts/ai/sevilla/dashboard_v2/comparison/*.csv
data/artifacts/ai/sevilla/dashboard_v2/comparison/*.json
data/artifacts/ai/yelp/dashboard/*.csv
data/artifacts/ai/yelp/dashboard/*.json
```

Especialmente:

```text
mention_examples.csv
```

porque puede contener texto de reseñas completas.

Sí se pueden subir:

```text
dashboard/streamlit_app.py
dashboard/streamlit_sevilla_v2_app.py
dashboard/streamlit_yelp_app.py
dashboard/README.md
scripts/export_sevilla_dashboard_data.py
scripts/export_sevilla_dashboard_data_v2.py
scripts/export_yelp_dashboard_data.py
```

También se pueden subir los scripts de pipeline y comparación v2, siempre que no incluyan modelos pesados ni artefactos generados.

No subir modelos ni artefactos pesados:

```text
models/
data/artifacts/ai/sevilla/model_inference/
data/artifacts/ai/sevilla/dashboard_v2/
```

salvo muestras reducidas expresamente preparadas para documentación.

---

## 7. Diferencia entre dashboards

| Dashboard | Fuente | Territorio | Uso | Producción |
|---|---|---|---|---|
| Sevilla IA v2 | Google Places Reviews + modelos IA v2 | Sevilla | Dashboard principal experimental y comparación v1/v2 | No todavía |
| Sevilla Pilot v1 | Google Places Reviews + reglas híbridas | Sevilla | Baseline local histórico | No |
| Yelp Prototype | Yelp Open Dataset | Dataset Yelp | Benchmark IA a gran escala | No |

El dashboard **Sevilla IA v2** es el más importante para la fase actual porque incorpora modelos entrenados, ranking v2, comparación contra v1 y una capa de evidencias más completa.

El dashboard **Sevilla Pilot v1** sigue siendo útil para comparar la evolución desde el primer piloto local.

El dashboard **Yelp Prototype** sirve para demostrar que la cadena IA se validó sobre mayor volumen antes de aplicarla a Sevilla.

---

## 8. Problemas frecuentes

### Streamlit no reconoce `streamlit`

Activar el entorno virtual:

```powershell
.venv\Scripts\activate
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

### El dashboard Sevilla IA v2 dice que faltan archivos

Regenerar los datos:

```powershell
python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --strict
```

### El dashboard Sevilla Pilot v1 dice que faltan archivos

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --strict
```

### El dashboard Yelp dice que faltan archivos

```powershell
python -m scripts.export_yelp_dashboard_data `
  --output-dir data/artifacts/ai/yelp/dashboard `
  --expected-selected 622 `
  --strict
```

### No aparecen reseñas completas

Comprobar que el exportador se ejecutó con:

```powershell
--include-mentions --include-full-review-text
```

En Sevilla IA v2, además, comprobar que `mention_examples.csv` existe dentro de:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

### No aparecen coordenadas reales en el mapa v2

Comprobar que el export se ejecutó con:

```powershell
--coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv
```

y que existe:

```text
data/artifacts/ai/sevilla/dashboard_v2/place_coordinates.csv
```

Si no hay coordenadas reales, el dashboard puede usar fallback aproximado por distrito. Ese fallback es solo visual y no debe interpretarse como ubicación exacta del local.

### Los scores v2 no coinciden con v1

Es normal. El ranking v2 cambia la fórmula de scoring porque incorpora:

- NER;
- normalización con reranker;
- sentimiento ABSA;
- evidencia y calidad v2;
- comparación contra v1;
- penalizaciones nuevas.

Por tanto:

```text
score v2 ≠ score v1
```

La comparación correcta es por solapamiento, cobertura, diversidad, tiers y ejemplos concretos, no por igualdad directa de puntuaciones.

---

## 9. Estado actual

```text
[OK] Dashboard Sevilla IA v2 creado
[OK] Export Sevilla dashboard v2 creado
[OK] Comparación v1 vs v2 integrada
[OK] Dashboard Sevilla Pilot v1 conservado
[OK] Export Sevilla Pilot v1 validado
[OK] Dashboard Yelp funcionando
[OK] Export Yelp dashboard validado
[OK] Requirements actualizados
[OK] Documentación operativa actualizada
```

---

## 10. Recomendación de uso

Para la fase actual del proyecto:

```text
Usar dashboard/streamlit_sevilla_v2_app.py como dashboard principal.
Usar dashboard/streamlit_app.py solo como baseline Sevilla Pilot v1.
Usar dashboard/streamlit_yelp_app.py como benchmark técnico externo.
```

Para presentación o defensa del proyecto, se recomienda empezar por:

1. `streamlit_sevilla_v2_app.py` → resumen ejecutivo.
2. Comparativa v1/v2 → demostrar mejora y continuidad.
3. Territorio → enseñar cobertura por barrios/distritos.
4. Reseñas → demostrar trazabilidad textual.
5. Evidencia y calidad → dejar claro que sigue siendo experimental.

La idea clave que debe transmitirse es:

```text
Hidden Gems no solo lista restaurantes: identifica platos concretos asociados a locales y barrios, con evidencia textual y trazabilidad de IA.
```
