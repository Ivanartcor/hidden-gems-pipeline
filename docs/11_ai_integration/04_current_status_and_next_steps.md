# Nota de actualización


# 04 - Current Status and Next Steps

## 1. Estado actual general

La integración del módulo IA queda completada y validada en varios niveles:

```text
1. Yelp prototype
   Corpus externo amplio usado para validar arquitectura IA.

2. Sevilla pilot
   Primer piloto local generado desde Google Places Reviews de Sevilla,
   cargado en PostgreSQL y consultable mediante vistas/scripts.

3. Sevilla IA v2
   Evolución posterior con modelos entrenados, ranking v2, comparación v1/v2
   y dashboard Streamlit basado en artefactos exportados.
```

Esto significa que el proyecto ya no está solo en fase de preparación. Actualmente existe un flujo completo:

```text
reviews
→ menciones de platos
→ sentimiento por mención
→ señales por local/plato
→ ranking
→ PostgreSQL / artefactos versionados
→ vistas consultables / dashboard
→ demo y revisión
```

---

## 2. Estado validado: Yelp prototype

Fases cerradas:

```text
1. Diseño y creación del schema IA.
2. Carga del catálogo de platos y aliases.
3. Carga del núcleo Yelp para prototipo IA.
4. Carga de menciones de platos.
5. Carga de sentimiento por mención.
6. Carga de señales agregadas por local y plato.
7. Carga del ranking Hidden Gems v1.
8. Creación de vistas SQL.
9. Creación de script de demo de consultas.
10. Validación final de integridad.
```

Conteos:

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |

Estado:

```text
ranking_scope = yelp_prototype
is_production_ready = false
ready_for_querying_ai_ranking = true
```

Integridad:

```text
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

---

## 3. Estado validado: Sevilla pilot

Fases cerradas:

```text
1. Recolección Google Places Sevilla.
2. Recolección Google Places Reviews Sevilla.
3. Exportación de reviews para IA.
4. Exploración del corpus local.
5. Detección de candidatos de platos.
6. Normalización y catálogo local.
7. Sentimiento por mención.
8. Agregación place + dish.
9. Ranking sevilla_pilot.
10. Carga en PostgreSQL.
11. Check de integridad.
12. Script demo de consultas.
13. Documentación docs/12_sevilla_ai_pilot.
```

Volumen de fuente:

```text
800+ locales Google Places
4.000+ reviews Google Places
```

Resultados IA cargados:

| Elemento | Registros |
|---|---:|
| `dish` local Sevilla | 190 |
| `dish_alias` Sevilla | 243 |
| `dish_mention` Sevilla | 2.979 |
| `dish_mention_sentiment` Sevilla | 2.979 |
| `dish_place_signal` Sevilla | 2.212 |
| `hidden_gem_candidate` Sevilla | 256 |
| candidatos seleccionados | 150 |

Cobertura:

```text
selected_places = 122
selected_dishes = 38
selected_neighborhoods = 55
selected_districts = 11
```

Ranking:

```text
artifact_ranking_scope = sevilla_pilot
db_ranking_scope = other
ranking_version = sevilla_hidden_gems_ranking_pilot_v1
is_production_ready = false
ready_for_sevilla_pilot_queries = true
```

El uso de `other` en `ranking_scope` es una decisión técnica temporal debida a la constraint actual del DDL. El scope lógico `sevilla_pilot` se conserva en `ranking_config_json`.

---

## 4. Distribución del ranking Sevilla pilot

```text
total_pairs_scored = 256
selected_hidden_gem_candidates = 150
not_selected = 106
```

Tiers:

```text
top_hidden_gem = 2
strong_hidden_gem = 7
promising_hidden_gem = 72
exploratory_hidden_gem = 69
```

Score seleccionado:

```text
min = 55.0423
mean = 63.2804
median ≈ 62.7168
max = 80.1471
```

Ejemplos destacados:

```text
Pizzería San Pablo → pizza
restaurante asiático shan → sushi
Il Ristorantino Dell'Avvocato Calle Cuna → pizza
Tarannà → atún
Taberna Los Terceros → solomillo al whisky
Cafeteria mi abuela, churreria → churros
I Love Churros → churros
BAR EL BUCHITO → carrillada
Bar BOCACHICA → ensaladilla
Las Golondrinas - Pagés del Corro → bacalao
```

---


## 5. Estado validado: Sevilla IA v2

Fases cerradas:

```text
1. Uso del piloto Sevilla como baseline.
2. Entrenamiento/aplicación de NER BETO para menciones de platos.
3. Construcción de capa Hybrid + NER candidates v2.
4. Normalización/entity linking con reranker.
5. Sentimiento ABSA por mención.
6. Agregación place_id + dish_id.
7. Ranking Hidden Gems Sevilla v2.
8. Comparación ranking v1 vs v2.
9. Export específico para dashboard v2.
10. Dashboard Streamlit Sevilla IA v2.
11. Documentación docs/13_sevilla_ai_v2.
```

Resultados principales:

| Métrica | Valor |
|---|---:|
| candidatos puntuados | 2.335 |
| candidatos seleccionados | 268 |
| locales seleccionados | 198 |
| platos seleccionados | 40 |
| barrios seleccionados | 67 |
| distritos seleccionados | 11 |
| menciones usadas en seleccionados | 651 |
| reviews usadas en seleccionados | 627 |
| score medio seleccionado | 80,58 |
| score máximo seleccionado | 91,66 |
| score mínimo seleccionado | 66,12 |

Distribución por tier:

```text
top_hidden_gem = 16
strong_hidden_gem = 77
promising_hidden_gem = 139
exploratory_hidden_gem = 36
```

Comparación con ranking Sevilla pilot v1:

```text
v1_selected_unique = 150
v2_selected_unique = 268
matched_candidates = 119
v1_only_candidates = 31
v2_only_candidates = 149
v1_coverage_in_v2 = 79.3 %
jaccard_overlap = 39.8 %
incremento_locales = +76
incremento_barrios = +12
```

Estado:

```text
ranking_type = experimental model-assisted
production_ready_count_v2 = 0
dashboard_ready = true
```

La fase v2 no debe presentarse como ranking de producción, sino como ranking experimental asistido por modelos.


## 6. Qué está ya cerrado

```text
Verticales de adquisición
→ Sevilla Geo
→ OSM / Overpass
→ Google Places
→ Google Places Reviews
→ Yelp Open Dataset

IA experimental
→ Yelp notebooks/modelos/prototipo
→ Sevilla notebooks 12-17

Integración PostgreSQL
→ schema IA
→ loaders
→ checks
→ vistas
→ query demos

Documentación
→ docs/10_ai_module
→ docs/11_ai_integration
→ docs/12_sevilla_ai_pilot
→ docs/13_sevilla_ai_v2
```

Dashboard
→ dashboard/streamlit_sevilla_v2_app.py
→ data/artifacts/ai/sevilla/dashboard_v2/
```

---

## 7. Limitaciones actuales

### 7.1. Sevilla pilot no es producción

El piloto local es útil y consultable, pero todavía no debe publicarse como ranking final.

Motivos:

- Google devuelve un subconjunto limitado de reviews por local;
- el corpus local todavía es reducido frente a una versión productiva;
- el sentimiento es híbrido/reglado;
- faltan revisiones manuales sistemáticas;
- hay que evaluar falsos positivos desde una interfaz o dashboard;
- `is_production_ready = false`.

### 7.2. Restricción temporal de `ranking_scope`

El DDL actual no incluye `sevilla_pilot` como valor nativo de `ranking_scope`, por lo que se ha usado:

```text
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
```

Esto es correcto para el piloto, pero puede revisarse en una futura migración.

### 7.3. IA mejorable

La capa IA actual es suficientemente buena para prototipo avanzado, pero no definitiva.

La fase v2 ya ha incorporado:

- NER específico en español con BETO;
- normalización/entity linking con reranker;
- sentimiento por aspecto/plato mediante ABSA;
- ranking v2;
- dashboard específico.

Posibles mejoras posteriores:

- ampliar el catálogo gastronómico español;
- mejorar detección de platos compuestos;
- reducir falsos positivos en menciones `ner_only`;
- aumentar ejemplos manuales de ABSA, especialmente `neutral` y `negative`;
- revisar platos demasiado genéricos;
- añadir validación humana sistemática;
- definir umbrales de producción.

---

## 8. Siguiente fase recomendada

El orden recomendado tras Sevilla IA v2 es:

```text
1. Actualizar README y documentación general para reflejar v2.
2. Mantener v1 como baseline y v2 como ranking principal experimental.
3. Revisar manualmente top_hidden_gem y strong_hidden_gem.
4. Decidir si se persiste ranking v2 en PostgreSQL o se mantiene como artefacto/dashboard.
5. Si se carga en PostgreSQL, crear loaders/checks específicos para v2.
6. Definir una versión production_candidate con umbrales más estrictos.
7. Ajustar penalizaciones de platos genéricos y evidencia emerging.
8. Preparar la presentación/memoria usando dashboard v2.
```

---

## 9. Fase A: documentación general

Ya se está actualizando:

```text
README.md
docs/01_context/
docs/02_architecture/
docs/03_data_model/
docs/04_sources/
docs/05_verticals/
docs/10_ai_module/
docs/11_ai_integration/
docs/12_sevilla_ai_pilot/
docs/13_sevilla_ai_v2/
```

Objetivo:

```text
Que el repositorio refleje que el piloto IA Sevilla existe, está cargado y es consultable,
y que Sevilla IA v2 existe como evolución experimental basada en modelos y dashboard.
```

---

## 10. Fase B: scripts demo finales

Scripts a mantener para Sevilla pilot:

```text
scripts/query_sevilla_hidden_gems_demo.py
scripts/check_sevilla_ai_pilot_loaded.py
scripts/load_sevilla_ai_pilot_outputs.py
scripts/export_reviews_for_ai.py
scripts/check_ai_review_export.py
```

Scripts a mantener para Sevilla IA v2:

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
scripts/run_sevilla_dish_normalization_reranker_v1.py
scripts/run_sevilla_mention_sentiment_absa_v1.py
scripts/build_sevilla_place_dish_signals_v2.py
scripts/build_sevilla_hidden_gems_ranking_v2.py
scripts/compare_sevilla_ranking_v1_vs_v2.py
scripts/export_sevilla_dashboard_data_v2.py
```

Revisión recomendada:

- `--help` claro;
- rutas por defecto consistentes;
- salida en `data/artifacts/`;
- report JSON cuando aplique;
- filtros por distrito/barrio/plato/local;
- nombres de columnas estables para dashboard.

---

## 11. Fase C: contrato de datos para dashboard

Para el dashboard piloto v1 ya existía una necesidad de contrato de datos. En v2, este contrato queda más consolidado en `dashboard_v2/data_contract.json`.

Bloques mínimos:

```text
Top global
Top por distrito
Top por barrio
Top por plato
Detalle de candidato
Resumen por local
Resumen por plato
Menciones justificativas
```

Fuente recomendada para Sevilla pilot v1:

```text
CSV/JSON exportados por query_sevilla_hidden_gems_demo.py
```

Fuente recomendada para Sevilla IA v2:

```text
CSV/JSON exportados por export_sevilla_dashboard_data_v2.py
```

Fuente posterior posible:

```text
PostgreSQL directo si se carga v2
FastAPI
```

---

## 12. Fase D: dashboard piloto / dashboard v2

La recomendación inicial era usar Streamlit. Esa decisión ya se ha materializado en:

```text
dashboard/streamlit_sevilla_v2_app.py
```

El dashboard v2 consume:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Incluye:

```text
resumen ejecutivo
ranking IA v2
filtros por distrito/barrio/plato/local/tier/evidencia/calidad
análisis territorial
mapa
platos y locales
evidencia y calidad
comparación v1 vs v2
detalle de menciones y reseñas
explicación de puntuación
contrato de datos
```

---

## 13. Fase E: mejora IA posterior

Ya se han entrenado e integrado modelos para NER, normalización y ABSA. El siguiente paso no debe ser entrenar por entrenar, sino revisar el ranking v2 desde el dashboard.

El dashboard ayudará a detectar:

```text
falsos positivos
platos demasiado genéricos
locales con señal débil
barrios con poca cobertura
tiers mal calibrados
problemas de sentimiento
normalizaciones dudosas
necesidad real de dataset anotado adicional
```

Después se podrá decidir entre:

```text
ajustar reglas de ranking
ampliar catálogo y aliases
revisar top candidates manualmente
crear dataset anotado adicional
entrenar ABSA v1.1
entrenar NER v1.3
crear versión production_candidate con umbrales estrictos
```

---

## 14. Conclusión

La integración IA ya no es solo un prototipo con Yelp: incluye un piloto real de Sevilla construido sobre Google Places Reviews, cargado en PostgreSQL y consultable.

Además, la fase Sevilla IA v2 aporta una evolución posterior basada en modelos entrenados, ranking v2, comparación con v1 y dashboard Streamlit.

El siguiente salto debe ser convertir v2 en una base defendible de análisis y validación:

```text
dashboard v2
→ revisión manual del top
→ decisión sobre persistencia PostgreSQL de v2
→ ajuste de calidad/evidencia
→ posible versión production_candidate
→ mejoras IA dirigidas por evidencia
```
