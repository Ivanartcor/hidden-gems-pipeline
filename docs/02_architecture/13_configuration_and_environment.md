# 13. Configuration and Environment

## 1. Objetivo de la configuración del proyecto

La configuración en Hidden Gems tiene un papel central porque el sistema depende de:

- rutas locales de datos;
- parámetros de conexión a base de datos;
- endpoints de fuentes externas;
- claves de APIs;
- comportamiento operativo del entorno;
- rutas de artefactos de IA;
- rutas de modelos locales;
- parámetros de ejecución de loaders, checks, demos y dashboards;
- dependencias de entrenamiento/inferencia IA;
- futura capa API o despliegue.

Por ello, la configuración está desacoplada de la lógica de negocio y centralizada en puntos controlados.

El objetivo es que el proyecto pueda ejecutarse de forma consistente en distintos entornos sin reescribir código.

---

## 2. Enfoque general

La configuración se apoya en cuatro piezas principales.

### 2.1. Variables de entorno

Se definen en `.env` y se documentan en `.env.example`.

### 2.2. Capa de settings en código

Se centraliza en `src/config/settings.py`, que carga y tipa esas variables mediante `pydantic-settings`.

### 2.3. Argumentos CLI

Los scripts operativos aceptan rutas y parámetros por argumento. Esto evita hardcodear inputs/outputs y facilita repetir ejecuciones.

### 2.4. Artefactos versionados por carpeta

La fase IA y dashboard usa carpetas explícitas para separar versiones:

```text
data/artifacts/ai/sevilla/model_inference/
data/artifacts/ai/sevilla/dashboard/
data/artifacts/ai/sevilla/dashboard_v2/
models/
```

---

## 3. Archivos principales de configuración

## 3.1. `.env`

Contiene valores reales del entorno local o de ejecución.

Ejemplos:

- credenciales de PostgreSQL;
- rutas base;
- endpoints fuente;
- claves de servicios externos;
- configuración de Google Places.

Este archivo no debe versionarse si contiene datos sensibles.

---

## 3.2. `.env.example`

Plantilla pública del entorno necesario para arrancar el proyecto.

Su función es:

- documentar qué variables necesita el sistema;
- facilitar preparación en otras máquinas;
- evitar ambigüedad sobre la configuración necesaria.

---

## 3.3. `src/config/settings.py`

Punto central de lectura y validación de configuración.

Ventajas:

- tipado de parámetros;
- valores por defecto razonables;
- carga automática desde `.env`;
- uso centralizado desde el resto del código.

---

## 3.4. `src/config/source_registry.yaml`

Permite registrar metadatos de fuentes de forma declarativa.

Su objetivo es desacoplar parte de la definición de fuentes de la lógica del código.

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
- `data/artifacts/ai`;
- `data/artifacts/ai/sevilla`;
- `data/artifacts/ai/sevilla/model_inference`;
- `data/artifacts/ai/sevilla/dashboard`;
- `data/artifacts/ai/sevilla/dashboard_v2`.

### 4.4. Fuentes externas

- endpoint base de Overpass;
- clave de Google Maps / Google Places;
- rutas locales para Yelp Open Dataset.

### 4.5. Logging y parámetros operativos

- nivel de log;
- creación automática de carpetas;
- control de logs en artefactos.

### 4.6. Modelos IA locales

Los modelos entrenados se guardan localmente, normalmente en:

```text
models/
├── sevilla_dish_ner_beto_v1_2/
├── sevilla_dish_normalization_reranker_beto_v1/
└── sevilla_mention_sentiment_absa_beto_v1/
```

Esta carpeta debe estar en `.gitignore`.

---

## 5. Entorno de ejecución

El proyecto está pensado para ejecutarse en un entorno Python local controlado.

### Requisitos principales

- Python compatible con el entorno definido;
- PostgreSQL;
- extensión PostGIS;
- dependencias instaladas desde `requirements.txt`;
- espacio en disco suficiente para datasets, artefactos y modelos;
- conexión de red para fuentes API cuando aplique;
- GPU opcional para entrenamiento en notebooks/Kaggle, no obligatoria para ejecución local.

---

## 6. Preparación del entorno local

## 6.1. Crear entorno virtual

En Windows:

```powershell
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

```powershell
pip install -r requirements.txt
```

Dependencias relevantes:

- `pandas`;
- `sqlalchemy`;
- `psycopg2-binary`;
- `pydantic`;
- `pydantic-settings`;
- `requests` / `httpx`;
- `rapidfuzz`;
- `streamlit`;
- `plotly`;
- `torch`;
- `transformers`;
- `datasets`, si se reproducen entrenamientos o notebooks.

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

Antes de ejecutar verticales completas:

```powershell
python -m scripts.check_db_connection
python -m scripts.check_schema
```

Esto permite validar que el entorno base está listo.

---

## 7. Entorno de datos

El proyecto depende de una estructura local de datos organizada.

Capas principales:

- `data/raw/`;
- `data/staging/`;
- `data/reference/`;
- `data/artifacts/`;
- `data/external/`;
- `data/artifacts/ai/`;
- `data/artifacts/ai/sevilla/`.

El pipeline no solo usa base de datos: también genera y consume artefactos en disco.

Por eso el entorno contempla dos dimensiones:

```text
PostgreSQL/PostGIS
+
filesystem de artefactos
```

---

## 8. Configuración por tipo de componente

## 8.1. Configuración de conectores

Los conectores necesitan parámetros específicos de fuente.

Ejemplos:

- Overpass → `overpass_base_url`;
- Google Places → `google_maps_api_key`;
- Yelp Open Dataset → rutas locales bajo `data/external`.

---

## 8.2. Configuración de base de datos

Toda la persistencia canónica e IA depende de la conexión a PostgreSQL/PostGIS.

Elementos clave:

- URL de conexión;
- schema objetivo;
- engine SQLAlchemy;
- validación de conexión;
- puerto local, habitualmente `5433`.

La conexión se centraliza en `src/db/database.py`.

---

## 8.3. Configuración de logging

El proyecto dispone de logging centralizado.

Función:

- generar logs de ejecución;
- escribir en `data/artifacts/logs/pipeline.log`;
- permitir trazabilidad operativa;
- facilitar depuración de verticales y loaders.

---

## 8.4. Configuración de artefactos IA

Los scripts IA trabajan con rutas de entrada y salida explícitas.

Ejemplos generales:

```text
data/artifacts/ai/normalization/
data/artifacts/ai/sentiment/
data/artifacts/ai/aggregation/
data/artifacts/ai/ranking/
data/artifacts/ai/checks/
data/artifacts/ai/query_demo/
```

Ejemplos específicos Sevilla v1/v2:

```text
data/artifacts/ai/sevilla/exploration/
data/artifacts/ai/sevilla/dish_detection/
data/artifacts/ai/sevilla/dish_normalization/
data/artifacts/ai/sevilla/sentiment/
data/artifacts/ai/sevilla/aggregation/
data/artifacts/ai/sevilla/ranking/
data/artifacts/ai/sevilla/query_demo/
data/artifacts/ai/sevilla/model_inference/
data/artifacts/ai/sevilla/dashboard/
data/artifacts/ai/sevilla/dashboard_v2/
```

En general, estas rutas se pasan por argumentos CLI.

---

## 8.5. Configuración de modelos IA

Los modelos entrenados no se versionan en Git. Se descargan o descomprimen localmente.

Ubicación recomendada:

```text
models/sevilla_dish_normalization_reranker_beto_v1/
models/sevilla_mention_sentiment_absa_beto_v1/
```

Ejemplo de uso:

```powershell
python -m scripts.run_sevilla_mention_sentiment_absa_v1 `
  --input-path data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/sevilla_dish_mentions_normalized_reranker_v1.jsonl `
  --model-dir models/sevilla_mention_sentiment_absa_beto_v1 `
  --output-dir data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1 `
  --strict
```

---

## 8.6. Configuración de dashboards

Los dashboards Streamlit leen artefactos ya exportados.

Ejecuciones principales:

```powershell
streamlit run dashboard/streamlit_app.py
streamlit run dashboard/streamlit_yelp_app.py
streamlit run dashboard/streamlit_sevilla_v2_app.py
```

El dashboard Sevilla IA v2 espera por defecto:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

---

## 9. Relación entre entorno y scripts operativos

Cada script del proyecto asume que el entorno ya está preparado.

Esto implica:

- la base de datos debe existir;
- el schema debe estar creado;
- las variables de entorno deben estar disponibles;
- las rutas de datos deben ser accesibles;
- las dependencias deben estar instaladas;
- los DDL necesarios deben haberse ejecutado;
- los modelos deben existir localmente cuando el script los requiera;
- los artefactos de entrada deben estar en la ruta indicada.

El proyecto diferencia claramente entre:

- scripts de preparación y comprobación del entorno;
- scripts de ejecución de verticales;
- loaders de integración IA;
- scripts de comprobación post-carga;
- scripts de consulta o demo;
- scripts de inferencia de modelos;
- scripts de export de dashboard;
- dashboards Streamlit.

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

## 11. Entorno de entrenamiento en Kaggle

Los modelos pesados se han entrenado en Kaggle, usando GPU cuando era necesario.

Uso típico:

```text
notebook en Kaggle
→ dataset JSONL/CSV subido como input privado
→ entrenamiento con Transformers
→ export ZIP del modelo
→ descarga local
→ descompresión en models/
→ inferencia local con scripts
```

Esto evita exigir GPU local para el proyecto y permite reproducir la fase de entrenamiento de forma documentada.

---

## 12. Consideraciones de espacio en disco

Algunos procesos pueden manejar muchos registros o generar temporales en PostgreSQL.

Ejemplos:

- carga de reviews Yelp;
- checks de mapeo contra tablas grandes;
- consultas agregadas sin índices adecuados;
- generación de reports grandes;
- exportación de artefactos IA a CSV/JSONL;
- almacenamiento de modelos Transformer;
- dashboard exports con ejemplos de reseñas completas.

Recomendaciones:

- mantener espacio libre suficiente en el disco donde está PostgreSQL;
- evitar joins innecesariamente grandes;
- usar checks optimizados;
- usar parámetros como `--max-rows` cuando se quiera una prueba ligera;
- limpiar artefactos temporales o outputs antiguos si el disco está justo;
- no versionar modelos ni datasets grandes.

---

## 13. Configuración y reproducibilidad

Uno de los objetivos principales es favorecer la reproducibilidad.

La configuración actual ayuda a que:

- el entorno pueda replicarse;
- el proyecto pueda documentarse mejor;
- las ejecuciones sean más controlables;
- el comportamiento sea más predecible;
- los loaders IA puedan repetirse con `--dry-run` antes de escribir en base de datos;
- el piloto Sevilla pueda comprobarse con reports JSON y scripts demo;
- la fase IA v2 pueda repetirse desde artefactos intermedios;
- el dashboard pueda reconstruirse a partir de un contrato de datos claro.

---

## 14. Buenas prácticas ya adoptadas

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
- separación entre artefactos pesados y código versionado;
- uso de scopes y flags para no confundir piloto con producción;
- validación final antes de consultar resultados;
- modelos en `models/` fuera de Git;
- dashboards sobre exports, no directamente sobre lógica inestable;
- documentación de contratos de datos.

---

## 15. Reglas de versionado y Git

No se deben versionar:

```text
.env
.venv/
models/
data/raw/
data/external/
data/staging/**/*.jsonl
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
```

Sí se versionan normalmente:

```text
README.md
requirements.txt
.env.example
scripts/
src/
db/
docs/
dashboard/
```

Algunos summaries pequeños `.json` pueden versionarse si sirven como evidencia documental y no contienen datos sensibles ni demasiado peso.

---

## 16. Mejoras futuras previstas

Aunque la base actual es correcta, la capa de configuración podrá evolucionar en varias líneas:

- más metadata declarativa por fuente;
- separación más explícita entre local, dev y producción;
- configuración adicional para pipelines IA productivos;
- parámetros finos para matching y deduplicación;
- configuración formal de dashboard;
- configuración de FastAPI;
- perfiles de configuración para local, notebook, batch, dashboard y API;
- descarga automática de modelos desde Drive o repositorio privado;
- scheduler o automatización programada.

---

## 17. Conclusión

La configuración y el entorno de Hidden Gems son una parte esencial de la arquitectura del sistema.

Gracias a la combinación de:

- variables de entorno;
- settings centralizados;
- estructura de datos organizada;
- scripts de comprobación;
- rutas explícitas para artefactos;
- modelos locales no versionados;
- reports reproducibles;
- checks de integración;
- exports de dashboard;

el proyecto puede ejecutarse de forma consistente, trazable y profesional.

Esta base permite que las verticales, la capa IA, el piloto Sevilla, la fase IA v2 y los dashboards funcionen de manera controlada.
