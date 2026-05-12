# 09. Dashboard operations

## 1. Propósito

Este documento describe cómo operar los dashboards Streamlit de Hidden Gems.

Los dashboards no sustituyen al pipeline ni a PostgreSQL. Son una capa de visualización para explorar resultados ya generados, cargados, validados y exportados.

Actualmente existen dos dashboards:

```text
1. Dashboard Sevilla Pilot
2. Dashboard Yelp Prototype
```

La lógica general es:

```text
PostgreSQL / vistas IA
→ script de exportación
→ CSV/JSON limpios en data/artifacts
→ Streamlit dashboard
```

---

## 2. Dashboards disponibles

## 2.1. Sevilla Pilot

Archivo:

```text
dashboard/streamlit_app.py
```

Datos esperados:

```text
data/artifacts/ai/sevilla/dashboard/
```

Objetivo:

```text
Mostrar el piloto IA local de Sevilla basado en Google Places Reviews.
```

Estado:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
```

Este dashboard es el más cercano al producto final de Hidden Gems, porque trabaja con locales reales de Sevilla, barrios, distritos y reseñas reales de Google Places.

---

## 2.2. Yelp Prototype

Archivo:

```text
dashboard/streamlit_yelp_app.py
```

Datos esperados:

```text
data/artifacts/ai/yelp/dashboard/
```

Objetivo:

```text
Mostrar el prototipo IA/benchmark construido sobre Yelp Open Dataset.
```

Estado:

```text
ranking_scope = yelp_prototype
ranking_version = hidden_gems_ranking_v1
is_production_ready = false
```

Este dashboard no representa el producto final de Sevilla. Sirve para demostrar que la cadena IA se validó sobre un corpus amplio.

---

## 3. Requisitos

Los dashboards requieren tener instalado el entorno del proyecto:

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
```

Dependencias principales:

```text
streamlit
plotly
pandas
sqlalchemy
```

---

## 4. Generación de datos del dashboard Sevilla

Comando completo recomendado:

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

Comando sin reseñas completas:

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --strict
```

Checks esperados:

```text
has_candidates = true
has_selected_candidates = true
expected_selected_matches = true
score_in_0_100 = true
selected_have_place = true
selected_have_dish = true
selected_have_neighborhood = true
selected_have_district = true
selected_have_coordinates = true
global_ranks_are_unique = true
all_selected_are_not_production_ready = true
artifact_scope_ok = true
db_ranking_scope_ok = true
```

---

## 5. Generación de datos del dashboard Yelp

Comando completo recomendado:

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

Comando sin reseñas completas:

```powershell
python -m scripts.export_yelp_dashboard_data `
  --output-dir data/artifacts/ai/yelp/dashboard `
  --expected-selected 622 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --strict
```

Conteos validados del export actual:

```text
all_candidates = 622
selected_candidates = 622
selected_places = 430
selected_dishes = 69
selected_cities = 140
selected_states = 39
mention_examples_rows = 300
```

Checks esperados:

```text
has_candidates = true
has_selected_candidates = true
expected_selected_matches = true
score_in_0_100 = true
selected_have_place = true
selected_have_dish = true
global_ranks_are_unique = true
all_selected_are_not_production_ready = true
ranking_scope_ok = true
```

---

## 6. Ejecución de dashboards

## 6.1. Ejecutar Sevilla Pilot

```powershell
streamlit run dashboard/streamlit_app.py
```

## 6.2. Ejecutar Yelp Prototype

```powershell
streamlit run dashboard/streamlit_yelp_app.py
```

---

## 7. Archivos generados por los exportadores

## 7.1. Sevilla

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

## 7.2. Yelp

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

## 8. Uso de reseñas completas

Los dashboards pueden mostrar reseñas completas en una vista de detalle si el exportador se ejecutó con:

```powershell
--include-mentions --include-full-review-text
```

Regla operativa:

```text
Las reseñas completas no deben aparecer en la vista principal.
Solo deben mostrarse bajo un desplegable o detalle opcional.
```

Motivo:

```text
- evitar saturar la interfaz;
- mantener una presentación limpia;
- reducir exposición innecesaria de texto completo;
- dejar claro que es contenido de apoyo/auditoría.
```

---

## 9. Qué no subir a Git

No versionar datos exportados del dashboard:

```text
data/artifacts/ai/sevilla/dashboard/*.csv
data/artifacts/ai/sevilla/dashboard/*.json
data/artifacts/ai/yelp/dashboard/*.csv
data/artifacts/ai/yelp/dashboard/*.json
```

Especialmente si contienen reseñas completas:

```text
mention_examples.csv
```

Sí versionar:

```text
dashboard/streamlit_app.py
dashboard/streamlit_yelp_app.py
dashboard/README.md
scripts/export_sevilla_dashboard_data.py
scripts/export_yelp_dashboard_data.py
docs/08_operations/09_dashboard_operations.md
```

---

## 10. Secciones principales de los dashboards

## 10.1. Sevilla Pilot

```text
1. Resumen ejecutivo
2. KPIs principales
3. Top Hidden Gems Sevilla
4. Filtros por distrito, barrio, plato, local, tier y score
5. Mapa de candidatos
6. Exploración territorial
7. Exploración por plato
8. Exploración por local
9. Detalle de candidato
10. Menciones y reseñas asociadas
11. Calidad y limitaciones
```

## 10.2. Yelp Prototype

```text
1. Resumen del benchmark IA
2. KPIs principales
3. Top Hidden Gems Yelp
4. Filtros por estado, ciudad, plato, local, tier y score
5. Mapa de candidatos
6. Exploración por ciudad y estado
7. Exploración por plato
8. Exploración por local
9. Detalle de candidato
10. Menciones y reseñas asociadas
11. Calidad y limitaciones
```

---

## 11. Interpretación correcta

## 11.1. Sevilla

Debe presentarse como:

```text
Piloto IA local sobre Sevilla.
```

No debe presentarse como:

```text
Ranking productivo final.
```

Motivo:

```text
is_production_ready = false
```

---

## 11.2. Yelp

Debe presentarse como:

```text
Benchmark IA / prototipo a gran escala.
```

No debe presentarse como:

```text
Producto local de Sevilla.
```

Motivo:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 12. Problemas frecuentes

### 12.1. Faltan archivos CSV o JSON

Regenerar el export correspondiente.

Sevilla:

```powershell
python -m scripts.export_sevilla_dashboard_data --output-dir data/artifacts/ai/sevilla/dashboard --expected-selected 150 --strict
```

Yelp:

```powershell
python -m scripts.export_yelp_dashboard_data --output-dir data/artifacts/ai/yelp/dashboard --expected-selected 622 --strict
```

---

### 12.2. Streamlit no encuentra dependencias

```powershell
pip install -r requirements.txt
```

---

### 12.3. Error `StreamlitDuplicateElementId`

Este error aparece cuando dos gráficos tienen el mismo identificador automático.

Solución:

```text
usar la versión actualizada del dashboard donde cada st.plotly_chart tiene key única.
```

---

### 12.4. Error de slider por tipos int/float

Streamlit exige que `value`, `min_value` y `max_value` tengan el mismo tipo.

Solución:

```text
usar value como float cuando min_value y max_value son float.
```

---

## 13. Flujo recomendado para regenerar dashboard

Cuando cambien datos, ranking o scripts:

```text
1. Ejecutar pipeline o loader correspondiente.
2. Ejecutar checks de base de datos.
3. Ejecutar exportador de dashboard.
4. Revisar dashboard_export_summary.json.
5. Ejecutar Streamlit.
6. Revisar visualmente resultados.
```

---

## 14. Estado actual

```text
[OK] Dashboard Sevilla creado y funcionando
[OK] Export Sevilla validado
[OK] Dashboard Yelp creado y funcionando
[OK] Export Yelp validado
[OK] Requirements actualizados
[OK] README de dashboard creado
[OK] Operaciones de dashboard documentadas
```

---

## 15. Siguientes mejoras posibles

```text
1. Crear app multipágina de Streamlit con Sevilla y Yelp en una sola interfaz.
2. Añadir modo comparativo Sevilla vs Yelp.
3. Añadir export a HTML/PDF para presentación.
4. Añadir capturas para memoria técnica.
5. Crear versión ligera sin reseñas completas para compartir.
6. Crear API sobre los mismos datos del dashboard.
```

