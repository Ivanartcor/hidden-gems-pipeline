# 02. Problema y objetivos

## 1. Problema que aborda el proyecto

La información gastronómica disponible en plataformas digitales suele estar dispersa, heterogénea y orientada principalmente al consumo inmediato, no al análisis estructurado.

Existen numerosas fuentes con datos potencialmente valiosos, como fichas de locales, reseñas, categorías, coordenadas o divisiones territoriales, pero estos datos presentan varias dificultades:

- proceden de sistemas distintos con modelos incompatibles
- no siguen una taxonomía común
- mezclan señales útiles con ruido
- pueden contener duplicados, inconsistencias o datos incompletos
- no suelen venir preparados para análisis por barrio o por unidad territorial concreta
- rara vez están listos para alimentar directamente procesos de NLP o scoring

Esto genera una barrera importante para cualquier proyecto que quiera explotar la información gastronómica de forma rigurosa y reutilizable.

En el caso de Hidden Gems, el problema es aún más específico: no basta con reunir restaurantes, sino que hace falta construir una base sólida que permita relacionar correctamente locales, reseñas, categorías y geografía, para después poder detectar señales de valor gastronómico a nivel de barrio.

Por tanto, el problema principal no es la ausencia de datos, sino la falta de un sistema que los **adquiera, unifique, limpie, estructure y prepare de manera consistente**.

---

## 2. Necesidad técnica del proyecto

Antes de poder realizar análisis avanzados sobre platos, reseñas o rankings territoriales, es necesario resolver una capa previa de ingeniería del dato.

Esa necesidad técnica se concreta en varios puntos:

- definir qué fuentes son relevantes y cómo se integran
- garantizar trazabilidad desde la fuente hasta el dato estructurado
- separar claramente dato raw, dato procesado y dato derivado
- construir una base geográfica fiable para trabajar por barrios
- disponer de un modelo de datos que represente correctamente locales, reseñas, categorías y ejecuciones
- dejar preparado el sistema para futuras fases de normalización y NLP

Este proyecto nace precisamente para cubrir esa necesidad fundacional.

---

## 3. Objetivo general

Desarrollar un **pipeline inteligente de adquisición y procesamiento de datos gastronómicos**, integrado en el ecosistema de Hidden Gems, capaz de obtener información desde múltiples fuentes, almacenarla de forma trazable, validarla, estructurarla y enriquecerla geográficamente para su explotación analítica posterior.

---

## 4. Objetivos específicos

### 4.1. Diseñar una arquitectura de adquisición reproducible
Definir una estructura clara para organizar el flujo de datos desde las fuentes externas hasta su persistencia en el sistema, separando responsabilidades y facilitando el reprocesado.

### 4.2. Integrar múltiples fuentes de datos
Trabajar con una estrategia multisource que combine fuentes dinámicas, abiertas y geográficas, minimizando la dependencia de un único proveedor.

### 4.3. Construir una capa raw trazable
Registrar ejecuciones, artefactos y orígenes de forma que cada dato pueda auditarse y relacionarse con su fuente y su proceso de carga.

### 4.4. Definir un modelo de datos sólido
Representar adecuadamente entidades clave como locales, referencias de fuente, reseñas, categorías, barrios, distritos y asignaciones geográficas.

### 4.5. Preparar la base para procesos de normalización
Dejar el sistema listo para futuras tareas de normalización de entidades, clasificación, detección de duplicados y unificación semántica.

### 4.6. Incorporar contexto geográfico útil
Vincular los locales a unidades territoriales oficiales, permitiendo que el análisis posterior se realice por barrio y no solo por coordenadas o listados genéricos.

### 4.7. Facilitar la futura explotación analítica
Construir una base que permita, en fases posteriores, incorporar NLP, extracción de señales textuales, detección de platos y mecanismos de scoring o ranking.

### 4.8. Documentar el sistema de forma profesional
Generar documentación clara y estructurada para que el proyecto sea entendible, reproducible y mantenible.

---

## 5. Objetivos de valor dentro de Hidden Gems

Más allá del valor técnico inmediato, este proyecto cumple un papel estratégico dentro del PI.

Permite:

- transformar una idea general en una infraestructura operativa real
- reducir el riesgo de improvisación en fases posteriores
- apoyar el desarrollo de verticales de adquisición independientes
- dar coherencia al modelo de datos desde el inicio
- sentar la base para decisiones futuras de calidad, normalización y análisis

En este sentido, el proyecto no solo persigue “tener una base de datos”, sino construir una **columna vertebral técnica** sobre la que Hidden Gems pueda crecer sin perder consistencia.

---

## 6. Criterio de éxito de esta fase

Se considerará que esta fase cumple sus objetivos si el proyecto logra:

- definir y documentar correctamente su arquitectura de adquisición
- disponer de una base de datos coherente con el modelo diseñado
- conectar y documentar las primeras verticales de datos
- garantizar trazabilidad entre fuentes, ejecuciones y registros
- dejar resuelto el marco estructural necesario para continuar con normalización, calidad y explotación analítica

El éxito, por tanto, no se mide por tener ya el producto final completo, sino por haber construido correctamente la **infraestructura de datos que lo hace viable**.