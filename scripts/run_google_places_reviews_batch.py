from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


# -----------------------------------------------------------------------------
# USO DEL BATCH DE GOOGLE PLACES REVIEWS
# -----------------------------------------------------------------------------
#
# Este script ejecuta un lote controlado de enriquecimiento de reviews usando
# Google Places Place Details sobre locales que ya existen en el modelo canónico.
#
# Flujo interno por cada local:
#
#   place_source_ref google_places
#   → scripts.load_google_places_reviews_pipeline
#   → Place Details
#   → raw_asset
#   → staging reviews
#   → check staging interno
#   → importación en hidden_gems.review
#   → check import interno
#
# MODO 1: Solo ver el plan, sin llamar a Google
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_batch_dry_run_v1 `
#     --limit-places 5 `
#     --dry-run
#
# MODO 2: Ejecutar llamadas a Google, transformar y validar, pero sin importar
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_batch_no_import_v1 `
#     --limit-places 5 `
#     --skip-import `
#     --max-total-places 5 `
#     --max-errors 5
#
# MODO 3: Ejecutar batch completo con importación en hidden_gems.review
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_batch_import_v1 `
#     --limit-places 5 `
#     --max-total-places 5 `
#     --max-errors 5
#
# MODO 4: Ejecutar solo para un barrio concreto
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_santa_cruz_import_v1 `
#     --neighborhood "SANTA CRUZ" `
#     --limit-places 5 `
#     --max-total-places 5 `
#     --max-errors 5
#
# MODO 5: Ejecutar solo para un distrito
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_distrito_triana_import_v1 `
#     --district Triana `
#     --limit-places 5 `
#     --max-total-places 5 `
#     --max-errors 5
#
# MODO 6: Ejecutar para IDs concretos
#
#   python -m scripts.run_google_places_reviews_batch `
#     --batch-name gp_reviews_ids_import_v1 `
#     --place-source-ref-id <PLACE_SOURCE_REF_ID_1> `
#     --place-source-ref-id <PLACE_SOURCE_REF_ID_2> `
#     --max-total-places 2
#
# Opciones importantes:
#
#   --skip-import
#       Ejecuta hasta staging/check staging, pero no inserta en hidden_gems.review.
#
#   --dry-run
#       Solo construye plan.json. No llama a Google.
#
#   --include-already-reviewed
#       Incluye locales que ya tienen reviews Google importadas.
#       Por defecto el batch prioriza locales sin reviews previas.
#
#   --require-reviews
#       Fuerza error si un local no devuelve reviews aceptadas.
#       Por defecto se permite que Google devuelva 0 reviews.
#
#   --max-total-places
#       Límite de seguridad. Evita lanzar batches grandes por accidente.
#
#   --allow-large-batch
#       Permite superar max-total-places. Usar solo si ya se ha validado el flujo.
#
# Después de ejecutar un batch real, validar con:
#
#   python -m scripts.check_google_places_reviews_batch `
#     --batch-name <BATCH_NAME> `
#     --save-artifact
#
# Artefactos generados:
#
#   data/artifacts/google_places_reviews_batches/<batch_name>/plan.json
#   data/artifacts/google_places_reviews_batches/<batch_name>/results.json
#   data/artifacts/google_places_reviews_batches/<batch_name>/batch_summary.json
#
# -----------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta un batch controlado de Google Places Reviews usando "
            "scripts.load_google_places_reviews_pipeline como unidad operativa."
        )
    )

    parser.add_argument(
        "--batch-name",
        type=str,
        default=None,
        help="Nombre lógico del batch. Si no se indica, se genera automáticamente.",
    )

    parser.add_argument(
        "--place-source-ref-id",
        action="append",
        default=None,
        help=(
            "place_source_ref_id concreto de Google Places. "
            "Se puede repetir. Si se indica, tiene prioridad sobre filtros."
        ),
    )

    parser.add_argument(
        "--neighborhood",
        action="append",
        default=None,
        help="Filtra locales por barrio. Se puede repetir.",
    )

    parser.add_argument(
        "--district",
        action="append",
        default=None,
        help="Filtra locales por distrito. Se puede repetir.",
    )

    parser.add_argument(
        "--limit-places",
        type=int,
        default=5,
        help="Número máximo de locales a procesar. Por defecto: 5.",
    )

    parser.add_argument(
        "--max-total-places",
        type=int,
        default=5,
        help="Máximo de locales permitido por seguridad. Por defecto: 5.",
    )

    parser.add_argument(
        "--allow-large-batch",
        action="store_true",
        help="Permite superar max-total-places. No recomendado al principio.",
    )

    parser.add_argument(
        "--include-already-reviewed",
        action="store_true",
        help=(
            "Incluye locales que ya tienen reviews de Google importadas. "
            "Por defecto se priorizan/exigen locales sin reviews Google."
        ),
    )

    parser.add_argument(
        "--language-code",
        type=str,
        default="es",
        help="Idioma de respuesta para Place Details. Por defecto: es.",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        default="ES",
        help="Región de respuesta para Place Details. Por defecto: ES.",
    )

    parser.add_argument(
        "--include-rating-summary",
        action="store_true",
        help=(
            "Incluye rating y userRatingCount en FieldMask. "
            "No necesario para importar reviews."
        ),
    )

    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Ejecuta cada pipeline hasta staging/check staging, sin importar reviews.",
    )

    parser.add_argument(
        "--require-reviews",
        action="store_true",
        help=(
            "Si se activa, cada pipeline falla si Google no devuelve reviews aceptadas. "
            "Por defecto se permiten locales sin reviews devueltas."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo construye y muestra el plan, sin llamar a Google Places.",
    )

    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Pausa entre locales para no saturar la API.",
    )

    parser.add_argument(
        "--max-errors",
        type=int,
        default=2,
        help="Número máximo de errores tolerados antes de detener el batch.",
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Detiene el batch en el primer error.",
    )

    return parser


def utc_now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(value: str, max_length: int = 60) -> str:
    text_value = value.strip().lower()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(
        character for character in text_value if not unicodedata.combining(character)
    )
    text_value = re.sub(r"[^\w\s-]", "", text_value, flags=re.UNICODE)
    text_value = re.sub(r"[-\s]+", "_", text_value)
    return text_value[:max_length].strip("_") or "item"


def normalize_for_match(value: str) -> str:
    text_value = value.strip()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(
        character for character in text_value if not unicodedata.combining(character)
    )
    text_value = text_value.lower()
    text_value = re.sub(r"\s+", " ", text_value)
    return text_value


def fetch_google_place_source_refs() -> list[dict[str, Any]]:
    query = text(
        """
        WITH google_review_counts AS (
            SELECT
                r.place_source_ref_id,
                COUNT(*) AS existing_google_review_count
            FROM hidden_gems.review r
            JOIN hidden_gems.source_system ss_review
                ON ss_review.source_system_id = r.source_system_id
            WHERE ss_review.source_code = 'google_places'
              AND r.place_source_ref_id IS NOT NULL
              AND r.is_active = TRUE
              AND r.is_deleted_in_source = FALSE
            GROUP BY r.place_source_ref_id
        )
        SELECT
            psr.place_source_ref_id::text AS place_source_ref_id,
            psr.place_id::text AS place_id,
            psr.source_record_id AS google_place_id,
            psr.source_name_raw,
            p.display_name AS place_display_name,
            p.canonical_name AS place_canonical_name,
            COALESCE(n.official_name, 'unknown') AS neighborhood_name,
            COALESCE(d.official_name, 'unknown') AS district_name,
            COALESCE(grc.existing_google_review_count, 0) AS existing_google_review_count
        FROM hidden_gems.place_source_ref psr
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = psr.source_system_id
        JOIN hidden_gems.place p
            ON p.place_id = psr.place_id
        LEFT JOIN hidden_gems.place_neighborhood_assignment pna
            ON pna.place_id = p.place_id
           AND pna.is_current = TRUE
        LEFT JOIN hidden_gems.neighborhood n
            ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN hidden_gems.district d
            ON d.district_id = pna.district_id
        LEFT JOIN google_review_counts grc
            ON grc.place_source_ref_id = psr.place_source_ref_id
        WHERE ss.source_code = 'google_places'
          AND psr.is_current = TRUE
          AND psr.is_deleted_in_source = FALSE
          AND psr.source_record_id IS NOT NULL
        ORDER BY
            COALESCE(grc.existing_google_review_count, 0) ASC,
            psr.updated_at DESC NULLS LAST,
            psr.created_at DESC
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()

    return [dict(row) for row in rows]


def filter_by_requested_ids(
    candidates: list[dict[str, Any]],
    requested_ids: list[str] | None,
) -> list[dict[str, Any]]:
    if not requested_ids:
        return candidates

    requested_set = {value.strip() for value in requested_ids if value.strip()}
    selected = [
        candidate
        for candidate in candidates
        if candidate["place_source_ref_id"] in requested_set
    ]

    missing = requested_set - {candidate["place_source_ref_id"] for candidate in selected}
    if missing:
        raise ValueError(
            "No se encontraron algunos place_source_ref_id de Google Places: "
            f"{sorted(missing)}"
        )

    id_position = {
        value: index
        for index, value in enumerate(requested_ids)
    }

    selected.sort(
        key=lambda row: id_position.get(row["place_source_ref_id"], 999999)
    )

    return selected


def filter_by_text_fields(
    candidates: list[dict[str, Any]],
    *,
    requested_neighborhoods: list[str] | None,
    requested_districts: list[str] | None,
) -> list[dict[str, Any]]:
    selected = candidates

    if requested_neighborhoods:
        requested_normalized = [
            normalize_for_match(value)
            for value in requested_neighborhoods
        ]

        selected = [
            candidate
            for candidate in selected
            if any(
                requested == normalize_for_match(str(candidate["neighborhood_name"]))
                or requested in normalize_for_match(str(candidate["neighborhood_name"]))
                for requested in requested_normalized
            )
        ]

    if requested_districts:
        requested_normalized = [
            normalize_for_match(value)
            for value in requested_districts
        ]

        selected = [
            candidate
            for candidate in selected
            if any(
                requested == normalize_for_match(str(candidate["district_name"]))
                or requested in normalize_for_match(str(candidate["district_name"]))
                for requested in requested_normalized
            )
        ]

    return selected


def select_candidates(
    *,
    requested_ids: list[str] | None,
    requested_neighborhoods: list[str] | None,
    requested_districts: list[str] | None,
    limit_places: int,
    include_already_reviewed: bool,
) -> list[dict[str, Any]]:
    candidates = fetch_google_place_source_refs()

    if requested_ids:
        selected = filter_by_requested_ids(candidates, requested_ids)
    else:
        selected = filter_by_text_fields(
            candidates,
            requested_neighborhoods=requested_neighborhoods,
            requested_districts=requested_districts,
        )

        if not include_already_reviewed:
            selected = [
                candidate
                for candidate in selected
                if int(candidate.get("existing_google_review_count") or 0) == 0
            ]

    if limit_places < 1:
        raise ValueError("limit-places debe ser mayor que 0.")

    selected = selected[:limit_places]

    if not selected:
        raise ValueError(
            "No se seleccionó ningún local Google Places para el batch. "
            "Prueba con --include-already-reviewed, otro filtro o IDs explícitos."
        )

    return selected


def validate_safety_limits(
    *,
    plan: list[dict[str, Any]],
    max_total_places: int,
    allow_large_batch: bool,
) -> None:
    if max_total_places < 1:
        raise ValueError("max-total-places debe ser mayor que 0.")

    if len(plan) > max_total_places and not allow_large_batch:
        raise ValueError(
            f"El plan contiene {len(plan)} locales, pero max-total-places={max_total_places}. "
            "Reduce --limit-places o usa --allow-large-batch si realmente quieres permitirlo."
        )


def build_plan(
    *,
    batch_name: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []

    for index, candidate in enumerate(candidates, start=1):
        place_name = (
            candidate.get("place_display_name")
            or candidate.get("source_name_raw")
            or candidate.get("place_canonical_name")
            or "place"
        )

        query_name = "_".join(
            [
                slugify(batch_name, 24),
                f"p{index:02d}",
                slugify(str(place_name), 24),
            ]
        )

        plan.append(
            {
                "batch_name": batch_name,
                "position": index,
                "query_name": query_name,
                "place_source_ref_id": candidate["place_source_ref_id"],
                "place_id": candidate["place_id"],
                "google_place_id": candidate["google_place_id"],
                "place_display_name": candidate.get("place_display_name"),
                "source_name_raw": candidate.get("source_name_raw"),
                "neighborhood_name": candidate.get("neighborhood_name"),
                "district_name": candidate.get("district_name"),
                "existing_google_review_count": int(
                    candidate.get("existing_google_review_count") or 0
                ),
            }
        )

    return plan


def extract_last_json_object(stdout: str) -> dict[str, Any]:
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

    raise ValueError("No se pudo extraer el JSON final completo del stdout del pipeline.")


def run_single_pipeline(
    *,
    row: dict[str, Any],
    language_code: str,
    region_code: str,
    include_rating_summary: bool,
    skip_import: bool,
    require_reviews: bool,
) -> dict[str, Any]:
    command = [
        sys.executable,
        "-m",
        "scripts.load_google_places_reviews_pipeline",
        "--place-source-ref-id",
        row["place_source_ref_id"],
        "--query-name",
        row["query_name"],
        "--language-code",
        language_code,
        "--region-code",
        region_code,
    ]

    if include_rating_summary:
        command.append("--include-rating-summary")

    if skip_import:
        command.append("--skip-import")

    if require_reviews:
        command.append("--require-reviews")

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
        "place_source_ref_id": row["place_source_ref_id"],
        "place_id": row["place_id"],
        "google_place_id": row["google_place_id"],
        "place_display_name": row["place_display_name"],
        "neighborhood_name": row["neighborhood_name"],
        "district_name": row["district_name"],
        "existing_google_review_count_before": row["existing_google_review_count"],
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
        result["staging_summary"] = pipeline_output.get("staging_summary")
        result["import_summary"] = pipeline_output.get("import_summary")
        result["checks"] = pipeline_output.get("checks")
        result["paths"] = pipeline_output.get("paths")
    else:
        result["error"] = {
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": completed.stderr[-4000:],
        }

    return result


def _as_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value)
    return 0


def sum_nested(results: list[dict[str, Any]], path: tuple[str, ...]) -> int:
    total = 0

    for result in results:
        if not result.get("success"):
            continue

        current: Any = result

        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)

        total += _as_int(current)

    return total


def summarize_batch_results(
    *,
    batch_name: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    skip_import: bool,
) -> dict[str, Any]:
    success_results = [
        result
        for result in results
        if result.get("success")
    ]
    error_results = [
        result
        for result in results
        if not result.get("success")
    ]

    neighborhoods_processed = sorted(
        {
            str(result["neighborhood_name"])
            for result in results
            if result.get("neighborhood_name")
        }
    )

    districts_processed = sorted(
        {
            str(result["district_name"])
            for result in results
            if result.get("district_name")
        }
    )

    return {
        "batch_name": batch_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "skip_import": skip_import,
        "planned_place_count": len(plan),
        "executed_place_count": len(results),
        "success_count": len(success_results),
        "error_count": len(error_results),
        "districts_processed": districts_processed,
        "neighborhoods_processed": neighborhoods_processed,
        "places_with_success": [
            {
                "place_display_name": result.get("place_display_name"),
                "place_source_ref_id": result.get("place_source_ref_id"),
                "google_place_id": result.get("google_place_id"),
                "neighborhood_name": result.get("neighborhood_name"),
            }
            for result in success_results
        ],
        "places_with_error": [
            {
                "place_display_name": result.get("place_display_name"),
                "place_source_ref_id": result.get("place_source_ref_id"),
                "google_place_id": result.get("google_place_id"),
                "neighborhood_name": result.get("neighborhood_name"),
                "error": result.get("error"),
            }
            for result in error_results
        ],
        "totals": {
            "raw_review_count": sum_nested(results, ("raw_summary", "review_count")),
            "staging_total_reviews": sum_nested(results, ("staging_summary", "total_reviews")),
            "staging_accepted_count": sum_nested(results, ("staging_summary", "accepted_count")),
            "staging_rejected_count": sum_nested(results, ("staging_summary", "rejected_count")),
            "staging_skipped_count": sum_nested(results, ("staging_summary", "skipped_count")),
            "staging_issue_count": sum_nested(results, ("staging_summary", "issue_count")),
            "imported_count": sum_nested(results, ("import_summary", "imported_count")),
            "inserted_count": sum_nested(results, ("import_summary", "inserted_count")),
            "updated_count": sum_nested(results, ("import_summary", "updated_count")),
            "import_skipped_count": sum_nested(results, ("import_summary", "skipped_count")),
            "validation_issue_count": sum_nested(results, ("import_summary", "validation_issue_count")),
        },
    }


def save_batch_artifacts(
    *,
    batch_name: str,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, str]:
    output_dir = settings.data_artifacts_path / "google_places_reviews_batches" / batch_name
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

    batch_name = args.batch_name or f"google_places_reviews_batch_{utc_now_compact()}"
    batch_name = slugify(batch_name, 80)

    selected_candidates = select_candidates(
        requested_ids=args.place_source_ref_id,
        requested_neighborhoods=args.neighborhood,
        requested_districts=args.district,
        limit_places=args.limit_places,
        include_already_reviewed=args.include_already_reviewed,
    )

    plan = build_plan(
        batch_name=batch_name,
        candidates=selected_candidates,
    )

    validate_safety_limits(
        plan=plan,
        max_total_places=args.max_total_places,
        allow_large_batch=args.allow_large_batch,
    )

    logger.info(
        "Plan Google Places Reviews batch construido | batch_name=%s | places=%s | dry_run=%s | skip_import=%s",
        batch_name,
        len(plan),
        args.dry_run,
        args.skip_import,
    )

    if args.dry_run:
        summary = {
            "batch_name": batch_name,
            "dry_run": True,
            "planned_place_count": len(plan),
            "skip_import": args.skip_import,
            "plan": plan,
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
        logger.info("Dry-run de batch Google Places Reviews completado correctamente.")
        return 0

    results: list[dict[str, Any]] = []
    error_count = 0

    for index, row in enumerate(plan, start=1):
        logger.info(
            "Ejecutando reviews pipeline %s/%s | place=%s | neighborhood=%s | query_name=%s",
            index,
            len(plan),
            row.get("place_display_name"),
            row.get("neighborhood_name"),
            row["query_name"],
        )

        try:
            result = run_single_pipeline(
                row=row,
                language_code=args.language_code,
                region_code=args.region_code,
                include_rating_summary=args.include_rating_summary,
                skip_import=args.skip_import,
                require_reviews=args.require_reviews,
            )
        except Exception as exc:
            result = {
                **row,
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
                "Pipeline de reviews fallido | query_name=%s | error_count=%s",
                row["query_name"],
                error_count,
            )

            if args.stop_on_error or error_count >= args.max_errors:
                logger.warning(
                    "Batch de reviews detenido por política de errores | stop_on_error=%s | error_count=%s | max_errors=%s",
                    args.stop_on_error,
                    error_count,
                    args.max_errors,
                )
                break

        if index < len(plan) and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

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
            "Batch Google Places Reviews finalizado con errores | batch_name=%s | errors=%s",
            batch_name,
            summary["error_count"],
        )
        return 1

    logger.info(
        "Batch Google Places Reviews finalizado correctamente | batch_name=%s | success=%s",
        batch_name,
        summary["success_count"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())