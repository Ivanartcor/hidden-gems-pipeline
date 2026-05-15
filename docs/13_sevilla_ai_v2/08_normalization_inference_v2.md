# 08. Inferencia de normalización / Entity Linking v2

## 1. Propósito del documento

Este documento describe la fase de inferencia de normalización de platos dentro de la fase **Sevilla IA v2** de Hidden Gems.

El objetivo de esta etapa es transformar cada mención detectada de un plato en una referencia normalizada del catálogo:

```text
mención textual + contexto + catálogo de platos
→ dish_id normalizado
→ dish_name canónico
→ confianza de normalización
→ estado de revisión
```

Esta fase se ejecuta después de construir la capa **Hybrid + NER candidates v2** y antes de aplicar el modelo de sentimiento por mención.

---

## 2. Rol dentro del pipeline IA v2

La normalización/entity linking se sitúa en este punto del flujo:

```text
Reviews Sevilla
→ extracción híbrida inicial
→ Modelo 1: NER de platos
→ Hybrid + NER candidates v2
→ Normalización / Entity Linking v2
→ Modelo 2: sentimiento ABSA por mención
→ señales place-dish v2
→ ranking Hidden Gems v2
→ dashboard Sevilla IA v2
```

Su función es crítica porque el ranking final no se calcula sobre textos libres como `croquetas`, `croquetitas`, `croqueta de jamón`, `croquetas de cola de toro`, etc., sino sobre entidades normalizadas del catálogo.

---

## 3. Problema que resuelve

Las reseñas contienen menciones de platos escritas de forma irregular:

```text
croquetas
croquetones
croquetas de jamón
croquetas caseras
croquetas de cola de toro
solomillo al whisky
solomillo whisky
tarta queso
cheesecake
```

Sin normalización, el sistema tendría varios problemas:

1. Duplicaría señales que realmente pertenecen al mismo plato.
2. Mezclaría platos diferentes con nombres parecidos.
3. No podría agrupar correctamente por `place_id + dish_id`.
4. El ranking perdería consistencia.
5. El dashboard tendría filtros de platos poco limpios.

La normalización v2 intenta resolver estos problemas enlazando cada mención con el plato correcto del catálogo.

---

## 4. Enfoque aplicado

La solución usada en IA v2 es híbrida:

```text
generación de candidatos por catálogo/aliases/reglas
→ reranking con modelo BETO
→ selección del mejor candidato
→ validación por confianza, margen y calidad
```

No se usa un clasificador cerrado de platos, porque el catálogo puede crecer. En su lugar, se usa un modelo tipo **reranker/cross-encoder** entrenado para decidir si una pareja:

```text
mención + contexto
plato candidato
```

representa una correspondencia correcta.

---

## 5. Modelo utilizado

Modelo local:

```text
models/sevilla_dish_normalization_reranker_beto_v1/
```

Modelo base:

```text
dccuchile/bert-base-spanish-wwm-cased
```

Tipo de tarea:

```text
Sequence Classification binaria
0 = candidato incorrecto
1 = candidato correcto
```

Entrada conceptual:

```text
Texto A:
Mención: ensaladilla de gambas | Contexto: Pedimos ensaladilla de gambas y croquetas...

Texto B:
Plato candidato: ensaladilla de gambas
```

Salida:

```text
match_score = probabilidad de que el candidato sea el plato correcto
```

---

## 6. Script de inferencia

Script principal:

```text
scripts/run_sevilla_dish_normalization_reranker_v1.py
```

Durante el desarrollo también se creó una variante optimizada para evitar tiempos excesivos en CPU:

```text
scripts/run_sevilla_dish_normalization_reranker_v1_fast_progress.py
```

La versión optimizada incorpora:

```text
- índice léxico rápido del catálogo;
- reducción de candidatos irrelevantes;
- progreso visible durante el scoring;
- ejecución más estable en CPU;
- parámetros ajustables de top-k, batch size y longitud máxima.
```

---

## 7. Entrada de la etapa

Entrada principal:

```text
data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/
└── sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl
```

Granularidad:

```text
una fila por mención candidata de plato
```

Campos relevantes de entrada:

```text
review_id
place_id
place_name
selected_mention_text_v2
selected_mention_norm_v2
context_sentence
target_clause_context
source_strategy_v2
needs_manual_review
ready_for_sentiment
```

---

## 8. Catálogo de platos

El script carga el catálogo de platos y aliases desde PostgreSQL.

Durante la ejecución analizada se cargaron aproximadamente:

```text
Catalog dishes: 10.127
Catalog aliases: 10.478
Catalog lexical entries: 11.771
```

La generación de candidatos utiliza:

```text
- coincidencias exactas;
- aliases;
- normalización léxica;
- tokens principales;
- prefijos;
- similitud aproximada;
- candidatos ya sugeridos por la capa anterior, si existen.
```

---

## 9. Salida de la etapa

Carpeta de salida:

```text
data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1/
```

Archivos generados:

```text
sevilla_dish_mentions_normalized_reranker_v1.csv
sevilla_dish_mentions_normalized_reranker_v1.jsonl
sevilla_dish_normalization_low_confidence_v1.csv
sevilla_dish_normalization_no_candidate_v1.csv
sevilla_dish_normalization_summary_v1.json
recommended_next_steps.md
```

Granularidad de la salida principal:

```text
una fila por mención candidata normalizada
```

---

## 10. Estados de normalización

La inferencia asigna un estado a cada fila.

| Estado | Significado |
|---|---|
| `linked` | La mención se enlazó a un plato con confianza suficiente. |
| `linked_needs_review` | Hay enlace, pero la fila arrastra señales revisables o tiene alguna alerta. |
| `low_confidence` | El modelo no tiene suficiente confianza para aceptar automáticamente el enlace. |
| `no_candidate` | No se generó ningún candidato válido del catálogo. |

---

## 11. Resultados obtenidos

Resultado general:

```text
input_rows: 2.965
normalized_rows: 2.965
ready_for_sentiment: 2.880
needs_manual_review: 379
no_candidate_rows: 27
```

Distribución de estados:

```text
linked: 2.586
linked_needs_review: 294
low_confidence: 58
no_candidate: 27
```

Estos resultados indican que la mayoría de menciones pudieron enlazarse correctamente a un plato del catálogo.

---

## 12. Confianza de normalización

La confianza media del reranker fue alta:

```text
mean normalization score: 0.9677
median normalization score: 0.9964
P75: 0.9966
```

Esto indica que, para la mayoría de las menciones, el modelo encontró un candidato claramente preferido.

Aun así, la confianza no debe interpretarse como una garantía absoluta. Por eso se conservan los estados `linked_needs_review`, `low_confidence` y `no_candidate`.

---

## 13. Casos sin candidato

La fase detectó un conjunto pequeño de términos sin candidato claro en catálogo, por ejemplo:

```text
chuleta
cangrejo
anguila
parrillada
cerdo
arenque
macarrones
pescadito
salchicha
vieiras
torreznos
canelones
gambón
centollo
cocochas
```

Algunos de estos términos podrían añadirse como platos o aliases en futuras iteraciones. Otros pueden ser ingredientes, categorías o menciones demasiado genéricas.

---

## 14. Reglas de revisión

No todas las menciones enlazadas se consideran igualmente fiables. La inferencia marca revisión en casos como:

```text
- baja confianza del reranker;
- margen bajo entre el primer y segundo candidato;
- mención procedente de estrategia ner_only;
- fragmentos demasiado cortos o ambiguos;
- menciones compuestas;
- arrastre de revisión desde la capa Hybrid + NER;
- candidato demasiado genérico.
```

Estas marcas son importantes porque las siguientes fases pueden reducir el peso de estas menciones.

---

## 15. Relación con la fase ABSA

La salida de normalización sirve como entrada para el modelo de sentimiento por mención.

Solo las filas normalizadas y preparadas pasan de forma fuerte a la fase ABSA:

```text
normalización enlazada
→ dish_id disponible
→ contexto disponible
→ listo para sentimiento por mención
```

Las filas `no_candidate` o de baja confianza pueden quedar fuera del ranking fuerte o entrar con menor peso.

---

## 16. Decisión técnica

La capa se da por válida como:

```text
sevilla_dish_normalization_reranker_v1
```

pero con esta consideración:

```text
Es una capa de inferencia experimental asistida por modelo, no una capa de producción definitiva.
```

La decisión se basa en:

```text
- cobertura muy alta sobre las menciones;
- pocos casos sin candidato;
- confianza media elevada;
- salida compatible con ABSA;
- trazabilidad de estados y motivos de revisión.
```

---

## 17. Limitaciones

Limitaciones conocidas:

1. La calidad depende de que el catálogo contenga el plato o un alias razonable.
2. Un plato nuevo no puede enlazarse si no existe candidato.
3. El modelo reranker no genera entidades nuevas, solo ordena candidatos.
4. Los platos genéricos pueden competir con platos específicos.
5. Algunas menciones `ner_only` pueden ser experimentales.
6. La confianza alta no elimina la necesidad de revisión en casos dudosos.

---

## 18. Próximas mejoras

Mejoras recomendadas:

```text
- añadir nuevos platos y aliases derivados de no_candidate;
- revisar términos genéricos frecuentes;
- añadir penalización o reglas para platos demasiado amplios;
- crear un flujo de revisión manual para low_confidence;
- descargar automáticamente el modelo desde Drive si no existe en local;
- recalibrar umbrales con evaluación humana.
```

---

## 19. Conclusión

La inferencia de normalización v2 permite convertir menciones textuales en entidades de plato normalizadas, habilitando la agregación por `place_id + dish_id`.

Esta etapa es esencial para que Hidden Gems deje de trabajar sobre menciones sueltas y pase a construir señales gastronómicas consistentes por local y plato.
