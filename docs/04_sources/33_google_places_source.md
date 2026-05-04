# Google Places Source

## 1. Descripción general

**Google Places** está prevista como una fuente dinámica de enriquecimiento y consolidación para Hidden Gems Pipeline.

A diferencia de OSM Overpass, que se ha usado como fuente abierta inicial, Google Places puede aportar información más completa y actualizada sobre locales gastronómicos, especialmente en aspectos de negocio, contacto, estado operativo, rating y volumen de reseñas.

En la fase actual del proyecto, esta vertical todavía no está implementada. Sin embargo, su integración ya está contemplada en el diseño de arquitectura, configuración y modelo de datos.

---

## 2. Rol previsto dentro del pipeline

Google Places actuará como una **fuente de negocio dinámica**.

Su papel principal será enriquecer y contrastar los locales gastronómicos presentes en el sistema.

### Usos previstos

* descubrir nuevos locales no presentes en OSM
* enriquecer locales existentes
* mejorar datos de contacto
* obtener señales de rating y número de reseñas
* obtener estado operativo
* reforzar el matching multi-fuente

---

## 3. Tipo de información esperada

Google Places puede aportar información como:

* identificador fuente del lugar
* nombre comercial
* dirección formateada
* coordenadas
* tipos o categorías
* teléfono
* sitio web
* rating
* número de reseñas
* estado operativo
* horarios
* URL o referencia de fuente

Estos datos encajan de forma natural con el contrato intermedio `NormalizedPlaceCandidate` y con la tabla `place_source_ref`.

---

## 4. Encaje con el modelo de datos

La integración de Google Places debe seguir la misma filosofía que Overpass:

**Google Places no debe sobrescribir directamente la entidad canónica sin control.**

Cada registro fuente debe conservarse como representación propia en:

* `place_source_ref`

Y solo después de aplicar reglas de matching y consolidación se podrá crear o actualizar:

* `place`

### Entidades implicadas

* `source_system`
* `source_run`
* `raw_asset`
* `place`
* `place_source_ref`
* `category`
* `place_category`
* `place_neighborhood_assignment`
* `validation_issue`

---

## 5. Encaje con `NormalizedPlaceCandidate`

Google Places deberá transformarse al mismo contrato común utilizado por Overpass.

### Bloques esperados del candidato

* `provenance`
* `names`
* `address`
* `location`
* `classification`
* `business`
* `quality`
* `geo_enrichment`
* `matching`
* `source_attributes`
* `source_payload`

Esto permitirá que Google Places pueda integrarse sin crear una lógica completamente diferente para el modelo canónico.

---

## 6. Estrategia de adquisición prevista

La adquisición deberá realizarse mediante un conector específico.

### Componente previsto

```text
src/connectors/google_places.py
```

### Responsabilidades esperadas

* construir peticiones a la API
* controlar parámetros de búsqueda
* gestionar paginación si aplica
* registrar `source_run`
* guardar raw en `data/raw/google_places/`
* controlar errores y límites
* devolver payload para transformación posterior

---

## 7. Estrategia de búsqueda prevista

La búsqueda podrá plantearse de distintas formas según la fase.

### 7.1. Búsqueda por área

Usar bounding boxes, círculos o puntos de referencia para captar locales gastronómicos por zona.

### 7.2. Búsqueda guiada por barrios

Usar los barrios ya cargados desde Sevilla Geo para lanzar consultas segmentadas territorialmente.

### 7.3. Enriquecimiento desde candidatos existentes

Usar locales ya obtenidos desde Overpass como semillas para buscar equivalentes en Google Places.

Esta tercera estrategia será especialmente útil para matching y consolidación.

---

## 8. Flujo previsto

La vertical Google Places debería seguir el patrón común del pipeline.

### Fase 1. Ingesta raw

* ejecutar consulta
* registrar ejecución
* guardar payload raw

### Fase 2. Perfilado

* revisar estructura real de respuesta
* analizar campos disponibles
* detectar valores incompletos o inconsistentes

### Fase 3. Transformación

* transformar cada place externo en `NormalizedPlaceCandidate`
* normalizar nombre, dirección, coordenadas y categorías

### Fase 4. Matching

* buscar coincidencias con `place` existente
* usar señales como nombre, distancia, dirección, teléfono y web

### Fase 5. Importación

* crear o actualizar `place_source_ref`
* crear o actualizar `place` si corresponde
* asignar categoría y barrio

### Fase 6. Comprobación

* validar registros cargados
* revisar incidencias
* comprobar calidad del matching

---

## 9. Diferencias respecto a Overpass

Aunque Google Places y Overpass puedan aportar locales, no son fuentes equivalentes.

| Aspecto          | Overpass                             | Google Places                     |
| ---------------- | ------------------------------------ | --------------------------------- |
| Naturaleza       | Abierta / colaborativa               | API externa dinámica              |
| Acceso           | Sin API key en el flujo actual       | Requiere configuración de API key |
| Coste / cuota    | Más flexible para prototipo          | Requiere control de uso           |
| Datos de negocio | Irregulares                          | Potencialmente más completos      |
| Ratings          | No disponibles de forma estructurada | Fuente importante de rating       |
| Reviews          | No integradas en la vertical actual  | Puede aportar señales asociadas   |
| Cobertura        | Variable según edición OSM           | Amplia en negocios activos        |

---

## 10. Consideraciones de coste y control

Google Places debe integrarse con especial cuidado porque depende de una API externa y puede estar sujeta a límites de uso, cuotas o costes.

Por eso se decidió no comenzar el proyecto por esta fuente.

La estrategia correcta es:

* validar primero la arquitectura con fuentes libres
* limitar las consultas iniciales
* registrar cada ejecución
* evitar peticiones innecesarias
* usar caché raw siempre que sea posible
* controlar el gasto antes de escalar

---

## 11. Configuración prevista

La configuración ya contempla una variable para la clave de Google Maps / Google Places:

```text
google_maps_api_key
```

Esta variable debe definirse en `.env` cuando se implemente la vertical.

No debe hardcodearse en el código ni versionarse en el repositorio.

---

## 12. Matching esperado

Google Places será especialmente importante en la fase de matching multi-fuente.

### Señales útiles

* nombre normalizado
* distancia geográfica
* dirección
* teléfono
* web
* categoría
* rating
* número de reseñas

### Resultado esperado

El sistema deberá decidir si un registro de Google:

* corresponde a un `place` ya existente
* crea un nuevo `place`
* requiere revisión manual

---

## 13. Calidad y validación prevista

La vertical deberá validar al menos:

* existencia de identificador fuente
* existencia de nombre
* coordenadas válidas
* estructura de categorías
* estado operativo
* presencia de campos mínimos para importación
* duplicados internos si aparecen

Las incidencias deberán registrarse en `validation_issue`.

---

## 14. Riesgos y limitaciones

### Riesgos principales

* dependencia de API externa
* cambios en estructura de respuesta
* límites o costes de uso
* resultados variables según búsqueda
* posible duplicidad con OSM
* necesidad de matching cuidadoso

### Mitigación

* trazabilidad completa mediante `source_run` y `raw_asset`
* pruebas iniciales con áreas pequeñas
* control estricto de queries
* transformación a candidato común
* matching basado en múltiples señales

---

## 15. Estado actual

La vertical Google Places está pendiente de implementación.

Actualmente ya existen decisiones de arquitectura que facilitan su integración futura:

* modelo `place` / `place_source_ref`
* contrato `NormalizedPlaceCandidate`
* capa raw
* `source_run` y `raw_asset`
* configuración para API key
* experiencia previa de Overpass como fuente de negocio

---

## 16. Conclusión

Google Places será una fuente clave para enriquecer Hidden Gems Pipeline con información de negocio más completa y dinámica.

No se ha implementado todavía por decisión estratégica: antes era necesario validar el flujo con fuentes libres y controlables.

Cuando se incorpore, deberá seguir el mismo patrón profesional ya aplicado en Overpass: raw trazable, transformación a candidato común, matching controlado, importación canónica y comprobación post-carga.
