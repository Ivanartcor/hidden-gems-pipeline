# 01. Visión general del proyecto

## 1. Introducción

Este proyecto consiste en el diseño e implementación de un **pipeline inteligente de adquisición y procesamiento de datos gastronómicos**, concebido como un módulo técnico reutilizable dentro del ecosistema de **Hidden Gems**.

Su propósito no es construir una aplicación final de usuario, sino una base sólida de ingeniería de datos que permita recopilar, estructurar, validar y enriquecer información procedente de múltiples fuentes, dejándola preparada para su explotación analítica posterior.

En otras palabras, el valor principal del proyecto no está en la interfaz, sino en la **capacidad del sistema para transformar datos heterogéneos y dispersos en una base consistente, trazable y útil para análisis geográficos y textuales**.

---

## 2. Relación con Hidden Gems

Hidden Gems es el Proyecto Intermodular (PI) al que este trabajo da soporte técnico directo.

La idea general de Hidden Gems es descubrir valor gastronómico a nivel de barrio, priorizando el análisis de platos y señales derivadas de reseñas, categorías, localización y calidad del dato, en lugar de limitarse a construir un ranking genérico de restaurantes.

Dentro de ese marco, este proyecto se enfoca en una de las capas más importantes y fundacionales del sistema:

- adquisición de datos desde múltiples fuentes
- organización de la capa raw
- trazabilidad de ejecuciones
- validación y limpieza
- normalización e integración
- enriquecimiento geográfico
- preparación del dataset para fases posteriores de NLP y ranking

Por tanto, este trabajo no debe entenderse como algo separado de Hidden Gems, sino como un **módulo estratégico del PI**, desarrollado con suficiente independencia como para poder ser implementado, probado y documentado de forma autónoma.

---

## 3. Enfoque del proyecto

El proyecto adopta una visión de **pipeline batch, modular y reproducible**, orientada a que cada etapa tenga una responsabilidad clara y sea auditable.

El flujo general del sistema puede resumirse así:

**fuentes externas → adquisición → almacenamiento raw → validación y limpieza → normalización → enriquecimiento geográfico → persistencia estructurada**

Este enfoque permite trabajar con un modelo de datos robusto, separar claramente las responsabilidades de cada capa y evitar dependencias frágiles entre fuentes, lógica de negocio y explotación analítica.

---

## 4. Fuentes de información contempladas

Para construir una base de datos gastronómica útil y con contexto territorial suficiente, el proyecto parte de una estrategia **multisource**. Las fuentes seleccionadas cubren funciones distintas dentro del pipeline:

- **Google Places** como fuente dinámica principal de locales y reseñas recientes
- **OSM / Overpass** como fuente abierta para puntos de interés y enriquecimiento espacial
- **Barrios y distritos de Sevilla** como fuente geográfica oficial de referencia
- **Yelp Open Dataset** como dataset de apoyo para experimentación y validación de procesos textuales

Esta combinación permite evitar la dependencia exclusiva de una única fuente y refuerza la trazabilidad, la cobertura y la calidad del dato.

---

## 5. Qué aporta este proyecto

Este proyecto aporta una base técnica imprescindible para el desarrollo posterior de Hidden Gems. Entre sus contribuciones principales se encuentran:

- una estructura formal para gestionar fuentes heterogéneas
- un modelo trazable de ejecuciones y artefactos raw
- una base de datos preparada para integrar locales, reseñas, categorías y geografía
- una separación clara entre dato fuente, dato canónico y dato derivado
- un entorno adecuado para incorporar después procesos de NLP, extracción de señales gastronómicas y ranking por barrio

El resultado esperado no es solo “tener datos”, sino disponer de un sistema que permita **ingestarlos, entenderlos, validarlos y reutilizarlos con rigor técnico**.

---

## 6. Carácter del sistema

Este proyecto se sitúa entre varias disciplinas complementarias:

- **ingeniería de datos**, por su énfasis en adquisición, organización, trazabilidad y persistencia
- **procesamiento de datos geográficos**, por la asignación y explotación territorial
- **procesamiento textual**, por la futura preparación de reseñas y señales semánticas
- **automatización inteligente**, por el papel de la lógica de integración, validación y enriquecimiento dentro del pipeline

El sistema, por tanto, no es simplemente un ETL tradicional ni tampoco una aplicación analítica cerrada, sino una infraestructura técnica intermedia que hace posible el resto del proyecto.

---

## 7. Resultado esperado de esta fase

En esta fase, el objetivo es consolidar una base robusta sobre la que seguir construyendo. Eso implica:

- disponer de un esquema de base de datos bien definido
- tener operativas las primeras verticales de adquisición
- establecer las reglas de integración y validación
- organizar la documentación técnica del proyecto
- dejar preparado el terreno para las siguientes capas de normalización, calidad y explotación analítica

En resumen, esta fase convierte una idea conceptual en una **plataforma técnica inicial y estructurada**, desde la que Hidden Gems puede evolucionar con orden y consistencia.