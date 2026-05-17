# 09 - Limitaciones y trabajo futuro del módulo IA

## 1. Objetivo del documento

Este documento recoge las principales limitaciones del módulo IA desarrollado para Hidden Gems y define líneas de mejora futuras.

El objetivo es dejar claro qué se ha conseguido, qué partes deben interpretarse como prototipo y qué pasos serían necesarios para convertir la cadena IA en una solución más robusta y aplicable a Sevilla.

---

## Nota de lectura

Este documento conserva las limitaciones de la **IA v1 basada en Yelp**.

Eso es importante porque algunas limitaciones no describen necesariamente el estado absoluto del repositorio completo, sino el alcance de esta fase concreta. Si existe una capa posterior de Sevilla / IA v2, esa capa debe leerse como evolución de este módulo, mientras que este archivo sigue funcionando como diagnóstico técnico de la versión inicial.

En resumen:

```text
este documento
→ limitaciones y trabajo futuro desde IA v1 / Yelp

capas posteriores
→ integración territorial, Sevilla, barrios, artefactos finales y entrega
```

---

## 2. Estado actual del módulo IA

La cadena IA actual está completa hasta ranking v1:

```text
reviews Yelp
→ detección de platos
→ normalización
→ sentimiento por mención
→ agregación de señales
→ ranking Hidden Gems v1
```

Se ha demostrado que el flujo es viable y produce candidatos explicables.

Sin embargo, el estado de esta fase debe entenderse como:

```text
prototipo funcional de la lógica IA central
```

No como ranking final de producción para Sevilla.

Si el repositorio ya incorpora una capa posterior de Sevilla / IA v2, esa capa debe considerarse la evolución territorial de esta base, no una corrección que elimine la utilidad de este documento.

---

## 3. Limitaciones de datos

### 3.1. Uso de Yelp como dataset principal IA

El módulo IA se ha desarrollado principalmente con el dataset Yelp.

Esto tiene ventajas:

- contiene muchas reviews gastronómicas;
- permite entrenar y validar modelos NLP;
- ofrece metadatos de negocio;
- facilita experimentar antes de tener datos reales locales.

Pero también introduce limitaciones:

- está en inglés;
- no representa Sevilla;
- no contiene barrios oficiales de Sevilla;
- no refleja necesariamente el lenguaje gastronómico local;
- puede incluir tipos de negocios o platos poco frecuentes en España;
- los resultados del ranking v1 no son directamente recomendaciones para el producto final.

---

### 3.2. Ausencia de corpus real de Sevilla en IA v1

El ranking v1 no usa reseñas reales de Sevilla.

La versión final de Hidden Gems necesita conectar, o haber conectado en una capa posterior, la lógica IA con fuentes como:

- Google Places;
- OSM / Overpass;
- dataset oficial de barrios y distritos de Sevilla;
- posibles reseñas, snippets o textos asociados a locales reales;
- datos propios del producto si se generan en el futuro.

Por tanto, el ranking Yelp v1 debe considerarse un prototipo técnico. Las salidas orientadas a Sevilla deben documentarse aparte para no mezclar resultados experimentales con resultados territoriales.

---

### 3.3. Idioma inglés frente a español

El entrenamiento y la inferencia principal se han realizado en inglés.

Esto limita la transferencia directa a reseñas en español.

Ejemplos de diferencias lingüísticas:

| Inglés | Español |
|---|---|
| `burger was amazing` | `la hamburguesa estaba increíble` |
| `fries were cold` | `las patatas estaban frías` |
| `best tacos ever` | `los mejores tacos que he probado` |

El modelo NER y las reglas de sentimiento actuales están optimizados para inglés.

---

### 3.4. Sesgo del dataset Yelp

Yelp puede tener sesgos propios:

- usuarios más inclinados a dejar opiniones extremas;
- zonas geográficas concretas;
- negocios de Estados Unidos;
- vocabulario gastronómico diferente al español;
- reviews largas con múltiples aspectos mezclados.

Esto puede afectar al sentimiento, ranking y frecuencia de platos.

---

## 4. Limitaciones del detector de platos

### 4.1. Dataset weak-supervised

El detector NER fue entrenado con un dataset construido mediante weak supervision.

Esto permitió avanzar sin etiquetado manual masivo, pero implica que:

- algunas etiquetas pueden ser incorrectas;
- algunos platos pueden no estar marcados;
- algunas entidades pueden estar sobregeneralizadas;
- el modelo puede aprender patrones del generador débil.

### 4.2. Errores de entidad

Aunque el NER obtuvo buenos resultados, todavía existen:

- falsos positivos;
- falsos negativos;
- spans incompletos;
- spans demasiado largos;
- separaciones incorrectas de platos compuestos.

Ejemplo de posible problema:

```text
spicy tuna tacos
```

Puede separarse en:

```text
tuna + tacos
```

o no capturar el modificador `spicy`.

### 4.3. Falta de validación humana extensa

No existe todavía un gold standard manual amplio para evaluar el detector en condiciones reales.

---

## 5. Limitaciones de normalización

### 5.1. Reglas manuales y heurísticas

La normalización v2 mejora la v1, pero sigue basada en reglas.

Ejemplos corregidos:

```text
hummu → hummus
crab cak → crab cakes
wing → wings
```

Sin embargo, todavía pueden existir problemas como:

- platos diferentes agrupados incorrectamente;
- variantes que deberían fusionarse y no se fusionan;
- modificadores importantes perdidos;
- platos demasiado específicos;
- platos demasiado genéricos.

---

### 5.2. Duplicados potenciales

Se generaron 6.984 candidatos de duplicados.

Esto indica que el catálogo todavía necesita revisión.

Ejemplos de casos difíciles:

```text
burger / cheeseburger
crab / crab cakes
chicken / fried chicken
tacos / tuna tacos
```

No todos deben fusionarse automáticamente.

---

### 5.3. Falta de taxonomía gastronómica final

Actualmente existe un catálogo semilla, pero no una taxonomía final revisada.

Una taxonomía más madura podría incluir:

- familia del plato;
- cocina asociada;
- tipo de plato;
- ingrediente principal;
- plato base;
- variante;
- idioma;
- alias español/inglés.

---

## 6. Limitaciones del sentimiento por mención

### 6.1. Enfoque weak-supervised

El sentimiento por mención no se entrenó con etiquetas humanas.

La versión final actual es:

```text
hybrid_context_lexicon_v1_1
```

Combina:

- contexto local;
- cláusula objetivo;
- léxicos positivos/negativos;
- patrones directos;
- rating general como fallback;
- confianza del NER;
- flags de ambigüedad.

Esto es explicable y útil, pero no equivale a un modelo ABSA validado.

---

### 6.2. Ambigüedad del contexto

Las reviews suelen mezclar muchos elementos:

```text
The service was terrible, but the pasta was delicious.
```

En estos casos, el sentimiento general de la review no coincide necesariamente con el sentimiento del plato.

La v1.1 intenta resolverlo, pero no siempre puede.

---

### 6.3. Señales locales débiles

Muchas menciones de platos no tienen una valoración explícita cerca.

Ejemplo:

```text
I ordered the burger and fries.
```

Aquí no se puede saber si el plato fue bueno o malo sin más contexto.

Por eso muchos casos dependen de `review_prior_fallback`.

---

### 6.4. Riesgo de sesgo por reglas

Las reglas pueden favorecer expresiones concretas:

- `delicious`;
- `amazing`;
- `cold`;
- `dry`;
- `bland`.

Pero pueden fallar ante:

- ironía;
- frases complejas;
- negaciones lejanas;
- comparaciones;
- matices culturales;
- expresiones en español.

---

## 7. Limitaciones de agregación

### 7.1. Sensibilidad a la evidencia disponible

Un plato con pocas menciones puede parecer excelente si todas son positivas.

Para mitigarlo se aplicaron:

- pesos de fiabilidad;
- prior bayesiano neutral;
- thresholds mínimos;
- tiers de evidencia;
- penalizaciones por baja evidencia.

Aun así, los candidatos con poca evidencia deben interpretarse con cautela.

---

### 7.2. Señales de negocio no completas

El dataset actual no incorpora todavía señales externas como:

- popularidad real del local;
- precio;
- horario;
- ubicación geográfica real de Sevilla;
- barrio;
- categoría local validada;
- afluencia;
- datos temporales recientes.

El ranking actual se basa principalmente en texto y metadatos Yelp.

---

### 7.3. Ruido residual

Aunque se detectaron 806 pares ruidosos y 359 posibles bebidas, pueden quedar casos no identificados.

Ejemplos de ruido posible:

- nombres de platos demasiado largos;
- nombres con contexto incrustado;
- bebidas mezcladas con platos;
- términos genéricos;
- errores de NER.

---

## 8. Limitaciones del ranking v1

### 8.1. Pesos heurísticos

El `hidden_gem_score_v1` se basa en pesos definidos manualmente.

No se han aprendido a partir de feedback humano.

Esto significa que los pesos son razonables y explicables, pero no necesariamente óptimos.

---

### 8.2. No existe learning-to-rank

El ranking no utiliza todavía un modelo de aprendizaje para ordenar resultados.

No hay datos etiquetados de tipo:

```text
este candidato es realmente un hidden gem
este candidato no lo es
```

Sin ese feedback, un modelo learning-to-rank no sería fiable.

---

### 8.3. No hay validación humana del top final

Los 622 candidatos seleccionados no han sido verificados manualmente.

Deben interpretarse como:

```text
candidatos priorizados para revisión
```

No como recomendaciones definitivas.

---

### 8.4. No hay barrios ni distritos en el ranking Yelp v1

El ranking documentado en esta carpeta funciona a nivel:

```text
negocio + plato + ciudad/estado
```

La versión territorial de Hidden Gems debe funcionar a nivel:

```text
local + plato + barrio + distrito
```

Esta es una diferencia clave y justifica que la integración Sevilla / barrios se documente en una capa posterior, aunque reutilice componentes de este módulo.

---

## 9. Trabajo futuro o evolución posterior: adaptación a Sevilla

### 9.1. Integrar Google Places

El siguiente paso práctico es conectar los módulos IA con locales reales obtenidos desde Google Places.

Se necesitarán datos como:

- `place_id`;
- nombre del local;
- coordenadas;
- tipos/categorías;
- rating;
- número de reseñas;
- dirección;
- estado operativo;
- posibles reseñas o snippets si están disponibles.

---

### 9.2. Integrar OSM / Overpass

OSM aporta una fuente abierta y complementaria.

Puede ayudar a:

- ampliar cobertura de locales;
- validar categorías;
- obtener geometrías o puntos;
- comparar presencia entre fuentes.

---

### 9.3. Asignación geográfica a barrios

La integración con el dataset oficial de Sevilla permitirá asignar cada local a:

- distrito;
- barrio;
- geometría oficial.

Esto permitirá transformar el ranking actual en:

```text
mejores platos por barrio
```

que es el objetivo principal de Hidden Gems.

---

## 10. Trabajo futuro: mejora del NER

### 10.1. Crear gold standard manual

Se recomienda etiquetar manualmente una muestra de reviews para crear un gold standard.

Podría incluir:

- 500 reviews en inglés;
- 500 reviews en español;
- spans exactos de platos;
- casos negativos;
- platos compuestos;
- bebidas separadas de platos.

---

### 10.2. Fine-tuning multilingüe

Para español convendría evaluar modelos como:

- `bert-base-multilingual-cased`;
- `xlm-roberta-base`;
- modelos BETO/Spanish BERT;
- modelos multilingües de Hugging Face.

---

### 10.3. Mejorar postprocesado de spans

Se pueden añadir reglas para:

- unir modificadores relevantes;
- separar platos coordinados;
- eliminar determinantes;
- evitar spans demasiado largos;
- distinguir comida de bebida.

---

## 11. Trabajo futuro: normalización por embeddings

La normalización actual puede mejorarse con embeddings.

Una estrategia futura sería:

```text
surface forms
→ embeddings semánticos
→ clustering
→ revisión manual
→ catálogo consolidado
```

Esto permitiría agrupar mejor variantes como:

```text
burger
cheeseburger
bacon burger
burger with bacon
```

pero sin fusionar automáticamente conceptos diferentes.

---

## 12. Trabajo futuro: modelo ABSA

El sentimiento por mención debería evolucionar hacia un modelo de **aspect-based sentiment analysis**.

Input posible:

```text
review_text + dish_mention + contexto marcado
```

Salida:

```text
positive / neutral / negative / mixed
```

La cadena actual ya generó:

```text
25.011 candidatos high reliability
```

Estos podrían usarse como punto de partida weak-supervised.

Pero lo ideal sería combinarlos con una muestra manual revisada.

---

## 13. Trabajo futuro: adaptación al español

Para usar Hidden Gems en Sevilla, se necesita adaptar los módulos al español.

Áreas necesarias:

- detector de platos en español;
- catálogo de platos en español;
- aliases español/inglés;
- sentimiento con léxico español;
- modelo ABSA multilingüe;
- tratamiento de expresiones locales;
- platos típicos sevillanos y andaluces.

Ejemplos:

```text
croquetas
solomillo al whisky
espinacas con garbanzos
montadito de pringá
salmorejo
tortilla de camarones
```

---

## 14. Trabajo futuro: validación humana

La validación humana es necesaria para convertir el prototipo en producto.

Se recomienda revisar manualmente:

- top candidatos del ranking;
- candidatos rechazados con score alto;
- errores de normalización;
- sentimiento por mención en casos ambiguos;
- platos frecuentes;
- platos raros;
- candidatos por barrio.

Esta revisión puede alimentar:

- reglas nuevas;
- datasets gold;
- métricas de calidad;
- modelos supervisados futuros.

---

## 15. Trabajo futuro: learning-to-rank

Cuando existan datos de feedback, se podría entrenar un modelo de ranking.

Posibles señales:

- sentimiento local;
- número de menciones;
- número de reviews;
- ratio positivo;
- ratio negativo;
- rareza;
- barrio;
- categoría del local;
- rating del local;
- popularidad;
- validaciones humanas;
- clicks o favoritos de usuarios.

Modelos posibles:

- regresión logística/ranking simple;
- gradient boosting;
- LambdaMART;
- modelos neuronales de ranking;
- enfoques híbridos explicables.

No se recomienda hacerlo todavía sin etiquetas humanas.

---

## 16. Trabajo futuro: integración con base de datos

Los resultados IA deberían integrarse con el modelo de datos del pipeline.

Entidades relacionadas:

- `Place`;
- `PlaceSourceRef`;
- `Review`;
- `Category`;
- `PlaceCategory`;
- `Neighborhood`;
- `PlaceNeighborhoodAssignment`;
- `SourceSystem`;
- `SourceRun`;
- `RawAsset`;
- `ValidationIssue`.

Además, podrían añadirse entidades específicas para IA:

- `Dish`;
- `DishAlias`;
- `DishMention`;
- `DishMentionSentiment`;
- `DishBusinessSignal`;
- `HiddenGemCandidate`.

---

## 17. Trabajo futuro: trazabilidad y MLOps

Para producción, cada ejecución IA debería registrar:

- versión del modelo NER;
- versión del normalizador;
- versión del sentiment scorer;
- versión del ranking;
- fecha de ejecución;
- fuente de datos;
- parámetros usados;
- métricas generadas;
- artefactos producidos.

Esto permitirá reproducibilidad y auditoría.

---

## 18. Riesgos principales

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Datos no representativos | Ranking poco aplicable a Sevilla | Adaptar con datos locales. |
| Errores de sentimiento | Candidatos mal valorados | Validación humana y modelo ABSA. |
| Normalización incorrecta | Platos fusionados o separados mal | Revisión de catálogo y embeddings. |
| Exceso de platos populares | Menos hiddenness | Penalización por prevalencia global. |
| Poca evidencia | Candidatos inestables | Priors bayesianos y thresholds. |
| Falta de barrios | No cumple objetivo final | Integrar PostGIS y dataset oficial. |

---

## 19. Priorización recomendada desde IA v1

Esta priorización se planteó desde el cierre de la IA v1. Algunas tareas pueden estar ya completadas o movidas a capas posteriores del repositorio.

### Fase inmediata

1. Documentar completamente el módulo IA.
2. Conectar outputs IA con el README del repositorio.
3. Preparar una muestra de resultados para presentación.
4. Volver al pipeline principal de Sevilla.

### Fase siguiente

1. Ingesta real de Google Places.
2. Integración OSM.
3. Asignación de locales a barrios.
4. Diseño de tablas IA en PostgreSQL/PostGIS.
5. Adaptación inicial a español.

### Fase avanzada

1. Gold standard manual.
2. Modelo ABSA.
3. Normalización por embeddings.
4. Learning-to-rank.
5. Evaluación con usuarios.

---

## 20. Conclusión

La parte IA de Hidden Gems ya demuestra que el enfoque es viable.

Se ha construido una cadena completa que transforma reseñas no estructuradas en candidatos de platos destacados.

Sin embargo, la versión v1 debe considerarse un prototipo técnico:

```text
válido para demostrar lógica IA,
no equivalente por sí solo a recomendaciones finales en Sevilla.
```

La prioridad tras esta fase es conectar, o documentar claramente cómo se ha conectado, esta lógica con el pipeline real de adquisición de datos, geografía oficial y locales de Sevilla.
