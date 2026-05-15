# 02. Visión general del pipeline Sevilla IA v2

## 1. Objetivo del pipeline v2

El pipeline Sevilla IA v2 transforma reseñas gastronómicas en un ranking experimental de platos destacados por barrio. La diferencia principal frente al piloto v1 es que ahora se introducen modelos entrenados en tres puntos críticos:

1. detección de menciones de platos;
2. normalización de menciones hacia un catálogo de platos;
3. sentimiento específico hacia cada mención de plato.

El objetivo no es solo obtener un ranking final, sino generar un flujo trazable donde cada candidato pueda explicarse desde sus evidencias originales.

---

## 2. Flujo general

El flujo completo de la fase es el siguiente:

```text
Reseñas Sevilla
    ↓
Extracción híbrida inicial de menciones
    ↓
Modelo 1: Dish NER
    ↓
Hybrid + NER mention candidates v2
    ↓
Modelo 3: Dish Normalization / Entity Linking
    ↓
Menciones normalizadas con dish_id
    ↓
Modelo 2: Mention Sentiment / ABSA
    ↓
Menciones con sentimiento por plato
    ↓
Place-dish signals v2
    ↓
Hidden Gems ranking v2
    ↓
Comparación ranking v1 vs v2
    ↓
Export dashboard v2
    ↓
Dashboard Sevilla IA v2
```

---

## 3. Principios de diseño

### 3.1. Modularidad

Cada bloque genera artefactos propios y puede ejecutarse, revisarse o sustituirse de forma independiente.

Ejemplo:

```text
normalization_reranker_v1/
sentiment_absa_v1/
place_dish_signals_v2/
ranking_v2/
```

Esto permite repetir una parte concreta del pipeline sin tener que reprocesar todo el sistema.

---

### 3.2. Trazabilidad

Cada capa conserva identificadores relevantes como:

- `review_id`;
- `place_id`;
- `dish_id`;
- texto de mención;
- contexto;
- estrategia de detección;
- confianza de normalización;
- confianza de sentimiento;
- motivos de revisión.

La trazabilidad es clave porque el ranking no debe ser una caja negra: cada posición debe poder justificarse con datos.

---

### 3.3. Enfoque experimental

El ranking v2 no se marca como producción. Se mantiene como fase experimental porque:

- usa modelos entrenados sobre datasets ampliados pero no masivos;
- algunas etiquetas de entrenamiento son débiles;
- muchas señales tienen evidencia `emerging`;
- todavía hay candidatos que requieren revisión manual;
- las reseñas públicas pueden tener sesgo positivo.

---

## 4. Bloque 1: Extracción de menciones

### 4.1. Entrada

La entrada inicial son reseñas con texto y metadatos de locales.

Campos relevantes:

- `review_id`;
- `place_id`;
- `place_name`;
- `review_text_raw`;
- `rating_value`;
- distrito y barrio asignados al local.

---

### 4.2. Extracción híbrida inicial

Antes de aplicar modelos, el sistema ya contaba con una extracción híbrida basada en:

- catálogo de platos;
- aliases;
- reglas léxicas;
- patrones de mención;
- scoring heurístico.

Esta capa servía como baseline del ranking v1.

---

### 4.3. Modelo NER de platos

El modelo NER detecta spans de texto que podrían corresponder a platos.

Ejemplo:

```text
"Pedimos croquetas de jamón y una tarta de queso espectacular."
```

Salida esperada:

```text
croquetas de jamón
tarta de queso
```

El modelo complementa la extracción híbrida, especialmente en casos donde el catálogo o las reglas no detectan bien una mención.

---

## 5. Bloque 2: Hybrid + NER candidates v2

Este bloque combina:

```text
menciones híbridas v1 + menciones NER v1.2
```

Genera una capa unificada con tres estrategias:

| Estrategia | Significado |
|---|---|
| `hybrid_and_ner` | La mención aparece tanto por sistema híbrido como por NER. Es la señal de mayor confianza. |
| `hybrid_only` | La mención aparece solo por la extracción híbrida. |
| `ner_only` | La mención aparece solo por NER. Es experimental y requiere más cautela. |

Resultados principales:

| Métrica | Valor |
|---|---:|
| Menciones híbridas | 2.979 |
| Menciones NER | 2.964 |
| Matches entre ambas capas | 2.735 |
| Filas finales candidatas | 2.965 |
| Reviews con candidatos | 1.626 |
| Locales con candidatos | 786 |

---

## 6. Bloque 3: Normalización / entity linking

### 6.1. Problema

Una mención textual no basta para el ranking. Es necesario convertirla en un plato canónico.

Ejemplos:

```text
"croquetas"
"croqueta de jamón"
"croquetas caseras"
```

pueden mapear a platos distintos o a un plato genérico, según el contexto.

---

### 6.2. Enfoque elegido

En lugar de entrenar un clasificador cerrado de platos, se entrena un reranker:

```text
mención + contexto + plato candidato → score de match
```

Esto permite que el catálogo crezca sin tener que redefinir completamente la tarea.

---

### 6.3. Inferencia local

El script local:

```text
scripts/run_sevilla_dish_normalization_reranker_v1.py
```

realiza:

1. carga de menciones Hybrid + NER v2;
2. carga del catálogo de platos y aliases;
3. generación de candidatos;
4. scoring con BETO reranker;
5. selección del mejor candidato;
6. marcado de baja confianza o revisión.

Resultados principales:

| Métrica | Valor |
|---|---:|
| Filas de entrada | 2.965 |
| Filas normalizadas | 2.965 |
| `linked` | 2.586 |
| `linked_needs_review` | 294 |
| `low_confidence` | 58 |
| `no_candidate` | 27 |
| Listas para sentimiento | 2.880 |

---

## 7. Bloque 4: Sentimiento por mención / ABSA

### 7.1. Problema

El sentimiento de una reseña completa no siempre coincide con el sentimiento hacia un plato concreto.

Ejemplo:

```text
"Las croquetas estaban increíbles, pero el arroz fue decepcionante."
```

Sentimiento por mención:

| Mención | Sentimiento |
|---|---|
| croquetas | positive |
| arroz | negative |

---

### 7.2. Modelo ABSA

El modelo ABSA clasifica cada mención normalizada en:

```text
negative
neutral
positive
```

Entrada conceptual:

```text
Mención + plato normalizado + contexto local + rating + local
```

---

### 7.3. Inferencia local

El script local:

```text
scripts/run_sevilla_mention_sentiment_absa_v1.py
```

aplica el modelo a las menciones normalizadas.

Resultados principales:

| Métrica | Valor |
|---|---:|
| Filas de entrada | 2.965 |
| Filas predichas | 2.880 |
| Filas no listas | 85 |
| Listas para downstream | 2.561 |
| Positivas | 2.388 |
| Negativas | 343 |
| Neutrales | 149 |

---

## 8. Bloque 5: Señales place-dish v2

La capa de señales agrega menciones por:

```text
place_id + dish_id
```

Esta es la granularidad central del proyecto, porque Hidden Gems no busca restaurantes genéricos, sino combinaciones específicas:

```text
local → plato destacado
```

Métricas generadas:

- `mention_count_v2`;
- `review_count_v2`;
- `positive_ratio_v2`;
- `negative_ratio_v2`;
- `weighted_sentiment_score_v2`;
- `avg_absa_confidence_v2`;
- `avg_normalization_confidence_v2`;
- `evidence_tier_v2`;
- `aggregate_quality_tier_v2`;
- `ready_for_ranking_v2`.

Resultados principales:

| Métrica | Valor |
|---|---:|
| Señales place-dish | 2.335 |
| Señales listas para ranking | 276 |
| Locales únicos | 638 |
| Platos únicos | 182 |
| Distritos | 12 |
| Barrios | 95 |

---

## 9. Bloque 6: Ranking Hidden Gems v2

El ranking v2 calcula una puntuación:

```text
hidden_gem_score_v2
```

La puntuación combina:

- sentimiento ABSA ponderado;
- volumen de menciones;
- número de reviews;
- evidencia;
- calidad de normalización;
- calidad de sentimiento;
- consenso entre extracción híbrida y NER;
- rareza o especificidad del plato;
- penalizaciones por negativos, baja evidencia o necesidad de revisión.

Resultados:

| Métrica | Valor |
|---|---:|
| Candidatos puntuados | 2.335 |
| Candidatos seleccionados | 268 |
| Locales seleccionados | 198 |
| Platos seleccionados | 40 |
| Barrios seleccionados | 67 |
| Distritos seleccionados | 11 |

Distribución:

| Tier | Candidatos |
|---|---:|
| `top_hidden_gem` | 16 |
| `strong_hidden_gem` | 77 |
| `promising_hidden_gem` | 139 |
| `exploratory_hidden_gem` | 36 |

---

## 10. Bloque 7: Comparación v1 vs v2

El pipeline incluye una comparación formal entre ranking v1 y ranking v2.

Resultados principales:

| Métrica | Valor |
|---|---:|
| Candidatos v1 | 150 |
| Candidatos v2 | 268 |
| Coincidentes | 119 |
| Solo v1 | 31 |
| Solo v2 | 149 |
| Cobertura de v1 en v2 | 79,3 % |
| Jaccard overlap | 39,8 % |
| Incremento de locales | +76 |
| Incremento de barrios | +12 |

La lectura es positiva: v2 mantiene gran parte del ranking v1 y amplía notablemente la cobertura.

---

## 11. Bloque 8: Dashboard v2

El export del dashboard prepara una carpeta limpia:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Archivos principales:

```text
ranking_detail.csv
selected_candidates.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
district_summary.csv
neighborhood_summary.csv
dish_summary.csv
place_summary.csv
mention_examples.csv
comparison/
data_contract.json
```

El dashboard Streamlit consume estos archivos y ofrece una interfaz para explorar:

- ranking global;
- territorio;
- platos;
- locales;
- calidad;
- evidencia;
- reseñas;
- comparación v1/v2;
- explicación de la puntuación.

---

## 12. Salidas principales del pipeline

| Fase | Carpeta de salida |
|---|---|
| Hybrid + NER | `data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/` |
| Normalización | `data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/` |
| Sentimiento ABSA | `data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/` |
| Señales place-dish | `data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/` |
| Ranking v2 | `data/artifacts/ai/sevilla/model_inference/ranking_v2/` |
| Comparación | `data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison/` |
| Dashboard v2 | `data/artifacts/ai/sevilla/dashboard_v2/` |

---

## 13. Decisión técnica

El pipeline v2 queda validado como flujo experimental de IA para Sevilla.

La decisión es:

```text
Usar ranking v2 como ranking principal experimental para análisis y dashboard.
Mantener ranking v1 como baseline comparativo.
No marcar v2 como producción hasta completar revisión humana y mejora de evidencia.
```
