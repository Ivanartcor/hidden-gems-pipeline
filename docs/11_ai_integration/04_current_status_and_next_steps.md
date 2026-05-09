# 04 - Current Status and Next Steps

## Estado actual

La integración del módulo IA en PostgreSQL queda completada y validada.

Se han realizado estas fases:

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

---

## Estado de datos cargados

El check final confirma los siguientes conteos:

| Tabla | Registros |
|---|---:|
| `dish` | 9.937 |
| `dish_alias` | 10.235 |
| `dish_mention` | 94.932 |
| `dish_mention_sentiment` | 94.932 |
| `dish_place_signal` | 31.036 |
| `hidden_gem_candidate` | 622 |
| `place` | 7.230 |
| `review` | 80.037 |

---

## Resumen de menciones

```text
dish_mentions = 94.932
reviews_with_mentions = 42.461
places_with_mentions = 4.088
dishes_mentioned = 9.937
avg_ner_confidence = 0.97571
```

Esto confirma que el módulo NER quedó integrado y conectado con reviews, places y catálogo de platos.

---

## Distribución de sentimiento

La tabla `dish_mention_sentiment` contiene:

| Sentimiento | Tier | Registros |
|---|---|---:|
| positive | high | 22.322 |
| positive | medium | 17.729 |
| positive | low | 3.091 |
| neutral | medium | 4.376 |
| neutral | low | 40.990 |
| negative | high | 2.689 |
| negative | medium | 3.390 |
| negative | low | 345 |

La distribución confirma la decisión tomada durante el módulo 09: el sentimiento final es conservador y muchos neutrales de baja fiabilidad se mantienen como señales débiles.

---

## Resumen de señales agregadas

```text
total_signals = 31.036
places_with_signals = 4.088
dishes_with_signals = 9.937
rankable_signals = 3.841
avg_confidence_weighted_sentiment = 0.36397
avg_bayesian_sentiment_score = 0.09125
```

Esto refleja el paso de menciones individuales a pares `place + dish`.

---

## Resumen del ranking cargado

```text
ranking_scope = yelp_prototype
ranking_version = hidden_gems_ranking_v1
total_candidates = 622
selected_candidates = 622
min_score = 60.00283
avg_score = 66.86828
max_score = 82.92816
production_ready_rows = 0
```

Distribución por tier:

| Tier | Registros | Score mínimo | Score medio | Score máximo |
|---|---:|---:|---:|---:|
| `top_hidden_gem` | 2 | 82.04289 | 82.48553 | 82.92816 |
| `strong_hidden_gem` | 50 | 75.16746 | 77.38033 | 81.98466 |
| `promising_hidden_gem` | 182 | 68.01238 | 70.95088 | 74.97431 |
| `exploratory_hidden_gem` | 388 | 60.00283 | 63.51809 | 67.99076 |

---

## Top candidatos actuales

Los primeros candidatos cargados son:

```text
1. Sushi Ushi → sushi → 82.92816
2. Taqueria Cuernavaca → tacos → 82.04289
3. Blues City Deli → sandwich → 81.98466
4. Surrey's Café & Juice Bar → shrimp → 81.89650
5. Three Muses → steak → 81.74085
```

Estos resultados son coherentes con el ranking generado en los notebooks y ahora están disponibles desde PostgreSQL.

---

## Integridad validada

El check final confirma:

```text
orphan_dish_mentions_review = 0
orphan_dish_mentions_place = 0
orphan_dish_mentions_dish = 0
orphan_sentiments_mention = 0
orphan_signals_place = 0
orphan_signals_dish = 0
orphan_candidates_signal = 0
```

Esto significa que:

- no hay menciones sin review;
- no hay menciones sin place;
- no hay menciones sin dish;
- no hay sentimientos sin mención;
- no hay señales sin place/dish;
- no hay candidatos sin señal asociada.

---

## Estado de producción

Actualmente:

```text
ranking_scope = yelp_prototype
production_ready_candidates = 0
candidates_with_neighborhood = 0
```

Esto es correcto y esperado.

El ranking cargado no debe interpretarse como ranking final de Sevilla. Es un prototipo validado con Yelp para demostrar que la cadena completa funciona.

---

## Qué está ya cerrado

La parte cerrada del proyecto incluye:

```text
IA experimental en notebooks
↓
documentación del bloque IA
↓
schema IA en PostgreSQL
↓
loaders de artefactos IA
↓
checks de integridad
↓
vistas SQL
↓
script de demo de consultas
```

En términos prácticos, ya existe una cadena completa:

```text
reviews
→ menciones de platos
→ sentimiento por mención
→ señales por local/plato
→ ranking
→ PostgreSQL
→ vistas consultables
```

---

# Siguiente fase recomendada

La siguiente fase natural es volver al objetivo real del producto:

```text
Sevilla + Google Places + OSM + barrios
```

El objetivo será adaptar la cadena ya validada para datos reales de Sevilla.

---

## Fase 1 siguiente: ranking Sevilla operativo inicial

El primer paso realista no debería ser entrenar más IA, sino conectar lo que ya existe con datos operativos.

Objetivo:

```text
place de Sevilla
+ reviews de Google Places
+ neighborhood assignment
→ aplicar lógica IA
→ generar candidatos Hidden Gems por barrio
```

Para esto hará falta revisar:

```text
1. Qué places de Google Places tienen reviews cargadas.
2. Qué places tienen asignación a barrio.
3. Qué volumen de texto real existe en español/inglés.
4. Si el modelo actual puede procesar esos textos directamente.
5. Si hace falta traducción o adaptación lingüística.
```

---

## Fase 2 siguiente: loaders o jobs IA para datos operativos

Hasta ahora los artefactos vienen de notebooks.

Para Sevilla, necesitaremos jobs reproducibles:

```text
scripts/run_ai_dish_detection_for_reviews.py
scripts/run_ai_mention_sentiment_for_reviews.py
scripts/run_ai_signal_aggregation_for_places.py
scripts/run_hidden_gems_ranking.py
```

O una estructura productiva dentro de:

```text
src/ai/
```

Con módulos como:

```text
src/ai/dish_detection.py
src/ai/dish_normalization.py
src/ai/mention_sentiment.py
src/ai/signal_aggregation.py
src/ai/ranking.py
```

---

## Fase 3 siguiente: integración con barrios

Para que Hidden Gems cumpla su objetivo real, el ranking debe poder responder:

```text
¿Qué platos destacan por barrio?
```

Eso implica poblar correctamente:

```text
hidden_gem_candidate.neighborhood_id
hidden_gem_candidate.district_id
```

A partir de:

```text
place_neighborhood_assignment
```

Y crear vistas futuras como:

```text
vw_ai_hidden_gems_by_neighborhood
vw_ai_hidden_gems_sevilla_top
vw_ai_hidden_gems_neighborhood_dish_summary
```

---

## Fase 4 siguiente: adaptación lingüística

El modelo IA fue desarrollado principalmente sobre Yelp en inglés.

Para Sevilla, las reviews pueden estar en:

```text
español
inglés
multilingüe
texto mixto
```

Opciones futuras:

1. Usar el modelo actual como baseline.
2. Traducir subconjuntos de entrenamiento.
3. Crear un dataset español de platos y sentimiento.
4. Entrenar un modelo ABSA específico.
5. Ampliar `dish_alias` con términos españoles.

No conviene empezar esta fase hasta conocer el volumen real de reviews disponibles en Google Places.

---

## Fase 5 siguiente: API o dashboard

Una vez exista ranking operativo para Sevilla, tendrá sentido exponerlo.

Posibles salidas:

```text
FastAPI endpoint: /hidden-gems
FastAPI endpoint: /hidden-gems/by-neighborhood/{neighborhood_id}
FastAPI endpoint: /places/{place_id}/dishes
Power BI / dashboard
Jupyter demo
```

Pero esta fase debería venir después de tener candidatos reales de Sevilla.

---

## Orden recomendado desde aquí

El orden recomendado es:

```text
1. Revisar estado de reviews Google Places en base de datos.
2. Revisar asignación de places a barrios.
3. Crear check de readiness Sevilla IA.
4. Diseñar primer job IA operativo sobre reviews existentes.
5. Generar primeras dish_mentions operativas para Google Places.
6. Agregar señales por place/dish.
7. Generar ranking Sevilla global.
8. Generar ranking por barrio.
9. Crear vistas Sevilla.
10. Documentar resultados.
```

---

## Script recomendado como siguiente paso inmediato

El siguiente script útil sería:

```text
scripts/check_sevilla_ai_readiness.py
```

Este script debería comprobar:

```text
places de Google Places con reviews
reviews elegibles para IA
idiomas disponibles
places con coordenadas
places con neighborhood assignment
barrios con suficientes places/reviews
volumen textual por barrio
```

Con eso sabremos si podemos aplicar el módulo IA directamente a Sevilla o si antes necesitamos más adquisición de datos.

---

## Conclusión

La integración IA en PostgreSQL queda completada.

El proyecto está listo para pasar de:

```text
prototipo IA validado con Yelp
```

a:

```text
aplicación progresiva sobre datos reales de Sevilla
```

La prioridad ahora debería ser medir la preparación real del dataset Sevilla/Google Places antes de ejecutar modelos o rankings productivos.
