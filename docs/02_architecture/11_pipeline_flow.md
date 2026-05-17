# 11. Flujo del pipeline

## 1. Objetivo del flujo del pipeline

El flujo del pipeline define cómo se transforma un dato bruto procedente de una fuente externa en una entidad útil, trazable y explotable dentro del sistema Hidden Gems.

No se trata de una única ejecución lineal sin control, sino de una cadena de fases diferenciadas donde cada una cumple una función concreta:

- adquirir;
- conservar;
- validar;
- transformar;
- enriquecer;
- deduplicar;
- persistir;
- comprobar;
- derivar señales IA;
- entrenar o aplicar modelos cuando corresponde;
- generar ranking;
- exportar para dashboard;
- exponer resultados consultables.

Este diseño permite trabajar con fuentes heterogéneas manteniendo consistencia y control en cada paso.

---

## 2. Visión general del flujo

A nivel general, el pipeline sigue este recorrido:

```text
fuente externa
→ conector / loader
→ source_run
→ raw_asset
→ staging
→ normalización / enriquecimiento
→ deduplicación / matching
→ persistencia canónica o de referencia
→ checks
→ export para IA
→ capa IA derivada
→ modelos / inferencia
→ señales local-plato
→ ranking
→ comparación de versiones
→ export dashboard
→ dashboard / consulta
```

Aunque cada vertical tiene sus particularidades, el patrón general es el mismo:

> Ningún dato relevante entra sin trazabilidad y ninguna salida derivada se da por válida sin comprobación.

---

## 3. Fase 1. Inicio de ejecución

Todo flujo comienza con una ejecución identificable del sistema.

Antes de procesar datos se crea un registro en `source_run`, que representa una ejecución concreta del pipeline sobre una fuente determinada.

### Qué se registra aquí

- sistema fuente;
- tipo de ejecución;
- trigger;
- estado inicial;
- metadata básica de la petición;
- contadores y resultado final.

### Para qué sirve

- trazabilidad temporal;
- auditoría;
- control del ciclo de vida de una ejecución;
- relación con assets raw y validaciones posteriores.

---

## 4. Fase 2. Adquisición desde la fuente

El conector correspondiente se encarga de:

- construir la consulta o petición a la fuente;
- realizar la descarga o lectura;
- capturar la respuesta original;
- devolver el payload sin mezclar todavía con lógica de negocio.

### Ejemplos

- Sevilla Geo: lectura o descarga de un GeoJSON de barrios.
- Overpass: ejecución de una query para POIs gastronómicos dentro de un bbox.
- Google Places: Text Search para descubrir locales.
- Google Places Reviews: Place Details para extraer reviews de locales existentes.
- Yelp Open Dataset: lectura controlada de ficheros bulk para corpus IA.

---

## 5. Fase 3. Persistencia raw

Una vez obtenida la respuesta, el sistema la almacena en la capa `raw`.

Esto genera dos resultados:

1. **Persistencia física**, guardando el asset en disco.
2. **Persistencia lógica**, creando un registro en `raw_asset`.

### Objetivo

Garantizar que siempre existe una copia fiel o una referencia auditable del input original.

---

## 6. Fase 4. Validación estructural

Con el raw ya almacenado, se comprueba que la estructura mínima de los datos sea válida.

Esta validación no intenta todavía entender el dominio completo, sino detectar si el input es procesable.

### Ejemplos de validación estructural

- comprobar que un GeoJSON sea `FeatureCollection`;
- comprobar que exista `features`;
- comprobar que un JSON de Overpass tenga `elements`;
- comprobar que Google Places devuelva campos mínimos;
- comprobar que un JSONL de Yelp pueda leerse línea a línea;
- comprobar columnas esperadas en artefactos IA;
- comprobar que outputs de Sevilla tengan `place_id`, `review_id`, `dish_id` y geografía asociada.

---

## 7. Fase 5. Transformación a staging

En esta fase se traduce la estructura fuente a una estructura interna intermedia.

Aquí se realizan tareas como:

- limpieza básica de texto;
- normalización de nombres;
- derivación de coordenadas utilizables;
- extracción de campos relevantes;
- construcción de candidatos intermedios;
- generación de summaries y artefactos QA.

### Ejemplos

```text
Sevilla Geo
→ district / neighborhood staging
```

```text
Overpass
→ candidatos normalizados de local
```

```text
Google Places
→ candidatos canónicos comparables
```

```text
Yelp
→ subsets gastronómicos y corpus IA
```

```text
Sevilla IA
→ reviews_for_ai
→ dish candidates
→ mentions
→ signals
→ ranking
```

---

## 8. Fase 6. Perfilado y QA intermedio

Una vez generada la salida staging, el proyecto puede producir artefactos de análisis.

### Ejemplos

- frecuencia de tags en Overpass;
- categorías más frecuentes;
- porcentaje de candidatos sin nombre;
- volumen de reviews útiles;
- distribución de splits de corpus IA;
- distribución de etiquetas de sentimiento;
- checks de mapeo entre artefactos IA y base de datos;
- cobertura de barrios y distritos;
- conteos de candidatos Hidden Gems seleccionados;
- comparación v1 vs v2.

### Objetivo

Tomar decisiones mejores antes de consolidar datos o usar artefactos en ranking/dashboard.

---

## 9. Fase 7. Enriquecimiento

Después de transformar los datos, el pipeline puede aplicar lógica adicional para enriquecerlos.

### Enriquecimiento geográfico

Permite asignar:

- barrio;
- distrito;
- método de asignación;
- confianza.

### Enriquecimiento textual / IA

Las reviews se enriquecen con:

- menciones de platos;
- normalización de platos;
- sentimiento por mención;
- señales agregadas;
- ranking de candidatos.

---

## 10. Fase 8. Deduplicación y matching

Antes de persistir en `place`, el sistema decide:

- si varios registros representan el mismo local;
- si un registro debe enlazarse con un `place` ya existente;
- o si debe crear una nueva entidad canónica.

### Mapeo IA contra core

Para integrar IA, se resuelve el puente:

```text
source_place_record_id / business_id
→ place_source_ref
→ place_id

source_review_id
→ review
→ review_id interno
```

Este paso evita cargar menciones o rankings huérfanos.

---

## 11. Fase 9. Persistencia en el modelo final

Una vez que el dato ha superado validación, transformación y deduplicación, se escribe en el modelo relacional.

### Persistencia de referencia

- `district`;
- `neighborhood`.

### Persistencia canónica

- `place`;
- `place_source_ref`;
- `review`;
- `place_category`;
- `place_neighborhood_assignment`.

### Persistencia IA derivada

- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

La persistencia IA no sustituye al dato canónico, sino que lo complementa.

---

## 12. Fase 10. Registro de incidencias

Durante el flujo pueden aparecer problemas que no siempre bloquean la ejecución, pero sí conviene registrar.

Para eso existe `validation_issue`.

### Qué puede registrarse

- campos ausentes;
- estructuras incorrectas;
- geografía no resoluble;
- candidatos no importables;
- problemas de calidad o matching;
- menciones sin review mapeable;
- señales sin `place_id`;
- candidatos IA sin `dish_id`;
- inconsistencias de artefactos.

---

## 13. Fase 11. Comprobación post-importación

Después de escribir en base de datos o generar artefactos finales, el pipeline no se considera terminado hasta comprobar el resultado.

### Qué suelen comprobar los checks

- número de registros cargados;
- integridad de geometrías;
- presencia de asignaciones geográficas;
- categorías creadas;
- incidencias registradas;
- coherencia general del import;
- ausencia de huérfanos IA;
- mapeo correcto entre `review`, `place`, `dish` y ranking;
- existencia de outputs CSV/JSONL;
- valores de score en rango;
- cobertura territorial.

Ejemplos IA:

- `check_ai_dish_catalog.py`;
- `check_ai_downstream_import_readiness.py`;
- `check_ai_ranking_loaded.py`;
- `check_sevilla_ai_pilot_loaded.py`.

---

## 14. Fase 12. Consulta y explotación

Una vez validados los datos, el sistema puede exponerlos mediante vistas SQL, scripts de consulta y dashboards.

La capa IA cuenta con:

```text
db/ddl/08_ai_views.sql
scripts/query_ai_ranking_demo.py
scripts/query_sevilla_hidden_gems_demo.py
dashboard/
```

Estas piezas permiten consultar:

- top candidatos Hidden Gems;
- resumen por local;
- resumen por plato;
- resumen por distrito;
- resumen por barrio;
- detalle de candidato;
- menciones justificativas;
- comparación entre versiones de ranking;
- visualización territorial y de reseñas.

---

## 15. Flujos actualmente implementados

## 15.1. Flujo Sevilla Geo

1. inicio de `source_run`;
2. lectura o descarga del dataset geográfico;
3. guardado raw;
4. validación del GeoJSON;
5. transformación de barrios y distritos;
6. importación a tablas de referencia;
7. comprobación final.

Resultado:

- base territorial sobre la que se apoyan el resto de verticales.

---

## 15.2. Flujo Overpass

1. inicio de `source_run`;
2. ejecución de query Overpass;
3. guardado raw;
4. validación estructural de `elements`;
5. transformación a candidato común;
6. perfilado y QA;
7. deduplicación intra-fuente;
8. importación a `place` y tablas relacionadas;
9. comprobación final.

Resultado:

- fuente abierta integrada en el modelo canónico.

---

## 15.3. Flujo Google Places Text Search

1. ejecución de consulta Text Search;
2. guardado raw;
3. transformación a candidato normalizado;
4. deduplicación;
5. importación canónica;
6. batch por barrios o distritos;
7. check global de batch.

Resultado:

- locales procedentes de Google Places integrados como `place` y `place_source_ref`.

---

## 15.4. Flujo Google Places Reviews

1. selección de locales con referencia Google válida;
2. ejecución de Place Details;
3. extracción de reviews;
4. raw y staging;
5. importación en `review`;
6. checks individuales y batch.

Resultado:

- reviews reales asociadas a locales canónicos.

---

## 15.5. Flujo Yelp + IA prototipo

1. preparación de negocios y reviews Yelp gastronómicos;
2. creación de corpus IA;
3. detección de platos;
4. normalización de platos;
5. sentimiento por mención;
6. agregación de señales;
7. ranking Hidden Gems v1;
8. carga en PostgreSQL;
9. checks de integridad;
10. vistas y demo de consulta.

Resultado:

- prototipo IA completo con ranking `yelp_prototype`, no producción Sevilla.

---

## 15.6. Flujo Sevilla IA Pilot v1

1. recolección de locales y reviews reales desde Google Places;
2. exportación de reviews operativas desde PostgreSQL a JSONL;
3. exploración del corpus Sevilla;
4. detección de candidatos de platos en español;
5. normalización y catálogo local de platos;
6. sentimiento por mención;
7. agregación de señales por local y plato;
8. ranking piloto `sevilla_pilot`;
9. carga en PostgreSQL;
10. check completo de integridad;
11. consulta demo desde vistas IA;
12. export de datos para dashboard v1.

Resultado:

```text
150 candidatos seleccionados
122 locales
38 platos
55 barrios
11 distritos
```

---

## 15.7. Flujo Sevilla IA v2

La fase Sevilla IA v2 amplía el piloto local con modelos entrenados y una explotación visual final.

Flujo completo:

```text
Google Reviews Sevilla
→ dataset de entrenamiento / anotación
→ Modelo 1: NER de platos
→ Hybrid + NER candidates v2
→ Modelo 3: normalización / entity linking
→ Modelo 2: sentimiento por mención / ABSA
→ place-dish signals v2
→ ranking Hidden Gems Sevilla v2
→ comparación v1 vs v2
→ dashboard_v2 export
→ Streamlit Sevilla IA v2
```

Scripts principales:

```text
scripts/build_sevilla_hybrid_ner_mention_candidates_v2.py
scripts/run_sevilla_dish_normalization_reranker_v1.py
scripts/run_sevilla_mention_sentiment_absa_v1.py
scripts/build_sevilla_place_dish_signals_v2.py
scripts/build_sevilla_hidden_gems_ranking_v2.py
scripts/compare_sevilla_ranking_v1_vs_v2.py
scripts/export_sevilla_dashboard_data_v2.py
```

Resultado:

```text
2.335 candidatos puntuados
268 candidatos seleccionados
198 locales seleccionados
40 platos seleccionados
67 barrios seleccionados
11 distritos seleccionados
```

---

## 16. Flujo final de entrega académica

El flujo cerrado para entrega académica es:

```text
fuentes
→ base canónica
→ reviews
→ IA v1/v2
→ ranking explicable
→ comparación
→ dashboard
→ documentación
```

El estado final se considera:

```text
MVP técnico avanzado / prototipo analítico funcional
```

No se marca como producción porque requiere validación humana, revisión de calidad y despliegue formal.

---

## 17. Ventajas de este flujo

El diseño actual ofrece varias ventajas:

- permite depurar cada fase por separado;
- hace más fácil añadir nuevas fuentes;
- evita mezclar lógica de adquisición con lógica de negocio;
- mejora la calidad del dato antes de consolidarlo;
- facilita observabilidad y testing;
- mantiene control real sobre la evolución del sistema;
- permite recalcular resultados IA sin destruir histórico;
- prepara el ranking por barrio sin contaminar el core;
- permite construir dashboard o API sobre artefactos ya validados;
- facilita comparar versiones de ranking;
- mantiene separación entre piloto, prototipo y producción.

---

## 18. Conclusión

El flujo del pipeline de Hidden Gems está concebido para transformar datos heterogéneos y ruidosos en una base canónica controlada, útil y preparada para crecer.

Actualmente, el flujo ya ha sido validado con:

- un prototipo externo sobre Yelp;
- un piloto local real sobre reviews de Google Places Sevilla;
- una fase IA v2 con modelos entrenados;
- un ranking v2 comparado contra el baseline;
- un dashboard final para explotación analítica.

Ese enfoque convierte el repositorio en un pipeline real, trazable y defendible, no en una colección de scripts sueltos.
