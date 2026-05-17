# 08. Flujo Git y preparación de entregas




## 1. Objetivo del documento

Este documento define el flujo recomendado para versionar, revisar y entregar cambios del proyecto **Hidden Gems**.

El proyecto combina:

```text
código Python
scripts operativos
DDL SQL
documentación Markdown
notebooks IA
configuración pública
artefactos locales
reports de checks
datos raw/staging
```

Por eso es importante separar correctamente qué debe subirse a Git y qué debe quedarse en local.

---

## 2. Principio general

La regla principal es:

```text
Git debe contener el proyecto reproducible, no todos los datos generados por el proyecto.
```

Deben versionarse:

```text
- código fuente;
- scripts;
- DDL;
- documentación;
- notebooks finales o plantillas;
- configuración pública;
- ejemplos pequeños y seguros.
```

No deben versionarse:

```text
- .env;
- API keys;
- raw completos;
- staging completo;
- datasets externos;
- JSONL pesados;
- CSV grandes con reviews;
- logs extensos;
- dumps de base de datos.
```

---

## 3. Comprobación antes de trabajar

Antes de empezar una sesión de trabajo:

```powershell
git status
```

Esto permite saber si hay cambios pendientes.

Si se está en una rama de trabajo:

```powershell
git branch
```

Si se trabaja directamente en `main`, conviene ser especialmente cuidadoso con los commits.

---

## 4. Flujo recomendado por bloque de trabajo

Para cada bloque importante:

```text
1. Hacer cambios.
2. Ejecutar scripts/checks correspondientes.
3. Revisar git status.
4. Revisar git diff.
5. Añadir solo archivos correctos.
6. Hacer commit claro.
```

Ejemplo:

```powershell
git status
git diff README.md
git diff docs/
git add README.md docs/
git commit -m "docs: update documentation after Sevilla AI pilot"
```

---

## 5. Revisión con `git diff`

Antes de añadir archivos, revisar cambios:

```powershell
git diff
```

Para un archivo concreto:

```powershell
git diff README.md
git diff docs/05_verticals/42_vertical_google_places.md
```

Esto es especialmente importante en documentación larga para confirmar que no se ha eliminado contenido útil accidentalmente.

---

## 6. Añadir archivos de forma selectiva

Evitar:

```powershell
git add .
```

salvo que se haya revisado muy bien el estado del repo.

Preferir:

```powershell
git add README.md
git add docs/08_operations/
git add scripts/query_sevilla_hidden_gems_demo.py
```

Para ver qué se va a commitear:

```powershell
git status
```

---

## 7. Archivos que nunca deberían aparecer en `git status`

Si aparecen, revisar `.gitignore` antes de hacer commit:

```text
.env
.venv/
data/raw/
data/staging/
data/external/
data/artifacts/logs/
*.log
*.sqlite
*.dump
```

También vigilar:

```text
data/artifacts/ai/**/*.jsonl
data/artifacts/ai/**/*.csv
data/artifacts/nlp_corpus/*.jsonl
```

Estos archivos pueden contener datos pesados o textos completos.

---

## 8. Archivos que normalmente sí se versionan

```text
README.md
docs/**/*.md
db/ddl/*.sql
scripts/*.py
src/**/*.py
src/config/*.yaml
notebooks/*.ipynb
requirements.txt
.env.example
.gitignore
```

Con los notebooks, revisar que no incluyan salidas enormes antes de subirlos.

---

## 9. Commits recomendados por tipo

Usar mensajes claros y agrupados por intención.

Ejemplos:

```text
docs: update project context after Sevilla AI pilot
docs: add operations runbooks
feat: add Sevilla hidden gems query demo
feat: add dashboard data export script
fix: handle strict JSON summaries in ranking notebook
chore: update gitignore for AI artifacts
sql: add AI views for Sevilla pilot queries
```

Evitar mensajes ambiguos:

```text
update
cosas
cambios
final
```

---

## 10. Commits recomendados para el estado actual del proyecto

Después de la consolidación documental actual, se podrían hacer commits como:

```powershell
git add README.md docs/01_context docs/02_architecture docs/03_data_model docs/04_sources docs/05_verticals docs/11_ai_integration docs/12_sevilla_ai_pilot
git commit -m "docs: update repository documentation for Sevilla AI pilot"
```

Después:

```powershell
git add docs/08_operations
git commit -m "docs: add operations runbooks"
```

Cuando consolidemos scripts demo:

```powershell
git add scripts/query_sevilla_hidden_gems_demo.py
git commit -m "feat: add Sevilla hidden gems query demo"
```

---

## 11. Checklist antes de cada commit

```text
[ ] He revisado git status.
[ ] He revisado git diff.
[ ] No aparece .env.
[ ] No aparecen raw/staging/datasets externos.
[ ] No aparecen JSONL o CSV pesados por accidente.
[ ] Los scripts modificados se han probado o al menos revisado.
[ ] Los checks relevantes han pasado.
[ ] La documentación no contradice el estado real del proyecto.
[ ] El mensaje de commit describe bien el cambio.
```

---

## 12. Checklist específico para documentación

Antes de commitear docs:

```text
[ ] Los enlaces internos son correctos.
[ ] No hay secciones duplicadas innecesarias.
[ ] No se ha eliminado contenido importante.
[ ] El estado actual distingue entre Yelp prototype y Sevilla pilot.
[ ] Sevilla pilot aparece como piloto cargado y validado, no como fase futura.
[ ] No se afirma que sea producción final.
[ ] Los conteos están actualizados.
```

Conteos relevantes del piloto Sevilla:

```text
190 dishes
243 aliases
2.979 mentions
2.979 sentiments
2.212 signals
256 ranking candidates
150 selected candidates
ready_for_sevilla_pilot_queries = true
is_production_ready = false
```

---

## 13. Checklist específico para scripts

Antes de commitear scripts:

```text
[ ] Tiene argumentos CLI claros.
[ ] Tiene rutas por defecto razonables.
[ ] No contiene claves hardcodeadas.
[ ] Usa settings centralizados cuando aplica.
[ ] Genera report JSON si es un loader/check.
[ ] Tiene --dry-run si escribe datos críticos, cuando sea razonable.
[ ] Los mensajes de consola son claros.
[ ] No escribe fuera de data/artifacts salvo que esté justificado.
```

---

## 14. Checklist específico para notebooks

Antes de commitear notebooks:

```text
[ ] El notebook ejecuta de principio a fin.
[ ] No contiene API keys.
[ ] No contiene outputs enormes.
[ ] No contiene rutas personales innecesarias.
[ ] Las celdas están ordenadas.
[ ] Los artefactos de salida se guardan en data/artifacts/.
[ ] Los summaries JSON son JSON estricto.
[ ] Se explica si el resultado es piloto/no producción.
```

Para limpiar outputs si hace falta, usar desde el editor o herramientas de Jupyter.

---

## 15. Checklist específico para DDL

Antes de commitear cambios SQL:

```text
[ ] El script se ha probado en una base local.
[ ] Respeta el schema hidden_gems.
[ ] No rompe constraints existentes.
[ ] Los cambios son compatibles con datos ya cargados o se documenta la migración.
[ ] Se actualiza documentación relacionada.
[ ] Si cambia ranking_scope, se revisan loaders y checks.
```

Ejemplo importante:

```text
Actualmente sevilla_pilot se conserva como artifact_ranking_scope y se carga en DB como ranking_scope = other.
```

Si se decide añadir `sevilla_pilot` como scope nativo, habría que actualizar DDL, loaders, checks y documentación.

---

## 16. Preparación de entrega académica o demo

Para una entrega, conviene preparar un estado limpio:

```text
1. README actualizado.
2. Docs principales actualizados.
3. Scripts funcionales.
4. Notebooks finales disponibles.
5. DDL completo.
6. .env.example correcto.
7. .gitignore protege datos.
8. Reports finales guardados localmente.
9. Dashboard o demo si aplica.
```

No entregar:

```text
- .env real;
- API keys;
- datasets externos completos;
- raw completos;
- staging masivo;
- logs innecesarios;
- dumps con datos sensibles.
```

---

## 17. Preparación de una demo técnica

Para demo local, el flujo recomendado es:

```text
1. Arrancar PostgreSQL.
2. Activar entorno virtual.
3. Comprobar conexión.
4. Ejecutar check de carga Sevilla.
5. Ejecutar query demo.
6. Mostrar resultados o dashboard.
```

Comandos:

```powershell
.venv\Scripts\activate
python -m scripts.check_db_connection
python -m scripts.check_sevilla_ai_pilot_loaded `
  --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json
python -m scripts.query_sevilla_hidden_gems_demo `
  --limit 30 `
  --top-per-group 5
```

---

## 18. Preparación para dashboard

Antes de crear o ejecutar dashboard:

```text
[ ] La consulta demo funciona.
[ ] Existen CSV/JSON limpios para dashboard.
[ ] El ranking Sevilla pilot está cargado.
[ ] ready_for_sevilla_pilot_queries = true.
[ ] No se exponen textos completos innecesarios.
[ ] Los filtros esperados están definidos.
```

Futuro script recomendado:

```text
scripts/export_sevilla_dashboard_data.py
```

---

## 19. Sincronización con GitHub

Después de commitear:

```powershell
git push
```

Si hay cambios remotos:

```powershell
git pull
```

Si se trabaja en equipo, evitar pisar cambios sin revisar diffs.

---

## 20. Revisión posterior al push

Después de subir cambios:

```text
[ ] Revisar README en GitHub.
[ ] Revisar que los enlaces funcionen.
[ ] Confirmar que no aparecen archivos pesados.
[ ] Confirmar que .env no está publicado.
[ ] Confirmar que docs renderizan correctamente.
```

---

## 21. Versionado conceptual del proyecto

Aunque el repositorio no use todavía releases formales, conviene pensar en hitos:

```text
v0.1 - Base pipeline y arquitectura
v0.2 - Verticales Sevilla Geo / Overpass / Google Places
v0.3 - Yelp corpus e IA prototype
v0.4 - Integración IA PostgreSQL
v0.5 - Sevilla AI pilot end-to-end
v0.6 - Dashboard piloto
v0.7 - API o producto inicial
```

Esto ayuda a explicar el progreso del proyecto.

---

## 22. Qué hacer si se sube algo por error

Si todavía no se ha hecho commit:

```powershell
git restore --staged <archivo>
```

Si se hizo commit pero no push:

```powershell
git reset --soft HEAD~1
```

Si se subió una clave o dato sensible a GitHub:

```text
1. Revocar inmediatamente la clave.
2. Crear una nueva clave.
3. Eliminar el archivo del repo.
4. Considerar limpiar historial si es necesario.
```

No basta con borrar el archivo en un commit posterior si contenía una clave real: la clave debe revocarse.

---

## 23. Flujo recomendado para la fase actual

Dado el estado actual del proyecto, el flujo inmediato recomendado es:

```text
1. Commit de documentación actualizada.
2. Commit de docs/08_operations.
3. Revisar scripts demo finales.
4. Crear/exportar contrato de datos para dashboard.
5. Crear dashboard Streamlit piloto.
6. Documentar dashboard.
7. Decidir mejoras IA posteriores.
```

---

## 24. Conclusión

Un buen flujo Git evita dos problemas frecuentes:

```text
1. Perder cambios importantes.
2. Subir datos o secretos que no deberían publicarse.
```

La regla práctica es:

```text
Antes de cada commit: git status + git diff.
Antes de cada push: revisar que el repo sigue limpio.
```

Con este flujo, Hidden Gems puede crecer como proyecto técnico serio sin mezclar código, documentación, datos pesados y credenciales.

---

## 25. Actualización final: entrega académica cerrada

El proyecto integrado se considera cerrado académicamente con la fase:

```text
Sevilla IA v2 + dashboard final + documentación completa
```

Estado conceptual:

```text
Estado académico: cerrado para entrega.
Estado técnico: MVP avanzado / prototipo analítico funcional.
Estado producción: no producción, pendiente de validación humana y despliegue.
```

Commits recomendados:

```powershell
git add README.md docs/
git commit -m "docs: finalize documentation for Sevilla AI v2 delivery"
```

```powershell
git add scripts/ dashboard/ requirements.txt .gitignore
git commit -m "feat: add Sevilla AI v2 ranking export and dashboard"
```

Checklist final antes de push:

```text
[ ] README enlaza a docs/13_sevilla_ai_v2/.
[ ] docs/01_context a docs/08_operations están actualizados.
[ ] docs/13_sevilla_ai_v2 está completa.
[ ] dashboard/streamlit_sevilla_v2_app.py existe.
[ ] scripts/export_sevilla_dashboard_data_v2.py existe.
[ ] requirements.txt incluye dependencias dashboard/modelos.
[ ] .gitignore excluye models/, raw, staging, external y artifacts pesados.
[ ] No aparece .env.
[ ] No aparecen modelos entrenados.
[ ] No aparecen CSV/JSONL pesados.
[ ] El dashboard v2 se ha probado localmente.
```

No subir:

```text
models/
data/artifacts/ai/sevilla/dashboard_v2/mention_examples.csv
data/artifacts/ai/sevilla/model_inference/**/*.jsonl
data/artifacts/ai/sevilla/model_inference/**/*.csv
data/raw/
data/staging/
.env
```

Frase de cierre del repositorio:

```text
Hidden Gems queda cerrado como Proyecto Integrado con un pipeline completo de datos + IA + ranking + dashboard, manteniendo el ranking final como experimental y no productivo.
```
