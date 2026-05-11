# 09. Operación del dashboard Hidden Gems Sevilla

## 1. Propósito del documento

Este documento describe cómo operar el dashboard del piloto IA de **Hidden Gems Sevilla**.

El dashboard permite visualizar los resultados del ranking `sevilla_pilot` generado a partir de reviews reales de Google Places, procesadas por el flujo IA del proyecto y cargadas en PostgreSQL.

Su función es servir como capa de presentación para:

```text
- demostrar el valor del MVP;
- explorar candidatos Hidden Gems;
- revisar resultados por distrito, barrio, plato y local;
- inspeccionar explicaciones del ranking;
- detectar errores o mejoras necesarias en la IA;
- preparar presentaciones técnicas o académicas.
```

---

## 2. Relación con el flujo general

El dashboard es la última capa del flujo operativo actual:

```text
Google Places Reviews
→ hidden_gems.review
→ export_reviews_for_ai.py
→ notebooks IA Sevilla 12-17
→ load_sevilla_ai_pilot_outputs.py
→ check_sevilla_ai_pilot_loaded.py
→ export_sevilla_dashboard_data.py
→ dashboard/streamlit_app.py
```

No sustituye a PostgreSQL ni a los checks. El dashboard consume datos ya preparados por un exportador.

---

## 3. Archivos implicados

### Script de dashboard

```text
dashboard/streamlit_app.py
```

### Documentación rápida

```text
dashboard/README.md
```

### Exportador de datos

```text
scripts/export_sevilla_dashboard_data.py
```

### Query demo relacionado

```text
scripts/query_sevilla_hidden_gems_demo.py
```

### Carpeta de datos generada

```text
data/artifacts/ai/sevilla/dashboard/
```

---

## 4. Dependencias

El dashboard requiere:

```text
streamlit
plotly
pandas
```

Estas dependencias deben estar en `requirements.txt`.

Si hace falta instalarlas manualmente:

```powershell
pip install streamlit plotly pandas
```

---

## 5. Preparación previa

Antes de ejecutar el dashboard, el piloto IA Sevilla debe estar cargado y validado en PostgreSQL.

Ejecutar:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

Resultado esperado:

```text
ready_for_sevilla_pilot_queries = true
errors = []
warnings = []
```

Si este check no pasa, no se debe generar el dashboard todavía.

---

## 6. Exportación de datos para el dashboard

El dashboard no consulta directamente la base de datos. Lee CSV y JSON generados por:

```text
scripts/export_sevilla_dashboard_data.py
```

Comando recomendado completo:

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

Este comando exporta todos los candidatos seleccionados, los resúmenes agregados y ejemplos de menciones/reseñas para la vista de detalle.

---

## 7. Archivos exportados

El exportador debe generar:

```text
dashboard_metadata.json
kpi_summary.json
candidates_detail.csv
candidates_all.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
district_summary.csv
neighborhood_summary.csv
dish_summary.csv
place_summary.csv
tier_summary.csv
quality_summary.csv
filter_options.json
data_contract.json
dashboard_export_summary.json
mention_examples.csv
```

El archivo más importante para la tabla principal es:

```text
candidates_detail.csv
```

El archivo más delicado es:

```text
mention_examples.csv
```

porque puede incluir reseñas completas si se usa `--include-full-review-text`.

---

## 8. Checks del exportador

El exportador debe terminar con checks en `true`:

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

Conteos esperados del piloto actual:

```text
all_candidates = 256
selected_candidates = 150
selected_places = 122
selected_dishes = 38
selected_neighborhoods = 55
selected_districts = 11
```

---

## 9. Ejecución del dashboard

Desde la raíz del repositorio:

```powershell
streamlit run dashboard/streamlit_app.py
```

Streamlit abrirá una URL local, normalmente:

```text
http://localhost:8501
```

---

## 10. Secciones funcionales del dashboard

El dashboard está organizado para presentar el piloto completo:

```text
1. Resumen ejecutivo.
2. KPIs principales.
3. Top Hidden Gems global.
4. Filtros por distrito, barrio, plato, tier, evidencia y score.
5. Tabla exploradora de candidatos.
6. Mapa de candidatos.
7. Análisis territorial por distrito y barrio.
8. Análisis por plato.
9. Análisis por local.
10. Detalle de candidato.
11. Componentes del score.
12. Penalizaciones.
13. Menciones y reseñas asociadas.
14. Reseña completa opcional en vista de detalle.
15. Calidad, checks y limitaciones.
```

---

## 11. Uso recomendado en presentación

Para presentar el proyecto, el orden recomendado es:

```text
1. Mostrar KPIs generales.
2. Explicar que el ranking es piloto y no producción.
3. Enseñar el top global.
4. Filtrar por distrito o barrio.
5. Buscar un plato concreto.
6. Abrir el detalle de un candidato.
7. Mostrar componentes del score.
8. Mostrar una reseña/mención solo si aporta explicación.
9. Cerrar con calidad y limitaciones.
```

Esto demuestra tanto la parte visual como la trazabilidad técnica del sistema.

---

## 12. Tratamiento de reseñas completas

El dashboard permite mostrar reseñas completas únicamente en una vista de detalle.

Reglas:

```text
- No mostrar reseñas completas en la vista principal.
- No mostrar reseñas completas en tablas globales.
- Usarlas solo bajo un desplegable o sección de detalle.
- No incluir capturas públicas con textos completos si no es necesario.
- No subir a GitHub archivos que contengan reviews completas.
```

Si no se quieren exportar reseñas completas:

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --include-mentions `
  --strict
```

Sin `--include-full-review-text`, el dashboard tendrá menos información textual sensible.

---

## 13. Qué no subir a Git

No versionar:

```text
data/artifacts/ai/sevilla/dashboard/*.csv
data/artifacts/ai/sevilla/dashboard/*.json
```

Especialmente:

```text
data/artifacts/ai/sevilla/dashboard/mention_examples.csv
```

cuando contiene reseñas completas.

Sí versionar:

```text
dashboard/streamlit_app.py
dashboard/README.md
scripts/export_sevilla_dashboard_data.py
scripts/query_sevilla_hidden_gems_demo.py
docs/08_operations/09_dashboard_operations.md
```

---

## 14. Solución de problemas frecuentes

### Error: no aparecen datos

Comprobar que existe:

```text
data/artifacts/ai/sevilla/dashboard/candidates_detail.csv
```

Regenerar datos con:

```powershell
python -m scripts.export_sevilla_dashboard_data `
  --output-dir data/artifacts/ai/sevilla/dashboard `
  --expected-selected 150 `
  --strict
```

---

### Error: faltan columnas

Puede ocurrir si el dashboard espera un contrato más reciente que el exportador.

Solución:

```text
1. Actualizar scripts/export_sevilla_dashboard_data.py.
2. Regenerar data/artifacts/ai/sevilla/dashboard/.
3. Reiniciar Streamlit.
```

---

### Error con slider de Streamlit

Streamlit exige que `value`, `min_value` y `max_value` tengan el mismo tipo.

Solución aplicada:

```python
value=float(default_value)
min_value=0.0
max_value=100.0
step=1.0
```

---

### El mapa no muestra puntos

Comprobar:

```text
selected_have_coordinates = true
```

en `dashboard_export_summary.json`.

También revisar que las columnas existen:

```text
latitude
longitude
```

---

### Reseñas completas visibles donde no deberían

Revisar el dashboard y asegurar que `review_text_raw` solo se usa dentro de secciones de detalle.

Si se quiere evitar completamente:

```text
No ejecutar el exportador con --include-full-review-text.
```

---

## 15. Regeneración del dashboard tras cambios

Cuando se recalcule el ranking o se carguen nuevos datos:

```text
1. Ejecutar check de carga Sevilla.
2. Regenerar export de dashboard.
3. Reiniciar Streamlit.
4. Revisar KPIs y checks.
```

Comandos:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json

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

streamlit run dashboard/streamlit_app.py
```

---

## 16. Estado actual

El dashboard queda operativo sobre el piloto actual con:

```text
256 candidatos puntuados
150 candidatos seleccionados
122 locales seleccionados
38 platos seleccionados
55 barrios cubiertos
11 distritos cubiertos
413 ejemplos de menciones/reseñas exportados para detalle
```

El ranking se mantiene como:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
is_production_ready = false
```

---

## 17. Próximos pasos

Una vez validado el dashboard, el siguiente uso natural es análisis de calidad:

```text
- detectar falsos positivos;
- revisar platos mal normalizados;
- localizar barrios con poca evidencia;
- revisar candidatos con baja evidencia;
- ajustar reglas y diccionario español;
- decidir si merece la pena entrenar o adaptar modelos IA.
```

El dashboard no solo es una capa visual. También es una herramienta para decidir las siguientes mejoras del sistema.
