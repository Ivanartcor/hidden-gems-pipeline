# Fuente de datos: Yelp Open Dataset

## 1. Descripción general

**Yelp Open Dataset** se incorpora a Hidden Gems como fuente externa de apoyo para análisis textual e inteligencia artificial.

A diferencia de Sevilla Geo, Overpass y Google Places, Yelp no se utiliza como fuente productiva para descubrir locales de Sevilla ni como ranking final por barrio.

Su valor principal es aportar volumen de negocios y reseñas gastronómicas para:

- construir corpus NLP;
- entrenar y validar modelos;
- prototipar extracción de platos;
- probar sentimiento por mención;
- validar agregación y ranking;
- comprobar integración IA en PostgreSQL.

Flujo:

```text
Yelp Open Dataset
→ dataset externo local
→ extracción controlada
→ subset gastronómico
→ corpus NLP
→ entrenamiento/evaluación IA
→ prototipo IA integrado en PostgreSQL
```

No es:

```text
Yelp Open Dataset
→ ranking productivo de Sevilla
```

---

## 2. Rol dentro del pipeline

Yelp actúa como:

1. corpus textual gastronómico amplio;
2. fuente prototipo para validar integración IA.

Usos realizados:

- limpieza y normalización textual;
- sentimiento general desde rating como baseline;
- entrenamiento/prototipado de modelos;
- detección de platos mediante NER;
- normalización de platos;
- sentimiento por mención;
- agregación de señales;
- ranking Hidden Gems v1;
- carga de resultados IA en PostgreSQL.

---

## 3. Diferencia respecto a otras fuentes

| Fuente | Rol principal | Uso operativo Sevilla | Uso IA/NLP |
|---|---|---:|---:|
| Sevilla Geo | Referencia territorial | Sí | No |
| OSM / Overpass | POIs abiertos | Sí | No directo |
| Google Places | Descubrimiento/enriquecimiento | Sí | Parcial |
| Google Places Reviews | Reviews locales reales | Sí | Sí |
| Yelp Open Dataset | Corpus externo/prototipo | No producción | Sí |

La diferencia clave es:

```text
Google Reviews → review → place → barrio/distrito → sevilla_pilot
Yelp Reviews   → corpus externo → yelp_prototype
```

---

## 4. Restricciones de uso

Reglas aplicadas:

- no subir dataset original al repositorio;
- no compartir ficheros originales;
- no publicar reseñas completas;
- no usar Yelp como fuente comercial;
- no usar Yelp como sustituto de Google Places para Sevilla;
- mantener `data/external/` fuera de Git;
- mantener JSONL pesados fuera de Git;
- documentar métricas y summaries, no contenido sensible;
- marcar resultados como prototipo.

---

## 5. Ficheros usados

Dataset local:

```text
data/external/yelp_open_dataset/yelp_dataset-001.tar
```

Ficheros usados:

```text
yelp_academic_dataset_business.json
yelp_academic_dataset_review.json
```

No usados inicialmente:

```text
yelp_academic_dataset_user.json
yelp_academic_dataset_checkin.json
yelp_academic_dataset_tip.json
```

---

## 6. Formato

JSON Lines:

```text
un objeto JSON por línea
```

Lectura en streaming:

```python
for line in file:
    row = json.loads(line)
```

No se usa `json.load(file)` por volumen.

---

## 7. Ubicación local recomendada

```text
data/external/yelp_open_dataset/
  yelp_dataset-001.tar
  extracted/
    yelp_academic_dataset_business.json
    yelp_academic_dataset_review.json

data/staging/yelp_open_dataset/
  food_businesses.jsonl
  food_business_ids.txt
  food_businesses_summary.json
  food_reviews.jsonl
  food_reviews_summary.json

data/artifacts/nlp_corpus/
  yelp_food_reviews_corpus_sample_100k_lines.jsonl
  yelp_food_reviews_corpus_sample_100k_lines_summary.json

data/artifacts/ai/
  normalization/
  sentiment/
  aggregation/
  ranking/
  checks/
```

---

## 8. Source system

```text
source_code = yelp_open_dataset
source_type = bulk_dataset
auth_type = none
data_format_default = jsonl
refresh_mode_default = snapshot
supports_incremental = false
```

Yelp puede cargarse parcialmente en PostgreSQL, pero solo para crear el puente necesario con los artefactos IA.

---

## 9. Información aportada

### Business

- `business_id`;
- nombre;
- dirección;
- ciudad/estado;
- coordenadas;
- rating;
- número de reseñas;
- categorías;
- atributos.

### Review

- `review_id`;
- `business_id`;
- `user_id`;
- `stars`;
- texto;
- fecha;
- votos útiles/funny/cool.

---

## 10. Decisión de integración

Yelp se puede importar como:

```text
Yelp business → place + place_source_ref
Yelp review   → review
```

siempre que el objetivo sea validar IA y no producción Sevilla.

El ranking derivado se marca como:

```text
ranking_scope = yelp_prototype
is_production_ready = false
```

---

## 11. Encaje con el modelo

### Core/prototipo

```text
business_id → place_source_ref.source_record_id → place_id
review_id   → review.source_review_id → review_id interno
```

Tablas:

- `source_system`;
- `source_run`;
- `raw_asset`;
- `place`;
- `place_source_ref`;
- `review`.

### Capa IA

- `ai_model_version`;
- `ai_pipeline_run`;
- `dish`;
- `dish_alias`;
- `dish_mention`;
- `dish_mention_sentiment`;
- `dish_place_signal`;
- `hidden_gem_candidate`.

---

## 12. Flujo implementado

Fuente:

```text
Yelp TAR
→ profile TAR
→ extract selected files
→ profile JSONL
→ build food business subset
→ build food review subset
→ build NLP corpus
→ check NLP corpus
```

Integración IA:

```text
food_businesses.jsonl + food_reviews.jsonl
→ load_yelp_ai_core_reviews.py
→ place / place_source_ref / review
→ check_ai_downstream_import_readiness.py
→ load_ai_mentions_and_sentiment.py
→ dish_mention / dish_mention_sentiment
→ load_ai_signals_and_ranking.py
→ dish_place_signal / hidden_gem_candidate
→ check_ai_ranking_loaded.py
→ query_ai_ranking_demo.py
```

---

## 13. Scripts implementados

Fuente:

- `scripts/profile_yelp_tar.py`;
- `scripts/extract_yelp_selected_files.py`;
- `scripts/profile_yelp_jsonl_files.py`;
- `scripts/build_yelp_food_business_subset.py`;
- `scripts/build_yelp_food_review_subset.py`;
- `scripts/build_yelp_nlp_corpus.py`;
- `scripts/check_yelp_nlp_corpus.py`.

Integración IA:

- `scripts/load_yelp_ai_core_reviews.py`;
- `scripts/check_ai_downstream_import_readiness.py`;
- `scripts/load_ai_mentions_and_sentiment.py`;
- `scripts/load_ai_signals_and_ranking.py`;
- `scripts/check_ai_ranking_loaded.py`;
- `scripts/query_ai_ranking_demo.py`.

---

## 14. Resultados fuente

Perfilado inicial:

```text
member_file_count = 6
total_size_gb ≈ 8.654
business.json ≈ 113 MB
review.json ≈ 5.094 GB
```

Subset gastronómico:

```text
food_businesses = 66.770
```

Corpus NLP de muestra:

```text
documents = 79.270
train = 63.540
validation = 7.849
test = 7.881
language = en
```

Labels derivados de rating:

```text
positive = 54.857
neutral = 9.835
negative = 14.578
```

---

## 15. Resultados de integración IA Yelp

Estado validado:

```text
dish = 9.937
dish_alias = 10.235
dish_mention = 94.932
dish_mention_sentiment = 94.932
dish_place_signal = 31.036
hidden_gem_candidate = 622
```

Ranking:

```text
ranking_scope = yelp_prototype
ranking_version = hidden_gems_ranking_v1
selected_candidates = 622
production_ready_rows = 0
```

---

## 16. Relación con Google Reviews Sevilla

Yelp permitió construir la arquitectura IA amplia.

Google Reviews Sevilla permitió ejecutarla en contexto local real.

| Aspecto | Google Reviews | Yelp Open Dataset |
|---|---|---|
| Locales Sevilla | Sí | No |
| Enlace a barrio | Sí | No productivo |
| Uso operativo | Sí | No producción |
| Corpus IA | Local/español | Externo/inglés |
| Ranking | `sevilla_pilot` | `yelp_prototype` |

La relación correcta es:

```text
Yelp corpus
→ entrenamiento amplio / baseline / prototipo

Google Reviews Sevilla
→ validación local / piloto / futura producción
```

---

## 17. Diferencia entre `yelp_prototype` y `sevilla_pilot`

### `yelp_prototype`

- fuente: Yelp;
- corpus amplio;
- principalmente inglés;
- no tiene valor territorial Sevilla;
- sirve para validar arquitectura IA;
- no producción.

### `sevilla_pilot`

- fuente: Google Places Reviews;
- corpus local Sevilla;
- español/multilingüe;
- enlazado a barrio y distrito;
- sirve para validar el caso real local;
- todavía no producción.

---

## 18. Calidad y validación

Yelp valida:

- TAR;
- extracción;
- JSONL;
- negocios gastronómicos;
- reviews;
- corpus NLP;
- mappings a `place` y `review`;
- mappings a `dish`;
- ausencia de huérfanos IA;
- ranking consultable.

---

## 19. Riesgos y mitigaciones

### Riesgos

- Yelp no representa Sevilla;
- corpus mayoritariamente inglés;
- sentimiento desde rating es etiqueta débil;
- volumen elevado;
- no publicar reseñas completas;
- riesgo de confundir prototipo con producto.

### Mitigaciones

- `ranking_scope = yelp_prototype`;
- `is_production_ready = false`;
- documentación clara;
- JSONL fuera de Git;
- uso de Google Reviews para Sevilla;
- separación entre prototipo y piloto local.

---

## 20. Estado actual

Yelp queda implementado y validado como corpus/prototipo.

Estado:

```text
[OK] TAR perfilado
[OK] extracción selectiva
[OK] JSONL profiling
[OK] subset gastronómico
[OK] corpus NLP
[OK] check del corpus
[OK] integración IA en PostgreSQL
[OK] ranking yelp_prototype
[OK] vistas SQL
[OK] demo de consulta
```

El foco actual del proyecto ya se ha desplazado hacia:

```text
Google Reviews Sevilla
→ sevilla_pilot
→ dashboard
→ revisión de ranking
→ posible mejora IA
```

---

## 21. Fuera de alcance

No forma parte de Yelp:

- producción Sevilla;
- ranking por barrio local;
- publicar reseñas completas;
- sustituir Google Places;
- marcar candidatos como production ready;
- usar Yelp como fuente comercial.

---

## 22. Próximos pasos relacionados

- mantener Yelp como benchmark/corpus de apoyo;
- usarlo si se entrenan modelos mejores;
- comparar errores Yelp vs Sevilla;
- no mezclar sus resultados con ranking local;
- mantener documentación y scripts de integración.

---

## 23. Conclusión

Yelp Open Dataset queda integrado como fuente de apoyo IA.

Su función ya se ha cumplido en gran parte: permitió construir y validar la arquitectura IA completa.

El proyecto ya ha dado el siguiente paso con Google Reviews Sevilla y el piloto `sevilla_pilot`, por lo que Yelp debe mantenerse como corpus/benchmark, no como eje de producto local.


---

## 24. Relación con la fase Sevilla IA v2

Yelp no participa como fuente operativa local en Sevilla IA v2, pero sí conserva valor como antecedente y soporte metodológico.

Su papel en el proyecto queda actualizado así:

```text
Yelp Open Dataset
→ corpus amplio / prototipo IA / benchmark
→ ayuda a diseñar el flujo de IA
→ no producción local Sevilla
```

La fase Sevilla IA v2 utiliza como base real:

```text
Google Places Reviews Sevilla
→ modelos entrenados/adaptados
→ ranking local v2
```

Por tanto, Yelp queda separado de los resultados finales del dashboard Sevilla IA v2. Esta separación evita mezclar datos externos no territoriales con resultados locales de Sevilla.

---

## 25. Utilidad actual de Yelp tras cerrar la entrega

Aunque el foco final está en Google Reviews Sevilla, Yelp sigue siendo útil para:

- justificar la evolución inicial del módulo IA;
- disponer de un corpus grande para pruebas futuras;
- comparar enfoques de sentimiento y extracción de platos;
- validar scripts generales de carga IA;
- probar nuevas arquitecturas sin consumir cuotas de Google;
- servir como benchmark externo.

No debe usarse para:

- ranking local Sevilla;
- visualización de Hidden Gems Sevilla;
- resultados productivos;
- inferencias territoriales por barrio sevillano.

---

## 26. Estado final actualizado

Yelp queda cerrado como fuente de apoyo:

```text
[OK] corpus/prototipo IA validado
[OK] integración PostgreSQL validada
[OK] ranking yelp_prototype consultable
[OK] utilidad metodológica para la IA del proyecto
[NO] producción Sevilla
[NO] dashboard Sevilla IA v2
```

El foco final de la entrega se apoya en Google Places Reviews para resultados locales, manteniendo Yelp como corpus externo documentado y controlado.
