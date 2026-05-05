from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Comprueba la importación de Google Places Reviews en hidden_gems.review."
        )
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        required=True,
        help="raw_asset_id usado para importar las reviews.",
    )

    parser.add_argument(
        "--source-run-id",
        type=str,
        default=None,
        help="source_run_id opcional. Si no se indica, se obtiene desde raw_asset.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el resultado en data/artifacts/google_places_reviews_import_qa.",
    )

    return parser


def fetch_one(query: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    with engine.connect() as connection:
        row = connection.execute(text(query), params or {}).mappings().first()

    return dict(row) if row else None


def fetch_all(query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        rows = connection.execute(text(query), params or {}).mappings().all()

    return [dict(row) for row in rows]


def fetch_scalar(query: str, params: dict[str, Any] | None = None) -> int:
    with engine.connect() as connection:
        value = connection.execute(text(query), params or {}).scalar_one()

    return int(value)


def load_import_summary(raw_asset_id: str) -> dict[str, Any] | None:
    path = (
        settings.data_staging_path
        / "google_places_reviews"
        / raw_asset_id
        / "import"
        / "import_summary.json"
    )

    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        return None

    return data


def fetch_raw_asset_metadata(raw_asset_id: str) -> dict[str, Any]:
    query = """
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

    row = fetch_one(query, {"raw_asset_id": raw_asset_id})

    if row is None:
        raise ValueError(f"No existe raw_asset_id={raw_asset_id}")

    if row["source_code"] != "google_places":
        raise ValueError(
            f"El raw_asset no pertenece a google_places: {row['source_code']}"
        )

    request_summary = row.get("request_summary") or {}
    if not isinstance(request_summary, dict):
        request_summary = {}

    row["request_summary"] = request_summary
    return row


def build_params(raw_asset_id: str, source_run_id: str) -> dict[str, Any]:
    return {
        "raw_asset_id": raw_asset_id,
        "source_run_id": source_run_id,
        "source_code": "google_places",
    }


def build_review_profile(params: dict[str, Any]) -> dict[str, Any]:
    main_counts = fetch_one(
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
            COUNT(*) FILTER (WHERE r.author_name_raw IS NOT NULL) AS with_author_count,
            COUNT(*) FILTER (WHERE r.review_created_at IS NOT NULL) AS with_review_created_at_count,
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

    return {
        "counts": main_counts,
        "language_counts": language_counts,
        "rating_counts": rating_counts,
        "neighborhood_counts": neighborhood_counts,
    }


def build_link_integrity_profile(params: dict[str, Any]) -> dict[str, Any]:
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

    return {
        "invalid_place_source_ref_count": invalid_place_source_ref_count,
        "missing_current_neighborhood_count": missing_current_neighborhood_count,
        "duplicate_reviews": duplicate_reviews,
        "duplicate_review_count": len(duplicate_reviews),
    }


def build_validation_issue_profile(params: dict[str, Any]) -> dict[str, Any]:
    total = fetch_scalar(
        """
        SELECT COUNT(*)
        FROM hidden_gems.validation_issue vi
        WHERE vi.source_run_id = :source_run_id
          AND vi.raw_asset_id = :raw_asset_id
        """,
        params,
    )

    by_severity = fetch_all(
        """
        SELECT
            vi.severity::text AS severity,
            COUNT(*) AS total
        FROM hidden_gems.validation_issue vi
        WHERE vi.source_run_id = :source_run_id
          AND vi.raw_asset_id = :raw_asset_id
        GROUP BY vi.severity
        ORDER BY vi.severity
        """,
        params,
    )

    top_issue_codes = fetch_all(
        """
        SELECT
            vi.issue_code,
            COUNT(*) AS total
        FROM hidden_gems.validation_issue vi
        WHERE vi.source_run_id = :source_run_id
          AND vi.raw_asset_id = :raw_asset_id
        GROUP BY vi.issue_code
        ORDER BY total DESC, vi.issue_code
        LIMIT 20
        """,
        params,
    )

    return {
        "count": total,
        "by_severity": by_severity,
        "top_issue_codes": top_issue_codes,
    }


def fetch_sample_reviews(params: dict[str, Any]) -> list[dict[str, Any]]:
    return fetch_all(
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


def build_checks(
    *,
    import_summary: dict[str, Any] | None,
    review_profile: dict[str, Any],
    link_integrity_profile: dict[str, Any],
    validation_issue_profile: dict[str, Any],
) -> dict[str, bool]:
    counts = review_profile["counts"]

    total_reviews = int(counts.get("total_reviews") or 0)

    imported_expected = None
    if import_summary:
        imported_expected = (
            (import_summary.get("import_result") or {}).get("imported_count")
        )

    checks = {
        "has_imported_reviews": total_reviews > 0,
        "imported_count_matches_import_summary": (
            True
            if imported_expected is None
            else total_reviews == int(imported_expected or 0)
        ),
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
        "valid_place_source_ref_links": (
            int(link_integrity_profile["invalid_place_source_ref_count"]) == 0
        ),
        "all_reviews_have_current_neighborhood": (
            int(link_integrity_profile["missing_current_neighborhood_count"]) == 0
        ),
        "no_duplicate_reviews_in_scope": (
            int(link_integrity_profile["duplicate_review_count"]) == 0
        ),
        "no_validation_issues_in_scope": (
            int(validation_issue_profile["count"]) == 0
        ),
    }

    return checks


def save_artifact(raw_asset_id: str, output: dict[str, Any]) -> Path:
    output_dir = settings.data_artifacts_path / "google_places_reviews_import_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{raw_asset_id}_reviews_import_check.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_asset_metadata = fetch_raw_asset_metadata(args.raw_asset_id)
    source_run_id = args.source_run_id or raw_asset_metadata["source_run_id"]

    if source_run_id != raw_asset_metadata["source_run_id"]:
        logger.warning(
            "El source_run_id indicado no coincide con el source_run_id del raw_asset | provided=%s | raw_asset=%s",
            source_run_id,
            raw_asset_metadata["source_run_id"],
        )

    params = build_params(
        raw_asset_id=args.raw_asset_id,
        source_run_id=source_run_id,
    )

    import_summary = load_import_summary(args.raw_asset_id)
    review_profile = build_review_profile(params)
    link_integrity_profile = build_link_integrity_profile(params)
    validation_issue_profile = build_validation_issue_profile(params)
    sample_reviews = fetch_sample_reviews(params)

    checks = build_checks(
        import_summary=import_summary,
        review_profile=review_profile,
        link_integrity_profile=link_integrity_profile,
        validation_issue_profile=validation_issue_profile,
    )

    output = {
        "filters": {
            "source_code": "google_places",
            "source_run_id": source_run_id,
            "raw_asset_id": args.raw_asset_id,
        },
        "raw_asset_metadata": raw_asset_metadata,
        "import_summary": import_summary,
        "review_profile": review_profile,
        "link_integrity_profile": link_integrity_profile,
        "validation_issue": validation_issue_profile,
        "sample_reviews": sample_reviews,
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
            "Check de import Google Places Reviews completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check de import Google Places Reviews completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())