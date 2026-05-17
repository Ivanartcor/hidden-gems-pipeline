# 07 - Ranking Hidden Gems v1

## 1. Objetivo del módulo

El objetivo de este módulo es transformar las señales agregadas por negocio y plato en un **ranking final de candidatos Hidden Gems**.

Hasta esta fase, el sistema ya dispone de:

- menciones de platos detectadas automáticamente;
- platos normalizados;
- sentimiento asociado a cada mención;
- señales agregadas por plato global;
- señales agregadas por negocio + plato;
- scoring preliminar conservador.

El ranking v1 toma esa información y calcula un score final explicable:

```text
business_id + dish_id
→ sentimiento local
→ evidencia
→ confianza
→ balance positivo/negativo
→ rareza / hiddenness
→ penalizaciones
→ hidden_gem_score_v1
```

El resultado es una lista priorizada de combinaciones **negocio + plato** que podrían considerarse candidatos destacados.

---

## Alcance de este documento

Este archivo documenta el **ranking Hidden Gems v1 basado en Yelp**.

Debe conservarse porque contiene la lógica de scoring, los componentes, las penalizaciones, los criterios de selección y la explicación del ranking inicial. Aunque el repositorio evolucione hacia Sevilla, barrios y salidas territoriales, este documento sigue siendo la referencia técnica de la fórmula v1.

Cuando se hable de ciudad/estado, debe entenderse como dimensión disponible en el prototipo Yelp. En la evolución posterior de Hidden Gems, esa dimensión se sustituye o complementa por:

```text
local + plato + barrio + distrito
```

---

## 2. Papel dentro del flujo de IA

El ranking es el último paso de la cadena IA actual:

```text
reviews gastronómicas
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

Este módulo no entrena un modelo. Aplica una función de ranking explicable y conservadora sobre los candidatos generados por la agregación.

---

## 3. Notebook implicado

| Notebook | Función |
|---|---|
| `11_hidden_gems_ranking_v1.ipynb` | Calcula el ranking final Hidden Gems v1 a partir de los candidatos negocio-plato y señales globales. |

---

## 4. Entradas del módulo

El notebook usa principalmente dos archivos procedentes del módulo 10.

### 4.1. Candidatos negocio-plato

```text
dish_business_ranking_candidates_v1.csv
```

Contiene los pares `business_id + dish_id_v2` con señales agregadas y scoring preliminar.

Incluye campos como:

- `business_id`;
- `business_name`;
- `city`;
- `state`;
- `dish_id_v2`;
- `canonical_dish_name_v2`;
- `mention_count`;
- `review_count`;
- `positive_ratio`;
- `negative_ratio`;
- `bayesian_sentiment_score`;
- `total_signal_weight`;
- `business_dish_evidence_tier`;
- `preliminary_ranking_score_v1`;
- `preliminary_candidate_tier_v1`;
- `is_ranking_ready_v1`;
- `is_hard_noise_dish_name`;
- `is_possible_beverage`.

### 4.2. Señales globales por plato

```text
dish_global_ranking_signals_v1.csv
```

Aporta contexto global del plato:

- menciones globales;
- reviews globales;
- negocios donde aparece;
- sentimiento global;
- score global;
- evidencia global.

Estas señales ayudan a calcular la parte de **hiddenness** y diferenciación local.

### 4.3. Resumen de scoring preliminar

```text
dish_signal_scoring_summary_v1.json
```

Se utiliza como referencia documental y de validación.

---

## 5. Estado de entrada

El input del ranking v1 tiene esta estructura:

| Métrica | Valor |
|---|---:|
| Pares negocio-plato totales | 31.036 |
| Candidatos `ranking_ready_v1` | 3.841 |
| No listos para ranking | 27.195 |
| `strong_candidate` | 645 |
| `promising_candidate` | 1.021 |
| `weak_candidate` | 1.223 |
| `not_ready` | 28.147 |
| Pares con evidencia `strong` | 996 |
| Pares con evidencia `solid` | 1.406 |
| Pares con evidencia `emerging` | 1.440 |
| Pares con evidencia `weak` | 27.194 |
| Pares ruidosos detectados | 806 |
| Posibles bebidas detectadas | 359 |
| Score preliminar máximo | 88,81 |

---

## 6. Preparación del dataframe de ranking

Antes de calcular el score final se realiza una preparación básica:

1. normalización de campos de texto;
2. conversión de columnas booleanas;
3. conversión de columnas numéricas;
4. parseo de flags de calidad;
5. unión con contexto global del plato;
6. validación de duplicados `business_id + dish_id_v2`.

El dataframe final de entrada mantiene los 31.036 pares negocio-plato y añade columnas globales como:

- `global_dish_mention_count`;
- `global_dish_review_count`;
- `global_dish_business_count`;
- `global_dish_positive_ratio`;
- `global_dish_negative_ratio`;
- `global_dish_confidence_weighted_sentiment`;
- `global_evidence_tier`;
- `global_ranking_signal_score_v1`.

---

## 7. Componentes del `hidden_gem_score_v1`

El score final combina varios componentes. Cada uno se normaliza aproximadamente a `[0, 1]`.

### 7.1. Componente de sentimiento local

Representa cómo se habla del plato dentro de un negocio concreto.

Se basa en:

```text
bayesian_sentiment_score
```

La transformación conceptual es:

```text
local_sentiment_component = (bayesian_sentiment_score + 1) / 2
```

Esto convierte el rango `[-1, 1]` en `[0, 1]`.

---

### 7.2. Componente de evidencia

Mide cuánta información respalda el candidato.

Combina:

- número de reviews;
- número de menciones.

Conceptualmente:

```text
evidence_component =
    0.65 × review_evidence_component
  + 0.35 × mention_evidence_component
```

Se da más peso a las reviews únicas que a las menciones, porque varias menciones pueden proceder de la misma review.

---

### 7.3. Componente de confianza

Mide la calidad de la señal agregada.

Combina:

- `avg_signal_weight`;
- `total_signal_weight`.

Conceptualmente:

```text
confidence_component =
    0.60 × signal_confidence_component
  + 0.40 × total_signal_component
```

Este componente favorece candidatos con señales fiables y suficientes.

---

### 7.4. Componente de balance positivo/negativo

Mide si el plato tiene más evidencia positiva que negativa:

```text
positive_balance_raw = positive_ratio - negative_ratio
```

Después se transforma a `[0, 1]`:

```text
positive_balance_component = (positive_balance_raw + 1) / 2
```

Un candidato con muchas menciones negativas queda penalizado.

---

### 7.5. Componente de rareza / hiddenness

La idea de Hidden Gems no es recomendar únicamente lo más popular, sino detectar platos que destacan de forma local.

El componente de hiddenness combina dos ideas:

1. **Rareza global**: platos que aparecen en menos negocios tienen más rareza.
2. **Outperformance local**: platos que funcionan mejor en un negocio concreto que en su señal global reciben más puntuación.

Conceptualmente:

```text
hiddenness_component =
    0.45 × rarity_component
  + 0.55 × local_outperformance_component
```

Esto evita que el ranking sea solo una lista de platos globalmente populares.

---

### 7.6. Componente preliminar

Se incorpora una pequeña parte del score preliminar del módulo 10:

```text
preliminary_component = preliminary_ranking_score_v1 / 100
```

Su peso es reducido. Sirve como señal auxiliar, no como score dominante.

---

## 8. Fórmula base del ranking

La fórmula conceptual del score base es:

```text
hidden_gem_score_base_v1 = 100 × (
    0.30 × local_sentiment_component
  + 0.20 × evidence_component
  + 0.15 × confidence_component
  + 0.13 × positive_balance_component
  + 0.15 × hiddenness_component
  + 0.07 × preliminary_component
)
```

Esta fórmula prioriza:

1. sentimiento local;
2. evidencia;
3. confianza;
4. balance positivo;
5. hiddenness;
6. señal preliminar.

---

## 9. Penalizaciones aplicadas

Después de calcular el score base se aplican factores de penalización.

### 9.1. Factor por evidence tier

| Tier | Factor |
|---|---:|
| `strong` | 1,00 |
| `solid` | 0,96 |
| `emerging` | 0,90 |
| `weak` | 0,00 |

Los pares `weak` no deberían entrar en ranking final.

### 9.2. Factor por candidate tier preliminar

| Tier | Factor |
|---|---:|
| `strong_candidate` | 1,00 |
| `promising_candidate` | 0,97 |
| `weak_candidate` | 0,92 |
| `not_ready` | 0,00 |

### 9.3. Penalización por negatividad

El ratio negativo penaliza el score final:

```text
negative_penalty_factor_final = 1 - negative_ratio × 1.70
```

Con límite mínimo de 0,45.

### 9.4. Penalización por bebida

Los posibles términos de bebida reciben penalización ligera:

```text
beverage_penalty_factor_final = 0.88
```

La razón es que Hidden Gems se centra principalmente en platos.

### 9.5. Penalización por ruido

Los nombres claramente ruidosos se eliminan del ranking:

```text
noise_penalty_factor_final = 0
```

### 9.6. Penalización por baja evidencia

Si el candidato no alcanza un mínimo de reviews, queda fuera:

```text
low_evidence_penalty_factor_final = 0
```

---

## 10. Score final

El score final se calcula como:

```text
hidden_gem_score_v1 =
    hidden_gem_score_base_v1
  × evidence_tier_factor
  × candidate_tier_factor
  × negative_penalty_factor_final
  × beverage_penalty_factor_final
  × noise_penalty_factor_final
  × low_evidence_penalty_factor_final
```

Después se acota a `[0, 100]`.

---

## 11. Selección de candidatos

Un par negocio-plato se considera candidato Hidden Gem si:

```text
is_base_rankable = true
hidden_gem_score_v1 >= 55
```

Esta condición garantiza que el candidato ya había superado filtros de ranking del módulo 10 y que el score final tiene un valor mínimo.

---

## 12. Tiers finales del ranking

Los candidatos seleccionados se clasifican en cuatro tiers:

| Tier | Criterio conceptual |
|---|---|
| `top_hidden_gem` | Candidato excelente, score muy alto, evidencia sólida/fuerte y baja negatividad. |
| `strong_hidden_gem` | Candidato fuerte, con buen score y evidencia suficiente. |
| `promising_hidden_gem` | Candidato prometedor, útil para exploración. |
| `exploratory_hidden_gem` | Candidato válido pero más exploratorio. |
| `not_selected` | No seleccionado en la versión final. |

---

## 13. Resultados finales

El ranking v1 produce los siguientes resultados:

| Métrica | Valor |
|---|---:|
| Pares totales evaluados | 31.036 |
| Candidatos base rankable | 3.841 |
| Candidatos Hidden Gems seleccionados | 622 |
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 50 |
| `promising_hidden_gem` | 182 |
| `exploratory_hidden_gem` | 388 |
| `not_selected` | 30.414 |
| Score máximo | 82,93 |
| Score medio de seleccionados | 66,87 |
| Score mediano de seleccionados | 65,74 |

---

## 14. Top candidatos del ranking v1

Los primeros candidatos del ranking final son:

| Rank | Tier | Negocio | Ciudad | Plato | Menciones | Reviews | Score |
|---:|---|---|---|---|---:|---:|---:|
| 1 | `top_hidden_gem` | Sushi Ushi | Valrico | sushi | 53 | 28 | 82,93 |
| 2 | `top_hidden_gem` | Taqueria Cuernavaca | Santa Barbara | tacos | 73 | 45 | 82,04 |
| 3 | `strong_hidden_gem` | Blues City Deli | Saint Louis | sandwich | 108 | 87 | 81,98 |
| 4 | `strong_hidden_gem` | Surrey's Café & Juice Bar | New Orleans | shrimp | 159 | 120 | 81,90 |
| 5 | `strong_hidden_gem` | Three Muses | New Orleans | steak | 32 | 26 | 81,74 |
| 6 | `strong_hidden_gem` | HipCityVeg - University City | Philadelphia | fries | 37 | 31 | 81,32 |
| 7 | `strong_hidden_gem` | Kei Sushi | Reno | sushi | 64 | 31 | 81,24 |
| 8 | `strong_hidden_gem` | The Garden Brunch Cafe | Nashville | pancake | 75 | 52 | 80,03 |
| 9 | `strong_hidden_gem` | SPOT Gourmet Burgers | Philadelphia | burger | 105 | 42 | 79,91 |
| 10 | `strong_hidden_gem` | Muriel's Jackson Square | New Orleans | shrimp | 99 | 73 | 79,84 |

---

## 15. Explicabilidad del ranking

Cada candidato incluye una explicación textual generada a partir de las señales del ranking.

Ejemplo:

```text
sushi en Sushi Ushi obtiene un score 82.9/100;
basado en 53 menciones y 28 reviews;
con 71.7% menciones positivas y 0.0% negativas;
evidencia strong;
destaca por encima de la señal global del plato.
```

La explicación resume:

- plato;
- negocio;
- score;
- volumen de evidencia;
- ratio positivo y negativo;
- tier de evidencia;
- si destaca por encima de la señal global del plato;
- si tiene rareza o menor presencia global.

---

## 16. Rankings derivados

Además del ranking global, se generan rankings secundarios:

### 16.1. Ranking por ciudad

Archivo:

```text
hidden_gems_top_by_city_v1.csv
```

Permite consultar los mejores candidatos dentro de cada ciudad.

### 16.2. Ranking por estado

Archivo:

```text
hidden_gems_top_by_state_v1.csv
```

Permite comparar candidatos dentro del mismo estado.

Estos rankings son útiles en el prototipo Yelp, aunque en la versión final para Sevilla se sustituirán por rankings por barrio y distrito.

---

## 17. Artefactos generados

### 17.1. Ranking principal

| Archivo | Descripción |
|---|---|
| `hidden_gems_ranking_v1.csv` | Ranking completo con todos los pares negocio-plato evaluados. |
| `hidden_gems_selected_candidates_v1.csv` | Solo candidatos seleccionados como Hidden Gems. |
| `hidden_gems_top_candidates_v1.csv` | Top 100 candidatos globales. |
| `hidden_gems_ranking_summary_v1.json` | Resumen estructurado del ranking. |

### 17.2. Rankings derivados

| Archivo | Descripción |
|---|---|
| `hidden_gems_top_by_city_v1.csv` | Top candidatos por ciudad. |
| `hidden_gems_top_by_state_v1.csv` | Top candidatos por estado. |

### 17.3. Muestras de revisión

| Archivo | Descripción |
|---|---|
| `hidden_gems_sample_top_v1.csv` | Muestra de top hidden gems. |
| `hidden_gems_sample_strong_v1.csv` | Muestra de strong hidden gems. |
| `hidden_gems_sample_promising_v1.csv` | Muestra de promising hidden gems. |
| `hidden_gems_sample_exploratory_v1.csv` | Muestra de exploratory hidden gems. |
| `hidden_gems_sample_not_selected_high_score_v1.csv` | Candidatos con score alto no seleccionados. |

---

## 18. Interpretación correcta del ranking

Este ranking debe interpretarse como un **prototipo funcional de priorización**, no como un ranking gastronómico validado manualmente.

El sistema selecciona candidatos que cumplen condiciones de:

- buen sentimiento local;
- evidencia suficiente;
- baja negatividad;
- confianza razonable;
- score explicable;
- ausencia de ruido evidente.

Sin embargo, los candidatos todavía necesitan revisión humana y adaptación al contexto real de Sevilla.

---

## 19. Relación con la evolución Sevilla / IA v2

El ranking v1 trabaja con la estructura disponible en Yelp:

```text
plato + negocio + ciudad/estado
```

La evolución natural del proyecto consiste en proyectar esta lógica hacia el objetivo real de Hidden Gems:

```text
plato + local + barrio + distrito
```

Para ello, esta fórmula de ranking debe conectarse con:

- Google Places;
- OSM / Overpass;
- dataset oficial de barrios/distritos de Sevilla;
- geocodificación y asignación espacial;
- posible corpus de reseñas, snippets o textos disponibles en español;
- entidades persistentes de IA dentro del modelo de datos.

La lógica de scoring de este documento sigue siendo reutilizable, pero las dimensiones territoriales y las fuentes de entrada cambian en la capa posterior.

---

## 20. Limitaciones del ranking v1

Limitaciones actuales de la versión v1 documentada aquí:

- se basa en Yelp, no en datos reales de Sevilla;
- no incorpora barrios ni distritos dentro de este ranking v1;
- el sentimiento por mención es weak-supervised;
- la normalización de platos no está revisada manualmente;
- el ranking no ha sido validado por usuarios;
- los pesos del score son heurísticos;
- no existe todavía learning-to-rank en esta fase;
- algunos platos genéricos siguen apareciendo en posiciones altas;
- los resultados son candidatos, no recomendaciones definitivas.

Estas limitaciones deben interpretarse como límites del prototipo Yelp v1. La capa Sevilla / IA v2 puede reutilizar este diseño y resolver parte de la integración territorial sin borrar el valor técnico de este ranking.

---

## 21. Conclusión

El módulo `11_hidden_gems_ranking_v1.ipynb` valida la lógica central de Hidden Gems.

A partir de miles de reseñas y menciones, el sistema ha sido capaz de producir una lista priorizada, explicable y filtrada de candidatos negocio-plato.

Aunque todavía es un prototipo sobre Yelp, demuestra que la cadena IA completa es viable:

```text
texto no estructurado
→ platos detectados
→ platos normalizados
→ sentimiento por plato
→ señales agregadas
→ ranking explicable
```

La evolución posterior consiste en conectar esta lógica con datos reales de Sevilla, asignación geográfica y rankings por barrio/distrito, manteniendo la trazabilidad de la fórmula v1.
