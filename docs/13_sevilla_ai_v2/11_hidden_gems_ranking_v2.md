# 11. Ranking Hidden Gems Sevilla v2

## 1. Propósito del documento

Este documento describe la construcción del **ranking Hidden Gems Sevilla v2**, generado a partir de las señales `place_id + dish_id` calculadas en la fase IA v2.

El ranking v2 es el resultado principal de la fase de modelos entrenados.

Su objetivo es ordenar candidatos del tipo:

```text
local + plato
```

según su potencial como *hidden gem* gastronómico dentro de Sevilla.

---

## 2. Qué diferencia al ranking v2

El ranking v1 era un ranking piloto basado principalmente en señales híbridas y reglas.

El ranking v2 incorpora una cadena completa de IA:

```text
NER entrenado
+ normalización/entity linking con reranker
+ sentimiento ABSA por mención
+ agregación place-dish
+ scoring v2
```

Esto permite que el ranking v2 sea más rico y explicable.

---

## 3. Entrada del ranking

Archivo de entrada:

```text
data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/
└── sevilla_place_dish_signals_v2.jsonl
```

Granularidad:

```text
una fila por combinación place_id + dish_id
```

Cada fila contiene:

```text
- local;
- plato normalizado;
- distrito;
- barrio;
- número de menciones;
- número de reviews;
- ratio positivo;
- ratio negativo;
- sentimiento ABSA ponderado;
- confianza de modelos;
- evidencia;
- calidad agregada;
- motivos de revisión;
- elegibilidad para ranking.
```

---

## 4. Script principal

Script:

```text
scripts/build_sevilla_hidden_gems_ranking_v2.py
```

Este script:

```text
1. Lee las señales place-dish v2.
2. Calcula componentes normalizados de puntuación.
3. Aplica bonus y penalizaciones.
4. Genera hidden_gem_score_v2.
5. Asigna tiers.
6. Selecciona candidatos destacados.
7. Genera salidas globales, territoriales y por plato.
```

---

## 5. Salida del ranking

Carpeta de salida:

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2/
```

Archivos generados:

```text
sevilla_hidden_gems_ranking_v2.csv
sevilla_hidden_gems_ranking_v2.jsonl
sevilla_hidden_gems_selected_v2.csv
sevilla_hidden_gems_selected_v2.jsonl
sevilla_hidden_gems_top_global_v2.csv
sevilla_hidden_gems_top_by_district_v2.csv
sevilla_hidden_gems_top_by_neighborhood_v2.csv
sevilla_hidden_gems_top_by_dish_v2.csv
sevilla_hidden_gems_manual_review_v2.csv
sevilla_hidden_gems_tier_summary_v2.csv
sevilla_hidden_gems_district_summary_v2.csv
sevilla_hidden_gems_neighborhood_summary_v2.csv
sevilla_hidden_gems_dish_summary_v2.csv
sevilla_hidden_gems_ranking_v2_summary.json
recommended_next_steps.md
```

---

## 6. Fórmula conceptual de puntuación

El ranking calcula una puntuación `hidden_gem_score_v2` normalizada entre 0 y 100.

La fórmula conceptual es:

```text
hidden_gem_score_v2 =
    sentimiento ABSA ponderado
  + evidencia de menciones y reviews
  + calidad de normalización y sentimiento
  + consenso entre métodos de extracción
  + especificidad/rareza del plato
  + señal débil de rating
  - penalización por negatividad
  - penalización por baja evidencia
  - penalización por revisión manual
  - penalización por baja calidad
```

No es una fórmula puramente estadística ni un modelo cerrado. Es una función de scoring explicable construida sobre las señales generadas por los modelos.

---

## 7. Componentes positivos

El ranking premia:

```text
- alto weighted_sentiment_score_v2;
- ratio positivo alto;
- ratio negativo bajo;
- varias menciones;
- varias reviews distintas;
- evidence_tier solid o strong;
- aggregate_quality_tier high;
- confianza alta de ABSA;
- confianza alta de normalización;
- coincidencia hybrid_and_ner;
- platos algo más específicos;
- distribución territorial útil para Hidden Gems.
```

---

## 8. Penalizaciones

El ranking penaliza:

```text
- negative_ratio alto;
- pocas menciones o pocas reviews;
- evidence_tier weak;
- quality_tier low;
- señales con manual_review;
- menciones ner_only experimentales;
- fragmentos dudosos;
- baja confianza ABSA;
- baja confianza de normalización;
- candidatos demasiado inciertos.
```

Estas penalizaciones son importantes para evitar que una única mención positiva coloque un candidato débil demasiado arriba.

---

## 9. Tiers del ranking

El ranking clasifica los candidatos seleccionados en cuatro tiers:

| Tier | Interpretación |
|---|---|
| `top_hidden_gem` | Candidato muy destacado dentro del piloto. |
| `strong_hidden_gem` | Candidato fuerte, con buena señal. |
| `promising_hidden_gem` | Candidato prometedor, útil para exploración. |
| `exploratory_hidden_gem` | Candidato exploratorio, requiere cautela. |

También existen señales no seleccionadas para ranking final.

---

## 10. Resultados generales

Resultado del ranking v2:

```text
input_signals: 2.335
total_signals_scored: 2.335
selected_hidden_gem_candidates: 268
selected_places: 198
selected_dishes: 40
selected_neighborhoods: 67
selected_districts: 11
production_ready_count: 0
```

El resultado es amplio y cubre buena parte de Sevilla, pero se mantiene como experimental.

---

## 11. Distribución por tiers

Distribución de seleccionados:

```text
top_hidden_gem: 16
strong_hidden_gem: 77
promising_hidden_gem: 139
exploratory_hidden_gem: 36
```

Lectura:

```text
- Hay 16 candidatos especialmente destacados.
- El bloque strong crece mucho respecto a v1.
- La mayoría queda en promising, lo cual es razonable para un ranking experimental.
- Se mantiene un bloque exploratory para señales útiles pero menos robustas.
```

---

## 12. Resumen de puntuaciones

Puntuación de candidatos seleccionados:

```text
score medio: 80.583688
score mínimo: 66.1237
score máximo: 91.6554
mediana: 81.2994
```

Estos scores son comparables dentro de v2, pero no deben compararse directamente con los scores de v1 porque la fórmula cambió.

---

## 13. Evidencia y calidad de seleccionados

Distribución de evidencia en seleccionados:

```text
emerging: 215
solid: 48
strong: 5
```

Distribución de calidad agregada:

```text
medium: 199
high: 48
low: 21
```

Esto es clave para la interpretación: el ranking v2 es útil y más rico, pero la mayor parte de candidatos todavía tienen evidencia emergente.

---

## 14. Top inicial del ranking

Ejemplos destacados del top global:

```text
Chechi's Cocina Canadiense → hamburguesa
Cafetería Chocolateria Osto E Hijos → churros
Pizzería San Pablo → pizza
LA TENTACIÓN BURGUER → hamburguesa
Café Los Pilares Bar → churros
Il Ristorantino Dell'Avvocato Calle Cuna → pizza
Bar Talo → chicharrones
Bar Er' 080 → montadito
Cafetería El Buda → churros
EL DESPACHO → chicharrones
```

Estos resultados muestran que el ranking detecta combinaciones local-plato específicas, incluyendo zonas fuera del centro tradicional.

---

## 15. Interpretación del resultado

El ranking v2 debe interpretarse como:

```text
ranking experimental asistido por modelos
```

No debe presentarse como verdad definitiva ni producción cerrada.

La razón principal es que:

```text
- la mayoría de señales tienen evidencia emerging;
- no hay validación humana final del top;
- algunos platos son genéricos;
- las reseñas de Google tienen sesgo positivo;
- la cadena depende de modelos entrenados y reglas de agregación.
```

---

## 16. Checks de calidad

Los checks principales del script fueron correctos:

```text
has_ranking: true
has_selected_candidates: true
score_in_0_100: true
selected_have_place: true
selected_have_dish: true
selected_have_neighborhood: true
selected_have_district: true
selected_ranks_are_unique: true
all_selected_are_not_production_ready: true
```

El último check no es un error. Indica que los seleccionados no deben etiquetarse como producción.

---

## 17. Relación con el dashboard

El ranking v2 se exporta posteriormente a:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

El dashboard usa:

```text
ranking_detail.csv
selected_candidates.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
tier_summary.csv
evidence_summary.csv
quality_summary.csv
mention_examples.csv
comparison/
```

Esto permite explorar el ranking desde varias perspectivas:

```text
- global;
- por distrito;
- por barrio;
- por plato;
- por local;
- por evidencia;
- por calidad;
- por comparación v1/v2;
- por reseñas de soporte.
```

---

## 18. Comparación esperada con v1

El ranking v2 no sustituye al v1 sin análisis. Primero se compara con el baseline piloto.

La comparación posterior mostró:

```text
v1_selected_unique: 150
v2_selected_unique: 268
matched_candidates: 119
v1_only_candidates: 31
v2_only_candidates: 149
v1_coverage_in_v2: 0.793333
jaccard_overlap: 0.397993
```

Esto indica que v2 conserva una parte importante de v1 y, además, amplía el espacio de descubrimiento.

---

## 19. Limitaciones

Limitaciones principales:

1. Los scores v2 no son equivalentes a los scores v1.
2. No hay candidatos marcados como producción.
3. Muchos seleccionados tienen evidencia `emerging`.
4. Algunos platos genéricos suben bastante.
5. El ranking depende de la cobertura del catálogo.
6. La calidad depende de NER, normalización y ABSA.
7. La fórmula de ranking requiere validación humana.

---

## 20. Próximas mejoras

Mejoras propuestas:

```text
- añadir penalización suave para platos demasiado genéricos;
- añadir bonus por platos locales/específicos;
- revisar top_hidden_gem manualmente;
- crear una versión production_candidate con umbrales más estrictos;
- ampliar datos de reseñas y fuentes;
- comparar con evaluación humana;
- ajustar pesos de scoring según feedback.
```

---

## 21. Conclusión

El ranking Hidden Gems Sevilla v2 constituye el principal resultado de la fase IA v2.

Aporta:

```text
- más candidatos que v1;
- más locales;
- más barrios;
- scoring más explicable;
- señales de sentimiento por plato;
- normalización con modelo;
- comparación con baseline;
- explotación directa en dashboard.
```

Su estado correcto es:

```text
Ranking IA v2 experimental basado en modelos entrenados
```

y debe usarse como base para análisis, presentación, validación y futuras iteraciones.
