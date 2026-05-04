# 03. Alcance y no objetivos

## 1. Introducción

Uno de los aspectos más importantes en este proyecto es definir con claridad qué se pretende construir en esta fase y qué queda fuera de alcance.

Dado que el trabajo forma parte del ecosistema de **Hidden Gems** y comparte relación con el Proyecto Intermodular, existe el riesgo de intentar abarcar demasiadas capas a la vez: adquisición, modelado, calidad, NLP, ranking, interfaz y explotación analítica completa. Sin una delimitación explícita, eso llevaría a una solución dispersa, difícil de implementar y más difícil todavía de mantener.

Por ello, este documento fija el alcance real del proyecto y deja por escrito los **objetivos que sí forman parte de esta fase** y aquellos que, aun siendo relevantes para Hidden Gems en el futuro, **no se desarrollarán aquí**.

---

## 2. Alcance del proyecto

El alcance de esta fase se centra en construir la **base técnica de adquisición y estructuración del dato** para Hidden Gems.

En términos prácticos, esto incluye:

### 2.1. Diseño e implementación del pipeline de adquisición
Se desarrollará un pipeline modular y reproducible que permita obtener datos desde distintas fuentes y organizarlos de forma controlada.

### 2.2. Integración multisource
El sistema se preparará para trabajar con varias fuentes complementarias, diferenciando claramente el origen de cada dato y permitiendo trazabilidad entre ellas.

### 2.3. Gestión de la capa raw
Se establecerá una estrategia de almacenamiento y trazabilidad del dato bruto, con registro de ejecuciones, artefactos y metadatos técnicos.

### 2.4. Modelo de datos estructurado
Se construirá una base de datos coherente con el dominio del proyecto, incluyendo locales, reseñas, referencias de fuente, geografía, categorías y validación.

### 2.5. Base geográfica oficial
Se incorporará el soporte territorial necesario para trabajar a nivel de barrio y distrito, utilizando una referencia geográfica consistente.

### 2.6. Preparación para normalización y calidad
La arquitectura quedará preparada para incorporar procesos posteriores de limpieza avanzada, integración semántica, control de calidad y enriquecimiento.

### 2.7. Documentación técnica del sistema
Se documentará la arquitectura, el contexto, el modelo de datos, las fuentes, las verticales y el roadmap del proyecto de forma ordenada y mantenible.

---

## 3. Qué sí hace este proyecto

En esta fase, el proyecto sí se compromete a:

- organizar el sistema de adquisición de datos
- definir y materializar el esquema de base de datos
- separar correctamente entidades canónicas, entidades fuente y entidades derivadas
- registrar la trazabilidad de fuentes, ejecuciones y artefactos raw
- estructurar la información geográfica oficial
- preparar el sistema para explotación posterior
- documentar el marco técnico y conceptual del proyecto

En otras palabras, esta fase construye la **infraestructura de datos y documentación base** sobre la que se apoyarán el resto de capas de Hidden Gems.

---

## 4. Qué no hace este proyecto en esta fase

Para mantener un alcance realista, este trabajo **no pretende** desarrollar en esta fase los siguientes elementos:

### 4.1. Aplicación final de usuario
No se desarrollará una plataforma completa orientada a usuario final, ni una interfaz de exploración plenamente funcional.

### 4.2. Sistema de ranking definitivo
Aunque el proyecto está diseñado para preparar el terreno del ranking por barrio, no se implementará aquí el motor analítico final de scoring completo.

### 4.3. Extracción avanzada de platos
La detección específica de platos, entidades gastronómicas o relaciones semánticas profundas se deja para una fase posterior.

### 4.4. Sentimiento y NLP completo
La base textual quedará preparada, pero no se construirá aún un sistema completo de análisis de sentimiento, embeddings o modelos avanzados de lenguaje.

### 4.5. Recomendador final
No se desarrollará todavía una lógica final de recomendación personalizada ni una capa de sugerencias complejas.

### 4.6. Tiempo real o streaming
El sistema se orienta a procesamiento por lotes. No se implementará una arquitectura de eventos, streaming o actualización en tiempo real.

### 4.7. Arquitectura distribuida pesada
No forma parte del alcance desplegar una solución basada en Spark, Kafka, microservicios complejos o infraestructura sobredimensionada para el estado actual del proyecto.

### 4.8. Ecosistema completo de explotación
No se incluirán todavía dashboards completos, cuadros de mando definitivos ni un entorno cerrado de explotación analítica para terceros.

---

## 5. No objetivos explícitos

Además de lo anterior, se fijan como **no objetivos** de esta fase:

- competir con plataformas comerciales de búsqueda o reseñas
- construir una base de datos exhaustiva de todo el ecosistema gastronómico
- cubrir todas las ciudades o territorios posibles desde el inicio
- resolver en esta fase todos los problemas de calidad y normalización semántica
- automatizar completamente toda la inteligencia analítica de Hidden Gems

El proyecto no busca volumen por sí mismo, sino **estructura, consistencia y capacidad de evolución**.

---

## 6. Delimitación respecto a Hidden Gems

Es importante entender que este proyecto forma parte del ecosistema de Hidden Gems, pero no agota su alcance.

Hidden Gems, como PI, tiene una ambición más amplia, que incluye posteriormente:

- explotación analítica avanzada
- señalización de valor gastronómico
- interpretación textual más rica
- posible ranking por barrio
- y, en fases futuras, componentes de presentación o consulta más orientados a usuario

Esta fase, sin embargo, se centra en la **infraestructura de adquisición y modelado del dato**, porque es la pieza que hace viables todas las siguientes.

Así, la relación con Hidden Gems queda delimitada de la siguiente forma:

- **Hidden Gems** aporta la visión global del sistema
- **este proyecto** desarrolla la base técnica necesaria para que esa visión pueda sostenerse con datos reales y procesables

---

## 7. Criterio de control del alcance

Para evitar desviaciones, toda decisión técnica futura debería responder a esta pregunta:

**¿Contribuye directamente a mejorar la adquisición, trazabilidad, estructuración o preparación del dato para Hidden Gems?**

Si la respuesta es no, probablemente esa funcionalidad no pertenece a esta fase.

Este criterio ayuda a mantener el foco del proyecto y evita que el desarrollo se disperse en componentes atractivos, pero prematuros.

---

## 8. Conclusión

El alcance de esta fase está claramente orientado a construir una base sólida de ingeniería de datos para Hidden Gems. El proyecto sí aborda adquisición, estructuración, geografía, trazabilidad y documentación, pero no entra todavía en la construcción de la capa analítica completa ni en el producto final orientado a usuario.

Esta delimitación no reduce el valor del proyecto; al contrario, lo hace más realista, más defendible y más útil dentro del desarrollo global de Hidden Gems, ya que garantiza que las siguientes fases se apoyen sobre una infraestructura técnica coherente y mantenible.