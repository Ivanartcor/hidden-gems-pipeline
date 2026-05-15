# 12. Comparación ranking v1 vs ranking IA v2

## 1. Objetivo del documento

Este documento describe la comparación entre el ranking piloto inicial de Hidden Gems Sevilla (**v1**) y el nuevo ranking asistido por modelos (**IA v2**).

El objetivo no es únicamente comprobar si el ranking v2 obtiene puntuaciones más altas, sino entender si el nuevo flujo:

- conserva una parte razonable del ranking piloto v1;
- amplía la cobertura de locales, barrios y platos;
- introduce candidatos nuevos con sentido gastronómico;
- mejora la calidad de las señales utilizadas para puntuar;
- permite justificar mejor cada resultado mostrado en el dashboard;
- sigue manteniendo las limitaciones necesarias para no presentarlo como producción.

La comparación sirve como validación final de la fase IA v2.

---

## 2. Entradas utilizadas

La comparación se realiza a partir de dos artefactos principales.

### Ranking v1

El ranking v1 procede del export inicial utilizado por el dashboard Sevilla piloto:

```text
data/artifacts/ai/sevilla/dashboard/candidates_detail.csv
```

Este ranking representa el baseline previo a los modelos entrenados. Se basa principalmente en reglas, señales híbridas iniciales, menciones detectadas sin NER entrenado y scoring piloto.

### Ranking IA v2

El ranking v2 procede del nuevo flujo completo de IA:

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl
```

Este ranking se construye a partir de:

```text
NER v1.2
→ Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
→ Hidden Gems ranking v2
```

---

## 3. Script de comparación

El script utilizado para generar la comparación es:

```text
scripts/compare_sevilla_ranking_v1_vs_v2.py
```

Comando recomendado:

```powershell
python -m scripts.compare_sevilla_ranking_v1_vs_v2 `
  --v1-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --v2-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --output-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --strict
```

---

## 4. Artefactos generados

La comparación genera la carpeta:

```text
data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison/
```

con los siguientes archivos:

| Archivo | Descripción |
|---|---|
| `sevilla_ranking_v1_vs_v2_summary.json` | Resumen global de la comparación. |
| `ranking_overlap.csv` | Candidatos presentes tanto en v1 como en v2. |
| `v2_only_candidates.csv` | Candidatos nuevos que aparecen solo en v2. |
| `v1_only_candidates.csv` | Candidatos de v1 que no aparecen en v2. |
| `score_shift_comparison.csv` | Cambios de score/rank para candidatos coincidentes. |
| `top_district_shift.csv` | Cambios agregados por distrito. |
| `top_neighborhood_shift.csv` | Cambios agregados por barrio. |
| `top_dish_shift.csv` | Cambios agregados por plato. |
| `tier_shift_summary.csv` | Cambios de tier entre v1 y v2. |
| `recommended_next_steps.md` | Recomendaciones generadas a partir de la comparación. |

---

## 5. Método de emparejamiento

La comparación utiliza como clave lógica el par:

```text
place + dish
```

En la práctica, se construye una clave estable a partir de:

```text
place_id + dish_id/dish_name
```

Esto permite comparar correctamente candidatos del tipo:

```text
Bar X → croquetas
Bar X → solomillo al whisky
Bar Y → croquetas
```

Aunque compartan plato, son señales distintas porque pertenecen a locales distintos.

---

## 6. Resultados principales

La comparación produjo los siguientes resultados:

| Métrica | Valor |
|---|---:|
| Candidatos seleccionados v1 | 150 |
| Candidatos seleccionados v2 | 268 |
| Candidatos coincidentes | 119 |
| Candidatos solo v1 | 31 |
| Candidatos solo v2 | 149 |
| Unión total de candidatos | 299 |

La lectura principal es que el ranking v2 no sustituye de forma arbitraria al v1. Conserva una parte importante del ranking anterior y, al mismo tiempo, amplía de manera clara el espacio de candidatos.

---

## 7. Solapamiento entre rankings

Los indicadores de solapamiento fueron:

| Indicador | Valor |
|---|---:|
| Jaccard overlap | 0.397993 |
| Cobertura de v1 dentro de v2 | 0.793333 |
| Cobertura de v2 dentro de v1 | 0.444030 |

### Interpretación

La cobertura de v1 dentro de v2 es alta:

```text
119 / 150 = 79,3 %
```

Esto significa que v2 mantiene casi el 80 % de los candidatos seleccionados por el ranking piloto.

La cobertura de v2 dentro de v1 es menor porque v2 selecciona muchos más candidatos. Esto no es negativo: indica que el nuevo ranking amplía el espacio de descubrimiento.

En conjunto:

```text
v2 conserva gran parte de v1
+
v2 añade nuevos candidatos
=
expansión razonable del ranking, no reemplazo aleatorio
```

---

## 8. Mejora de diversidad

Uno de los resultados más importantes de la comparación es la mejora de diversidad.

| Dimensión | v1 | v2 | Diferencia |
|---|---:|---:|---:|
| Locales seleccionados | 122 | 198 | +76 |
| Platos seleccionados | 38 | 40 | +2 |
| Barrios seleccionados | 55 | 67 | +12 |
| Distritos seleccionados | 11 | 11 | 0 |

La mejora principal se observa en locales y barrios.

Esto es especialmente relevante para Hidden Gems, porque el objetivo del proyecto no es crear un ranking centrado solo en los locales más populares, sino descubrir platos destacados distribuidos territorialmente.

---

## 9. Cambios de tiers

La distribución por tiers cambió de forma notable.

### Ranking v1

| Tier | Candidatos |
|---|---:|
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 7 |
| `promising_hidden_gem` | 72 |
| `exploratory_hidden_gem` | 69 |

### Ranking IA v2

| Tier | Candidatos |
|---|---:|
| `top_hidden_gem` | 16 |
| `strong_hidden_gem` | 77 |
| `promising_hidden_gem` | 139 |
| `exploratory_hidden_gem` | 36 |

El ranking v2 es más ambicioso porque incorpora señales más ricas:

- sentimiento ABSA específico por mención;
- normalización entrenada hacia `dish_id`;
- evidencia agregada por local-plato;
- calidad de señal;
- penalizaciones por baja confianza o revisión manual.

Aun así, los scores de v1 y v2 no deben interpretarse como escalas equivalentes. El modelo de scoring ha cambiado, por lo que la comparación debe centrarse más en cobertura, diversidad, cambios de tier y coherencia de resultados.

---

## 10. Cambios de puntuación

Para los candidatos coincidentes, la diferencia media de score fue positiva:

```text
score_delta_v2_minus_v1 mean: 18.790768
```

Esto indica que muchos candidatos que ya aparecían en v1 reciben mayor confianza en v2 gracias a la nueva cadena de IA.

Ejemplos de mejoras destacadas:

| Candidato | Cambio observado |
|---|---|
| `Chichacol montaitos → chicharrones` | Sube de exploratory a strong. |
| `Cafetería Bar El Pilar → churros` | Sube de exploratory a strong. |
| `Chechi's Cocina Canadiense → hamburguesa` | Sube de exploratory a top. |
| `Cafetería Chocolateria Osto E Hijos → churros` | Sube de exploratory a top. |
| `ÁVILA BAR → arepa` | Sube de exploratory a top. |

Estos cambios se explican principalmente por la existencia de menciones positivas claras, varias reviews asociadas y mejor calidad agregada.

---

## 11. Candidatos nuevos de v2

El ranking v2 introduce 149 candidatos que no estaban seleccionados en v1.

Algunos ejemplos destacados son:

| Local | Plato | Lectura |
|---|---|---|
| LA TENTACIÓN BURGUER | hamburguesa | Señal fuerte, varias reviews, sentimiento positivo. |
| Café Los Pilares Bar | churros | Señal territorial interesante fuera del centro. |
| Bar Talo | chicharrones | Plato concreto con buena evidencia. |
| Islamorada Tapas Bar | tortilla de patatas | Señal local-plato específica. |
| Fuera de Carta Bermejales | patatas bravas | Candidato relevante por barrio. |
| Casa Juan Camisa – La Gamba | solomillo al whisky | Plato local reconocible. |
| Cariña VZ | arepa | Aporta diversidad gastronómica. |
| Bar DE ARACENA A LA MESA | presa ibérica | Plato específico y de alto interés. |

Estos candidatos refuerzan la utilidad del ranking v2 como sistema de descubrimiento.

---

## 12. Candidatos que desaparecen de v1

El ranking v1 conserva 31 candidatos que no aparecen en la selección v2.

Esto puede deberse a varias razones:

- el modelo ABSA no confirma con suficiente fuerza el sentimiento positivo;
- la normalización v2 enlaza la mención hacia otro plato más específico;
- la señal queda penalizada por baja evidencia o baja calidad;
- el candidato baja frente a otros con mejor evidencia;
- el ranking v2 selecciona más variedad pero usa criterios distintos.

Estos casos no deben interpretarse automáticamente como errores. Son candidatos útiles para revisión manual posterior.

---

## 13. Puntos a vigilar

Aunque el ranking v2 mejora la cobertura y la calidad, también introduce algunos riesgos.

### Platos genéricos arriba

Aparecen varios platos genéricos en posiciones altas:

```text
hamburguesa
pizza
churros
montadito
croqueta
```

No es necesariamente incorrecto, porque pueden ser verdaderos hidden gems, pero conviene explicar que el sistema detecta **platos destacados por evidencia textual**, no únicamente platos tradicionales sevillanos.

### Evidencia emergente

Muchos candidatos tienen evidencia `emerging`, lo que significa que son prometedores pero todavía no suficientemente robustos para producción.

### Escala de puntuación distinta

El score v2 no es comparable directamente con el score v1. Se debe comparar dentro de la misma versión.

---

## 14. Conclusión

La comparación valida el ranking IA v2 como una mejora relevante respecto al ranking piloto v1.

Conclusión técnica:

```text
El ranking v2 conserva casi el 80 % del ranking v1, amplía de forma significativa la cobertura de locales y barrios, introduce candidatos nuevos con señales interpretables y permite justificar mejor cada resultado gracias a la cadena de modelos entrenados.
```

Sin embargo, el ranking debe presentarse como:

```text
Ranking IA v2 experimental / model-assisted
```

y no como ranking final de producción.

---

## 15. Recomendación

Para la siguiente fase se recomienda:

1. Usar v2 como ranking principal en el dashboard experimental.
2. Mantener v1 como baseline comparativo.
3. Exponer siempre `evidence_tier` y `quality_tier`.
4. Añadir filtros para separar `top`, `strong`, `promising` y `exploratory`.
5. Revisar manualmente candidatos `v2_only` de alto score.
6. Considerar una penalización suave para platos demasiado genéricos en una futura v2.1.
