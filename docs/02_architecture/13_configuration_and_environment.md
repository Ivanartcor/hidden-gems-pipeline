# 13. Configuration and Environment

## 1. Objetivo de la configuración del proyecto

La configuración en Hidden Gems tiene un papel central porque el sistema depende de:

- rutas locales de datos;
- parámetros de conexión a base de datos;
- endpoints de fuentes externas;
- claves de APIs;
- comportamiento operativo del entorno;
- rutas de artefactos de IA;
- parámetros de ejecución de loaders, checks y demos.

Por ello, la configuración está desacoplada de la lógica de negocio y centralizada en puntos controlados.

El objetivo es que el proyecto pueda ejecutarse de forma consistente en distintos entornos sin reescribir código.

---

## 2. Enfoque general

La configuración del proyecto se apoya en dos piezas principales.

### 2.1. Variables de entorno

Se definen en `.env` y se documentan en `.env.example`.

### 2.2. Capa de settings en código

Se centraliza en `src/config/settings.py`, que carga y tipa esas variables mediante `pydantic-settings`.

De esta forma:

- el código no depende de valores hardcodeados;
- la configuración queda validada;
- el entorno puede cambiar sin tocar la lógica del pipeline;
- los scripts operativos comparten una misma conexión y rutas base.

---

## 3. Archivos principales de configuración

## 3.1. `.env`

Contiene los valores reales del entorno local o de ejecución.

Ejemplos de uso:

- credenciales de PostgreSQL;
- rutas base de datos o artefactos;
- endpoints fuente;
- claves de servicios externos;
- configuración de Google Places.

Este archivo no debe versionarse en Git si contiene datos sensibles.

---

## 3.2. `.env.example`

Sirve como plantilla pública del entorno necesario para arrancar el proyecto.

Su función es:

- documentar qué variables necesita el sistema;
- facilitar la preparación del entorno en otras máquinas;
- evitar ambigüedad sobre qué configuración es necesaria.

---

## 3.3. `src/config/settings.py`

Es el punto central de lectura y validación de configuración.

Desde aquí se exponen los parámetros comunes que usa el resto del sistema.

### Ventajas de este enfoque

- tipado de parámetros;
- valores por defecto razonables;
- carga automática desde `.env`;
- uso centralizado desde el resto del código.

---

## 3.4. `src/config/source_registry.yaml`

Este archivo permite registrar metadatos de fuentes de forma declarativa.

Su objetivo es desacoplar parte de la definición de fuentes de la lógica del código y dejar preparada una gestión más escalable del ecosistema de conectores.

---

## 4. Configuración actual disponible

A nivel actual, el proyecto contempla configuración para los siguientes bloques.

### 4.1. Entorno de aplicación

- `APP_ENV`;
- modo local/desarrollo;
- comportamiento de logging.

### 4.2. Base de datos PostgreSQL/PostGIS

- host;
- puerto;
- base de datos;
- usuario;
- contraseña;
- schema;
- opciones de conexión.

### 4.3. Rutas de datos

- `data/raw`;
- `data/staging`;
- `data/reference`;
- `data/artifacts`;
- `data/external`;
- `data/artifacts/ai`.

### 4.4. Fuentes externas

- endpoint base de Overpass;
- clave de Google Maps / Google Places;
- rutas locales para Yelp Open Dataset.

### 4.5. Logging y parámetros operativos

- nivel de log;
- creación automática de carpetas;
- control de logs en artefactos.

---

## 5. Entorno de ejecución

El proyecto está pensado para ejecutarse en un entorno Python local bien controlado.

### Requisitos principales

- Python compatible con el entorno definido;
- PostgreSQL;
- extensión PostGIS;
- dependencias instaladas desde `requirements.txt`;
- espacio en disco suficiente para datasets y artefactos;
- conexión de red para fuentes API cuando aplique.

---

## 6. Preparación del entorno local

## 6.1. Crear entorno virtual

En Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 6.2. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto deja preparado el entorno Python del proyecto.

---

## 6.3. Configurar `.env`

A partir de `.env.example`, se debe crear `.env` y completar al menos:

- host de PostgreSQL;
- puerto;
- nombre de base de datos;
- usuario;
- contraseña;
- schema;
- rutas de datos si se desean modificar;
- clave de Google Maps / Places.

---

## 6.4. Verificar conexión y schema

Antes de ejecutar verticales completas, conviene comprobar:

```bash
python -m scripts.check_db_connection
python -m scripts.check_schema
```

Esto permite validar que el entorno base está listo.

---

## 7. Entorno de datos

Además del entorno Python y la base de datos, el proyecto depende de una estructura local de datos bien organizada.

### Capas actuales

- `data/raw/`;
- `data/staging/`;
- `data/reference/`;
- `data/artifacts/`;
- `data/external/`;
- `data/artifacts/ai/`.

Estas rutas pueden mantenerse con valores por defecto o parametrizarse desde configuración.

### Importancia

El pipeline no solo usa la base de datos: también genera y consume artefactos en disco.

Por eso el entorno de ejecución debe contemplar ambas dimensiones:

- persistencia en PostgreSQL;
- persistencia en filesystem.

---

## 8. Configuración por tipo de componente

## 8.1. Configuración de conectores

Los conectores necesitan parámetros específicos de fuente.

### Ejemplos

- Overpass → `overpass_base_url`;
- Google Places → `google_maps_api_key`;
- Yelp Open Dataset → rutas locales bajo `data/external`.

---

## 8.2. Configuración de base de datos

La capa DB necesita parámetros robustos y estables porque toda la persistencia canónica y la capa IA dependen de ella.

### Elementos clave

- URL de conexión;
- schema objetivo;
- engine SQLAlchemy;
- validación de conexión;
- puerto local, en este proyecto habitualmente `5433`.

La conexión no se dispersa por el proyecto, sino que se centraliza en `src/db/database.py`.

---

## 8.3. Configuración de logging

El proyecto dispone de configuración de logging centralizada.

### Función actual

- generar logs de ejecución;
- escribir en `data/artifacts/logs/pipeline.log`;
- permitir trazabilidad operativa;
- facilitar depuración de verticales y loaders.

---

## 8.4. Configuración de artefactos IA

Los scripts IA trabajan con rutas de entrada y salida explícitas.

Ejemplos:

```text
data/artifacts/ai/normalization/
data/artifacts/ai/sentiment/
data/artifacts/ai/aggregation/
data/artifacts/ai/ranking/
data/artifacts/ai/checks/
data/artifacts/ai/query_demo/
```

En general, estas rutas se pasan por argumentos CLI, no por variables globales fijas.

Esto permite reejecutar cargas o checks sobre artefactos alternativos sin modificar código.

---

## 9. Relación entre entorno y scripts operativos

Cada script del proyecto asume que el entorno ya está preparado.

### Esto implica que:

- la base de datos debe existir;
- el schema debe estar creado;
- las variables de entorno deben estar disponibles;
- las rutas de datos deben ser accesibles;
- las dependencias deben estar instaladas;
- los DDL necesarios deben haberse ejecutado;
- los artefactos de entrada deben estar en la ruta indicada.

Por eso el proyecto diferencia claramente entre:

- scripts de preparación y comprobación del entorno;
- scripts de ejecución de verticales;
- loaders de integración IA;
- scripts de comprobación post-carga;
- scripts de consulta o demo.

---

## 10. Ejecución en PowerShell

El entorno habitual de desarrollo local es Windows con PowerShell.

Para comandos multilínea se usa el backtick:

```powershell
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Regla importante:

> El backtick debe ser el último carácter de la línea, sin espacios después.

---

## 11. Consideraciones de espacio en disco

Algunos procesos pueden manejar muchos registros o generar temporales en PostgreSQL.

Ejemplos:

- carga de reviews Yelp;
- checks de mapeo contra tablas grandes;
- consultas agregadas sin índices adecuados;
- generación de reports grandes.

Recomendaciones:

- mantener espacio libre suficiente en el disco donde está PostgreSQL;
- evitar joins innecesariamente grandes;
- usar checks optimizados;
- usar parámetros como `--max-rows` o `--max-unique-ids` cuando se quiera una prueba ligera;
- limpiar artefactos temporales o outputs antiguos si el disco está justo.

---

## 12. Configuración y reproducibilidad

Uno de los objetivos principales de esta organización es favorecer la reproducibilidad.

Un pipeline de datos no debe depender de ajustes manuales dispersos en el código o en la máquina.

La configuración actual ayuda a que:

- el entorno pueda replicarse en otra máquina;
- el proyecto pueda documentarse mejor;
- las ejecuciones sean más controlables;
- el comportamiento sea más predecible;
- los loaders IA puedan repetirse con `--dry-run` antes de escribir en base de datos.

---

## 13. Buenas prácticas ya adoptadas

El proyecto sigue varias buenas prácticas importantes:

- uso de `.env.example`;
- separación entre configuración y lógica;
- settings tipados en Python;
- centralización de conexión a base de datos;
- logging centralizado;
- estructura de carpetas consistente;
- scripts de comprobación del entorno;
- `--dry-run` en loaders críticos;
- reports JSON para checks y cargas;
- separación entre artefactos pesados y código versionado.

---

## 14. Mejoras futuras previstas

Aunque la base actual es correcta, la capa de configuración podrá evolucionar en varias líneas:

- más metadata declarativa por fuente;
- separación más explícita entre entorno local, dev y producción;
- configuración adicional para pipelines IA productivos;
- parámetros más finos para matching y deduplicación;
- configuración de exportación de reviews para IA;
- integración más completa con FastAPI si se expone una capa de servicio;
- perfiles de configuración para ejecución local, notebook, batch y API.

---

## 15. Conclusión

La configuración y el entorno de Hidden Gems no son un detalle secundario, sino una parte esencial de la arquitectura del sistema.

Gracias a la combinación de:

- variables de entorno;
- settings centralizados;
- estructura de datos organizada;
- scripts de comprobación;
- rutas explícitas para artefactos;
- reports reproducibles;

el proyecto puede ejecutarse de forma más consistente, trazable y profesional.

Esta base es la que permite que las verticales, la capa IA y las futuras fases de producción sobre Sevilla funcionen de manera controlada.
