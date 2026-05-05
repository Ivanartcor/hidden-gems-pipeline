from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


TOTAL_FIELDS = [
    "raw_place_count",
    "accepted_count",
    "needs_review_count",
    "rejected_count",
    "transform_issue_count",
    "dedup_output_count",
    "dedup_duplicate_group_count",
    "imported_count",
    "skipped_count",
    "place_created_count",
    "place_updated_count",
    "place_source_ref_created_count",
    "place_source_ref_updated_count",
    "validation_issue_count",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba la coherencia global de un batch de Google Places por barrios."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--batch-name",
        type=str,
        help="Nombre del batch dentro de data/artifacts/google_places_batches.",
    )
    source_group.add_argument(
        "--batch-dir",
        type=str,
        help="Ruta directa al directorio del batch.",
    )

    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="Permite que el batch tenga consultas fallidas sin devolver código 1.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda batch_check.json dentro del directorio del batch.",
    )

    return parser


def resolve_batch_dir(args: argparse.Namespace) -> Path:
    if args.batch_dir:
        batch_dir = Path(args.batch_dir)
    else:
        batch_dir = settings.data_artifacts_path / "google_places_batches" / args.batch_name

    if not batch_dir.exists():
        raise FileNotFoundError(f"No existe el directorio del batch: {batch_dir}")

    if not batch_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {batch_dir}")

    return batch_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def sum_result_field(
    results: list[dict[str, Any]],
    *,
    summary_name: str,
    field_name: str,
) -> int:
    total = 0

    for result in results:
        if not result.get("success"):
            continue

        if summary_name == "raw_summary":
            value = get_nested(result, ("raw_summary", field_name))
        elif summary_name == "transform_summary":
            value = get_nested(result, ("transform_summary", field_name))
        elif summary_name == "dedup_summary":
            value = get_nested(result, ("dedup_summary", field_name))
        elif summary_name == "import_summary":
            value = get_nested(result, ("import_summary", field_name))
        else:
            value = None

        if isinstance(value, int):
            total += value

    return total


def recompute_totals(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "raw_place_count": sum_result_field(
            results,
            summary_name="raw_summary",
            field_name="place_count",
        ),
        "accepted_count": sum_result_field(
            results,
            summary_name="transform_summary",
            field_name="accepted_count",
        ),
        "needs_review_count": sum_result_field(
            results,
            summary_name="transform_summary",
            field_name="needs_review_count",
        ),
        "rejected_count": sum_result_field(
            results,
            summary_name="transform_summary",
            field_name="rejected_count",
        ),
        "transform_issue_count": sum_result_field(
            results,
            summary_name="transform_summary",
            field_name="issue_count",
        ),
        "dedup_output_count": sum_result_field(
            results,
            summary_name="dedup_summary",
            field_name="output_count",
        ),
        "dedup_duplicate_group_count": sum_result_field(
            results,
            summary_name="dedup_summary",
            field_name="duplicate_group_count",
        ),
        "imported_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="imported_count",
        ),
        "skipped_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="skipped_count",
        ),
        "place_created_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="place_created_count",
        ),
        "place_updated_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="place_updated_count",
        ),
        "place_source_ref_created_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="place_source_ref_created_count",
        ),
        "place_source_ref_updated_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="place_source_ref_updated_count",
        ),
        "validation_issue_count": sum_result_field(
            results,
            summary_name="import_summary",
            field_name="validation_issue_count",
        ),
    }

def collect_success_result_ids(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    source_run_ids: list[str] = []
    raw_asset_ids: list[str] = []

    for result in results:
        if not result.get("success"):
            continue

        source_run_id = result.get("source_run_id")
        raw_asset_id = result.get("raw_asset_id")

        if source_run_id:
            source_run_ids.append(str(source_run_id))

        if raw_asset_id:
            raw_asset_ids.append(str(raw_asset_id))

    return {
        "source_run_ids": source_run_ids,
        "raw_asset_ids": raw_asset_ids,
    }


def find_duplicates(values: list[str]) -> list[dict[str, Any]]:
    counter = Counter(values)

    duplicates = [
        {
            "value": value,
            "count": count,
        }
        for value, count in counter.items()
        if count > 1
    ]

    duplicates.sort(key=lambda row: row["count"], reverse=True)
    return duplicates


def profile_results(results: list[dict[str, Any]]) -> dict[str, Any]:
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
            str(result.get("neighborhood_name"))
            for result in results
            if result.get("neighborhood_name")
        }
    )
    neighborhoods_with_success = sorted(
        {
            str(result.get("neighborhood_name"))
            for result in success_results
            if result.get("neighborhood_name")
        }
    )
    neighborhoods_with_error = sorted(
        {
            str(result.get("neighborhood_name"))
            for result in error_results
            if result.get("neighborhood_name")
        }
    )

    ids = collect_success_result_ids(results)

    return {
        "executed_query_count": len(results),
        "success_count": len(success_results),
        "error_count": len(error_results),
        "neighborhoods_processed": neighborhoods_processed,
        "neighborhoods_with_success": neighborhoods_with_success,
        "neighborhoods_with_error": neighborhoods_with_error,
        "source_run_ids": ids["source_run_ids"],
        "raw_asset_ids": ids["raw_asset_ids"],
        "duplicate_source_run_ids": find_duplicates(ids["source_run_ids"]),
        "duplicate_raw_asset_ids": find_duplicates(ids["raw_asset_ids"]),
        "failed_queries": [
            {
                "query_name": result.get("query_name"),
                "text_query": result.get("text_query"),
                "neighborhood_name": result.get("neighborhood_name"),
                "return_code": result.get("return_code"),
                "error": result.get("error"),
            }
            for result in error_results
        ],
    }


def build_checks(
    *,
    plan: list[dict[str, Any]],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    recomputed_totals: dict[str, int],
    result_profile: dict[str, Any],
    allow_errors: bool,
) -> dict[str, bool]:
    query_names = [
        str(row.get("query_name"))
        for row in plan
        if row.get("query_name")
    ]

    duplicate_query_names = find_duplicates(query_names)

    summary_totals = summary.get("totals", {}) or {}

    totals_match = True
    for field_name in TOTAL_FIELDS:
        if int(summary_totals.get(field_name) or 0) != int(recomputed_totals.get(field_name) or 0):
            totals_match = False
            break

    success_results = [
        result
        for result in results
        if result.get("success")
    ]

    all_success_have_pipeline_output = all(
        isinstance(result.get("pipeline_output"), dict)
        for result in success_results
    )

    all_success_have_source_run_id = all(
        bool(result.get("source_run_id"))
        for result in success_results
    )

    all_success_have_raw_asset_id = all(
        bool(result.get("raw_asset_id"))
        for result in success_results
    )

    all_success_have_transform_summary = all(
        isinstance(result.get("transform_summary"), dict)
        for result in success_results
    )

    all_success_have_dedup_summary = all(
        isinstance(result.get("dedup_summary"), dict)
        for result in success_results
    )

    skip_import = bool(summary.get("skip_import"))

    if skip_import:
        all_success_have_import_summary = True
        all_import_checks_pass = True
    else:
        all_success_have_import_summary = all(
            isinstance(result.get("import_summary"), dict)
            for result in success_results
        )

        all_import_checks_pass = True
        for result in success_results:
            pipeline_output = result.get("pipeline_output") or {}
            import_checks = get_nested(pipeline_output, ("checks", "import"))

            if not isinstance(import_checks, dict):
                all_import_checks_pass = False
                break

            if not all(bool(value) for value in import_checks.values()):
                all_import_checks_pass = False
                break

    return {
        "plan_has_no_duplicate_query_names": len(duplicate_query_names) == 0,
        "planned_query_count_matches_plan": (
            int(summary.get("planned_query_count") or 0) == len(plan)
        ),
        "executed_query_count_matches_results": (
            int(summary.get("executed_query_count") or 0) == len(results)
        ),
        "success_count_matches_results": (
            int(summary.get("success_count") or 0)
            == int(result_profile["success_count"])
        ),
        "error_count_matches_results": (
            int(summary.get("error_count") or 0)
            == int(result_profile["error_count"])
        ),
        "no_errors_or_allowed": allow_errors or int(result_profile["error_count"]) == 0,
        "summary_totals_match_recomputed_totals": totals_match,
        "all_success_have_pipeline_output": all_success_have_pipeline_output,
        "all_success_have_source_run_id": all_success_have_source_run_id,
        "all_success_have_raw_asset_id": all_success_have_raw_asset_id,
        "all_success_have_transform_summary": all_success_have_transform_summary,
        "all_success_have_dedup_summary": all_success_have_dedup_summary,
        "all_success_have_import_summary_when_required": all_success_have_import_summary,
        "all_import_checks_pass_when_required": all_import_checks_pass,
        "no_duplicate_source_run_ids": len(result_profile["duplicate_source_run_ids"]) == 0,
        "no_duplicate_raw_asset_ids": len(result_profile["duplicate_raw_asset_ids"]) == 0,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    batch_dir = resolve_batch_dir(args)

    plan = load_json_file(batch_dir / "plan.json")
    results = load_json_file(batch_dir / "results.json")
    summary = load_json_file(batch_dir / "batch_summary.json")

    if not isinstance(plan, list):
        raise ValueError("plan.json no contiene una lista válida.")

    if not isinstance(results, list):
        raise ValueError("results.json no contiene una lista válida.")

    if not isinstance(summary, dict):
        raise ValueError("batch_summary.json no contiene un objeto válido.")

    recomputed_totals = recompute_totals(results)
    result_profile = profile_results(results)

    checks = build_checks(
        plan=plan,
        results=results,
        summary=summary,
        recomputed_totals=recomputed_totals,
        result_profile=result_profile,
        allow_errors=args.allow_errors,
    )

    output = {
        "batch_dir": str(batch_dir),
        "summary": summary,
        "result_profile": result_profile,
        "recomputed_totals": recomputed_totals,
        "checks": checks,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    if args.save_artifact:
        output_path = batch_dir / "batch_check.json"
        output_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        logger.info("Check de batch guardado en: %s", output_path)

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Check de batch Google Places completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check de batch Google Places completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())