# Sevilla Geo Source

## 1. Descripción general

**Sevilla Geo** es la fuente geográfica de referencia utilizada por Hidden Gems Pipeline para construir la base territorial del sistema.

Su función principal es proporcionar información oficial o estructurada sobre los barrios y distritos de Sevilla, junto con sus geometrías asociadas.

Esta fuente es fundamental porque Hidden Gems no pretende analizar únicamente locales de forma aislada, sino descubrir información gastronómica organizada por barrio.

Por tanto, antes de importar y explotar locales gastronómicos, el sistema necesita disponer de una capa geográfica fiable sobre la que realizar asignaciones territoriales.

---

## 2. Rol dentro del pipeline

Sevilla Geo actúa como una fuente de referencia, no como una fuente de negocio.

Esto significa que no crea directamente entidades `place`, sino entidades geográficas que luego serán utilizadas por otras verticales.

### Tablas principales que alimenta

* `district`
* `neighborhood`

### Tablas que se apoyan posteriormente en esta fuente

* `place_neighborhood_assignment`

---

## 3. Dataset utilizado

La fuente geográfica principal utilizada es el dataset de barrios de Sevilla.

El dataset puede obtenerse de dos formas:

### 3.1. Desde archivo local

Ejemplo:

```text
data/reference/Barrios.geojson
```

### 3.2. Desde endpoint público

Endpoint utilizado en el proyecto:

```text
https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson
```

Ambas opciones son compatibles con el flujo implementado.

---

## 4. Formato de entrada

El dataset llega en formato **GeoJSON**.

La estructura general del archivo es:

```json
{
  "type": "FeatureCollection",
  "name": "Barrios",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "FID": 1,
        "Barrio": "TABLADA",
        "DISTRITO": 11,
        "DISTRITO_N": "Los Remedios",
        "Superf_Ha": 1330.75252946777,
        "Shape__Area": 21094434.066894501,
        "Shape__Length": 20195.948030727999
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": []
      }
    }
  ]
}
```

### Campos relevantes

| Campo           | Descripción                            | Uso dentro del pipeline      |
| --------------- | -------------------------------------- | ---------------------------- |
| `FID`           | Identificador fuente del elemento      | Trazabilidad del feature     |
| `Barrio`        | Nombre del barrio                      | `neighborhood.official_name` |
| `DISTRITO`      | Código oficial o numérico del distrito | `district.official_code`     |
| `DISTRITO_N`    | Nombre del distrito                    | `district.official_name`     |
| `geometry`      | Geometría del barrio                   | `neighborhood.geometry`      |
| `Shape__Area`   | Área de la geometría                   | Referencia fuente / metadata |
| `Shape__Length` | Longitud del perímetro                 | Referencia fuente / metadata |

---

## 5. Particularidad importante: derivación de distritos

El dataset principal contiene features de barrios, pero cada barrio incluye información del distrito al que pertenece.

Por tanto, en la vertical implementada se tomó una decisión importante:

**los distritos se derivan a partir del dataset de barrios.**

Esto evita depender inicialmente de otro dataset adicional para distritos y permite construir:

* barrios individuales
* agrupación lógica de distritos
* geometría de distrito mediante unión de geometrías de barrios

---

## 6. Flujo implementado

La vertical Sevilla Geo recorre el flujo completo de extremo a extremo.

### 6.1. Ingesta

El conector obtiene el GeoJSON desde:

* archivo local
* endpoint público

Después guarda el payload original en `data/raw/sevilla_geo/`.

### 6.2. Trazabilidad

Cada ejecución queda registrada mediante:

* `source_system`
* `source_run`
* `raw_asset`

Esto permite reconstruir qué dataset se cargó, cuándo y desde dónde.

### 6.3. Transformación

El transformer realiza:

* validación de `FeatureCollection`
* lectura de `features`
* validación de campos obligatorios
* limpieza de texto
* normalización de nombres
* conversión de `Polygon` a `MultiPolygon`
* agrupación de barrios por distrito

### 6.4. Importación

El importer escribe los datos en:

* `district`
* `neighborhood`

### 6.5. Comprobación

Después de la carga, un script de comprobación valida:

* número de barrios cargados
* número de distritos cargados
* geometrías inválidas
* geometrías vacías
* barrios sin distrito
* incidencias generadas

---

## 7. Componentes implementados

### Conector

```text
src/connectors/sevilla_geo.py
```

Responsable de:

* leer o descargar el GeoJSON
* iniciar la ejecución
* guardar raw
* registrar metadata de la fuente

### Transformer

```text
src/geo/sevilla_geo_transformer.py
```

Responsable de:

* validar estructura
* limpiar campos
* normalizar nombres
* convertir geometrías
* preparar registros intermedios de barrio y distrito

### Importer

```text
src/geo/sevilla_geo_importer.py
```

Responsable de:

* insertar o actualizar distritos
* insertar o actualizar barrios
* registrar incidencias
* actualizar métricas de ejecución

### Scripts operativos

```text
scripts/run_sevilla_geo_ingestion.py
scripts/load_sevilla_geo_reference.py
scripts/check_sevilla_geo_load.py
```

---

## 8. Script principal de carga

La vertical completa se ejecuta con:

```bash
python -m scripts.load_sevilla_geo_reference --source-version 2026_04
```

También puede ejecutarse indicando una URL explícita:

```bash
python -m scripts.load_sevilla_geo_reference \
  --download-url "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson" \
  --source-version 2026_04
```

O mediante archivo local:

```bash
python -m scripts.load_sevilla_geo_reference \
  --local-file-path "data/reference/Barrios.geojson" \
  --source-version 2026_04
```

---

## 9. Script de comprobación

Después de la carga puede ejecutarse:

```bash
python -m scripts.check_sevilla_geo_load --source-version 2026_04
```

Este script comprueba:

* conteo de distritos
* conteo de barrios
* geometrías inválidas
* geometrías vacías
* barrios sin distrito
* incidencias de validación

---

## 10. Datos generados en filesystem

La vertical genera datos en varias capas.

### Raw

```text
data/raw/sevilla_geo/YYYY/MM/DD/<run_code>/...
```

Contiene el GeoJSON original descargado o leído.

### Reference

```text
data/reference/Barrios.geojson
```

Puede contener una copia local del dataset geográfico.

### Artifacts

```text
data/artifacts/logs/pipeline.log
```

Contiene logs de ejecución.

---

## 11. Datos generados en base de datos

La vertical alimenta principalmente:

### `district`

Representa los distritos de Sevilla derivados desde las geometrías de los barrios.

### `neighborhood`

Representa los barrios individuales con su geometría y relación con distrito.

### `validation_issue`

Registra incidencias estructurales o de calidad detectadas durante la transformación o importación.

### `source_run` y `raw_asset`

Registran trazabilidad de ejecución y del asset raw.

---

## 12. Validaciones aplicadas

Durante la transformación se validan aspectos como:

* el payload debe ser un `FeatureCollection`
* debe existir una lista `features`
* cada feature debe tener `properties`
* cada feature debe tener `geometry`
* deben existir los campos obligatorios:

  * `Barrio`
  * `DISTRITO`
  * `DISTRITO_N`
* la geometría debe ser `Polygon` o `MultiPolygon`
* no debe haber duplicados de barrio dentro del mismo distrito tras normalización

---

## 13. Normalización aplicada

La fuente se normaliza en varios niveles:

### Texto

* limpieza de espacios
* eliminación de ruido básico
* generación de nombre normalizado
* generación de display name

### Geometría

* conversión de `Polygon` a `MultiPolygon`
* asignación SRID 4326
* unión de geometrías de barrios para formar distritos

### Agrupación

* agrupación de barrios por código de distrito
* construcción de distritos derivados

---

## 14. Por qué se carga antes que las fuentes de negocio

Sevilla Geo debe cargarse antes que Overpass, Google Places o Yelp por una razón fundamental:

**las fuentes de locales necesitan una capa territorial previa para poder asignar cada local a un barrio.**

Sin barrios cargados, los locales podrían importarse con coordenadas, pero no podrían enriquecerse correctamente con:

* `neighborhood_id`
* `district_id`
* método de asignación
* confianza de asignación

Por tanto, Sevilla Geo funciona como vertical base del sistema.

---

## 15. Limitaciones conocidas

Aunque la vertical está funcionando, existen algunas consideraciones:

* si cambia el dataset oficial, puede ser necesario recargarlo
* si cambian nombres o límites de barrios, podrían cambiar asignaciones posteriores
* la geometría depende de la calidad del GeoJSON original
* los distritos son derivados desde barrios, no cargados desde una fuente independiente

Estas limitaciones son aceptables para la fase actual del proyecto.

---

## 16. Estado actual

La vertical Sevilla Geo está implementada y operativa.

Actualmente cubre:

* adquisición
* raw storage
* trazabilidad
* transformación
* importación
* comprobación

Esto la convierte en una de las verticales cerradas del proyecto y en la base geográfica necesaria para el resto del pipeline.

---

## 17. Conclusión

Sevilla Geo es una fuente fundamental para Hidden Gems Pipeline porque proporciona la estructura territorial sobre la que se apoya el análisis por barrio.

Su implementación permite que el sistema no dependa solo de coordenadas aisladas, sino de una geografía normalizada y consultable dentro de PostgreSQL/PostGIS.

Gracias a esta vertical, el resto de fuentes de negocio pueden enriquecerse con barrio y distrito, lo que conecta directamente con el objetivo principal de Hidden Gems: descubrir información gastronómica localizada y útil por zonas concretas de Sevilla.


---

## 18. Relación con Sevilla IA v2 y dashboard final

En la fase Sevilla IA v2, la fuente Sevilla Geo mantiene su papel como base territorial oficial del sistema.

Aunque esta fuente no aporta reseñas ni platos, es imprescindible para que los resultados finales puedan interpretarse correctamente por:

- distrito;
- barrio;
- cobertura territorial;
- distribución de candidatos Hidden Gems;
- filtros del dashboard;
- mapa del dashboard Sevilla IA v2.

El export final del dashboard v2 conserva y utiliza campos territoriales normalizados como:

```text
district_name_std
neighborhood_name_std
```

También permite mostrar resultados agregados en archivos como:

```text
district_summary.csv
neighborhood_summary.csv
top_by_district.csv
top_by_neighborhood.csv
filter_options.json
```

Por tanto, Sevilla Geo queda como una fuente estable y cerrada dentro de la entrega, pero sigue siendo crítica para que el ranking no sea un simple listado de locales, sino un ranking contextualizado territorialmente.

---

## 19. Estado final en la entrega académica

La vertical Sevilla Geo se considera cerrada para la entrega:

```text
[OK] geografía oficial cargada
[OK] distritos disponibles
[OK] barrios disponibles
[OK] soporte para asignación de locales
[OK] soporte para dashboard territorial
[OK] soporte para ranking por barrio/distrito
```

No requiere cambios funcionales para la fase entregada. Las mejoras futuras se limitarían a actualizar la fuente si cambian los límites oficiales o a mejorar la precisión visual del mapa si se incorporan nuevas geometrías o capas GIS al dashboard.
