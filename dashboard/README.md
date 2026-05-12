# Hidden Gems Dashboards

Este directorio contiene los dashboards Streamlit del proyecto **Hidden Gems**.

Actualmente existen dos dashboards diferenciados:

```text
Dashboard Sevilla Pilot
→ dashboard/streamlit_app.py
→ datos reales de Google Places Reviews Sevilla
→ aplicación local del concepto Hidden Gems
```

```text
Dashboard Yelp Prototype
→ dashboard/streamlit_yelp_app.py
→ corpus Yelp Open Dataset
→ benchmark/prototipo IA a gran escala
```

La separación es intencionada. Sevilla representa el caso de uso local del producto; Yelp representa la validación técnica del módulo IA sobre un corpus más grande.

---

## 1. Dashboard Sevilla Pilot

### Objetivo

Visualizar el piloto IA local de Sevilla:

```text
Google Places Reviews Sevilla
→ detección de platos
→ sentimiento por mención
→ señales local-plato
→ ranking Hidden Gems Sevilla
→ dashboard Streamlit
```

Este dashboard permite explorar:

- ranking global de Hidden Gems Sevilla;
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
db_ranking_scope = other
is_production_ready = false
```

El uso de `db_ranking_scope = other` se debe a la restricción actual del DDL. El scope real del artefacto queda conservado en `ranking_config_json` como `artifact_ranking_scope = sevilla_pilot`.

### Generar datos del dashboard Sevilla

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

### Ejecutar dashboard Sevilla

```powershell
streamlit run dashboard/streamlit_app.py
```

---

## 2. Dashboard Yelp Prototype

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

## 3. Requisitos

Los dashboards usan principalmente:

```text
streamlit
plotly
pandas
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

## 4. Estructura esperada de datos

### Sevilla

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

### Yelp

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

## 5. Seguridad de datos y Git

Los dashboards pueden funcionar con `mention_examples.csv` que, si se exporta con `--include-full-review-text`, contiene reseñas completas.

No subir a GitHub:

```text
data/artifacts/ai/sevilla/dashboard/*.csv
data/artifacts/ai/sevilla/dashboard/*.json
data/artifacts/ai/yelp/dashboard/*.csv
data/artifacts/ai/yelp/dashboard/*.json
```

Especialmente:

```text
mention_examples.csv
```

Sí se pueden subir:

```text
dashboard/streamlit_app.py
dashboard/streamlit_yelp_app.py
dashboard/README.md
scripts/export_sevilla_dashboard_data.py
scripts/export_yelp_dashboard_data.py
```

---

## 6. Diferencia entre dashboards

| Dashboard | Fuente | Territorio | Uso | Producción |
|---|---|---|---|---|
| Sevilla Pilot | Google Places Reviews | Sevilla | Demo local del producto | No todavía |
| Yelp Prototype | Yelp Open Dataset | Dataset Yelp | Benchmark IA | No |

El dashboard de Sevilla es el más cercano al producto real.

El dashboard de Yelp sirve para demostrar que la cadena IA se validó sobre mayor volumen antes de aplicarla a Sevilla.

---

## 7. Problemas frecuentes

### Streamlit no reconoce `streamlit`

Activar el entorno virtual:

```powershell
.venv\Scripts\activate
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

### El dashboard dice que faltan archivos

Regenerar los datos:

```powershell
python -m scripts.export_sevilla_dashboard_data --output-dir data/artifacts/ai/sevilla/dashboard --expected-selected 150 --strict
```

O para Yelp:

```powershell
python -m scripts.export_yelp_dashboard_data --output-dir data/artifacts/ai/yelp/dashboard --expected-selected 622 --strict
```

### Error de Plotly por elementos duplicados

Usar la versión actualizada de `streamlit_yelp_app.py`, donde cada `st.plotly_chart(...)` tiene una clave única.

### No aparecen reseñas completas

Comprobar que el exportador se ejecutó con:

```powershell
--include-mentions --include-full-review-text
```

---

## 8. Estado actual

```text
[OK] Dashboard Sevilla funcionando
[OK] Export Sevilla dashboard validado
[OK] Dashboard Yelp funcionando
[OK] Export Yelp dashboard validado
[OK] Requirements actualizados
[OK] Documentación operativa creada
```

