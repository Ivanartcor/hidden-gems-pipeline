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
    "raw_review_count",
    "staging_total_reviews",
    "staging_accepted_count",
    "staging_rejected_count",
    "staging_skipped_count",
    "staging_issue_count",
    "imported_count",
    "inserted_count",
    "updated_count",
    "import_skipped_count",
    "validation_issue_count",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba la coherencia global de un batch de Google Places Reviews."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--batch-name",
        type=str,
        help="Nombre del batch dentro de data/artifacts/google_places_reviews_batches.",
    )
    source_group.add_argument(
        "--batch-dir",
        type=str,
        help="Ruta directa al directorio del batch.",
    )

    parser.add_argument(
        "--allow-errors",
        action="store_true",
        help="Permite que el batch tenga pipelines fallidos sin devolver código 1.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda reviews_batch_check.json dentro del directorio del batch.",
    )

    return parser


def resolve_batch_dir(args: argparse.Namespace) -> Path:
    if args.batch_dir:
        batch_dir = Path(args.batch_dir)
    else:
        batch_dir = (
            settings.data_artifacts_path
            / "google_places_reviews_batches"
            / args.batch_name
        )

    if not batch_dir.exists():
        raise FileNotFoundError(f"No existe el directorio del batch: {batch_dir}")

    if not batch_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {batch_dir}")

    return batch_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        clean = value.strip()
        if clean.isdigit():
            return int(clean)

    return 0


def find_duplicates(values: list[str]) -> list[dict[str, Any]]:
    counter = Counter(values)

    duplicates = [
        {
            "value": value,
            "count": count,
        }
        for value, count in counter.items()
        if value and count > 1
    ]

    duplicates.sort(key=lambda row: row["count"], reverse=True)
    return duplicates


def sum_nested(results: list[dict[str, Any]], path: tuple[str, ...]) -> int:
    total = 0

    for result in results:
        if not result.get("success"):
            continue

        value = get_nested(result, path)
        total += as_int(value)

    return total


def recompute_totals(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "raw_review_count": sum_nested(
            results,
            ("raw_summary", "review_count"),
        ),
        "staging_total_reviews": sum_nested(
            results,
            ("staging_summary", "total_reviews"),
        ),
        "staging_accepted_count": sum_nested(
            results,
            ("staging_summary", "accepted_count"),
        ),
        "staging_rejected_count": sum_nested(
            results,
            ("staging_summary", "rejected_count"),
        ),
        "staging_skipped_count": sum_nested(
            results,
            ("staging_summary", "skipped_count"),
        ),
        "staging_issue_count": sum_nested(
            results,
            ("staging_summary", "issue_count"),
        ),
        "imported_count": sum_nested(
            results,
            ("import_summary", "imported_count"),
        ),
        "inserted_count": sum_nested(
            results,
            ("import_summary", "inserted_count"),
        ),
        "updated_count": sum_nested(
            results,
            ("import_summary", "updated_count"),
        ),
        "import_skipped_count": sum_nested(
            results,
            ("import_summary", "skipped_count"),
        ),
        "validation_issue_count": sum_nested(
            results,
            ("import_summary", "validation_issue_count"),
        ),
    }


def collect_success_ids(results: list[dict[str, Any]]) -> dict[str, list[str]]:
    source_run_ids: list[str] = []
    raw_asset_ids: list[str] = []
    place_source_ref_ids: list[str] = []
    google_place_ids: list[str] = []

    for result in results:
        if not result.get("success"):
            continue

        if result.get("source_run_id"):
            source_run_ids.append(str(result["source_run_id"]))

        if result.get("raw_asset_id"):
            raw_asset_ids.append(str(result["raw_asset_id"]))

        if result.get("place_source_ref_id"):
            place_source_ref_ids.append(str(result["place_source_ref_id"]))

        if result.get("google_place_id"):
            google_place_ids.append(str(result["google_place_id"]))

    return {
        "source_run_ids": source_run_ids,
        "raw_asset_ids": raw_asset_ids,
        "place_source_ref_ids": place_source_ref_ids,
        "google_place_ids": google_place_ids,
    }


def all_checks_pass(checks: Any) -> bool:
    if not isinstance(checks, dict):
        return False

    return all(bool(value) for value in checks.values())


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

    ids = collect_success_ids(results)

    districts_processed = sorted(
        {
            str(result.get("district_name"))
            for result in results
            if result.get("district_name")
        }
    )

    neighborhoods_processed = sorted(
        {
            str(result.get("neighborhood_name"))
            for result in results
            if result.get("neighborhood_name")
        }
    )

    places_processed = [
        {
            "place_display_name": result.get("place_display_name"),
            "place_source_ref_id": result.get("place_source_ref_id"),
            "google_place_id": result.get("google_place_id"),
            "neighborhood_name": result.get("neighborhood_name"),
            "district_name": result.get("district_name"),
            "success": result.get("success"),
            "raw_asset_id": result.get("raw_asset_id"),
            "source_run_id": result.get("source_run_id"),
        }
        for result in results
    ]

    failed_queries = [
        {
            "query_name": result.get("query_name"),
            "place_display_name": result.get("place_display_name"),
            "place_source_ref_id": result.get("place_source_ref_id"),
            "google_place_id": result.get("google_place_id"),
            "neighborhood_name": result.get("neighborhood_name"),
            "district_name": result.get("district_name"),
            "return_code": result.get("return_code"),
            "error": result.get("error"),
        }
        for result in error_results
    ]

    staging_failed_internal_checks: list[dict[str, Any]] = []
    import_failed_internal_checks: list[dict[str, Any]] = []

    for result in success_results:
        staging_checks = get_nested(result, ("checks", "staging"))
        import_checks = get_nested(result, ("checks", "import"))

        if isinstance(staging_checks, dict):
            failed = [
                name
                for name, passed in staging_checks.items()
                if not passed
            ]
            if failed:
                staging_failed_internal_checks.append(
                    {
                        "query_name": result.get("query_name"),
                        "place_display_name": result.get("place_display_name"),
                        "raw_asset_id": result.get("raw_asset_id"),
                        "failed_checks": failed,
                    }
                )
        else:
            staging_failed_internal_checks.append(
                {
                    "query_name": result.get("query_name"),
                    "place_display_name": result.get("place_display_name"),
                    "raw_asset_id": result.get("raw_asset_id"),
                    "failed_checks": ["missing_staging_checks"],
                }
            )

        if import_checks is not None:
            if isinstance(import_checks, dict):
                failed = [
                    name
                    for name, passed in import_checks.items()
                    if not passed
                ]
                if failed:
                    import_failed_internal_checks.append(
                        {
                            "query_name": result.get("query_name"),
                            "place_display_name": result.get("place_display_name"),
                            "raw_asset_id": result.get("raw_asset_id"),
                            "failed_checks": failed,
                        }
                    )
            else:
                import_failed_internal_checks.append(
                    {
                        "query_name": result.get("query_name"),
                        "place_display_name": result.get("place_display_name"),
                        "raw_asset_id": result.get("raw_asset_id"),
                        "failed_checks": ["invalid_import_checks_structure"],
                    }
                )

    return {
        "executed_place_count": len(results),
        "success_count": len(success_results),
        "error_count": len(error_results),
        "districts_processed": districts_processed,
        "neighborhoods_processed": neighborhoods_processed,
        "places_processed": places_processed,
        "failed_queries": failed_queries,
        "source_run_ids": ids["source_run_ids"],
        "raw_asset_ids": ids["raw_asset_ids"],
        "place_source_ref_ids": ids["place_source_ref_ids"],
        "google_place_ids": ids["google_place_ids"],
        "duplicate_source_run_ids": find_duplicates(ids["source_run_ids"]),
        "duplicate_raw_asset_ids": find_duplicates(ids["raw_asset_ids"]),
        "duplicate_place_source_ref_ids": find_duplicates(ids["place_source_ref_ids"]),
        "duplicate_google_place_ids": find_duplicates(ids["google_place_ids"]),
        "staging_failed_internal_checks": staging_failed_internal_checks,
        "import_failed_internal_checks": import_failed_internal_checks,
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
    dry_run = bool(summary.get("dry_run"))
    skip_import = bool(summary.get("skip_import"))

    plan_query_names = [
        str(row.get("query_name"))
        for row in plan
        if row.get("query_name")
    ]

    duplicate_query_names = find_duplicates(plan_query_names)

    summary_totals = summary.get("totals") or {}

    totals_match = True
    if not dry_run:
        for field_name in TOTAL_FIELDS:
            if as_int(summary_totals.get(field_name)) != as_int(
                recomputed_totals.get(field_name)
            ):
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

    all_success_have_raw_summary = all(
        isinstance(result.get("raw_summary"), dict)
        for result in success_results
    )

    all_success_have_staging_summary = all(
        isinstance(result.get("staging_summary"), dict)
        for result in success_results
    )

    all_success_have_staging_checks = all(
        isinstance(get_nested(result, ("checks", "staging")), dict)
        for result in success_results
    )

    all_staging_checks_pass = all(
        all_checks_pass(get_nested(result, ("checks", "staging")))
        for result in success_results
    )

    if dry_run:
        all_success_have_pipeline_output = True
        all_success_have_source_run_id = True
        all_success_have_raw_asset_id = True
        all_success_have_raw_summary = True
        all_success_have_staging_summary = True
        all_success_have_staging_checks = True
        all_staging_checks_pass = True

    if skip_import or dry_run:
        all_success_have_import_summary_when_required = True
        all_success_have_import_checks_when_required = True
        all_import_checks_pass_when_required = True
        no_imports_when_skip_import = (
            as_int(summary_totals.get("imported_count")) == 0
            and as_int(summary_totals.get("inserted_count")) == 0
            and as_int(summary_totals.get("updated_count")) == 0
        )
    else:
        all_success_have_import_summary_when_required = all(
            isinstance(result.get("import_summary"), dict)
            for result in success_results
        )

        all_success_have_import_checks_when_required = all(
            isinstance(get_nested(result, ("checks", "import")), dict)
            for result in success_results
        )

        all_import_checks_pass_when_required = all(
            all_checks_pass(get_nested(result, ("checks", "import")))
            for result in success_results
        )

        no_imports_when_skip_import = True

    staging_parts_match_total = (
        as_int(summary_totals.get("staging_total_reviews"))
        == as_int(summary_totals.get("staging_accepted_count"))
        + as_int(summary_totals.get("staging_rejected_count"))
        + as_int(summary_totals.get("staging_skipped_count"))
    )

    import_count_matches_parts = (
        as_int(summary_totals.get("imported_count"))
        == as_int(summary_totals.get("inserted_count"))
        + as_int(summary_totals.get("updated_count"))
    )

    if dry_run:
        staging_parts_match_total = True
        import_count_matches_parts = True

    return {
        "plan_has_no_duplicate_query_names": len(duplicate_query_names) == 0,
        "planned_place_count_matches_plan": (
            as_int(summary.get("planned_place_count")) == len(plan)
        ),
        "executed_place_count_matches_results": (
            as_int(summary.get("executed_place_count")) == len(results)
            if not dry_run
            else len(results) == 0
        ),
        "success_count_matches_results": (
            as_int(summary.get("success_count")) == as_int(result_profile["success_count"])
            if not dry_run
            else True
        ),
        "error_count_matches_results": (
            as_int(summary.get("error_count")) == as_int(result_profile["error_count"])
            if not dry_run
            else True
        ),
        "no_errors_or_allowed": (
            allow_errors
            or dry_run
            or as_int(result_profile["error_count"]) == 0
        ),
        "summary_totals_match_recomputed_totals": totals_match,
        "staging_parts_match_total": staging_parts_match_total,
        "import_count_matches_parts": import_count_matches_parts,
        "all_success_have_pipeline_output": all_success_have_pipeline_output,
        "all_success_have_source_run_id": all_success_have_source_run_id,
        "all_success_have_raw_asset_id": all_success_have_raw_asset_id,
        "all_success_have_raw_summary": all_success_have_raw_summary,
        "all_success_have_staging_summary": all_success_have_staging_summary,
        "all_success_have_staging_checks": all_success_have_staging_checks,
        "all_staging_checks_pass": all_staging_checks_pass,
        "all_success_have_import_summary_when_required": all_success_have_import_summary_when_required,
        "all_success_have_import_checks_when_required": all_success_have_import_checks_when_required,
        "all_import_checks_pass_when_required": all_import_checks_pass_when_required,
        "no_imports_when_skip_import": no_imports_when_skip_import,
        "no_duplicate_source_run_ids": len(result_profile["duplicate_source_run_ids"]) == 0,
        "no_duplicate_raw_asset_ids": len(result_profile["duplicate_raw_asset_ids"]) == 0,
        "no_duplicate_place_source_ref_ids_in_success_scope": (
            len(result_profile["duplicate_place_source_ref_ids"]) == 0
        ),
        "no_duplicate_google_place_ids_in_success_scope": (
            len(result_profile["duplicate_google_place_ids"]) == 0
        ),
        "no_failed_internal_staging_checks": (
            len(result_profile["staging_failed_internal_checks"]) == 0
        ),
        "no_failed_internal_import_checks": (
            len(result_profile["import_failed_internal_checks"]) == 0
        ),
    }


def save_check_artifact(
    *,
    batch_dir: Path,
    output: dict[str, Any],
) -> Path:
    output_path = batch_dir / "reviews_batch_check.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


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

    if args.save_artifact:
        artifact_path = save_check_artifact(
            batch_dir=batch_dir,
            output=output,
        )
        output["artifact_path"] = str(artifact_path)

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Check de batch Google Places Reviews completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check de batch Google Places Reviews completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())