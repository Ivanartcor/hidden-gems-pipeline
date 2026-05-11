# 04 - Current Status and Next Steps

## 1. Estado actual general

La integración del módulo IA en PostgreSQL queda completada y validada en dos niveles:

```text
1. Yelp prototype
   Corpus externo amplio usado para validar arquitectura IA.

2. Sevilla pilot
   Primer piloto local generado desde Google Places Reviews de Sevilla.
```

Esto significa que el proyecto ya no está solo en fase de preparación. Actualmente existe un flujo completo:

```text
reviews
→ menciones de platos
→ sentimiento por mención
→ señales por local/plato
→ ranking
→ PostgreSQL
→ vistas consultables
→ scripts demo
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

## 5. Qué está ya cerrado

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
```

---

## 6. Limitaciones actuales

### 6.1. Sevilla pilot no es producción

El piloto local es útil y consultable, pero todavía no debe publicarse como ranking final.

Motivos:

- Google devuelve un subconjunto limitado de reviews por local;
- el corpus local todavía es reducido frente a una versión productiva;
- el sentimiento es híbrido/reglado;
- faltan revisiones manuales sistemáticas;
- hay que evaluar falsos positivos desde una interfaz o dashboard;
- `is_production_ready = false`.

### 6.2. Restricción temporal de `ranking_scope`

El DDL actual no incluye `sevilla_pilot` como valor nativo de `ranking_scope`, por lo que se ha usado:

```text
db_ranking_scope = other
artifact_ranking_scope = sevilla_pilot
```

Esto es correcto para el piloto, pero puede revisarse en una futura migración.

### 6.3. IA mejorable

La capa IA actual es suficientemente buena para prototipo, pero no definitiva.

Posibles mejoras posteriores:

- ampliar diccionario gastronómico español;
- mejorar detección de platos compuestos;
- reducir falsos positivos;
- entrenar NER específico español;
- mejorar sentimiento por aspecto/plato;
- añadir validación humana.

---

## 7. Siguiente fase recomendada

El orden acordado para continuar es:

```text
1. Actualizar README y documentación general.
2. Consolidar scripts demo finales.
3. Definir contrato de datos para dashboard.
4. Crear dashboard piloto.
5. Revisar calidad del ranking con uso real.
6. Decidir si conviene mejorar reglas o crear modelos IA nuevos.
```

---

## 8. Fase A: documentación general

Ya se está actualizando:

```text
README.md
docs/01_context/
docs/02_architecture/
docs/03_data_model/
docs/04_sources/
docs/05_verticals/
docs/11_ai_integration/
docs/12_sevilla_ai_pilot/
```

Objetivo:

```text
Que el repositorio refleje que el piloto IA Sevilla ya existe, está cargado y es consultable.
```

---

## 9. Fase B: scripts demo finales

Scripts a consolidar:

```text
scripts/query_sevilla_hidden_gems_demo.py
scripts/check_sevilla_ai_pilot_loaded.py
scripts/load_sevilla_ai_pilot_outputs.py
scripts/export_reviews_for_ai.py
scripts/check_ai_review_export.py
```

Revisión recomendada:

- `--help` claro;
- rutas por defecto consistentes;
- salida en `data/artifacts/`;
- report JSON cuando aplique;
- filtros por distrito/barrio/plato/local;
- nombres de columnas estables para dashboard.

---

## 10. Fase C: contrato de datos para dashboard

Antes del dashboard, conviene cerrar qué datos debe consumir.

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

Fuente recomendada para la primera versión:

```text
CSV/JSON exportados por query_sevilla_hidden_gems_demo.py
```

Fuente posterior posible:

```text
PostgreSQL directo
FastAPI
```

---

## 11. Fase D: dashboard piloto

Recomendación inicial:

```text
Streamlit
```

Motivo:

- rápido de construir;
- integrado con Python;
- suficiente para demo técnica;
- permite filtros, tablas, cards y gráficos;
- puede consumir CSV/JSON o PostgreSQL.

Funcionalidades mínimas:

```text
filtro por distrito
filtro por barrio
filtro por plato
top global
top por zona
cards de candidatos
tabla completa
detalle con explicación del ranking
resumen por distrito/plato/tier
```

---

## 12. Fase E: mejora IA posterior

No conviene empezar entrenando nuevos modelos antes de ver el ranking en dashboard.

El dashboard ayudará a detectar:

```text
falsos positivos
platos demasiado genéricos
locales con señal débil
barrios con poca cobertura
tiers mal calibrados
problemas de sentimiento
necesidad real de modelo entrenado
```

Después se podrá decidir entre:

```text
mejorar reglas
ampliar lexicón español
crear dataset anotado
entrenar NER español
usar modelo multilingüe
mejorar sentimiento ABSA
```

---

## 13. Conclusión

La integración IA ya no es solo un prototipo con Yelp: ahora incluye un piloto real de Sevilla construido sobre Google Places Reviews, cargado en PostgreSQL y consultable.

El siguiente salto no debe ser añadir complejidad IA directamente, sino convertir el resultado actual en algo demostrable y revisable:

```text
consultas finales
→ contrato de datos
→ dashboard piloto
→ revisión de calidad
→ mejoras IA dirigidas por evidencia
```
