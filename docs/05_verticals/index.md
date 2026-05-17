# 05. Verticales del pipeline

Este bloque documenta las verticales operativas del proyecto Hidden Gems Pipeline.

Una vertical representa un flujo completo y trazable desde una fuente o bloque funcional hasta sus salidas en base de datos, artefactos, checks o capas derivadas.

---

## Contenido

- [40. Vertical Sevilla Geo](./40_vertical_sevilla_geo.md)
- [41. Vertical OSM / Overpass](./41_vertical_overpass.md)
- [42. Vertical Google Places](./42_vertical_google_places.md)
- [43. Vertical Google Places Reviews](./43_vertical_google_places_reviews.md)
- [44. Vertical Yelp Open Dataset](./44_vertical_yelp_open_dataset.md)

---

## Estado final de las verticales

| Vertical | Papel principal | Estado para entrega |
|---|---|---|
| Sevilla Geo | Base territorial de barrios y distritos | Cerrada y usada en dashboard/ranking v2 |
| OSM / Overpass | Fuente abierta de locales gastronómicos | Cerrada como fuente multisource de apoyo |
| Google Places | Fuente operativa de locales reales de Sevilla | Cerrada y usada como base del flujo local |
| Google Places Reviews | Fuente textual local de reseñas reales | Cerrada y usada en Sevilla IA v2 |
| Yelp Open Dataset | Corpus externo y prototipo IA | Cerrada como benchmark/prototipo, no producción Sevilla |

---

## Relación con la fase Sevilla IA v2

La fase final del proyecto se apoya principalmente en Google Places y Google Places Reviews:

```text
Google Places Text Search
→ place / place_source_ref / barrio
→ Google Places Reviews
→ review local de Sevilla
→ Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ place-dish signals v2
→ hidden gems ranking v2
→ dashboard Sevilla IA v2
```

El resultado final de la fase Sevilla IA v2 fue:

```text
total_candidates_scored_v2 = 2.335
selected_candidates_v2 = 268
selected_places_v2 = 198
selected_dishes_v2 = 40
selected_neighborhoods_v2 = 67
selected_districts_v2 = 11
```

La comparación contra el ranking v1 permitió comprobar que v2 conserva gran parte del baseline y amplía cobertura:

```text
v1_selected_unique = 150
v2_selected_unique = 268
matched_candidates = 119
v1_coverage_in_v2 = 0.793333
selected_places_delta_v2_minus_v1 = +76
selected_neighborhoods_delta_v2_minus_v1 = +12
```

---

## Lectura recomendada

Para entender esta carpeta de forma completa, se recomienda leer en este orden:

1. `40_vertical_sevilla_geo.md`, para entender la base territorial.
2. `41_vertical_overpass.md`, para entender la fuente abierta multisource.
3. `42_vertical_google_places.md`, para entender la adquisición de locales reales.
4. `43_vertical_google_places_reviews.md`, para entender la fuente textual local.
5. `44_vertical_yelp_open_dataset.md`, para entender el prototipo IA histórico y corpus externo.

La documentación específica de la fase final con modelos, ranking v2, comparación y dashboard está en:

```text
docs/13_sevilla_ai_v2/
```

---

## Nota de alcance

Las verticales de esta carpeta documentan adquisición, integración, trazabilidad y preparación de datos.

La lógica IA, los modelos entrenados, la normalización/reranking, ABSA, ranking v2 y dashboard final se documentan en capas posteriores. Esta separación evita mezclar responsabilidades:

```text
verticales → obtienen y preparan datos
IA v2      → procesa reseñas y genera ranking/dashboard
```

El estado final del proyecto para entrega académica es un **MVP técnico avanzado / prototipo analítico funcional**, no una versión de producción pública.
