# 01. Contexto del proyecto

Este bloque reúne la documentación que explica el sentido del proyecto, su propósito, el problema que aborda y el marco en el que se desarrolla dentro del ecosistema **Hidden Gems**.

Aquí se presenta la visión general de **Hidden Gems Pipeline**, su relación con Hidden Gems como Proyecto Intermodular, los objetivos técnicos del repositorio y los límites que separan la infraestructura ya construida de las fases futuras de producto, explotación y producción real.

---

## Contenido

- [01. Visión general del proyecto](./01_project_overview.md)
- [02. Problema y objetivos](./02_problem_and_objectives.md)
- [03. Alcance y no objetivos](./03_scope_and_non_goals.md)

---

## Qué cubre esta sección

Esta sección cubre:

- visión general del proyecto;
- relación con Hidden Gems como PI;
- problema que se quiere resolver;
- objetivos generales y específicos;
- alcance actual del repositorio;
- separación entre pipeline de datos, módulo IA, piloto Sevilla y futuras capas de producto;
- límites actuales respecto a producción final, API pública, dashboard definitivo y aplicación orientada a usuario.

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
→ normalización
→ sentimiento por mención
→ señales local-plato
→ ranking Hidden Gems piloto
→ carga en PostgreSQL
→ vistas SQL
→ scripts demo de consulta
```

El repositorio incluye dos grandes líneas IA diferenciadas:

1. **Prototipo Yelp**: usado como corpus externo para validar arquitectura, entrenamiento, integración IA y carga controlada.
2. **Piloto Sevilla con Google Places Reviews**: usado como primera prueba local real sobre reseñas de Sevilla, con ranking `sevilla_pilot` cargado y validado en PostgreSQL.

---

## Relación con el piloto Sevilla

La documentación de contexto debe leerse teniendo en cuenta que ya existe una fase específica dedicada al piloto Sevilla:

```text
docs/12_sevilla_ai_pilot/
```

Ese bloque documenta la ejecución completa sobre datos reales de Sevilla:

```text
Google Places / Google Reviews Sevilla
→ export reviews para IA
→ notebooks 12–17
→ ranking sevilla_pilot
→ loader PostgreSQL
→ check de integridad
→ script de consulta demo
```

Este piloto no sustituye todavía a un producto final, pero sí demuestra que el flujo completo de Hidden Gems puede operar sobre datos locales reales.

---

## Qué no cubre esta sección

Este bloque no entra en detalle sobre implementación, arquitectura técnica, modelo de datos, scripts operativos, verticales de fuente, notebooks IA, loaders, checks o consultas SQL.

Esos aspectos se documentan en los bloques posteriores:

```text
docs/02_architecture/
docs/03_data_model/
docs/04_sources/
docs/05_verticals/
docs/10_ai_module/
docs/11_ai_integration/
docs/12_sevilla_ai_pilot/
```

---

## Nota de alcance

El ranking disponible actualmente debe entenderse como **piloto validado**, no como ranking productivo final.

Existen dos scopes relevantes:

```text
ranking_scope = yelp_prototype
```

para el prototipo IA basado en Yelp, y:

```text
artifact_ranking_scope = sevilla_pilot
```

para el piloto local sobre reseñas reales de Google Places Sevilla. Debido a una restricción actual del DDL, este último se guarda en base con `ranking_scope = other`, conservando `sevilla_pilot` dentro de la configuración JSON del ranking.

Ninguno de estos rankings está marcado aún como producción:

```text
is_production_ready = false
```

El siguiente objetivo de producto será consolidar una capa de consulta/dashboard, revisar resultados con uso real y decidir después si se mejora la IA con modelos específicos en español o multilingües.
