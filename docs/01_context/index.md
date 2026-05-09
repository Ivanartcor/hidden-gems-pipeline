# 01. Contexto del proyecto

Este bloque reúne la documentación que explica el sentido del proyecto, su propósito, el problema que aborda y el marco en el que se desarrolla.

Aquí se presenta la visión general de **Hidden Gems Pipeline**, su relación con **Hidden Gems** como Proyecto Intermodular, los objetivos técnicos del repositorio y los límites que separan la infraestructura ya construida de las fases futuras de producto, explotación y producción real.

## Contenido

- [01. Visión general del proyecto](./01_project_overview.md)
- [02. Problema y objetivos](./02_problem_and_objectives.md)
- [03. Alcance y no objetivos](./03_scope_and_non_goals.md)

## Qué cubre esta sección

- visión general del proyecto;
- relación con Hidden Gems como PI;
- problema que se quiere resolver;
- objetivos generales y específicos;
- alcance actual del repositorio;
- separación entre pipeline de datos, módulo IA prototipo y futuras capas de producto;
- límites actuales respecto a ranking productivo por barrio, API, dashboard y aplicación final.

## Qué no cubre esta sección

Este bloque no entra en detalle sobre implementación, arquitectura técnica, modelo de datos, scripts operativos, verticales de fuente o integración IA en PostgreSQL. Esos aspectos se documentan en los bloques posteriores de `docs/`.

Referencias principales:

```text
docs/02_architecture/
docs/03_data_model/
docs/04_sources/
docs/05_verticals/
docs/10_ai_module/
docs/11_ai_integration/
```

## Nota de estado

La documentación de contexto describe el proyecto en su estado actual: una infraestructura de datos ya operativa, con verticales de adquisición implementadas y una primera capa IA integrada como prototipo sobre Yelp Open Dataset.

El ranking disponible actualmente debe entenderse como:

```text
ranking_scope = yelp_prototype
```

No como ranking productivo final de Sevilla por barrio.
