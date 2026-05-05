from __future__ import annotations

import argparse
import json

from sqlalchemy import text

from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba el resultado del import canónico de Google Places en la base de datos."
    )

    parser.add_argument(
        "--source-run-id",
        type=str,
        default=None,
        help="Filtra place_source_ref y validation_issue por source_run_id.",
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        default=None,
        help="Filtra place_source_ref y validation_issue por raw_asset_id.",
    )

    return parser


def fetch_scalar(connection, query: str, params: dict | None = None) -> int:
    result = connection.execute(text(query), params or {}).scalar_one()
    return int(result)


def fetch_rows(connection, query: str, params: dict | None = None) -> list[dict]:
    result = connection.execute(text(query), params or {})
    return [dict(row._mapping) for row in result]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    params: dict[str, str] = {
        "source_code": "google_places",
    }

    source_ref_extra_filter = ""
    validation_extra_filter = ""

    if args.source_run_id:
        source_ref_extra_filter += " AND psr.source_run_id = :source_run_id"
        validation_extra_filter += " AND vi.source_run_id = :source_run_id"
        params["source_run_id"] = args.source_run_id

    if args.raw_asset_id:
        source_ref_extra_filter += " AND psr.raw_asset_id = :raw_asset_id"
        validation_extra_filter += " AND vi.raw_asset_id = :raw_asset_id"
        params["raw_asset_id"] = args.raw_asset_id

    with engine.connect() as connection:
        source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            """,
            params,
        )

        distinct_place_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(DISTINCT psr.place_id)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            """,
            params,
        )

        current_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.is_current = TRUE
            {source_ref_extra_filter}
            """,
            params,
        )

        deleted_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.is_deleted_in_source = TRUE
            {source_ref_extra_filter}
            """,
            params,
        )

        missing_geom_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.source_geom_point IS NULL
            {source_ref_extra_filter}
            """,
            params,
        )

        missing_name_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND (psr.source_name_raw IS NULL OR BTRIM(psr.source_name_raw) = '')
            {source_ref_extra_filter}
            """,
            params,
        )

        entity_type_counts = fetch_rows(
            connection,
            f"""
            SELECT psr.source_entity_type, COUNT(*) AS total
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            GROUP BY psr.source_entity_type
            ORDER BY total DESC, psr.source_entity_type
            """,
            params,
        )

        top_primary_categories = fetch_rows(
            connection,
            f"""
            SELECT psr.source_primary_category_raw, COUNT(*) AS total
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            GROUP BY psr.source_primary_category_raw
            ORDER BY total DESC, psr.source_primary_category_raw
            LIMIT 20
            """,
            params,
        )

        match_methods = fetch_rows(
            connection,
            f"""
            SELECT
                psr.match_method,
                COUNT(*) AS total,
                ROUND(AVG(psr.match_confidence)::numeric, 4) AS avg_match_confidence
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            GROUP BY psr.match_method
            ORDER BY total DESC, psr.match_method
            """,
            params,
        )

        places_without_primary_category_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
            WHERE NOT EXISTS (
                SELECT 1
                FROM hidden_gems.place_category pc
                WHERE pc.place_id = linked_places.place_id
                  AND pc.is_active = TRUE
                  AND pc.is_primary = TRUE
            )
            """,
            params,
        )

        places_without_current_neighborhood_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
            WHERE NOT EXISTS (
                SELECT 1
                FROM hidden_gems.place_neighborhood_assignment pna
                WHERE pna.place_id = linked_places.place_id
                  AND pna.is_current = TRUE
            )
            """,
            params,
        )

        assignment_methods = fetch_rows(
            connection,
            f"""
            SELECT pna.assignment_method, COUNT(*) AS total
            FROM hidden_gems.place_neighborhood_assignment pna
            JOIN (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
              ON linked_places.place_id = pna.place_id
            WHERE pna.is_current = TRUE
            GROUP BY pna.assignment_method
            ORDER BY total DESC, pna.assignment_method
            """,
            params,
        )

        validation_issue_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.validation_issue vi
            WHERE 1=1
            {validation_extra_filter}
            """,
            params,
        )

        validation_issue_by_severity = fetch_rows(
            connection,
            f"""
            SELECT vi.severity, COUNT(*) AS total
            FROM hidden_gems.validation_issue vi
            WHERE 1=1
            {validation_extra_filter}
            GROUP BY vi.severity
            ORDER BY vi.severity
            """,
            params,
        )

        validation_issue_by_code = fetch_rows(
            connection,
            f"""
            SELECT vi.issue_code, COUNT(*) AS total
            FROM hidden_gems.validation_issue vi
            WHERE 1=1
            {validation_extra_filter}
            GROUP BY vi.issue_code
            ORDER BY total DESC, vi.issue_code
            LIMIT 20
            """,
            params,
        )

        sample_places = fetch_rows(
            connection,
            f"""
            SELECT
                p.place_id,
                p.canonical_name,
                p.display_name,
                p.address_text,
                p.place_confidence,
                psr.source_name_raw,
                psr.source_record_id,
                psr.source_status_raw,
                psr.match_method,
                psr.match_confidence
            FROM hidden_gems.place p
            JOIN hidden_gems.place_source_ref psr
              ON psr.place_id = p.place_id
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            ORDER BY psr.created_at DESC, p.canonical_name
            LIMIT 20
            """,
            params,
        )

        sample_neighborhoods = fetch_rows(
            connection,
            f"""
            SELECT
                p.display_name,
                psr.source_name_raw,
                n.official_name AS neighborhood,
                d.official_name AS district,
                pna.assignment_method,
                pna.assignment_confidence
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
            {source_ref_extra_filter}
            ORDER BY psr.created_at DESC, p.display_name
            LIMIT 20
            """,
            params,
        )

    output = {
        "filters": {
            "source_code": "google_places",
            "source_run_id": args.source_run_id,
            "raw_asset_id": args.raw_asset_id,
        },
        "place_source_ref": {
            "count": source_ref_count,
            "distinct_place_count": distinct_place_count,
            "current_count": current_source_ref_count,
            "deleted_in_source_count": deleted_source_ref_count,
            "missing_geom_count": missing_geom_source_ref_count,
            "missing_name_count": missing_name_source_ref_count,
            "entity_type_counts": entity_type_counts,
            "top_primary_categories": top_primary_categories,
            "match_methods": match_methods,
        },
        "place": {
            "without_primary_category_count": places_without_primary_category_count,
            "without_current_neighborhood_count": places_without_current_neighborhood_count,
            "sample_places": sample_places,
        },
        "place_neighborhood_assignment": {
            "assignment_methods": assignment_methods,
            "sample_neighborhoods": sample_neighborhoods,
        },
        "validation_issue": {
            "count": validation_issue_count,
            "by_severity": validation_issue_by_severity,
            "top_issue_codes": validation_issue_by_code,
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    checks = {
        "has_google_place_source_refs": source_ref_count > 0,
        "all_source_refs_current": source_ref_count == current_source_ref_count,
        "no_deleted_source_refs": deleted_source_ref_count == 0,
        "no_missing_source_geometry": missing_geom_source_ref_count == 0,
        "no_missing_source_name": missing_name_source_ref_count == 0,
        "all_places_have_primary_category": places_without_primary_category_count == 0,
        "all_places_have_current_neighborhood": places_without_current_neighborhood_count == 0,
        "no_validation_issues_for_filtered_scope": validation_issue_count == 0,
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Comprobación del import canónico Google Places completada con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Comprobación del import canónico Google Places completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())