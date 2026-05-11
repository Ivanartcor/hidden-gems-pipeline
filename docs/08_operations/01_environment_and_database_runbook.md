# 01. Environment and Database Runbook

## 1. Propósito

Este runbook explica cómo preparar el entorno local necesario para ejecutar **Hidden Gems Pipeline**.

Incluye:

- entorno Python;
- variables de entorno;
- conexión a PostgreSQL/PostGIS;
- creación del schema mediante DDL;
- seed de fuentes;
- checks iniciales;
- recomendaciones para evitar problemas comunes.

Debe consultarse antes de ejecutar verticales de ingesta, loaders IA o scripts de consulta.

---

## 2. Requisitos previos

El entorno local debe tener instalado:

```text
- Python compatible con el proyecto;
- PostgreSQL;
- extensión PostGIS;
- Git;
- acceso al repositorio hidden-gems-pipeline;
- espacio en disco suficiente para data/raw, data/staging y data/artifacts;
- conexión a internet para fuentes API cuando aplique;
- Google Cloud configurado si se va a usar Google Places.
```

En Windows, el proyecto se ha trabajado principalmente con:

```text
- Windows 11;
- PowerShell;
- entorno virtual .venv;
- PostgreSQL en puerto local habitual 5433.
```

---

## 3. Clonar o preparar el repositorio

Si se parte de cero:

```powershell
git clone <repo-url>
cd hidden-gems-pipeline
```

Si el repositorio ya existe:

```powershell
git status
git pull
```

Antes de ejecutar scripts, comprobar que se está en la raíz del proyecto, donde existen archivos como:

```text
README.md
requirements.txt
main.py
scripts/
src/
db/
docs/
```

---

## 4. Crear entorno virtual

En Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

En Linux/macOS:

```bash
python -m venv .venv
source .venv/bin/activate
```

Comprobar que el entorno está activo:

```powershell
python --version
pip --version
```

---

## 5. Instalar dependencias

Con el entorno virtual activado:

```powershell
pip install -r requirements.txt
```

Si aparecen errores de permisos en Windows, revisar que:

- el entorno virtual está activado;
- no se está instalando globalmente por accidente;
- la terminal tiene permisos suficientes;
- no hay procesos usando paquetes dentro de `.venv`.

---

## 6. Configurar `.env`

Crear el archivo `.env` a partir de `.env.example`:

```powershell
copy .env.example .env
```

Completar los valores reales. Variables típicas:

```env
APP_ENV=dev

PGHOST=localhost
PGPORT=5433
PGDATABASE=hidden_gems
PGUSER=postgres
PGPASSWORD=tu_password
PGSCHEMA=hidden_gems

DATA_RAW_PATH=./data/raw
DATA_STAGING_PATH=./data/staging
DATA_REFERENCE_PATH=./data/reference
DATA_ARTIFACTS_PATH=./data/artifacts
DATA_EXTERNAL_PATH=./data/external

GOOGLE_MAPS_API_KEY=
GOOGLE_PLACES_BASE_URL=https://places.googleapis.com/v1
```

Reglas importantes:

```text
- No subir .env a Git.
- No escribir claves reales en documentación.
- No pegar API keys en notebooks públicos.
- Mantener .env.example sin secretos.
```

---

## 7. Preparar PostgreSQL y PostGIS

La base debe existir antes de ejecutar los DDL.

Ejemplo conceptual:

```sql
CREATE DATABASE hidden_gems;
```

Después, conectarse con pgAdmin, DBeaver o psql y ejecutar los scripts SQL del proyecto en orden.

El schema principal esperado es:

```sql
hidden_gems
```

---

## 8. Orden de ejecución de DDL

Ejecutar los scripts de `db/ddl/` en este orden:

```text
00_foundation.sql
01_governance.sql
02_geo_reference.sql
03_core_places.sql
04_classification_and_geo_assignment.sql
05_validation.sql
06_review_enrichment.sql
07_ai_module.sql
08_ai_views.sql
```

### Función de cada bloque

| Script | Función |
|---|---|
| `00_foundation.sql` | Extensiones, schema, enums y funciones comunes. |
| `01_governance.sql` | Fuentes, runs y raw assets. |
| `02_geo_reference.sql` | Distritos y barrios. |
| `03_core_places.sql` | `place`, `place_source_ref`, `review`. |
| `04_classification_and_geo_assignment.sql` | Categorías y asignación a barrio. |
| `05_validation.sql` | Incidencias de calidad. |
| `06_review_enrichment.sql` | Ampliación de `review` para NLP y trazabilidad. |
| `07_ai_module.sql` | Tablas IA y ranking. |
| `08_ai_views.sql` | Vistas SQL de consulta IA. |

No ejecutar los scripts fuera de orden salvo que se sepa exactamente qué dependencias existen.

---

## 9. Comprobar conexión a base de datos

Desde la raíz del proyecto y con `.venv` activo:

```powershell
python -m scripts.check_db_connection
```

Resultado esperado:

```text
Conexión correcta a PostgreSQL
Schema accesible
```

Si falla, revisar:

```text
- PGHOST
- PGPORT
- PGDATABASE
- PGUSER
- PGPASSWORD
- PostgreSQL encendido
- firewall local
- puerto correcto
```

---

## 10. Comprobar schema

Después de ejecutar DDL:

```powershell
python -m scripts.check_schema
```

Este check debe confirmar que las tablas esperadas existen.

Si faltan tablas, comprobar:

- si se ejecutó el DDL completo;
- si se ejecutó sobre la base correcta;
- si el schema configurado coincide con `PGSCHEMA`;
- si hubo errores silenciosos al ejecutar SQL en pgAdmin/DBeaver.

---

## 11. Registrar fuentes base

Ejecutar el seed de fuentes:

```powershell
python -m scripts.seed_source_systems
```

Fuentes esperadas:

```text
sevilla_geo
osm_overpass
google_places
yelp_open_dataset
```

Este paso es importante porque las verticales dependen de `source_system` para registrar `source_run`, `raw_asset`, `place_source_ref` y `review`.

---

## 12. Estructura de carpetas de datos

El proyecto utiliza varias capas en filesystem:

```text
data/raw/        → respuestas fuente originales
data/staging/    → resultados intermedios
data/reference/  → datasets de referencia
data/artifacts/  → reports, checks, logs, summaries
data/external/   → datasets externos grandes
```

Si alguna carpeta no existe, los scripts suelen crearla automáticamente, pero es recomendable revisar:

```powershell
dir data
```

---

## 13. Preparar Google Cloud si se usa Google Places

Para ejecutar Google Places o Google Places Reviews se necesita:

```text
1. Proyecto de Google Cloud.
2. Facturación activa.
3. Places API habilitada.
4. API key creada.
5. API key restringida a Places API.
6. Presupuestos y alertas configurados.
7. Cuotas bajas para desarrollo.
8. GOOGLE_MAPS_API_KEY en .env.
```

Reglas:

```text
- No usar FieldMask: *.
- No lanzar batches grandes al principio.
- Empezar con dry-run.
- Revisar uso en Google Cloud después de tandas reales.
```

---

## 14. Smoke test general

Una vez preparado el entorno, ejecutar:

```powershell
python -m scripts.check_db_connection
python -m scripts.check_schema
python -m scripts.seed_source_systems
```

Después, si existe `main.py` como punto de entrada mínimo:

```powershell
python main.py
```

El objetivo es comprobar que:

```text
- settings cargan correctamente;
- logger funciona;
- conexión DB funciona;
- schema existe;
- no hay errores básicos de importación Python.
```

---

## 15. Preparación para notebooks

Los notebooks IA se ejecutan sobre artefactos de `data/artifacts/ai/`.

Antes de abrir notebooks, comprobar:

```text
- .venv creado e instalado;
- kernel Jupyter apunta al entorno correcto;
- rutas relativas se ejecutan desde la raíz del repo;
- artefactos de entrada existen;
- los outputs pesados no se van a versionar por error.
```

Si se usa VS Code/Jupyter local:

```text
Seleccionar kernel de .venv.
Ejecutar desde notebooks/ pero con ROOT_DIR apuntando a la raíz del repo.
```

---

## 16. Variables y rutas críticas

Antes de ejecutar procesos grandes, confirmar:

```text
PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD
PGSCHEMA
GOOGLE_MAPS_API_KEY si aplica
DATA_RAW_PATH
DATA_STAGING_PATH
DATA_REFERENCE_PATH
DATA_ARTIFACTS_PATH
DATA_EXTERNAL_PATH
```

Los errores de ruta suelen generar:

- archivos no encontrados;
- artefactos en carpetas inesperadas;
- notebooks que no localizan inputs;
- loaders que leen una versión antigua del output.

---

## 17. Criterio de entorno listo

El entorno se considera listo cuando:

```text
[OK] .venv activo
[OK] requirements instalados
[OK] .env configurado
[OK] PostgreSQL accesible
[OK] PostGIS disponible
[OK] DDL ejecutado en orden
[OK] check_db_connection correcto
[OK] check_schema correcto
[OK] seed_source_systems ejecutado
[OK] carpetas data disponibles
[OK] API key configurada si se usa Google Places
```

---

## 18. Problemas frecuentes

### 18.1. El comando no reconoce módulos de `scripts`

Asegurarse de ejecutar desde la raíz del proyecto:

```powershell
python -m scripts.check_db_connection
```

No ejecutar así desde otra carpeta:

```powershell
python scripts/check_db_connection.py
```

El modo recomendado es siempre:

```text
python -m scripts.nombre_script
```

---

### 18.2. Error de conexión a PostgreSQL

Revisar:

```text
- PostgreSQL iniciado;
- puerto correcto, normalmente 5433 en este proyecto;
- contraseña correcta;
- base de datos existente;
- schema creado;
- .env cargado.
```

---

### 18.3. Error por tabla inexistente

Posibles causas:

```text
- falta ejecutar DDL;
- DDL ejecutado en otra base;
- schema incorrecto;
- error previo en SQL;
- no se ejecutó 07_ai_module.sql o 08_ai_views.sql.
```

---

### 18.4. Google Places falla por API key

Revisar:

```text
- GOOGLE_MAPS_API_KEY en .env;
- Places API habilitada;
- facturación activa;
- key restringida correctamente;
- cuota no agotada;
- FieldMask válido.
```

---

## 19. Conclusión

La preparación del entorno es una fase obligatoria antes de ejecutar ingestas, notebooks o loaders.

Hidden Gems depende tanto de PostgreSQL/PostGIS como del filesystem local de artefactos. Por eso el entorno no se considera listo hasta que se han validado:

```text
base de datos + schema + fuentes + carpetas + configuración + checks iniciales
```

Una vez completado este runbook, el siguiente paso natural es seguir el documento:

```text
02_data_ingestion_runbook.md
```
