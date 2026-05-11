# 12. Project Structure

## 1. Objetivo de la estructura del proyecto

La estructura de **Hidden Gems** no se ha organizado solo para guardar archivos, sino para reflejar directamente la arquitectura lógica del sistema.

Cada bloque del repositorio responde a una necesidad concreta del pipeline:

- configuración;
- adquisición de datos;
- transformación;
- geografía;
- persistencia;
- IA derivada;
- operación;
- documentación;
- artefactos de ejecución;
- consulta demo;
- futura visualización.

El objetivo es que la organización física del proyecto facilite:

1. comprensión rápida del sistema;
2. separación clara de responsabilidades;
3. crecimiento ordenado a medida que entren nuevas verticales, modelos, dashboards y capas de consulta.

---

## 2. Vista general de la estructura actual

A nivel general, el proyecto se organiza en los siguientes bloques principales:

- raíz del proyecto;
- `data/`;
- `db/`;
- `docs/`;
- `notebooks/`;
- `scripts/`;
- `src/`;
- `tests/`.

Cada uno cumple una función concreta dentro del pipeline.

---

## 3. Raíz del proyecto

En la raíz se ubican los archivos básicos de entrada, configuración y arranque.

### Archivos principales

- `.env`;
- `.env.example`;
- `.gitignore`;
- `main.py`;
- `README.md`;
- `requirements.txt`.

### Función de cada uno

#### `.env`

Contiene la configuración real del entorno local.

#### `.env.example`

Sirve como plantilla para configurar el proyecto en otros entornos.

#### `.gitignore`

Evita versionar ficheros sensibles, temporales o datasets pesados.

#### `main.py`

Punto de entrada mínimo del proyecto. Su función actual es inicializar el pipeline y comprobar el entorno base.

#### `README.md`

Documento principal de entrada al repositorio.

#### `requirements.txt`

Lista de dependencias del proyecto.

---

## 4. Carpeta `data/`

La carpeta `data/` agrupa artefactos de datos y resultados de ejecución fuera de la base de datos.

Su organización refleja las capas operativas del pipeline.

---

## 4.1. `data/raw/`

Aquí se almacenan los assets originales descargados o leídos desde las fuentes.

### Ejemplos

- `data/raw/osm_overpass/...`;
- `data/raw/sevilla_geo/...`;
- `data/raw/google_places/...`;
- `data/raw/google_places_reviews/...`.

### Función

- conservar la respuesta fuente sin transformación destructiva;
- permitir auditoría;
- facilitar reejecuciones y depuración;
- mantener trazabilidad entre ejecución y asset.

---

## 4.2. `data/staging/`

Aquí se guardan artefactos intermedios derivados del raw.

### Ejemplos

- `data/staging/osm_overpass/`;
- `data/staging/google_places/`;
- `data/staging/google_places_reviews/`;
- `data/staging/yelp_open_dataset/`.

### Función

- almacenar resultados de transformación intermedia;
- separar raw de datos procesados;
- guardar resultados de QA y deduplicación;
- servir como capa de trabajo previa a la persistencia canónica.

---

## 4.3. `data/reference/`

Contiene datasets de referencia relativamente estables.

Ejemplo:

- GeoJSON de barrios/distritos de Sevilla.

### Función

- mantener datasets base reutilizables;
- apoyar transformaciones o cargas de referencia;
- disponer de inputs manuales o semiestables dentro del proyecto.

---

## 4.4. `data/external/`

Contiene datasets externos grandes no versionados.

Ejemplo:

```text
data/external/yelp_open_dataset/
```

### Función

- almacenar datasets bulk descargados manualmente;
- evitar versionar archivos pesados;
- servir como origen para procesos de extracción controlada.

---

## 4.5. `data/artifacts/`

Agrupa artefactos operativos generados por scripts y procesos.

### Ejemplos

- `logs/`;
- `overpass_profiles/`;
- `google_places_batches/`;
- `google_places_reviews_batches/`;
- `yelp_open_dataset_qa/`;
- `nlp_corpus/`;
- `ai/`.

### Función

- guardar logs de ejecución;
- guardar perfiles exploratorios;
- guardar resultados de QA y comprobación;
- mantener evidencia de análisis operativo;
- conservar informes de carga y checks IA.

---

## 4.6. `data/artifacts/ai/`

Esta carpeta agrupa los artefactos específicos del módulo IA y su integración.

Estructura general:

```text
data/artifacts/ai/
├── normalization/
├── sentiment/
├── aggregation/
├── ranking/
├── checks/
├── query_demo/
├── yelp/
└── sevilla/
```

### Función

- almacenar outputs de notebooks IA;
- guardar reportes de loaders;
- guardar checks de preparación e integridad;
- guardar exports de la demo de ranking;
- separar artefactos generales/Yelp de artefactos específicos del piloto Sevilla.

---

## 4.7. `data/artifacts/ai/sevilla/`

Contiene los artefactos del piloto local Sevilla.

Estructura esperada:

```text
data/artifacts/ai/sevilla/
├── exploration/
├── dish_detection/
├── dish_normalization/
├── sentiment/
├── aggregation/
├── ranking/
└── query_demo/
```

### Función

- almacenar reviews exportadas para IA;
- guardar resultados de notebooks 12–17;
- conservar reportes de carga y checks del piloto;
- generar CSV/JSON para scripts demo y dashboard futuro.

---

## 5. Carpeta `db/`

La carpeta `db/` agrupa todo lo relacionado con la persistencia SQL y la definición del modelo relacional.

---

## 5.1. `db/ddl/`

Contiene los scripts de definición del schema.

### Scripts actuales

- `00_foundation.sql`;
- `01_governance.sql`;
- `02_geo_reference.sql`;
- `03_core_places.sql`;
- `04_classification_and_geo_assignment.sql`;
- `05_validation.sql`;
- `06_review_enrichment.sql`;
- `07_ai_module.sql`;
- `08_ai_views.sql`.

### Función

- definir la base de datos completa;
- estructurar el schema por áreas lógicas;
- facilitar creación, revisión y despliegue progresivo;
- añadir la capa IA derivada y sus vistas de consulta.

---

## 5.2. `db/queries/`

Reservada para consultas auxiliares, comprobaciones o queries reutilizables.

---

## 5.3. `db/seeds/`

Pensada para cargas iniciales o seeds controlados.

---

## 6. Carpeta `docs/`

La carpeta `docs/` está destinada a la documentación detallada del proyecto.

Estructura principal actual:

```text
docs/
├── 01_context/
├── 02_architecture/
├── 03_data_model/
├── 04_sources/
├── 05_verticals/
├── 10_ai_module/
├── 11_ai_integration/
└── 12_sevilla_ai_pilot/
```

Algunas carpetas intermedias pueden existir o recuperarse en futuras reorganizaciones documentales, pero el bloque nuevo y relevante para el estado actual es:

```text
docs/12_sevilla_ai_pilot/
```

### Función

- separar documentación grande del README raíz;
- mantener documentación técnica estructurada;
- documentar decisiones, entidades, fuentes, verticales, IA, integración y piloto Sevilla;
- permitir crecimiento ordenado del conocimiento del proyecto.

---

## 7. Carpeta `notebooks/`

Reservada para notebooks de exploración, validación o prototipado.

### Función

- análisis exploratorio;
- entrenamiento y evaluación de modelos;
- prototipos rápidos;
- validaciones manuales;
- pruebas de lógica antes de integrarla en scripts o módulos estables.

### Uso actual relevante

#### Prototipo Yelp

- detección de platos;
- construcción de dataset BIO;
- entrenamiento NER Transformer;
- inferencia de menciones;
- normalización de platos;
- sentimiento por mención;
- agregación de señales;
- ranking Hidden Gems v1.

#### Piloto Sevilla

- exploración de reviews reales de Google;
- detección de candidatos de platos en español;
- normalización y catálogo local;
- sentimiento por mención;
- agregación de señales local-plato;
- ranking `sevilla_pilot`.

---

## 8. Carpeta `scripts/`

La carpeta `scripts/` concentra los puntos de entrada operativos del proyecto.

Aquí se ubican los scripts ejecutables que recorren verticales completas o realizan comprobaciones concretas.

---

## 8.1. Scripts base de entorno

- `check_db_connection.py`;
- `check_schema.py`;
- `seed_source_systems.py`.

---

## 8.2. Vertical Sevilla Geo

- `run_sevilla_geo_ingestion.py`;
- `load_sevilla_geo_reference.py`;
- `check_sevilla_geo_load.py`.

---

## 8.3. Vertical Overpass

- `run_overpass_ingestion.py`;
- `profile_overpass_raw.py`;
- `transform_overpass_candidates.py`;
- `check_overpass_staging.py`;
- `deduplicate_overpass_candidates.py`;
- `import_overpass_places.py`;
- `check_overpass_import.py`;
- `load_overpass_pipeline.py`.

---

## 8.4. Vertical Google Places

Incluye scripts para:

- Text Search individual;
- batch por barrios/distritos;
- transformación;
- importación;
- checks de batch.

---

## 8.5. Vertical Google Places Reviews

Incluye scripts para:

- Place Details individual;
- batch de reviews;
- staging;
- importación en `review`;
- checks post-importación.

---

## 8.6. Vertical Yelp Open Dataset

Incluye scripts para:

- perfilado del `.tar`;
- extracción controlada de ficheros;
- perfilado JSONL;
- construcción de subset de negocios gastronómicos;
- construcción de subset de reviews;
- corpus NLP.

---

## 8.7. Scripts IA e integración general

Scripts principales:

- `load_ai_dish_catalog.py`;
- `check_ai_dish_catalog.py`;
- `load_yelp_ai_core_reviews.py`;
- `check_ai_downstream_import_readiness.py`;
- `load_ai_mentions_and_sentiment.py`;
- `load_ai_signals_and_ranking.py`;
- `check_ai_ranking_loaded.py`;
- `query_ai_ranking_demo.py`.

### Función

- cargar catálogo de platos y aliases;
- importar core Yelp para prototipo IA;
- cargar menciones y sentimiento;
- cargar señales agregadas y ranking;
- verificar integridad;
- consultar resultados IA desde PostgreSQL.

---

## 8.8. Scripts IA Sevilla Pilot

Scripts principales:

- `export_reviews_for_ai.py`;
- `check_ai_review_export.py`;
- `load_sevilla_ai_pilot_outputs.py`;
- `check_sevilla_ai_pilot_loaded.py`;
- `query_sevilla_hidden_gems_demo.py`.

### Función

- exportar reviews reales de Google Places desde PostgreSQL a JSONL;
- validar el export IA;
- cargar outputs IA del piloto Sevilla;
- comprobar integridad de la carga;
- consultar el ranking `sevilla_pilot` mediante vistas SQL.

---

## 9. Carpeta `src/`

La carpeta `src/` contiene la lógica reutilizable y el núcleo real del pipeline.

---

## 9.1. `src/config/`

Contiene la configuración central del sistema.

### Función

- centralizar variables y rutas;
- registrar fuentes;
- desacoplar configuración de la lógica del pipeline.

---

## 9.2. `src/connectors/`

Contiene conectores de adquisición por fuente.

### Función

- encapsular acceso a fuentes externas;
- iniciar `source_run`;
- descargar payloads;
- persistir raw.

---

## 9.3. `src/db/`

Contiene utilidades de acceso a base de datos.

### Función

- conexión SQLAlchemy;
- punto común para acceso a PostgreSQL/PostGIS.

---

## 9.4. `src/geo/`

Agrupa lógica específica de geografía y datasets territoriales.

### Función

- transformación geográfica;
- importación de referencia territorial;
- soporte a enriquecimiento geoespacial.

---

## 9.5. `src/ingestion/`

Contiene lógica común de ingesta y trazabilidad.

### Función

- gestionar ejecuciones de fuente;
- registrar `source_run`;
- persistir `raw_asset`;
- soportar flujos de adquisición reutilizables.

---

## 9.6. `src/normalization/`

Es uno de los núcleos más importantes del sistema.

### Función

- definir contratos comunes de candidatos;
- transformar fuentes a modelos intermedios;
- deduplicar datos;
- importar al modelo canónico.

---

## 9.7. `src/nlp/`

Reservada para evolución de NLP/IA en código productivo.

### Función prevista

- limpieza lingüística;
- análisis de reviews;
- detección de platos;
- scoring textual;
- exportación de corpus desde base de datos;
- adaptación futura a español/multilingüe.

---

## 9.8. `src/utils/`

Contiene utilidades transversales.

### Función

- configuración de logging;
- soporte común compartido entre módulos.

---

## 10. Carpeta `tests/`

Pensada para pruebas automáticas del proyecto.

Actualmente todavía no es una de las partes más desarrolladas, pero su presencia marca una intención clara de evolución hacia un pipeline más verificable y estable.

---

## 11. Relación entre estructura y flujo real

La estructura actual refleja el flujo del sistema:

- `src/connectors/` → adquisición;
- `src/ingestion/` → trazabilidad y raw;
- `data/raw/` → persistencia original;
- `src/normalization/` / `src/geo/` → transformación;
- `data/staging/` → resultados intermedios;
- `scripts/load_*` / importadores → persistencia;
- `scripts/check_*` → comprobación;
- `data/artifacts/` → observabilidad;
- `data/artifacts/ai/` → artefactos IA;
- `data/artifacts/ai/sevilla/` → artefactos IA del piloto Sevilla;
- `db/ddl/07_ai_module.sql` → persistencia IA;
- `db/ddl/08_ai_views.sql` → consulta IA;
- `scripts/query_*` → demos de consulta.

---

## 12. Valoración de la estructura actual

La estructura actual ya es suficientemente sólida para soportar varias verticales, una capa IA integrada y un piloto local Sevilla sin convertirse en una colección desordenada de scripts.

Sus principales fortalezas son:

- separación clara entre código, datos y operación;
- organización por responsabilidades;
- trazabilidad en carpetas de datos;
- scripts ejecutables bien diferenciados;
- base preparada para crecer con nuevas fuentes;
- documentación técnica organizada;
- integración IA persistida y consultable;
- piloto Sevilla documentado y validado.

A medida que el proyecto siga creciendo, probablemente habrá que reforzar:

- `tests/`;
- `src/nlp/` o una futura capa `src/ai/` si la lógica IA pasa de notebooks a código productivo;
- scripts de consulta finales para dashboard;
- capa API;
- carpeta de dashboard si se implementa con Streamlit u otra herramienta.

---

## 13. Conclusión

La estructura del proyecto Hidden Gems no es accidental: responde a la arquitectura del sistema y al flujo real de procesamiento de datos.

Cada carpeta está pensada para sostener una parte concreta del pipeline y facilitar que el proyecto pueda crecer sin perder orden, trazabilidad ni claridad.

La estructura actual ya contempla no solo adquisición y normalización, sino también integración IA, vistas SQL, consulta de ranking y piloto real sobre Sevilla, dejando el repositorio preparado para avanzar hacia dashboard, API y mejora IA posterior.
