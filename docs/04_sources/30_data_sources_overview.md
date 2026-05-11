# 30. Data Sources Overview

## 1. Finalidad del bloque de fuentes

El bloque de fuentes de datos documenta el origen, función y tratamiento de cada fuente usada en **Hidden Gems Pipeline**.

El proyecto combina fuentes abiertas, datasets geográficos oficiales, APIs externas, reviews reales y datasets de apoyo para IA.

Este bloque explica:

- qué aporta cada fuente;
- qué tipo de datos proporciona;
- cómo entra en el pipeline;
- qué tablas o artefactos alimenta;
- qué limitaciones tiene;
- qué papel cumple en el modelo global;
- qué fuentes son operativas y cuáles son corpus/prototipo IA.

---

## 2. Enfoque general

La estrategia del proyecto combina varias fuentes con roles complementarios.

Principio clave:

> Las fuentes externas no son la verdad única. Cada fuente se incorpora de forma trazable y se adapta progresivamente al modelo interno.

Esto implica:

- conservar raw;
- registrar ejecuciones en `source_run`;
- registrar artefactos en `raw_asset`;
- vincular representaciones fuente mediante `place_source_ref`;
- mantener `place` como entidad canónica;
- guardar reviews en `review` solo cuando hay relación clara con `place`;
- almacenar resultados IA en tablas derivadas.

---

## 3. Fuentes contempladas

1. **Sevilla Geo**
2. **OSM / Overpass**
3. **Google Places Text Search**
4. **Google Places Reviews**
5. **Yelp Open Dataset**

---

## 4. Sevilla Geo

### Tipo

Dataset geográfico de referencia.

### Rol

Aporta barrios y distritos oficiales de Sevilla.

### Alimenta

- `district`;
- `neighborhood`;
- `place_neighborhood_assignment` de forma indirecta.

### Estado

Implementada y funcionando de extremo a extremo.

### Importancia

Sin esta fuente, Hidden Gems tendría coordenadas, pero no podría trabajar con ranking por barrio o distrito.

---

## 5. OSM / Overpass

### Tipo

Fuente abierta de puntos de interés geolocalizados.

### Rol

Aporta una base abierta inicial de locales gastronómicos.

### Alimenta

- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`;
- `validation_issue`.

### Estado

Implementada con:

- ingesta raw;
- perfilado;
- transformación;
- QA;
- deduplicación;
- importación;
- check post-importación.

---

## 6. Google Places Text Search

### Tipo

API externa dinámica.

### Rol

Fuente dinámica principal para descubrimiento y enriquecimiento de locales gastronómicos.

### Alimenta

- `source_system`;
- `source_run`;
- `raw_asset`;
- `place`;
- `place_source_ref`;
- `category`;
- `place_category`;
- `place_neighborhood_assignment`;
- `validation_issue`.

### Estado

Implementada y validada con:

- conector `GooglePlacesConnector`;
- Text Search;
- raw trazable;
- staging;
- deduplicación;
- importación canónica;
- batch por barrios/distritos;
- checks.

---

## 7. Google Places Reviews

### Tipo

Subvertical de Google Places basada en Place Details.

### Rol

Aporta reseñas reales asociadas a locales ya consolidados.

### Alimenta

- `review`;
- corpus local para IA;
- piloto IA Sevilla.

### Estado

Implementada y validada con batches controlados.

En la fase de piloto serio se consolidaron aproximadamente:

```text
800+ locales Google Places
4.000+ reviews Google Places
```

El corpus exportado para IA quedó en torno a:

```text
4.110 reviews
831 locales
96 barrios
11 distritos
```

Estas reviews son la fuente local real utilizada para el piloto IA Sevilla.

---

## 8. Yelp Open Dataset

### Tipo

Dataset externo de apoyo para IA/NLP y prototipo.

### Rol

Yelp aporta volumen para desarrollar y validar la inteligencia textual:

- detección de platos;
- normalización;
- sentimiento por mención;
- agregación;
- ranking.

### Estado

Implementado como:

- corpus NLP;
- prototipo IA integrado en PostgreSQL;
- ranking `yelp_prototype` consultable.

### Consideración

Yelp no representa producción Sevilla.

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 9. Clasificación de fuentes por función

| Fuente | Función principal | Tipo de dato | Estado |
|---|---|---|---|
| Sevilla Geo | Referencia territorial | Barrios, distritos, geometrías | Implementada |
| OSM / Overpass | POIs gastronómicos abiertos | Locales, coordenadas, tags | Implementada |
| Google Places Text Search | Descubrimiento/enriquecimiento | Locales, coordenadas, tipos | Implementada |
| Google Places Reviews | Reviews operativas locales | Reseñas enlazadas a `place` | Implementada y usada en piloto Sevilla |
| Yelp Open Dataset | Corpus IA/NLP y prototipo | Negocios, reviews, señales IA | Implementada como corpus/prototipo |

---

## 10. Estrategia multi-fuente

Las fuentes no se fusionan directamente entre sí.

Flujo:

```text
raw independiente
→ transformación específica
→ candidato común
→ place canónico
→ place_source_ref por fuente
→ review source-bound
→ capa IA derivada
```

Esto permite usar varias fuentes sin perder trazabilidad ni mezclar identidades externas.

---

## 11. Fuentes por uso

### 11.1. Fuentes de referencia

- Sevilla Geo.

### 11.2. Fuentes de negocio

- OSM / Overpass;
- Google Places;
- Yelp solo en modo prototipo IA.

### 11.3. Fuentes de reviews operativas

- Google Places Reviews.

### 11.4. Fuentes de corpus IA

- Yelp Open Dataset;
- Google Reviews Sevilla exportadas desde PostgreSQL.

---

## 12. Estado actual de integración

### Sevilla Geo

Completada.

### OSM / Overpass

Completada.

### Google Places

Completada para Text Search y batches por barrios/distritos.

### Google Places Reviews

Completada para carga controlada de reviews.

### Yelp Open Dataset

Completado como corpus/prototipo IA.

### Piloto IA Sevilla

Completado usando Google Places Reviews.

Flujo realizado:

```text
Google Places Reviews Sevilla
→ export_reviews_for_ai
→ notebooks 12–17
→ detección de platos
→ normalización local
→ sentimiento por mención
→ señales place-dish
→ ranking sevilla_pilot
→ carga PostgreSQL
→ check final
→ query demo
```

Resultado validado:

```text
reviews corpus = 4.110
mentions ranking-ready = 2.979
place-dish signals = 2.212
ranking candidates = 256
selected candidates = 150
ready_for_sevilla_pilot_queries = true
```

---

## 13. Riesgos y limitaciones generales

### Sevilla Geo

- puede cambiar si cambian límites administrativos;
- requiere consistencia de geometrías.

### OSM / Overpass

- datos colaborativos incompletos;
- tags heterogéneos;
- duplicados técnicos.

### Google Places

- uso sujeto a API key, cuotas y costes;
- Google no devuelve todas las reviews históricas;
- dependencia externa;
- escalado controlado por batches.

### Google Reviews

- número limitado de reviews por local;
- textos breves o poco descriptivos;
- sesgo positivo frecuente;
- no todas las menciones contienen valoración local explícita.

### Yelp

- no representa Sevilla;
- corpus mayoritariamente inglés;
- se mantiene como prototipo/corpus.

---

## 14. Relación de fuentes con IA

Yelp permitió construir el módulo IA amplio:

```text
Yelp reviews
→ dish NER
→ normalización
→ sentimiento
→ señales
→ yelp_prototype
```

Google Reviews permitió ejecutar el piloto local real:

```text
Google Reviews Sevilla
→ reglas/híbrido español
→ catálogo Sevilla
→ sentimiento por mención
→ señales local-plato
→ sevilla_pilot
```

---

## 15. Conclusión

La estrategia de fuentes de Hidden Gems combina datos estructurales, locales, reseñas y corpus IA.

El proyecto ya no está solo preparado para aplicar IA a Sevilla: el flujo se ha ejecutado con reviews reales de Google Places y ha generado un piloto `sevilla_pilot` cargado y consultable.

La siguiente fase de fuentes no es añadir más orígenes sin control, sino mejorar cobertura, revisar calidad, preparar dashboard y decidir si se amplía la extracción de reviews o se mejora el modelo IA.
