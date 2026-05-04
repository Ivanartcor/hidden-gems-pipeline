# Flujo del pipeline

## 1. Objetivo del flujo del pipeline

El flujo del pipeline define cómo se transforma un dato bruto procedente de una fuente externa en una entidad útil, trazable y explotable dentro del sistema Hidden Gems.

No se trata de una única ejecución lineal sin control, sino de una cadena de fases bien diferenciadas donde cada una cumple una función concreta:

* adquirir
* conservar
* validar
* transformar
* enriquecer
* deduplicar
* persistir
* comprobar

Este diseño permite trabajar con fuentes heterogéneas manteniendo consistencia y control en cada paso.

---

## 2. Visión general del flujo

A nivel general, el pipeline sigue este recorrido:

**fuente externa → conector → source_run → raw_asset → staging → normalización / enriquecimiento → deduplicación / matching → persistencia canónica o de referencia → comprobación**

Aunque cada vertical tiene sus particularidades, el patrón general es el mismo.

---

## 3. Fase 1. Inicio de ejecución

Todo flujo comienza con una ejecución identificable del sistema.

Antes de procesar datos se crea un registro en `source_run`, que representa una ejecución concreta del pipeline sobre una fuente determinada.

### Qué se registra aquí

* sistema fuente
* tipo de ejecución
* trigger
* estado inicial
* metadata básica de la petición

### Para qué sirve

* trazabilidad temporal
* auditoría
* control del ciclo de vida de una ejecución
* relación con assets raw y validaciones posteriores

---

## 4. Fase 2. Adquisición desde la fuente

A continuación entra en juego el conector correspondiente.

El conector se encarga de:

* construir la consulta o petición a la fuente
* realizar la descarga o lectura
* capturar la respuesta original
* devolver el payload sin mezclar todavía con lógica de negocio

### Ejemplos

* Sevilla Geo: lectura o descarga de un GeoJSON de barrios
* Overpass: ejecución de una query para POIs gastronómicos dentro de un bbox

En esta fase todavía no se decide cómo va a quedar el dato en el modelo final.

---

## 5. Fase 3. Persistencia raw

Una vez obtenida la respuesta, el sistema la almacena en la capa `raw`.

Esto genera dos resultados:

### 5.1. Persistencia física

El asset se guarda en disco dentro de `data/raw/`.

### 5.2. Persistencia lógica

Se crea un registro en `raw_asset` con metadata como:

* ruta
* formato
* tamaño
* hash
* fuente
* ejecución asociada

### Objetivo

Garantizar que siempre existe una copia fiel del input original.

Esto permite:

* volver a ejecutar transformaciones
* auditar errores
* comparar cambios entre ejecuciones
* no depender de que la fuente externa siga respondiendo igual

---

## 6. Fase 4. Validación estructural

Con el raw ya almacenado, se comprueba que la estructura mínima de los datos sea válida.

Esta validación no intenta todavía entender el dominio completo, sino detectar si el input es procesable.

### Ejemplos de validación estructural

* comprobar que un GeoJSON sea `FeatureCollection`
* comprobar que exista `features`
* comprobar que un JSON de Overpass tenga `elements`
* comprobar que existan campos mínimos para continuar

### Resultado posible

* continuar el flujo
* registrar incidencias en `validation_issue`
* marcar elementos problemáticos
* rechazar partes del input si son imposibles de tratar

---

## 7. Fase 5. Transformación a staging

En esta fase se empieza a traducir la estructura fuente a una estructura interna intermedia.

Aquí se realizan tareas como:

* limpieza básica de texto
* normalización de nombres
* derivación de coordenadas utilizables
* extracción de campos relevantes
* construcción de candidatos intermedios

### Sevilla Geo

El raw geográfico se transforma en registros intermedios preparados para poblar `district` y `neighborhood`.

### Overpass

Los elementos OSM se convierten en `NormalizedPlaceCandidate`, una estructura común que servirá también para futuras fuentes como Google Places y Yelp.

---

## 8. Fase 6. Perfilado y QA intermedio

Una vez generada la salida staging, el proyecto puede producir artefactos de análisis para entender mejor el contenido de la fuente.

### Ejemplos

* frecuencia de tags en Overpass
* categorías más frecuentes
* porcentaje de candidatos sin nombre
* problemas estructurales recurrentes

### Objetivo

Tomar decisiones mejores antes de consolidar datos en el modelo principal.

Esta fase es muy importante porque evita diseñar normalizaciones o matching a ciegas.

---

## 9. Fase 7. Enriquecimiento

Después de transformar los datos, el pipeline puede aplicar lógica adicional para enriquecerlos.

### Enriquecimiento geográfico

Uno de los más importantes en este proyecto es la asignación territorial:

* barrio
* distrito
* método de asignación
* confianza

Esto permite pasar de una coordenada aislada a una ubicación explotable para el análisis por barrio.

Más adelante también podrán existir enriquecimientos como:

* normalización avanzada de categorías
* señales de marca o cadena
* atributos de negocio útiles para ranking

---

## 10. Fase 8. Deduplicación y matching

No todos los registros fuente deben llegar tal cual al modelo canónico.

Antes de persistir en `place`, el sistema necesita decidir:

* si varios registros de una misma fuente representan el mismo local
* si un registro de una fuente debe enlazarse con un `place` ya existente
* o si debe crear una nueva entidad canónica

### 10.1. Deduplicación intra-fuente

Ejemplo actual:

* Overpass agrupa duplicados probables dentro de su propia salida

### 10.2. Matching inter-fuente

Fase prevista para el futuro:

* enlazar OSM, Google Places y Yelp contra un mismo `place`

Esta fase es crítica porque es donde se protege la coherencia del modelo canónico.

---

## 11. Fase 9. Persistencia en el modelo final

Una vez que el dato ha superado validación, transformación y deduplicación, se escribe en el modelo relacional del sistema.

### 11.1. Persistencia de referencia

Para fuentes estructurales como Sevilla Geo:

* `district`
* `neighborhood`

### 11.2. Persistencia canónica

Para fuentes de negocio como Overpass:

* `place`
* `place_source_ref`
* `place_category`
* `place_neighborhood_assignment`

### Idea clave

La persistencia no consiste en copiar directamente la fuente, sino en escribir una representación interna coherente y trazable.

---

## 12. Fase 10. Registro de incidencias

Durante el flujo pueden aparecer problemas que no siempre bloquean la ejecución, pero sí conviene registrar.

Para eso existe `validation_issue`.

### Qué puede registrarse aquí

* campos ausentes
* estructuras incorrectas
* geografía no resoluble
* candidatos no importables
* problemas de calidad o matching

Esta capa es fundamental para dar visibilidad a errores y mantener control sobre la calidad real del pipeline.

---

## 13. Fase 11. Comprobación post-importación

Después de escribir en base de datos, el pipeline no se considera terminado hasta comprobar el resultado.

Por eso existen scripts específicos de verificación.

### Qué suelen comprobar

* número de registros cargados
* integridad de geometrías
* presencia de asignaciones geográficas
* categorías creadas
* incidencias registradas
* coherencia general del import

Esto convierte el pipeline en un flujo controlado de extremo a extremo y no en una simple importación ciega.

---

## 14. Dos tipos de flujo actualmente implementados

## 14.1. Flujo Sevilla Geo

### Resumen

1. inicio de `source_run`
2. lectura o descarga del dataset geográfico
3. guardado raw
4. validación del GeoJSON
5. transformación de barrios y distritos
6. importación a tablas de referencia
7. comprobación final

### Resultado

Se obtiene la base territorial sobre la que se apoyan el resto de verticales.

---

## 14.2. Flujo Overpass

### Resumen

1. inicio de `source_run`
2. ejecución de query Overpass
3. guardado raw
4. validación estructural de `elements`
5. transformación a `NormalizedPlaceCandidate`
6. perfilado y QA
7. deduplicación intra-fuente
8. importación a `place` y tablas relacionadas
9. comprobación final

### Resultado

Se obtiene una primera fuente de negocio completa integrada en el modelo canónico.

---

## 15. Flujo futuro previsto

Cuando entren Google Places y Yelp, el flujo seguirá el mismo patrón general, con transformadores específicos y una fase de matching cada vez más importante.

### Patrón esperado

* adquisición fuente
* raw
* staging
* candidato común
* matching con `place`
* actualización de `place_source_ref`
* explotación posterior

Esto confirma que el pipeline no está diseñado para una sola fuente aislada, sino para un ecosistema multi-fuente.

---

## 16. Ventajas de este flujo

El diseño actual del pipeline ofrece varias ventajas:

* permite depurar cada fase por separado
* hace más fácil añadir nuevas fuentes
* evita mezclar lógica de adquisición con lógica de negocio
* mejora la calidad del dato antes de consolidarlo
* facilita observabilidad y testing
* mantiene control real sobre la evolución del sistema

---

## 17. Conclusión

El flujo del pipeline de Hidden Gems está concebido para transformar datos heterogéneos y ruidosos en una base canónica controlada, útil y preparada para crecer.

La clave no está solo en descargar información, sino en recorrer una secuencia disciplinada de pasos donde cada fase aporta:

* trazabilidad
* validación
* estructura
* calidad
* enriquecimiento
* persistencia coherente

Ese enfoque es el que convierte el repositorio en un pipeline real y no simplemente en una colección de scripts sueltos.
