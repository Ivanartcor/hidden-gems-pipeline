# 03. Modelo de datos

Este bloque documenta el modelo de datos de **Hidden Gems Pipeline**, incluyendo el core operacional, la geografía, la clasificación, la trazabilidad, la calidad y la capa IA derivada.

El modelo está preparado para soportar tres niveles de madurez:

1. **Core operacional**: locales, referencias fuente, reseñas, geografía, categorías, trazabilidad y calidad.
2. **IA persistida en PostgreSQL**: prototipo Yelp y piloto Sevilla v1 cargados en tablas IA.
3. **Sevilla IA v2 en artefactos reproducibles**: modelos entrenados, inferencia local, ranking v2, comparación v1/v2, export y dashboard.

---

## Contenido

- [20. Visión general del modelo de datos](./20_data_model_overview.md)
- [21. Esquema de base de datos](./21_database_schema.md)
- [22. Catálogo de entidades: núcleo de negocio](./22_business_core_entities.md)
- [23. Catálogo de entidades: geografía](./23_geography_entities.md)
- [24. Catálogo de entidades: clasificación](./24_classification_entities.md)
- [25. Catálogo de entidades: gobierno y trazabilidad](./25_governance_traceability_entities.md)
- [26. Catálogo de entidades: calidad](./26_quality_entities.md)

---

## Lectura recomendada

Para entender el modelo completo se recomienda este orden:

```text
20_data_model_overview.md
→ 21_database_schema.md
→ 22_business_core_entities.md
→ 23_geography_entities.md
→ 24_classification_entities.md
→ 25_governance_traceability_entities.md
→ 26_quality_entities.md
```

---

## Relación con IA v2

La fase Sevilla IA v2 no invalida el modelo de datos anterior. Al contrario, lo confirma:

```text
place + review + neighborhood
→ menciones de platos
→ normalización/entity linking
→ sentimiento ABSA
→ señales place-dish
→ ranking Hidden Gems v2
→ dashboard Sevilla IA v2
```

La principal diferencia es que v2 se ha conservado como **capa de artefactos reproducibles** en lugar de insertarse todavía de forma definitiva en PostgreSQL. Esto permite entregar el proyecto como MVP técnico avanzado sin forzar un estado productivo prematuro.

---

## Estado de producción

Ningún ranking actual se marca como producción:

```text
is_production_ready = false
```

Esto aplica tanto al prototipo Yelp, como al piloto Sevilla v1 y al ranking Sevilla IA v2. La promoción a producción queda como fase futura y requerirá validación humana, ajuste de criterios, posible ampliación de constraints de ranking scope y revisión de calidad.
