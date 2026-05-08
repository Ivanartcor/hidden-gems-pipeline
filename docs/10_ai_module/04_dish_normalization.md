# 04 - Normalización de platos

## 1. Objetivo del módulo

El objetivo de este módulo es transformar menciones textuales detectadas por el modelo NER en platos canónicos reutilizables dentro de Hidden Gems.

El detector de platos produce menciones como:

```text
burger
burgers
cheeseburger
burger with bacon
mac and cheese
french fries
crab cakes
```

Sin normalización, cada variante quedaría como un plato distinto. Esto rompería los cálculos posteriores de sentimiento, agregación y ranking.

La normalización permite pasar de menciones superficiales a entidades más estables:

```text
burgers → burger
french fries → fries
crab cake → crab cakes
hummu → hummus
```

Este módulo genera una primera versión de catálogo de platos y aliases a partir de las menciones detectadas por el modelo `Dish NER v1`.

---

## 2. Papel dentro del flujo de IA

La normalización se sitúa justo después de la inferencia del modelo NER:

```text
reviews
→ Dish NER
→ menciones de platos
→ normalización de platos
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems
```

El módulo recibe menciones detectadas en reviews y devuelve una tabla enriquecida con:

- forma textual original;
- forma limpia;
- forma canónica;
- `dish_id`;
- método de normalización;
- flags de calidad;
- estado de revisión.

---

## 3. Notebook implicado

| Notebook | Función |
|---|---|
| `08_dish_normalization_and_catalog_builder.ipynb` | Construye el catálogo inicial de platos, aliases y menciones normalizadas. |

---

## 4. Entrada del módulo

El input principal es el archivo generado por el notebook de inferencia NER:

```text
dish_mentions_model_v1_full.jsonl
```

Este archivo contiene las menciones detectadas por el modelo sobre el corpus Yelp.

Resumen del input:

| Métrica | Valor |
|---|---:|
| Reviews procesadas en inferencia | 79.270 |
| Menciones detectadas | 95.061 |
| Reviews con menciones | 42.471 |
| Reviews sin menciones | 36.799 |
| Media de menciones por review | 1,20 |
| Media de menciones por review con menciones | 2,24 |
| Confianza media del NER | 0,9752 |
| Confianza mediana del NER | 0,9991 |
| Reviews truncadas | 8.279 |

---

## 5. Problema de normalización

Las menciones extraídas por NER son expresiones naturales escritas por usuarios. Esto provoca varios tipos de variación:

### 5.1. Singular/plural

```text
burger / burgers
pizza / pizzas
taco / tacos
crab cake / crab cakes
```

### 5.2. Variantes léxicas

```text
french fries / fries / home fries
omelette / omelet
doughnut / donut
```

### 5.3. Platos compuestos

```text
fried chicken
mac and cheese
brisket ramen
waffle fries
```

### 5.4. Menciones extendidas

```text
burger with bacon
salad with grilled chicken
gnocchi with marinara
```

### 5.5. Ruido residual

El modelo NER puede detectar fragmentos poco útiles o demasiado genéricos:

```text
food
meal
appetizer
side
#
up
```

Por eso el normalizador no solo agrupa, sino que también marca flags de calidad.

---

## 6. Enfoque aplicado

La normalización se diseñó como un proceso híbrido, basado en reglas trazables y revisables.

No se entrenó todavía un modelo de embeddings ni un clustering semántico avanzado, porque en esta fase era más importante tener:

- control sobre las transformaciones;
- trazabilidad;
- facilidad de depuración;
- salidas estables para los módulos posteriores;
- catálogo inicial revisable manualmente.

El proceso general fue:

```text
mención detectada
→ limpieza textual
→ normalización básica
→ detección de ruido
→ canonical rule v1
→ revisión de errores
→ overrides v2
→ catálogo semilla
→ aliases
→ menciones normalizadas v2
```

---

## 7. Normalización v1

La primera versión aplicó reglas simples:

- conversión a minúsculas;
- limpieza de espacios;
- eliminación de puntuación periférica;
- eliminación de determinantes iniciales;
- eliminación de palabras de cierre no útiles;
- singularización ligera;
- detección de términos genéricos o ruidosos.

### 7.1. Resultados v1

| Métrica | Valor |
|---|---:|
| Menciones de entrada | 95.061 |
| Menciones normalizadas v1 | 94.303 |
| Menciones pendientes/excluidas v1 | 758 |
| Platos canónicos semilla v1 | 9.401 |
| Aliases semilla v1 | 9.692 |

La v1 funcionó como primera base, pero mostró errores claros derivados de una singularización demasiado agresiva.

### 7.2. Errores detectados en v1

Ejemplos de errores:

| Mención original | Canonical v1 incorrecto |
|---|---|
| `hummus` | `hummu` |
| `crab cakes` | `crab cak` |
| `wings` | `wing` |
| `ribs` | `rib` |
| `nachos` | `nacho` |
| `mashed potatoes` | `mashed potato` |

Estos errores no eran graves para la arquitectura, pero sí afectaban a la calidad del catálogo. Por eso se construyó una versión v2.

---

## 8. Normalización v2

La versión v2 añadió overrides controlados y reglas más conservadoras.

### 8.1. Correcciones principales

| Canonical v1 | Canonical v2 |
|---|---|
| `hummu` | `hummus` |
| `crab cak` | `crab cakes` |
| `wing` | `wings` |
| `rib` | `ribs` |
| `nacho` | `nachos` |
| `mashed potato` | `mashed potatoes` |
| `french fries` | `fries` |
| `home fries` | `fries` |
| `taco` | `tacos` |
| `omelette` | `omelet` |
| `doughnut` | `donut` |

### 8.2. Resultados v2

| Métrica | Valor |
|---|---:|
| Menciones de entrada | 95.061 |
| Menciones normalizadas v2 | 94.932 |
| Menciones pendientes/excluidas v2 | 129 |
| Platos canónicos semilla v2 | 9.937 |
| Aliases semilla v2 | 10.235 |
| Candidatos de duplicados generados | 6.984 |
| Menciones marcadas para revisión | 300 |

La reducción de pendientes de 758 a 129 indica que la v2 mejora la cobertura sin perder trazabilidad.

---

## 9. Catálogo de platos

El catálogo semilla se generó agrupando por forma canónica v2.

Cada plato canónico incluye señales como:

- `dish_id`;
- `canonical_dish_name`;
- idioma;
- versión del catálogo;
- método de normalización;
- menciones totales;
- reviews totales;
- negocios totales;
- número de surface forms;
- confianza media;
- rating medio;
- menciones positivas, neutrales y negativas;
- estado de revisión manual;
- prioridad de revisión.

Ejemplos de platos canónicos frecuentes:

```text
pizza
burger
fries
sushi
tacos
shrimp
steak
ice cream
wings
donut
oysters
sandwich
pancake
crab
burrito
pho
salmon
ribs
fried chicken
mac and cheese
hummus
crab cakes
mashed potatoes
```

---

## 10. Aliases

Los aliases conectan variantes textuales con el plato canónico.

Ejemplo conceptual:

| Alias | Canonical dish |
|---|---|
| `burger` | `burger` |
| `burgers` | `burger` |
| `french fries` | `fries` |
| `home fries` | `fries` |
| `crab cake` | `crab cakes` |
| `crab cakes` | `crab cakes` |

Esta tabla es importante porque permite:

- auditar cómo se agrupan variantes;
- alimentar una futura base de datos relacional;
- preparar revisión manual;
- reutilizar el catálogo en el pipeline de Sevilla.

---

## 11. Candidatos de duplicados

La v2 generó un archivo de candidatos de duplicados mediante similitud textual.

Ejemplos de pares que pueden aparecer:

```text
burger / cheeseburger
crab / crab cakes
chicken / fried chicken
fries / waffle fries
tacos / tuna tacos
```

No se fusionaron automáticamente porque muchos pares similares no son realmente equivalentes.

Por ejemplo:

```text
burger ≠ cheeseburger
crab ≠ crab cakes
chicken ≠ fried chicken
tuna ≠ tuna tacos
```

La decisión fue dejar estos casos como candidatos de revisión, no como fusiones automáticas.

---

## 12. Artefactos generados

### 12.1. Artefactos principales

| Archivo | Descripción |
|---|---|
| `dish_mentions_normalized_v2.jsonl` | Menciones con plato canónico v2 y `dish_id_v2`. |
| `dish_catalog_seed_v2.csv` | Catálogo semilla de platos normalizados. |
| `dish_aliases_seed_v2.csv` | Tabla de aliases/surface forms. |
| `dish_normalization_summary_v2.json` | Resumen de métricas del módulo. |

### 12.2. Artefactos de revisión

| Archivo | Descripción |
|---|---|
| `dish_surface_forms_v2.csv` | Surface forms detectadas y agregadas. |
| `dish_normalization_duplicate_candidates_v2.csv` | Candidatos de duplicados para revisión. |
| `dish_catalog_review_top_v2.csv` | Platos principales para revisión manual. |
| `dish_catalog_review_low_confidence_v2.csv` | Platos con menor confianza. |
| `dish_catalog_review_many_aliases_v2.csv` | Platos con muchas variantes. |
| `dish_mentions_review_flags_v2.jsonl` | Menciones con flags de revisión. |

---

## 13. Decisiones de diseño

### 13.1. No usar clustering todavía

Aunque el problema podría resolverse parcialmente con embeddings y clustering, se decidió no hacerlo en esta fase porque:

- el dataset todavía procede de Yelp en inglés;
- no hay validación humana suficiente;
- una fusión automática incorrecta puede perjudicar el ranking;
- las reglas permiten explicar cada decisión;
- el catálogo semilla aún debe madurar.

### 13.2. Mantener granularidad

Se prefirió conservar platos compuestos en lugar de fusionarlos agresivamente.

Por ejemplo:

```text
fried chicken
chicken wings
brisket ramen
waffle fries
mac and cheese
```

Estos platos pueden ser señales de ranking muy útiles. Fusionarlos demasiado pronto perdería información.

### 13.3. Excluir solo ruido claro

La normalización no pretende eliminar todo lo dudoso. Se excluye o marca lo claramente problemático, pero se conserva suficiente información para que el scoring posterior pueda penalizar o filtrar.

---

## 14. Limitaciones

La normalización v2 es funcional, pero no perfecta.

Limitaciones principales:

- se basa en reglas e inglés;
- no resuelve todas las variantes semánticas;
- no distingue siempre plato principal, ingrediente o acompañamiento;
- algunos platos compuestos pueden estar sobresegmentados;
- algunos aliases requieren revisión humana;
- los candidatos de duplicados no se fusionan automáticamente;
- aún no hay adaptación final al español.

---

## 15. Relación con fases posteriores

El archivo principal de salida es:

```text
dish_mentions_normalized_v2.jsonl
```

Este archivo alimenta el módulo de sentimiento por mención:

```text
dish_mentions_normalized_v2.jsonl
→ 09_dish_mention_sentiment_hybrid_v1.ipynb
```

A partir de ahí, cada mención ya tiene:

- plato detectado;
- plato normalizado;
- identificador de plato;
- review original;
- negocio;
- confianza NER;
- estado de normalización.

Esto permite calcular sentimiento a nivel de mención y no solo a nivel de review.
