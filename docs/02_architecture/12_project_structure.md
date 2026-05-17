# 12. Project Structure

## 1. Objetivo de la estructura del proyecto

La estructura de **Hidden Gems Pipeline** no se ha organizado solo para guardar archivos, sino para reflejar directamente la arquitectura lógica del sistema.

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
- dashboards;
- modelos locales no versionados.

El objetivo es que la organización física del proyecto facilite:

1. comprensión rápida del sistema;
2. separación clara de responsabilidades;
3. crecimiento ordenado a medida que entren nuevas verticales, modelos, dashboards y capas de consulta.

---

## 2. Vista general de la estructura actual

A nivel general, el proyecto se organiza en los siguientes bloques principales:

```text
hidden-gems-pipeline/
├── data/
├── dashboard/
├── db/
├── docs/
├── models/          # local, no versionado
├── notebooks/
├── scripts/
├── src/
├── tests/
├── .env
├── .env.example
├── .gitignore
├── main.py
├── README.md
└── requirements.txt
```

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

Contiene la configuración real del entorno local. No debe versionarse.

#### `.env.example`

Plantilla pública para configurar el proyecto en otros entornos.

#### `.gitignore`

Evita versionar ficheros sensibles, temporales, datasets pesados, artefactos masivos y modelos.

#### `main.py`

Punto de entrada mínimo del proyecto.

#### `README.md`

Documento principal de entrada al repositorio.

#### `requirements.txt`

Lista de dependencias del proyecto, incluyendo dependencias de pipeline, IA y dashboards.

---

## 4. Carpeta `data/`

La carpeta `data/` agrupa artefactos de datos y resultados de ejecución fuera de la base de datos.

---

## 4.1. `data/raw/`

Almacena assets originales descargados o leídos desde fuentes.

Ejemplos:

- `data/raw/osm_overpass/`;
- `data/raw/sevilla_geo/`;
- `data/raw/google_places/`;
- `data/raw/google_places_reviews/`.

Función:

- conservar respuesta fuente sin transformación destructiva;
- permitir auditoría;
- facilitar reejecuciones y depuración;
- mantener trazabilidad entre ejecución y asset.

---

## 4.2. `data/staging/`

Guarda artefactos intermedios derivados del raw.

Ejemplos:

- `data/staging/osm_overpass/`;
- `data/staging/google_places/`;
- `data/staging/google_places_reviews/`;
- `data/staging/yelp_open_dataset/`.

Función:

- almacenar resultados de transformación intermedia;
- separar raw de datos procesados;
- guardar resultados de QA y deduplicación;
- servir como capa de trabajo previa a persistencia.

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

Ejemplos:

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

Agrupa artefactos específicos del módulo IA y su integración.

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

---

## 4.7. `data/artifacts/ai/sevilla/`

Contiene artefactos del piloto local Sevilla y de la fase IA v2.

Estructura relevante:

```text
data/artifacts/ai/sevilla/
├── exploration/
├── dish_detection/
├── dish_normalization/
├── sentiment/
├── aggregation/
├── ranking/
├── query_demo/
├── dashboard/
├── dashboard_v2/
└── model_inference/
```

### `model_inference/`

Agrupa salidas de inferencia y ranking IA v2:

```text
data/artifacts/ai/sevilla/model_inference/
├── hybrid_ner_v2/
├── normalization_reranker_v1/
├── sentiment_absa_v1/
├── place_dish_signals_v2/
├── ranking_v2/
└── ranking_v2_comparison/
```

### `dashboard_v2/`

Contiene el contrato de datos y CSV/JSON necesarios para el dashboard Sevilla IA v2:

```text
dashboard_metadata.json
kpi_summary.json
ranking_detail.csv
selected_candidates.csv
top_global.csv
top_by_district.csv
top_by_neighborhood.csv
top_by_dish.csv
district_summary.csv
neighborhood_summary.csv
dish_summary.csv
place_summary.csv
tier_summary.csv
evidence_summary.csv
quality_summary.csv
mention_examples.csv
comparison/
data_contract.json
dashboard_export_summary.json
```

---

## 5. Carpeta `dashboard/`

Contiene dashboards Streamlit del proyecto.

Estructura actual recomendada:

```text
dashboard/
├── streamlit_app.py
├── streamlit_yelp_app.py
└── streamlit_sevilla_v2_app.py
```

### Función

- visualizar ranking Sevilla v1;
- visualizar resultados Yelp/prototipo;
- visualizar ranking Sevilla IA v2;
- consultar KPIs, rankings, territorio, platos, locales, evidencia, calidad, comparación v1/v2 y reseñas.

---

## 6. Carpeta `models/`

Carpeta local no versionada destinada a modelos entrenados.

Ejemplos:

```text
models/
├── sevilla_dish_ner_beto_v1_2/
├── sevilla_dish_normalization_reranker_beto_v1/
└── sevilla_mention_sentiment_absa_beto_v1/
```

### Función

- almacenar modelos descargados desde Kaggle o Drive;
- permitir inferencia local;
- evitar subir pesos pesados al repositorio.

Debe estar incluida en `.gitignore`.

---

## 7. Carpeta `db/`

Agrupa todo lo relacionado con persistencia SQL y definición del modelo relacional.

### `db/ddl/`

Contiene scripts de definición del schema.

Scripts principales:

- `00_foundation.sql`;
- `01_governance.sql`;
- `02_geo_reference.sql`;
- `03_core_places.sql`;
- `04_classification_and_geo_assignment.sql`;
- `05_validation.sql`;
- `06_review_enrichment.sql`;
- `07_ai_module.sql`;
- `08_ai_views.sql`.

### `db/queries/`

Reservada para consultas auxiliares, comprobaciones o queries reutilizables.

### `db/seeds/`

Pensada para cargas iniciales o seeds controlados.

---

## 8. Carpeta `docs/`

Documentación detallada del proyecto.

Estructura actual:

```text
docs/
├── 01_context/
├── 02_architecture/
├── 03_data_model/
├── 04_sources/
├── 05_verticals/
├── 08_operations/
├── 09_roadmap/
├── 10_ai_module/
├── 11_ai_integration/
├── 12_sevilla_ai_pilot/
└── 13_sevilla_ai_v2/
```

### Función

- separar documentación grande del README raíz;
- mantener documentación técnica estructurada;
- documentar decisiones, entidades, fuentes, verticales, IA, integración, dashboards y fase v2;
- permitir crecimiento ordenado del conocimiento del proyecto.

---

## 9. Carpeta `notebooks/`

Reservada para notebooks de exploración, validación o prototipado.

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

#### Piloto Sevilla v1

- exploración de reviews reales de Google;
- detección de candidatos de platos en español;
- normalización y catálogo local;
- sentimiento por mención;
- agregación de señales local-plato;
- ranking `sevilla_pilot`.

#### Sevilla IA v2

- entrenamiento NER v1.2;
- entrenamiento normalización/entity linking reranker;
- entrenamiento ABSA por mención;
- evaluación y análisis de errores.

---

## 10. Carpeta `scripts/`

Concentra los puntos de entrada operativos del proyecto.

---

## 10.1. Scripts base de entorno

- `check_db_connection.py`;
- `check_schema.py`;
- `seed_source_systems.py`.

---

## 10.2. Vertical Sevilla Geo

- `run_sevilla_geo_ingestion.py`;
- `load_sevilla_geo_reference.py`;
- `check_sevilla_geo_load.py`.

---

## 10.3. Vertical Overpass

- `run_overpass_ingestion.py`;
- `profile_overpass_raw.py`;
- `transform_overpass_candidates.py`;
- `check_overpass_staging.py`;
- `deduplicate_overpass_candidates.py`;
- `import_overpass_places.py`;
- `check_overpass_import.py`;
- `load_overpass_pipeline.py`.

---

## 10.4. Vertical Google Places

Incluye scripts para:

- Text Search individual;
- batch por barrios/distritos;
- transformación;
- importación;
- checks de batch.

---

## 10.5. Vertical Google Places Reviews

Incluye scripts para:

- Place Details individual;
- batch de reviews;
- staging;
- importación en `review`;
- checks post-importación.

---

## 10.6. Vertical Yelp Open Dataset

Incluye scripts para:

- perfilado del `.tar`;
- extracción controlada de ficheros;
- perfilado JSONL;
- construcción de subset de negocios gastronómicos;
- construcción de subset de reviews;
- corpus NLP.

---

## 10.7. Scripts IA e integración general

Scripts principales:

- `load_ai_dish_catalog.py`;
- `check_ai_dish_catalog.py`;
- `load_yelp_ai_core_reviews.py`;
- `check_ai_downstream_import_readiness.py`;
- `load_ai_mentions_and_sentiment.py`;
- `load_ai_signals_and_ranking.py`;
- `check_ai_ranking_loaded.py`;
- `query_ai_ranking_demo.py`.

---

## 10.8. Scripts IA Sevilla Pilot v1

Scripts principales:

- `export_reviews_for_ai.py`;
- `check_ai_review_export.py`;
- `load_sevilla_ai_pilot_outputs.py`;
- `check_sevilla_ai_pilot_loaded.py`;
- `query_sevilla_hidden_gems_demo.py`;
- `export_sevilla_dashboard_data.py`.

---

## 10.9. Scripts Sevilla IA v2

Scripts principales:

- `build_sevilla_hybrid_ner_mention_candidates_v2.py`;
- `run_sevilla_dish_normalization_reranker_v1.py`;
- `run_sevilla_mention_sentiment_absa_v1.py`;
- `build_sevilla_place_dish_signals_v2.py`;
- `build_sevilla_hidden_gems_ranking_v2.py`;
- `compare_sevilla_ranking_v1_vs_v2.py`;
- `export_sevilla_dashboard_data_v2.py`.

Función:

- combinar extracción híbrida y NER;
- aplicar normalización/entity linking;
- aplicar sentimiento ABSA;
- construir señales place-dish;
- construir ranking v2;
- comparar v1/v2;
- exportar datos para dashboard.

---

## 11. Carpeta `src/`

Contiene la lógica reutilizable y el núcleo real del pipeline.

### `src/config/`

Configuración central del sistema.

### `src/connectors/`

Conectores de adquisición por fuente.

### `src/db/`

Utilidades de acceso a base de datos.

### `src/geo/`

Lógica específica de geografía y datasets territoriales.

### `src/ingestion/`

Lógica común de ingesta y trazabilidad.

### `src/normalization/`

Contratos comunes de candidatos, normalización, deduplicación e importación.

### `src/nlp/`

Reservada para evolución de NLP/IA en código productivo.

### `src/utils/`

Utilidades transversales.

---

## 12. Carpeta `tests/`

Pensada para pruebas automáticas del proyecto.

Aunque todavía no es una de las partes más desarrolladas, su presencia marca una intención clara de evolución hacia un pipeline más verificable y estable.

---

## 13. Relación entre estructura y flujo real

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
- `data/artifacts/ai/sevilla/` → artefactos IA Sevilla v1/v2;
- `db/ddl/07_ai_module.sql` → persistencia IA;
- `db/ddl/08_ai_views.sql` → consulta IA;
- `scripts/query_*` → demos de consulta;
- `dashboard/` → explotación visual.

---

## 14. Valoración de la estructura actual

La estructura actual ya es suficientemente sólida para soportar:

- varias verticales de fuente;
- una capa IA integrada;
- un piloto local Sevilla;
- una fase IA v2 con modelos entrenados;
- dashboards de explotación;
- documentación técnica completa;
- entrega académica del proyecto.

Fortalezas:

- separación clara entre código, datos y operación;
- organización por responsabilidades;
- trazabilidad en carpetas de datos;
- scripts ejecutables bien diferenciados;
- base preparada para crecer con nuevas fuentes;
- documentación técnica organizada;
- integración IA persistida y consultable;
- dashboard final v2;
- artefactos reproducibles para ranking y comparación.

A medida que el proyecto siga creciendo, convendrá reforzar:

- `tests/`;
- `src/nlp/` o una futura capa `src/ai/` si la lógica IA pasa de scripts/notebooks a código productivo;
- descarga automática de modelos;
- capa API;
- despliegue del dashboard.

---

## 15. Conclusión

La estructura del proyecto Hidden Gems no es accidental: responde a la arquitectura del sistema y al flujo real de procesamiento de datos.

Cada carpeta sostiene una parte concreta del pipeline y permite que el proyecto crezca sin perder orden, trazabilidad ni claridad.

El estado actual contempla adquisición, normalización, integración IA, vistas SQL, consulta de ranking, dashboards y una fase IA v2 finalizada para entrega académica.
