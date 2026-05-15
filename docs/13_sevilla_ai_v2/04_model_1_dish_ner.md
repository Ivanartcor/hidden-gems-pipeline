# 04. Modelo 1: detección de menciones de platos mediante NER

## 1. Objetivo del modelo

El **Modelo 1** de la fase Sevilla IA v2 tiene como objetivo detectar menciones de platos dentro del texto de las reseñas. Esta tarea es necesaria porque el sistema Hidden Gems no busca recomendar restaurantes completos, sino identificar **qué platos concretos destacan en cada local y barrio**.

En el ranking piloto v1, una parte importante de la detección se apoyaba en reglas, catálogos y patrones híbridos. Esa aproximación era útil como primera versión, pero tenía varias limitaciones:

- podía perder menciones no previstas en el catálogo inicial;
- era sensible a variaciones lingüísticas;
- tenía dificultad para detectar menciones compuestas;
- podía confundir ingredientes, platos y fragmentos de frase;
- dependía demasiado de coincidencias léxicas.

Por eso, en la fase v2 se entrenó un modelo NER específico para detectar menciones gastronómicas en reseñas de Sevilla.

---

## 2. Tipo de problema

La tarea se plantea como **token classification** con esquema BIO.

Ejemplo conceptual:

```text
Texto:    Las croquetas de cola de toro estaban espectaculares.
Etiquetas: O   B-DISH     I-DISH I-DISH I-DISH O       O
```

El modelo debe aprender a detectar spans de texto que correspondan a platos o preparaciones gastronómicas.

La salida esperada no es todavía un `dish_id`, sino una mención textual:

```text
croquetas de cola de toro
```

La normalización hacia el catálogo se realiza después mediante el Modelo 3.

---

## 3. Modelo base

Para el entrenamiento se utilizó un modelo tipo BERT en español:

```text
dccuchile/bert-base-spanish-wwm-cased
```

Este modelo se conoce habitualmente como **BETO** y está entrenado para español. Se eligió por las siguientes razones:

- buen rendimiento general en tareas NLP en español;
- tamaño asumible para entrenamiento en Kaggle;
- compatibilidad directa con `transformers`;
- buena capacidad para entender contexto local de frases;
- adecuado para tareas de clasificación por token.

La cabeza final del modelo se sustituyó por una capa de clasificación de tokens adaptada a las etiquetas BIO del problema.

---

## 4. Dataset de entrenamiento

El entrenamiento se realizó con un dataset extendido de menciones de platos, construido a partir de:

1. menciones detectadas por el sistema híbrido inicial;
2. ejemplos manuales añadidos;
3. ejemplos negativos;
4. menciones compuestas;
5. variaciones reales de reseñas;
6. casos diseñados para reducir falsos positivos.

El objetivo del dataset extendido fue que el modelo no aprendiera únicamente platos evidentes, sino también estructuras más variadas:

```text
croquetas de jamón
croquetas de cola de toro
ensaladilla de gambas
solomillo al whisky
tarta de queso
patatas bravas
rabo de toro
```

También se añadieron ejemplos donde no debía detectarse ningún plato, para que el modelo no etiquetara cualquier alimento aislado o fragmento ambiguo.

---

## 5. Estrategia de entrenamiento

El entrenamiento se realizó en Kaggle con GPU, siguiendo una estructura similar al resto de modelos de la fase IA v2.

Elementos principales:

| Elemento | Valor |
|---|---|
| Modelo base | `dccuchile/bert-base-spanish-wwm-cased` |
| Tipo de tarea | Token classification |
| Esquema | BIO |
| Framework | Hugging Face Transformers |
| Entorno | Kaggle Notebook con GPU |
| Métrica principal | F1 de entidad |
| Salida | Spans detectados de tipo plato |

Durante el entrenamiento se dio más importancia a la calidad de detección de entidades completas que a la precisión token a token, ya que para el pipeline downstream importa recuperar correctamente la mención completa del plato.

---

## 6. Resultados del entrenamiento

Los resultados del modelo fueron especialmente fuertes en los subconjuntos manuales.

Resumen aproximado de rendimiento observado en test:

| Subconjunto | Precision | Recall | F1 | Interpretación |
|---|---:|---:|---:|---|
| `manual_gold` | 0,9935 | 0,9935 | 0,9935 | Rendimiento muy alto sobre etiquetas manuales. |
| `weak_hybrid` | 0,7166 | 0,7426 | 0,7293 | Rendimiento aceptable sobre etiquetas débiles y más ruidosas. |

La diferencia entre `manual_gold` y `weak_hybrid` era esperable. Las etiquetas manuales son más limpias, mientras que las etiquetas débiles pueden contener ruido, menciones discutibles o spans imperfectos generados por reglas.

Conclusión del entrenamiento:

```text
El modelo NER es válido como detector de menciones de platos, especialmente combinado con el sistema híbrido existente.
```

No se decidió sustituir completamente el sistema híbrido por el modelo, sino combinarlos para aprovechar las fortalezas de ambos.

---

## 7. Uso dentro del pipeline v2

El modelo NER se aplica después de la extracción híbrida inicial. La lógica no es:

```text
NER sustituye a reglas
```

sino:

```text
reglas + catálogo + NER → capa unificada de menciones candidatas
```

Flujo simplificado:

```text
Reseñas Sevilla
→ extracción híbrida inicial
→ inferencia NER
→ limpieza de spans NER
→ combinación Hybrid + NER
→ candidatos de menciones v2
```

Esta combinación permite clasificar las menciones en tres estrategias:

| Estrategia | Significado |
|---|---|
| `hybrid_and_ner` | La mención aparece tanto en el sistema híbrido como en NER. Es la señal más fiable. |
| `hybrid_only` | La mención solo aparece en el sistema híbrido. Se mantiene por continuidad con v1. |
| `ner_only` | La mención solo aparece en NER. Se incorpora como señal experimental. |

---

## 8. Scripts relacionados

Los scripts asociados a este modelo dentro del repositorio son:

```text
scripts/run_sevilla_dish_ner_model_v1_2.py
scripts/clean_sevilla_dish_ner_model_output_v1_2.py
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
```

El flujo esperado es:

```text
1. Ejecutar inferencia NER sobre reseñas.
2. Limpiar la salida del modelo.
3. Combinar menciones NER con menciones híbridas.
```

---

## 9. Artefactos generados

Los artefactos principales derivados del uso del modelo NER se almacenan en:

```text
data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
```

Ejemplo de salida usada por fases posteriores:

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
└── sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl
```

Esta salida es la entrada directa del modelo de normalización / entity linking.

---

## 10. Limitaciones

Aunque el modelo NER mejora la detección de menciones, tiene limitaciones:

- puede detectar fragmentos incompletos;
- puede detectar ingredientes que no deberían ser platos finales;
- puede generar menciones `ner_only` con menor confianza;
- depende de la calidad del dataset de anotación;
- no asigna por sí solo un `dish_id`;
- no determina sentimiento;
- no decide si una mención es suficiente para ranking.

Por este motivo, sus salidas se tratan como **candidatos**, no como hechos finales.

---

## 11. Decisión de diseño

La decisión final fue usar el NER como una mejora incremental y trazable:

```text
NER v1.2 → mejora la cobertura de menciones
Sistema híbrido → aporta precisión y continuidad con v1
Hybrid + NER v2 → capa combinada para normalización
```

Esta decisión permite mejorar el pipeline sin perder trazabilidad ni romper la lógica anterior del ranking piloto.
