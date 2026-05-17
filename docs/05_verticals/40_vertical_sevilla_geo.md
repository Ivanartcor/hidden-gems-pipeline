# 40. Vertical Sevilla Geo


## 1. Introducción

La vertical **Sevilla Geo** es la vertical encargada de incorporar al sistema la base territorial oficial utilizada por Hidden Gems.

Su función principal es cargar, validar y normalizar la información geográfica de **distritos** y **barrios** de Sevilla, para que el resto de verticales puedan asignar locales a unidades territoriales oficiales.

Esta vertical es una de las piezas fundacionales del proyecto porque Hidden Gems no se limita a almacenar locales gastronómicos, sino que necesita relacionarlos con barrios concretos.

La pregunta que esta vertical permite responder es:

> ¿Cuál es la estructura territorial oficial sobre la que se asignarán y analizarán los locales?

---

## 2. Objetivo de la vertical

El objetivo de la vertical Sevilla Geo es construir y mantener una referencia geográfica oficial para el sistema.

Concretamente, la vertical debe:

- obtener la capa geográfica de barrios y distritos
- conservar el raw original descargado
- registrar la ejecución de ingesta
- validar la estructura y geometría del dataset
- normalizar nombres, códigos y geometrías
- cargar las entidades `district` y `neighborhood`
- dejar preparada la base territorial para asignar locales a barrios
- registrar incidencias de calidad cuando corresponda

---

## 3. Papel dentro de Hidden Gems

Esta vertical proporciona la **base espacial** del sistema.

Sin esta vertical, otras verticales como OSM / Overpass o Google Places podrían obtener locales con coordenadas, pero no podrían asignarlos correctamente a barrios oficiales.

Por tanto, Sevilla Geo debe ejecutarse antes de cualquier proceso que dependa de asignación territorial.

Ejemplos de procesos dependientes:

- asignar POIs de OSM a barrios
- asignar locales de Google Places a barrios
- calcular cobertura por barrio
- medir densidad de locales por zona
- preparar rankings futuros por barrio

---

## 4. Fuente de datos

La fuente utilizada corresponde al dataset geográfico de barrios y distritos de Sevilla.

### Fuente lógica en el sistema

```text
source_code = sevilla_geo
````

### Tipo de fuente

```text
source_type = geo_dataset
```

### Modo de actualización

```text
refresh_mode = manual_snapshot
```

La fuente se considera un dataset de referencia relativamente estable. No se espera una actualización frecuente como en APIs dinámicas.

---

## 5. Entidades del modelo afectadas

La vertical Sevilla Geo afecta principalmente a las siguientes entidades.

## 5.1. Gobierno y trazabilidad

| Entidad            | Uso                                                   |
| ------------------ | ----------------------------------------------------- |
| `source_system`    | Registra la fuente `sevilla_geo`                      |
| `source_run`       | Registra cada importación o actualización del dataset |
| `raw_asset`        | Registra los ficheros raw descargados o generados     |
| `validation_issue` | Registra problemas de geometría, estructura o calidad |

## 5.2. Geografía

| Entidad        | Uso                          |
| -------------- | ---------------------------- |
| `district`     | Almacena distritos oficiales |
| `neighborhood` | Almacena barrios oficiales   |

---

## 6. Flujo general de la vertical

El flujo de la vertical es el siguiente:

```text
Dataset geográfico Sevilla
        ↓
Descarga / lectura del GeoJSON
        ↓
Registro del source_run
        ↓
Almacenamiento raw_asset
        ↓
Validación de estructura y geometría
        ↓
Normalización de nombres y geometrías
        ↓
Carga de district
        ↓
Carga de neighborhood
        ↓
Registro de incidencias de calidad
```

---

## 7. Entrada de datos

La entrada principal de esta vertical es un fichero geográfico, normalmente en formato GeoJSON.

El dataset debe contener, como mínimo, información suficiente para construir:

* nombre del barrio
* nombre o código del distrito
* geometría del barrio
* identificador o código oficial si existe
* versión o fecha de referencia si está disponible

---

## 8. Raw esperado

La capa raw debe conservar el dataset original descargado o utilizado.

Ejemplo conceptual de almacenamiento:

```text
data/raw/sevilla_geo/YYYY/MM/DD/<run_code>/barrios_original.geojson
```

Además, pueden generarse otros assets:

```text
data/raw/sevilla_geo/YYYY/MM/DD/<run_code>/source_metadata.json
data/artifacts/quality_reports/<run_code>_geo_quality_report.json
```

Estos assets deben registrarse en `raw_asset`.

---

## 9. Registro de ejecución

Cada ejecución de la vertical debe crear un registro en `source_run`.

### Valores recomendados

```text
source_system = sevilla_geo
run_type = manual_import
trigger_type = cli/manual
status = running/completed/completed_with_warnings/failed
```

### Contadores relevantes

| Campo                     | Significado                           |
| ------------------------- | ------------------------------------- |
| `records_extracted_count` | Número de features leídas del dataset |
| `records_staged_count`    | Número de barrios/distritos aceptados |
| `records_rejected_count`  | Número de registros rechazados        |
| `raw_asset_count`         | Número de assets raw generados        |
| `error_count`             | Número de errores detectados          |
| `warning_count`           | Número de advertencias                |

---

## 10. Normalización aplicada

La vertical debe aplicar una normalización mínima antes de cargar la información en base de datos.

### 10.1. Normalización de nombres

Los nombres oficiales se conservan, pero también se genera una versión normalizada.

Ejemplo:

```text
official_name = "LOS REMEDIOS"
normalized_name = "los_remedios"
```

La normalización puede incluir:

* conversión a minúsculas
* eliminación de tildes
* sustitución de espacios por guiones bajos
* eliminación de dobles espacios
* limpieza de caracteres no relevantes

### 10.2. Normalización de geometrías

Las geometrías deben cargarse como:

```sql
GEOMETRY(MultiPolygon, 4326)
```

Si la fuente trae `Polygon`, debe convertirse a `MultiPolygon`.

### 10.3. Derivación de campos geográficos

El schema calcula automáticamente:

* `centroid_point`
* `area_m2`

mediante triggers de base de datos.

---

## 11. Carga en `district`

La entidad `district` representa los distritos oficiales de Sevilla.

### Campos principales cargados

| Campo             | Fuente / cálculo              |
| ----------------- | ----------------------------- |
| `official_code`   | Código oficial si existe      |
| `official_name`   | Nombre del distrito           |
| `normalized_name` | Nombre normalizado            |
| `display_name`    | Nombre legible opcional       |
| `geometry`        | Geometría oficial normalizada |
| `source_version`  | Versión del dataset si existe |
| `is_active`       | `true` por defecto            |

### Decisión importante

El distrito se trata como **dato maestro geográfico**, no como resultado analítico.

---

## 12. Carga en `neighborhood`

La entidad `neighborhood` representa los barrios oficiales de Sevilla.

### Campos principales cargados

| Campo             | Fuente / cálculo               |
| ----------------- | ------------------------------ |
| `district_id`     | FK al distrito correspondiente |
| `official_code`   | Código oficial si existe       |
| `official_name`   | Nombre oficial del barrio      |
| `normalized_name` | Nombre normalizado             |
| `display_name`    | Nombre legible opcional        |
| `geometry`        | Geometría oficial normalizada  |
| `source_version`  | Versión del dataset si existe  |
| `is_active`       | `true` por defecto             |

### Decisión importante

El barrio es la **unidad territorial principal** para análisis posteriores de Hidden Gems.

---

## 13. Validaciones de calidad

La vertical debe validar tanto la estructura del dataset como la calidad geográfica.

### Validaciones mínimas

* el fichero existe y puede leerse
* cada feature tiene geometría
* cada geometría es válida
* cada geometría no está vacía
* cada barrio tiene nombre
* cada barrio puede asociarse a un distrito
* no hay duplicados claros de barrio dentro del mismo distrito

### Validaciones recomendadas

* área mayor que 0
* SRID correcto
* nombres normalizables
* geometrías convertibles a MultiPolygon
* número esperado de barrios razonable

---

## 14. Incidencias posibles

La vertical puede registrar incidencias en `validation_issue`.

| issue_code                | issue_type   | severity sugerida | Descripción                                           |
| ------------------------- | ------------ | ----------------- | ----------------------------------------------------- |
| `raw_asset_missing`       | `validation` | `critical`        | No se encuentra el fichero de entrada                 |
| `schema_mismatch`         | `schema`     | `error`           | La estructura del GeoJSON no coincide con lo esperado |
| `missing_required_field`  | `validation` | `error`           | Falta un campo obligatorio                            |
| `empty_name`              | `quality`    | `error`           | Barrio o distrito sin nombre válido                   |
| `invalid_geometry`        | `geospatial` | `error`           | Geometría inválida                                    |
| `empty_geometry`          | `geospatial` | `error`           | Geometría vacía                                       |
| `district_not_found`      | `geospatial` | `error`           | No se puede asociar barrio a distrito                 |
| `duplicated_neighborhood` | `quality`    | `warning`         | Posible barrio duplicado                              |

---

## 15. Relación con vertical OSM / Overpass

La vertical Sevilla Geo debe ejecutarse antes de OSM / Overpass si se quiere asignar POIs a barrios.

OSM / Overpass necesita que existan previamente:

* `district`
* `neighborhood`
* geometrías válidas
* índices espaciales activos

Una vez cargados los barrios, la vertical OSM puede realizar operaciones como:

```text
place.geom_point dentro de neighborhood.geometry
```

para crear registros en `place_neighborhood_assignment`.

---

## 16. Salidas de la vertical

Las salidas principales son:

### En base de datos

* registros en `district`
* registros en `neighborhood`
* registros en `source_run`
* registros en `raw_asset`
* registros en `validation_issue` si aplica

### En sistema de ficheros

* raw GeoJSON original
* manifest de ejecución si aplica
* reporte QA si aplica
* logs de ejecución

---

## 17. Criterio de éxito

La vertical se considera correcta si:

* el source system `sevilla_geo` existe
* el run queda registrado
* el raw queda registrado como asset
* los distritos se cargan correctamente
* los barrios se cargan correctamente
* las geometrías son válidas
* los centroides y áreas se derivan correctamente
* las incidencias se registran cuando existen
* otras verticales pueden usar `neighborhood` para asignación espacial

---

## 18. Estado actual

La vertical Sevilla Geo ya ha sido implementada como una de las primeras verticales del proyecto.

Su resultado principal es dejar disponible la base geográfica oficial para que el resto de verticales puedan trabajar con asignación territorial.

---

## 19. Próximas mejoras

Posibles mejoras futuras:

* añadir versionado más explícito de capas geográficas
* generar reportes comparativos entre versiones
* incorporar validaciones topológicas más avanzadas
* comprobar solapes o huecos entre barrios
* crear vistas de consulta rápida para cobertura territorial
* documentar métricas de calidad geográfica en `docs/07_quality/`

---

## 20. Conclusión

La vertical Sevilla Geo es una pieza base del pipeline de Hidden Gems.

Su función es proporcionar una referencia territorial fiable, trazable y validada. Sin ella, el sistema podría almacenar locales, pero no podría analizarlos correctamente por barrio.

Esta vertical convierte la dimensión geográfica en una parte estructural del modelo de datos y prepara el terreno para el análisis gastronómico territorial.

---

## 21. Actualización final: papel de Sevilla Geo en Sevilla IA v2

Tras las primeras fases de adquisición e integración, la vertical Sevilla Geo ha quedado confirmada como una pieza estructural del proyecto final. Su aportación no se limita a permitir la carga de locales: también permite interpretar, filtrar y visualizar los resultados del ranking Hidden Gems por territorio.

En la fase **Sevilla IA v2**, la geografía oficial se utiliza de forma directa o indirecta para:

- asociar locales de Google Places a barrios y distritos;
- agregar señales local-plato con contexto territorial;
- generar rankings por distrito y por barrio;
- calcular resúmenes territoriales para el dashboard;
- comparar la cobertura territorial del ranking v1 frente al ranking v2;
- representar visualmente los resultados en el mapa del dashboard Sevilla IA v2.

### 21.1. Resultados territoriales del ranking v2

La fase final Sevilla IA v2 generó un ranking experimental con:

```text
selected_candidates_v2 = 268
selected_places_v2 = 198
selected_dishes_v2 = 40
selected_neighborhoods_v2 = 67
selected_districts_v2 = 11
```

Estos datos demuestran que la capa geográfica no se ha utilizado solo como referencia pasiva, sino como dimensión analítica real del producto.

### 21.2. Relación con el dashboard

El dashboard final `dashboard/streamlit_sevilla_v2_app.py` consume el export:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

y utiliza información territorial para:

- filtros por distrito;
- filtros por barrio;
- rankings territoriales;
- summaries por distrito y barrio;
- visualización en mapa;
- análisis de cobertura v1 vs v2.

Cuando el export incluye coordenadas reales de locales, el mapa puede representar puntos reales. Si no hay coordenadas para alguna entidad, la lógica del dashboard puede apoyarse en centroides o aproximaciones territoriales.

### 21.3. Estado final de la vertical

Para la entrega académica, Sevilla Geo queda cerrada como vertical estable:

```text
[OK] Base territorial cargada
[OK] Barrios y distritos disponibles
[OK] Integración con asignación de locales
[OK] Uso en ranking Sevilla pilot v1
[OK] Uso en ranking Sevilla IA v2
[OK] Uso en dashboard final
```

No se requiere modificar esta vertical para la entrega. Sus mejoras futuras serían de refinamiento, como versionado geográfico más avanzado, validaciones topológicas o revisión de cambios administrativos.

