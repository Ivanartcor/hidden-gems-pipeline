# Nota de actualización


# 03 - AI Query Layer

## Objetivo

Este documento describe la capa de consulta creada sobre las tablas IA de Hidden Gems.

Una vez cargados los datos IA en PostgreSQL, se creó una capa de vistas SQL y scripts de demo para facilitar:

- exploración de rankings;
- auditoría de señales;
- revisión de menciones;
- exportación de resultados;
- demostración del prototipo Yelp;
- demostración del piloto local Sevilla.

La implementación SQL principal está en:

```text
db/ddl/08_ai_views.sql
```

Para Sevilla IA v2 existe además una capa de consulta basada en artefactos exportados para dashboard:

```text
data/artifacts/ai/sevilla/dashboard_v2/
dashboard/streamlit_sevilla_v2_app.py
```

Esta segunda capa no reemplaza a las vistas SQL. Actúa como capa de explotación visual del ranking v2 y consume CSV/JSON exportados.

---

## Por qué crear vistas

Las tablas IA están normalizadas:

```text
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Esto es correcto para integridad y mantenimiento, pero no es cómodo para consulta directa.

Las vistas permiten tener salidas legibles para:

- ver rankings;
- consultar candidatos;
- auditar señales;
- revisar menciones justificativas;
- exportar resultados para demo o análisis;
- alimentar un futuro dashboard.

---

## Vistas creadas

```text
vw_ai_pipeline_run_summary
vw_ai_dish_place_signals
vw_ai_hidden_gem_candidate_detail
vw_ai_hidden_gems_yelp_top
vw_ai_hidden_gems_place_summary
vw_ai_hidden_gems_dish_summary
vw_ai_hidden_gems_city_summary
vw_ai_dish_mentions_with_sentiment
```

La vista más general y reutilizable es:

```text
vw_ai_hidden_gem_candidate_detail
```

Es la base para consultar tanto Yelp prototype como Sevilla pilot.

---

# 1. `vw_ai_pipeline_run_summary`

Permite consultar ejecuciones IA registradas:

```sql
SELECT *
FROM hidden_gems.vw_ai_pipeline_run_summary
ORDER BY started_at DESC;
```

Sirve para revisar:

- código del run;
- tipo de ejecución;
- estado;
- fechas;
- métricas;
- artefactos de entrada/salida.

---

# 2. `vw_ai_dish_place_signals`

Consulta señales agregadas por local y plato.

Ejemplo:

```sql
SELECT
    place_name,
    dish_name,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio,
    bayesian_sentiment_score,
    evidence_tier
FROM hidden_gems.vw_ai_dish_place_signals
WHERE is_rankable_candidate = true
ORDER BY bayesian_sentiment_score DESC
LIMIT 50;
```

Sirve para responder:

```text
¿Qué platos tienen mejor señal en cada local?
¿Qué locales tienen más menciones positivas para un plato?
¿Qué pares local-plato tienen evidencia suficiente?
```

---

# 3. `vw_ai_hidden_gem_candidate_detail`

Vista detallada de candidatos Hidden Gems.

Une:

```text
hidden_gem_candidate
+ dish_place_signal
+ place
+ dish
+ neighborhood/district cuando aplica
```

Incluye:

- ranking;
- tier;
- local;
- plato;
- score;
- componentes;
- penalizaciones;
- evidencia;
- barrio/distrito;
- explicación textual.

Ejemplo general:

```sql
SELECT
    hidden_gem_selected_rank,
    hidden_gem_tier,
    place_name,
    dish_name,
    hidden_gem_score,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio,
    ranking_explanation
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
ORDER BY hidden_gem_selected_rank
LIMIT 30;
```

---

# 4. Consulta Yelp prototype

Vista simplificada:

```text
vw_ai_hidden_gems_yelp_top
```

Consulta:

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_yelp_top
LIMIT 20;
```

Script:

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

Detalle con menciones:

```powershell
python -m scripts.query_ai_ranking_demo `
  --place-name "Sushi Ushi" `
  --dish-name "sushi" `
  --include-mentions `
  --mentions-top-n 25
```

Estado:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

# 5. Consulta Sevilla pilot

Script principal:

```text
scripts/query_sevilla_hidden_gems_demo.py
```

Este script usa la capa de vistas IA y aplica filtros específicos para el piloto Sevilla:

```text
artifact_ranking_scope = sevilla_pilot
ranking_scope en DB = other
is_selected = true
is_production_ready = false
```

Ejemplo global:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

Filtro por distrito:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --district "Casco Antiguo" `
  --limit 20
```

Filtro por barrio:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --neighborhood "TRIANA" `
  --limit 20
```

Filtro por plato:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --dish "tarta de queso" `
  --limit 20
```

Detalle con menciones:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --place-name "Golondrinas" `
  --include-mentions `
  --limit 10
```

---

## 6. Capa de consulta Sevilla IA v2

La fase Sevilla IA v2 añade una capa de consulta orientada a dashboard.

No depende directamente de las vistas SQL anteriores, sino de un export limpio generado desde los artefactos v2.

Script productor:

```text
scripts/export_sevilla_dashboard_data_v2.py
```

Dashboard:

```text
dashboard/streamlit_sevilla_v2_app.py
```

Carpeta consumida:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Archivos principales:

```text
ranking_detail.csv
selected_candidates.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
district_summary.csv
neighborhood_summary.csv
dish_summary.csv
place_summary.csv
tier_summary.csv
evidence_summary.csv
quality_summary.csv
mention_examples.csv
place_coordinates.csv
comparison/
data_contract.json
dashboard_metadata.json
dashboard_export_summary.json
```

Granularidades principales:

| Archivo | Granularidad |
|---|---|
| `ranking_detail.csv` | Un candidato/señal place-dish puntuado. |
| `selected_candidates.csv` | Un candidato seleccionado como Hidden Gem v2. |
| `mention_examples.csv` | Una mención/reseña asociada a un candidato seleccionado. |
| `district_summary.csv` | Un distrito. |
| `neighborhood_summary.csv` | Un barrio. |
| `dish_summary.csv` | Un plato. |
| `place_summary.csv` | Un local. |

El dashboard permite consultar:

```text
- ranking global v2;
- filtros por distrito, barrio, plato, local, tier, evidencia y calidad;
- mapa territorial;
- análisis de platos y locales;
- evidencia y calidad;
- comparación v1 vs v2;
- menciones y reseñas justificativas;
- explicación del score.
```

Estado:

```text
ranking_type = experimental model-assisted
selected_candidates = 268
production_ready_count_v2 = 0
```

---

# 7. Outputs del script Sevilla demo

El script genera:

```text
data/artifacts/ai/sevilla/query_demo/
  sevilla_demo_top_global.csv
  sevilla_demo_top_by_district.csv
  sevilla_demo_top_by_neighborhood.csv
  sevilla_demo_top_by_dish.csv
  sevilla_demo_district_summary.csv
  sevilla_demo_neighborhood_summary.csv
  sevilla_demo_dish_summary.csv
  sevilla_demo_place_summary.csv
  sevilla_hidden_gems_query_demo_report.json
```

Estos ficheros son candidatos naturales para alimentar el dashboard inicial.

---

## 8. Resultados de consulta Sevilla pilot

La consulta demo validó que el ranking es explotable por:

- top global;
- distrito;
- barrio;
- plato;
- local;
- detalle con menciones.

Ejemplo de top en Casco Antiguo:

```text
Il Ristorantino Dell'Avvocato Calle Cuna → pizza
Tarannà → atún
Il Ristorantino Dell´Avvocato Sevilla → pizza
Taberna Los Terceros → solomillo al whisky
```

Resumen global validado:

```text
selected_hidden_gem_candidates = 150
selected_places = 122
selected_dishes = 38
selected_neighborhoods = 55
selected_districts = 11
ready_for_sevilla_pilot_queries = true
```

---

## 9. Consultas SQL útiles

### Top candidatos genérico

```sql
SELECT
    hidden_gem_selected_rank,
    hidden_gem_tier,
    place_name,
    dish_name,
    hidden_gem_score,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
WHERE is_selected = true
ORDER BY hidden_gem_selected_rank
LIMIT 30;
```

### Top candidatos Sevilla pilot

```sql
SELECT
    hidden_gem_selected_rank,
    hidden_gem_tier,
    place_name,
    dish_name,
    hidden_gem_score,
    district_name,
    neighborhood_name,
    ranking_explanation
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
WHERE is_selected = true
  AND is_production_ready = false
  AND ranking_scope = 'other'
  AND ranking_config_json->>'artifact_ranking_scope' = 'sevilla_pilot'
ORDER BY hidden_gem_selected_rank
LIMIT 30;
```

### Top por distrito

```sql
SELECT
    district_name,
    COUNT(*) AS selected_count,
    COUNT(DISTINCT place_id) AS selected_places,
    COUNT(DISTINCT dish_id) AS selected_dishes,
    ROUND(AVG(hidden_gem_score)::numeric, 4) AS avg_score,
    MAX(hidden_gem_score) AS max_score
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
WHERE is_selected = true
  AND ranking_scope = 'other'
  AND ranking_config_json->>'artifact_ranking_scope' = 'sevilla_pilot'
GROUP BY district_name
ORDER BY max_score DESC;
```

### Auditoría de menciones de un candidato

```sql
SELECT
    place_name,
    dish_name,
    mention_text,
    sentiment_label,
    sentiment_confidence,
    target_clause_context
FROM hidden_gems.vw_ai_dish_mentions_with_sentiment
WHERE place_name ILIKE '%Golondrinas%'
ORDER BY sentiment_confidence DESC
LIMIT 25;
```

---

## 10. Estado de la capa de consulta

```text
[OK] 08_ai_views.sql cargado en PostgreSQL
[OK] query_ai_ranking_demo.py funcional para Yelp prototype
[OK] query_sevilla_hidden_gems_demo.py funcional para Sevilla pilot
[OK] vistas devuelven candidatos, señales y menciones justificativas
[OK] exports CSV/JSON disponibles para dashboard
```

---

## 11. Próxima evolución de la query layer

El contrato de datos del dashboard v2 ya está definido mediante:

```text
data/artifacts/ai/sevilla/dashboard_v2/data_contract.json
```

y se apoya en estos bloques:

```text
Top global
Top por distrito
Top por barrio
Top por plato
Detalle de candidato
Resumen por local
Resumen por plato
Menciones justificativas
Comparación v1/v2
Evidencia y calidad
Coordenadas
```

Opciones de consumo:

```text
1. CSV/JSON exportados por query_sevilla_hidden_gems_demo.py para Sevilla pilot v1.
2. CSV/JSON exportados por export_sevilla_dashboard_data_v2.py para Sevilla IA v2.
3. Consulta directa a PostgreSQL desde Streamlit si se carga v2 en DB.
4. API intermedia con FastAPI en una fase posterior.
```

Para el dashboard v2, la opción documentada y validada es usar los CSV/JSON de `dashboard_v2/`. Para una versión más cercana a producto, la opción posterior sería API o conexión directa a PostgreSQL.
