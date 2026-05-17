# 04. Fuentes de datos

Este bloque documenta las fuentes utilizadas en **Hidden Gems Pipeline**, su papel dentro del sistema, su estado de implementación y su relación con la capa IA.

La estrategia del proyecto no trata a las fuentes externas como verdad única. Cada fuente entra de forma trazable, se conserva en raw cuando procede, se transforma a estructuras comunes y se conecta con el modelo canónico o con artefactos IA derivados.

---

## Índice

| Documento | Contenido |
|---|---|
| [30. Data Sources Overview](./30_data_sources_overview.md) | Visión general de todas las fuentes y su papel en el pipeline. |
| [31. Sevilla Geo Source](./31_sevilla_geo_source.md) | Fuente geográfica oficial para barrios y distritos de Sevilla. |
| [32. OSM / Overpass Source](./32_overpass_source.md) | Fuente abierta de POIs gastronómicos geolocalizados. |
| [33. Google Places Source](./33_google_places_source.md) | Fuente operativa principal de locales y reviews de Sevilla. |
| [34. Yelp Open Dataset Source](./34_yelp_source.md) | Corpus externo y prototipo IA, no producción Sevilla. |

---

## Estado final de la capa de fuentes

| Fuente | Rol | Estado final |
|---|---|---|
| Sevilla Geo | Referencia territorial | Implementada y cerrada |
| OSM / Overpass | Base abierta de locales | Implementada y cerrada |
| Google Places Text Search | Descubrimiento/enriquecimiento local | Implementada |
| Google Places Reviews | Reviews reales locales | Fuente principal para Sevilla IA v1/v2 |
| Yelp Open Dataset | Corpus IA externo | Prototipo/benchmark, no producción Sevilla |

---

## Relación con Sevilla IA v2

La fase final de entrega utiliza principalmente Google Places Reviews como fuente textual local:

```text
Google Places Reviews Sevilla
→ NER de platos
→ normalización / entity linking
→ sentimiento ABSA por mención
→ señales local-plato v2
→ ranking Hidden Gems Sevilla v2
→ dashboard_v2
```

Sevilla Geo aporta la capa territorial, Google Places Text Search aporta locales y coordenadas, y Yelp queda como corpus de apoyo y antecedente del módulo IA.

---

## Nota de producción

Ningún resultado derivado de fuentes y modelos IA v2 se marca como producción definitiva:

```text
is_production_ready = false
```

La entrega académica se considera un **MVP técnico avanzado / prototipo analítico funcional**, no una plataforma productiva final.
