# 02. Problema y objetivos


## 1. Problema que aborda el proyecto

La información gastronómica disponible en plataformas digitales suele estar dispersa, heterogénea y orientada principalmente al consumo inmediato, no al análisis estructurado.

Existen numerosas fuentes con datos potencialmente valiosos, como fichas de locales, reseñas, categorías, coordenadas, ratings o divisiones territoriales, pero estos datos presentan varias dificultades:

- proceden de sistemas distintos con modelos incompatibles;
- no siguen una taxonomía común;
- mezclan señales útiles con ruido;
- pueden contener duplicados, inconsistencias o datos incompletos;
- no suelen venir preparados para análisis por barrio o por unidad territorial concreta;
- rara vez están listos para alimentar directamente procesos de NLP, detección de platos o scoring;
- los resultados derivados de IA necesitan trazabilidad para poder ser auditados y reutilizados.

Esto genera una barrera importante para cualquier proyecto que quiera explotar la información gastronómica de forma rigurosa y mantenible.

En el caso de Hidden Gems, el problema es aún más específico: no basta con reunir restaurantes. Hace falta construir una base sólida que permita relacionar correctamente:

```text
locales
reseñas
platos mencionados
sentimiento textual
categorías
fuentes externas
barrio / distrito
calidad del dato
ranking explicable
dashboard de consulta
```

Por tanto, el problema principal no es la ausencia de datos, sino la falta de un sistema que los **adquiera, unifique, limpie, estructure, trace, procese con IA y prepare de manera consistente** para análisis gastronómico avanzado.

---

## 2. Necesidad técnica del proyecto

Antes de poder realizar análisis avanzados sobre platos, reseñas o rankings territoriales, es necesario resolver una capa previa de ingeniería del dato.

Esa necesidad técnica se concreta en varios puntos:

- definir qué fuentes son relevantes y cómo se integran;
- garantizar trazabilidad desde la fuente hasta el dato estructurado;
- separar claramente dato raw, dato procesado y dato derivado;
- construir una base geográfica fiable para trabajar por barrios;
- disponer de un modelo de datos que represente correctamente locales, reseñas, categorías, fuentes, ejecuciones, geografía y resultados IA;
- preparar corpus textuales para NLP;
- integrar resultados IA sin crear entidades huérfanas;
- validar que menciones, sentimientos, señales y rankings se conectan con `place`, `review` y `dish`;
- diferenciar prototipos IA, pilotos locales, rankings experimentales y resultados productivos finales;
- proporcionar una forma visual y entendible de explorar los resultados.

Este proyecto nace precisamente para cubrir esa necesidad fundacional.

---

## 3. Objetivo general

Desarrollar un **pipeline inteligente de adquisición, procesamiento, integración IA y explotación analítica de datos gastronómicos**, integrado en el ecosistema de Hidden Gems, capaz de obtener información desde múltiples fuentes, almacenarla de forma trazable, validarla, estructurarla, enriquecerla geográficamente y prepararla para análisis avanzado, ranking y visualización.

El objetivo no es solo almacenar locales o reseñas, sino construir una base capaz de soportar el ciclo completo:

```text
fuente externa
→ dato raw
→ dato canónico
→ review operativa
→ corpus textual
→ detección de platos
→ normalización/entity linking
→ sentimiento por mención
→ señales agregadas
→ ranking Hidden Gems
→ comparación de versiones
→ consulta demo / dashboard
→ futura API o producto
```

---

## 4. Objetivos específicos

### 4.1. Diseñar una arquitectura de adquisición reproducible

Definir una estructura clara para organizar el flujo de datos desde las fuentes externas hasta su persistencia en el sistema, separando responsabilidades y facilitando el reprocesado.

### 4.2. Integrar múltiples fuentes de datos

Trabajar con una estrategia multisource que combine fuentes dinámicas, abiertas, geográficas y corpus externos, minimizando la dependencia de un único proveedor.

### 4.3. Construir una capa raw trazable

Registrar ejecuciones, artefactos y orígenes de forma que cada dato pueda auditarse y relacionarse con su fuente y su proceso de carga.

### 4.4. Definir un modelo de datos sólido

Representar adecuadamente entidades clave como locales, referencias de fuente, reseñas, categorías, barrios, distritos, asignaciones geográficas, platos, menciones, sentimientos, señales y candidatos de ranking.

### 4.5. Preparar y normalizar datos para análisis textual

Construir datasets y corpus que permitan trabajar con reseñas gastronómicas de forma controlada, incluyendo textos locales de Google Reviews y corpus amplio procedente de Yelp Open Dataset.

### 4.6. Incorporar contexto geográfico útil

Vincular los locales a unidades territoriales oficiales, permitiendo que el análisis posterior se realice por barrio y no solo por coordenadas o listados genéricos.

### 4.7. Desarrollar una capa IA de extracción y scoring

Crear una lógica IA para:

- detectar menciones de platos;
- normalizar nombres de platos;
- asociar sentimiento a menciones;
- agregar señales por local y plato;
- generar candidatos Hidden Gems;
- explicar el resultado mediante scores, tiers y texto justificativo.

### 4.8. Integrar resultados IA en PostgreSQL

Persistir los resultados derivados de IA en tablas específicas, con versionado, trazabilidad, checks de integridad y vistas de consulta.

### 4.9. Validar el flujo sobre datos reales de Sevilla

Aplicar la cadena IA sobre reviews reales de Google Places en Sevilla, generando un ranking piloto local con cobertura por barrios y distritos.

### 4.10. Mejorar el flujo IA con modelos entrenados

Entrenar y aplicar modelos específicos para mejorar la cadena local de Sevilla:

- **Modelo 1: Dish NER**, para detectar menciones de platos;
- **Modelo 3: Normalización / entity linking**, mediante reranker cross-encoder;
- **Modelo 2: Mention Sentiment / ABSA**, para clasificar sentimiento hacia el plato concreto.

### 4.11. Construir una capa de señales y ranking v2

Agrupar las predicciones por `place_id + dish_id`, calcular señales agregadas y construir un ranking Hidden Gems Sevilla v2 que mejore el piloto anterior.

### 4.12. Comparar ranking v1 vs ranking v2

Evaluar si la nueva cadena IA conserva candidatos útiles del ranking piloto y amplía la cobertura de locales, platos y barrios.

### 4.13. Facilitar la explotación analítica

Construir una base que permita consultar resultados mediante scripts, vistas SQL, exports de dashboard y dashboards Streamlit.

### 4.14. Documentar el sistema de forma profesional

Generar documentación clara y estructurada para que el proyecto sea entendible, reproducible y mantenible.

---

## 5. Objetivos de valor dentro de Hidden Gems

Más allá del valor técnico inmediato, este proyecto cumple un papel estratégico dentro del PI.

Permite:

- transformar una idea general en una infraestructura operativa real;
- reducir el riesgo de improvisación en fases posteriores;
- apoyar el desarrollo de verticales de adquisición independientes;
- dar coherencia al modelo de datos desde el inicio;
- conectar datos geográficos, reseñas y señales IA;
- diferenciar claramente corpus experimental, dato operativo, piloto local, ranking experimental y ranking productivo;
- demostrar valor mediante dashboards;
- sentar la base para decisiones futuras de calidad, normalización, IA, API y producto.

En este sentido, el proyecto no solo persigue “tener una base de datos”, sino construir una **columna vertebral técnica** sobre la que Hidden Gems pueda crecer sin perder consistencia.

---

## 6. Criterio de éxito de esta fase

Se considera que esta fase cumple sus objetivos si el proyecto logra:

- definir y documentar correctamente su arquitectura de adquisición;
- disponer de una base de datos coherente con el modelo diseñado;
- conectar y documentar verticales de datos reales;
- garantizar trazabilidad entre fuentes, ejecuciones y registros;
- cargar reseñas operativas cuando exista vínculo con locales canónicos;
- generar corpus NLP externo controlado;
- validar una primera capa IA prototipo sobre Yelp;
- aplicar el flujo IA sobre reviews reales de Sevilla;
- integrar los resultados IA en PostgreSQL sin huérfanos;
- disponer de vistas y consultas para explotar los resultados;
- generar un ranking piloto `sevilla_pilot` consultable;
- entrenar modelos específicos para mejorar la fase local;
- generar ranking Hidden Gems Sevilla IA v2;
- comparar v1 y v2;
- exportar datos para dashboard;
- disponer de dashboards funcionales;
- dejar documentada la fase final de entrega.

El éxito, por tanto, no se mide por tener ya el producto final completo, sino por haber construido correctamente la **infraestructura de datos e IA que lo hace viable**.

---

## 7. Estado de cumplimiento

A día de esta versión, el proyecto cumple los objetivos principales planteados para la entrega académica.

```text
Sevilla Geo                              ✅ implementado
OSM / Overpass                           ✅ implementado
Google Places Text Search                ✅ implementado
Google Places Reviews                    ✅ implementado
Yelp Open Dataset                        ✅ implementado como corpus/prototipo
Módulo IA Yelp                           ✅ implementado e integrado
Piloto IA Sevilla v1                     ✅ implementado, cargado y validado
Vistas SQL IA                            ✅ disponibles
Scripts demo de consulta                 ✅ disponibles
Dashboard Sevilla v1                     ✅ implementado
Dashboard Yelp                           ✅ implementado
NER de platos para Sevilla IA v2          ✅ entrenado y aplicado
Normalización/entity linking v2           ✅ entrenado y aplicado
ABSA sentiment por mención v2             ✅ entrenado y aplicado
Señales place-dish v2                    ✅ generadas
Ranking Hidden Gems Sevilla v2           ✅ generado
Comparación ranking v1 vs v2             ✅ generada
Export dashboard v2                      ✅ generado
Dashboard Sevilla IA v2                  ✅ implementado
Documentación Sevilla IA v2              ✅ completada
Entrega académica                        ✅ cerrada
```

Resultados principales del ranking Sevilla IA v2:

```text
total_candidates_scored_v2: 2.335
selected_candidates_v2: 268
selected_places_v2: 198
selected_dishes_v2: 40
selected_neighborhoods_v2: 67
selected_districts_v2: 11
```

Resultados de comparación v1/v2:

```text
v1_selected_unique: 150
v2_selected_unique: 268
matched_candidates: 119
v1_coverage_in_v2: 0.793333
selected_places_delta_v2_minus_v1: +76
selected_neighborhoods_delta_v2_minus_v1: +12
```

---

## 8. Objetivo cerrado de entrega

El objetivo inmediato ya no es demostrar que el sistema puede funcionar, sino dejar el repositorio preparado como entrega final del Proyecto Integrado.

La entrega queda definida como:

```text
pipeline de datos + integración IA + ranking + dashboard + documentación
```

No se entrega una aplicación final de consumo masivo, sino un **MVP técnico avanzado** que demuestra el ciclo completo desde fuentes de datos hasta visualización analítica.



Realizado por Iván Arteaga Cordero
