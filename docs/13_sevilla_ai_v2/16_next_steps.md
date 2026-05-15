# 16. Próximos pasos tras la fase IA v2

## 1. Objetivo del documento

Este documento recoge el roadmap posterior a la fase IA v2 de Hidden Gems Sevilla.

La fase IA v2 deja completado el siguiente flujo:

```text
NER v1.2
→ Hybrid + NER candidates v2
→ Normalization reranker v1
→ ABSA sentiment v1
→ Place-dish signals v2
→ Hidden Gems ranking v2
→ Comparación v1 vs v2
→ Dashboard Sevilla IA v2
```

A partir de aquí, el proyecto puede avanzar en varias direcciones:

- consolidación documental;
- mejora de calidad de datos;
- validación humana;
- refinamiento de ranking;
- automatización;
- integración de modelos;
- preparación para una demo final.

---

## 2. Estado actual

La fase IA v2 queda cerrada con:

| Elemento | Estado |
|---|---|
| Modelo NER de platos | Entrenado y aplicado. |
| Capa Hybrid + NER v2 | Generada. |
| Modelo de normalización/reranker | Entrenado y aplicado. |
| Modelo ABSA por mención | Entrenado y aplicado. |
| Señales place-dish v2 | Generadas. |
| Ranking Hidden Gems v2 | Generado. |
| Comparación v1 vs v2 | Generada. |
| Export dashboard v2 | Generado. |
| Dashboard Streamlit v2 | Creado. |
| Documentación técnica v2 | En proceso/finalizada con esta carpeta. |

---

## 3. Corto plazo

Estos pasos deberían hacerse primero.

### 3.1 Actualizar README principal

Añadir al `README.md`:

- resumen de la fase IA v2;
- nuevos modelos entrenados;
- nuevos scripts;
- nueva carpeta de documentación;
- comando para ejecutar el dashboard v2;
- advertencia de que los modelos no se suben al repositorio;
- estado experimental del ranking.

Sección sugerida:

```text
## Sevilla IA v2: modelos entrenados y ranking experimental
```

---

### 3.2 Actualizar índice global de documentación

Si existe un índice general en `docs/`, añadir la nueva carpeta:

```text
docs/13_sevilla_ai_v2/
```

y enlazar:

```text
00_index.md
01_phase_overview.md
02_v2_pipeline_overview.md
...
16_next_steps.md
```

---

### 3.3 Revisar scripts y nombres finales

Verificar que los scripts finales tienen nombres consistentes:

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
scripts/run_sevilla_dish_normalization_reranker_v1.py
scripts/run_sevilla_mention_sentiment_absa_v1.py
scripts/build_sevilla_place_dish_signals_v2.py
scripts/build_sevilla_hidden_gems_ranking_v2.py
scripts/compare_sevilla_ranking_v1_vs_v2.py
scripts/export_sevilla_dashboard_data_v2.py
dashboard/streamlit_sevilla_v2_app.py
```

También conviene comprobar que no quedan archivos temporales tipo:

```text
*_PATCHED.py
*_fast_progress.py
*_uuid_safe.py
```

si ya se han integrado en el archivo final.

---

### 3.4 Verificar `requirements.txt`

Confirmar que contiene dependencias necesarias para:

- Streamlit;
- Plotly;
- Transformers;
- Torch;
- Pandas;
- SQLAlchemy;
- Psycopg2;
- Scikit-learn;
- Datasets, si se usan notebooks localmente.

Dependencias mínimas nuevas:

```text
streamlit
plotly
torch
transformers
datasets
scikit-learn
```

---

### 3.5 Añadir `models/` al `.gitignore`

Confirmar que el repositorio ignora:

```gitignore
models/
```

y, si procede:

```gitignore
data/artifacts/
data/raw/
*.safetensors
```

El código debe estar versionado, pero no los pesos de los modelos.

---

## 4. Validación de resultados

### 4.1 Revisión manual del top ranking

Revisar manualmente una muestra de candidatos:

```text
top_hidden_gem
strong_hidden_gem
v2_only de alto score
low quality de alto score
platos genéricos arriba
```

Objetivo:

- comprobar si el candidato tiene sentido;
- leer reseñas asociadas;
- detectar errores de normalización;
- detectar falsos positivos;
- identificar platos que deberían fusionarse o separarse.

---

### 4.2 Revisión de `no_candidate`

Revisar los platos que quedaron sin candidato en normalización.

Acciones:

- añadir nuevos platos al catálogo;
- añadir aliases;
- decidir si son ingredientes o platos;
- marcar términos ambiguos.

Ejemplos detectados:

```text
chuleta
cangrejo
anguila
parrillada
torreznos
canelones
gambón
centollo
cocochas
```

---

### 4.3 Revisión de baja confianza

Revisar:

```text
normalization_low_confidence
absa_low_confidence
linked_needs_review
experimental_ner_only
likely_fragment
```

Estos grupos no deben revisarse todos de golpe. Prioridad:

1. candidatos seleccionados;
2. high score;
3. top/strong tier;
4. platos nuevos o raros;
5. señales con pocas reviews.

---

## 5. Mejora del ranking

### 5.1 Penalización de platos genéricos

En una futura versión v2.1 se podría añadir una penalización suave para platos demasiado genéricos:

```text
hamburguesa
pizza
croqueta
montadito
churros
```

No se trata de eliminarlos, sino de evitar que dominen el top si hay alternativas más específicas.

Posible estrategia:

```text
generic_dish_penalty = 0.00 a 0.08
```

según el tipo de plato.

---

### 5.2 Bonus por especificidad gastronómica

Añadir bonus a platos más específicos:

```text
croquetas de cola de toro
solomillo al whisky
presa ibérica
cazón en adobo
pringá
torrija
rabo de toro
```

Posible estrategia:

```text
specificity_bonus = 0.00 a 0.08
```

---

### 5.3 Bonus territorial

Para reforzar el concepto de descubrimiento por barrio:

- aumentar ligeramente candidatos en barrios con poca presencia;
- evitar que el ranking se concentre en Casco Antiguo;
- exponer rankings locales por distrito/barrio;
- crear un score de rareza territorial.

---

### 5.4 Ajuste por popularidad del local

El concepto "hidden gem" no debería favorecer automáticamente locales muy populares.

Futura mejora:

```text
penalizar ligeramente locales con demasiadas reseñas o demasiada popularidad
bonus a locales con buena señal y menor presencia global
```

Esto requiere incorporar métricas adicionales del local.

---

## 6. Mejora de modelos

### 6.1 NER v1.3

Posibles mejoras:

- añadir más ejemplos manuales;
- reforzar negativos difíciles;
- mejorar entidades compuestas;
- separar mejor plato vs ingrediente;
- evaluar en reseñas nuevas no vistas;
- mejorar tratamiento de mayúsculas, errores y abreviaturas.

---

### 6.2 Normalización reranker v1.1

Posibles mejoras:

- ampliar catálogo y aliases;
- añadir hard negatives más difíciles;
- entrenar con más casos de `needs_new_dish`;
- evaluar con candidatos generados reales, no solo candidatos del dataset;
- probar un modelo multilingüe si aparecen reseñas en inglés.

---

### 6.3 ABSA v1.1

Posibles mejoras:

- revisar weak labels erróneas;
- añadir ejemplos de neutralidad real;
- añadir frases con contraste:
  ```text
  X bueno, Y malo
  ```
- añadir más negativos reales;
- mejorar ventanas de contexto;
- calibrar probabilidades.

---

## 7. Automatización de modelos

Actualmente los modelos se guardan localmente en:

```text
models/
```

Futura mejora:

- crear descarga automática desde Google Drive;
- validar checksum;
- mostrar mensaje claro si falta el modelo;
- permitir modo `--skip-model` o fallback híbrido;
- documentar cómo colocar los modelos.

Ejemplo deseado:

```powershell
python -m scripts.download_models `
  --model sevilla_mention_sentiment_absa_beto_v1
```

---

## 8. Mejora del dashboard

### 8.1 Dashboard v2

Mejoras posibles:

- añadir selector v1/v2 en una misma interfaz;
- añadir vista "solo candidatos con evidencia fuerte";
- añadir vista "candidatos a revisar";
- añadir mapa con clusters;
- añadir ranking por proximidad;
- permitir exportar filtros a CSV;
- añadir panel de explicación de modelo por candidato;
- mejorar fichas de reseñas.

---

### 8.2 Dashboard comparativo

Crear una pestaña o dashboard específico para:

```text
v1 vs v2
```

Con:

- scatter score v1 vs score v2;
- Sankey de cambio de tier;
- mapa de candidatos nuevos v2;
- top subidas y bajadas;
- candidatos que desaparecen.

---

### 8.3 Dashboard de calidad

Crear una vista específica para revisión interna:

- low confidence;
- no candidate;
- likely fragment;
- experimental NER-only;
- weak evidence;
- low quality;
- negativos fuertes;
- contradicciones.

---

## 9. Integración con pipeline

A medio plazo, los scripts IA v2 deberían integrarse en un flujo reproducible.

Posible orquestación:

```text
run_ai_v2_pipeline.py
```

Con pasos:

```text
1. Ejecutar NER
2. Limpiar NER
3. Construir Hybrid + NER
4. Normalizar
5. Predecir sentimiento
6. Agregar señales
7. Construir ranking
8. Comparar v1/v2
9. Exportar dashboard
```

Y opciones:

```powershell
--skip-ner
--skip-normalization
--skip-sentiment
--only-dashboard-export
--strict
```

---

## 10. Integración con base de datos

Actualmente gran parte de IA v2 trabaja sobre artefactos.

Futuro paso:

- diseñar tablas para resultados IA v2;
- persistir `dish_mention`;
- persistir `place_dish_signal`;
- persistir `hidden_gem_ranking`;
- mantener versionado de ranking;
- distinguir `ranking_scope` y `ranking_version`.

Tablas candidatas:

```text
ai_dish_mention
ai_dish_normalization
ai_mention_sentiment
ai_place_dish_signal
ai_hidden_gem_ranking
```

---

## 11. Evaluación humana

Para pasar de experimental a preproducción, haría una evaluación humana sencilla.

### Propuesta

Seleccionar:

```text
50 candidatos top/strong
50 candidatos promising
30 candidatos exploratory
30 candidatos v2_only
20 candidatos low confidence
```

Evaluar manualmente:

| Pregunta | Valores |
|---|---|
| ¿El plato está bien detectado? | sí/no/dudoso |
| ¿La normalización es correcta? | sí/no/dudoso |
| ¿El sentimiento es correcto? | sí/no/dudoso |
| ¿El candidato parece un hidden gem? | sí/no/dudoso |
| ¿Debe estar en el dashboard público? | sí/no |

Esto permitiría calcular una métrica de calidad humana.

---

## 12. Preparación para memoria técnica

La fase IA v2 debe resumirse en la memoria técnica con:

- problema inicial;
- motivación del salto a modelos;
- datasets;
- entrenamiento;
- métricas;
- inferencia;
- ranking;
- dashboard;
- limitaciones;
- próximos pasos.

Estructura posible para memoria:

```text
1. Evolución del pipeline hacia IA v2
2. Modelos entrenados
3. Integración de modelos en inferencia local
4. Construcción de señales place-dish
5. Ranking Hidden Gems v2
6. Comparación v1 vs v2
7. Dashboard de explotación
8. Limitaciones y trabajo futuro
```

---

## 13. Prioridad recomendada

Orden recomendado de ejecución tras cerrar esta documentación:

```text
1. Actualizar README principal.
2. Actualizar índice global de docs.
3. Limpiar scripts parcheados y dejar nombres finales.
4. Verificar requirements.txt y .gitignore.
5. Ejecutar dashboard v2 y capturar capturas para memoria.
6. Revisar top 30 manualmente.
7. Preparar sección de memoria técnica.
8. Preparar presentación/demo.
```

---

## 14. Roadmap por fases

### Fase inmediata

```text
Documentación + limpieza + demo dashboard
```

### Fase siguiente

```text
Validación manual + refinamiento de ranking v2.1
```

### Fase posterior

```text
Automatización completa + persistencia en base de datos
```

### Fase futura

```text
Escalado a más ciudades / verticales / fuentes
```

---

## 15. Conclusión

La fase IA v2 deja el proyecto en un punto sólido:

```text
ya no solo existe un pipeline de datos,
sino una cadena completa de modelos entrenados,
ranking interpretable y dashboard funcional.
```

El siguiente objetivo no debería ser añadir más complejidad inmediatamente, sino consolidar:

- documentación;
- reproducibilidad;
- validación;
- claridad de presentación;
- limpieza de scripts;
- dashboard final.

Con eso, Hidden Gems queda muy bien preparado para defensa técnica, demo y futuras iteraciones.
