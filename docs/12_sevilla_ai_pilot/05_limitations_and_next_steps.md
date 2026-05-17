# 05. Limitaciones y próximos pasos del piloto Sevilla IA


## 1. Objetivo

Este documento recoge las principales limitaciones del piloto IA Sevilla y propone los siguientes pasos para evolucionarlo desde un prototipo validado hacia una versión más robusta, consultable y eventualmente productiva.

El piloto actual ya demuestra que Hidden Gems puede detectar platos concretos, asociarlos a locales y barrios, calcular señales de sentimiento y generar un ranking explicable. Sin embargo, todavía no debe interpretarse como un ranking definitivo de producción.

## 2. Estado actual resumido

El piloto Sevilla IA se encuentra en estado:

```text
prototipo end-to-end completado, cargado y validado en PostgreSQL
```

Resumen final:

| Área | Estado |
|---|---|
| Datos reales Google Places | Completado |
| Exportación JSONL IA | Completada |
| Notebooks IA 12–17 | Completados |
| Ranking `sevilla_pilot` | Generado |
| Carga PostgreSQL | Completada |
| Check PostgreSQL | Sin errores ni warnings |
| Consulta demo | Funcionando |
| Producción | No activada |

El ranking queda explícitamente marcado como:

```text
is_production_ready = false
```

## 3. Limitaciones de datos

### 3.1. Límite de reseñas por local

Google Places no proporciona un histórico completo de reseñas por local en este flujo. En la práctica, cada local ofrece una muestra limitada de reseñas.

Esto implica que muchos pares `local + plato` tienen poca evidencia:

- 2 menciones;
- 2 reviews;
- 3 menciones;
- 3 reviews.

Por este motivo, el ranking debe interpretarse como una señal exploratoria.

### 3.2. Sesgo de reseñas positivas

Las reseñas de Google tienden a estar muy concentradas en ratings altos. Esto se refleja en la distribución del sentimiento:

| Sentimiento | Menciones |
|---|---:|
| Positive | 2.395 |
| Negative | 388 |
| Neutral | 196 |

Este sesgo puede favorecer platos mencionados en reviews positivas aunque la valoración local específica sea débil.

El pipeline mitiga parcialmente esto mediante:

- sentimiento local por contexto;
- penalización por fallback;
- penalización por ruido;
- tier de evidencia;
- score suavizado.

Aun así, sigue siendo una limitación importante.

### 3.3. Cobertura desigual por barrio

Aunque el corpus cubre 96 barrios y el ranking seleccionado cubre 55 barrios, la densidad de información no es uniforme.

Algunos distritos tienen más seleccionados:

| Distrito | Seleccionados |
|---|---:|
| Casco Antiguo | 44 |
| Cerro - Amate | 15 |
| Sur | 14 |
| Este - Alcosa - Torreblanca | 14 |
| Nervión | 13 |
| San Pablo - Santa Justa | 12 |
| Macarena | 10 |
| Triana | 10 |
| Norte | 9 |
| Bellavista - La Palmera | 7 |
| Los Remedios | 2 |

Esto puede deberse a:

- densidad real de locales;
- diferencias en volumen de reviews;
- queries usadas en Google Places;
- barrios con menor presencia gastronómica;
- límites de resultados por llamada.

### 3.4. Dependencia de una única fuente operativa

El piloto Sevilla se basa en Google Places como fuente principal para datos reales.

Esto aporta valor por disponibilidad y geolocalización, pero también limita:

- número de reseñas accesibles;
- diversidad de opiniones;
- profundidad histórica;
- control sobre orden y selección de reseñas;
- disponibilidad de textos por idioma.

A futuro sería recomendable combinar fuentes.

## 4. Limitaciones del enfoque IA actual

### 4.1. Detección basada en reglas y lexicones

La detección de platos en español se ha construido con un enfoque híbrido, principalmente basado en:

- lexicón gastronómico;
- reglas regex;
- patrones de platos compuestos;
- clasificación por tipos;
- contexto gastronómico.

Ventajas:

- es explicable;
- es controlable;
- funciona bien para un piloto;
- no requiere GPU ni entrenamiento;
- permite depuración manual.

Limitaciones:

- puede perder platos no incluidos en el lexicón;
- puede confundir ingredientes con platos;
- puede no captar expresiones complejas;
- requiere mantenimiento manual;
- no generaliza igual que un modelo entrenado.

### 4.2. Normalización aún mejorable

El catálogo local Sevilla contiene 190 platos/candidatos, con 181 elegibles para ranking.

Aunque el resultado es sólido, todavía hay casos mejorables:

```text
atún → podría diferenciar atún rojo, tataki de atún, tartar de atún
pulpo → podría diferenciar pulpo a la brasa, pulpo frito, pulpo a la gallega
bacalao → podría diferenciar bacalao frito, pisto con bacalao, pavía
hamburguesa → podría diferenciar smash burger, burger de buey, etc.
arroz → podría diferenciar arroz negro, arroz meloso, risotto, paella
```

La v1 prioriza estabilidad y trazabilidad frente a granularidad extrema.

### 4.3. Sentimiento por mención con fallback

El sentimiento por mención usa dos fuentes:

```text
local_context_primary
review_prior_fallback
```

Distribución:

| Método | Menciones |
|---|---:|
| `local_context_primary` | 1.590 |
| `review_prior_fallback` | 1.389 |

Casi la mitad de las menciones dependen del rating de la review porque el contexto local no contenía una señal clara.

Esto es útil para no perder cobertura, pero introduce ruido. Por eso los candidatos con mucho fallback deben interpretarse con más cautela.

### 4.4. Revisión manual pendiente

Aunque se revisó una muestra y los checks son correctos, todavía conviene realizar revisión manual más amplia de:

- `top_hidden_gem`;
- `strong_hidden_gem`;
- una muestra de `promising_hidden_gem`;
- candidatos con baja evidencia;
- candidatos con mucho fallback;
- candidatos con platos ambiguos;
- candidatos de barrios con poca cobertura.

El archivo de revisión principal es:

```text
data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_manual_review_v1.csv
```

## 5. Limitaciones del ranking

### 5.1. Score no equivalente a verdad absoluta

El score `hidden_gem_score_v1` es una métrica compuesta. Combina:

- calidad local del plato;
- evidencia;
- confianza;
- hiddenness;
- unicidad barrial;
- penalizaciones por ruido;
- penalizaciones por negativos.

No debe interpretarse como una nota gastronómica absoluta, sino como una prioridad de candidato para exploración.

### 5.2. Candidatos con evidencia baja

El ranking selecciona también candidatos `exploratory_hidden_gem` y `promising_hidden_gem` con evidencia limitada.

Esto es intencional: el objetivo del piloto es descubrir posibles joyas ocultas, no solo confirmar locales muy populares.

Sin embargo, para producción habría que exigir umbrales más estrictos o validación externa.

### 5.3. `ranking_scope` temporal en base de datos

Por restricción actual del DDL, el ranking se guarda en base como:

```text
db_ranking_scope = other
```

Y conserva el scope real en configuración:

```text
artifact_ranking_scope = sevilla_pilot
```

Esto es funcional, pero sería más limpio añadir `sevilla_pilot` como valor nativo del dominio de `ranking_scope`.

## 6. Próximos pasos técnicos

### 6.1. Documentación final del piloto

Completar y mantener este bloque documental:

```text
docs/12_sevilla_ai_pilot/
├── 00_index.md
├── 01_google_places_data_collection.md
├── 02_ai_notebook_pipeline.md
├── 03_database_loading_and_validation.md
├── 04_query_demo_and_results.md
└── 05_limitations_and_next_steps.md
```

También conviene actualizar el `README.md` principal para mencionar que ya existe un piloto IA Sevilla end-to-end.

### 6.2. Añadir `sevilla_pilot` al DDL

Mejora recomendada:

```text
Actualizar restricción de hidden_gem_candidate.ranking_scope
para incluir sevilla_pilot como valor nativo.
```

Ventaja:

- consultas más limpias;
- menor dependencia de JSON config;
- semántica explícita en base de datos.

### 6.3. Crear vistas específicas Sevilla pilot

Aunque ya existen vistas IA generales, puede ser útil crear vistas especializadas:

```text
vw_sevilla_pilot_hidden_gems
vw_sevilla_pilot_top_by_district
vw_sevilla_pilot_top_by_neighborhood
vw_sevilla_pilot_top_by_dish
vw_sevilla_pilot_candidate_evidence
```

Estas vistas simplificarían el consumo desde API o dashboard.

### 6.4. Mejorar el script demo

El script `query_sevilla_hidden_gems_demo.py` ya funciona, pero podría ampliarse con:

- export HTML simple;
- filtros por tier;
- filtros por familia de plato;
- filtros por score mínimo;
- opción `--only-selected`;
- opción `--include-evidence`;
- salida JSON para API;
- ejemplos de menciones por candidato.

### 6.5. Crear endpoints API

Una evolución natural sería exponer endpoints como:

```text
GET /hidden-gems/sevilla
GET /hidden-gems/sevilla/districts/{district}
GET /hidden-gems/sevilla/neighborhoods/{neighborhood}
GET /hidden-gems/sevilla/dishes/{dish}
GET /hidden-gems/sevilla/places/{place_id}
```

Respuesta esperada:

```json
{
  "place_name": "Pizzería San Pablo",
  "dish": "pizza",
  "neighborhood": "SAN PABLO D Y E",
  "district": "San Pablo - Santa Justa",
  "score": 80.1471,
  "tier": "top_hidden_gem",
  "explanation": "..."
}
```

### 6.6. Dashboard inicial

Otra evolución sería un dashboard sencillo con:

- top global;
- filtro por distrito;
- filtro por barrio;
- filtro por plato;
- mapa de locales;
- tabla de explicaciones;
- distribución de platos por zona;
- detalles de evidencia.

Podría construirse con:

- Power BI;
- Streamlit;
- Angular;
- Superset;
- una API propia sobre PostgreSQL.

## 7. Próximos pasos de IA

### 7.1. Revisión manual sistemática

Crear un proceso de revisión manual con columnas:

```text
is_valid_candidate
is_correct_dish
is_correct_sentiment
is_specific_enough
should_be_ranking_eligible
review_notes
```

Esto permitiría generar un dataset de evaluación local y medir precisión real.

### 7.2. Ajuste del lexicón de platos

Mejorar:

- platos sevillanos;
- tapas clásicas;
- pescados/fritos;
- carnes ibéricas;
- postres locales;
- variantes ortográficas;
- diminutivos y plurales;
- platos compuestos.

Ejemplos:

```text
serranito
pringá
pavía
adobo
cazón en adobo
montadito de pringá
solomillo al whisky
espinacas con garbanzos
huevos a la flamenca
```

### 7.3. Entrenar o adaptar modelo NER multilingüe

Si se recopila un dataset anotado suficiente, se puede plantear:

- anotar reviews reales de Sevilla;
- entrenar un NER específico de platos en español;
- comparar contra reglas actuales;
- usar un transformer multilingüe;
- mantener reglas como capa de postprocesado.

### 7.4. Mejorar sentimiento por mención

El sentimiento actual es útil, pero se puede mejorar con:

- modelo español de sentiment analysis;
- detección más fina de target sentiment;
- reglas para frases con varios platos;
- detección de comparativas;
- separación de sentimiento de servicio/precio/ambiente;
- calibración de confianza.

Ejemplo de problema:

```text
"La comida estuvo buena, pero el servicio fue lento"
```

El sentimiento positivo podría no pertenecer a todos los platos mencionados, y el negativo puede referirse al servicio.

### 7.5. Mejorar ranking y hiddenness

El componente de `hiddenness` puede evolucionar con:

- popularidad del local;
- número de reseñas del local;
- rating global del local;
- centralidad geográfica;
- densidad gastronómica del barrio;
- rareza del plato por barrio;
- diferencia entre señal local y señal global del plato;
- penalización por cadenas o locales muy populares.

## 8. Próximos pasos de datos

### 8.1. Ampliar fuentes

Posibles fuentes futuras:

```text
Google Places adicional
OpenStreetMap / Overpass
fuentes abiertas municipales
cartas/menús públicos si son legales y accesibles
reseñas propias o feedback de usuarios
```

### 8.2. Refrescos incrementales

Crear un flujo incremental:

```text
1. detectar nuevos locales
2. actualizar referencias Google Places
3. refrescar reseñas disponibles
4. exportar solo nuevas reviews
5. ejecutar IA incremental
6. actualizar ranking
```

### 8.3. Control de cambios

Versionar:

- modelo de detección;
- catálogo;
- sentimiento;
- scoring;
- ranking;
- fecha del corpus;
- parámetros de ejecución.

Esto permitirá comparar rankings entre ejecuciones.

## 9. Criterios para pasar a producción

Antes de marcar `is_production_ready = true`, deberían cumplirse criterios mínimos:

| Criterio | Estado actual | Requisito recomendado |
|---|---|---|
| Integridad DB | Cumplida | Mantener |
| Cobertura territorial | Buena | Validar zonas débiles |
| Revisión manual | Parcial | Revisión sistemática de muestra |
| Precisión de detección | No medida formalmente | Medir con dataset anotado |
| Precisión de sentimiento | No medida formalmente | Evaluar contra muestra manual |
| Robustez ranking | Piloto | Ajustar pesos y umbrales |
| API/dashboard | Pendiente | Implementar capa de consumo |
| Actualización incremental | Pendiente | Diseñar flujo operativo |
| Legalidad/licencias | A revisar | Documentar condiciones de uso |

## 10. Roadmap recomendado

### Fase inmediata

```text
1. Finalizar documentación del piloto Sevilla IA.
2. Actualizar README principal.
3. Revisar manualmente top 30–50 candidatos.
4. Crear vistas SQL específicas para sevilla_pilot.
5. Mejorar query demo con filtros extra.
```

### Fase corta

```text
1. Crear endpoint o dashboard básico.
2. Ajustar DDL para ranking_scope = sevilla_pilot.
3. Crear dataset manual de validación.
4. Refinar lexicón y normalización.
5. Ajustar pesos del ranking.
```

### Fase media

```text
1. Diseñar pipeline incremental.
2. Evaluar modelo NER español/multilingüe.
3. Mejorar sentimiento target-specific.
4. Ampliar fuentes de datos.
5. Generar ranking por barrio más estable.
```

### Fase avanzada

```text
1. Integrar API/frontend.
2. Dashboard interactivo con mapa.
3. Sistema de feedback de usuarios.
4. Reentrenamiento/validación continua.
5. Ranking productivo versionado.
```

## 11. Conclusión

El piloto Sevilla IA demuestra que Hidden Gems ya puede ejecutar un flujo completo:

```text
datos reales
→ IA híbrida
→ señales local-plato
→ ranking explicable
→ carga PostgreSQL
→ consulta demo
```

El resultado es suficientemente sólido para documentación, demostración y análisis interno.

No obstante, por las limitaciones de cobertura, muestra de reseñas, fallback de sentimiento y revisión manual, el ranking debe mantenerse como:

```text
sevilla_pilot
is_production_ready = false
```

La evolución natural descrita en este cierre se materializa parcialmente en la fase posterior `docs/13_sevilla_ai_v2/`, donde se incorporan modelos entrenados, ranking v2, comparación v1/v2 y dashboard Streamlit.

A partir de ahí, el siguiente salto ya no es solo demostrar el prototipo, sino reforzar su fiabilidad con validación humana, más datos, criterios de producción e integración operativa si el proyecto avanza hacia API o producto.
---

## 12. Actualización tras la fase Sevilla IA v2

Después de este piloto se desarrolló la fase:

```text
docs/13_sevilla_ai_v2/
```

Esa fase aborda varias de las mejoras planteadas aquí.

| Necesidad detectada en piloto v1 | Estado tras Sevilla IA v2 |
|---|---|
| Entrenar o adaptar un modelo NER español | Abordado mediante NER BETO para detección de menciones de platos. |
| Mejorar normalización más allá de reglas | Abordado mediante reranker BETO / entity linking. |
| Mejorar sentimiento por mención | Abordado mediante modelo ABSA BETO. |
| Comparar contra el ranking piloto | Abordado con comparación formal v1 vs v2. |
| Crear dashboard inicial | Abordado con dashboard Streamlit Sevilla IA v2. |
| Revisar evidencia y calidad | Abordado parcialmente con `evidence_tier`, `quality_tier`, menciones y reseñas visibles en dashboard. |
| Mantener estado no productivo | Se mantiene: v2 también es experimental y `production_ready = false`. |

La lectura actualizada del roadmap es:

```text
Piloto v1
→ validó el flujo local con reglas híbridas y PostgreSQL

Sevilla IA v2
→ mejoró la cadena con modelos entrenados, ranking ampliado y dashboard

Siguientes mejoras reales
→ validación humana, más datos, calibración de producción, integración DB/API si procede
```

---

## 13. Próximos pasos que siguen vigentes tras v2

Aunque v2 mejora mucho el piloto, siguen pendientes o abiertos estos puntos:

### 13.1. Validación humana sistemática

Sigue siendo necesario revisar manualmente:

- top candidatos v2;
- candidatos `v2_only`;
- candidatos con evidencia `emerging`;
- platos genéricos en posiciones altas;
- menciones con baja confianza;
- casos de sentimiento dudoso.

### 13.2. Criterios de producción

Tanto v1 como v2 siguen marcados como no productivos.

Antes de producción habría que definir criterios como:

```text
mínimo de reviews
mínimo de menciones
evidence_tier mínimo
quality_tier mínimo
validación humana mínima
precisión aceptable de NER/normalización/ABSA
política de actualización
```

### 13.3. Integración operativa

La fase v2 genera artefactos y dashboard, pero una versión de producto podría requerir:

```text
loader PostgreSQL específico para v2
vistas SQL v2
API FastAPI
frontend
pipeline incremental
monitorización de calidad
```

### 13.4. Más datos y más fuentes

La limitación de reseñas por local sigue existiendo.

Por tanto, sigue siendo interesante estudiar:

- más ejecuciones Google Places controladas;
- fuentes abiertas complementarias;
- datos propios de usuarios;
- feedback manual;
- enriquecimiento de menús/cartas cuando sea legal y viable.

### 13.5. Calibración del ranking

La comparación v1/v2 muestra mejora de cobertura, pero todavía hay que calibrar:

- penalización de platos demasiado genéricos;
- bonus de platos locales/específicos;
- pesos de evidencia;
- umbrales para `top`, `strong`, `promising` y `exploratory`;
- diferencia entre ranking exploratorio y ranking productivo.
