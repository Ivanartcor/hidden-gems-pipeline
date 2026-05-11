# 00. Sevilla AI Pilot — Índice y visión general

## 1. Propósito del bloque

Este bloque documenta el **piloto IA Sevilla** de Hidden Gems, es decir, la primera versión end-to-end que utiliza datos reales de Google Places para detectar platos mencionados en reseñas, normalizarlos, estimar sentimiento por mención, construir señales por local-plato y generar un ranking piloto de platos destacados.

El objetivo de este bloque no es sustituir a la documentación general del proyecto, sino dejar trazada la nueva fase en la que Hidden Gems deja de ser únicamente un pipeline de adquisición y modelado de datos y pasa a incorporar una primera capa funcional de IA aplicada al caso real de Sevilla.

El alcance de este bloque cubre:

- recolección de locales y reseñas reales de Google Places;
- exportación de reseñas a formato JSONL para IA;
- ejecución de notebooks IA sobre el corpus Sevilla;
- generación de catálogo local de platos;
- detección de menciones de platos;
- sentimiento por mención;
- agregación de señales local-plato;
- ranking `sevilla_pilot`;
- carga en PostgreSQL;
- validación y consulta mediante scripts demo.

## 2. Estado actual del piloto

El piloto Sevilla IA se encuentra en estado **completado y validado a nivel de prototipo**.

Se han completado las siguientes fases:

| Fase | Estado | Resultado |
|---|---:|---|
| Recolección Google Places | Completada | Más de 800 locales y más de 4.000 reseñas reales |
| Exportación para IA | Completada | JSONL estándar con reseñas listas para procesar |
| Exploración corpus Sevilla | Completada | Análisis de cobertura, idioma, ratings y términos gastronómicos |
| Detección de platos | Completada | Candidatos de platos en español detectados y clasificados |
| Normalización | Completada | Catálogo local Sevilla y aliases generados |
| Sentimiento por mención | Completada | Sentimiento híbrido por plato/mención |
| Agregación local-plato | Completada | Señales por pareja `place + dish` |
| Ranking piloto | Completada | Ranking `sevilla_pilot` con 150 candidatos seleccionados |
| Carga PostgreSQL | Completada | Tablas IA cargadas con catálogo, menciones, señales y ranking |
| Check PostgreSQL | Completado | Integridad validada sin errores ni warnings |
| Consulta demo | Completada | Script de consulta sobre vistas IA funcionando |

## 3. Volumen final de datos

La fase de exportación y procesamiento se basó en un corpus real procedente de Google Places para Sevilla.

Resumen operativo:

| Elemento | Valor aproximado / final |
|---|---:|
| Locales Google Places recolectados | 800+ |
| Reviews Google Places recolectadas | 4.000+ |
| Reviews exportadas para IA | 4.110 |
| Locales únicos exportados | 831 |
| Barrios cubiertos | 96 |
| Distritos cubiertos | 11 |
| Reviews en español | 4.108 |
| Reviews en otros idiomas | 2 |
| Reviews sin barrio | 0 |
| Reviews sin distrito | 0 |
| Duplicados críticos | 0 |

El corpus es suficiente para un **piloto serio**, aunque no se considera todavía producción porque la evidencia por local está limitada por el número de reseñas disponibles por cada lugar.

## 4. Estructura documental del bloque

Este bloque se organiza en los siguientes documentos:

```text
12_sevilla_ai_pilot/
├── 00_index.md
├── 01_google_places_data_collection.md
├── 02_ai_notebook_pipeline.md
├── 03_database_loading_and_validation.md
├── 04_query_demo_and_results.md
└── 05_limitations_and_next_steps.md
```

Los documentos incluidos en esta primera entrega son:

| Documento | Contenido |
|---|---|
| `00_index.md` | Índice general, estado del piloto y visión global |
| `01_google_places_data_collection.md` | Recolección de datos desde Google Places y exportación para IA |
| `02_ai_notebook_pipeline.md` | Flujo completo de notebooks IA Sevilla, artefactos y resultados |

Los documentos pendientes documentarán la carga en base de datos, las consultas demo y las limitaciones del piloto.

## 5. Flujo general del piloto

El flujo completo ejecutado puede resumirse así:

```text
Google Places Text Search
        ↓
Locales reales de Sevilla
        ↓
Google Places Details / Reviews
        ↓
Reviews reales asociadas a place/place_source_ref
        ↓
export_reviews_for_ai.py
        ↓
reviews_for_ai_google_places.jsonl
        ↓
Notebooks IA 12–17
        ↓
Catálogo, menciones, sentimiento, señales y ranking
        ↓
load_sevilla_ai_pilot_outputs.py
        ↓
Tablas IA PostgreSQL
        ↓
check_sevilla_ai_pilot_loaded.py
        ↓
query_sevilla_hidden_gems_demo.py
```

## 6. Scripts principales relacionados

| Script | Función |
|---|---|
| `run_google_places_neighborhood_batch.py` | Ejecuta tandas de búsqueda de locales por barrio/distrito |
| `check_google_places_batch.py` | Valida resultados de batch de locales |
| `run_google_places_reviews_batch.py` | Obtiene reseñas para locales ya importados |
| `check_google_places_reviews_batch.py` | Valida resultados de batch de reseñas |
| `export_reviews_for_ai.py` | Exporta reseñas desde PostgreSQL a JSONL estándar IA |
| `check_ai_review_export.py` | Valida el JSONL exportado para IA |
| `load_sevilla_ai_pilot_outputs.py` | Carga resultados IA Sevilla en PostgreSQL |
| `check_sevilla_ai_pilot_loaded.py` | Valida la carga IA Sevilla en PostgreSQL |
| `query_sevilla_hidden_gems_demo.py` | Consulta demo del ranking piloto desde la base |

## 7. Notebooks principales

| Notebook | Fase |
|---|---|
| `12_sevilla_reviews_ai_exploration.ipynb` | Exploración del corpus Sevilla |
| `13_sevilla_dish_candidate_detection.ipynb` | Detección de candidatos de platos |
| `14_sevilla_dish_normalization_and_catalog.ipynb` | Normalización y catálogo local |
| `15_sevilla_mention_sentiment.ipynb` | Sentimiento por mención |
| `16_sevilla_place_dish_signal_aggregation.ipynb` | Agregación de señales local-plato |
| `17_sevilla_hidden_gems_ranking_pilot.ipynb` | Ranking piloto Hidden Gems Sevilla |

## 8. Resultado final del ranking piloto

El ranking piloto `sevilla_pilot` produjo:

| Métrica | Valor |
|---|---:|
| Pares local-plato evaluados | 256 |
| Candidatos seleccionados | 150 |
| Locales seleccionados | 122 |
| Platos seleccionados | 38 |
| Barrios seleccionados | 55 |
| Distritos seleccionados | 11 |

Distribución de tiers:

| Tier | Conteo |
|---|---:|
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 7 |
| `promising_hidden_gem` | 72 |
| `exploratory_hidden_gem` | 69 |
| `not_selected` | 106 |

El ranking queda marcado como piloto:

```text
ranking_scope lógico: sevilla_pilot
ranking_scope en DB: other
is_production_ready: false
```

La diferencia entre `sevilla_pilot` y `other` se debe a la restricción actual del DDL, donde `hidden_gem_candidate.ranking_scope` todavía no incluye `sevilla_pilot` como valor nativo. El valor real del scope del artefacto queda conservado en la configuración JSON del ranking.

## 9. Criterio de interpretación

Este piloto debe interpretarse como una **prueba funcional avanzada**, no como un ranking definitivo de producción.

Permite demostrar que Hidden Gems puede:

- descubrir platos concretos mencionados en reseñas reales;
- vincularlos a locales, barrios y distritos;
- estimar sentimiento por mención;
- agregar evidencia por local-plato;
- producir un ranking explicable;
- cargarlo en PostgreSQL;
- consultarlo desde vistas y scripts.

Sin embargo, todavía requiere:

- revisión manual de una muestra más amplia;
- mejora de reglas de detección y normalización;
- ajuste de pesos del ranking;
- posible ampliación de fuentes de reseñas;
- futura exposición mediante API o dashboard.
