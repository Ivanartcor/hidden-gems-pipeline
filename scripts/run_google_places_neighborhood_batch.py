from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
import yaml
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_QUERY_TEMPLATES = [
    "restaurantes en {neighborhood}, Sevilla",
    "bares de tapas en {neighborhood}, Sevilla",
    "cafeterías en {neighborhood}, Sevilla",
]
DEFAULT_QUERY_PLAN_PATH = Path("src/config/google_places_query_plan.yaml")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta un batch controlado de Google Places Text Search por barrios, "
            "usando scripts.load_google_places_pipeline como unidad operativa."
        )
    )

    parser.add_argument(
        "--batch-name",
        type=str,
        default=None,
        help="Nombre lógico del batch. Si no se indica, se genera automáticamente.",
    )

    parser.add_argument(
        "--config-path",
        type=str,
        default=None,
        help=(
            "Ruta al YAML de configuración de Google Places. "
            "Por defecto: src/config/google_places_query_plan.yaml."
        ),
    )

    parser.add_argument(
        "--ignore-query-plan",
        action="store_true",
        help="Ignora el YAML de configuración y usa solo valores CLI/defaults internos.",
    )

    parser.add_argument(
        "--neighborhood",
        action="append",
        default=None,
        help=(
            "Nombre de barrio a incluir. Se puede repetir. "
            "Si no se indica, se usan barrios de la base según limit-neighborhoods "
            "o los distritos indicados con --district."
        ),
    )

    parser.add_argument(
        "--district",
        action="append",
        default=None,
        help=(
            "Nombre de distrito a incluir. Se puede repetir. "
            "Ejemplo: --district Triana --district Nervión. "
            "Si se usa, se incluyen todos los barrios de esos distritos."
        ),
    )

    parser.add_argument(
        "--limit-neighborhoods",
        type=int,
        default=3,
        help="Número máximo de barrios a procesar si no se pasan barrios ni distritos explícitos.",
    )

    parser.add_argument(
        "--query-template",
        action="append",
        default=None,
        help=(
            "Plantilla de consulta. Debe contener {search_name} o {neighborhood}. "
            "Se puede repetir. Si no se indica, se usan las plantillas del YAML "
            "o las plantillas gastronómicas por defecto."
        ),
    )

    parser.add_argument(
        "--queries-per-neighborhood",
        type=int,
        default=None,
        help=(
            "Número máximo de plantillas a ejecutar por barrio. "
            "Si no se indica, se usa el valor del YAML o 2."
        ),
    )

    parser.add_argument(
        "--max-result-count",
        type=int,
        default=None,
        help=(
            "Número máximo de resultados por consulta individual. "
            "Si no se indica, se usa el valor del YAML o 5."
        ),
    )

    parser.add_argument(
        "--max-total-queries",
        type=int,
        default=10,
        help="Máximo de consultas totales permitidas en este batch.",
    )

    parser.add_argument(
        "--language-code",
        type=str,
        default=None,
        help="Código de idioma para Google Places. Si no se indica, se usa YAML o es.",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        default=None,
        help="Código regional para Google Places. Si no se indica, se usa YAML o ES.",
    )

    parser.add_argument(
        "--trigger-type",
        type=str,
        default="cli",
        help="Tipo de trigger para source_run. Por defecto: cli.",
    )

    parser.add_argument(
        "--run-type",
        type=str,
        default="incremental",
        help="Tipo de run para source_run. Por defecto: incremental.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=None,
        help="Pausa entre consultas. Si no se indica, se usa YAML o 1.0.",
    )

    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Ejecuta cada pipeline hasta deduplicación, sin importar a tablas canónicas.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo construye y muestra el plan, sin llamar a Google Places.",
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Detiene el batch en el primer error.",
    )

    parser.add_argument(
        "--max-errors",
        type=int,
        default=3,
        help="Número máximo de errores tolerados antes de detener el batch.",
    )

    parser.add_argument(
        "--allow-large-batch",
        action="store_true",
        help="Permite superar max-total-queries. No recomendado en desarrollo.",
    )

    parser.add_argument(
        "--allow-large-page-size",
        action="store_true",
        help="Permite max-result-count > 10. No recomendado en desarrollo.",
    )

    return parser


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str, max_length: int = 80) -> str:
    text_value = value.strip().lower()
    text_value = re.sub(r"[^\w\s-]", "", text_value, flags=re.UNICODE)
    text_value = re.sub(r"[-\s]+", "_", text_value)
    return text_value[:max_length].strip("_") or "item"


def normalize_for_match(value: str) -> str:
    text_value = value.strip()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(
        character
        for character in text_value
        if not unicodedata.combining(character)
    )
    text_value = text_value.lower()
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value


def load_query_plan_config(
    *,
    config_path: str | None,
    ignore_query_plan: bool,
) -> dict[str, Any]:
    if ignore_query_plan:
        return {}

    resolved_path = Path(config_path) if config_path else DEFAULT_QUERY_PLAN_PATH

    if not resolved_path.exists():
        logger.warning(
            "No existe archivo de configuración Google Places: %s. Se usarán defaults internos.",
            resolved_path,
        )
        return {}

    with resolved_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"El archivo YAML no contiene un objeto válido: {resolved_path}")

    return data


def get_config_defaults(config: dict[str, Any]) -> dict[str, Any]:
    defaults = config.get("defaults") or {}

    if not isinstance(defaults, dict):
        raise ValueError("La sección defaults del YAML debe ser un objeto.")

    return defaults


def resolve_language_code(args: argparse.Namespace, config: dict[str, Any]) -> str:
    defaults = get_config_defaults(config)
    return args.language_code or str(defaults.get("language_code") or "es")


def resolve_region_code(args: argparse.Namespace, config: dict[str, Any]) -> str:
    defaults = get_config_defaults(config)
    return args.region_code or str(defaults.get("region_code") or "ES")


def resolve_max_result_count(args: argparse.Namespace, config: dict[str, Any]) -> int:
    defaults = get_config_defaults(config)
    value = args.max_result_count

    if value is None:
        value = int(defaults.get("max_result_count") or 5)

    return int(value)


def resolve_queries_per_neighborhood(args: argparse.Namespace, config: dict[str, Any]) -> int:
    defaults = get_config_defaults(config)
    value = args.queries_per_neighborhood

    if value is None:
        value = int(defaults.get("queries_per_neighborhood") or 2)

    return int(value)


def resolve_sleep_seconds(args: argparse.Namespace, config: dict[str, Any]) -> float:
    defaults = get_config_defaults(config)
    value = args.sleep_seconds

    if value is None:
        value = float(defaults.get("sleep_seconds") or 1.0)

    return float(value)


def get_neighborhood_aliases(config: dict[str, Any]) -> dict[str, str]:
    aliases = config.get("neighborhood_aliases") or {}

    if not isinstance(aliases, dict):
        raise ValueError("La sección neighborhood_aliases del YAML debe ser un objeto.")

    return {
        normalize_for_match(str(key)): str(value).strip()
        for key, value in aliases.items()
        if str(key).strip() and str(value).strip()
    }


def default_search_name_from_official_name(value: str) -> str:
    clean_value = value.strip()
    clean_value = re.sub(r"\s+", " ", clean_value)
    clean_value = clean_value.replace("-", " - ")

    # Title case como fallback visual. Los casos importantes se corrigen con aliases.
    return clean_value.title()


def resolve_search_name(
    *,
    neighborhood_name: str,
    aliases: dict[str, str],
) -> str:
    normalized_name = normalize_for_match(neighborhood_name)

    if normalized_name in aliases:
        return aliases[normalized_name]

    return default_search_name_from_official_name(neighborhood_name)


def fetch_neighborhoods() -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            n.neighborhood_id::text AS neighborhood_id,
            n.official_name AS neighborhood_name,
            d.official_name AS district_name
        FROM hidden_gems.neighborhood n
        LEFT JOIN hidden_gems.district d
            ON d.district_id = n.district_id
        ORDER BY d.official_name NULLS LAST, n.official_name
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    return [dict(row) for row in rows]


def filter_neighborhoods(
    neighborhoods: list[dict[str, Any]],
    requested_names: list[str] | None,
    requested_districts: list[str] | None,
    limit: int,
) -> list[dict[str, Any]]:
    selected_by_id: dict[str, dict[str, Any]] = {}

    if requested_names:
        for requested_name in requested_names:
            requested_normalized = normalize_for_match(requested_name)

            exact_matches = [
                neighborhood
                for neighborhood in neighborhoods
                if normalize_for_match(str(neighborhood["neighborhood_name"]))
                == requested_normalized
            ]

            if exact_matches:
                for neighborhood in exact_matches:
                    selected_by_id[neighborhood["neighborhood_id"]] = neighborhood
                continue

            partial_matches = [
                neighborhood
                for neighborhood in neighborhoods
                if requested_normalized
                in normalize_for_match(str(neighborhood["neighborhood_name"]))
            ]

            if partial_matches:
                for neighborhood in partial_matches:
                    selected_by_id[neighborhood["neighborhood_id"]] = neighborhood
                continue

            available = [
                str(row["neighborhood_name"])
                for row in neighborhoods[:30]
            ]
            raise ValueError(
                f"No se encontró ningún barrio para '{requested_name}'. "
                f"Ejemplos disponibles: {available}"
            )

    if requested_districts:
        for requested_district in requested_districts:
            requested_normalized = normalize_for_match(requested_district)

            exact_matches = [
                neighborhood
                for neighborhood in neighborhoods
                if normalize_for_match(str(neighborhood.get("district_name") or ""))
                == requested_normalized
            ]

            if exact_matches:
                for neighborhood in exact_matches:
                    selected_by_id[neighborhood["neighborhood_id"]] = neighborhood
                continue

            partial_matches = [
                neighborhood
                for neighborhood in neighborhoods
                if requested_normalized
                in normalize_for_match(str(neighborhood.get("district_name") or ""))
            ]

            if partial_matches:
                for neighborhood in partial_matches:
                    selected_by_id[neighborhood["neighborhood_id"]] = neighborhood
                continue

            available = sorted(
                {
                    str(row.get("district_name"))
                    for row in neighborhoods
                    if row.get("district_name")
                }
            )
            raise ValueError(
                f"No se encontró ningún distrito para '{requested_district}'. "
                f"Distritos disponibles: {available}"
            )

    if selected_by_id:
        return list(selected_by_id.values())

    if limit < 1:
        raise ValueError("limit-neighborhoods debe ser mayor que 0.")

    return neighborhoods[:limit]

def resolve_query_templates(
    query_templates: list[str] | None,
    queries_per_neighborhood: int,
    config: dict[str, Any],
) -> list[str]:
    config_text_search = config.get("text_search") or {}

    if config_text_search and not isinstance(config_text_search, dict):
        raise ValueError("La sección text_search del YAML debe ser un objeto.")

    config_templates = config_text_search.get("query_templates") or []

    if query_templates:
        templates = query_templates
    elif config_templates:
        templates = config_templates
    else:
        templates = DEFAULT_QUERY_TEMPLATES

    clean_templates: list[str] = []
    seen: set[str] = set()

    for template in templates:
        clean_template = str(template).strip()

        if "{search_name}" not in clean_template and "{neighborhood}" not in clean_template:
            raise ValueError(
                "La plantilla debe contener '{search_name}' o '{neighborhood}': "
                f"{clean_template}"
            )

        if clean_template and clean_template not in seen:
            clean_templates.append(clean_template)
            seen.add(clean_template)

    if queries_per_neighborhood < 1:
        raise ValueError("queries-per-neighborhood debe ser mayor que 0.")

    return clean_templates[:queries_per_neighborhood]


def build_plan(
    *,
    batch_name: str,
    neighborhoods: list[dict[str, Any]],
    query_templates: list[str],
    max_result_count: int,
    aliases: dict[str, str],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []

    for neighborhood in neighborhoods:
        neighborhood_name = str(neighborhood["neighborhood_name"])
        district_name = neighborhood.get("district_name")
        search_name = resolve_search_name(
            neighborhood_name=neighborhood_name,
            aliases=aliases,
        )

        for index, template in enumerate(query_templates, start=1):
            text_query = template.format(
                neighborhood=neighborhood_name,
                search_name=search_name,
                district=district_name or "",
            )

            query_name = "_".join(
                [
                    slugify(batch_name, 24),
                    slugify(neighborhood_name, 22),
                    f"q{index:02d}",
                ]
            )

            plan.append(
                {
                    "batch_name": batch_name,
                    "neighborhood_id": neighborhood["neighborhood_id"],
                    "neighborhood_name": neighborhood_name,
                    "district_name": district_name,
                    "search_name": search_name,
                    "query_template": template,
                    "query_index": index,
                    "query_name": query_name,
                    "text_query": text_query,
                    "max_result_count": max_result_count,
                }
            )

    return plan


def validate_safety_limits(
    *,
    plan: list[dict[str, Any]],
    max_total_queries: int,
    max_result_count: int,
    allow_large_batch: bool,
    allow_large_page_size: bool,
) -> None:
    if max_result_count < 1:
        raise ValueError("max-result-count debe ser mayor que 0.")

    if max_result_count > 10 and not allow_large_page_size:
        raise ValueError(
            "max-result-count > 10 bloqueado por seguridad. "
            "Usa --allow-large-page-size si realmente quieres permitirlo."
        )

    if len(plan) > max_total_queries and not allow_large_batch:
        raise ValueError(
            f"El plan contiene {len(plan)} consultas, pero max-total-queries={max_total_queries}. "
            "Reduce barrios/consultas o usa --allow-large-batch si realmente quieres permitirlo."
        )


def extract_last_json_object(stdout: str) -> dict[str, Any]:
    """
    Extrae el JSON completo impreso por scripts.load_google_places_pipeline.

    Importante:
    - No debe devolver un objeto interno del JSON.
    - Debe devolver el objeto cuyo cierre llega hasta el final del stdout,
      ignorando solo espacios/saltos de línea posteriores.
    """
    clean_stdout = stdout.strip()

    if not clean_stdout:
        raise ValueError("stdout vacío: no hay JSON que extraer.")

    try:
        parsed = json.loads(clean_stdout)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()

    for index, char in enumerate(clean_stdout):
        if char != "{":
            continue

        try:
            parsed, end = decoder.raw_decode(clean_stdout[index:])
        except json.JSONDecodeError:
            continue

        remaining = clean_stdout[index + end :].strip()

        if isinstance(parsed, dict) and remaining == "":
            return parsed

    raise ValueError(
        "No se pudo extraer el JSON final completo del stdout del pipeline."
    )

def run_single_pipeline(
    *,
    row: dict[str, Any],
    language_code: str,
    region_code: str,
    trigger_type: str,
    run_type: str,
    skip_import: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "scripts.load_google_places_pipeline",
        "--text-query",
        row["text_query"],
        "--query-name",
        row["query_name"],
        "--max-result-count",
        str(row["max_result_count"]),
        "--language-code",
        language_code,
        "--region-code",
        region_code,
        "--trigger-type",
        trigger_type,
        "--run-type",
        run_type,
    ]

    if skip_import:
        command.append("--skip-import")

    started_at = datetime.now(timezone.utc)

    completed = subprocess.run(
        command,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    finished_at = datetime.now(timezone.utc)

    result: dict[str, Any] = {
        "query_name": row["query_name"],
        "text_query": row["text_query"],
        "neighborhood_id": row["neighborhood_id"],
        "neighborhood_name": row["neighborhood_name"],
        "district_name": row["district_name"],
        "search_name": row.get("search_name"),
        "return_code": completed.returncode,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": round((finished_at - started_at).total_seconds(), 3),
        "success": completed.returncode == 0,
    }

    if completed.returncode == 0:
        pipeline_output = extract_last_json_object(completed.stdout)
        result["pipeline_output"] = pipeline_output
        result["source_run_id"] = pipeline_output.get("source_run_id")
        result["raw_asset_id"] = pipeline_output.get("raw_asset_id")
        result["raw_summary"] = pipeline_output.get("raw_summary")
        result["transform_summary"] = pipeline_output.get("transform_summary")
        result["dedup_summary"] = pipeline_output.get("dedup_summary")
        result["import_summary"] = pipeline_output.get("import_summary")
        result["paths"] = pipeline_output.get("paths")
    else:
        result["error"] = {
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }

    return result


def summarize_batch_results(
    *,
    batch_name: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    skip_import: bool,
) -> dict[str, Any]:
    success_results = [
        result for result in results
        if result.get("success")
    ]
    error_results = [
        result for result in results
        if not result.get("success")
    ]

    def sum_nested(path: tuple[str, ...]) -> int:
        total = 0

        for result in success_results:
            current: Any = result

            for key in path:
                if not isinstance(current, dict):
                    current = None
                    break
                current = current.get(key)

            if isinstance(current, int):
                total += current

        return total

    neighborhoods_processed = sorted(
        {
            str(result["neighborhood_name"])
            for result in results
        }
    )

    neighborhoods_with_success = sorted(
        {
            str(result["neighborhood_name"])
            for result in success_results
        }
    )

    neighborhoods_with_error = sorted(
        {
            str(result["neighborhood_name"])
            for result in error_results
        }
    )

    return {
        "batch_name": batch_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "skip_import": skip_import,
        "planned_query_count": len(plan),
        "executed_query_count": len(results),
        "success_count": len(success_results),
        "error_count": len(error_results),
        "neighborhoods_processed": neighborhoods_processed,
        "neighborhoods_with_success": neighborhoods_with_success,
        "neighborhoods_with_error": neighborhoods_with_error,
        "totals": {
            "raw_place_count": sum_nested(("raw_summary", "place_count")),
            "accepted_count": sum_nested(("transform_summary", "accepted_count")),
            "needs_review_count": sum_nested(("transform_summary", "needs_review_count")),
            "rejected_count": sum_nested(("transform_summary", "rejected_count")),
            "transform_issue_count": sum_nested(("transform_summary", "issue_count")),
            "dedup_output_count": sum_nested(("dedup_summary", "output_count")),
            "dedup_duplicate_group_count": sum_nested(("dedup_summary", "duplicate_group_count")),
            "imported_count": sum_nested(("import_summary", "imported_count")),
            "skipped_count": sum_nested(("import_summary", "skipped_count")),
            "place_created_count": sum_nested(("import_summary", "place_created_count")),
            "place_updated_count": sum_nested(("import_summary", "place_updated_count")),
            "place_source_ref_created_count": sum_nested(("import_summary", "place_source_ref_created_count")),
            "place_source_ref_updated_count": sum_nested(("import_summary", "place_source_ref_updated_count")),
            "validation_issue_count": sum_nested(("import_summary", "validation_issue_count")),
        },
    }


def save_batch_artifacts(
    *,
    batch_name: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir = settings.data_artifacts_path / "google_places_batches" / batch_name
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_path = output_dir / "plan.json"
    results_path = output_dir / "results.json"
    summary_path = output_dir / "batch_summary.json"

    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    results_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return {
        "output_dir": str(output_dir),
        "plan_path": str(plan_path),
        "results_path": str(results_path),
        "summary_path": str(summary_path),
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    batch_name = args.batch_name or f"google_places_neighborhood_batch_{utc_now_compact()}"
    batch_name = slugify(batch_name, 80)

    query_plan_config = load_query_plan_config(
        config_path=args.config_path,
        ignore_query_plan=args.ignore_query_plan,
    )

    language_code = resolve_language_code(args, query_plan_config)
    region_code = resolve_region_code(args, query_plan_config)
    max_result_count = resolve_max_result_count(args, query_plan_config)
    queries_per_neighborhood = resolve_queries_per_neighborhood(args, query_plan_config)
    sleep_seconds = resolve_sleep_seconds(args, query_plan_config)
    aliases = get_neighborhood_aliases(query_plan_config)

    neighborhoods = fetch_neighborhoods()
    selected_neighborhoods = filter_neighborhoods(
        neighborhoods,
        args.neighborhood,
        args.district,
        args.limit_neighborhoods,
    )
    query_templates = resolve_query_templates(
        args.query_template,
        queries_per_neighborhood,
        query_plan_config,
    )

    plan = build_plan(
        batch_name=batch_name,
        neighborhoods=selected_neighborhoods,
        query_templates=query_templates,
        max_result_count=max_result_count,
        aliases=aliases,
    )

    validate_safety_limits(
        plan=plan,
        max_total_queries=args.max_total_queries,
        max_result_count=max_result_count,
        allow_large_batch=args.allow_large_batch,
        allow_large_page_size=args.allow_large_page_size,
    )

    logger.info(
        "Plan Google Places por barrios construido | batch_name=%s | neighborhoods=%s | queries=%s | dry_run=%s",
        batch_name,
        len(selected_neighborhoods),
        len(plan),
        args.dry_run,
    )

    if args.dry_run:
        summary = {
            "batch_name": batch_name,
            "dry_run": True,
            "planned_query_count": len(plan),
            "selected_neighborhoods": selected_neighborhoods,
            "query_templates": query_templates,
            "plan": plan,
            "query_plan_config_loaded": bool(query_plan_config),
            "language_code": language_code,
            "region_code": region_code,
            "max_result_count": max_result_count,
            "queries_per_neighborhood": queries_per_neighborhood,
            "aliases_loaded_count": len(aliases),
        }

        artifact_paths = save_batch_artifacts(
            batch_name=batch_name,
            plan=plan,
            results=[],
            summary=summary,
        )

        output = {
            **summary,
            "artifacts": artifact_paths,
        }

        print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        logger.info("Dry-run de batch Google Places completado correctamente.")
        return 0

    results: list[dict[str, Any]] = []
    error_count = 0

    for index, row in enumerate(plan, start=1):
        logger.info(
            "Ejecutando consulta %s/%s | neighborhood=%s | query_name=%s | text_query=%s",
            index,
            len(plan),
            row["neighborhood_name"],
            row["query_name"],
            row["text_query"],
        )

        try:
            result = run_single_pipeline(
                row=row,
                language_code=language_code,
                region_code=region_code,
                trigger_type=args.trigger_type,
                run_type=args.run_type,
                skip_import=args.skip_import,
            )
        except Exception as exc:
            result = {
                "query_name": row["query_name"],
                "text_query": row["text_query"],
                "neighborhood_id": row["neighborhood_id"],
                "neighborhood_name": row["neighborhood_name"],
                "district_name": row["district_name"],
                "success": False,
                "return_code": None,
                "error": {
                    "exception": str(exc),
                },
            }

        results.append(result)

        if not result.get("success"):
            error_count += 1
            logger.warning(
                "Consulta fallida | query_name=%s | error_count=%s",
                row["query_name"],
                error_count,
            )

            if args.stop_on_error or error_count >= args.max_errors:
                logger.warning(
                    "Batch detenido por política de errores | stop_on_error=%s | error_count=%s | max_errors=%s",
                    args.stop_on_error,
                    error_count,
                    args.max_errors,
                )
                break

        if index < len(plan) and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    summary = summarize_batch_results(
        batch_name=batch_name,
        plan=plan,
        results=results,
        skip_import=args.skip_import,
    )

    artifact_paths = save_batch_artifacts(
        batch_name=batch_name,
        plan=plan,
        results=results,
        summary=summary,
    )

    output = {
        **summary,
        "artifacts": artifact_paths,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    if summary["error_count"] > 0:
        logger.warning(
            "Batch Google Places finalizado con errores | batch_name=%s | errors=%s",
            batch_name,
            summary["error_count"],
        )
        return 1

    logger.info(
        "Batch Google Places finalizado correctamente | batch_name=%s | success=%s",
        batch_name,
        summary["success_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())