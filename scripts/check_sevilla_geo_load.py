from __future__ import annotations

import argparse
import json

from sqlalchemy import text

from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

# Ejemplos de uso
#
# Comprobación general:
# python -m scripts.check_sevilla_geo_load
#
# Filtrando por versión:
# python -m scripts.check_sevilla_geo_load --source-version 2026_04
#
# Filtrando por run concreto:
# python -m scripts.check_sevilla_geo_load --source-run-id TU_SOURCE_RUN_ID



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba el estado de la carga Sevilla Geo en district, neighborhood y validation_issue."
    )

    parser.add_argument(
        "--source-version",
        type=str,
        default=None,
        help="Filtra district y neighborhood por source_version.",
    )

    parser.add_argument(
        "--source-run-id",
        type=str,
        default=None,
        help="Filtra validation_issue por source_run_id.",
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

    district_filter = ""
    neighborhood_filter = ""
    district_params: dict[str, str] = {}
    neighborhood_params: dict[str, str] = {}

    if args.source_version:
        district_filter = "WHERE source_version = :source_version"
        neighborhood_filter = "WHERE source_version = :source_version"
        district_params["source_version"] = args.source_version
        neighborhood_params["source_version"] = args.source_version

    validation_filter = ""
    validation_params: dict[str, str] = {}

    if args.source_run_id:
        validation_filter = "WHERE source_run_id = :source_run_id"
        validation_params["source_run_id"] = args.source_run_id

    with engine.connect() as connection:
        district_count = fetch_scalar(
            connection,
            f"SELECT COUNT(*) FROM hidden_gems.district {district_filter}",
            district_params,
        )

        district_active_count = fetch_scalar(
            connection,
            f"SELECT COUNT(*) FROM hidden_gems.district {district_filter} "
            if district_filter
            else "SELECT COUNT(*) FROM hidden_gems.district WHERE is_active = TRUE",
            district_params,
        )
        if district_filter:
            district_active_count = fetch_scalar(
                connection,
                """
                SELECT COUNT(*)
                FROM hidden_gems.district
                WHERE source_version = :source_version
                  AND is_active = TRUE
                """,
                district_params,
            )

        district_invalid_geometry_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.district
            {"WHERE source_version = :source_version AND " if args.source_version else "WHERE "}
            NOT ST_IsValid(geometry)
            """,
            district_params,
        )

        district_empty_geometry_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.district
            {"WHERE source_version = :source_version AND " if args.source_version else "WHERE "}
            ST_IsEmpty(geometry)
            """,
            district_params,
        )

        neighborhood_count = fetch_scalar(
            connection,
            f"SELECT COUNT(*) FROM hidden_gems.neighborhood {neighborhood_filter}",
            neighborhood_params,
        )

        neighborhood_active_count = fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            WHERE is_active = TRUE
            """
            if not args.source_version
            else """
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            WHERE source_version = :source_version
              AND is_active = TRUE
            """,
            neighborhood_params,
        )

        neighborhood_invalid_geometry_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            {"WHERE source_version = :source_version AND " if args.source_version else "WHERE "}
            NOT ST_IsValid(geometry)
            """,
            neighborhood_params,
        )

        neighborhood_empty_geometry_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            {"WHERE source_version = :source_version AND " if args.source_version else "WHERE "}
            ST_IsEmpty(geometry)
            """,
            neighborhood_params,
        )

        neighborhoods_without_district_count = fetch_scalar(
            connection,
            """
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            WHERE district_id IS NULL
            """
            if not args.source_version
            else """
            SELECT COUNT(*)
            FROM hidden_gems.neighborhood
            WHERE source_version = :source_version
              AND district_id IS NULL
            """,
            neighborhood_params,
        )

        validation_issue_count = fetch_scalar(
            connection,
            f"SELECT COUNT(*) FROM hidden_gems.validation_issue {validation_filter}",
            validation_params,
        )

        validation_issue_by_severity = fetch_rows(
            connection,
            f"""
            SELECT severity, COUNT(*) AS total
            FROM hidden_gems.validation_issue
            {validation_filter}
            GROUP BY severity
            ORDER BY severity
            """,
            validation_params,
        )

        validation_issue_by_code = fetch_rows(
            connection,
            f"""
            SELECT issue_code, COUNT(*) AS total
            FROM hidden_gems.validation_issue
            {validation_filter}
            GROUP BY issue_code
            ORDER BY total DESC, issue_code
            LIMIT 10
            """,
            validation_params,
        )

        district_versions = fetch_rows(
            connection,
            """
            SELECT source_version, COUNT(*) AS total
            FROM hidden_gems.district
            GROUP BY source_version
            ORDER BY source_version
            """
        )

        neighborhood_versions = fetch_rows(
            connection,
            """
            SELECT source_version, COUNT(*) AS total
            FROM hidden_gems.neighborhood
            GROUP BY source_version
            ORDER BY source_version
            """
        )

    output = {
        "filters": {
            "source_version": args.source_version,
            "source_run_id": args.source_run_id,
        },
        "district": {
            "count": district_count,
            "active_count": district_active_count,
            "invalid_geometry_count": district_invalid_geometry_count,
            "empty_geometry_count": district_empty_geometry_count,
            "source_versions": district_versions,
        },
        "neighborhood": {
            "count": neighborhood_count,
            "active_count": neighborhood_active_count,
            "invalid_geometry_count": neighborhood_invalid_geometry_count,
            "empty_geometry_count": neighborhood_empty_geometry_count,
            "without_district_count": neighborhoods_without_district_count,
            "source_versions": neighborhood_versions,
        },
        "validation_issue": {
            "count": validation_issue_count,
            "by_severity": validation_issue_by_severity,
            "top_issue_codes": validation_issue_by_code,
        },
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Comprobación Sevilla Geo completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())