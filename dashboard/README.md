# Dashboard Hidden Gems Sevilla

## 1. Propósito

Este dashboard permite explorar de forma visual el piloto IA de **Hidden Gems Sevilla**.

Su objetivo es presentar, consultar y validar los resultados generados por el flujo:

```text
Google Places Reviews Sevilla
→ exportación de reviews para IA
→ detección y normalización de platos
→ sentimiento por mención
→ agregación de señales local-plato
→ ranking Hidden Gems Sevilla pilot
→ exportación de datos para dashboard
→ visualización Streamlit
```

El dashboard está pensado como una **demo técnica y analítica** del MVP, no como una aplicación final de producción.

---

## 2. Estado del ranking mostrado

El dashboard trabaja sobre el ranking piloto:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
ranking_version = sevilla_hidden_gems_ranking_pilot_v1
is_production_ready = false
```

La razón por la que en base de datos aparece `db_ranking_scope = other` es que la restricción actual del DDL no incluye todavía `sevilla_pilot` como valor nativo. El scope real del artefacto se conserva en `ranking_config_json` y en los archivos exportados para dashboard.

---

## 3. Datos que consume

El dashboard lee por defecto desde:

```text
data/artifacts/ai/sevilla/dashboard/
```

Esta carpeta se genera con:

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

Archivos principales generados:

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

---

## 4. Ejecución del dashboard

Desde la raíz del repositorio:

```powershell
streamlit run dashboard/streamlit_app.py
```

Si se quiere usar una carpeta de datos distinta, puede modificarse la ruta por defecto en el propio dashboard o adaptar el exportador para generar los datos en la ruta esperada.

---

## 5. Dependencias

El dashboard requiere las dependencias habituales del proyecto y, además:

```text
streamlit
plotly
```

Estas dependencias deben estar incluidas en `requirements.txt`.

Instalación manual si fuera necesario:

```powershell
pip install streamlit plotly
```

---

## 6. Secciones del dashboard

El dashboard incluye:

```text
1. Portada y resumen ejecutivo del piloto.
2. KPIs principales.
3. Top Hidden Gems global Sevilla.
4. Filtros por distrito, barrio, plato, tier, evidencia y score.
5. Tabla exploradora de candidatos.
6. Mapa de candidatos con coordenadas.
7. Análisis por distrito y barrio.
8. Análisis por plato.
9. Análisis por local.
10. Detalle individual de candidato.
11. Componentes del score y penalizaciones.
12. Menciones y reseñas asociadas.
13. Detalle opcional de reseña completa.
14. Calidad, checks y limitaciones del piloto.
```

---

## 7. Filtros disponibles

El dashboard permite explorar los resultados por:

```text
Distrito
Barrio
Plato
Local
Tier
Evidence tier
Score mínimo
Búsqueda textual libre
```

Los filtros se construyen a partir de:

```text
filter_options.json
candidates_detail.csv
```

---

## 8. Reseñas completas

El archivo `mention_examples.csv` puede contener reseñas completas si el exportador se ejecuta con:

```powershell
--include-full-review-text
```

En ese caso, el dashboard puede mostrar la reseña completa únicamente en una vista de detalle, bajo una acción voluntaria del usuario.

Regla de uso:

```text
La reseña completa no debe aparecer en vistas principales, tablas generales ni capturas públicas innecesarias.
```

---

## 9. Archivos que no deben subirse a GitHub

No deben versionarse los datos exportados del dashboard, especialmente si incluyen textos de reseñas.

Mantener fuera de Git:

```text
data/artifacts/ai/sevilla/dashboard/*.csv
data/artifacts/ai/sevilla/dashboard/*.json
```

Especialmente:

```text
data/artifacts/ai/sevilla/dashboard/mention_examples.csv
```

cuando se haya generado con reseñas completas.

Sí deben versionarse:

```text
dashboard/streamlit_app.py
dashboard/README.md
scripts/export_sevilla_dashboard_data.py
scripts/query_sevilla_hidden_gems_demo.py
docs/08_operations/09_dashboard_operations.md
```

---

## 10. Flujo recomendado de uso

### Paso 1. Validar que el piloto está cargado

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

El check debe indicar:

```text
ready_for_sevilla_pilot_queries = true
```

### Paso 2. Exportar datos para dashboard

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

### Paso 3. Ejecutar Streamlit

```powershell
streamlit run dashboard/streamlit_app.py
```

---

## 11. Limitaciones actuales

El dashboard muestra un piloto real, pero no un producto final:

```text
- Google Places puede devolver un subconjunto limitado de reviews por local.
- El ranking está marcado como no productivo.
- Los resultados requieren revisión manual antes de considerarse definitivos.
- La detección de platos y sentimiento se basa en una aproximación híbrida inicial.
- La cobertura por barrio depende de los locales y reviews recolectados.
```

---

## 12. Próximos pasos

Después de validar el dashboard, las siguientes mejoras posibles son:

```text
1. Revisar falsos positivos y errores de normalización.
2. Ajustar reglas y umbrales del ranking.
3. Ampliar diccionario gastronómico español.
4. Mejorar sentimiento por mención.
5. Incorporar modelos IA más específicos si el análisis de errores lo justifica.
6. Convertir el dashboard en producto web/API si el MVP lo requiere.
```
