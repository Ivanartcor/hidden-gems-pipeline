# 04. Consulta demo y resultados del ranking Sevilla piloto


## 1. Objetivo

Este documento describe cómo consultar el ranking `sevilla_pilot` ya cargado en PostgreSQL y qué resultados principales devuelve.

La finalidad de esta fase es demostrar que el piloto IA Sevilla no solo genera artefactos en notebooks, sino que también puede ser explotado desde la base de datos mediante vistas y scripts de consulta.

El foco de la consulta es obtener respuestas del tipo:

```text
¿Qué platos destacados hay en Sevilla?
¿Qué platos destacan en un distrito concreto?
¿Qué platos aparecen en un barrio concreto?
¿Dónde destaca un plato específico?
¿Qué platos destacan en un local concreto?
```

## 2. Script de consulta

Script principal:

```text
scripts/query_sevilla_hidden_gems_demo.py
```

Función:

- consultar candidatos Hidden Gems desde PostgreSQL;
- aplicar filtros opcionales por distrito, barrio, plato o local;
- generar top global;
- generar top por distrito;
- generar top por barrio;
- generar top por plato;
- generar resúmenes agregados;
- exportar resultados a CSV y JSON de reporte.

## 3. Vistas utilizadas

El script se apoya principalmente en las vistas IA creadas sobre el esquema `hidden_gems`:

```text
vw_ai_hidden_gem_candidate_detail
vw_ai_dish_place_signals
vw_ai_dish_mentions_with_sentiment
vw_ai_hidden_gems_place_summary
vw_ai_hidden_gems_dish_summary
```

La vista más importante para el ranking es:

```text
vw_ai_hidden_gem_candidate_detail
```

Esta vista permite consultar en una sola capa:

- local;
- dirección;
- plato;
- barrio;
- distrito;
- score;
- tier;
- evidencia;
- ratios de sentimiento;
- explicación del ranking;
- scope lógico del artefacto.

## 4. Ejecución general

Para obtener la demo global del ranking Sevilla piloto:

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

Este comando consulta todos los candidatos seleccionados del ranking piloto y genera artefactos en:

```text
data/artifacts/ai/sevilla/query_demo/
```

## 5. Filtros disponibles

### 5.1. Filtro por distrito

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --district "Casco Antiguo" `
  --limit 20
```

Devuelve candidatos seleccionados únicamente del distrito indicado.

### 5.2. Filtro por barrio

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --neighborhood "TRIANA" `
  --limit 20
```

Permite buscar candidatos de barrios cuyo nombre contenga el texto indicado.

### 5.3. Filtro por plato

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --dish "tarta de queso" `
  --limit 20
```

Muestra locales donde ese plato aparece seleccionado o puntuado.

### 5.4. Filtro por local

```powershell
python -m scripts.query_sevilla_hidden_gems_demo `
  --place-name "Golondrinas" `
  --include-mentions `
  --limit 10
```

Permite revisar señales de un local concreto y, si se activa `--include-mentions`, recuperar menciones relacionadas.

## 6. Artefactos generados

El script genera los siguientes archivos:

```text
data/artifacts/ai/sevilla/query_demo/sevilla_demo_top_global.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_top_by_district.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_top_by_neighborhood.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_top_by_dish.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_district_summary.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_neighborhood_summary.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_dish_summary.csv
data/artifacts/ai/sevilla/query_demo/sevilla_demo_place_summary.csv
data/artifacts/ai/sevilla/query_demo/sevilla_hidden_gems_query_demo_report.json
```

Estos artefactos sirven para revisar el ranking desde fuera de la base de datos, compartir resultados o alimentar una visualización preliminar.

## 7. Resultado global del ranking cargado

El ranking seleccionado contiene:

| Métrica | Valor |
|---|---:|
| Candidatos seleccionados | 150 |
| Locales seleccionados | 122 |
| Platos seleccionados | 38 |
| Barrios seleccionados | 55 |
| Distritos seleccionados | 11 |

Distribución por tier:

| Tier | Conteo |
|---|---:|
| `top_hidden_gem` | 2 |
| `strong_hidden_gem` | 7 |
| `promising_hidden_gem` | 72 |
| `exploratory_hidden_gem` | 69 |

Los 106 candidatos restantes quedan como `not_selected`.

## 8. Top global del piloto

El top global validado desde base de datos comienza con:

| Rank | Tier | Local | Plato | Barrio | Distrito | Score |
|---:|---|---|---|---|---|---:|
| 1 | `top_hidden_gem` | Pizzería San Pablo | pizza | SAN PABLO D Y E | San Pablo - Santa Justa | 80,1471 |
| 2 | `top_hidden_gem` | restaurante asiático shan | sushi | BELLAVISTA | Bellavista - La Palmera | 78,9556 |
| 3 | `strong_hidden_gem` | Il Ristorantino Dell'Avvocato Calle Cuna | pizza | ALFALFA | Casco Antiguo | 74,1349 |
| 4 | `strong_hidden_gem` | Tarannà | atún | SANTA CATALINA | Casco Antiguo | 73,8812 |
| 5 | `strong_hidden_gem` | Il Ristorantino Dell´Avvocato Sevilla | pizza | ENCARNACIÓN-REGINA | Casco Antiguo | 73,2847 |
| 6 | `strong_hidden_gem` | Flor de la Caña Café y Ron SR. | tarta de queso | LEON XIII-LOS NARANJOS | Macarena | 72,0559 |
| 7 | `strong_hidden_gem` | Taberna Los Terceros | solomillo al whisky | SANTA CATALINA | Casco Antiguo | 70,9464 |
| 8 | `strong_hidden_gem` | Cafeteria mi abuela, churreria | churros | FELIPE II-LOS DIEZ MANDAMIENTOS | Sur | 70,4390 |
| 9 | `strong_hidden_gem` | I Love Churros | churros | CRUZ ROJA-CAPUCHINOS | Macarena | 70,3222 |
| 10 | `promising_hidden_gem` | BAR EL BUCHITO | carrillada | PALMETE | Cerro - Amate | 72,0268 |

Nota: el ranking conserva el `hidden_gem_selected_rank` de selección, y los tiers también influyen en la interpretación. Por eso puede aparecer un `promising_hidden_gem` con score superior a algún `strong_hidden_gem` si su evidencia o reglas de selección lo clasifican en un tier inferior.

## 9. Ejemplo de salida filtrada por distrito

Al ejecutar el filtro por `Casco Antiguo`, el script cargó:

| Métrica | Valor |
|---|---:|
| Candidatos cargados | 44 |
| Candidatos seleccionados | 44 |
| Lugares seleccionados | 36 |
| Platos seleccionados | 22 |
| Barrios seleccionados | 10 |
| Distritos seleccionados | 1 |

Primeros resultados del distrito:

| Rank | Tier | Local | Plato | Barrio | Score |
|---:|---|---|---|---|---:|
| 3 | `strong_hidden_gem` | Il Ristorantino Dell'Avvocato Calle Cuna | pizza | ALFALFA | 74,1349 |
| 4 | `strong_hidden_gem` | Tarannà | atún | SANTA CATALINA | 73,8812 |
| 5 | `strong_hidden_gem` | Il Ristorantino Dell´Avvocato Sevilla | pizza | ENCARNACIÓN-REGINA | 73,2847 |

Esto confirma que el script filtra correctamente por distrito y mantiene el ranking original del piloto.

## 10. Resumen por distrito

El resumen por distrito validado fue:

| Distrito | Candidatos seleccionados | Locales | Platos | Score medio | Score máximo |
|---|---:|---:|---:|---:|---:|
| Casco Antiguo | 44 | 36 | 22 | 64,50884 | 74,1349 |
| Cerro - Amate | 15 | 11 | 9 | 64,26263 | 72,0268 |
| Sur | 14 | 10 | 11 | 63,19030 | 70,4390 |
| Este - Alcosa - Torreblanca | 14 | 10 | 11 | 60,83516 | 68,1937 |
| Nervión | 13 | 10 | 10 | 60,80162 | 70,1081 |
| San Pablo - Santa Justa | 12 | 11 | 11 | 64,26317 | 80,1471 |
| Macarena | 10 | 10 | 8 | 63,49952 | 72,0559 |
| Triana | 10 | 8 | 9 | 61,98345 | 69,4382 |
| Norte | 9 | 7 | 9 | 62,70342 | 70,4884 |
| Bellavista - La Palmera | 7 | 7 | 6 | 63,93839 | 78,9556 |
| Los Remedios | 2 | 2 | 2 | 62,53600 | 67,4108 |

El distrito con más candidatos seleccionados es `Casco Antiguo`, lo cual es esperable por densidad de locales y volumen de reseñas.

## 11. Top platos seleccionados

Los platos con más apariciones entre los 150 seleccionados son:

| Plato | Familia | Candidatos | Locales | Score medio | Score máximo |
|---|---|---:|---:|---:|---:|
| ensaladilla | tapas_clasicas | 16 | 16 | 61,87473 | 69,5217 |
| tarta de queso | postres_y_desayunos | 12 | 12 | 65,39958 | 72,0559 |
| pizza | internacional | 10 | 10 | 66,91043 | 80,1471 |
| carrillada | tapas_clasicas | 10 | 10 | 63,37928 | 72,0268 |
| atún | mar_y_pescado | 9 | 9 | 65,50759 | 73,8812 |
| solomillo al whisky | tapas_clasicas | 9 | 9 | 63,85676 | 70,9464 |
| gambas | mar_y_pescado | 9 | 9 | 60,59051 | 67,4108 |
| churros | postres_y_desayunos | 7 | 7 | 64,35071 | 70,4390 |
| torrija | postres_y_desayunos | 6 | 6 | 64,05407 | 71,2764 |
| hamburguesa | carne | 5 | 5 | 61,18936 | 68,1937 |
| croqueta | tapas_clasicas | 5 | 5 | 61,62078 | 67,0323 |
| patatas bravas | fritos_y_raciones | 5 | 5 | 61,25530 | 65,3040 |

Esta distribución refleja una mezcla razonable de tapas clásicas, platos de pescado, carnes, postres y opciones internacionales.

## 12. Interpretación de las explicaciones

Cada candidato incluye una explicación generada automáticamente.

Ejemplo:

```text
pizza en Pizzería San Pablo obtiene 80.1/100; con 6 menciones en 5 reviews; 100.0% positivas y 0.0% negativas; evidencia strong; barrio SAN PABLO D Y E; distrito San Pablo - Santa Justa; la mayoría de señales vienen del contexto local de la mención; candidato destacado del piloto.
```

La explicación resume:

- plato;
- local;
- score;
- volumen de menciones;
- volumen de reviews;
- ratio positivo;
- ratio negativo;
- tier de evidencia;
- barrio;
- distrito;
- observaciones sobre señal local o fallback;
- naturaleza piloto del candidato.

## 13. Uso de los resultados

Los resultados del script demo sirven para:

- validar manualmente el ranking;
- crear capturas o tablas para documentación;
- alimentar un dashboard inicial;
- construir endpoints de API;
- seleccionar casos de prueba;
- analizar cobertura por barrio;
- detectar sesgos del ranking.

## 14. Conclusión

El script `query_sevilla_hidden_gems_demo.py` confirma que el piloto IA Sevilla está correctamente cargado y explotable desde PostgreSQL.

El sistema ya permite consultar Hidden Gems por:

- ranking global;
- distrito;
- barrio;
- plato;
- local;
- familia de plato;
- tier de calidad.

Esto deja el proyecto preparado para la siguiente fase: documentación final, revisión manual ampliada, ajustes de scoring y futura exposición mediante API o dashboard.
---

## 15. Relación con el dashboard Sevilla IA v2

La consulta demo descrita aquí corresponde al piloto v1 cargado en PostgreSQL:

```text
query_sevilla_hidden_gems_demo.py
→ sevilla_pilot
→ CSV/JSON de demo
```

Posteriormente se desarrolló una capa de explotación más avanzada para IA v2:

```text
dashboard/streamlit_sevilla_v2_app.py
```

con datos exportados en:

```text
data/artifacts/ai/sevilla/dashboard_v2/
```

La diferencia de uso es:

| Capa | Función |
|---|---|
| Query demo v1 | Validar que el ranking piloto está cargado y puede consultarse desde PostgreSQL. |
| Dashboard v2 | Explorar el ranking IA v2, comparar v1/v2, revisar evidencia, calidad, menciones y territorio. |

Por tanto, este documento sigue siendo válido como prueba de explotación del piloto v1, pero el dashboard principal de análisis posterior pertenece a `docs/13_sevilla_ai_v2/`.

No debe interpretarse que los resultados de este documento sean los más recientes del proyecto, sino el baseline consultable desde base de datos.
