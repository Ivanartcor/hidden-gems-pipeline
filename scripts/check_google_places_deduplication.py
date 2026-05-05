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
        description="Comprueba la salida de deduplicación de Google Places."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--dedup-dir",
        type=str,
        help="Ruta directa al directorio deduplication de Google Places.",
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
        help="Número máximo de elementos a mostrar en rankings y previews.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el resultado del check en data/artifacts/google_places_dedup_qa.",
    )

    return parser


def resolve_dedup_dir(args: argparse.Namespace) -> Path:
    if args.dedup_dir:
        dedup_dir = Path(args.dedup_dir)
    else:
        dedup_dir = (
            settings.data_staging_path
            / "google_places"
            / args.raw_asset_id
            / "deduplication"
        )

    if not dedup_dir.exists():
        raise FileNotFoundError(f"No existe el directorio deduplication: {dedup_dir}")

    if not dedup_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {dedup_dir}")

    return dedup_dir


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


def profile_unique_candidates(
    unique_candidates: list[dict[str, Any]],
    top_n: int,
) -> dict[str, Any]:
    source_system_counter: Counter[str] = Counter()
    candidate_status_counter: Counter[str] = Counter()
    business_status_counter: Counter[str] = Counter()
    primary_category_counter: Counter[str] = Counter()
    google_type_counter: Counter[str] = Counter()

    missing_source_record_id_count = 0
    missing_name_count = 0
    missing_coordinates_count = 0
    missing_category_count = 0
    missing_address_count = 0

    source_record_id_map: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    completeness_scores: list[float] = []

    examples: list[dict[str, Any]] = []

    for candidate in unique_candidates:
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
        business_status = normalize_text(
            safe_get(candidate, "provenance", "source_status_raw")
        )
        candidate_status = normalize_text(
            safe_get(candidate, "quality", "candidate_status")
        )
        primary_category = normalize_text(
            safe_get(candidate, "classification", "source_primary_category_raw")
        )
        source_categories = safe_get(
            candidate,
            "classification",
            "source_categories_raw",
        ) or []
        completeness_score = safe_get(
            candidate,
            "quality",
            "completeness_score",
        )
        latitude = safe_get(candidate, "location", "latitude")
        longitude = safe_get(candidate, "location", "longitude")

        if source_system_code:
            source_system_counter[source_system_code] += 1

        if candidate_status:
            candidate_status_counter[candidate_status] += 1

        if business_status:
            business_status_counter[business_status] += 1

        if primary_category:
            primary_category_counter[primary_category] += 1

        for google_type in source_categories:
            clean_type = normalize_text(google_type)
            if clean_type:
                google_type_counter[clean_type] += 1

        if not source_record_id:
            missing_source_record_id_count += 1

        if not display_name:
            missing_name_count += 1

        if latitude is None or longitude is None:
            missing_coordinates_count += 1

        if not primary_category:
            missing_category_count += 1

        if not source_address_raw:
            missing_address_count += 1

        if isinstance(completeness_score, (float, int)):
            completeness_scores.append(float(completeness_score))

        if source_record_id:
            source_record_id_map[source_record_id].append(
                {
                    "display_name": display_name,
                    "normalized_name": normalized_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "candidate_status": candidate_status,
                }
            )

        if len(examples) < 5:
            examples.append(
                {
                    "source_record_id": source_record_id,
                    "display_name": display_name,
                    "normalized_name": normalized_name,
                    "source_address_raw": source_address_raw,
                    "primary_category": primary_category,
                    "latitude": latitude,
                    "longitude": longitude,
                    "business_status": business_status,
                    "candidate_status": candidate_status,
                    "completeness_score": completeness_score,
                }
            )

    duplicate_source_record_ids = []

    for source_record_id, rows in source_record_id_map.items():
        if len(rows) > 1:
            duplicate_source_record_ids.append(
                {
                    "source_record_id": source_record_id,
                    "count": len(rows),
                    "examples": rows[:5],
                }
            )

    duplicate_source_record_ids.sort(
        key=lambda row: row["count"],
        reverse=True,
    )

    avg_completeness_score = (
        round(sum(completeness_scores) / len(completeness_scores), 4)
        if completeness_scores
        else None
    )

    return {
        "count": len(unique_candidates),
        "source_system_counts": dict(source_system_counter),
        "candidate_status_counts": dict(candidate_status_counter),
        "business_status_counts": dict(business_status_counter),
        "top_primary_categories": dict(primary_category_counter.most_common(top_n)),
        "top_google_types": dict(google_type_counter.most_common(top_n)),
        "missing_fields": {
            "missing_source_record_id_count": missing_source_record_id_count,
            "missing_name_count": missing_name_count,
            "missing_coordinates_count": missing_coordinates_count,
            "missing_category_count": missing_category_count,
            "missing_address_count": missing_address_count,
        },
        "avg_completeness_score": avg_completeness_score,
        "duplicate_source_record_ids": duplicate_source_record_ids[:top_n],
        "examples": examples,
    }


def profile_duplicate_groups(
    duplicate_groups: list[dict[str, Any]],
    top_n: int,
) -> dict[str, Any]:
    group_size_counter: Counter[int] = Counter()
    hard_rule_counter: Counter[str] = Counter()
    signal_counter: Counter[str] = Counter()

    examples: list[dict[str, Any]] = []

    for group in duplicate_groups:
        member_keys = group.get("member_keys") or []
        evidences = group.get("evidences") or []

        group_size_counter[len(member_keys)] += 1

        for evidence in evidences:
            hard_rule = evidence.get("hard_rule_triggered")
            if hard_rule:
                hard_rule_counter[str(hard_rule)] += 1

            for signal in evidence.get("signals") or []:
                signal_counter[str(signal)] += 1

        if len(examples) < top_n:
            representative_candidate = group.get("representative_candidate") or {}

            examples.append(
                {
                    "group_id": group.get("group_id"),
                    "representative_key": group.get("representative_key"),
                    "representative_name": safe_get(
                        representative_candidate,
                        "names",
                        "display_name",
                    ),
                    "member_count": len(member_keys),
                    "member_keys": member_keys[:5],
                    "evidences": evidences[:5],
                }
            )

    return {
        "count": len(duplicate_groups),
        "group_size_counts": dict(group_size_counter),
        "hard_rule_counts": dict(hard_rule_counter.most_common(top_n)),
        "signal_counts": dict(signal_counter.most_common(top_n)),
        "examples": examples,
    }


def validate_dedup_consistency(
    *,
    dedup_summary: dict[str, Any],
    unique_candidates: list[dict[str, Any]],
    duplicate_groups: list[dict[str, Any]],
    pair_evidences: list[dict[str, Any]],
    unique_profile: dict[str, Any],
) -> dict[str, bool]:
    duplicate_group_member_extra_count = 0

    for group in duplicate_groups:
        member_keys = group.get("member_keys") or []
        if len(member_keys) > 1:
            duplicate_group_member_extra_count += len(member_keys) - 1

    source_system_counts = unique_profile.get("source_system_counts", {})
    missing_fields = unique_profile.get("missing_fields", {})
    duplicate_source_record_ids = unique_profile.get("duplicate_source_record_ids", [])

    return {
        "dedup_output_count_matches_unique_candidates": (
            int(dedup_summary.get("output_count") or 0) == len(unique_candidates)
        ),
        "dedup_duplicate_group_count_matches_file": (
            int(dedup_summary.get("duplicate_group_count") or 0) == len(duplicate_groups)
        ),
        "dedup_pair_evidence_count_matches_file": (
            int(dedup_summary.get("pair_evidence_count") or 0) == len(pair_evidences)
        ),
        "dedup_grouped_duplicate_count_matches_groups": (
            int(dedup_summary.get("grouped_duplicate_count") or 0)
            == duplicate_group_member_extra_count
        ),
        "unique_candidates_are_google_places": (
            not unique_candidates
            or list(source_system_counts.keys()) == ["google_places"]
        ),
        "unique_candidates_have_no_duplicate_source_record_id": (
            len(duplicate_source_record_ids) == 0
        ),
        "unique_candidates_have_source_record_id": (
            missing_fields.get("missing_source_record_id_count", 0) == 0
        ),
        "unique_candidates_have_coordinates": (
            missing_fields.get("missing_coordinates_count", 0) == 0
        ),
        "unique_candidates_have_category": (
            missing_fields.get("missing_category_count", 0) == 0
        ),
    }


def maybe_save_artifact(result: dict[str, Any], dedup_dir: Path) -> Path:
    output_dir = settings.data_artifacts_path / "google_places_dedup_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{dedup_dir.parent.name}_dedup_check.json"
    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_file


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dedup_dir = resolve_dedup_dir(args)

    dedup_summary = load_json_file(dedup_dir / "dedup_summary.json")
    unique_candidates = load_json_file(dedup_dir / "unique_candidates.json")
    duplicate_groups = load_json_file(dedup_dir / "duplicate_groups.json")
    pair_evidences = load_json_file(dedup_dir / "pair_evidences.json")

    unique_profile = profile_unique_candidates(
        unique_candidates,
        args.top_n,
    )
    duplicate_group_profile = profile_duplicate_groups(
        duplicate_groups,
        args.top_n,
    )

    result = {
        "dedup_dir": str(dedup_dir),
        "dedup_summary": dedup_summary,
        "unique_profile": unique_profile,
        "duplicate_group_profile": duplicate_group_profile,
        "pair_evidence_count": len(pair_evidences),
        "pair_evidences_preview": pair_evidences[: args.top_n],
    }

    result["checks"] = validate_dedup_consistency(
        dedup_summary=dedup_summary,
        unique_candidates=unique_candidates,
        duplicate_groups=duplicate_groups,
        pair_evidences=pair_evidences,
        unique_profile=unique_profile,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in result["checks"].items()
        if not passed
    ]

    if args.save_artifact:
        artifact_path = maybe_save_artifact(result, dedup_dir)
        logger.info("QA de deduplicación Google Places guardado en: %s", artifact_path)

    if failed_checks:
        logger.warning(
            "Check de deduplicación Google Places completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check de deduplicación Google Places completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())