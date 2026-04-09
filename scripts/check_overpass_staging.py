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
        description="QA sobre el staging generado por la transformación de Overpass."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--staging-dir",
        type=str,
        help="Ruta directa al directorio staging de Overpass.",
    )
    source_group.add_argument(
        "--raw-asset-id",
        type=str,
        help="raw_asset_id usado como carpeta staging en data/staging/osm_overpass.",
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
        help="Guarda el resultado del QA en data/artifacts/overpass_qa.",
    )

    return parser


def resolve_staging_dir(args: argparse.Namespace) -> Path:
    if args.staging_dir:
        staging_dir = Path(args.staging_dir)
    else:
        staging_dir = settings.data_staging_path / "osm_overpass" / args.raw_asset_id

    if not staging_dir.exists():
        raise FileNotFoundError(f"No existe el directorio staging: {staging_dir}")

    if not staging_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {staging_dir}")

    return staging_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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
    lat = safe_get(candidate, "location", "latitude")
    lon = safe_get(candidate, "location", "longitude")

    if lat is None or lon is None:
        return None

    return f"{round(float(lat), decimals)},{round(float(lon), decimals)}"


def profile_candidates(candidates: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    primary_category_counter: Counter[str] = Counter()
    cuisine_counter: Counter[str] = Counter()
    brand_counter: Counter[str] = Counter()

    missing_address_count = 0
    missing_phone_count = 0
    missing_website_count = 0
    missing_opening_hours_count = 0
    missing_cuisine_count = 0
    missing_brand_count = 0

    duplicate_by_normalized_name: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate_by_name_and_coord: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate_by_phone: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate_by_website: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    completeness_scores: list[float] = []

    for candidate in candidates:
        normalized_name = normalize_text(safe_get(candidate, "names", "normalized_name"))
        display_name = normalize_text(safe_get(candidate, "names", "display_name"))
        primary_category = normalize_text(
            safe_get(candidate, "classification", "source_primary_category_raw")
        )
        brand = normalize_text(safe_get(candidate, "names", "brand_raw"))
        phone = normalize_text(
            safe_get(candidate, "business", "phone_normalized")
            or safe_get(candidate, "business", "phone_raw")
        )
        website = normalize_text(safe_get(candidate, "business", "website_url"))
        address = normalize_text(safe_get(candidate, "address", "source_address_raw"))
        opening_hours = normalize_text(safe_get(candidate, "business", "opening_hours_raw"))
        cuisine_values = safe_get(candidate, "classification", "cuisine_raw") or []
        completeness_score = safe_get(candidate, "quality", "completeness_score")

        if primary_category:
            primary_category_counter[primary_category] += 1

        for cuisine_value in cuisine_values:
            clean_cuisine = normalize_text(cuisine_value)
            if clean_cuisine:
                cuisine_counter[clean_cuisine] += 1

        if brand:
            brand_counter[brand] += 1

        if not address:
            missing_address_count += 1
        if not phone:
            missing_phone_count += 1
        if not website:
            missing_website_count += 1
        if not opening_hours:
            missing_opening_hours_count += 1
        if not cuisine_values:
            missing_cuisine_count += 1
        if not brand:
            missing_brand_count += 1

        if isinstance(completeness_score, (float, int)):
            completeness_scores.append(float(completeness_score))

        if normalized_name:
            duplicate_by_normalized_name[normalized_name].append(
                {
                    "display_name": display_name,
                    "source_record_id": safe_get(candidate, "provenance", "source_record_id"),
                    "latitude": safe_get(candidate, "location", "latitude"),
                    "longitude": safe_get(candidate, "location", "longitude"),
                }
            )

        coord_key = rounded_coord_pair(candidate)
        if normalized_name and coord_key:
            composite_key = f"{normalized_name} | {coord_key}"
            duplicate_by_name_and_coord[composite_key].append(
                {
                    "display_name": display_name,
                    "source_record_id": safe_get(candidate, "provenance", "source_record_id"),
                    "coord": coord_key,
                }
            )

        if phone:
            duplicate_by_phone[phone].append(
                {
                    "display_name": display_name,
                    "source_record_id": safe_get(candidate, "provenance", "source_record_id"),
                }
            )

        if website:
            duplicate_by_website[website].append(
                {
                    "display_name": display_name,
                    "source_record_id": safe_get(candidate, "provenance", "source_record_id"),
                }
            )

    def only_real_duplicates(source_map: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        rows = []
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

    return {
        "count": len(candidates),
        "avg_completeness_score": avg_completeness_score,
        "top_primary_categories": dict(primary_category_counter.most_common(top_n)),
        "top_cuisines": dict(cuisine_counter.most_common(top_n)),
        "top_brands": dict(brand_counter.most_common(top_n)),
        "missing_fields": {
            "missing_address_count": missing_address_count,
            "missing_phone_count": missing_phone_count,
            "missing_website_count": missing_website_count,
            "missing_opening_hours_count": missing_opening_hours_count,
            "missing_cuisine_count": missing_cuisine_count,
            "missing_brand_count": missing_brand_count,
        },
        "potential_duplicates": {
            "by_normalized_name": only_real_duplicates(duplicate_by_normalized_name),
            "by_name_and_rounded_coords": only_real_duplicates(duplicate_by_name_and_coord),
            "by_phone": only_real_duplicates(duplicate_by_phone),
            "by_website": only_real_duplicates(duplicate_by_website),
        },
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
                    "source_entity_type": safe_get(candidate, "provenance", "source_entity_type"),
                    "source_record_id": safe_get(candidate, "provenance", "source_record_id"),
                    "display_name": safe_get(candidate, "names", "display_name"),
                    "normalized_name": safe_get(candidate, "names", "normalized_name"),
                    "primary_category": safe_get(
                        candidate,
                        "classification",
                        "source_primary_category_raw",
                    ),
                    "warning_messages": warnings,
                    "rejection_reasons": rejections,
                    "completeness_score": safe_get(candidate, "quality", "completeness_score"),
                }
            )

    return {
        "count": len(candidates),
        "warning_reasons": dict(warning_counter.most_common(top_n)),
        "rejection_reasons": dict(rejection_counter.most_common(top_n)),
        "examples": examples,
    }


def maybe_save_artifact(result: dict[str, Any], staging_dir: Path) -> Path:
    output_dir = settings.data_artifacts_path / "overpass_qa"
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

    result = {
        "staging_dir": str(staging_dir),
        "summary": summary,
        "accepted_profile": profile_candidates(accepted_candidates, args.top_n),
        "needs_review_profile": profile_review_candidates(needs_review_candidates, args.top_n),
        "rejected_profile": profile_review_candidates(rejected_candidates, args.top_n),
        "issue_count": len(issues),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    if args.save_artifact:
        artifact_path = maybe_save_artifact(result, staging_dir)
        logger.info("QA guardado en: %s", artifact_path)

    logger.info("QA de staging Overpass completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())