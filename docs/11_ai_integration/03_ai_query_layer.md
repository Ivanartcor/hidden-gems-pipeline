# 03 - AI Query Layer

## Objetivo

Este documento describe la capa de consulta creada sobre las tablas IA de Hidden Gems.

Una vez cargados los datos IA en PostgreSQL, se creó un script SQL de vistas para facilitar la exploración, auditoría y demostración del ranking.

La implementación está en:

```text
db/ddl/08_ai_views.sql
```

Y el script de demo está en:

```text
scripts/query_ai_ranking_demo.py
```

---

## Por qué crear vistas

Las tablas IA están normalizadas y separadas por responsabilidad:

```text
dish
dish_alias
dish_mention
dish_mention_sentiment
dish_place_signal
hidden_gem_candidate
```

Esto es correcto para integridad y mantenimiento, pero no es cómodo para consulta directa.

Las vistas permiten tener salidas legibles para:

- ver rankings;
- consultar candidatos;
- auditar señales;
- revisar menciones que justifican un candidato;
- exportar resultados para demo o análisis.

---

## Vistas creadas

`08_ai_views.sql` crea las siguientes vistas:

```text
vw_ai_pipeline_run_summary
vw_ai_dish_place_signals
vw_ai_hidden_gem_candidate_detail
vw_ai_hidden_gems_yelp_top
vw_ai_hidden_gems_place_summary
vw_ai_hidden_gems_dish_summary
vw_ai_hidden_gems_city_summary
vw_ai_dish_mentions_with_sentiment
```

---

# 1. `vw_ai_pipeline_run_summary`

## Propósito

Consultar ejecuciones IA registradas.

## Uso

Permite revisar:

- código del run;
- tipo de ejecución;
- estado;
- fecha de inicio y fin;
- métricas;
- artefactos de entrada/salida.

## Ejemplo

```sql
SELECT *
FROM hidden_gems.vw_ai_pipeline_run_summary
ORDER BY started_at DESC;
```

---

# 2. `vw_ai_dish_place_signals`

## Propósito

Consultar señales agregadas por local y plato.

Equivale a una versión legible de `dish_place_signal` unida con `place` y `dish`.

## Uso

Sirve para responder:

```text
¿Qué platos tienen mejor señal en cada local?
¿Qué locales tienen más menciones positivas para un plato?
¿Qué pares local-plato tienen evidencia fuerte?
```

## Ejemplo

```sql
SELECT
    place_name,
    dish_name,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio,
    bayesian_sentiment_score,
    evidence_tier
FROM hidden_gems.vw_ai_dish_place_signals
WHERE is_rankable_candidate = true
ORDER BY bayesian_sentiment_score DESC
LIMIT 50;
```

---

# 3. `vw_ai_hidden_gem_candidate_detail`

## Propósito

Vista detallada de candidatos Hidden Gems.

Une:

```text
hidden_gem_candidate
+ dish_place_signal
+ place
+ dish
```

## Uso

Es la vista más completa para analizar el ranking.

Incluye:

- ranking;
- tier;
- local;
- dirección;
- plato;
- score;
- componentes;
- penalizaciones;
- señales de evidencia;
- explicación textual.

## Ejemplo

```sql
SELECT
    hidden_gem_selected_rank,
    hidden_gem_tier,
    place_name,
    dish_name,
    hidden_gem_score,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio,
    ranking_explanation
FROM hidden_gems.vw_ai_hidden_gem_candidate_detail
WHERE ranking_scope = 'yelp_prototype'
ORDER BY hidden_gem_selected_rank
LIMIT 30;
```

---

# 4. `vw_ai_hidden_gems_yelp_top`

## Propósito

Vista simplificada para demo rápida del ranking Yelp.

Esta es la vista recomendada para enseñar los resultados principales.

## Consulta principal

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_yelp_top
LIMIT 20;
```

## Campos clave

```text
hidden_gem_selected_rank
hidden_gem_tier
place_name
address_text
dish_name
hidden_gem_score
mention_count
review_count
positive_ratio
negative_ratio
evidence_tier
aggregate_quality_tier
ranking_explanation
```

## Ejemplo de resultado esperado

Los primeros candidatos validados son:

```text
1. Sushi Ushi → sushi → 82.92816
2. Taqueria Cuernavaca → tacos → 82.04289
3. Blues City Deli → sandwich → 81.98466
```

---

# 5. `vw_ai_hidden_gems_place_summary`

## Propósito

Resumen por local de candidatos seleccionados.

## Uso

Permite responder:

```text
¿Qué locales tienen más platos candidatos?
¿Qué local tiene el score máximo más alto?
¿Qué locales parecen especialmente fuertes en varias categorías?
```

## Ejemplo

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_place_summary
ORDER BY selected_count DESC, max_hidden_gem_score DESC
LIMIT 30;
```

## Ejemplos observados

En el check final aparecen locales como:

```text
District Donuts Sliders Brew
Jones
Khyber Pass Pub
Luke
Katie's Restaurant & Bar
```

con varios candidatos seleccionados.

---

# 6. `vw_ai_hidden_gems_dish_summary`

## Propósito

Resumen por plato dentro del ranking seleccionado.

## Uso

Permite ver qué platos aparecen más en los candidatos finales.

## Ejemplo

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_dish_summary
ORDER BY selected_count DESC, max_hidden_gem_score DESC
LIMIT 30;
```

## Ejemplos observados

Los platos con más apariciones seleccionadas incluyen:

```text
pizza
burger
sushi
tacos
fries
shrimp
steak
wings
sandwich
oysters
```

---

# 7. `vw_ai_hidden_gems_city_summary`

## Propósito

Resumen por ciudad/dirección geográfica disponible en Yelp.

## Uso

Permite explorar el prototipo por ciudades del dataset Yelp.

## Ejemplo

```sql
SELECT *
FROM hidden_gems.vw_ai_hidden_gems_city_summary
ORDER BY selected_count DESC, max_hidden_gem_score DESC;
```

## Nota

Esta vista todavía no equivale a barrios de Sevilla. Para el producto final habrá que usar `neighborhood` y `place_neighborhood_assignment`.

---

# 8. `vw_ai_dish_mentions_with_sentiment`

## Propósito

Permite auditar las menciones concretas y su sentimiento.

Es clave para explicar por qué un plato recibe una señal positiva o negativa.

## Ejemplo recomendado

```sql
SELECT *
FROM hidden_gems.vw_ai_dish_mentions_with_sentiment
WHERE place_name = 'Sushi Ushi'
  AND dish_name = 'sushi'
ORDER BY sentiment_confidence DESC
LIMIT 25;
```

## Uso

Sirve para:

- revisar menciones positivas/negativas;
- auditar errores del NER;
- verificar sentimiento por mención;
- justificar candidatos de ranking;
- crear muestras de validación manual.

---

## Script de demo: `query_ai_ranking_demo.py`

Además de las vistas SQL, se creó un script Python para consultar la capa IA desde el repositorio.

## Ejecución básica

```powershell
python -m scripts.query_ai_ranking_demo
```

## Top N candidatos

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 20
```

## Exportar resultados

```powershell
python -m scripts.query_ai_ranking_demo `
  --top-n 50 `
  --export-dir data/artifacts/ai/query_demo
```

## Consultar candidato concreto

```powershell
python -m scripts.query_ai_ranking_demo `
  --place-name "Sushi Ushi" `
  --dish-name "sushi" `
  --include-mentions `
  --mentions-top-n 25
```

## Filtrar por ciudad

```powershell
python -m scripts.query_ai_ranking_demo `
  --city "New Orleans" `
  --top-n 30
```

---

## Consultas SQL útiles

### Top 20 candidatos

```sql
SELECT
    hidden_gem_selected_rank,
    hidden_gem_tier,
    place_name,
    dish_name,
    hidden_gem_score,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio
FROM hidden_gems.vw_ai_hidden_gems_yelp_top
LIMIT 20;
```

### Top platos seleccionados

```sql
SELECT
    dish_name,
    selected_count,
    avg_hidden_gem_score,
    max_hidden_gem_score
FROM hidden_gems.vw_ai_hidden_gems_dish_summary
ORDER BY selected_count DESC, max_hidden_gem_score DESC
LIMIT 30;
```

### Top locales con más candidatos

```sql
SELECT
    place_name,
    selected_count,
    avg_hidden_gem_score,
    max_hidden_gem_score
FROM hidden_gems.vw_ai_hidden_gems_place_summary
ORDER BY selected_count DESC, max_hidden_gem_score DESC
LIMIT 30;
```

### Señales rankeables fuertes

```sql
SELECT
    place_name,
    dish_name,
    mention_count,
    review_count,
    positive_ratio,
    negative_ratio,
    bayesian_sentiment_score,
    evidence_tier,
    aggregate_quality_tier
FROM hidden_gems.vw_ai_dish_place_signals
WHERE is_rankable_candidate = true
  AND evidence_tier = 'strong'
ORDER BY bayesian_sentiment_score DESC
LIMIT 50;
```

### Auditoría de menciones positivas de un plato

```sql
SELECT
    place_name,
    dish_name,
    mention_text,
    sentiment_label,
    sentiment_confidence,
    sentiment_reliability_tier,
    target_clause_context
FROM hidden_gems.vw_ai_dish_mentions_with_sentiment
WHERE place_name = 'Sushi Ushi'
  AND dish_name = 'sushi'
  AND sentiment_label = 'positive'
ORDER BY sentiment_confidence DESC
LIMIT 25;
```

---

## Estado de la capa de consulta

La capa de consulta está operativa.

Se ha comprobado que:

```text
08_ai_views.sql se carga correctamente en PostgreSQL.
query_ai_ranking_demo.py funciona correctamente.
Las vistas devuelven candidatos, resúmenes y menciones justificativas.
```

---

## Importante

Las vistas actuales están centradas en `ranking_scope = yelp_prototype`.

Cuando el sistema evolucione hacia Sevilla, será recomendable crear vistas adicionales orientadas a barrios:

```text
vw_ai_hidden_gems_sevilla_top
vw_ai_hidden_gems_by_neighborhood
vw_ai_hidden_gems_neighborhood_dish_summary
```

Para ello será necesario que `hidden_gem_candidate.neighborhood_id` esté poblado.
