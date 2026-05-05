from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba la calidad del staging de Google Places Reviews."
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        required=True,
        help="raw_asset_id transformado por transform_google_places_reviews.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el resultado del check en data/artifacts/google_places_reviews_staging_qa.",
    )

    return parser


def fetch_raw_asset_metadata(raw_asset_id: str) -> dict[str, Any]:
    query = text(
        """
        SELECT
            ra.raw_asset_id::text AS raw_asset_id,
            ra.source_run_id::text AS source_run_id,
            ra.storage_path,
            ra.asset_name,
            ra.query_name,
            sr.request_summary,
            ss.source_code
        FROM hidden_gems.raw_asset ra
        JOIN hidden_gems.source_run sr
            ON sr.source_run_id = ra.source_run_id
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = ra.source_system_id
        WHERE ra.raw_asset_id = :raw_asset_id
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"raw_asset_id": raw_asset_id},
        ).mappings().first()

    if row is None:
        raise ValueError(f"No existe raw_asset_id={raw_asset_id}")

    metadata = dict(row)

    if metadata["source_code"] != "google_places":
        raise ValueError(
            f"El raw_asset no pertenece a google_places: {metadata['source_code']}"
        )

    request_summary = metadata.get("request_summary") or {}
    if not isinstance(request_summary, dict):
        request_summary = {}

    metadata["request_summary"] = request_summary

    return metadata


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def get_staging_dir(raw_asset_id: str) -> Path:
    return settings.data_staging_path / "google_places_reviews" / raw_asset_id


def get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def profile_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    source_review_ids = [
        get_nested(review, ("provenance", "source_record_id"))
        for review in reviews
    ]

    source_place_record_ids = [
        get_nested(review, ("provenance", "source_place_record_id"))
        for review in reviews
    ]

    languages = [
        get_nested(review, ("text", "review_language"))
        for review in reviews
        if get_nested(review, ("text", "review_language"))
    ]

    ratings = [
        get_nested(review, ("rating", "rating_value"))
        for review in reviews
        if get_nested(review, ("rating", "rating_value")) is not None
    ]

    status_counts = Counter(
        get_nested(review, ("quality", "candidate_status"))
        for review in reviews
    )

    language_counts = Counter(str(language) for language in languages)
    rating_counts = Counter(str(rating) for rating in ratings)

    duplicate_source_review_ids = [
        {
            "source_review_id": source_review_id,
            "count": count,
        }
        for source_review_id, count in Counter(source_review_ids).items()
        if source_review_id and count > 1
    ]

    missing_text_count = sum(
        1
        for review in reviews
        if not is_non_empty_string(get_nested(review, ("text", "review_text_raw")))
    )

    missing_rating_count = sum(
        1
        for review in reviews
        if get_nested(review, ("rating", "rating_value")) is None
    )

    missing_author_count = sum(
        1
        for review in reviews
        if not is_non_empty_string(get_nested(review, ("author", "author_name_raw")))
    )

    missing_publish_time_count = sum(
        1
        for review in reviews
        if not is_non_empty_string(get_nested(review, ("time", "review_created_at")))
    )

    missing_place_link_count = sum(
        1
        for review in reviews
        if not (
            is_non_empty_string(get_nested(review, ("provenance", "place_id")))
            and is_non_empty_string(get_nested(review, ("provenance", "place_source_ref_id")))
            and is_non_empty_string(get_nested(review, ("provenance", "source_place_record_id")))
        )
    )

    invalid_source_review_id_count = sum(
        1
        for source_review_id in source_review_ids
        if not is_sha256(source_review_id)
    )

    invalid_payload_hash_count = sum(
        1
        for review in reviews
        if not is_sha256(get_nested(review, ("provenance", "source_payload_hash")))
    )

    operational_count = sum(
        1
        for review in reviews
        if review.get("is_operational_review") is True
    )

    training_eligible_count = sum(
        1
        for review in reviews
        if review.get("is_training_eligible") is True
    )

    return {
        "review_count": len(reviews),
        "status_counts": dict(status_counts),
        "language_counts": dict(language_counts),
        "rating_counts": dict(rating_counts),
        "unique_source_review_id_count": len(
            {value for value in source_review_ids if value}
        ),
        "unique_source_place_record_id_count": len(
            {value for value in source_place_record_ids if value}
        ),
        "duplicate_source_review_ids": duplicate_source_review_ids,
        "missing_text_count": missing_text_count,
        "missing_rating_count": missing_rating_count,
        "missing_author_count": missing_author_count,
        "missing_publish_time_count": missing_publish_time_count,
        "missing_place_link_count": missing_place_link_count,
        "invalid_source_review_id_count": invalid_source_review_id_count,
        "invalid_payload_hash_count": invalid_payload_hash_count,
        "operational_count": operational_count,
        "training_eligible_count": training_eligible_count,
    }


def build_checks(
    *,
    raw_asset_metadata: dict[str, Any],
    summary: dict[str, Any],
    accepted_reviews: list[dict[str, Any]],
    rejected_reviews: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    accepted_profile: dict[str, Any],
) -> dict[str, bool]:
    payload_metadata = summary.get("payload_metadata") or {}
    request_summary = raw_asset_metadata.get("request_summary") or {}

    total_reviews = int(summary.get("total_reviews") or 0)
    accepted_count = int(summary.get("accepted_count") or 0)
    rejected_count = int(summary.get("rejected_count") or 0)
    skipped_count = int(summary.get("skipped_count") or 0)
    issue_count = int(summary.get("issue_count") or 0)

    google_place_id_summary = payload_metadata.get("google_place_id")
    google_place_id_request = request_summary.get("google_place_id")

    place_id_summary = payload_metadata.get("place_id")
    place_id_request = request_summary.get("place_id")

    place_source_ref_summary = payload_metadata.get("place_source_ref_id")
    place_source_ref_request = request_summary.get("place_source_ref_id")

    return {
        "staging_total_matches_parts": (
            total_reviews == accepted_count + rejected_count + skipped_count
        ),
        "accepted_count_matches_file": accepted_count == len(accepted_reviews),
        "rejected_count_matches_file": rejected_count == len(rejected_reviews),
        "issue_count_matches_file": issue_count == len(issues),
        "has_google_place_id": is_non_empty_string(google_place_id_summary),
        "google_place_id_matches_request": (
            google_place_id_summary == google_place_id_request
        ),
        "place_id_matches_request": place_id_summary == place_id_request,
        "place_source_ref_id_matches_request": (
            place_source_ref_summary == place_source_ref_request
        ),
        "has_accepted_reviews": len(accepted_reviews) > 0,
        "accepted_reviews_have_unique_source_review_id": (
            accepted_profile["unique_source_review_id_count"] == len(accepted_reviews)
        ),
        "accepted_reviews_have_no_duplicate_source_review_id": (
            len(accepted_profile["duplicate_source_review_ids"]) == 0
        ),
        "accepted_reviews_have_valid_source_review_id": (
            accepted_profile["invalid_source_review_id_count"] == 0
        ),
        "accepted_reviews_have_valid_payload_hash": (
            accepted_profile["invalid_payload_hash_count"] == 0
        ),
        "accepted_reviews_have_text": (
            accepted_profile["missing_text_count"] == 0
        ),
        "accepted_reviews_have_place_link": (
            accepted_profile["missing_place_link_count"] == 0
        ),
        "accepted_reviews_are_operational": (
            accepted_profile["operational_count"] == len(accepted_reviews)
        ),
        "accepted_reviews_are_training_eligible": (
            accepted_profile["training_eligible_count"] == len(accepted_reviews)
        ),
    }


def save_artifact(raw_asset_id: str, output: dict[str, Any]) -> Path:
    output_dir = settings.data_artifacts_path / "google_places_reviews_staging_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{raw_asset_id}_reviews_staging_check.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_asset_metadata = fetch_raw_asset_metadata(args.raw_asset_id)
    staging_dir = get_staging_dir(args.raw_asset_id)

    summary = load_json(staging_dir / "summary.json")
    accepted_reviews = load_json(staging_dir / "accepted_reviews.json")
    rejected_reviews = load_json(staging_dir / "rejected_reviews.json")
    issues = load_json(staging_dir / "issues.json")

    if not isinstance(summary, dict):
        raise ValueError("summary.json no contiene un objeto válido.")

    if not isinstance(accepted_reviews, list):
        raise ValueError("accepted_reviews.json no contiene una lista válida.")

    if not isinstance(rejected_reviews, list):
        raise ValueError("rejected_reviews.json no contiene una lista válida.")

    if not isinstance(issues, list):
        raise ValueError("issues.json no contiene una lista válida.")

    accepted_profile = profile_reviews(accepted_reviews)
    rejected_profile = profile_reviews(rejected_reviews)

    checks = build_checks(
        raw_asset_metadata=raw_asset_metadata,
        summary=summary,
        accepted_reviews=accepted_reviews,
        rejected_reviews=rejected_reviews,
        issues=issues,
        accepted_profile=accepted_profile,
    )

    output = {
        "raw_asset_id": args.raw_asset_id,
        "staging_dir": str(staging_dir),
        "raw_asset_metadata": raw_asset_metadata,
        "summary": summary,
        "accepted_profile": accepted_profile,
        "rejected_profile": rejected_profile,
        "issue_count": len(issues),
        "issues_sample": issues[:20],
        "checks": checks,
    }

    if args.save_artifact:
        artifact_path = save_artifact(args.raw_asset_id, output)
        output["artifact_path"] = str(artifact_path)

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Check de staging Google Places Reviews completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check de staging Google Places Reviews completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())