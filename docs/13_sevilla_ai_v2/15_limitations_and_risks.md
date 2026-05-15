# 15. Limitaciones y riesgos de la fase IA v2

## 1. Objetivo del documento

Este documento recoge las principales limitaciones, riesgos y cautelas de interpretación del ranking Hidden Gems Sevilla IA v2.

La fase IA v2 mejora de forma significativa el pipeline inicial, pero no convierte automáticamente el sistema en un producto de producción. El ranking debe interpretarse como:

```text
ranking experimental asistido por modelos
```

y no como una verdad definitiva sobre los mejores platos de Sevilla.

---

## 2. Estado experimental

Todos los candidatos seleccionados en v2 mantienen:

```text
production_ready = false
```

Esto significa que:

- el ranking es válido para análisis, demostración y memoria técnica;
- el ranking no debe presentarse como recomendador comercial definitivo;
- los resultados requieren validación humana antes de una explotación real;
- los candidatos con baja evidencia deben tratarse como señales exploratorias.

---

## 3. Sesgo de las reseñas

La fuente principal de señales son reseñas de usuarios.

Este tipo de datos tiene varios sesgos:

- las reseñas suelen estar sesgadas hacia experiencias muy positivas o muy negativas;
- muchos usuarios escriben reseñas generales del local, no de platos concretos;
- algunos platos se mencionan solo de forma indirecta;
- locales con más reseñas tienen más oportunidades de aparecer;
- locales con pocas reseñas pueden generar señales fuertes pero poco robustas;
- el lenguaje informal puede dificultar la detección y normalización.

En la fase v2 se intenta mitigar esto con ABSA por mención, evidencia por review y penalizaciones, pero el sesgo no desaparece.

---

## 4. Evidencia emergente

Aunque el ranking v2 selecciona 268 candidatos, muchos tienen evidencia `emerging`.

Distribución de evidencia en seleccionados:

| Evidence tier | Candidatos |
|---|---:|
| `emerging` | 215 |
| `solid` | 48 |
| `strong` | 5 |

Esto implica que buena parte de los resultados son prometedores, pero todavía no tienen una base de reviews suficientemente amplia.

### Riesgo

Un candidato con 2 reviews positivas puede parecer muy fuerte si no se muestra su evidencia.

### Mitigación

El dashboard debe exponer siempre:

- número de menciones;
- número de reviews;
- `evidence_tier`;
- `quality_tier`;
- ratio positivo;
- ratio negativo.

---

## 5. Calidad agregada

Distribución de calidad agregada:

| Quality tier | Candidatos |
|---|---:|
| `high` | 48 |
| `medium` | 199 |
| `low` | 21 |

La mayoría de candidatos son de calidad media. Esto es aceptable para una fase experimental, pero no suficiente para producción.

### Mitigación

Para presentaciones más conservadoras, se recomienda filtrar:

```text
quality_tier in ["high", "medium"]
evidence_tier in ["solid", "strong"]
```

y dejar `low` o `emerging` para exploración.

---

## 6. Platos genéricos en posiciones altas

El ranking v2 puede situar arriba platos genéricos como:

```text
hamburguesa
pizza
churros
croqueta
montadito
```

Esto no es necesariamente un error. Si existen menciones positivas, varias reviews y calidad alta, pueden ser verdaderos hidden gems.

Sin embargo, desde el punto de vista del producto, puede ser deseable priorizar platos más específicos o locales.

### Riesgo

El usuario puede percibir que el ranking no descubre platos diferenciales si aparecen demasiados platos genéricos.

### Mitigación futura

Añadir a una versión v2.1:

- penalización suave por plato demasiado genérico;
- bonus por platos específicos;
- bonus por platos locales/tradicionales;
- bonus por rareza territorial;
- agrupación de variantes de platos genéricos.

---

## 7. Dependencia del catálogo de platos

El modelo de normalización no descubre platos de forma completamente abierta. Funciona como reranker sobre candidatos generados desde catálogo y aliases.

Esto significa que:

```text
si un plato no existe en el catálogo o no se genera como candidato,
el modelo no puede enlazarlo correctamente.
```

### Riesgo

Algunos platos válidos pueden quedar como `no_candidate`.

Ejemplos detectados en la fase:

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

### Mitigación

Mantener una cola de revisión para:

- añadir nuevos platos;
- crear aliases;
- fusionar variantes;
- separar ingredientes de platos reales.

---

## 8. Riesgo de normalización incorrecta

El modelo de normalización obtuvo métricas muy altas en entrenamiento, pero puede cometer errores cuando:

- la mención es muy corta;
- el plato es ambiguo;
- hay varios platos en una misma frase;
- el candidato correcto no está en la lista;
- aparecen variantes locales poco frecuentes;
- el texto contiene errores ortográficos.

### Mitigación

El pipeline marca estados como:

```text
linked_needs_review
low_confidence
no_candidate
likely_fragment
experimental_ner_only
```

Estos estados deben usarse para reducir peso o excluir señales en rankings conservadores.

---

## 9. Riesgo en sentimiento ABSA

El modelo ABSA clasifica sentimiento por mención, no sentimiento global de la reseña.

Aunque obtuvo buenos resultados, puede fallar en casos como:

- ironía;
- negaciones complejas;
- comparaciones entre platos;
- frases largas con varios sentimientos;
- menciones neutras dentro de reseñas muy positivas;
- errores de etiqueta débil.

Ejemplo de dificultad:

```text
"Las croquetas estaban increíbles, pero el arroz fue decepcionante."
```

El modelo debe asignar:

```text
croquetas → positive
arroz → negative
```

pero esto depende de que la ventana de contexto sea correcta.

### Mitigación

Usar:

- confianza ABSA;
- margen entre clases;
- ejemplos de reseña en dashboard;
- revisión manual para low confidence.

---

## 10. Etiquetas débiles

Los datasets de entrenamiento combinan:

- etiquetas manuales;
- casos aumentados;
- weak labels generadas por reglas o heurísticas.

Las weak labels permiten ampliar el dataset, pero pueden contener errores.

Esto se observó especialmente en ABSA, donde algunas etiquetas débiles parecían contradecir el texto real.

### Riesgo

El modelo puede aprender ruido si las weak labels pesan demasiado.

### Mitigación aplicada

Durante el entrenamiento se usaron pesos diferenciados:

```text
manual_gold > weak_hybrid
```

y se evaluaron resultados por fuente de etiqueta.

---

## 11. Métricas altas no implican producción

Algunos modelos obtuvieron métricas muy altas.

Esto es positivo, pero no garantiza producción porque:

- el dataset procede del propio dominio y puede tener patrones repetidos;
- parte del dataset contiene etiquetas débiles;
- la evaluación no sustituye a una validación humana externa;
- los modelos se han entrenado para un piloto Sevilla, no para cualquier ciudad;
- el catálogo y las fuentes actuales condicionan la salida.

### Recomendación

Usar las métricas como evidencia técnica, pero acompañarlas siempre de limitaciones.

---

## 12. Comparabilidad v1 vs v2

Los scores de v1 y v2 no son equivalentes.

Aunque ambos están normalizados 0-100, la fórmula de v2 cambia al incorporar:

- sentimiento ABSA;
- normalización entrenada;
- calidad agregada;
- penalizaciones nuevas;
- evidencia revisada.

Por tanto:

```text
un 80 en v2 no equivale directamente a un 80 en v1
```

La comparación debe centrarse en:

- solapamiento;
- cobertura;
- diversidad;
- cambios de tier;
- ejemplos concretos;
- coherencia de candidatos.

---

## 13. Coordenadas y mapa

El dashboard v2 puede usar coordenadas reales cuando están disponibles.

Sin embargo:

- no todos los locales pueden tener coordenadas;
- algunas coordenadas pueden venir de fuentes anteriores;
- en ausencia de coordenadas, puede usarse un fallback aproximado por barrio/distrito;
- un mapa con centroides aproximados no debe interpretarse como ubicación exacta del local.

### Mitigación

Mostrar `coordinate_source` y diferenciar coordenadas reales de fallback.

---

## 14. Riesgo de sobreexplicación

El ranking genera explicaciones textuales para los candidatos.

Estas explicaciones son útiles, pero se basan en métricas del pipeline. No deben presentarse como revisión humana ni como garantía absoluta.

Ejemplo de explicación:

```text
churros en Café Los Pilares Bar obtiene 90.5/100...
```

Debe interpretarse como:

```text
explicación automática basada en señales disponibles
```

no como validación editorial.

---

## 15. Riesgos técnicos

Riesgos técnicos de la fase:

- modelos guardados localmente y no versionados en Git;
- dependencia de rutas de artefactos;
- posible desalineación si se regeneran artefactos antiguos;
- scripts pesados en CPU;
- inferencia lenta sin GPU para modelos BETO;
- necesidad de mantener compatibilidad de columnas.

### Mitigación

- usar summaries JSON;
- mantener `PATCH_ID` en scripts importantes;
- documentar comandos;
- versionar contratos de datos;
- guardar modelos en carpeta estándar;
- añadir descarga automática de modelos en el futuro.

---

## 16. Riesgos de producto

Desde el punto de vista de producto, existen riesgos:

- el usuario puede esperar "mejores restaurantes", pero el sistema rankea platos;
- algunos resultados pueden ser demasiado específicos o demasiado genéricos;
- el ranking puede favorecer locales con más reseñas;
- el ranking puede parecer definitivo si no se muestran evidencias;
- el concepto "hidden gem" es parcialmente subjetivo.

### Mitigación

Comunicar claramente:

```text
Hidden Gems descubre señales de platos destacados por barrio,
no certifica restaurantes ni sustituye evaluación gastronómica humana.
```

---

## 17. Recomendaciones de uso

Para una presentación responsable:

1. Mostrar siempre que el ranking es experimental.
2. Incluir filtros de evidencia y calidad.
3. Presentar ejemplos de reseñas.
4. Evitar afirmar que son "los mejores platos" de Sevilla.
5. Usar expresiones como:
   - "candidatos destacados";
   - "señales prometedoras";
   - "ranking asistido por modelos";
   - "evidencia textual disponible".
6. Separar claramente `top`, `strong`, `promising` y `exploratory`.

---

## 18. Conclusión

La fase IA v2 representa una mejora importante del proyecto, pero sus resultados deben interpretarse con cautela.

Conclusión:

```text
El ranking IA v2 es útil para análisis, exploración y demostración,
pero requiere validación humana, más datos y refinamiento antes de considerarse producción.
```

Esta honestidad fortalece la memoria técnica y mejora la credibilidad del proyecto.
