from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="QA sobre el staging generado por la transformación de Google Places."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--staging-dir",
        type=str,
        help="Ruta directa al directorio staging de Google Places.",
    )
    source_group.add_argument(
        "--raw-asset-id",
        type=str,
        help="raw_asset_id usado como carpeta staging en data/staging/google_places.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Número máximo de elementos a mostrar en rankings y duplicados.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el resultado del QA en data/artifacts/google_places_qa.",
    )

    return parser


def resolve_staging_dir(args: argparse.Namespace) -> Path:
    if args.staging_dir:
        staging_dir = Path(args.staging_dir)
    else:
        staging_dir = settings.data_staging_path / "google_places" / args.raw_asset_id

    if not staging_dir.exists():
        raise FileNotFoundError(f"No existe el directorio staging: {staging_dir}")

    if not staging_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {staging_dir}")

    return staging_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def safe_get(data: dict[str, Any], *path: str) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def rounded_coord_pair(candidate: dict[str, Any], decimals: int = 5) -> str | None:
    latitude = safe_get(candidate, "location", "latitude")
    longitude = safe_get(candidate, "location", "longitude")

    if latitude is None or longitude is None:
        return None

    return f"{round(float(latitude), decimals)},{round(float(longitude), decimals)}"


def profile_candidates(
    candidates: list[dict[str, Any]],
    top_n: int,
) -> dict[str, Any]:
    primary_category_counter: Counter[str] = Counter()
    google_type_counter: Counter[str] = Counter()
    food_style_counter: Counter[str] = Counter()
    business_status_counter: Counter[str] = Counter()

    missing_name_count = 0
    missing_address_count = 0
    missing_coordinates_count = 0
    missing_category_count = 0
    missing_google_maps_uri_count = 0
    missing_business_status_count = 0
    non_operational_count = 0

    duplicate_by_source_record_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate_by_normalized_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate_by_name_and_coord: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    completeness_scores: list[float] = []

    source_system_counter: Counter[str] = Counter()
    candidate_status_counter: Counter[str] = Counter()

    examples: list[dict[str, Any]] = []

    for candidate in candidates:
        source_system_code = normalize_text(
            safe_get(candidate, "provenance", "source_system_code")
        )
        source_record_id = normalize_text(
            safe_get(candidate, "provenance", "source_record_id")
        )
        display_name = normalize_text(
            safe_get(candidate, "names", "display_name")
        )
        normalized_name = normalize_text(
            safe_get(candidate, "names", "normalized_name")
        )
        source_address_raw = normalize_text(
            safe_get(candidate, "address", "source_address_raw")
        )
        source_url = normalize_text(
            safe_get(candidate, "provenance", "source_url")
        )
        business_status = normalize_text(
            safe_get(candidate, "provenance", "source_status_raw")
        )
        primary_category = normalize_text(
            safe_get(candidate, "classification", "source_primary_category_raw")
        )
        source_categories = safe_get(
            candidate, "classification", "source_categories_raw"
        ) or []
        food_styles = safe_get(
            candidate, "classification", "food_style_raw"
        ) or []
        candidate_status = normalize_text(
            safe_get(candidate, "quality", "candidate_status")
        )
        completeness_score = safe_get(candidate, "quality", "completeness_score")

        latitude = safe_get(candidate, "location", "latitude")
        longitude = safe_get(candidate, "location", "longitude")

        if source_system_code:
            source_system_counter[source_system_code] += 1

        if candidate_status:
            candidate_status_counter[candidate_status] += 1

        if primary_category:
            primary_category_counter[primary_category] += 1
        else:
            missing_category_count += 1

        if business_status:
            business_status_counter[business_status] += 1
            if business_status != "OPERATIONAL":
                non_operational_count += 1
        else:
            missing_business_status_count += 1

        for google_type in source_categories:
            clean_type = normalize_text(google_type)
            if clean_type:
                google_type_counter[clean_type] += 1

        for food_style in food_styles:
            clean_food_style = normalize_text(food_style)
            if clean_food_style:
                food_style_counter[clean_food_style] += 1

        if not display_name:
            missing_name_count += 1

        if not source_address_raw:
            missing_address_count += 1

        if latitude is None or longitude is None:
            missing_coordinates_count += 1

        if not source_url:
            missing_google_maps_uri_count += 1

        if isinstance(completeness_score, (float, int)):
            completeness_scores.append(float(completeness_score))

        if source_record_id:
            duplicate_by_source_record_id[source_record_id].append(
                {
                    "display_name": display_name,
                    "source_record_id": source_record_id,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

        if normalized_name:
            duplicate_by_normalized_name[normalized_name].append(
                {
                    "display_name": display_name,
                    "source_record_id": source_record_id,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

        coord_key = rounded_coord_pair(candidate)
        if normalized_name and coord_key:
            duplicate_by_name_and_coord[f"{normalized_name} | {coord_key}"].append(
                {
                    "display_name": display_name,
                    "source_record_id": source_record_id,
                    "coord": coord_key,
                }
            )

        if len(examples) < 5:
            examples.append(
                {
                    "source_record_id": source_record_id,
                    "display_name": display_name,
                    "source_address_raw": source_address_raw,
                    "primary_category": primary_category,
                    "latitude": latitude,
                    "longitude": longitude,
                    "business_status": business_status,
                    "candidate_status": candidate_status,
                    "completeness_score": completeness_score,
                    "source_url": source_url,
                }
            )

    def only_real_duplicates(
        source_map: dict[str, list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        for key, items in source_map.items():
            if len(items) > 1:
                rows.append(
                    {
                        "key": key,
                        "count": len(items),
                        "examples": items[:5],
                    }
                )

        rows.sort(key=lambda row: row["count"], reverse=True)
        return rows[:top_n]

    avg_completeness_score = (
        round(sum(completeness_scores) / len(completeness_scores), 4)
        if completeness_scores
        else None
    )

    min_completeness_score = (
        round(min(completeness_scores), 4)
        if completeness_scores
        else None
    )

    max_completeness_score = (
        round(max(completeness_scores), 4)
        if completeness_scores
        else None
    )

    return {
        "count": len(candidates),
        "source_system_counts": dict(source_system_counter),
        "candidate_status_counts": dict(candidate_status_counter),
        "business_status_counts": dict(business_status_counter),
        "top_primary_categories": dict(primary_category_counter.most_common(top_n)),
        "top_google_types": dict(google_type_counter.most_common(top_n)),
        "top_food_styles": dict(food_style_counter.most_common(top_n)),
        "completeness": {
            "avg_completeness_score": avg_completeness_score,
            "min_completeness_score": min_completeness_score,
            "max_completeness_score": max_completeness_score,
        },
        "missing_fields": {
            "missing_name_count": missing_name_count,
            "missing_address_count": missing_address_count,
            "missing_coordinates_count": missing_coordinates_count,
            "missing_category_count": missing_category_count,
            "missing_google_maps_uri_count": missing_google_maps_uri_count,
            "missing_business_status_count": missing_business_status_count,
        },
        "non_operational_count": non_operational_count,
        "potential_duplicates": {
            "by_source_record_id": only_real_duplicates(duplicate_by_source_record_id),
            "by_normalized_name": only_real_duplicates(duplicate_by_normalized_name),
            "by_name_and_rounded_coords": only_real_duplicates(duplicate_by_name_and_coord),
        },
        "examples": examples,
    }


def profile_review_candidates(
    candidates: list[dict[str, Any]],
    top_n: int,
) -> dict[str, Any]:
    warning_counter: Counter[str] = Counter()
    rejection_counter: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []

    for candidate in candidates:
        warnings = safe_get(candidate, "quality", "warning_messages") or []
        rejections = safe_get(candidate, "quality", "rejection_reasons") or []

        for warning in warnings:
            warning_counter[str(warning)] += 1

        for rejection in rejections:
            rejection_counter[str(rejection)] += 1

        if len(examples) < top_n:
            examples.append(
                {
                    "source_entity_type": safe_get(
                        candidate, "provenance", "source_entity_type"
                    ),
                    "source_record_id": safe_get(
                        candidate, "provenance", "source_record_id"
                    ),
                    "display_name": safe_get(candidate, "names", "display_name"),
                    "normalized_name": safe_get(candidate, "names", "normalized_name"),
                    "primary_category": safe_get(
                        candidate,
                        "classification",
                        "source_primary_category_raw",
                    ),
                    "business_status": safe_get(
                        candidate,
                        "provenance",
                        "source_status_raw",
                    ),
                    "warning_messages": warnings,
                    "rejection_reasons": rejections,
                    "completeness_score": safe_get(
                        candidate,
                        "quality",
                        "completeness_score",
                    ),
                }
            )

    return {
        "count": len(candidates),
        "warning_reasons": dict(warning_counter.most_common(top_n)),
        "rejection_reasons": dict(rejection_counter.most_common(top_n)),
        "examples": examples,
    }


def validate_staging_consistency(
    *,
    summary: dict[str, Any],
    accepted_candidates: list[dict[str, Any]],
    needs_review_candidates: list[dict[str, Any]],
    rejected_candidates: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    accepted_profile: dict[str, Any],
) -> dict[str, bool]:
    accepted_count = len(accepted_candidates)
    needs_review_count = len(needs_review_candidates)
    rejected_count = len(rejected_candidates)
    candidate_count = accepted_count + needs_review_count + rejected_count

    skipped_count = int(summary.get("skipped_count") or 0)
    total_places = int(summary.get("total_places") or 0)

    source_system_counts = accepted_profile.get("source_system_counts", {})
    duplicate_by_source_record_id = accepted_profile.get(
        "potential_duplicates",
        {},
    ).get("by_source_record_id", [])

    return {
        "summary_accepted_count_matches_file": (
            int(summary.get("accepted_count") or 0) == accepted_count
        ),
        "summary_needs_review_count_matches_file": (
            int(summary.get("needs_review_count") or 0) == needs_review_count
        ),
        "summary_rejected_count_matches_file": (
            int(summary.get("rejected_count") or 0) == rejected_count
        ),
        "summary_total_places_matches_candidates_plus_skipped": (
            total_places == candidate_count + skipped_count
        ),
        "summary_issue_count_matches_file": (
            int(summary.get("issue_count") or 0) == len(issues)
        ),
        "accepted_candidates_are_google_places": (
            not accepted_candidates
            or list(source_system_counts.keys()) == ["google_places"]
        ),
        "accepted_candidates_have_no_duplicate_source_record_id": (
            len(duplicate_by_source_record_id) == 0
        ),
        "accepted_candidates_have_coordinates": (
            accepted_profile.get("missing_fields", {}).get("missing_coordinates_count", 0) == 0
        ),
        "accepted_candidates_have_category": (
            accepted_profile.get("missing_fields", {}).get("missing_category_count", 0) == 0
        ),
    }


def maybe_save_artifact(result: dict[str, Any], staging_dir: Path) -> Path:
    output_dir = settings.data_artifacts_path / "google_places_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{staging_dir.name}_qa.json"
    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_file


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    staging_dir = resolve_staging_dir(args)

    summary = load_json_file(staging_dir / "summary.json")
    accepted_candidates = load_json_file(staging_dir / "accepted_candidates.json")
    needs_review_candidates = load_json_file(staging_dir / "needs_review_candidates.json")
    rejected_candidates = load_json_file(staging_dir / "rejected_candidates.json")
    issues = load_json_file(staging_dir / "issues.json")

    accepted_profile = profile_candidates(accepted_candidates, args.top_n)

    result = {
        "staging_dir": str(staging_dir),
        "summary": summary,
        "accepted_profile": accepted_profile,
        "needs_review_profile": profile_review_candidates(
            needs_review_candidates,
            args.top_n,
        ),
        "rejected_profile": profile_review_candidates(
            rejected_candidates,
            args.top_n,
        ),
        "issue_count": len(issues),
        "issues_preview": issues[: args.top_n],
    }

    result["checks"] = validate_staging_consistency(
        summary=summary,
        accepted_candidates=accepted_candidates,
        needs_review_candidates=needs_review_candidates,
        rejected_candidates=rejected_candidates,
        issues=issues,
        accepted_profile=accepted_profile,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in result["checks"].items()
        if not passed
    ]

    if args.save_artifact:
        artifact_path = maybe_save_artifact(result, staging_dir)
        logger.info("QA Google Places guardado en: %s", artifact_path)

    if failed_checks:
        logger.warning(
            "QA de staging Google Places completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("QA de staging Google Places completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())