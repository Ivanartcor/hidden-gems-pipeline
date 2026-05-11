# 01. Visión general del proyecto

## 1. Introducción

Este proyecto consiste en el diseño e implementación de un **pipeline inteligente de adquisición, procesamiento, validación, enriquecimiento e integración IA de datos gastronómicos**, concebido como un módulo técnico reutilizable dentro del ecosistema de **Hidden Gems**.

Su propósito principal no es construir directamente una aplicación final de usuario, sino crear una base sólida de ingeniería de datos e inteligencia analítica que permita recopilar, estructurar, validar, enriquecer y explotar información procedente de múltiples fuentes.

En otras palabras, el valor principal del proyecto está en la **capacidad del sistema para transformar datos heterogéneos y dispersos en una base consistente, trazable y útil para análisis geográfico, textual y gastronómico**.

El repositorio ha evolucionado desde una primera infraestructura de adquisición hacia una plataforma técnica que ya incluye:

- integración de fuentes geográficas y gastronómicas;
- persistencia canónica en PostgreSQL/PostGIS;
- carga de reseñas operativas;
- generación de corpus NLP;
- prototipado IA sobre Yelp;
- piloto IA local sobre reviews reales de Google Places Sevilla;
- integración de resultados IA en PostgreSQL;
- vistas y scripts de consulta para explorar candidatos Hidden Gems;
- documentación técnica específica del piloto Sevilla.

---

## 2. Relación con Hidden Gems

Hidden Gems es el Proyecto Intermodular al que este repositorio da soporte técnico directo.

La idea general de Hidden Gems es descubrir valor gastronómico a nivel de barrio, priorizando el análisis de **platos destacados**, reseñas, señales textuales, localización y calidad del dato, en lugar de limitarse a construir un ranking genérico de restaurantes.

Dentro de ese marco, este proyecto desarrolla la base técnica necesaria para que esa visión sea viable:

- adquisición de datos desde múltiples fuentes;
- organización de la capa raw;
- trazabilidad de ejecuciones;
- validación y limpieza;
- normalización e integración;
- enriquecimiento geográfico;
- carga de reseñas operativas;
- preparación de corpus NLP;
- detección de platos;
- normalización de platos;
- análisis de sentimiento por mención;
- señales local-plato;
- ranking prototipo y ranking piloto local;
- consulta de resultados desde PostgreSQL.

Por tanto, este trabajo no debe entenderse como algo separado de Hidden Gems, sino como un **módulo estratégico del PI**, desarrollado con suficiente independencia como para poder ser implementado, probado, documentado y evolucionado de forma autónoma.

---

## 3. Enfoque del proyecto

El proyecto adopta una visión de **pipeline batch, modular, reproducible y trazable**, orientada a que cada etapa tenga una responsabilidad clara y pueda auditarse.

El flujo general del sistema puede resumirse así:

```text
fuentes externas
→ adquisición
→ almacenamiento raw
→ validación y limpieza
→ normalización
→ enriquecimiento geográfico
→ persistencia estructurada
→ reviews
→ corpus NLP / capa IA
→ detección de platos
→ normalización de platos
→ sentimiento por mención
→ señales agregadas
→ ranking Hidden Gems
→ vistas SQL / consulta demo
```

Este enfoque permite trabajar con un modelo de datos robusto, separar responsabilidades y evitar dependencias frágiles entre fuentes, lógica de negocio, IA y explotación analítica.

La arquitectura mantiene una separación clara entre:

```text
dato fuente
dato raw
dato staging
dato canónico
dato geográfico
dato textual
dato IA derivado
vistas de consulta
artefactos de demo
```

---

## 4. Fuentes de información contempladas

Para construir una base gastronómica útil y con contexto territorial suficiente, el proyecto parte de una estrategia **multisource**. Las fuentes seleccionadas cubren funciones distintas dentro del pipeline:

- **Sevilla Geo**, como fuente geográfica oficial de barrios y distritos;
- **OSM / Overpass**, como fuente abierta de puntos de interés gastronómicos;
- **Google Places**, como fuente dinámica de descubrimiento y enriquecimiento de locales;
- **Google Places Reviews**, como fuente de reseñas reales vinculadas a locales consolidados;
- **Yelp Open Dataset**, como dataset externo para corpus NLP, entrenamiento, evaluación y prototipo IA.

Esta combinación evita la dependencia exclusiva de una única fuente y refuerza la trazabilidad, la cobertura, la calidad y la capacidad de evolución del sistema.

---

## 5. Qué aporta este proyecto

Este proyecto aporta una base técnica imprescindible para el desarrollo posterior de Hidden Gems. Entre sus contribuciones principales se encuentran:

- una estructura formal para gestionar fuentes heterogéneas;
- un modelo trazable de ejecuciones y artefactos raw;
- una base de datos preparada para integrar locales, reseñas, categorías y geografía;
- una separación clara entre dato fuente, dato canónico y dato derivado;
- verticales operativas para Sevilla Geo, OSM / Overpass, Google Places y Google Reviews;
- una vertical Yelp capaz de construir corpus NLP gastronómico;
- un módulo IA experimental para detectar y normalizar platos;
- un flujo IA local sobre reviews reales de Sevilla;
- una capa IA persistida en PostgreSQL;
- loaders y checks reproducibles para cargar artefactos IA;
- vistas SQL y scripts demo para consultar candidatos Hidden Gems;
- documentación técnica del piloto Sevilla.

El resultado esperado no es solo “tener datos”, sino disponer de un sistema que permita **ingestarlos, entenderlos, validarlos, enriquecerlos y reutilizarlos con rigor técnico**.

---

## 6. Carácter del sistema

Este proyecto se sitúa entre varias disciplinas complementarias:

- **ingeniería de datos**, por su énfasis en adquisición, organización, trazabilidad y persistencia;
- **procesamiento de datos geográficos**, por la asignación y explotación territorial;
- **procesamiento textual**, por el tratamiento de reseñas y corpus NLP;
- **inteligencia artificial aplicada**, por la detección de platos, sentimiento por mención y ranking explicable;
- **automatización inteligente**, por la lógica de integración, validación y enriquecimiento del pipeline;
- **explotación analítica**, por las vistas SQL, scripts de consulta y futura capa de dashboard.

El sistema, por tanto, no es simplemente un ETL tradicional ni una aplicación analítica cerrada. Es una infraestructura técnica intermedia que hace posible el resto del proyecto Hidden Gems.

---

## 7. Estado actual de la fase

En el estado actual, el proyecto ya ha superado la fase puramente conceptual y cuenta con una base técnica funcional.

Se dispone de:

- esquema PostgreSQL/PostGIS creado;
- vertical Sevilla Geo implementada;
- vertical OSM / Overpass implementada;
- vertical Google Places Text Search implementada;
- vertical Google Places Reviews implementada;
- vertical Yelp Open Dataset implementada como corpus NLP;
- módulo IA experimental documentado;
- integración IA en PostgreSQL validada;
- vistas SQL de consulta IA;
- script demo para consultar ranking prototipo;
- piloto IA Sevilla con reviews reales de Google Places;
- ranking `sevilla_pilot` generado, cargado y validado;
- script demo específico para consultar Hidden Gems Sevilla.

La capa IA actual tiene dos usos diferenciados:

### Prototipo Yelp

Permite demostrar el flujo completo:

```text
reviews Yelp
→ detección de platos
→ normalización
→ sentimiento por mención
→ señales negocio-plato
→ ranking Hidden Gems prototipo
→ PostgreSQL
→ vistas de consulta
```

Este ranking se marca como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

### Piloto Sevilla

Permite validar el flujo sobre datos locales reales:

```text
Google Places Reviews Sevilla
→ export reviews para IA
→ detección de platos en español
→ normalización local de platos
→ sentimiento por mención
→ señales local-plato
→ ranking sevilla_pilot
→ PostgreSQL
→ consulta demo
```

Este piloto se ha cargado con:

```text
dish_catalog: 190
dish_alias: 243
dish_mention: 2.979
dish_mention_sentiment: 2.979
dish_place_signal: 2.212
hidden_gem_candidate: 256
hidden_gem_selected: 150
```

Y se ha validado sin errores ni warnings, quedando listo para consultas demo.

---

## 8. Límite importante del estado actual

Aunque la integración IA ya está validada, los rankings actuales no deben interpretarse como producto final definitivo.

El ranking Yelp es un prototipo externo:

```text
ranking_scope = yelp_prototype
```

El ranking Sevilla es un piloto local:

```text
artifact_ranking_scope = sevilla_pilot
```

Por la restricción actual del DDL, en base se conserva como:

```text
db_ranking_scope = other
```

pero mantiene `sevilla_pilot` en la configuración JSON del ranking.

Ningún ranking está marcado todavía como producción:

```text
is_production_ready = false
```

Esto significa que los resultados son válidos para demo técnica, análisis interno y validación del flujo, pero aún requieren revisión de calidad, dashboard, criterios de publicación y posible mejora IA antes de considerarse producción.

---

## 9. Resultado esperado de esta fase

El resultado esperado de esta fase es consolidar una base robusta sobre la que seguir construyendo Hidden Gems.

Eso implica:

- disponer de un esquema de base de datos bien definido;
- tener operativas las principales verticales de adquisición;
- establecer reglas de integración, validación y trazabilidad;
- disponer de una capa IA integrada en PostgreSQL;
- haber demostrado el flujo sobre corpus externo y sobre datos reales de Sevilla;
- organizar la documentación técnica del proyecto;
- dejar preparado el terreno para dashboard, API y producto final;
- abrir el camino a mejoras IA específicas en español/multilingüe.

En resumen, esta fase convierte una idea conceptual en una **plataforma técnica inicial, estructurada, validada y extensible**, desde la que Hidden Gems puede evolucionar con orden y consistencia.
