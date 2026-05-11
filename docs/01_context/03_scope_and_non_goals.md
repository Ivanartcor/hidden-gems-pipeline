# 03. Alcance y no objetivos

## 1. Introducción

Uno de los aspectos más importantes en este proyecto es definir con claridad qué se pretende construir en esta fase y qué queda fuera de alcance.

Dado que el trabajo forma parte del ecosistema de **Hidden Gems** y comparte relación con el Proyecto Intermodular, existe el riesgo de intentar abarcar demasiadas capas a la vez: adquisición, modelado, calidad, NLP, ranking, interfaz, API y explotación analítica completa.

Sin una delimitación explícita, eso llevaría a una solución dispersa, difícil de implementar y más difícil todavía de mantener.

Por ello, este documento fija el alcance real del proyecto y deja por escrito los **objetivos que sí forman parte de esta fase** y aquellos que, aun siendo relevantes para Hidden Gems en el futuro, **no se consideran producto final de esta fase**.

---

## 2. Alcance del proyecto

El alcance de esta fase se centra en construir la **base técnica de adquisición, estructuración, trazabilidad, integración IA y consulta piloto** para Hidden Gems.

En términos prácticos, esto incluye:

### 2.1. Diseño e implementación del pipeline de adquisición

Se desarrolla un pipeline modular y reproducible que permite obtener datos desde distintas fuentes y organizarlos de forma controlada.

### 2.2. Integración multisource

El sistema trabaja con varias fuentes complementarias, diferenciando claramente el origen de cada dato y permitiendo trazabilidad entre ellas.

### 2.3. Gestión de la capa raw

Se establece una estrategia de almacenamiento y trazabilidad del dato bruto, con registro de ejecuciones, artefactos y metadatos técnicos.

### 2.4. Modelo de datos estructurado

Se construye una base de datos coherente con el dominio del proyecto, incluyendo locales, reseñas, referencias de fuente, geografía, categorías, validación y capa IA derivada.

### 2.5. Base geográfica oficial

Se incorpora el soporte territorial necesario para trabajar a nivel de barrio y distrito, utilizando una referencia geográfica consistente.

### 2.6. Verticales de adquisición

Forman parte del alcance las verticales de:

- Sevilla Geo;
- OSM / Overpass;
- Google Places Text Search;
- Google Places Reviews;
- Yelp Open Dataset como corpus externo.

### 2.7. Preparación textual y corpus NLP

El proyecto incluye la construcción de corpus NLP a partir de Yelp y la preparación de reseñas operativas de Google para fases locales de IA.

### 2.8. Prototipo IA sobre Yelp

Forma parte del alcance una primera capa IA experimental para validar el flujo completo de:

```text
reseñas
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ agregación local-plato
→ ranking prototipo
```

Este prototipo permite validar arquitectura, modelo de datos, loaders, checks y vistas.

### 2.9. Piloto IA sobre reviews reales de Sevilla

También forma parte del alcance actual la aplicación del flujo IA a datos reales locales de Sevilla procedentes de Google Places Reviews.

Este piloto cubre:

```text
Google Reviews Sevilla
→ export para IA
→ exploración del corpus
→ detección de platos en español
→ normalización local de platos
→ sentimiento por mención
→ agregación local-plato
→ ranking sevilla_pilot
→ carga en PostgreSQL
→ check de integridad
→ consulta demo
```

El piloto genera resultados consultables, pero todavía no se considera producto final ni producción.

### 2.10. Integración IA en PostgreSQL

Forma parte del alcance la persistencia de resultados IA en PostgreSQL mediante tablas específicas, loaders, checks, vistas SQL y scripts de consulta.

### 2.11. Documentación técnica del sistema

Se documenta la arquitectura, el contexto, el modelo de datos, las fuentes, las verticales, el módulo IA, la integración IA, el piloto Sevilla y los próximos pasos del proyecto de forma ordenada y mantenible.

---

## 3. Qué sí hace este proyecto

En esta fase, el proyecto sí se compromete a:

- organizar el sistema de adquisición de datos;
- definir y materializar el esquema de base de datos;
- separar correctamente entidades canónicas, entidades fuente y entidades derivadas;
- registrar la trazabilidad de fuentes, ejecuciones y artefactos raw;
- estructurar la información geográfica oficial;
- integrar locales gastronómicos desde OSM y Google Places;
- cargar reseñas reales de Google cuando están vinculadas a locales consolidados;
- construir un corpus externo de Yelp para NLP;
- desarrollar una primera aproximación IA sobre Yelp;
- ejecutar un piloto IA sobre reseñas reales de Sevilla;
- cargar catálogo de platos, aliases, menciones, sentimientos, señales y ranking;
- validar integridad de la capa IA mediante checks;
- crear vistas y scripts demo para consulta;
- documentar el marco técnico y conceptual del proyecto.

En otras palabras, esta fase construye la **infraestructura de datos, trazabilidad, IA y explotación piloto** sobre la que se apoyarán el resto de capas de Hidden Gems.

---

## 4. Qué no hace este proyecto en esta fase

Para mantener un alcance realista, este trabajo **no pretende** desarrollar en esta fase los siguientes elementos como producto final cerrado.

### 4.1. Aplicación final de usuario

No se desarrolla todavía una plataforma completa orientada a usuario final ni una experiencia de producto cerrada.

### 4.2. Ranking productivo definitivo por barrio

Aunque existe un ranking prototipo sobre Yelp y un ranking piloto local sobre Sevilla, no se considera todavía un ranking productivo final.

El prototipo Yelp está marcado como:

```text
ranking_scope = yelp_prototype
```

El piloto Sevilla está identificado como:

```text
artifact_ranking_scope = sevilla_pilot
```

y en base se almacena con:

```text
db_ranking_scope = other
```

por una restricción actual del DDL.

Ambos se mantienen con:

```text
is_production_ready = false
```

El ranking productivo requerirá revisión de calidad, criterios finales de publicación, posible ajuste de scores, dashboard/API y validación adicional.

### 4.3. Sistema IA final entrenado para español

La capa IA Sevilla actual usa un enfoque híbrido de reglas, lexicones, normalización local y scoring. Es válida para piloto, pero no se considera aún una solución final entrenada, evaluada y optimizada con un modelo específico en español.

### 4.4. Recomendador personalizado

No se desarrolla todavía una lógica final de recomendación personalizada ni una capa de sugerencias complejas según usuario.

### 4.5. Tiempo real o streaming

El sistema se orienta a procesamiento por lotes. No se implementa una arquitectura de eventos, streaming o actualización en tiempo real.

### 4.6. Arquitectura distribuida pesada

No forma parte del alcance desplegar una solución basada en Spark, Kafka, microservicios complejos o infraestructura sobredimensionada para el estado actual del proyecto.

### 4.7. Dashboard definitivo

El dashboard se plantea como siguiente fase de explotación, pero todavía no forma parte del estado cerrado documentado en este bloque.

### 4.8. API pública o backend de producto

Aunque FastAPI se contempla como exposición futura, no forma parte de esta fase construir una API pública completa.

---

## 5. No objetivos explícitos

Además de lo anterior, se fijan como **no objetivos** de esta fase:

- competir con plataformas comerciales de búsqueda o reseñas;
- construir una base de datos exhaustiva de todo el ecosistema gastronómico;
- cubrir todas las ciudades o territorios posibles desde el inicio;
- resolver en esta fase todos los problemas de calidad y normalización semántica;
- automatizar completamente toda la inteligencia analítica de Hidden Gems;
- publicar reseñas completas procedentes de datasets externos;
- utilizar Yelp como fuente operativa real de Sevilla;
- considerar el ranking Yelp como resultado final de producto;
- considerar el ranking `sevilla_pilot` como producción sin revisión posterior;
- entrenar obligatoriamente modelos complejos antes de validar el dashboard y el uso real.

El proyecto no busca volumen por sí mismo, sino **estructura, consistencia, trazabilidad y capacidad de evolución**.

---

## 6. Delimitación respecto a Hidden Gems

Es importante entender que este proyecto forma parte del ecosistema de Hidden Gems, pero no agota su alcance.

Hidden Gems, como PI, tiene una ambición más amplia, que incluye posteriormente:

- explotación analítica avanzada;
- señalización de valor gastronómico real;
- interpretación textual más rica;
- ranking por barrio en Sevilla;
- API o capa de servicio;
- dashboard o interfaz de consulta;
- posible producto orientado a usuario;
- mejora de modelos IA en español o multilingües.

Esta fase, sin embargo, se centra en la **infraestructura de adquisición, modelado, trazabilidad, IA piloto y consulta técnica**, porque es la pieza que hace viables todas las siguientes.

Así, la relación con Hidden Gems queda delimitada de la siguiente forma:

- **Hidden Gems** aporta la visión global del sistema;
- **este repositorio** desarrolla la base técnica necesaria para que esa visión pueda sostenerse con datos reales, procesables y auditables.

---

## 7. Criterio de control del alcance

Para evitar desviaciones, toda decisión técnica futura debería responder a esta pregunta:

**¿Contribuye directamente a mejorar la adquisición, trazabilidad, estructuración, calidad, preparación IA o explotación controlada del dato para Hidden Gems?**

Si la respuesta es no, probablemente esa funcionalidad no pertenece a esta fase.

Este criterio ayuda a mantener el foco del proyecto y evita que el desarrollo se disperse en componentes atractivos, pero prematuros.

---

## 8. Conclusión

El alcance de esta fase está orientado a construir una base sólida de ingeniería de datos, integración IA y explotación piloto para Hidden Gems.

El proyecto sí aborda adquisición, estructuración, geografía, trazabilidad, documentación, corpus NLP, prototipo IA, piloto Sevilla e integración en PostgreSQL, pero no entra todavía en la construcción del producto final, del ranking productivo definitivo ni de la interfaz orientada a usuario.

Esta delimitación no reduce el valor del proyecto; al contrario, lo hace más realista, más defendible y más útil dentro del desarrollo global de Hidden Gems, ya que garantiza que las siguientes fases se apoyen sobre una infraestructura técnica coherente y mantenible.
