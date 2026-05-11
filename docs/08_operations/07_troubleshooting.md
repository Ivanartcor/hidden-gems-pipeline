# 07. Troubleshooting operativo

## 1. Objetivo del documento

Este documento recoge problemas frecuentes detectados durante el desarrollo y operación de **Hidden Gems**, junto con sus causas probables y soluciones recomendadas.

El objetivo no es sustituir los logs ni los checks, sino disponer de una guía rápida para resolver errores habituales en:

```text
PowerShell
Python
PostgreSQL/PostGIS
Google Places
Google Places Reviews
Yelp Open Dataset
notebooks IA
loaders IA
checks y reports
```

---

## 2. Método general para resolver errores

Antes de modificar código o relanzar procesos grandes, seguir este orden:

```text
1. Leer el error completo.
2. Identificar el script/celda exacta que falla.
3. Revisar si el fallo ocurre antes o después de escribir en base de datos.
4. Revisar el artifact o report generado, si existe.
5. Revisar logs en data/artifacts/logs/pipeline.log.
6. Ejecutar el check correspondiente.
7. Repetir primero en dry-run o con límites pequeños.
8. No relanzar batches grandes hasta entender el problema.
```

---

## 3. Problemas de PowerShell

## 3.1. El comando multilínea no funciona

### Síntoma

El comando se corta, se ejecuta parcialmente o PowerShell muestra errores extraños.

### Causa probable

El backtick ``` ` ``` no está colocado correctamente.

En PowerShell, el backtick debe ser el último carácter de la línea, sin espacios después.

### Solución

Correcto:

```powershell
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox
```

Incorrecto:

```powershell
python -m scripts.load_overpass_pipeline ` 
  --south 37.3400
```

El espacio después del backtick rompe el comando.

---

## 3.2. Problemas con `curl` y JSON en Windows

### Síntoma

Una llamada `curl` a Google Places falla aunque la API key sea correcta.

### Causa probable

PowerShell interpreta las comillas del JSON de forma distinta a Bash/CMD.

### Solución

Usar scripts Python del proyecto en vez de `curl` para pruebas reales:

```powershell
python -m scripts.run_google_places_text_search `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_text_search_test `
  --max-result-count 3
```

También se puede usar `curl.exe`, pero para el flujo del proyecto es más seguro usar los scripts.

---

## 3.3. Error SSL `CRYPT_E_NO_REVOCATION_CHECK`

### Síntoma

`curl.exe` falla en Windows con un error de comprobación de revocación de certificado.

### Causa probable

Problema del stack de certificados de Windows al usar `curl.exe`.

### Solución

No usar `curl` para pruebas operativas. Usar Python y `requests` mediante los scripts del repositorio.

---

## 4. Problemas de entorno Python

## 4.1. No se reconoce el módulo `scripts...`

### Síntoma

```text
ModuleNotFoundError
No module named scripts
```

### Causa probable

El comando se está ejecutando fuera de la raíz del repositorio.

### Solución

Ir a la carpeta raíz del proyecto:

```powershell
cd C:\Users\USUARIO\Documents\Proyectos_Master_IA_Big_Data\hidden-gems-pipeline
```

Y ejecutar:

```powershell
python -m scripts.check_db_connection
```

---

## 4.2. Entorno virtual no activado

### Síntoma

Faltan dependencias aunque ya se instalaron.

### Solución

Activar entorno:

```powershell
.venv\Scripts\activate
```

Comprobar Python:

```powershell
python --version
where python
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

---

## 4.3. Error de permisos al instalar paquetes

### Síntoma

```text
WinError 5: Acceso denegado
```

### Causa probable

Se está instalando en Python global o en una ruta protegida.

### Solución

Usar entorno virtual:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 5. Problemas de configuración

## 5.1. Falta `.env`

### Síntoma

Errores de conexión a PostgreSQL o API key no disponible.

### Solución

Crear `.env` a partir de `.env.example`:

```powershell
copy .env.example .env
```

Completar variables reales:

```env
PGHOST=localhost
PGPORT=5433
PGDATABASE=hidden_gems
PGUSER=postgres
PGPASSWORD=...
PGSCHEMA=hidden_gems
GOOGLE_MAPS_API_KEY=...
```

---

## 5.2. API key de Google no configurada

### Síntoma

Google Places falla con error de autenticación o key ausente.

### Solución

Comprobar `.env`:

```env
GOOGLE_MAPS_API_KEY=tu_clave_real
```

Después, relanzar el comando desde una consola nueva o con el entorno cargado.

No subir `.env` a Git.

---

## 6. Problemas de PostgreSQL/PostGIS

## 6.1. No conecta con la base de datos

### Síntoma

```text
connection refused
password authentication failed
database does not exist
```

### Causas probables

- PostgreSQL no está arrancado.
- Puerto incorrecto.
- Usuario/contraseña incorrectos.
- Base de datos no creada.
- `.env` mal configurado.

### Solución

Ejecutar:

```powershell
python -m scripts.check_db_connection
```

Revisar:

```env
PGHOST
PGPORT
PGDATABASE
PGUSER
PGPASSWORD
PGSCHEMA
```

En este proyecto se usa habitualmente el puerto local:

```text
5433
```

---

## 6.2. Falta una tabla

### Síntoma

```text
relation hidden_gems.table_name does not exist
```

### Causa probable

No se ejecutó el DDL correspondiente o se hizo en otro schema/base.

### Solución

Ejecutar o revisar el orden de DDL:

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

Después comprobar:

```powershell
python -m scripts.check_schema
```

---

## 6.3. Error `No space left on device`

### Síntoma

PostgreSQL muestra:

```text
No space left on device
no se pudo escribir a archivo base/pgsql_tmp/...
```

### Causa probable

Una consulta generó temporales muy grandes. Ya ocurrió con una versión inicial de un check que hacía varios `LEFT JOIN` pesados.

### Solución

1. Liberar espacio en disco.
2. Evitar relanzar la consulta pesada.
3. Usar la versión optimizada del check.
4. Si existe opción, usar límites o checks por partes.
5. Revisar índices y joins.

Scripts relacionados:

```text
scripts/check_ai_downstream_import_readiness.py
```

La versión actual debe hacer conteos separados para evitar productos intermedios grandes.

---

## 7. Problemas de Google Places

## 7.1. La API devuelve error

### Posibles causas

```text
- API key ausente o incorrecta
- Places API no habilitada
- facturación no activada
- cuota agotada
- FieldMask incorrecto
- petición mal formada
```

### Solución

Revisar en Google Cloud:

```text
1. Proyecto correcto.
2. Places API habilitada.
3. Facturación activa.
4. API key válida.
5. Restricción de API compatible.
6. Cuotas y uso.
```

En el proyecto, probar con un batch pequeño:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_dry_run `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 1 `
  --dry-run
```

Luego sin importación:

```powershell
python -m scripts.run_google_places_neighborhood_batch `
  --batch-name gp_test_no_import `
  --neighborhood "SANTA CRUZ" `
  --queries-per-neighborhood 1 `
  --max-result-count 3 `
  --skip-import
```

---

## 7.2. Respuesta sin `places`

### Síntoma

El check raw indica que no hay lista de places o la lista está vacía.

### Causa probable

La búsqueda no devuelve resultados o el texto de query no es adecuado.

### Solución

Probar un `text_query` más natural:

```text
restaurantes en Triana, Sevilla
bares de tapas en Santa Cruz, Sevilla
cafeterías en Nervión, Sevilla
```

Revisar alias en:

```text
src/config/google_places_query_plan.yaml
```

---

## 7.3. Error por rutas largas en Windows

### Síntoma

Fallos al escribir raw/staging por ruta demasiado larga.

### Causa probable

`query_name` demasiado largo combinado con estructura de carpetas profunda.

### Solución

Usar nombres de batch y query más cortos:

```text
gp_sevilla_ai_pilot_01_import
gp_reviews_ai_pilot_01_import
```

Evitar incluir frases completas muy largas en `query_name`.

---

## 7.4. El barrio no coincide por tildes

### Síntoma

`Nervión` no se encuentra, pero `NERVION` sí existe en base.

### Causa probable

Diferencia entre nombres oficiales normalizados y nombres de búsqueda.

### Solución

Usar el nombre oficial esperado o revisar aliases en:

```text
src/config/google_places_query_plan.yaml
```

La lógica debe normalizar tildes mediante `unicodedata` cuando proceda.

---

## 8. Problemas de Google Places Reviews

## 8.1. Un local devuelve 0 reviews

### Síntoma

El pipeline no importa reviews para un local.

### Causa probable

Google no garantiza devolver reviews para todos los Place Details o puede devolver un subconjunto limitado.

### Solución

No considerarlo error salvo que se haya usado:

```powershell
--require-reviews
```

Para batches normales, permitir 0 reviews.

---

## 8.2. Reviews duplicadas

### Síntoma

Una segunda ejecución podría parecer que repite reviews.

### Explicación

La importación es idempotente. El identificador se calcula mediante hash estable.

Lo esperado en una segunda ejecución sobre el mismo raw es:

```text
inserted_count = 0
updated_count > 0
```

No es un problema si no aumenta el número total de reviews únicas.

---

## 8.3. Check de reviews falla por mapeo place/ref

### Causa probable

El Google Place ID del raw no coincide con la `place_source_ref` esperada.

### Solución

Revisar:

```text
place_source_ref_id
google_place_id
source_place_record_id
```

Ejecutar el check específico:

```powershell
python -m scripts.check_google_places_reviews_import `
  --raw-asset-id <RAW_ASSET_ID> `
  --save-artifact
```

---

## 9. Problemas con Yelp Open Dataset

## 9.1. Intentar abrir JSONL completo con `json.load`

### Síntoma

El proceso se queda bloqueado o consume demasiada memoria.

### Causa probable

Los ficheros de Yelp son JSON Lines y algunos pesan varios GB.

### Solución

Leer línea a línea:

```python
for line in file:
    row = json.loads(line)
```

Usar los scripts existentes:

```powershell
python -m scripts.profile_yelp_jsonl_files
python -m scripts.build_yelp_food_review_subset
```

---

## 9.2. Falsos positivos en negocios gastronómicos

### Síntoma

Aparecen negocios no gastronómicos en el subset.

### Causa probable

Categorías de Yelp ambiguas.

### Solución

Revisar filtros de categorías en:

```text
scripts/build_yelp_food_business_subset.py
```

Y validar el summary antes de construir corpus.

---

## 10. Problemas en notebooks IA

## 10.1. `KeyError` por columna inexistente

### Síntoma

```text
KeyError: 'food_term_count'
KeyError: 'place_id'
KeyError: ['ranking_explanation_v1'] not in index
```

### Causa probable

Una celda espera una columna que no se creó, se renombró o quedó como índice tras un `groupby`.

### Solución general

1. Inspeccionar columnas:

```python
list(df.columns)
```

2. Validar columnas antes de seleccionar:

```python
available_cols = [c for c in desired_cols if c in df.columns]
display(df[available_cols].head())
```

3. Si el problema viene de `groupby.apply`, evitar depender de columnas de agrupación dentro del grupo o usar funciones robustas.

---

## 10.2. `json.dumps` falla con `numpy.bool_`

### Síntoma

```text
TypeError: Object of type bool is not JSON serializable
```

### Causa probable

El valor no es `bool` puro de Python, sino `numpy.bool_`.

### Solución

Convertir explícitamente:

```python
basic_checks = {
    "has_rows": bool(len(df) > 0),
    "all_have_place": bool(df["place_id"].notna().all()),
}
```

---

## 10.3. Summary JSON no se puede subir o validar

### Síntoma

El JSON se abre en editor, pero algunas herramientas lo rechazan.

### Causa probable

Contiene valores no válidos para JSON estricto:

```text
NaN
Infinity
-Infinity
NaT
```

### Solución

Antes de guardar summaries:

```python
json.dump(clean_obj, f, indent=2, ensure_ascii=False, allow_nan=False)
```

Y convertir `NaN`/`Infinity` a `None`.

Después releer el JSON para validarlo:

```python
with open(path, encoding="utf-8") as f:
    json.load(f)
```

---

## 10.4. Warning de regex `invalid escape sequence`

### Síntoma

```text
SyntaxWarning: invalid escape sequence '\ '
```

### Causa probable

Uso de string normal con backslash en regex.

### Solución

Usar raw strings cuando proceda:

```python
r"\s+"
```

O evitar reemplazos con escapes incorrectos.

---

## 11. Problemas de loaders IA

## 11.1. Faltan mappings de review/place/dish

### Síntoma

El loader salta registros con contadores como:

```text
skipped_missing_review_mapping > 0
skipped_missing_place_mapping > 0
skipped_missing_dish_mapping > 0
```

### Causa probable

Los artefactos IA no corresponden con las entidades cargadas en PostgreSQL.

### Solución

Ejecutar readiness antes de cargar:

```powershell
python -m scripts.check_ai_downstream_import_readiness
```

Para Sevilla:

```powershell
python -m scripts.check_ai_review_export
python -m scripts.check_sevilla_ai_pilot_loaded
```

No cargar resultados si hay mapeos faltantes críticos.

---

## 11.2. Ranking scope no acepta `sevilla_pilot`

### Síntoma

La base rechaza `ranking_scope = sevilla_pilot`.

### Causa probable

El DDL actual de `hidden_gem_candidate.ranking_scope` no incluye ese valor como scope nativo.

### Solución adoptada

Guardar en base:

```text
db_ranking_scope = other
```

Y conservar el scope real del artefacto en JSON:

```text
artifact_ranking_scope = sevilla_pilot
```

Esto es correcto para el piloto actual.

Si más adelante se quiere scope nativo, habrá que modificar el DDL.

---

## 12. Problemas de checks

## 12.1. Un check tarda demasiado

### Causa probable

Consulta pesada, joins grandes o falta de filtros.

### Solución

1. Esperar si el dataset es grande, pero no indefinidamente.
2. Revisar si el script tiene flags de límite.
3. Usar versión optimizada del check.
4. Evitar consultas con grandes `LEFT JOIN` agregados.
5. Revisar espacio en disco.

---

## 12.2. `warnings` no está vacío

### Interpretación

No siempre significa fallo.

Regla:

```text
errors != [] → bloquear o revisar antes de seguir
warnings != [] → revisar y decidir
```

Si el warning es esperado y documentado, se puede continuar.

---

## 12.3. `ready_for... = false`

### Solución

No continuar con la fase siguiente hasta entender por qué.

Ejemplos:

```text
ready_to_load_dish_mentions = false
ready_for_querying_ai_ranking = false
ready_for_sevilla_pilot_queries = false
```

Cada uno indica que falta una condición crítica.

---

## 13. Problemas de consulta demo

## 13.1. La consulta devuelve menos candidatos de los esperados

### Causa probable

Se está usando un filtro por distrito, barrio, plato o local.

Ejemplo:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --district "Casco Antiguo" `
  --limit 20
```

Puede devolver solo los candidatos de ese distrito.

### Solución

Ejecutar sin filtros para vista global:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

---

## 13.2. No aparecen menciones justificativas

### Causa probable

No se usó `--include-mentions` o no hay menciones para ese filtro.

### Solución

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --place-name "Golondrinas" `
  --include-mentions `
  --limit 10
```

---

## 14. Checklist rápido por tipo de problema

## 14.1. Si falla una ingesta

```text
[ ] Revisar API/configuración.
[ ] Revisar raw_asset.
[ ] Ejecutar check raw.
[ ] Revisar logs.
[ ] Repetir con --skip-import o límite bajo.
```

## 14.2. Si falla una importación

```text
[ ] Revisar staging.
[ ] Ejecutar check staging.
[ ] Revisar campos obligatorios.
[ ] Revisar mapeos place/source_ref.
[ ] Ejecutar import en dry-run si existe.
```

## 14.3. Si falla IA

```text
[ ] Revisar columnas del artefacto.
[ ] Revisar mappings review/place/dish.
[ ] Ejecutar check de readiness.
[ ] Validar JSONL/CSV.
[ ] Revisar NaN/Infinity.
```

## 14.4. Si falla PostgreSQL

```text
[ ] Revisar conexión.
[ ] Revisar schema.
[ ] Revisar DDL ejecutado.
[ ] Revisar espacio en disco.
[ ] Revisar query pesada.
```

---

## 15. Conclusión

La mayoría de errores del proyecto se resuelven aplicando la misma filosofía:

```text
ejecutar poco
validar mucho
guardar reports
no avanzar con checks fallidos
```

Hidden Gems ya cuenta con suficientes scripts de comprobación para que casi ningún fallo deba resolverse a ciegas.

Cuando aparezca un error nuevo, la solución recomendada es incorporarlo a este documento para que el runbook operativo siga creciendo con el proyecto.
