# 07. Capa Hybrid + NER candidates v2

## 1. Objetivo de la capa

La capa **Hybrid + NER candidates v2** combina dos fuentes de detección de menciones de platos:

1. el sistema híbrido previo basado en reglas, catálogo y señales léxicas;
2. el modelo NER entrenado en la fase IA v2.

El objetivo no es elegir una única fuente, sino construir una capa unificada de menciones candidatas que aproveche las ventajas de ambas.

Esta capa es la entrada directa del modelo de normalización / entity linking.

---

## 2. Por qué combinar híbrido y NER

El sistema híbrido y el modelo NER tienen comportamientos diferentes.

| Fuente | Fortalezas | Riesgos |
|---|---|---|
| Sistema híbrido | Alta trazabilidad, continuidad con v1, buen control por catálogo. | Menor flexibilidad ante expresiones nuevas. |
| Modelo NER | Mejor cobertura lingüística, detecta variantes no previstas. | Puede detectar fragmentos, ingredientes o spans dudosos. |

La combinación permite:

- conservar lo que ya funcionaba en v1;
- añadir nuevas menciones detectadas por IA;
- identificar menciones con consenso fuerte;
- marcar menciones experimentales para revisión;
- mejorar cobertura sin perder trazabilidad.

---

## 3. Entradas de la capa

La capa toma como entrada dos conjuntos de menciones:

```text
Menciones híbridas v1
Menciones detectadas por NER v1.2 cleaned
```

Ejemplo de ruta del NER limpio:

```text
data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/
└── sevilla_dish_mentions_ner_model_v1_2.jsonl
```

La fuente híbrida procede de los artefactos previos de IA Sevilla piloto.

---

## 4. Matching entre menciones

Para combinar ambas fuentes se realiza un matching entre menciones por reseña y texto normalizado.

Criterios principales:

```text
review_id
selected_mention_norm
posición o solapamiento textual cuando está disponible
normalización léxica de la mención
```

El objetivo es detectar cuándo una mención del sistema híbrido y una mención del NER representan el mismo plato en la misma reseña.

---

## 5. Estrategias resultantes

Cada mención final queda clasificada con una estrategia:

| Estrategia | Significado | Uso posterior |
|---|---|---|
| `hybrid_and_ner` | La mención fue detectada por ambas fuentes. | Máxima confianza. |
| `hybrid_only` | La mención solo fue detectada por el sistema híbrido. | Se mantiene por continuidad y precisión de reglas. |
| `ner_only` | La mención solo fue detectada por NER. | Señal experimental, requiere más cautela. |

Esta estrategia se conserva en las fases posteriores y puede afectar a pesos de calidad, revisión y ranking.

---

## 6. Resultados de construcción

La ejecución de la capa produjo:

| Métrica | Valor |
|---|---:|
| Menciones híbridas | 2.979 |
| Menciones NER | 2.964 |
| Matches híbrido-NER | 2.735 |
| Filas finales candidatas | 2.965 |
| Reviews con candidatos | 1.626 |
| Locales con candidatos | 786 |
| Duplicados eliminados | 243 |

Distribución por estrategia:

| Estrategia | Filas |
|---|---:|
| `hybrid_and_ner` | 2.520 |
| `hybrid_only` | 223 |
| `ner_only` | 222 |

La mayoría de menciones quedan respaldadas por ambas fuentes, lo cual es una buena señal de estabilidad.

---

## 7. Dedupe de menciones

Después de combinar las fuentes, se eliminan duplicados por:

```text
review_id + selected_mention_norm_v2
```

Esto evita que una misma mención aparezca dos veces por haber sido detectada por ambos métodos.

La eliminación de duplicados es necesaria porque la capa posterior de normalización espera una mención candidata por unidad textual relevante.

---

## 8. Control de calidad

La capa genera indicadores de revisión para no tratar todas las menciones como equivalentes.

Resultados observados:

| Métrica | Valor |
|---|---:|
| Menciones compuestas | 482 |
| Necesitan revisión manual | 387 |
| Necesitan normalización de plato | 706 |
| Listas para sentimiento tras normalización potencial | 2.846 |
| Filas en cola de normalización | 814 |

La cola de normalización se prioriza para facilitar revisión y mejora incremental.

Prioridades observadas:

| Prioridad | Filas |
|---|---:|
| `high` | 475 |
| `medium` | 120 |
| `low` | 2.370 |

---

## 9. Principales menciones detectadas

Entre las menciones más frecuentes aparecen platos coherentes con el dominio gastronómico sevillano:

| Mención | Frecuencia aproximada |
|---|---:|
| croquetas | 193 |
| ensaladilla | 187 |
| carrillada | 101 |
| solomillo | 99 |
| atún | 91 |
| montaditos | 75 |
| gambas | 71 |
| tarta de queso | 61 |
| churros | 60 |
| bacalao | 60 |
| torrija | 58 |
| salmorejo | 56 |
| solomillo al whisky | 54 |

Esto confirma que la capa sigue centrada en menciones gastronómicas útiles para Hidden Gems.

---

## 10. Script asociado

El script principal es:

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
```

En algunas ejecuciones se usó una variante parcheada para resolver problemas de serialización JSON con UUID:

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2_uuid_safe.py
```

El problema corregido fue que algunos objetos `UUID`, `Timestamp` o valores especiales no eran serializables directamente a JSON.

---

## 11. Salidas generadas

La salida principal se guarda en:

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
```

Archivos esperados:

```text
sevilla_dish_mentions_hybrid_ner_candidates_v2.csv
sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl
sevilla_dish_mentions_hybrid_ner_matches_v2.csv
sevilla_dish_mentions_hybrid_ner_summary_v2.json
normalization_queue_v2.csv
recommended_next_steps.md
```

La salida usada por la normalización es:

```text
sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl
```

---

## 12. Papel dentro del flujo IA v2

La capa Hybrid + NER candidates v2 ocupa esta posición:

```text
Reseñas Sevilla
→ extracción híbrida inicial
→ Modelo NER
→ Hybrid + NER candidates v2
→ Normalización / entity linking
→ Sentimiento ABSA
→ Señales place-dish
→ Ranking v2
```

Es una capa de transición entre detección textual y normalización semántica.

---

## 13. Interpretación de confianza

La estrategia de detección se utiliza como señal de calidad:

```text
hybrid_and_ner > hybrid_only > ner_only
```

Interpretación:

- `hybrid_and_ner`: alta confianza porque dos métodos independientes coinciden.
- `hybrid_only`: confianza razonable por continuidad con v1.
- `ner_only`: cobertura adicional, pero debe tratarse como experimental.

En ranking, las menciones `ner_only` pueden recibir menor peso o marcarse para revisión.

---

## 14. Limitaciones

Limitaciones principales:

- las menciones `ner_only` pueden contener más ruido;
- pueden quedar fragmentos incompletos;
- algunas menciones compuestas requieren normalización cuidadosa;
- no todas las menciones tienen candidato de catálogo claro;
- esta capa todavía no conoce sentimiento ni calidad final;
- la frecuencia de menciones no equivale por sí sola a calidad gastronómica.

---

## 15. Decisión final

La capa se considera válida como:

```text
sevilla_hybrid_ner_mentions_v2
```

pero no como capa final del ranking.

Su función es producir candidatos de mención para fases posteriores:

```text
Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
```

Esta decisión permite mejorar cobertura sin perder control, ya que las fases posteriores siguen filtrando, normalizando y ponderando la evidencia.
