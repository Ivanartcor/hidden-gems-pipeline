# 01. Contexto del proyecto


Este bloque reúne la documentación que explica el sentido del proyecto, su propósito, el problema que aborda y el marco en el que se desarrolla dentro del ecosistema **Hidden Gems**.

Aquí se presenta la visión general de **Hidden Gems Pipeline**, su relación con Hidden Gems como Proyecto Integrado, los objetivos técnicos del repositorio y los límites que separan la infraestructura ya construida de las fases futuras de producto, validación humana y producción real.

---

## Contenido

- [01. Visión general del proyecto](./01_project_overview.md)
- [02. Problema y objetivos](./02_problem_and_objectives.md)
- [03. Alcance y no objetivos](./03_scope_and_non_goals.md)

---

## Qué cubre esta sección

Esta sección cubre:

- visión general del proyecto;
- relación con Hidden Gems como Proyecto Integrado;
- problema que se quiere resolver;
- objetivos generales y específicos;
- alcance actual del repositorio;
- separación entre pipeline de datos, módulo IA, pilotos, dashboards y futuras capas de producto;
- límites actuales respecto a producción final, API pública y aplicación orientada a usuario;
- estado de cierre de la fase entregable del proyecto.

---

## Estado actual resumido

El proyecto ya no se encuentra únicamente en una fase de diseño o prototipo aislado. Actualmente dispone de una infraestructura funcional que cubre:

```text
fuentes externas
→ adquisición trazable
→ raw / staging
→ modelo canónico en PostgreSQL/PostGIS
→ reviews operativas
→ artefactos IA
→ detección de platos
→ normalización / entity linking
→ sentimiento por mención
→ señales local-plato
→ ranking Hidden Gems
→ comparación de versiones
→ export para dashboard
→ dashboard Streamlit
→ documentación técnica
```

El repositorio incluye tres líneas principales de trabajo relacionadas con IA y explotación analítica:

1. **Prototipo Yelp**: usado como corpus externo para validar arquitectura, entrenamiento, integración IA y carga controlada.
2. **Piloto Sevilla v1 con Google Places Reviews**: usado como primera prueba local real sobre reseñas de Sevilla, con ranking `sevilla_pilot` cargado y validado en PostgreSQL.
3. **Sevilla IA v2**: fase final de entrega académica basada en modelos entrenados, inferencia local, normalización con reranker, sentimiento ABSA por mención, señales local-plato, ranking IA v2, comparación v1/v2 y dashboard específico.

---

## Relación con el piloto Sevilla y la fase IA v2

La documentación de contexto debe leerse teniendo en cuenta dos bloques posteriores:

```text
docs/12_sevilla_ai_pilot/
docs/13_sevilla_ai_v2/
```

El bloque `docs/12_sevilla_ai_pilot/` documenta la ejecución piloto sobre datos reales de Sevilla:

```text
Google Places / Google Reviews Sevilla
→ export reviews para IA
→ notebooks 12–17
→ ranking sevilla_pilot
→ loader PostgreSQL
→ check de integridad
→ script de consulta demo
```

El bloque `docs/13_sevilla_ai_v2/` documenta la fase final de mejora IA:

```text
reviews Sevilla
→ NER de platos entrenado
→ combinación híbrido + NER
→ normalización/entity linking con reranker
→ sentimiento por mención / ABSA
→ señales place-dish v2
→ ranking Hidden Gems Sevilla v2
→ comparación v1 vs v2
→ export dashboard v2
→ dashboard Streamlit Sevilla IA v2
```

La fase Sevilla IA v2 representa el cierre del alcance entregable del proyecto en el contexto académico.

---

## Qué no cubre esta sección

Este bloque no entra en detalle sobre implementación, arquitectura técnica, modelo de datos, scripts operativos, verticales de fuente, notebooks IA, loaders, checks, dashboards o consultas SQL.

Esos aspectos se documentan en los bloques posteriores:

```text
docs/02_architecture/
docs/03_data_model/
docs/04_sources/
docs/05_verticals/
docs/08_operations/
docs/10_ai_module/
docs/11_ai_integration/
docs/12_sevilla_ai_pilot/
docs/13_sevilla_ai_v2/
```

---

## Nota de alcance

Los rankings disponibles deben entenderse como resultados técnicos y analíticos validados para demostración, no como producto comercial final.

Existen varios scopes relevantes:

```text
ranking_scope = yelp_prototype
```

para el prototipo IA basado en Yelp, y:

```text
artifact_ranking_scope = sevilla_pilot
```

para el piloto local sobre reseñas reales de Google Places Sevilla. Debido a una restricción actual del DDL, este último se guarda en base con `ranking_scope = other`, conservando `sevilla_pilot` dentro de la configuración JSON del ranking.

La fase Sevilla IA v2 genera un ranking experimental asistido por modelos entrenados y orientado a dashboard:

```text
sevilla_hidden_gems_ranking_v2
```

Ninguno de estos rankings se presenta como producción definitiva:

```text
is_production_ready = false
```

El proyecto queda cerrado como **MVP técnico avanzado / prototipo analítico funcional** para entrega académica. Las futuras fases de producción requerirían validación humana, mejora del catálogo, revisión de resultados, automatización adicional, estrategia de despliegue y posible exposición mediante API o producto final.


Realizado por Iván Arteaga Cordero
