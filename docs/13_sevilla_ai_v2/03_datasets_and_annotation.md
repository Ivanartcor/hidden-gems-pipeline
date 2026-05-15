# 03. Datasets y anotación de la fase Sevilla IA v2

## 1. Objetivo de los datasets

La fase Sevilla IA v2 necesitaba datasets específicos para entrenar modelos orientados al dominio del proyecto. No bastaba con usar reseñas completas o puntuaciones generales, porque Hidden Gems trabaja con una granularidad más fina:

```text
local + plato + mención + contexto + sentimiento
```

Por ello se prepararon datasets de anotación para tres tareas:

1. **NER de platos**: detectar menciones textuales de platos.
2. **Normalización / entity linking**: enlazar menciones con platos canónicos del catálogo.
3. **Sentimiento por mención / ABSA**: clasificar el sentimiento hacia una mención concreta.

---

## 2. Enfoque general de anotación

Los datasets combinan varias fuentes de etiqueta:

| Tipo de etiqueta | Descripción | Uso |
|---|---|---|
| Manual / gold | Casos revisados o creados manualmente. | Mayor peso durante entrenamiento y evaluación. |
| Weak labels | Etiquetas generadas por reglas, heurísticas o pipeline previo. | Útiles para volumen, pero con menor confianza. |
| Datos aumentados | Casos añadidos manualmente para cubrir variantes y casos difíciles. | Mejoran robustez del modelo. |
| Negativos / controles | Textos sin plato o con menciones no válidas. | Ayudan a reducir falsos positivos. |

La idea no era eliminar los datos débiles, sino combinarlos de forma controlada con casos manuales para obtener datasets más amplios.

---

## 3. Formato principal: JSONL

Aunque algunos datasets también existen en CSV, el formato recomendado para entrenamiento es:

```text
.jsonl
```

Motivos:

- conserva mejor textos largos;
- evita problemas con comillas y separadores;
- permite guardar estructuras JSON internas;
- facilita leer fila a fila;
- reduce errores al trabajar con listas de candidatos o spans.

El CSV se mantiene como formato auxiliar para inspección visual.

---

## 4. Dataset 1: NER de menciones de platos

### 4.1. Objetivo

Entrenar un modelo que detecte menciones de platos dentro de reseñas gastronómicas.

Ejemplo:

```text
"Pedimos ensaladilla, croquetas de jamón y una torrija espectacular."
```

Menciones esperadas:

```text
ensaladilla
croquetas de jamón
torrija
```

---

### 4.2. Tipo de tarea

La tarea es de tipo:

```text
Token Classification
```

con etiquetas BIO:

```text
B-DISH
I-DISH
O
```

---

### 4.3. Contenido esperado

Cada fila del dataset debe contener, como mínimo:

- identificador de ejemplo;
- texto de reseña o fragmento;
- lista de tokens;
- etiquetas BIO;
- fuente de etiqueta;
- estado de anotación.

Ejemplo conceptual:

```json
{
  "text": "Las croquetas de jamón estaban espectaculares.",
  "tokens": ["Las", "croquetas", "de", "jamón", "estaban", "espectaculares"],
  "ner_tags": ["O", "B-DISH", "I-DISH", "I-DISH", "O", "O"],
  "label_source": "manual_gold"
}
```

---

### 4.4. Consideraciones

El dataset debe cubrir:

- platos simples: `croquetas`, `salmorejo`, `pizza`;
- platos compuestos: `croquetas de jamón`, `solomillo al whisky`;
- menciones múltiples en la misma frase;
- textos sin platos;
- variantes con mayúsculas, errores y acentos;
- menciones ambiguas o fragmentos.

---

## 5. Dataset 2: Normalización / entity linking

### 5.1. Objetivo

Entrenar un modelo capaz de decidir si una mención corresponde a un plato candidato del catálogo.

La tarea no consiste en clasificar directamente entre todos los platos existentes, sino en puntuar pares:

```text
mención + contexto + plato candidato → match / no_match
```

---

### 5.2. Motivo del enfoque reranker

Se eligió un enfoque de reranker porque el catálogo de platos puede crecer.

Un clasificador cerrado tendría este problema:

```text
nueva clase de plato → habría que adaptar la salida del modelo
```

En cambio, un reranker permite:

```text
nueva mención → generar candidatos del catálogo → puntuar cada candidato
```

Esto hace que el sistema sea más flexible.

---

### 5.3. Dataset extendido usado

Dataset principal:

```text
sevilla_dish_normalization_annotation_dataset_v1_extended.jsonl
```

Tamaño usado en el entrenamiento fuerte:

| Métrica | Valor |
|---|---:|
| Filas totales | 4.411 |
| Filas usables | 4.291 |

Distribución aproximada en splits:

| Split | Weak current dish | Manual existing dish | Manual new dish |
|---|---:|---:|---:|
| Train | 2.328 | 864 | 240 |
| Validation | 291 | 108 | 30 |
| Test | 292 | 108 | 30 |

---

### 5.4. Columnas relevantes

El dataset de normalización incluye columnas como:

| Columna | Descripción |
|---|---|
| `annotation_id` | Identificador de anotación. |
| `mention_text` | Texto de la mención. |
| `context_sentence` | Frase o contexto local. |
| `candidate_dish_options_json` | Lista de candidatos posibles. |
| `current_dish_id` | Plato asignado por la capa anterior. |
| `current_dish_name` | Nombre normalizado previo. |
| `manual_normalization_status` | Estado de revisión manual. |
| `manual_correct_dish_id` | Plato correcto si existe en catálogo. |
| `manual_correct_dish_name` | Nombre del plato correcto. |
| `manual_new_dish_name` | Nuevo plato sugerido si no existe. |
| `annotation_status` | Estado de anotación. |

---

### 5.5. Tipos de casos incluidos

El dataset cubre:

- mención ya correctamente normalizada;
- mención que debe cambiar a otro plato existente;
- mención que requiere plato nuevo;
- menciones demasiado genéricas;
- menciones ambiguas;
- falsos positivos o menciones que no deben enlazarse;
- variantes ortográficas y gastronómicas.

Ejemplos de casos difíciles:

```text
ensaladilla de gambas ≠ gambas
croquetas de rabo de toro ≠ rabo de toro
tarta de queso ≠ cheesecake si se quiere conservar variante específica
hamburguesa ≠ hamburguesas con patatas
```

---

## 6. Dataset 3: Sentimiento por mención / ABSA

### 6.1. Objetivo

Entrenar un modelo que clasifique el sentimiento hacia una mención concreta de plato.

No se clasifica la reseña completa.

Ejemplo:

```text
"Las croquetas estaban increíbles, pero el arroz fue decepcionante."
```

Resultado esperado:

| Mención | Sentimiento |
|---|---|
| croquetas | positive |
| arroz | negative |

---

### 6.2. Dataset extendido usado

Dataset principal:

```text
sevilla_mention_sentiment_annotation_dataset_v1_extended.jsonl
```

Tamaño:

| Métrica | Valor |
|---|---:|
| Filas totales | 5.200 |
| Filas usables | 5.200 |

Distribución de etiquetas:

| Etiqueta | Filas |
|---|---:|
| `positive` | 3.105 |
| `negative` | 1.104 |
| `neutral` | 991 |

Distribución por fuente:

| Fuente | Filas |
|---|---:|
| `weak_hybrid` | 2.911 |
| `manual_gold` | 2.289 |

---

### 6.3. Columnas relevantes

El dataset ABSA puede contener columnas como:

| Columna | Descripción |
|---|---|
| `review_id` | Identificador de reseña. |
| `place_id` | Identificador de local. |
| `place_name` | Nombre del local. |
| `mention_text` / `dish_mention_text` | Mención de plato. |
| `dish_name` / `current_dish_display_name` | Plato normalizado. |
| `context_sentence` | Frase de contexto. |
| `window_context` | Ventana de texto ampliada. |
| `review_text_raw` | Texto completo de reseña. |
| `rating_value` | Rating de la reseña. |
| `manual_sentiment_label` | Etiqueta manual. |
| `weak_sentiment_label` | Etiqueta débil. |
| `annotation_status` | Estado de anotación. |

---

### 6.4. Etiquetas

El modelo trabaja con tres clases:

| Label | Significado |
|---|---|
| `negative` | La mención expresa una valoración negativa del plato. |
| `neutral` | La mención es descriptiva, ambigua o poco valorativa. |
| `positive` | La mención expresa una valoración positiva del plato. |

---

### 6.5. Dificultad de la clase neutral

La clase `neutral` es especialmente difícil porque muchas frases neutras se parecen a positivas suaves o negativas suaves.

Ejemplos:

```text
"Pedimos ensaladilla."
```

puede ser neutral si no hay valoración, aunque aparezca en una reseña positiva.

```text
"La pizza estaba correcta."
```

puede ser neutral o positiva suave según el criterio de anotación.

Por eso se usa `macro_f1` como métrica principal, no solo accuracy.

---

## 7. Estrategia de pesos durante entrenamiento

Los modelos no tratan todas las filas con la misma confianza.

Principio general:

```text
manual_gold > augmented_manual > weak_hybrid
```

En el entrenamiento ABSA, por ejemplo:

- las etiquetas manuales tienen mayor peso;
- las etiquetas débiles se usan para volumen, pero con menor peso;
- los pesos de clase ayudan a compensar el desbalance.

Esto permite aprovechar más datos sin confiar ciegamente en las etiquetas débiles.

---

## 8. División train / validation / test

Para evitar fugas de información, los splits se realizaron con cuidado.

En ABSA, el split se hizo agrupando por `review_id`:

```text
menciones de la misma reseña no deben quedar repartidas entre train y test
```

Esto es importante porque una misma reseña puede contener varias menciones y compartir contexto, rating, local y estilo lingüístico.

---

## 9. Relación entre datasets y pipeline

Los datasets no son artefactos finales de usuario, sino elementos de entrenamiento que permiten construir los modelos del pipeline.

Relación:

```text
Dataset NER
    → modelo NER
    → menciones de platos

Dataset normalización
    → modelo reranker
    → dish_id normalizado

Dataset ABSA
    → modelo de sentimiento por mención
    → sentimiento negative/neutral/positive
```

Después, estos modelos se aplican sobre las menciones reales del pipeline Sevilla.

---

## 10. Riesgos de los datasets

Los datasets usados son suficientemente buenos para una fase experimental, pero tienen riesgos:

1. **Weak labels ruidosas**: algunas etiquetas débiles pueden estar equivocadas.
2. **Sesgo positivo**: las reseñas públicas suelen concentrar opiniones positivas.
3. **Cobertura limitada**: no todos los platos posibles están cubiertos por igual.
4. **Ambigüedad gastronómica**: algunas menciones pueden ser ingredientes, platos o categorías.
5. **Variantes lingüísticas**: faltas, abreviaturas, plurales, acentos y nombres extranjeros pueden generar ruido.
6. **Catálogo vivo**: el catálogo de platos debe crecer con nuevos hallazgos.

---

## 11. Conclusión

La fase IA v2 se apoya en datasets extendidos que combinan datos manuales, datos aumentados y etiquetas débiles. Esta estrategia ha permitido entrenar modelos suficientemente fuertes para un pipeline experimental completo.

La decisión técnica es:

```text
Usar los modelos entrenados como componentes experimentales de IA v2,
manteniendo trazabilidad, confianza y revisión en cada capa.
```

Los datasets no son definitivos: deben seguir evolucionando con revisión humana, nuevos ejemplos reales y casos difíciles detectados por el dashboard.
