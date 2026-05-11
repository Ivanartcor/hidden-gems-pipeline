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
→ carga IA en PostgreSQL
→ vistas de consulta
→ demo / dashboard futuro
```

Aunque cada vertical tiene sus particularidades, el patrón general es el mismo: **ningún dato relevante entra sin trazabilidad y ninguna salida derivada se da por válida sin comprobación**.

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

A continuación entra en juego el conector correspondiente.

El conector se encarga de:

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

Esto genera dos resultados.

### 5.1. Persistencia física

El asset se guarda en disco dentro de `data/raw/` o en la ruta correspondiente de datos externos/staging cuando se trabaja con datasets bulk.

### 5.2. Persistencia lógica

Se crea un registro en `raw_asset` con metadata como:

- ruta;
- formato;
- tamaño;
- hash;
- fuente;
- ejecución asociada.

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
- comprobar que los outputs Sevilla tengan `place_id`, `review_id`, `dish_id` y geografía asociada.

### Resultado posible

- continuar el flujo;
- registrar incidencias en `validation_issue`;
- marcar elementos problemáticos;
- rechazar partes del input si son imposibles de tratar.

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

### Sevilla Geo

El raw geográfico se transforma en registros intermedios preparados para poblar `district` y `neighborhood`.

### Overpass

Los elementos OSM se convierten en candidatos normalizados de local.

### Google Places

Las respuestas de Text Search se transforman en candidatos canónicos comparables con otras fuentes.

### Yelp Open Dataset

El dataset se transforma en subsets gastronómicos y corpus preparado para IA.

### Sevilla IA Pilot

Las reviews reales exportadas desde PostgreSQL se transforman progresivamente en artefactos IA:

```text
reviews_for_ai_google_places.jsonl
→ dish_candidates
→ dish_catalog / aliases
→ mentions with sentiment
→ place_dish_signals
→ hidden_gems ranking
```

---

## 8. Fase 6. Perfilado y QA intermedio

Una vez generada la salida staging, el proyecto puede producir artefactos de análisis para entender mejor el contenido de la fuente.

### Ejemplos

- frecuencia de tags en Overpass;
- categorías más frecuentes;
- porcentaje de candidatos sin nombre;
- volumen de reviews útiles;
- distribución de splits de corpus IA;
- distribución de etiquetas de sentimiento;
- checks de mapeo entre artefactos IA y base de datos;
- cobertura de barrios y distritos;
- conteos de candidatos Hidden Gems seleccionados.

### Objetivo

Tomar decisiones mejores antes de consolidar datos en el modelo principal o en la capa IA.

---

## 9. Fase 7. Enriquecimiento

Después de transformar los datos, el pipeline puede aplicar lógica adicional para enriquecerlos.

### Enriquecimiento geográfico

Uno de los más importantes en este proyecto es la asignación territorial:

- barrio;
- distrito;
- método de asignación;
- confianza.

Esto permite pasar de una coordenada aislada a una ubicación explotable para el análisis por barrio.

### Enriquecimiento textual

En la fase IA, las reviews se enriquecen con:

- menciones de platos;
- normalización de platos;
- sentimiento por mención;
- señales agregadas;
- ranking de candidatos.

---

## 10. Fase 8. Deduplicación y matching

No todos los registros fuente deben llegar tal cual al modelo canónico.

Antes de persistir en `place`, el sistema necesita decidir:

- si varios registros de una misma fuente representan el mismo local;
- si un registro de una fuente debe enlazarse con un `place` ya existente;
- o si debe crear una nueva entidad canónica.

### 10.1. Deduplicación intra-fuente

Ejemplo actual:

- Overpass agrupa duplicados probables dentro de su propia salida.

### 10.2. Matching inter-fuente

El sistema está preparado para enlazar OSM, Google Places y otras fuentes contra un mismo `place`.

### 10.3. Mapeo IA contra core

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

Una vez que el dato ha superado validación, transformación y deduplicación, se escribe en el modelo relacional del sistema.

### 11.1. Persistencia de referencia

Para fuentes estructurales como Sevilla Geo:

- `district`;
- `neighborhood`.

### 11.2. Persistencia canónica

Para fuentes de negocio:

- `place`;
- `place_source_ref`;
- `review`;
- `place_category`;
- `place_neighborhood_assignment`.

### 11.3. Persistencia IA derivada

Para resultados de inteligencia artificial:

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

### Qué puede registrarse aquí

- campos ausentes;
- estructuras incorrectas;
- geografía no resoluble;
- candidatos no importables;
- problemas de calidad o matching;
- menciones sin review mapeable;
- señales sin `place_id`;
- candidatos IA sin `dish_id`;
- inconsistencias de artefactos.

La tabla `validation_issue` está preparada para registrar incidencias sobre entidades core y entidades IA.

---

## 13. Fase 11. Comprobación post-importación

Después de escribir en base de datos, el pipeline no se considera terminado hasta comprobar el resultado.

Por eso existen scripts específicos de verificación.

### Qué suelen comprobar

- número de registros cargados;
- integridad de geometrías;
- presencia de asignaciones geográficas;
- categorías creadas;
- incidencias registradas;
- coherencia general del import;
- ausencia de huérfanos IA;
- mapeo correcto entre `review`, `place`, `dish` y ranking.

Ejemplos IA:

- `check_ai_dish_catalog.py`;
- `check_ai_downstream_import_readiness.py`;
- `check_ai_ranking_loaded.py`;
- `check_sevilla_ai_pilot_loaded.py`.

---

## 14. Fase 12. Consulta y explotación

Una vez validados los datos, el sistema puede exponerlos mediante vistas SQL y scripts de consulta.

La capa IA cuenta con:

```text
db/ddl/08_ai_views.sql
scripts/query_ai_ranking_demo.py
scripts/query_sevilla_hidden_gems_demo.py
```

Estas piezas permiten consultar:

- top candidatos Hidden Gems;
- resumen por local;
- resumen por plato;
- resumen por distrito;
- resumen por barrio;
- detalle de candidato;
- menciones justificativas cuando aplica.

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

## 15.6. Flujo Sevilla IA Pilot

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
11. consulta demo desde vistas IA.

Resultado:

- 150 candidatos seleccionados del piloto Sevilla, distribuidos por 122 locales, 38 platos, 55 barrios y 11 distritos.

---

## 16. Flujo objetivo de las siguientes fases

El siguiente flujo objetivo no es volver a demostrar el pipeline, sino convertir el piloto en una capa más explotable:

```text
ranking sevilla_pilot cargado
→ scripts demo finales
→ contrato de datos para dashboard
→ dashboard piloto
→ revisión de calidad con uso real
→ mejora IA si aporta valor
→ posible API / producto
```

Más adelante, si la calidad es suficiente, se podrá promover un scope más productivo:

```text
ranking_scope = sevilla_neighborhood
is_production_ready = true
```

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
- permite construir dashboard o API sobre vistas ya validadas.

---

## 18. Conclusión

El flujo del pipeline de Hidden Gems está concebido para transformar datos heterogéneos y ruidosos en una base canónica controlada, útil y preparada para crecer.

La clave no está solo en descargar información, sino en recorrer una secuencia disciplinada donde cada fase aporta trazabilidad, validación, estructura, calidad, enriquecimiento, persistencia coherente y explotación inteligente.

Ese enfoque es el que convierte el repositorio en un pipeline real y no en una colección de scripts sueltos. Actualmente, además, el flujo ya ha sido validado tanto con un prototipo externo sobre Yelp como con un piloto local real sobre reviews de Google Places Sevilla.
