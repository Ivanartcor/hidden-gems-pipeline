# 01. Recolección de datos Google Places para el piloto Sevilla


## 1. Objetivo

El objetivo de esta fase fue construir un corpus real de locales y reseñas de Sevilla utilizando Google Places como fuente operativa principal.

Esta fase era necesaria porque los módulos IA desarrollados previamente necesitaban una entrada realista para pasar de un prototipo basado en datasets externos a un flujo conectado con el caso de uso principal de Hidden Gems: descubrir **platos destacados por barrio** en Sevilla.

El resultado esperado era disponer de:

- locales reales de Sevilla;
- referencias externas trazables de Google Places;
- reseñas asociadas a esos locales;
- asignación territorial a barrio y distrito;
- un JSONL limpio para ejecutar la fase IA.

## 2. Flujo de adquisición

La adquisición se ejecutó en dos niveles:

```text
1. Google Places Text Search
   → descubre locales gastronómicos por barrio/distrito.

2. Google Places Details / Reviews
   → obtiene reseñas de los locales descubiertos.
```

Una vez importados los datos en PostgreSQL, se ejecutó un exportador específico para IA:

```text
PostgreSQL
→ export_reviews_for_ai.py
→ reviews_for_ai_google_places.jsonl
```

Este diseño evita que los notebooks IA llamen directamente a Google o dependan de tablas internas sin contrato. La frontera entre adquisición e IA queda definida por un artefacto estándar: el JSONL de reviews.

## 3. Scripts utilizados

### 3.1. Batch de locales

Script principal:

```text
scripts/run_google_places_neighborhood_batch.py
```

Función:

- genera consultas por barrio/distrito;
- llama a Google Places Text Search;
- guarda raw assets;
- transforma resultados;
- deduplica candidatos;
- importa o actualiza `place` y `place_source_ref`;
- mantiene trazabilidad mediante `source_run` y `raw_asset`.

Script de validación:

```text
scripts/check_google_places_batch.py
```

Función:

- valida plan de consultas;
- comprueba conteos ejecutados;
- revisa errores;
- valida transformaciones;
- valida importación;
- genera reporte en `data/artifacts/google_places_batches/`.

### 3.2. Batch de reseñas

Script principal:

```text
scripts/run_google_places_reviews_batch.py
```

Función:

- localiza `place_source_ref` de Google Places pendientes de reseñas;
- llama a Google Places Details para obtener reseñas;
- guarda raw assets;
- valida staging;
- importa reseñas a `review`;
- evita repetir locales ya procesados salvo que se indique explícitamente.

Script de validación:

```text
scripts/check_google_places_reviews_batch.py
```

Función:

- valida número de locales planificados y ejecutados;
- comprueba conteos de reseñas raw/staging/importadas;
- detecta duplicados;
- valida checks internos;
- genera reporte en `data/artifacts/google_places_reviews_batches/`.

## 4. Estrategia de ejecución

La adquisición se realizó de forma incremental y controlada, no como una ejecución masiva única.

El flujo seguido fue:

```text
1. Batch pequeño de locales.
2. Check del batch de locales.
3. Batch pequeño de reseñas.
4. Check del batch de reseñas.
5. Revisión de conteos reales.
6. Ampliación por barrios/distritos.
7. Nuevos batches de reseñas.
8. Repetición hasta alcanzar volumen suficiente.
```

Este enfoque permitió controlar:

- coste de llamadas;
- errores de API;
- duplicados;
- locales ya procesados;
- cobertura territorial;
- calidad de los datos importados.

## 5. Cobertura territorial

La adquisición se orientó a cubrir la ciudad de Sevilla por barrios y distritos.

El corpus final exportado para IA cubrió:

| Elemento | Valor |
|---|---:|
| Distritos cubiertos | 11 |
| Barrios cubiertos | 96 |
| Locales únicos exportados | 831 |
| Reviews exportadas | 4.110 |

La cobertura territorial fue suficiente para generar rankings por:

- Sevilla global;
- distrito;
- barrio;
- plato;
- local-plato.

## 6. Volumen final conseguido

Al cerrar la recolección se disponía de:

```text
800+ locales de Google Places
4.000+ reviews de Google Places
```

El exportador para IA generó finalmente:

| Métrica | Valor |
|---|---:|
| Reviews exportadas | 4.110 |
| Locales únicos | 831 |
| Barrios únicos | 96 |
| Distritos únicos | 11 |
| Reviews sin texto | 0 |
| Reviews sin barrio | 0 |
| Reviews sin distrito | 0 |
| Duplicados por review_id | 0 |

Distribución de idioma:

| Idioma | Reviews |
|---|---:|
| `es` | 4.108 |
| `fr` | 1 |
| `pt` | 1 |

La presencia de dos reseñas no españolas no afectó al prototipo, ya que el volumen español era claramente dominante.

## 7. Exportación para IA

Una vez importadas las reseñas, se creó el script:

```text
scripts/export_reviews_for_ai.py
```

Comando principal utilizado:

```powershell
python -m scripts.export_reviews_for_ai `
  --source-code google_places `
  --only-operational `
  --only-training-eligible `
  --min-text-length 20 `
  --output-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

El JSONL resultante contiene una review por línea, con información suficiente para IA y trazabilidad:

```json
{
  "review_id": "...",
  "place_id": "...",
  "place_source_ref_id": "...",
  "source_system_code": "google_places",
  "source_review_id": "...",
  "source_place_record_id": "...",
  "place_name": "...",
  "address_text": "...",
  "city": "Sevilla",
  "district_id": "...",
  "district_name": "...",
  "neighborhood_id": "...",
  "neighborhood_name": "...",
  "rating_value": 5.0,
  "review_language": "es",
  "review_created_at": "...",
  "text": "...",
  "text_normalized": "...",
  "is_operational_review": true,
  "is_training_eligible": true
}
```

## 8. Validación del export

Después del exportador se ejecutó:

```text
scripts/check_ai_review_export.py
```

Comando utilizado:

```powershell
python -m scripts.check_ai_review_export `
  --input-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl `
  --summary-path data/artifacts/ai/sevilla/reviews_for_ai_google_places_summary.json `
  --report-path data/artifacts/ai/sevilla/check_reviews_for_ai_google_places.json `
  --expected-source-code google_places `
  --min-rows 3000 `
  --min-text-length 20 `
  --require-neighborhood `
  --check-sevilla-bbox
```

El check confirmó:

- volumen suficiente para piloto;
- textos presentes;
- no duplicados críticos;
- barrios y distritos presentes;
- source code correcto;
- corpus preparado para notebooks IA.

## 9. Artefactos generados

Artefactos principales de esta fase:

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
data/artifacts/ai/sevilla/reviews_for_ai_google_places_summary.json
data/artifacts/ai/sevilla/check_reviews_for_ai_google_places.json
```

Artefactos de batches:

```text
data/artifacts/google_places_batches/<batch_name>/batch_check.json
data/artifacts/google_places_reviews_batches/<batch_name>/reviews_batch_check.json
```

## 10. Decisiones tomadas

### 10.1. Cerrar recolección con más de 4.000 reviews

Se decidió cerrar la recolección cuando se alcanzó una base de más de 4.000 reseñas y más de 800 locales, porque era suficiente para un piloto IA serio.

Seguir recolectando más datos antes de probar el flujo IA habría retrasado la validación del pipeline sin garantizar una mejora proporcional en resultados.

### 10.2. Trabajar con JSONL como contrato IA

Los notebooks no leen directamente de PostgreSQL. Leen el JSONL exportado.

Ventajas:

- reproducibilidad;
- desacoplamiento entre base de datos e IA;
- posibilidad de mover el experimento a local, Kaggle o Colab;
- revisión sencilla de datos;
- versionado de artefactos.

### 10.3. Mantener `is_production_ready = false`

Aunque el volumen es suficiente para un piloto, el ranking resultante no se marca como producción porque:

- Google Places ofrece una muestra limitada de reseñas por local;
- algunas señales local-plato tienen poca evidencia;
- el sentimiento es híbrido/reglas, no validado manualmente de forma exhaustiva;
- el ranking necesita evaluación humana antes de exposición pública.

## 11. Resultado de la fase

La fase de recolección y exportación quedó completada con éxito.

Entrada disponible para IA:

```text
data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl
```

Este archivo se convirtió en la base de los notebooks 12–17 del piloto IA Sevilla.
---

## 12. Relación con la fase Sevilla IA v2

La recolección de Google Places documentada aquí no queda obsoleta con la fase v2.

Esta capa sigue siendo la base de datos real sobre la que se construyeron las fases posteriores:

```text
Google Places Sevilla
→ reviews reales
→ export JSONL IA
→ piloto Sevilla v1
→ evolución Sevilla IA v2
```

La diferencia es que:

| Fase | Uso del corpus |
|---|---|
| Sevilla pilot v1 | Usa el corpus para detección híbrida, normalización reglada, sentimiento híbrido y ranking piloto. |
| Sevilla IA v2 | Usa la base local y artefactos derivados para aplicar modelos entrenados, normalización reranker, ABSA, ranking v2 y dashboard. |

Por tanto, este documento debe mantenerse como referencia de:

- cómo se obtuvo el corpus local;
- qué volumen inicial había;
- qué contrato JSONL se generó;
- qué garantías tenía la entrada real usada por las fases IA.
