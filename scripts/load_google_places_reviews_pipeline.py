from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.connectors.google_places import GooglePlacesConnector
from src.db.database import engine
from src.normalization.google_places_reviews_importer import (
    GooglePlacesReviewsImporter,
)
from src.normalization.google_places_reviews_transformer import (
    GooglePlacesReviewsTransformer,
)
from src.normalization.review_candidate import NormalizedReviewCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta el flujo completo de Google Places Reviews: "
            "Place Details → raw → staging → check staging → import → check import."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)

    source_group.add_argument(
        "--place-source-ref-id",
        type=str,
        default=None,
        help="ID de hidden_gems.place_source_ref de Google Places.",
    )

    source_group.add_argument(
        "--limit-first",
        action="store_true",
        help="Selecciona automáticamente el primer place_source_ref actual de Google Places.",
    )

    parser.add_argument(
        "--query-name",
        type=str,
        default=None,
        help="Nombre lógico de la consulta. Si no se indica, se genera automáticamente.",
    )

    parser.add_argument(
        "--language-code",
        type=str,
        default="es",
        help="Idioma de respuesta. Por defecto: es.",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        default="ES",
        help="Región de respuesta. Por defecto: ES.",
    )

    parser.add_argument(
        "--include-rating-summary",
        action="store_true",
        help=(
            "Incluye rating y userRatingCount en FieldMask. "
            "No es necesario para importar reviews; usar solo en pruebas controladas."
        ),
    )

    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Ejecuta hasta staging/check staging, pero no importa en hidden_gems.review.",
    )

    parser.add_argument(
        "--require-reviews",
        action="store_true",
        help=(
            "Si se activa, el pipeline falla cuando Google no devuelve reviews aceptadas. "
            "Por defecto se permite review_count=0."
        ),
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

    return parser


def fetch_place_source_ref(place_source_ref_id: str | None) -> dict[str, Any]:
    extra_filter = ""
    params: dict[str, Any] = {
        "source_code": "google_places",
    }

    if place_source_ref_id:
        extra_filter = "AND psr.place_source_ref_id = :place_source_ref_id"
        params["place_source_ref_id"] = place_source_ref_id

    query = text(
        f"""
        SELECT
            psr.place_source_ref_id::text AS place_source_ref_id,
            psr.place_id::text AS place_id,
            psr.source_record_id AS google_place_id,
            psr.source_name_raw,
            p.display_name AS place_display_name,
            n.official_name AS neighborhood_name,
            d.official_name AS district_name
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
        WHERE ss.source_code = :source_code
          AND psr.is_current = TRUE
          AND psr.is_deleted_in_source = FALSE
          AND psr.source_record_id IS NOT NULL
          {extra_filter}
        ORDER BY psr.updated_at DESC NULLS LAST, psr.created_at DESC
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, params).mappings().first()

    if row is None:
        if place_source_ref_id:
            raise ValueError(
                f"No se encontró place_source_ref actual de Google Places con id={place_source_ref_id}"
            )
        raise ValueError("No se encontró ningún place_source_ref actual de Google Places.")

    return dict(row)


def build_field_mask(include_rating_summary: bool) -> list[str]:
    fields = [
        "id",
        "displayName",
        "reviews",
    ]

    if include_rating_summary:
        fields.extend(
            [
                "rating",
                "userRatingCount",
            ]
        )

    return fields


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def serialize_candidate(candidate: NormalizedReviewCandidate) -> dict[str, Any]:
    return candidate.model_dump(mode="json")


def serialize_issue(issue: Any) -> dict[str, Any]:
    return {
        "issue_code": issue.issue_code,
        "severity": issue.severity,
        "message": issue.message,
        "review_index": issue.review_index,
        "source_entity_type": issue.source_entity_type,
        "source_record_id": issue.source_record_id,
        "field_name": issue.field_name,
        "received_value": issue.received_value,
    }


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = data

    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)

    return current


def profile_staged_reviews(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    source_review_ids = [
        get_nested(review, ("provenance", "source_record_id"))
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
        "language_counts": dict(Counter(str(language) for language in languages)),
        "rating_counts": dict(Counter(str(rating) for rating in ratings)),
        "unique_source_review_id_count": len(
            {value for value in source_review_ids if value}
        ),
        "duplicate_source_review_ids": duplicate_source_review_ids,
        "missing_text_count": missing_text_count,
        "missing_place_link_count": missing_place_link_count,
        "invalid_source_review_id_count": invalid_source_review_id_count,
        "invalid_payload_hash_count": invalid_payload_hash_count,
        "operational_count": operational_count,
        "training_eligible_count": training_eligible_count,
    }


def validate_staging(
    *,
    summary: dict[str, Any],
    accepted_reviews: list[dict[str, Any]],
    rejected_reviews: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    raw_google_place_id: str,
    place_context: dict[str, Any],
    require_reviews: bool,
) -> dict[str, bool]:
    accepted_profile = profile_staged_reviews(accepted_reviews)

    total_reviews = int(summary.get("total_reviews") or 0)
    accepted_count = int(summary.get("accepted_count") or 0)
    rejected_count = int(summary.get("rejected_count") or 0)
    skipped_count = int(summary.get("skipped_count") or 0)
    issue_count = int(summary.get("issue_count") or 0)

    payload_metadata = summary.get("payload_metadata") or {}

    checks = {
        "staging_total_matches_parts": (
            total_reviews == accepted_count + rejected_count + skipped_count
        ),
        "accepted_count_matches_file": accepted_count == len(accepted_reviews),
        "rejected_count_matches_file": rejected_count == len(rejected_reviews),
        "issue_count_matches_file": issue_count == len(issues),
        "has_google_place_id": is_non_empty_string(payload_metadata.get("google_place_id")),
        "google_place_id_matches_request": (
            payload_metadata.get("google_place_id") == raw_google_place_id
        ),
        "place_id_matches_context": (
            payload_metadata.get("place_id") == place_context["place_id"]
        ),
        "place_source_ref_id_matches_context": (
            payload_metadata.get("place_source_ref_id")
            == place_context["place_source_ref_id"]
        ),
        "has_accepted_reviews_or_allowed_empty": (
            len(accepted_reviews) > 0 if require_reviews else True
        ),
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

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check interno de staging de Google Places Reviews fallido: {failed_checks}")

    return checks


def fetch_one(query: str, params: dict[str, Any]) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(text(query), params).mappings().first()

    return dict(row) if row else None


def fetch_all(query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(text(query), params).mappings().all()

    return [dict(row) for row in rows]


def fetch_scalar(query: str, params: dict[str, Any]) -> int:
    with engine.connect() as connection:
        value = connection.execute(text(query), params).scalar_one()

    return int(value)


def build_import_check(
    *,
    source_run_id: str,
    raw_asset_id: str,
    expected_imported_count: int,
) -> dict[str, Any]:
    params = {
        "source_code": "google_places",
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
    }

    counts = fetch_one(
        """
        SELECT
            COUNT(*) AS total_reviews,
            COUNT(*) FILTER (WHERE r.place_id IS NOT NULL) AS linked_to_place_count,
            COUNT(*) FILTER (WHERE r.place_source_ref_id IS NOT NULL) AS linked_to_source_ref_count,
            COUNT(*) FILTER (
                WHERE r.review_text_raw IS NOT NULL
                  AND BTRIM(r.review_text_raw) <> ''
            ) AS with_text_count,
            COUNT(*) FILTER (WHERE r.rating_value IS NOT NULL) AS with_rating_count,
            COUNT(*) FILTER (WHERE r.review_language IS NOT NULL) AS with_language_count,
            COUNT(*) FILTER (WHERE r.source_payload_hash IS NOT NULL) AS with_payload_hash_count,
            COUNT(*) FILTER (WHERE r.source_place_record_id IS NOT NULL) AS with_source_place_record_id_count,
            COUNT(*) FILTER (WHERE r.source_review_id IS NOT NULL) AS with_source_review_id_count,
            COUNT(*) FILTER (WHERE r.is_operational_review = TRUE) AS operational_review_count,
            COUNT(*) FILTER (WHERE r.is_training_eligible = TRUE) AS training_eligible_count,
            COUNT(*) FILTER (WHERE r.is_active = TRUE) AS active_count,
            COUNT(*) FILTER (WHERE r.is_deleted_in_source = TRUE) AS deleted_in_source_count
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        """,
        params,
    ) or {}

    language_counts = fetch_all(
        """
        SELECT
            COALESCE(r.review_language, 'unknown') AS review_language,
            COUNT(*) AS total
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        GROUP BY COALESCE(r.review_language, 'unknown')
        ORDER BY total DESC, review_language
        """,
        params,
    )

    rating_counts = fetch_all(
        """
        SELECT
            r.rating_value::text AS rating_value,
            COUNT(*) AS total
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        GROUP BY r.rating_value
        ORDER BY r.rating_value DESC NULLS LAST
        """,
        params,
    )

    neighborhood_counts = fetch_all(
        """
        SELECT
            COALESCE(d.official_name, 'unknown') AS district_name,
            COALESCE(n.official_name, 'unknown') AS neighborhood_name,
            COUNT(*) AS total
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        JOIN hidden_gems.place p
            ON p.place_id = r.place_id
        LEFT JOIN hidden_gems.place_neighborhood_assignment pna
            ON pna.place_id = p.place_id
           AND pna.is_current = TRUE
        LEFT JOIN hidden_gems.neighborhood n
            ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN hidden_gems.district d
            ON d.district_id = pna.district_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        GROUP BY COALESCE(d.official_name, 'unknown'), COALESCE(n.official_name, 'unknown')
        ORDER BY total DESC, district_name, neighborhood_name
        """,
        params,
    )

    invalid_place_source_ref_count = fetch_scalar(
        """
        SELECT COUNT(*)
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        LEFT JOIN hidden_gems.place_source_ref psr
            ON psr.place_source_ref_id = r.place_source_ref_id
           AND psr.place_id = r.place_id
           AND psr.source_record_id = r.source_place_record_id
           AND psr.is_current = TRUE
           AND psr.is_deleted_in_source = FALSE
        LEFT JOIN hidden_gems.source_system ref_ss
            ON ref_ss.source_system_id = psr.source_system_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
          AND (
                psr.place_source_ref_id IS NULL
                OR ref_ss.source_code <> :source_code
          )
        """,
        params,
    )

    missing_current_neighborhood_count = fetch_scalar(
        """
        SELECT COUNT(*)
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        LEFT JOIN hidden_gems.place_neighborhood_assignment pna
            ON pna.place_id = r.place_id
           AND pna.is_current = TRUE
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
          AND pna.place_neighborhood_assignment_id IS NULL
        """,
        params,
    )

    duplicate_reviews = fetch_all(
        """
        SELECT
            r.source_place_record_id,
            r.source_review_id,
            COUNT(*) AS total
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        GROUP BY r.source_place_record_id, r.source_review_id
        HAVING COUNT(*) > 1
        ORDER BY total DESC
        """,
        params,
    )

    validation_issue_count = fetch_scalar(
        """
        SELECT COUNT(*)
        FROM hidden_gems.validation_issue vi
        WHERE vi.source_run_id = :source_run_id
          AND vi.raw_asset_id = :raw_asset_id
        """,
        params,
    )

    sample_reviews = fetch_all(
        """
        SELECT
            r.review_id::text AS review_id,
            r.place_id::text AS place_id,
            r.place_source_ref_id::text AS place_source_ref_id,
            r.source_place_record_id,
            r.source_review_id,
            p.display_name AS place_display_name,
            COALESCE(n.official_name, 'unknown') AS neighborhood_name,
            COALESCE(d.official_name, 'unknown') AS district_name,
            r.author_name_raw,
            r.rating_value,
            r.review_language,
            r.review_created_at,
            LEFT(r.review_text_raw, 300) AS review_text_sample,
            r.is_operational_review,
            r.is_training_eligible
        FROM hidden_gems.review r
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = r.source_system_id
        JOIN hidden_gems.place p
            ON p.place_id = r.place_id
        LEFT JOIN hidden_gems.place_neighborhood_assignment pna
            ON pna.place_id = p.place_id
           AND pna.is_current = TRUE
        LEFT JOIN hidden_gems.neighborhood n
            ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN hidden_gems.district d
            ON d.district_id = pna.district_id
        WHERE ss.source_code = :source_code
          AND r.source_run_id = :source_run_id
          AND r.raw_asset_id = :raw_asset_id
        ORDER BY r.review_created_at DESC NULLS LAST, r.created_at DESC
        LIMIT 10
        """,
        params,
    )

    total_reviews = int(counts.get("total_reviews") or 0)

    checks = {
        "imported_count_matches_expected": total_reviews == expected_imported_count,
        "all_reviews_linked_to_place": (
            int(counts.get("linked_to_place_count") or 0) == total_reviews
        ),
        "all_reviews_linked_to_source_ref": (
            int(counts.get("linked_to_source_ref_count") or 0) == total_reviews
        ),
        "all_reviews_have_text": (
            int(counts.get("with_text_count") or 0) == total_reviews
        ),
        "all_reviews_have_rating": (
            int(counts.get("with_rating_count") or 0) == total_reviews
        ),
        "all_reviews_have_language": (
            int(counts.get("with_language_count") or 0) == total_reviews
        ),
        "all_reviews_have_source_review_id": (
            int(counts.get("with_source_review_id_count") or 0) == total_reviews
        ),
        "all_reviews_have_source_place_record_id": (
            int(counts.get("with_source_place_record_id_count") or 0) == total_reviews
        ),
        "all_reviews_have_payload_hash": (
            int(counts.get("with_payload_hash_count") or 0) == total_reviews
        ),
        "all_reviews_are_operational": (
            int(counts.get("operational_review_count") or 0) == total_reviews
        ),
        "all_reviews_are_training_eligible": (
            int(counts.get("training_eligible_count") or 0) == total_reviews
        ),
        "all_reviews_are_active": (
            int(counts.get("active_count") or 0) == total_reviews
        ),
        "no_reviews_deleted_in_source": (
            int(counts.get("deleted_in_source_count") or 0) == 0
        ),
        "valid_place_source_ref_links": invalid_place_source_ref_count == 0,
        "all_reviews_have_current_neighborhood": missing_current_neighborhood_count == 0,
        "no_duplicate_reviews_in_scope": len(duplicate_reviews) == 0,
        "no_validation_issues_in_scope": validation_issue_count == 0,
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check interno de import Google Places Reviews fallido: {failed_checks}")

    return {
        "counts": counts,
        "language_counts": language_counts,
        "rating_counts": rating_counts,
        "neighborhood_counts": neighborhood_counts,
        "invalid_place_source_ref_count": invalid_place_source_ref_count,
        "missing_current_neighborhood_count": missing_current_neighborhood_count,
        "duplicate_reviews": duplicate_reviews,
        "validation_issue_count": validation_issue_count,
        "sample_reviews": sample_reviews,
        "checks": checks,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    place_context = fetch_place_source_ref(args.place_source_ref_id)
    google_place_id = str(place_context["google_place_id"]).removeprefix("places/").strip()

    query_name = args.query_name
    if not query_name:
        query_name = f"google_places_reviews_{google_place_id[:24]}"

    logger.info(
        "Iniciando flujo completo Google Places Reviews | query_name=%s | google_place_id=%s | place_source_ref_id=%s",
        query_name,
        google_place_id,
        place_context["place_source_ref_id"],
    )

    connector = GooglePlacesConnector()

    connector_result = connector.run_place_details(
        google_place_id=google_place_id,
        query_name=query_name,
        language_code=args.language_code,
        region_code=args.region_code,
        field_mask=build_field_mask(args.include_rating_summary),
        trigger_type=args.trigger_type,
        run_type=args.run_type,
        place_id=place_context["place_id"],
        place_source_ref_id=place_context["place_source_ref_id"],
    )

    run_context = connector_result["run_context"]
    raw_asset = connector_result["raw_asset"]
    payload = connector_result["payload"]

    source_run_id = run_context.source_run_id
    raw_asset_id = raw_asset["raw_asset_id"]

    staging_dir = settings.data_staging_path / "google_places_reviews" / raw_asset_id
    import_dir = staging_dir / "import"

    transformer = GooglePlacesReviewsTransformer()
    transform_result = transformer.transform_payload(
        payload,
        source_run_id=source_run_id,
        raw_asset_id=raw_asset_id,
        place_id=place_context["place_id"],
        place_source_ref_id=place_context["place_source_ref_id"],
    )

    accepted_reviews_candidates = [
        candidate
        for candidate in transform_result.candidates
        if candidate.quality.candidate_status == "accepted"
    ]

    rejected_reviews_candidates = [
        candidate
        for candidate in transform_result.candidates
        if candidate.quality.candidate_status == "rejected"
    ]

    accepted_reviews = [
        serialize_candidate(candidate)
        for candidate in accepted_reviews_candidates
    ]
    rejected_reviews = [
        serialize_candidate(candidate)
        for candidate in rejected_reviews_candidates
    ]
    issues = [
        serialize_issue(issue)
        for issue in transform_result.issues
    ]

    staging_summary = {
        "raw_asset_metadata": {
            "raw_asset_id": raw_asset_id,
            "source_run_id": source_run_id,
            "storage_path": raw_asset["storage_path"],
            "asset_name": raw_asset.get("asset_name"),
            "query_name": raw_asset.get("query_name"),
            "source_code": "google_places",
        },
        "payload_metadata": transform_result.payload_metadata,
        "total_reviews": transform_result.total_reviews,
        "accepted_count": transform_result.accepted_count,
        "rejected_count": transform_result.rejected_count,
        "skipped_count": transform_result.skipped_count,
        "issue_count": len(transform_result.issues),
        "output_dir": str(staging_dir),
    }

    write_json_file(staging_dir / "summary.json", staging_summary)
    write_json_file(staging_dir / "accepted_reviews.json", accepted_reviews)
    write_json_file(staging_dir / "rejected_reviews.json", rejected_reviews)
    write_json_file(staging_dir / "issues.json", issues)

    staging_checks = validate_staging(
        summary=staging_summary,
        accepted_reviews=accepted_reviews,
        rejected_reviews=rejected_reviews,
        issues=issues,
        raw_google_place_id=google_place_id,
        place_context=place_context,
        require_reviews=args.require_reviews,
    )

    import_summary: dict[str, Any] | None = None
    import_check: dict[str, Any] | None = None

    if not args.skip_import:
        importer = GooglePlacesReviewsImporter()
        import_result = importer.import_reviews(
            reviews=accepted_reviews,
            source_run_id=source_run_id,
            raw_asset_id=raw_asset_id,
        )

        import_summary = {
            "source_run_id": source_run_id,
            "raw_asset_id": raw_asset_id,
            "staging_dir": str(staging_dir),
            "input_summary": {
                "total_reviews": staging_summary["total_reviews"],
                "accepted_count": staging_summary["accepted_count"],
                "rejected_count": staging_summary["rejected_count"],
                "skipped_count": staging_summary["skipped_count"],
                "issue_count": staging_summary["issue_count"],
            },
            "import_result": {
                "input_count": import_result.input_count,
                "imported_count": import_result.imported_count,
                "inserted_count": import_result.inserted_count,
                "updated_count": import_result.updated_count,
                "skipped_count": import_result.skipped_count,
                "validation_issue_count": import_result.validation_issue_count,
            },
            "output_dir": str(import_dir),
        }

        write_json_file(import_dir / "import_summary.json", import_summary)

        import_check = build_import_check(
            source_run_id=source_run_id,
            raw_asset_id=raw_asset_id,
            expected_imported_count=import_result.imported_count,
        )

    final_output = {
        "source_code": "google_places",
        "pipeline_type": "google_places_reviews",
        "run_code": run_context.run_code,
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
        "storage_path": raw_asset["storage_path"],
        "query": {
            "query_name": query_name,
            "google_place_id": google_place_id,
            "language_code": args.language_code,
            "region_code": args.region_code,
            "field_mask": build_field_mask(args.include_rating_summary),
        },
        "place_context": place_context,
        "raw_summary": connector_result["summary"],
        "warnings": connector_result["warnings"],
        "staging_summary": {
            "total_reviews": transform_result.total_reviews,
            "accepted_count": transform_result.accepted_count,
            "rejected_count": transform_result.rejected_count,
            "skipped_count": transform_result.skipped_count,
            "issue_count": len(transform_result.issues),
            "language_counts": profile_staged_reviews(accepted_reviews)["language_counts"],
            "rating_counts": profile_staged_reviews(accepted_reviews)["rating_counts"],
        },
        "import_summary": (
            import_summary["import_result"]
            if import_summary
            else None
        ),
        "checks": {
            "staging": staging_checks,
            "import": import_check["checks"] if import_check else None,
        },
        "import_check": import_check,
        "paths": {
            "staging_dir": str(staging_dir),
            "import_dir": str(import_dir) if not args.skip_import else None,
        },
        "skip_import": args.skip_import,
    }

    write_json_file(import_dir / "pipeline_summary.json", final_output)

    artifact_path = (
        settings.data_artifacts_path
        / "google_places_reviews_pipeline"
        / f"{raw_asset_id}_reviews_pipeline_summary.json"
    )
    write_json_file(artifact_path, final_output)

    console_output = {
        **final_output,
        "artifact_path": str(artifact_path),
    }

    print(json.dumps(console_output, ensure_ascii=False, indent=2, default=str))

    logger.info(
        "Flujo completo Google Places Reviews finalizado correctamente | raw_asset_id=%s | source_run_id=%s",
        raw_asset_id,
        source_run_id,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())