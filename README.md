# Hidden Gems Pipeline

Pipeline inteligente de adquisición, validación, normalización y enriquecimiento de datos gastronómicos para **Hidden Gems**, un proyecto orientado a descubrir platos y locales gastronómicos destacados por barrio a partir de múltiples fuentes de datos.

---

## ¿Qué es este proyecto?

**Hidden Gems Pipeline** es el núcleo de procesamiento de datos del proyecto Hidden Gems.

Su objetivo no es construir directamente una aplicación final de cara al usuario, sino desarrollar la parte central y reutilizable que permite:

* adquirir datos desde distintas fuentes
* conservar una capa **raw** trazable
* validar y limpiar los datos de entrada
* normalizar información heterogénea en un modelo común
* enriquecer geográficamente los registros
* construir una base canónica preparada para fases posteriores de análisis, NLP, matching y ranking por barrio

En otras palabras: este repositorio implementa la **infraestructura de datos y automatización inteligente** sobre la que se apoyará el resto del sistema Hidden Gems.

---

## ¿Qué problema resuelve?

En el dominio gastronómico, la información útil suele estar dispersa, incompleta y en formatos distintos según la fuente.

Algunos problemas típicos son:

* cada fuente aporta datos con estructuras diferentes
* los mismos locales pueden aparecer duplicados entre fuentes
* hay registros incompletos, inconsistentes o ruidosos
* la información geográfica no siempre viene preparada para trabajar por barrio
* la calidad de los datos varía mucho según la fuente
* los datos no suelen estar listos directamente para ranking, análisis o NLP

Este pipeline resuelve ese problema creando un flujo de trabajo reproducible para:

* capturar datos de fuentes abiertas y externas
* trazar cada ejecución y cada asset descargado
* transformar datos heterogéneos a un formato común
* asignar localización geográfica útil dentro de Sevilla
* construir entidades canónicas (`place`) separadas de sus representaciones por fuente (`place_source_ref`)
* preparar el terreno para consolidación multi-fuente, extracción de platos y analítica posterior

---

## Objetivo del pipeline

El objetivo principal del proyecto es disponer de una base de datos consistente, trazable y extensible que permita alimentar las fases posteriores de Hidden Gems.

De forma más concreta, el pipeline busca:

* construir verticales completas de procesamiento por fuente
* soportar múltiples fuentes sin romper el modelo común
* mantener separación clara entre raw, staging y datos canónicos
* garantizar trazabilidad, validación y calidad
* enriquecer los locales con información geográfica útil para análisis por barrio
* facilitar futuras integraciones con Google Places, Yelp, NLP y ranking gastronómico

---

## Estado actual del proyecto

Actualmente el proyecto ya ha completado **2 de las 4 verticales principales previstas**:

### Verticales completadas

* **Sevilla Geo**

  * ingesta raw
  * transformación y validación geográfica
  * importación a `district` y `neighborhood`
  * scripts de comprobación

* **OSM Overpass**

  * ingesta raw
  * perfilado del dataset
  * transformación a candidato común de local
  * deduplicación intra-fuente
  * importación canónica a `place`, `place_source_ref`, `place_category` y `place_neighborhood_assignment`
  * scripts de comprobación

### Verticales pendientes

* **Google Places**
* **Yelp Open Dataset**

---

## Fuentes de datos del proyecto

Las fuentes contempladas en el diseño del pipeline son:

1. **Sevilla Geo**

   * dataset geográfico de barrios y distritos de Sevilla
   * base oficial para la asignación territorial

2. **OSM Overpass**

   * fuente abierta para captar POIs gastronómicos
   * útil como fuente libre, geolocalizada y relativamente rica en tags

3. **Google Places**

   * fuente dinámica para enriquecer información de negocio y consolidación multi-fuente

4. **Yelp Open Dataset**

   * dataset de apoyo para el ecosistema de NLP, reviews y estructura complementaria

---

## Arquitectura general

El proyecto sigue una arquitectura de pipeline por capas, modular y reproducible.

### Capas principales

* **raw**: descarga y conservación trazable de datos fuente
* **staging**: transformación intermedia, validación y artefactos derivados
* **reference**: datos de referencia estructurales, como geografía oficial
* **canonical / business**: entidades centrales del dominio, como `place`
* **artifacts / ops**: logs, perfiles, resúmenes y resultados de comprobación

### Flujo conceptual

Fuentes externas → conectores → raw → validación / limpieza → normalización → enriquecimiento → deduplicación / matching → persistencia canónica → comprobación

---

## Stack tecnológico

El stack principal del proyecto es:

### Lenguaje y librerías

* **Python**
* **pandas**
* **requests / httpx**
* **SQLAlchemy**
* **psycopg2-binary**
* **pydantic**
* **pydantic-settings**
* **spaCy**
* **RapidFuzz**
* **pytest**
* **logging**
* **Jupyter**

### Persistencia y base de datos

* **PostgreSQL**
* **PostGIS**

### API y futura exposición

* **FastAPI**

---

## Modelo de datos

El pipeline se apoya en un modelo relacional diseñado para separar claramente:

* entidades canónicas del dominio
* referencias por fuente
* geografía oficial
* clasificación
* trazabilidad
* calidad

### Entidades principales

#### Núcleo de negocio

* `place`
* `place_source_ref`
* `review`

#### Geografía

* `district`
* `neighborhood`
* `place_neighborhood_assignment`

#### Clasificación

* `category`
* `place_category`

#### Gobierno y trazabilidad

* `source_system`
* `source_run`
* `raw_asset`

#### Calidad

* `validation_issue`

---

## Estructura del repositorio simplificada

```text
hidden-gems-pipeline/
│   .env
│   .env.example
│   .gitignore
│   main.py
│   requirements.txt
│
├───data/
│   ├───artifacts/
│   ├───raw/
│   ├───reference/
│   └───staging/
│
├───db/
│   ├───ddl/
│   ├───queries/
│   └───seeds/
│
├───docs/
│   ├───01_context/
│   ├───02_architecture/
│   ├───03_data_model/
│   ├───04_sources/
│   ├───05_verticals/
│   ├───06_normalization/
│   ├───07_quality/
│   ├───08_operations/
│   └───09_roadmap/
│
├───notebooks/
├───scripts/
├───src/
│   ├───config/
│   ├───connectors/
│   ├───db/
│   ├───geo/
│   ├───ingestion/
│   ├───nlp/
│   ├───normalization/
│   └───utils/
│
└───tests/
```

---

## Cómo ejecutar el proyecto

### 1. Preparar entorno

Crear y activar entorno virtual, e instalar dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Crear el archivo `.env` a partir de `.env.example` y completar, como mínimo:

* host de PostgreSQL
* puerto
* base de datos
* usuario
* contraseña
* rutas de datos si fuese necesario
* clave de Google Maps cuando se empiece a usar Google Places

### 3. Verificar conexión y esquema

```bash
python -m scripts.check_db_connection
python -m scripts.check_schema
```

---

## Ejecuciones principales disponibles

### Vertical completa Sevilla Geo

```bash
python -m scripts.load_sevilla_geo_reference --source-version 2026_04
```

### Comprobación Sevilla Geo

```bash
python -m scripts.check_sevilla_geo_load --source-version 2026_04
```

### Vertical completa OSM Overpass

```bash
python -m scripts.load_overpass_pipeline \
  --south 37.3400 \
  --west -6.0400 \
  --north 37.4300 \
  --east -5.9200 \
  --query-name sevilla_gastronomy_bbox
```

### Comprobación del import canónico de Overpass

```bash
python -m scripts.check_overpass_import
```

---

## Principios de diseño seguidos

El desarrollo del pipeline sigue estas reglas:

* **trazabilidad primero**
* **no perder raw**
* **transformar antes de consolidar**
* **no fusionar fuentes directamente**
* **construir `place` como entidad canónica interna**
* **mantener separación clara entre representación fuente y entidad negocio**
* **hacer verticales completas, no piezas aisladas**
* **priorizar validación, observabilidad y control del flujo**

---

## Documentación detallada

La documentación extensa del proyecto está organizada en `docs/` por bloques temáticos.

### Índice de documentación

#### `docs/01_context/`

* visión general del proyecto
* problema y objetivos
* alcance y límites

#### `docs/02_architecture/`

* arquitectura del pipeline
* flujo general
* estructura del proyecto
* configuración y entorno

#### `docs/03_data_model/`

* modelo de datos
* entidades y relaciones
* decisiones de diseño del schema
* trazabilidad y calidad

#### `docs/04_sources/`

* descripción de fuentes
* rol de cada fuente en el sistema
* limitaciones y utilidad

#### `docs/05_verticals/`

* vertical Sevilla Geo
* vertical Overpass
* vertical Google Places
* vertical Yelp

#### `docs/06_normalization/`

* estrategia de normalización
* candidato común de local
* deduplicación y matching
* construcción de `place` canónico

#### `docs/07_quality/`

* validación de datos
* logging
* comprobaciones
* testing

#### `docs/08_operations/`

* quickstart
* guías de ejecución
* scripts operativos

#### `docs/09_roadmap/`

* decisiones clave
* estado actual
* roadmap de desarrollo

---

## Roadmap resumido

### Ya implementado

* base de datos PostgreSQL/PostGIS
* modelo relacional principal
* vertical completa Sevilla Geo
* vertical completa Overpass
* scripts de validación y comprobación

### Próximos pasos

* vertical Google Places
* integración estructurada de Yelp
* mejora del matching multi-fuente
* consolidación más avanzada de `place`
* enriquecimiento adicional para NLP y ranking gastronómico

---

## Estado del proyecto

Este repositorio se encuentra en una fase activa de desarrollo, con una base de datos ya montada, dos verticales ya cerradas y una estructura pensada para crecer de forma controlada y profesional.

El objetivo no es solo obtener datos, sino construir un pipeline sólido, trazable y extensible que sirva como base real para
