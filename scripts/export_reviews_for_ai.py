"""
Export operational reviews from PostgreSQL to a JSONL dataset for the AI module.

Typical PowerShell usage:

python -m scripts.export_reviews_for_ai `
  --source-code google_places `
  --only-operational `
  --only-training-eligible `
  --min-text-length 20 `
  --output-path data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl

Dry-run:

python -m scripts.export_reviews_for_ai `
  --source-code google_places `
  --only-operational `
  --only-training-eligible `
  --min-text-length 20 `
  --dry-run
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text


DEFAULT_SCHEMA = "hidden_gems"


def get_engine():
    """Reuse the project SQLAlchemy engine when available."""
    try:
        from src.db.database import engine  # type: ignore
        return engine
    except Exception:
        pass

    try:
        from src.db.database import get_engine as project_get_engine  # type: ignore
        return project_get_engine()
    except Exception:
        pass

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.engine import URL
        from src.config.settings import settings  # type: ignore

        url = URL.create(
            "postgresql+psycopg2",
            username=getattr(settings, "pguser"),
            password=getattr(settings, "pgpassword"),
            host=getattr(settings, "pghost"),
            port=int(getattr(settings, "pgport")),
            database=getattr(settings, "pgdatabase"),
        )
        return create_engine(url, future=True, pool_pre_ping=True)
    except Exception as exc:
        raise RuntimeError(
            "No se pudo crear el engine de base de datos. "
            "Revisa src.db.database o src.config.settings."
        ) from exc


def qident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def fqtn(schema: str, table: str) -> str:
    return f"{qident(schema)}.{qident(table)}"


def get_table_columns(conn, schema: str, table: str) -> set[str]:
    rows = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = :schema
              AND table_name = :table
            """
        ),
        {"schema": schema, "table": table},
    ).fetchall()
    return {row[0] for row in rows}


def ensure_tables_exist(conn, schema: str, required_tables: Iterable[str]) -> None:
    rows = conn.execute(
        text(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = :schema
            """
        ),
        {"schema": schema},
    ).fetchall()
    existing = {row[0] for row in rows}
    missing = [table for table in required_tables if table not in existing]
    if missing:
        raise RuntimeError(
            "Faltan tablas requeridas en el schema "
            f"{schema}: {', '.join(missing)}"
        )


def choose_column(
    alias: str,
    columns: set[str],
    candidates: list[str],
    output_name: str,
    default_sql: str = "NULL",
) -> str:
    for column in candidates:
        if column in columns:
            return f'{alias}.{qident(column)} AS {qident(output_name)}'
    return f'{default_sql} AS {qident(output_name)}'


def choose_column_ref(
    alias: str,
    columns: set[str],
    candidates: list[str],
    default_sql: str | None = "NULL",
) -> str | None:
    for column in candidates:
        if column in columns:
            return f'{alias}.{qident(column)}'
    return default_sql


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, bytes):
        return value.hex()
    return value


def normalize_record(row_mapping: dict[str, Any]) -> dict[str, Any]:
    record = {key: json_safe(value) for key, value in row_mapping.items()}

    if record.get("text") is not None:
        record["text"] = str(record["text"]).strip()
    if record.get("text_normalized") is not None:
        record["text_normalized"] = str(record["text_normalized"]).strip()
    if not record.get("text_normalized"):
        record["text_normalized"] = record.get("text")

    record["text_length_chars"] = len(record.get("text") or "")
    return record


def update_summary(summary: dict[str, Any], record: dict[str, Any]) -> None:
    summary["total_exported"] += 1

    for field, set_name in [
        ("review_id", "_review_ids"),
        ("source_review_id", "_source_review_ids"),
        ("place_id", "_place_ids"),
        ("place_source_ref_id", "_place_source_ref_ids"),
        ("neighborhood_id", "_neighborhood_ids"),
        ("district_id", "_district_ids"),
    ]:
        if record.get(field) is not None:
            summary[set_name].add(str(record[field]))

    language = record.get("review_language") or "unknown"
    rating = record.get("rating_value")
    source_code = record.get("source_system_code") or "unknown"

    summary["_language_counts"][str(language)] += 1
    summary["_source_system_counts"][str(source_code)] += 1

    if rating is None:
        summary["_rating_counts"]["unknown"] += 1
    else:
        try:
            summary["_rating_counts"][str(float(rating))] += 1
        except Exception:
            summary["_rating_counts"][str(rating)] += 1

    if not record.get("neighborhood_id"):
        summary["reviews_without_neighborhood"] += 1
    if not record.get("district_id"):
        summary["reviews_without_district"] += 1
    if not record.get("text"):
        summary["reviews_without_text"] += 1

    summary["_text_lengths"].append(int(record.get("text_length_chars") or 0))


def finalize_summary(summary: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    lengths = summary.pop("_text_lengths")
    review_ids = summary.pop("_review_ids")
    source_review_ids = summary.pop("_source_review_ids")
    place_ids = summary.pop("_place_ids")
    place_source_ref_ids = summary.pop("_place_source_ref_ids")
    neighborhood_ids = summary.pop("_neighborhood_ids")
    district_ids = summary.pop("_district_ids")

    language_counts = summary.pop("_language_counts")
    rating_counts = summary.pop("_rating_counts")
    source_system_counts = summary.pop("_source_system_counts")

    summary["unique_review_id_count"] = len(review_ids)
    summary["unique_source_review_id_count"] = len(source_review_ids)
    summary["unique_place_id_count"] = len(place_ids)
    summary["unique_place_source_ref_id_count"] = len(place_source_ref_ids)
    summary["unique_neighborhood_id_count"] = len(neighborhood_ids)
    summary["unique_district_id_count"] = len(district_ids)
    summary["duplicate_review_id_count"] = summary["total_exported"] - len(review_ids)

    summary["language_counts"] = dict(language_counts)
    summary["rating_counts"] = dict(rating_counts)
    summary["source_system_counts"] = dict(source_system_counts)

    summary["text_length_chars"] = {
        "min": min(lengths) if lengths else None,
        "max": max(lengths) if lengths else None,
        "mean": round(sum(lengths) / len(lengths), 4) if lengths else None,
    }

    summary["filters"] = {
        "schema": args.schema,
        "source_code": args.source_code,
        "only_operational": args.only_operational,
        "only_training_eligible": args.only_training_eligible,
        "language": args.language,
        "min_text_length": args.min_text_length,
        "require_neighborhood": args.require_neighborhood,
        "limit": args.limit,
    }

    summary["checks"] = {
        "has_exported_rows": summary["total_exported"] > 0,
        "review_ids_are_unique": summary["duplicate_review_id_count"] == 0,
        "all_have_text": summary["reviews_without_text"] == 0,
        "all_have_neighborhood_when_required": (
            not args.require_neighborhood or summary["reviews_without_neighborhood"] == 0
        ),
        "has_places": summary["unique_place_id_count"] > 0,
    }

    return summary


def build_query(conn, args: argparse.Namespace) -> tuple[str, dict[str, Any], list[str]]:
    schema = args.schema

    ensure_tables_exist(
        conn,
        schema,
        [
            "source_system",
            "review",
            "place",
            "place_source_ref",
            "place_neighborhood_assignment",
            "neighborhood",
            "district",
        ],
    )

    review_cols = get_table_columns(conn, schema, "review")
    place_cols = get_table_columns(conn, schema, "place")
    psr_cols = get_table_columns(conn, schema, "place_source_ref")
    neighborhood_cols = get_table_columns(conn, schema, "neighborhood")
    district_cols = get_table_columns(conn, schema, "district")

    warnings: list[str] = []

    text_expr = choose_column_ref(
        "r",
        review_cols,
        ["review_text_raw", "text", "review_text", "content"],
        "NULL",
    )
    text_normalized_expr = choose_column_ref(
        "r",
        review_cols,
        ["review_text_normalized", "text_normalized", "normalized_text"],
        text_expr,
    )

    select_parts = [
        choose_column("r", review_cols, ["review_id"], "review_id"),
        choose_column("r", review_cols, ["place_id"], "place_id"),
        choose_column("r", review_cols, ["place_source_ref_id"], "place_source_ref_id"),
        'ss."source_code" AS "source_system_code"',
        choose_column("r", review_cols, ["source_review_id"], "source_review_id"),
        choose_column("r", review_cols, ["source_place_record_id"], "source_place_record_id"),
        choose_column("psr", psr_cols, ["source_record_id"], "place_source_record_id"),
        choose_column(
            "p",
            place_cols,
            ["display_name", "canonical_name", "name", "normalized_name"],
            "place_name",
        ),
        choose_column(
            "p",
            place_cols,
            ["canonical_name", "display_name", "name"],
            "place_canonical_name",
        ),
        choose_column(
            "p",
            place_cols,
            ["address_text", "formatted_address", "address", "address_raw"],
            "address_text",
        ),
        choose_column("p", place_cols, ["city", "municipality"], "city", "'Sevilla'"),
        choose_column("n", neighborhood_cols, ["neighborhood_id"], "neighborhood_id"),
        choose_column(
            "n",
            neighborhood_cols,
            ["official_name", "display_name", "normalized_name", "name"],
            "neighborhood_name",
        ),
        choose_column("d", district_cols, ["district_id"], "district_id"),
        choose_column(
            "d",
            district_cols,
            ["official_name", "display_name", "normalized_name", "name"],
            "district_name",
        ),
        choose_column("r", review_cols, ["rating_value", "rating", "stars"], "rating_value"),
        choose_column("r", review_cols, ["review_language", "language"], "review_language"),
        choose_column(
            "r",
            review_cols,
            ["review_created_at", "created_at_source", "publish_time", "date"],
            "review_created_at",
        ),
        choose_column(
            "r",
            review_cols,
            ["review_updated_at", "updated_at_source"],
            "review_updated_at",
        ),
        f'{text_expr} AS "text"',
        f'{text_normalized_expr} AS "text_normalized"',
        choose_column("r", review_cols, ["is_operational_review"], "is_operational_review"),
        choose_column("r", review_cols, ["is_training_eligible"], "is_training_eligible"),
        choose_column("r", review_cols, ["source_review_url", "review_url"], "source_review_url"),
    ]

    if "geom_point" in place_cols:
        select_parts.extend(
            [
                'ST_Y(p."geom_point") AS "place_latitude"',
                'ST_X(p."geom_point") AS "place_longitude"',
            ]
        )
    else:
        select_parts.extend(['NULL AS "place_latitude"', 'NULL AS "place_longitude"'])
        warnings.append("place.geom_point no existe; se exportan lat/lon como null.")

    from_sql = f"""
        FROM {fqtn(schema, "review")} r
        JOIN {fqtn(schema, "source_system")} ss
            ON ss."source_system_id" = r."source_system_id"
        JOIN {fqtn(schema, "place")} p
            ON p."place_id" = r."place_id"
        LEFT JOIN {fqtn(schema, "place_source_ref")} psr
            ON psr."place_source_ref_id" = r."place_source_ref_id"
        LEFT JOIN {fqtn(schema, "place_neighborhood_assignment")} pna
            ON pna."place_id" = r."place_id"
           AND pna."is_current" = TRUE
        LEFT JOIN {fqtn(schema, "neighborhood")} n
            ON n."neighborhood_id" = pna."neighborhood_id"
        LEFT JOIN {fqtn(schema, "district")} d
            ON d."district_id" = pna."district_id"
    """

    where_parts = ['ss."source_code" = :source_code']
    params: dict[str, Any] = {"source_code": args.source_code}

    if "is_active" in review_cols:
        where_parts.append('r."is_active" = TRUE')
    else:
        warnings.append("review.is_active no existe; no se aplica filtro de review activa.")

    if "is_deleted_in_source" in review_cols:
        where_parts.append('r."is_deleted_in_source" = FALSE')
    else:
        warnings.append(
            "review.is_deleted_in_source no existe; no se aplica filtro de eliminadas."
        )

    if args.only_operational:
        if "is_operational_review" in review_cols:
            where_parts.append('r."is_operational_review" = TRUE')
        else:
            warnings.append(
                "--only-operational solicitado, pero review.is_operational_review no existe."
            )

    if args.only_training_eligible:
        if "is_training_eligible" in review_cols:
            where_parts.append('r."is_training_eligible" = TRUE')
        else:
            warnings.append(
                "--only-training-eligible solicitado, pero review.is_training_eligible no existe."
            )

    if args.language:
        lang_col = choose_column_ref("r", review_cols, ["review_language", "language"], None)
        if lang_col:
            where_parts.append(f"LOWER({lang_col}) = LOWER(:language)")
            params["language"] = args.language
        else:
            warnings.append("--language solicitado, pero no existe columna de idioma en review.")

    if args.min_text_length is not None:
        where_parts.append(f"LENGTH(TRIM(COALESCE({text_expr}, ''))) >= :min_text_length")
        params["min_text_length"] = int(args.min_text_length)

    if args.require_neighborhood:
        where_parts.append('pna."neighborhood_id" IS NOT NULL')

    where_sql = "WHERE " + "\n          AND ".join(where_parts)

    order_expr = choose_column_ref(
        "r",
        review_cols,
        ["review_created_at", "created_at_source", "publish_time", "date", "created_at"],
        'r."review_id"',
    )

    limit_sql = ""
    if args.limit is not None:
        limit_sql = "\nLIMIT :limit"
        params["limit"] = int(args.limit)

    sql = f"""
        SELECT
            {",\n            ".join(select_parts)}
        {from_sql}
        {where_sql}
        ORDER BY {order_expr} DESC NULLS LAST, r."review_id"
        {limit_sql}
    """

    return sql, params, warnings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta reviews canónicas a JSONL para el módulo IA de Hidden Gems."
    )
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--source-code", default="google_places")
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("data/artifacts/ai/sevilla/reviews_for_ai_google_places.jsonl"),
    )
    parser.add_argument("--summary-path", type=Path, default=None)
    parser.add_argument("--only-operational", action="store_true")
    parser.add_argument("--only-training-eligible", action="store_true")
    parser.add_argument("--language", default=None)
    parser.add_argument("--min-text-length", type=int, default=20)
    parser.add_argument("--require-neighborhood", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sample-size", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = get_engine()

    with engine.connect() as conn:
        sql, params, warnings = build_query(conn, args)

        count_sql = f"SELECT COUNT(*) AS count FROM ({sql}) AS export_query"
        total_count = conn.execute(text(count_sql), params).scalar_one()

        print("=" * 96)
        print("Export reviews for AI")
        print("=" * 96)
        print(f"Schema: {args.schema}")
        print(f"Source: {args.source_code}")
        print(f"Rows matching filters: {total_count}")

        if warnings:
            print("\nWarnings:")
            for warning in warnings:
                print(f"- {warning}")

        if args.dry_run:
            print("\nDry-run activo. No se escribirá ningún fichero.")
            sample_sql = sql
            sample_params = dict(params)
            if args.limit is None:
                sample_sql = sql + "\nLIMIT :sample_size"
                sample_params["sample_size"] = args.sample_size

            rows = conn.execute(text(sample_sql), sample_params).mappings().fetchall()
            print(f"\nMuestra ({len(rows)} filas):")
            for row in rows:
                record = normalize_record(dict(row))
                print(
                    json.dumps(
                        {
                            "review_id": record.get("review_id"),
                            "place_name": record.get("place_name"),
                            "neighborhood_name": record.get("neighborhood_name"),
                            "rating_value": record.get("rating_value"),
                            "review_language": record.get("review_language"),
                            "text_sample": (record.get("text") or "")[:160],
                        },
                        ensure_ascii=False,
                        default=str,
                    )
                )
            return

        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        if args.summary_path is None:
            args.summary_path = args.output_path.with_name(
                args.output_path.stem + "_summary.json"
            )
        args.summary_path.parent.mkdir(parents=True, exist_ok=True)

        summary: dict[str, Any] = {
            "script": "scripts.export_reviews_for_ai",
            "version": "reviews_for_ai_export_v1",
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "output_path": str(args.output_path),
            "summary_path": str(args.summary_path),
            "total_matching_filters": int(total_count),
            "total_exported": 0,
            "reviews_without_neighborhood": 0,
            "reviews_without_district": 0,
            "reviews_without_text": 0,
            "_review_ids": set(),
            "_source_review_ids": set(),
            "_place_ids": set(),
            "_place_source_ref_ids": set(),
            "_neighborhood_ids": set(),
            "_district_ids": set(),
            "_language_counts": Counter(),
            "_rating_counts": Counter(),
            "_source_system_counts": Counter(),
            "_text_lengths": [],
            "warnings": warnings,
        }

        with args.output_path.open("w", encoding="utf-8") as f:
            result = conn.execute(text(sql), params).mappings()
            for row in result:
                record = normalize_record(dict(row))
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                update_summary(summary, record)

        final_summary = finalize_summary(summary, args)
        with args.summary_path.open("w", encoding="utf-8") as f:
            json.dump(final_summary, f, ensure_ascii=False, indent=2)

        print("\nExportación completada.")
        print(f"JSONL: {args.output_path}")
        print(f"Summary: {args.summary_path}")
        print("\nResumen:")
        print(json.dumps(final_summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
