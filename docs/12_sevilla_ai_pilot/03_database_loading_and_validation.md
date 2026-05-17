# 03. Carga en PostgreSQL y validación del piloto Sevilla IA

## 1. Objetivo

Este documento describe la carga de los artefactos generados por los notebooks IA Sevilla en la base de datos PostgreSQL/PostGIS del proyecto Hidden Gems, así como la validación posterior de integridad.

La finalidad de esta fase fue transformar los resultados experimentales de notebooks en información persistida y consultable desde el esquema del proyecto.

El flujo cargado en base de datos incluye:

```text
catálogo de platos Sevilla
aliases de platos
menciones de platos
sentimiento por mención
señales local-plato
ranking Hidden Gems Sevilla piloto
```

Esta fase marca el paso de un prototipo puramente analítico a un prototipo integrado en la arquitectura del sistema.

## 2. Artefactos de entrada

El loader consume los artefactos generados por los notebooks `14`, `15`, `16` y `17`.

Entradas principales:

```text
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_catalog_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_aliases_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_normalized_v1.jsonl
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.jsonl
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_signals_v1.jsonl
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_candidates_all_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_selected_candidates_v1.csv
```

El ranking final del notebook 17 genera 256 candidatos evaluados, de los cuales 150 quedan seleccionados como candidatos Hidden Gems del piloto.

## 3. Script de carga

Script principal:

```text
scripts/load_sevilla_ai_pilot_outputs.py
```

Función:

- registrar versiones de modelos IA;
- registrar ejecuciones IA (`ai_pipeline_run`);
- cargar catálogo de platos en `dish`;
- cargar aliases en `dish_alias`;
- cargar menciones en `dish_mention`;
- cargar sentimiento en `dish_mention_sentiment`;
- cargar señales local-plato en `dish_place_signal`;
- cargar candidatos Hidden Gems en `hidden_gem_candidate`;
- validar mappings contra `review`, `place` y `dish`;
- generar reporte de carga.

## 4. Comando utilizado

Carga real:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --report-path data/artifacts/ai/sevilla/load_sevilla_ai_pilot_outputs_report.json
```

También se puede ejecutar en modo seguro:

```powershell
python -m scripts.load_sevilla_ai_pilot_outputs `
  --dry-run
```

El modo `dry-run` permite validar artefactos y mappings sin escribir en base de datos.

## 5. Versiones de modelo registradas

La carga registra cinco componentes lógicos del pipeline IA:

| Model code | Tipo | Tarea |
|---|---|---|
| `sevilla_dish_detection_hybrid_v1` | `hybrid` | detección de platos |
| `sevilla_dish_normalization_hybrid_v1` | `hybrid` | normalización de platos |
| `sevilla_mention_sentiment_hybrid_v1` | `hybrid` | sentimiento por mención |
| `sevilla_signal_aggregation_v1` | `aggregation` | agregación local-plato |
| `sevilla_hidden_gems_ranking_pilot_v1` | `ranking` | ranking Hidden Gems |

Todas las versiones quedan asociadas a idioma `es` y versión `v1`.

## 6. Pipeline runs registrados

La carga también crea o actualiza ejecuciones IA:

| Run code | Tipo |
|---|---|
| `ai_run_sevilla_dish_catalog_v1` | `dish_normalization` |
| `ai_run_sevilla_dish_mentions_v1` | `dish_detection` |
| `ai_run_sevilla_mention_sentiment_v1` | `mention_sentiment` |
| `ai_run_sevilla_signal_aggregation_v1` | `signal_aggregation` |
| `ai_run_sevilla_hidden_gems_ranking_pilot_v1` | `hidden_gems_ranking` |

Todas las ejecuciones quedaron en estado:

```text
completed
```

## 7. Resultado de la carga

La carga se ejecutó correctamente con los siguientes conteos:

| Entidad | Filas cargadas / validadas |
|---|---:|
| `ai_model_version` | 5 |
| `ai_pipeline_run` | 5 |
| `dish` | 190 |
| `dish_alias` | 243 |
| `dish_mention` | 2.979 |
| `dish_mention_sentiment` | 2.979 |
| `dish_place_signal` | 2.212 |
| `hidden_gem_candidate` | 256 |

El reporte de carga indicó:

```text
no_missing_review_mapping: true
no_missing_place_mapping: true
no_missing_dish_mapping: true
no_invalid_sentiment: true
```

Y todos los contadores de errores quedaron a cero:

| Error / salto | Conteo |
|---|---:|
| `catalog_missing_required` | 0 |
| `alias_missing_required` | 0 |
| `alias_missing_dish_mapping` | 0 |
| `mention_missing_required` | 0 |
| `mention_missing_review_mapping` | 0 |
| `mention_missing_place_mapping` | 0 |
| `mention_missing_dish_mapping` | 0 |
| `mention_invalid_sentiment` | 0 |
| `signal_missing_required` | 0 |
| `signal_missing_place_mapping` | 0 |
| `signal_missing_dish_mapping` | 0 |
| `ranking_missing_required` | 0 |
| `ranking_missing_place_mapping` | 0 |
| `ranking_missing_dish_mapping` | 0 |
| `ranking_missing_signal_mapping` | 0 |

## 8. Consideración sobre `ranking_scope`

El ranking lógico del piloto se denomina:

```text
sevilla_pilot
```

Sin embargo, el DDL actual de `hidden_gem_candidate.ranking_scope` no incluye todavía ese valor como opción nativa. Por compatibilidad con la restricción existente, el loader guarda:

```text
db_ranking_scope = other
```

Y conserva el scope real del artefacto dentro de la configuración JSON:

```text
artifact_ranking_scope = sevilla_pilot
```

Esta decisión evita modificar el DDL en mitad del piloto y mantiene la trazabilidad completa del ranking.

En una futura mejora, se puede añadir `sevilla_pilot` como valor nativo de la restricción de `ranking_scope`.

## 9. Script de validación

Script principal:

```text
scripts/check_sevilla_ai_pilot_loaded.py
```

Función:

- comprobar tablas IA requeridas;
- comprobar vistas IA opcionales;
- validar versiones de modelo;
- validar runs IA;
- comprobar conteos esperados;
- detectar menciones huérfanas;
- detectar sentimientos sin mención;
- detectar señales sin `place` o `dish`;
- detectar rankings sin señal;
- validar scores entre 0 y 100;
- validar candidatos seleccionados;
- comprobar cobertura por barrio y distrito;
- comprobar que el ranking no está marcado como producción;
- generar reporte final.

## 10. Comando de validación

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

También existe un modo flexible para omitir conteos exactos en pruebas:

```powershell
python -m scripts.check_sevilla_ai_pilot_loaded `
  --skip-expected-counts `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
```

## 11. Resultado del check

El check final confirmó:

```text
ready_for_sevilla_pilot_queries: true
errors: []
warnings: []
```

Conteos validados:

| Entidad | Conteo validado |
|---|---:|
| `dish_catalog` | 190 |
| `dish_alias` | 243 |
| `dish_mention` | 2.979 |
| `dish_mention_sentiment` | 2.979 |
| `dish_place_signal` | 2.212 |
| `hidden_gem_candidate` | 256 |
| `hidden_gem_selected` | 150 |

## 12. Integridad validada

El informe de validación confirmó que no existen problemas críticos:

| Check | Resultado |
|---|---:|
| Menciones sin review | 0 |
| Menciones sin place | 0 |
| Menciones sin dish | 0 |
| Menciones sin sentimiento | 0 |
| Sentimientos sin mención | 0 |
| Labels de sentimiento inválidos | 0 |
| Señales sin place | 0 |
| Señales sin dish | 0 |
| Rankings sin place | 0 |
| Rankings sin dish | 0 |
| Rankings sin señal | 0 |
| Rankings sin barrio | 0 |
| Rankings sin distrito | 0 |
| Scores fuera de rango | 0 |
| Seleccionados marcados como producción | 0 |
| Seleccionados sin explicación | 0 |
| Scope de artefacto incorrecto | 0 |
| Scope de DB incorrecto | 0 |

## 13. Vistas comprobadas

El check confirmó que existen y devuelven filas las vistas IA principales:

| Vista | Filas comprobadas |
|---|---:|
| `vw_ai_hidden_gem_candidate_detail` | 256 candidatos, 150 seleccionados |
| `vw_ai_dish_place_signals` | 2.212 señales |
| `vw_ai_dish_mentions_with_sentiment` | 2.979 menciones con sentimiento |

También existen:

```text
vw_ai_pipeline_run_summary
vw_ai_hidden_gems_place_summary
vw_ai_hidden_gems_dish_summary
```

## 14. Distribución del ranking cargado

El ranking cargado mantiene la siguiente distribución:

| Tier | Seleccionado | Filas |
|---|---:|---:|
| `top_hidden_gem` | Sí | 2 |
| `strong_hidden_gem` | Sí | 7 |
| `promising_hidden_gem` | Sí | 72 |
| `exploratory_hidden_gem` | Sí | 69 |
| `not_selected` | No | 106 |

Resumen de cobertura seleccionada:

| Métrica | Valor |
|---|---:|
| Candidatos seleccionados | 150 |
| Locales seleccionados | 122 |
| Platos seleccionados | 38 |
| Barrios seleccionados | 55 |
| Distritos seleccionados | 11 |
| Score mínimo seleccionado | 55,0423 |
| Score medio seleccionado | 63,2804 |
| Score máximo seleccionado | 80,1471 |
| Seleccionados production-ready | 0 |

## 15. Conclusión

La carga y validación del piloto Sevilla IA queda completada correctamente.

El sistema ya puede consultar desde PostgreSQL:

- catálogo de platos Sevilla;
- aliases y normalizaciones;
- menciones de platos;
- sentimiento por mención;
- señales local-plato;
- ranking piloto `sevilla_pilot`;
- candidatos seleccionados por barrio, distrito, plato y local.

El check final establece que la base está lista para consultas piloto:

```text
ready_for_sevilla_pilot_queries = true
```

Por tanto, la siguiente fase natural es usar las vistas IA para consulta, demo, revisión y futura exposición mediante API o dashboard.
---

## 16. Relación con Sevilla IA v2

La carga descrita en este documento corresponde al piloto v1:

```text
sevilla_pilot
→ PostgreSQL
→ vistas IA
→ query demo
```

La fase posterior `docs/13_sevilla_ai_v2/` genera una cadena más avanzada de artefactos:

```text
hybrid_ner_v2/
normalization_reranker_v1/
sentiment_absa_v1/
place_dish_signals_v2/
ranking_v2/
ranking_v2_comparison/
dashboard_v2/
```

En el estado documentado aquí, no debe asumirse automáticamente que el ranking v2 está cargado en las mismas tablas PostgreSQL. Para integrarlo en base de datos habría que crear una extensión explícita, por ejemplo:

```text
load_sevilla_ai_v2_outputs.py
check_sevilla_ai_v2_loaded.py
query_sevilla_hidden_gems_v2_demo.py
```

o adaptar los loaders existentes con un nuevo `ranking_scope` / `artifact_ranking_scope` específico.

Decisión documental actual:

```text
PostgreSQL validado = Sevilla pilot v1
Artefactos/dashboard v2 = documentados en docs/13_sevilla_ai_v2
```

Esto evita mezclar conteos y estados de madurez:

| Elemento | Sevilla pilot v1 | Sevilla IA v2 |
|---|---:|---:|
| Candidatos seleccionados | 150 | 268 |
| Locales seleccionados | 122 | 198 |
| Barrios seleccionados | 55 | 67 |
| Estado DB | Cargado y validado | No documentado aquí como cargado en PostgreSQL |
| Producción | No | No |
