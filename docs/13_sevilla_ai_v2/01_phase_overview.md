# 01. Resumen ejecutivo de la fase Sevilla IA v2

## 1. Contexto

La fase **Sevilla IA v2** nace como evolución del ranking piloto inicial de Hidden Gems Sevilla. El ranking v1 ya permitía seleccionar combinaciones interesantes de local y plato a partir de menciones, sentimiento aproximado y reglas de scoring, pero todavía dependía demasiado de heurísticas.

La nueva fase busca reforzar el sistema con modelos entrenados específicamente para el dominio gastronómico del proyecto:

1. **NER de platos**: detectar mejor menciones de platos dentro de reseñas.
2. **Normalización / entity linking**: enlazar cada mención con un plato canónico del catálogo.
3. **Sentimiento por mención / ABSA**: estimar el sentimiento hacia un plato concreto, no hacia toda la reseña.

Con estos tres bloques, el sistema pasa de una lógica principalmente híbrida/reglada a una arquitectura más cercana a un pipeline de IA modular, evaluable y extensible.

---

## 2. Objetivo de la fase

El objetivo principal de esta fase es construir un nuevo ranking experimental:

```text
sevilla_hidden_gems_ranking_v2
```

Este ranking debe ser capaz de:

- aprovechar menciones de platos detectadas por modelos entrenados;
- normalizar menciones hacia un catálogo de platos;
- usar sentimiento ABSA por plato;
- agregar señales por `place_id + dish_id`;
- generar una puntuación `hidden_gem_score_v2` más rica que la del piloto v1;
- compararse contra el ranking v1;
- alimentar un dashboard específico de IA v2.

---

## 3. Qué se ha construido

Durante la fase se han construido las siguientes capas:

```text
Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
→ Hidden Gems ranking v2
→ Ranking v1 vs v2 comparison
→ Dashboard Sevilla IA v2 export
→ Dashboard Streamlit Sevilla IA v2
```

Cada capa genera artefactos intermedios en CSV/JSONL, resúmenes JSON y ficheros de revisión.

---

## 4. Modelos entrenados

### 4.1. Modelo 1: Dish NER

Modelo para detectar menciones de platos en reseñas.

- Tipo: `TokenClassification`.
- Modelo base: BETO (`dccuchile/bert-base-spanish-wwm-cased`).
- Salida: spans de texto correspondientes a platos.
- Uso: complementar el sistema híbrido de detección de menciones.

---

### 4.2. Modelo 3: Dish Normalization / Entity Linking

Modelo para decidir si una mención corresponde a un plato candidato.

- Tipo: cross-encoder / reranker binario.
- Modelo base: BETO.
- Entrada: mención + contexto + plato candidato.
- Salida: score de correspondencia.
- Uso: seleccionar el `dish_id` más probable entre candidatos del catálogo.

Resultado del entrenamiento fuerte con dataset extendido:

| Métrica | Valor aproximado |
|---|---:|
| Test pair accuracy | 0,9991 |
| Test pair F1 | 0,9977 |
| Test ranking accuracy@1 | 1,0000 |
| Test ranking accuracy@3 | 1,0000 |
| Test MRR | 1,0000 |

---

### 4.3. Modelo 2: Mention Sentiment / ABSA

Modelo para clasificar el sentimiento hacia una mención concreta de plato.

- Tipo: sequence classification multiclase.
- Modelo base: BETO.
- Clases: `negative`, `neutral`, `positive`.
- Entrada: mención + plato normalizado + contexto + rating + local.
- Uso: sustituir/reforzar el sentimiento híbrido anterior.

Resultados principales:

| Métrica | Valor |
|---|---:|
| Accuracy test | 0,9472 |
| Macro F1 test | 0,9353 |
| Negative F1 | 0,9259 |
| Neutral F1 | 0,9158 |
| Positive F1 | 0,9643 |

---

## 5. Resultados del ranking IA v2

El ranking v2 genera una selección más amplia y diversa que el ranking v1.

| Métrica | Valor |
|---|---:|
| Candidatos puntuados | 2.335 |
| Candidatos seleccionados | 268 |
| Locales seleccionados | 198 |
| Platos seleccionados | 40 |
| Barrios seleccionados | 67 |
| Distritos seleccionados | 11 |
| Menciones usadas en seleccionados | 651 |
| Reviews usadas en seleccionados | 627 |
| Score medio seleccionado | 80,58 |
| Score máximo seleccionado | 91,66 |
| Score mínimo seleccionado | 66,12 |

Distribución por tier:

| Tier | Candidatos |
|---|---:|
| `top_hidden_gem` | 16 |
| `strong_hidden_gem` | 77 |
| `promising_hidden_gem` | 139 |
| `exploratory_hidden_gem` | 36 |

---

## 6. Comparación con el ranking v1

La comparación contra v1 muestra que el ranking v2 mantiene gran parte de lo ya detectado y, al mismo tiempo, amplía la cobertura.

| Métrica | Valor |
|---|---:|
| Seleccionados únicos v1 | 150 |
| Seleccionados únicos v2 | 268 |
| Coincidentes entre v1 y v2 | 119 |
| Solo v1 | 31 |
| Solo v2 | 149 |
| Cobertura de v1 dentro de v2 | 79,3 % |
| Jaccard overlap | 39,8 % |
| Incremento de locales | +76 |
| Incremento de barrios | +12 |

Interpretación:

- El v2 conserva casi el 80 % del ranking piloto v1.
- El v2 añade muchos candidatos nuevos gracias a los modelos entrenados.
- El v2 aumenta la cobertura territorial y de locales.
- El v2 no debe compararse con v1 usando scores absolutos, porque la fórmula de scoring cambió.

---

## 7. Dashboard Sevilla IA v2

Para explotar los resultados se ha creado un nuevo dashboard Streamlit:

```text
dashboard/streamlit_sevilla_v2_app.py
```

El dashboard utiliza el export:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

Incluye:

- KPIs del ranking IA v2;
- filtros por distrito, barrio, plato, local, tier, evidencia, calidad y score;
- ranking global y rankings por territorio/plato;
- mapa territorial con coordenadas cuando están disponibles;
- comparación v1 vs v2;
- análisis de evidencia y calidad;
- detalle de menciones y reseñas;
- explicación de la puntuación;
- contrato de datos.

---

## 8. Estado de madurez

El resultado de esta fase debe considerarse:

```text
ranking experimental asistido por modelos
```

No debe considerarse producción porque:

- `production_ready_count_v2 = 0`;
- muchas señales seleccionadas tienen evidencia `emerging`;
- hay casos de baja confianza o revisión manual;
- el corpus de reseñas públicas tiene sesgo hacia opiniones positivas;
- el catálogo de platos puede seguir ampliándose;
- algunos platos genéricos aparecen muy arriba y pueden requerir ajuste futuro.

---

## 9. Conclusión

La fase Sevilla IA v2 demuestra que Hidden Gems puede evolucionar desde un ranking piloto basado en reglas hacia un pipeline de IA más completo, formado por:

```text
extracción → normalización → sentimiento → agregación → ranking → dashboard
```

La mejora más importante no es solo el aumento de candidatos, sino la trazabilidad completa de cada decisión:

- qué mención originó la señal;
- qué plato se normalizó;
- qué sentimiento se predijo;
- qué evidencia soporta el candidato;
- qué calidad tiene la señal;
- cómo cambia respecto al ranking v1.

Por tanto, esta fase queda cerrada como una versión técnica sólida y defendible para presentación, análisis y evolución posterior.
