# 02. Pipeline de notebooks IA del piloto Sevilla

## 1. Objetivo

Este documento describe el flujo de notebooks ejecutado para transformar las reseñas reales de Google Places Sevilla en un ranking piloto de Hidden Gems.

El pipeline IA parte de un JSONL de reseñas y produce progresivamente:

```text
reviews reales
→ candidatos de platos
→ catálogo normalizado
→ sentimiento por mención
→ señales local-plato
→ ranking sevilla_pilot
```

La estrategia seguida es híbrida: combina reglas, lexicones, normalización controlada, señales estadísticas y scoring explicable. No se utiliza todavía un modelo transformer entrenado específicamente para español, porque el objetivo de esta fase era construir un primer prototipo serio, trazable y depurable.

## 2. Entrada común del pipeline

Archivo de entrada:

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

Resumen del corpus:

| Métrica | Valor |
|---|---:|
| Reviews | 4.110 |
| Locales | 831 |
| Barrios | 96 |
| Distritos | 11 |
| Reviews en español | 4.108 |
| Reviews sin texto | 0 |
| Reviews sin barrio | 0 |
| Reviews sin distrito | 0 |

## 3. Notebook 12 — Exploración del corpus Sevilla

Notebook:

```text
notebooks/12_sevilla_reviews_ai_exploration.ipynb
```

### 3.1. Objetivo

Explorar el corpus real de reseñas antes de construir reglas de detección de platos.

Este notebook responde preguntas como:

- cuántas reseñas hay por distrito y barrio;
- cuántos locales tienen reseñas;
- qué distribución de ratings existe;
- qué longitud tienen los textos;
- qué términos gastronómicos aparecen;
- qué porcentaje del corpus parece útil para IA gastronómica.

### 3.2. Entradas

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

### 3.3. Salidas principales

```text
data/artifacts/ai/sevilla/exploration/sevilla_reviews_ai_exploration_summary.json
data/artifacts/ai/sevilla/exploration/top_terms_by_rating.csv
data/artifacts/ai/sevilla/exploration/top_terms_by_neighborhood.csv
data/artifacts/ai/sevilla/exploration/candidate_reviews_with_food_terms_for_manual_inspection.csv
```

### 3.4. Resultados clave

| Métrica | Valor |
|---|---:|
| Reviews totales | 4.110 |
| Reviews con algún término gastronómico | 2.632 |
| Porcentaje con término gastronómico | 64,04 % |
| Reviews de utilidad alta inicial | 1.580 |
| Reviews de utilidad media inicial | 1.002 |
| Reviews de utilidad baja inicial | 50 |
| Reviews sin señal gastronómica inicial | 1.478 |

Términos gastronómicos frecuentes detectados en la exploración:

```text
croquetas, ensaladilla, solomillo, carrillada, atún, gambas,
bravas, bacalao, churros, pescado, presa, tortilla, salmorejo,
pulpo, hamburguesa, tarta de queso
```

### 3.5. Conclusión

El corpus era suficiente para construir una detección inicial de platos en español, pero requería separar cuidadosamente:

- platos concretos;
- términos genéricos;
- bebidas;
- ingredientes;
- acompañamientos;
- menciones ambiguas.

## 4. Notebook 13 — Detección de candidatos de platos

Notebook:

```text
notebooks/13_sevilla_dish_candidate_detection.ipynb
```

### 4.1. Objetivo

Detectar menciones candidatas de platos en las reseñas reales de Sevilla.

El enfoque combina:

- lexicón gastronómico español/andaluz;
- patrones regex para platos compuestos;
- detección de contexto gastronómico;
- clasificación de candidatos por tipo;
- extracción de contexto local.

### 4.2. Entradas

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

### 4.3. Salidas principales

```text
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_all_v1.csv
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_all_v1.jsonl
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_v1.csv
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_v1.jsonl
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_for_manual_review_v1.csv
data/artifacts/ai/sevilla/dish_detection/sevilla_top_canonical_dishes_v1.csv
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_detection_summary_v1.json
```

### 4.4. Resultados clave

| Métrica | Valor |
|---|---:|
| Candidatos totales de todos los tipos | 12.854 |
| Candidatos tipo plato | 3.659 |
| Reviews con algún candidato | 3.681 |
| Reviews con candidato de plato | 1.738 |
| Locales con candidato de plato | 706 |

Distribución por tipo:

| Tipo | Conteo |
|---|---:|
| `dish_candidate` | 3.659 |
| `generic_food_term` | 5.999 |
| `ingredient_or_side` | 1.944 |
| `beverage` | 1.252 |

### 4.5. Ejemplos de platos detectados

```text
ensaladilla
croqueta
carrillada
solomillo al whisky
atún
tarta de queso
patatas bravas
gambas
hamburguesa
churros
chocos
torrija
presa ibérica
bacalao
salmorejo
pulpo
tortilla de patatas
rabo de toro
pringá
```

### 4.6. Conclusión

La detección fue suficientemente buena para pasar a normalización, pero no para ranking directo. Antes era necesario construir un catálogo local y decidir qué menciones eran realmente elegibles.

## 5. Notebook 14 — Normalización y catálogo local Sevilla

Notebook:

```text
notebooks/14_sevilla_dish_normalization_and_catalog.ipynb
```

### 5.1. Objetivo

Convertir las menciones detectadas en un catálogo normalizado de platos locales.

El notebook genera:

- identificadores estables de plato;
- nombres normalizados;
- nombres de visualización;
- familias gastronómicas;
- grupos de plato;
- aliases;
- estado de elegibilidad para ranking.

### 5.2. Entradas

```text
data/artifacts/ai/sevilla/dish_detection/sevilla_dish_candidates_v1.jsonl
```

### 5.3. Salidas principales

```text
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_catalog_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_aliases_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_normalized_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_normalized_v1.jsonl
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_ranking_ready_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_ranking_ready_v1.jsonl
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_needing_review_v1.csv
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_normalization_summary_v1.json
```

### 5.4. Resultados clave

| Métrica | Valor |
|---|---:|
| Menciones candidatas iniciales | 3.659 |
| Menciones normalizadas | 3.659 |
| Menciones ranking-ready | 2.979 |
| Menciones para revisión | 599 |
| Menciones excluidas | 81 |
| Tamaño del catálogo local | 190 |
| Platos elegibles para ranking | 181 |
| Aliases generados | 243 |
| Reviews con plato ranking-ready | 1.452 |
| Locales con plato ranking-ready | 635 |
| Barrios cubiertos | 94 |
| Distritos cubiertos | 11 |

Familias principales del catálogo:

| Familia | Conteo |
|---|---:|
| `tapas_clasicas` | 57 |
| `postres_y_desayunos` | 26 |
| `mar_y_pescado` | 24 |
| `otros` | 24 |
| `carne` | 21 |
| `fritos_y_raciones` | 15 |
| `arroces_y_pasta` | 15 |
| `internacional` | 8 |

### 5.5. Conclusión

El catálogo normalizado permitió pasar de detecciones textuales a entidades de plato utilizables en base de datos y ranking.

## 6. Notebook 15 — Sentimiento por mención

Notebook:

```text
notebooks/15_sevilla_mention_sentiment.ipynb
```

### 6.1. Objetivo

Asignar sentimiento a cada mención ranking-ready de plato.

El objetivo no era clasificar la review completa, sino la valoración asociada a cada plato concreto.

### 6.2. Enfoque

El sentimiento se calculó con un enfoque híbrido:

- lexicón positivo/negativo gastronómico en español;
- detección de negaciones;
- detección de intensificadores;
- detección de contraste;
- señales locales por contexto de mención;
- fallback al rating cuando no hay señal local clara;
- flags para revisión manual.

### 6.3. Entradas

```text
data/artifacts/ai/sevilla/dish_normalization/sevilla_dish_candidates_ranking_ready_v1.jsonl
```

### 6.4. Salidas principales

```text
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.jsonl
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.csv
data/artifacts/ai/sevilla/sentiment/sevilla_mention_sentiment_summary_v1.json
data/artifacts/ai/sevilla/sentiment/sevilla_mention_sentiment_by_dish_v1.csv
data/artifacts/ai/sevilla/sentiment/sevilla_mention_sentiment_by_place_dish_v1.csv
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_sentiment_manual_review_v1.csv
```

### 6.5. Resultados clave

| Métrica | Valor |
|---|---:|
| Menciones con sentimiento | 2.979 |
| Reviews únicas | 1.452 |
| Locales únicos | 635 |
| Platos únicos | 181 |
| Barrios | 94 |
| Distritos | 11 |

Distribución de sentimiento:

| Sentimiento | Conteo |
|---|---:|
| `positive` | 2.395 |
| `negative` | 388 |
| `neutral` | 196 |

Razón del sentimiento:

| Razón | Conteo |
|---|---:|
| `local_context_primary` | 1.590 |
| `review_prior_fallback` | 1.389 |

Confianza:

| Métrica | Valor |
|---|---:|
| Mínima | 0,28 |
| Media | 0,6319 |
| Mediana | 0,71 |
| Máxima | 0,95 |

### 6.6. Conclusión

El resultado fue válido para agregación, pero con una advertencia: muchas menciones usan fallback del rating o requieren revisión manual. Por eso el ranking posterior debía ponderar la confianza y no tratar todas las menciones como evidencia equivalente.

## 7. Notebook 16 — Agregación de señales local-plato

Notebook:

```text
notebooks/16_sevilla_place_dish_signal_aggregation.ipynb
```

### 7.1. Objetivo

Agrupar menciones individuales en señales por pareja:

```text
local + plato
```

Esta fase convierte menciones dispersas en una unidad útil para ranking.

### 7.2. Entradas

```text
data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.jsonl
```

### 7.3. Salidas principales

```text
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_signals_v1.csv
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_signals_v1.jsonl
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_ranking_candidates_v1.csv
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_ranking_candidates_v1.jsonl
data/artifacts/ai/sevilla/aggregation/sevilla_global_dish_signals_v1.csv
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_signal_summary_v1.json
```

### 7.4. Resultados clave

| Métrica | Valor |
|---|---:|
| Pares local-plato generados | 2.212 |
| Pares ranking-ready | 256 |
| Pares no ranking-ready | 1.956 |
| Locales con señal | 635 |
| Platos con señal | 181 |
| Barrios con señal | 94 |
| Distritos con señal | 11 |

Tiers de evidencia:

| Evidence tier | Conteo |
|---|---:|
| `weak` | 1.909 |
| `emerging` | 215 |
| `solid` | 76 |
| `strong` | 12 |

Tiers de calidad:

| Signal quality tier | Conteo |
|---|---:|
| `single_mention_signal` | 1.720 |
| `weak_signal` | 203 |
| `emerging_signal` | 179 |
| `usable_signal` | 72 |
| `noisy_signal` | 28 |
| `high_quality_signal` | 10 |

### 7.5. Conclusión

La agregación fue conservadora: de 2.212 pares local-plato solo 256 quedaron listos para ranking. Esto es adecuado para un piloto porque reduce falsos positivos y evita seleccionar platos con una sola mención casual.

## 8. Notebook 17 — Ranking Hidden Gems Sevilla piloto

Notebook:

```text
notebooks/17_sevilla_hidden_gems_ranking_pilot.ipynb
```

### 8.1. Objetivo

Construir el ranking piloto `sevilla_pilot` a partir de las señales local-plato.

El ranking combina:

- calidad local del plato;
- volumen de evidencia;
- confianza de sentimiento;
- rareza o diferenciación del plato;
- singularidad por barrio;
- penalización por negativos;
- penalización por ruido de señal.

### 8.2. Entradas

```text
data/artifacts/ai/sevilla/aggregation/sevilla_place_dish_ranking_candidates_v1.jsonl
data/artifacts/ai/sevilla/aggregation/sevilla_global_dish_signals_v1.csv
```

### 8.3. Salidas principales

```text
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_candidates_all_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_candidates_all_v1.jsonl
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_selected_candidates_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_selected_candidates_v1.jsonl
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_top_by_neighborhood_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_top_by_district_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_top_by_dish_v1.csv
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_ranking_summary_v1.json
```

### 8.4. Pesos del ranking

| Componente | Peso |
|---|---:|
| Calidad local del plato | 0,42 |
| Evidencia | 0,24 |
| Confianza | 0,18 |
| Hiddenness / diferenciación | 0,10 |
| Unicidad por barrio | 0,06 |
| Penalización máxima por negativos | 0,18 |
| Penalización máxima por ruido | 0,10 |

### 8.5. Resultados clave

| Métrica | Valor |
|---|---:|
| Pares evaluados | 256 |
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

Resumen de score seleccionado:

| Métrica | Valor |
|---|---:|
| Mínimo | 55,0423 |
| Media | 63,2804 |
| Mediana | 62,7168 |
| Máximo | 80,1471 |

### 8.6. Top inicial del ranking

| Rank | Local | Plato | Barrio | Distrito | Score | Tier |
|---:|---|---|---|---|---:|---|
| 1 | Pizzería San Pablo | pizza | SAN PABLO D Y E | San Pablo - Santa Justa | 80,1471 | `top_hidden_gem` |
| 2 | restaurante asiático shan | sushi | BELLAVISTA | Bellavista - La Palmera | 78,9556 | `top_hidden_gem` |
| 3 | Il Ristorantino Dell'Avvocato Calle Cuna | pizza | ALFALFA | Casco Antiguo | 74,1349 | `strong_hidden_gem` |
| 4 | Tarannà | atún | SANTA CATALINA | Casco Antiguo | 73,8812 | `strong_hidden_gem` |
| 5 | Il Ristorantino Dell´Avvocato Sevilla | pizza | ENCARNACIÓN-REGINA | Casco Antiguo | 73,2847 | `strong_hidden_gem` |
| 6 | Flor de la Caña Café y Ron SR. | tarta de queso | LEON XIII-LOS NARANJOS | Macarena | 72,0559 | `strong_hidden_gem` |
| 7 | Taberna Los Terceros | solomillo al whisky | SANTA CATALINA | Casco Antiguo | 70,9464 | `strong_hidden_gem` |
| 8 | Cafeteria mi abuela, churreria | churros | FELIPE II-LOS DIEZ MANDAMIENTOS | Sur | 70,4390 | `strong_hidden_gem` |
| 9 | I Love Churros | churros | CRUZ ROJA-CAPUCHINOS | Macarena | 70,3222 | `strong_hidden_gem` |
| 10 | BAR EL BUCHITO | carrillada | PALMETE | Cerro - Amate | 72,0268 | `promising_hidden_gem` |

### 8.7. Cobertura por distrito

| Distrito | Seleccionados | Locales | Platos | Score medio | Score máximo |
|---|---:|---:|---:|---:|---:|
| Casco Antiguo | 44 | 36 | 22 | 64,5088 | 74,1349 |
| Cerro - Amate | 15 | 11 | 9 | 64,2626 | 72,0268 |
| Sur | 14 | 10 | 11 | 63,1903 | 70,4390 |
| Este - Alcosa - Torreblanca | 14 | 10 | 11 | 60,8352 | 68,1937 |
| Nervión | 13 | 10 | 10 | 60,8016 | 70,1081 |
| San Pablo - Santa Justa | 12 | 11 | 11 | 64,2632 | 80,1471 |
| Macarena | 10 | 10 | 8 | 63,4995 | 72,0559 |
| Triana | 10 | 8 | 9 | 61,9835 | 69,4382 |
| Norte | 9 | 7 | 9 | 62,7034 | 70,4884 |
| Bellavista - La Palmera | 7 | 7 | 6 | 63,9384 | 78,9556 |
| Los Remedios | 2 | 2 | 2 | 62,5360 | 67,4108 |

### 8.8. Conclusión

El notebook 17 generó un ranking piloto amplio, explicable y suficientemente consistente para ser cargado en PostgreSQL.

El resultado no se considera producción, pero sí una prueba funcional completa de Hidden Gems:

```text
reseñas reales → IA híbrida → ranking local-plato → carga en base → consulta demo
```

## 9. Salidas consolidadas del pipeline IA

| Fase | Artefacto clave |
|---|---|
| Exploración | `sevilla_reviews_ai_exploration_summary.json` |
| Detección | `sevilla_dish_candidates_v1.jsonl` |
| Normalización | `sevilla_dish_candidates_ranking_ready_v1.jsonl` |
| Catálogo | `sevilla_dish_catalog_v1.csv` |
| Aliases | `sevilla_dish_aliases_v1.csv` |
| Sentimiento | `sevilla_dish_mentions_with_sentiment_v1.jsonl` |
| Agregación | `sevilla_place_dish_signals_v1.jsonl` |
| Ranking input | `sevilla_place_dish_ranking_candidates_v1.jsonl` |
| Ranking final | `sevilla_hidden_gems_selected_candidates_v1.jsonl` |

## 10. Decisiones importantes

### 10.1. Enfoque híbrido antes que modelo entrenado

Se optó por un enfoque híbrido porque:

- el modelo NER previo estaba entrenado en inglés;
- el corpus Sevilla está casi completamente en español;
- las reglas permiten depurar errores rápidamente;
- el volumen del piloto es suficiente para reglas, pero no necesariamente para fine-tuning robusto;
- el objetivo era validación end-to-end, no máximo rendimiento de modelo.

### 10.2. Filtrar antes de ranking

No todas las menciones detectadas llegan al ranking.

El pipeline filtra progresivamente:

```text
12.854 candidatos totales
→ 3.659 candidatos tipo plato
→ 2.979 menciones ranking-ready
→ 2.212 señales local-plato
→ 256 pares ranking-ready
→ 150 hidden gems seleccionados
```

Este filtrado reduce ruido y evita que términos genéricos o menciones únicas dominen el ranking.

### 10.3. Ranking no productivo todavía

Todos los candidatos seleccionados quedan con:

```text
is_production_ready = false
```

Motivos:

- evidencia por local limitada;
- necesidad de revisión manual adicional;
- reglas de sentimiento todavía mejorables;
- ranking weights aún experimentales;
- dependencia de una sola fuente de reviews.

## 11. Resultado de la fase

La fase de notebooks IA queda completada con éxito y habilita la siguiente fase:

```text
Carga y validación en PostgreSQL
```

Esa fase se documenta en `03_database_loading_and_validation.md`.
