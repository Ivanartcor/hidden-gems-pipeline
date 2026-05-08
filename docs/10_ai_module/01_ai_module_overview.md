# 01 — Visión general del módulo de IA

## Contexto

**Hidden Gems** es un proyecto orientado a descubrir platos destacados por zona, con una idea central clara:

> No buscar únicamente restaurantes populares, sino identificar qué platos concretos destacan en determinados locales y, más adelante, en determinados barrios.

La parte de IA desarrollada hasta ahora se centra en construir el núcleo inteligente capaz de transformar reseñas gastronómicas en señales estructuradas sobre platos.

El enfoque trabajado ha sido:

```text
Pipeline inteligente de adquisición y procesamiento de datos gastronómicos para Hidden Gems
```

Dentro de ese pipeline, el módulo IA actúa sobre datos textuales de reseñas y genera salidas que luego pueden conectarse con el sistema geográfico, el modelo de negocio y el futuro producto final.

---

## Objetivo del módulo IA

El objetivo principal del módulo IA es convertir texto no estructurado en una estructura analítica útil para ranking.

A partir de reseñas como:

```text
The service was slow, but the pasta was delicious and the tiramisu was amazing.
```

el sistema debe ser capaz de extraer información como:

```text
pasta   → positive
tiramisu → positive
```

y posteriormente agregar esas señales a nivel de plato y negocio:

```text
Negocio X + pasta
→ muchas menciones
→ sentimiento positivo
→ baja negatividad
→ suficiente evidencia
→ candidato Hidden Gem
```

---

## Problema que resuelve

Las reseñas gastronómicas contienen mucha información útil, pero normalmente aparece mezclada:

- opinión sobre el servicio;
- opinión sobre el local;
- opinión sobre precios;
- opinión sobre ambiente;
- menciones a varios platos;
- sentimientos positivos y negativos en la misma review.

Ejemplo:

```text
The burger was dry and overpriced, but the fries were amazing.
```

Si solo se usa el rating general de la review, se pierde información importante. El objetivo es analizar cada plato de forma más precisa:

```text
burger → negative
fries  → positive
```

Por eso el módulo IA se divide en fases especializadas.

---

## Cadena inteligente construida

La cadena actual de IA se compone de los siguientes módulos:

| Fase | Módulo | Objetivo |
|---|---|---|
| 04 | Exploración de candidatos | Detectar posibles menciones de platos con reglas y weak supervision |
| 05 | Dataset NER | Construir dataset BIO para entrenamiento de entidades `DISH` |
| 06 | Dish NER Transformer | Entrenar modelo para detectar platos en reseñas |
| 07 | Inferencia NER | Aplicar el modelo y generar tabla de menciones |
| 08 | Normalización | Agrupar variantes y crear catálogo semilla de platos |
| 09 | Sentimiento por mención | Asignar sentimiento a cada mención de plato |
| 10 | Agregación | Agregar señales por plato y negocio |
| 11 | Ranking | Generar ranking Hidden Gems v1 |

Flujo conceptual:

```text
Yelp reviews
→ Dish NER
→ dish mentions
→ dish normalization
→ mention-level sentiment
→ signal aggregation
→ hidden gem ranking
```

---

## Por qué se ha dividido en módulos

La división modular evita construir una solución opaca y difícil de depurar.

Cada fase produce artefactos propios y puede evaluarse por separado:

```text
NER
→ ¿detecta bien platos?

Normalización
→ ¿agrupa bien variantes?

Sentimiento
→ ¿interpreta bien la opinión local sobre el plato?

Agregación
→ ¿calcula métricas robustas?

Ranking
→ ¿ordena candidatos de forma explicable?
```

Esto permite mejorar cada componente sin rehacer todo el sistema.

---

## Dataset utilizado en esta fase

La fase de IA se ha desarrollado principalmente con datos filtrados del **Yelp Open Dataset**, preparados previamente en la vertical de Yelp del proyecto.

Este dataset se ha usado como base porque aporta:

- reseñas gastronómicas reales;
- texto rico en menciones de platos;
- ratings asociados;
- metadatos de negocio;
- volumen suficiente para entrenamiento y validación.

Limitación importante:

> El dataset Yelp está en inglés y no representa todavía los datos reales de Sevilla. Por tanto, el ranking actual debe interpretarse como un prototipo funcional de la lógica IA, no como el resultado final de Hidden Gems Sevilla.

---

## Principales decisiones técnicas

### 1. Detector de platos como NER

La detección de platos se formuló como un problema de **Named Entity Recognition** con una entidad principal:

```text
DISH
```

Formato de etiquetas:

```text
O
B-DISH
I-DISH
```

Esto permite localizar menciones dentro del texto, no solo clasificar reseñas completas.

---

### 2. Weak supervision para construir dataset

Como no se disponía de un dataset manual grande de platos anotados, se utilizó una estrategia de weak supervision:

- extracción de candidatos;
- reglas de calidad;
- generación de etiquetas BIO;
- smoke test;
- entrenamiento sobre dataset high quality.

---

### 3. Modelo Transformer para NER

Se entrenó un modelo Transformer de clasificación token-level para detectar menciones de platos.

El modelo final logró una métrica fuerte en test:

```text
Entity F1 ≈ 0,9381
Precision ≈ 0,9094
Recall ≈ 0,9687
```

Estos resultados permitieron usar el modelo para inferencia masiva sobre el corpus.

---

### 4. Normalización basada en reglas y catálogo semilla

Después de detectar menciones, se creó una normalización v2 para agrupar variantes y corregir errores de singularización.

Ejemplos:

```text
hummu          → hummus
crab cak       → crab cakes
wing           → wings
rib            → ribs
nacho          → nachos
mashed potato  → mashed potatoes
french fries   → fries
taco           → tacos
```

---

### 5. Sentimiento por mención con enfoque híbrido

No se entrenó directamente un modelo ABSA porque aún no existía un dataset gold de sentimiento por mención.

Se creó una versión híbrida y explicable:

- contexto local;
- cláusula donde aparece el plato;
- léxico positivo/negativo;
- negaciones;
- conectores de contraste;
- rating general como fallback;
- niveles de fiabilidad.

Resultado final:

```text
94.932 menciones con sentimiento
43.142 positive
45.366 neutral
6.424 negative
```

---

### 6. Ranking explicable, no modelo opaco

El ranking final no se basa en un modelo black-box. Se calcula mediante componentes interpretables:

- sentimiento local;
- evidencia;
- confianza;
- balance positivo/negativo;
- hiddenness;
- penalizaciones de ruido;
- penalizaciones por baja evidencia.

Esto facilita explicar por qué un candidato aparece arriba.

---

## Resultados principales del ranking v1

El ranking v1 procesó:

```text
31.036 pares negocio-plato
3.841 candidatos base rankable
622 candidatos Hidden Gems seleccionados
```

Distribución final:

```text
top_hidden_gem: 2
strong_hidden_gem: 50
promising_hidden_gem: 182
exploratory_hidden_gem: 388
not_selected: 30.414
```

Top 2 candidatos:

```text
1. Sushi Ushi → sushi → 82,93
2. Taqueria Cuernavaca → tacos → 82,04
```

Estos resultados validan que el sistema puede construir un ranking razonado a partir de texto no estructurado.

---

## Relación con el pipeline principal

El módulo IA se conecta con el pipeline general de Hidden Gems de la siguiente forma:

```text
fuentes externas
→ adquisición de datos
→ raw/staging/reference
→ reviews y negocios
→ módulo IA
→ señales de platos
→ ranking
→ explotación analítica / producto
```

Actualmente, la IA se ha validado con Yelp. Más adelante debe conectarse con:

- Google Places;
- OSM / Overpass;
- datos geográficos oficiales de Sevilla;
- asignación de barrios;
- datos reales de restaurantes de Sevilla.

---

## Estado actual

Estado del módulo:

```text
Completado como prototipo funcional IA v1
```

Incluye:

- modelo NER entrenado;
- inferencia sobre corpus;
- normalización;
- sentimiento por mención;
- agregación;
- ranking;
- artefactos exportados;
- documentación en proceso.

No incluye todavía:

- ranking por barrios de Sevilla;
- adaptación robusta al español;
- validación humana;
- modelo ABSA entrenado;
- learning-to-rank;
- integración final con FastAPI o frontend.

---

## Valor del módulo dentro del proyecto

Este módulo demuestra que Hidden Gems puede ir más allá de un buscador de restaurantes.

El valor diferencial está en que el sistema puede responder preguntas como:

```text
¿Qué plato destaca realmente en este local?
¿Qué platos reciben mejor señal en diferentes zonas?
¿Qué locales tienen platos concretos muy bien valorados aunque no sean los más populares?
```

La cadena IA construida es la base para convertir el proyecto en un sistema de descubrimiento gastronómico orientado a platos.
