# Project Structure

## 1. Objetivo de la estructura del proyecto

La estructura de **Hidden Gems Pipeline** no se ha organizado solo para guardar archivos, sino para reflejar directamente la arquitectura lógica del sistema.

Cada bloque del repositorio responde a una necesidad concreta del pipeline:

* configuración
* adquisición de datos
* transformación
* geografía
* persistencia
* operación
* documentación
* artefactos de ejecución

El objetivo es que la organización física del proyecto facilite tres cosas:

1. comprensión rápida del sistema
2. separación clara de responsabilidades
3. crecimiento ordenado a medida que entren nuevas verticales

---

## 2. Vista general de la estructura actual

A nivel general, el proyecto se organiza en los siguientes bloques principales:

* raíz del proyecto
* `data/`
* `db/`
* `docs/`
* `notebooks/`
* `scripts/`
* `src/`
* `tests/`

Cada uno de estos bloques cumple una función concreta dentro del pipeline.

---

## 3. Raíz del proyecto

En la raíz se ubican los archivos básicos de entrada, configuración y arranque.

### Archivos principales

* `.env`
* `.env.example`
* `.gitignore`
* `main.py`
* `README.md`
* `requirements.txt`

### Función de cada uno

#### `.env`

Contiene la configuración real del entorno local.

#### `.env.example`

Sirve como plantilla para configurar el proyecto en otros entornos.

#### `.gitignore`

Evita versionar ficheros sensibles o temporales.

#### `main.py`

Punto de entrada mínimo del proyecto. Su función actual es inicializar el pipeline y comprobar el entorno base.

#### `README.md`

Documento principal de entrada al repositorio.

#### `requirements.txt`

Lista de dependencias del proyecto.

---

## 4. Carpeta `data/`

La carpeta `data/` agrupa todo lo relacionado con artefactos de datos y resultados de ejecución fuera de la base de datos.

Su organización refleja directamente las capas operativas del pipeline.

---

## 4.1. `data/raw/`

Aquí se almacenan los assets originales descargados o leídos desde las fuentes.

### Ejemplos actuales

* `data/raw/osm_overpass/...`
* `data/raw/sevilla_geo/...`

### Función

* conservar la respuesta fuente sin transformación destructiva
* permitir auditoría
* facilitar reejecuciones y depuración
* mantener trazabilidad entre ejecución y asset

La estructura por fuente y fecha permite identificar fácilmente cuándo y desde dónde se obtuvo cada raw.

---

## 4.2. `data/staging/`

Aquí se guardan los artefactos intermedios derivados del raw.

### Ejemplo actual

* `data/staging/osm_overpass/<raw_asset_id>/`

  * `accepted_candidates.json`
  * `needs_review_candidates.json`
  * `rejected_candidates.json`
  * `issues.json`
  * `summary.json`
  * `deduplication/`

    * `dedup_summary.json`
    * `duplicate_groups.json`
    * `pair_evidences.json`
    * `unique_candidates.json`
    * `import/`

      * `import_summary.json`

### Función

* almacenar resultados de transformación intermedia
* separar clearly raw de datos procesados
* guardar resultados de QA y deduplicación
* servir como capa de trabajo previa a la persistencia canónica

---

## 4.3. `data/reference/`

Contiene datasets de referencia relativamente estables.

### Ejemplo actual

* `Barrios.geojson`

### Función

* mantener datasets base reutilizables
* apoyar transformaciones o cargas de referencia
* disponer de inputs manuales o semiestables dentro del proyecto

---

## 4.4. `data/artifacts/`

Agrupa artefactos operativos generados por scripts y procesos.

### Ejemplos actuales

* `logs/`
* `overpass_profiles/`
* `overpass_qa/`

### Función

* guardar logs de ejecución
* guardar perfiles exploratorios
* guardar resultados de QA y comprobación
* mantener evidencia de análisis operativo

Esta carpeta no representa el dato de negocio, sino el soporte de observabilidad y operación del pipeline.

---

## 5. Carpeta `db/`

La carpeta `db/` agrupa todo lo relacionado con la persistencia SQL y la definición del modelo relacional.

---

## 5.1. `db/ddl/`

Contiene los scripts de definición del schema.

### Scripts actuales

* `00_foundation.sql`
* `01_governance.sql`
* `02_geo_reference.sql`
* `03_core_places.sql`
* `04_classification_and_geo_assignment.sql`
* `05_validation.sql`

### Función

* definir la base de datos completa
* estructurar el schema por áreas lógicas
* facilitar creación, revisión y despliegue progresivo

---

## 5.2. `db/queries/`

Reservada para consultas auxiliares, comprobaciones o queries reutilizables.

---

## 5.3. `db/seeds/`

Pensada para cargas iniciales o seeds controlados.

---

## 6. Carpeta `docs/`

La carpeta `docs/` está destinada a la documentación detallada del proyecto.

Actualmente existen carpetas como:

* `database/`
* `pipelines/`

y el objetivo es reorganizar la documentación de forma más sólida por bloques, por ejemplo:

* contexto
* arquitectura
* modelo de datos
* fuentes
* verticales
* normalización
* calidad
* operación
* roadmap

### Función

* separar documentación grande del README raíz
* mantener documentación técnica estructurada
* permitir crecimiento ordenado del conocimiento del proyecto

---

## 7. Carpeta `notebooks/`

Reservada para notebooks de exploración, validación o prototipado.

### Función

* análisis exploratorio
* prototipos rápidos
* validaciones manuales
* pruebas de lógica de datos antes de integrarlas en scripts o módulos estables

---

## 8. Carpeta `scripts/`

La carpeta `scripts/` concentra los puntos de entrada operativos del proyecto.

Aquí se ubican los scripts ejecutables que recorren verticales completas o realizan comprobaciones concretas.

### Tipos de scripts actuales

#### Scripts base de entorno

* `check_db_connection.py`
* `check_schema.py`
* `seed_source_systems.py`

#### Vertical Sevilla Geo

* `run_sevilla_geo_ingestion.py`
* `load_sevilla_geo_reference.py`
* `check_sevilla_geo_load.py`

#### Vertical Overpass

* `run_overpass_ingestion.py`
* `profile_overpass_raw.py`
* `transform_overpass_candidates.py`
* `check_overpass_staging.py`
* `deduplicate_overpass_candidates.py`
* `import_overpass_places.py`
* `check_overpass_import.py`
* `load_overpass_pipeline.py`

### Función

* servir como interfaz operativa del proyecto
* facilitar ejecución por fases
* permitir verticales completas de extremo a extremo
* separar lógica reusable del punto de entrada ejecutable

---

## 9. Carpeta `src/`

La carpeta `src/` contiene la lógica reutilizable y el núcleo real del pipeline.

Es la parte más importante de la estructura del proyecto.

---

## 9.1. `src/config/`

Contiene la configuración central del sistema.

### Archivos actuales

* `settings.py`
* `source_registry.yaml`

### Función

* centralizar variables y rutas
* registrar fuentes
* desacoplar configuración de la lógica del pipeline

---

## 9.2. `src/connectors/`

Contiene los conectores de adquisición por fuente.

### Archivos actuales

* `base.py`
* `overpass.py`
* `sevilla_geo.py`

### Función

* encapsular acceso a fuentes externas
* iniciar `source_run`
* descargar payloads
* persistir raw

---

## 9.3. `src/db/`

Contiene utilidades de acceso a base de datos.

### Archivos actuales

* `database.py`

### Función

* conexión SQLAlchemy
* punto común para acceso a PostgreSQL/PostGIS

---

## 9.4. `src/geo/`

Agrupa lógica específica de geografía y datasets territoriales.

### Archivos actuales

* `sevilla_geo_transformer.py`
* `sevilla_geo_importer.py`

### Función

* transformación geográfica
* importación de referencia territorial
* soporte a enriquecimiento geoespacial

---

## 9.5. `src/ingestion/`

Contiene lógica común de ingesta y trazabilidad.

### Archivos actuales

* `raw_storage.py`
* `run_manager.py`

### Función

* gestionar ejecuciones de fuente
* registrar `source_run`
* persistir `raw_asset`
* soportar flujos de adquisición reutilizables

---

## 9.6. `src/normalization/`

Es uno de los núcleos más importantes del sistema actual.

### Archivos actuales

* `place_candidate.py`
* `osm_overpass_transformer.py`
* `osm_overpass_deduplicator.py`
* `osm_overpass_importer.py`

### Función

* definir el contrato común de candidatos
* transformar fuentes a un modelo intermedio
* deduplicar datos intra-fuente
* importar al modelo canónico

---

## 9.7. `src/nlp/`

Reservada para fases futuras relacionadas con NLP y procesamiento de texto.

### Función prevista

* limpieza lingüística
* análisis de reviews
* detección de platos
* scoring textual

---

## 9.8. `src/utils/`

Contiene utilidades transversales.

### Archivos actuales

* `logging_config.py`

### Función

* configuración de logging
* soporte común compartido entre módulos

---

## 10. Carpeta `tests/`

Pensada para pruebas automáticas del proyecto.

Actualmente todavía no es una de las partes más desarrolladas, pero su presencia ya marca una intención clara de evolución hacia un pipeline más verificable y estable.

---

## 11. Relación entre estructura y flujo real

La estructura actual refleja el flujo del sistema de forma bastante directa:

* `src/connectors/` → adquisición
* `src/ingestion/` → trazabilidad y raw
* `data/raw/` → persistencia original
* `src/normalization/` / `src/geo/` → transformación
* `data/staging/` → resultados intermedios
* `src/normalization/*importer.py` → persistencia final
* `scripts/check_*` → comprobación
* `data/artifacts/` → observabilidad

Eso hace que el proyecto sea más fácil de entender y mantener.

---

## 12. Valoración de la estructura actual

La estructura actual ya es suficientemente sólida como para soportar varias verticales sin convertirse en una colección desordenada de scripts.

Sus principales fortalezas son:

* separación clara entre código, datos y operación
* organización por responsabilidades
* trazabilidad en carpetas de datos
* scripts ejecutables bien diferenciados
* base preparada para crecer con nuevas fuentes

A medida que el proyecto siga creciendo, probablemente habrá que reforzar sobre todo:

* `tests/`
* `docs/`
* `src/nlp/`

pero la base estructural ya es correcta y profesional.

---

## 13. Conclusión

La estructura del proyecto Hidden Gems Pipeline no es accidental: responde a la arquitectura del sistema y al flujo real de procesamiento de datos.

Cada carpeta está pensada para sostener una parte concreta del pipeline y facilitar que el proyecto pueda crecer sin perder orden, trazabilidad ni claridad.

