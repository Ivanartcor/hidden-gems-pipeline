"""
check_ai_downstream_import_readiness.py

Readiness check before loading downstream AI artifacts into PostgreSQL.

This script is intended to be executed after:

1. db/ddl/07_ai_module.sql has been applied.
2. scripts/load_ai_dish_catalog.py has loaded dish and dish_alias.
3. scripts/check_ai_dish_catalog.py has passed.

It checks whether the database is ready to load:

- dish_mention
- dish_mention_sentiment
- dish_place_signal
- hidden_gem_candidate

The main risk at this stage is that the AI artifacts generated from Yelp use
source identifiers such as `business_id` and `review_id`, while the canonical
Hidden Gems database must load downstream AI outputs using:

- place_id
- review_id UUID
- dish_id UUID

Therefore, this script verifies if source IDs in artifacts can be mapped to the
canonical tables review and place_source_ref.

Recommended execution from repository root, PowerShell:

python -m scripts.check_ai_downstream_import_readiness `
  --mentions-path data/artifacts/ai/sentiment/dish_mentions_with_sentiment_hybrid_v1.jsonl `
  --business-signals-path data/artifacts/ai/aggregation/dish_business_ranking_candidates_v1.csv `
  --ranking-path data/artifacts/ai/ranking/hidden_gems_selected_candidates_v1.csv `
  --report-path data/artifacts/ai/checks/check_ai_downstream_import_readiness_report.json

Basic execution without files:

python -m scripts.check_ai_downstream_import_readiness
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.config.settings import settings
from src.db.database import engine


ALLOWED_SCHEMA_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

DEFAULT_SOURCE_CODES = [
    "yelp_open_dataset",
    "yelp",
    "yelp_food_reviews",
]

REQUIRED_TABLES = [
    "ai_model_version",
    "ai_pipeline_run",
    "dish",
    "dish_alias",
    "dish_mention",
    "dish_mention_sentiment",
    "dish_place_signal",
    "hidden_gem_candidate",
    "place",
    "place_source_ref",
    "review",
    "source_system",
]

EXPECTED_AI_MODEL_CODES = [
    "dish_ner_transformer_v1",
    "dish_normalization_rule_based_v2",
    "mention_sentiment_hybrid_v1_1",
    "signal_aggregation_v1",
    "hidden_gems_ranking_v1",
]

EXPECTED_AI_RUN_CODES = [
    "ai_run_yelp_dish_normalization_v2_catalog_import",
]


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class IdSample:
    total_rows: int
    sample_rows: int
    review_ids: list[str]
    business_ids: list[str]
    dish_names: list[str]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not ALLOWED_SCHEMA_PATTERN.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, table: str) -> str:
    schema = validate_schema_name(schema)
    return f'"{schema}"."{table}"'


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nReport written to: {path}")


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return re.sub(r"\s+", " ", str(value)).strip()


def normalize_lower(value: Any) -> str:
    return normalize_space(value).lower()


def unique_non_empty(values: Iterable[Any], *, limit: int | None = None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        clean = normalize_space(value)
        if not clean or clean in seen:
            continue
        seen.add(clean)
        result.append(clean)
        if limit is not None and len(result) >= limit:
            break

    return result


def print_section(title: str) -> None:
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)


def print_table(rows: list[dict[str, Any]], *, empty_message: str = "No rows.") -> None:
    if not rows:
        print(empty_message)
        return
    print(pd.DataFrame(rows).to_string(index=False))


def mappings(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    rows = conn.execute(text(sql), params or {}).mappings().all()
    return [dict(row) for row in rows]


def scalar(conn: Connection, sql: str, params: dict[str, Any] | None = None) -> Any:
    return conn.execute(text(sql), params or {}).scalar_one()


def percentage(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100.0, 4)


def count_uuid_like(values: list[str]) -> int:
    return sum(1 for value in values if UUID_PATTERN.match(value))


# -----------------------------------------------------------------------------
# File readers
# -----------------------------------------------------------------------------

def read_jsonl_sample(path: Path, *, max_rows: int) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records: list[dict[str, Any]] = []
    invalid_lines = 0
    total_rows = 0

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            total_rows += 1
            if len(records) >= max_rows:
                continue

            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    records.append(item)
            except json.JSONDecodeError:
                invalid_lines += 1

    df = pd.DataFrame(records)
    df.attrs["total_rows"] = total_rows
    df.attrs["invalid_lines"] = invalid_lines
    return df


def read_csv_sample(path: Path, *, max_rows: int) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path, nrows=max_rows)
    try:
        # Count total rows excluding header without loading entire file into memory.
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            total_rows = max(0, sum(1 for _ in f) - 1)
    except Exception:
        total_rows = len(df)

    df.attrs["total_rows"] = total_rows
    return df


def extract_id_sample_from_df(df: pd.DataFrame, *, total_rows: int, max_unique_ids: int) -> IdSample:
    review_col_candidates = [
        "review_id",
        "source_review_id",
        "source_review_id_yelp",
        "source_review_id_raw",
    ]

    business_col_candidates = [
        "business_id",
        "source_business_id",
        "source_place_record_id",
        "source_record_id",
        "yelp_business_id",
    ]

    dish_col_candidates = [
        "canonical_dish_name_v2",
        "canonical_dish_name",
        "canonical_name",
        "dish_name",
    ]

    review_ids: list[str] = []
    business_ids: list[str] = []
    dish_names: list[str] = []

    for col in review_col_candidates:
        if col in df.columns:
            review_ids = unique_non_empty(df[col].tolist(), limit=max_unique_ids)
            break

    for col in business_col_candidates:
        if col in df.columns:
            business_ids = unique_non_empty(df[col].tolist(), limit=max_unique_ids)
            break

    for col in dish_col_candidates:
        if col in df.columns:
            dish_names = unique_non_empty(df[col].tolist(), limit=max_unique_ids)
            break

    return IdSample(
        total_rows=int(total_rows),
        sample_rows=int(len(df)),
        review_ids=review_ids,
        business_ids=business_ids,
        dish_names=dish_names,
    )


# -----------------------------------------------------------------------------
# Database checks
# -----------------------------------------------------------------------------

def check_tables(conn: Connection, schema: str) -> tuple[list[dict[str, Any]], list[str]]:
    rows = mappings(
        conn,
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = :schema
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
        """,
        {"schema": schema},
    )

    existing = {row["table_name"] for row in rows}
    missing = [table for table in REQUIRED_TABLES if table not in existing]

    table_rows = [
        {
            "table_name": table,
            "exists": table in existing,
        }
        for table in REQUIRED_TABLES
    ]

    return table_rows, missing


def fetch_source_system_summary(conn: Connection, schema: str) -> list[dict[str, Any]]:
    """
    Return source-system counts without creating a large join product.

    The previous version joined source_system + source_run + place_source_ref +
    review in a single query. After loading a large Yelp review corpus this can
    explode into a huge intermediate result and force PostgreSQL to write large
    temporary files. This version aggregates each table independently and then
    joins the small aggregated results.
    """

    return mappings(
        conn,
        f"""
        WITH
        sr_counts AS (
            SELECT
                source_system_id,
                COUNT(*) AS source_run_count
            FROM {qname(schema, 'source_run')}
            GROUP BY source_system_id
        ),
        psr_counts AS (
            SELECT
                source_system_id,
                COUNT(*) AS place_source_ref_count
            FROM {qname(schema, 'place_source_ref')}
            GROUP BY source_system_id
        ),
        review_counts AS (
            SELECT
                source_system_id,
                COUNT(*) AS review_count
            FROM {qname(schema, 'review')}
            GROUP BY source_system_id
        )
        SELECT
            ss.source_code,
            ss.source_name,
            ss.source_type::text AS source_type,
            ss.is_active,
            COALESCE(sr_counts.source_run_count, 0) AS source_run_count,
            COALESCE(psr_counts.place_source_ref_count, 0) AS place_source_ref_count,
            COALESCE(review_counts.review_count, 0) AS review_count
        FROM {qname(schema, 'source_system')} ss
        LEFT JOIN sr_counts
            ON sr_counts.source_system_id = ss.source_system_id
        LEFT JOIN psr_counts
            ON psr_counts.source_system_id = ss.source_system_id
        LEFT JOIN review_counts
            ON review_counts.source_system_id = ss.source_system_id
        ORDER BY review_count DESC, place_source_ref_count DESC, ss.source_code;
        """,
    )


def fetch_ai_catalog_summary(conn: Connection, schema: str) -> dict[str, Any]:
    result = {
        "ai_model_version_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'ai_model_version')};")),
        "ai_pipeline_run_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'ai_pipeline_run')};")),
        "dish_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'dish')};")),
        "dish_alias_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'dish_alias')};")),
    }

    model_rows = mappings(
        conn,
        f"""
        SELECT model_code, task_name, model_type, version_label, is_active
        FROM {qname(schema, 'ai_model_version')}
        WHERE model_code = ANY(:model_codes)
        ORDER BY model_code;
        """,
        {"model_codes": EXPECTED_AI_MODEL_CODES},
    )

    run_rows = mappings(
        conn,
        f"""
        SELECT run_code, run_type, status::text AS status, started_at, finished_at
        FROM {qname(schema, 'ai_pipeline_run')}
        WHERE run_code = ANY(:run_codes)
        ORDER BY run_code;
        """,
        {"run_codes": EXPECTED_AI_RUN_CODES},
    )

    result["expected_models_found"] = model_rows
    result["expected_model_codes_missing"] = sorted(
        set(EXPECTED_AI_MODEL_CODES) - {row["model_code"] for row in model_rows}
    )
    result["expected_runs_found"] = run_rows
    result["expected_run_codes_missing"] = sorted(
        set(EXPECTED_AI_RUN_CODES) - {row["run_code"] for row in run_rows}
    )

    return result


def fetch_core_counts(conn: Connection, schema: str) -> dict[str, Any]:
    return {
        "place_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'place')};")),
        "place_source_ref_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'place_source_ref')};")),
        "review_count": int(scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'review')};")),
        "review_with_source_review_id_count": int(
            scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'review')} WHERE source_review_id IS NOT NULL;")
        ),
        "review_with_source_place_record_id_count": int(
            scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'review')} WHERE source_place_record_id IS NOT NULL;")
        ),
        "training_eligible_review_count": int(
            scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'review')} WHERE is_training_eligible IS TRUE;")
        ),
        "operational_review_count": int(
            scalar(conn, f"SELECT COUNT(*) FROM {qname(schema, 'review')} WHERE is_operational_review IS TRUE;")
        ),
    }


def count_matches(conn: Connection, schema: str, ids: list[str], sql_template: str) -> int:
    if not ids:
        return 0

    return int(
        scalar(
            conn,
            sql_template,
            {"ids": ids},
        )
    )


def check_artifact_ids_against_db(
    conn: Connection,
    *,
    schema: str,
    sample: IdSample,
    source_codes: list[str],
) -> dict[str, Any]:
    review_ids = sample.review_ids
    business_ids = sample.business_ids
    dish_names = [normalize_lower(name) for name in sample.dish_names if normalize_lower(name)]

    source_filter_sql = ""
    source_params: dict[str, Any] = {}

    if source_codes:
        source_filter_sql = """
        AND source_system_id IN (
            SELECT source_system_id
            FROM {source_system_table}
            WHERE source_code = ANY(:source_codes)
        )
        """.format(source_system_table=qname(schema, "source_system"))
        source_params["source_codes"] = source_codes

    review_uuid_match_count = 0
    review_source_id_match_count = 0
    review_source_place_record_match_count = 0
    business_place_source_ref_match_count = 0
    business_review_source_place_match_count = 0
    dish_name_match_count = 0

    if review_ids:
        review_uuid_match_count = count_matches(
            conn,
            schema,
            review_ids,
            f"""
            SELECT COUNT(DISTINCT review_id::text)
            FROM {qname(schema, 'review')}
            WHERE review_id::text = ANY(:ids);
            """,
        )

        params = {"ids": review_ids, **source_params}
        review_source_id_match_count = int(
            scalar(
                conn,
                f"""
                SELECT COUNT(DISTINCT source_review_id)
                FROM {qname(schema, 'review')}
                WHERE source_review_id = ANY(:ids)
                {source_filter_sql};
                """,
                params,
            )
        )

    if business_ids:
        params = {"ids": business_ids, **source_params}

        business_place_source_ref_match_count = int(
            scalar(
                conn,
                f"""
                SELECT COUNT(DISTINCT source_record_id)
                FROM {qname(schema, 'place_source_ref')}
                WHERE source_record_id = ANY(:ids)
                {source_filter_sql};
                """,
                params,
            )
        )

        business_review_source_place_match_count = int(
            scalar(
                conn,
                f"""
                SELECT COUNT(DISTINCT source_place_record_id)
                FROM {qname(schema, 'review')}
                WHERE source_place_record_id = ANY(:ids)
                {source_filter_sql};
                """,
                params,
            )
        )

    if dish_names:
        dish_name_match_count = int(
            scalar(
                conn,
                f"""
                SELECT COUNT(DISTINCT normalized_name)
                FROM {qname(schema, 'dish')}
                WHERE normalized_name = ANY(:ids);
                """,
                {"ids": dish_names},
            )
        )

    review_id_count = len(review_ids)
    business_id_count = len(business_ids)
    dish_name_count = len(dish_names)

    return {
        "artifact_rows_total": sample.total_rows,
        "artifact_rows_sampled": sample.sample_rows,
        "unique_review_ids_sampled": review_id_count,
        "unique_business_ids_sampled": business_id_count,
        "unique_dish_names_sampled": dish_name_count,
        "review_ids_uuid_like": count_uuid_like(review_ids),
        "review_uuid_match_count": review_uuid_match_count,
        "review_uuid_match_pct": percentage(review_uuid_match_count, review_id_count),
        "review_source_id_match_count": review_source_id_match_count,
        "review_source_id_match_pct": percentage(review_source_id_match_count, review_id_count),
        "business_place_source_ref_match_count": business_place_source_ref_match_count,
        "business_place_source_ref_match_pct": percentage(business_place_source_ref_match_count, business_id_count),
        "business_review_source_place_match_count": business_review_source_place_match_count,
        "business_review_source_place_match_pct": percentage(business_review_source_place_match_count, business_id_count),
        "dish_name_match_count": dish_name_match_count,
        "dish_name_match_pct": percentage(dish_name_match_count, dish_name_count),
    }


# -----------------------------------------------------------------------------
# Main check flow
# -----------------------------------------------------------------------------

def run_readiness_check(
    *,
    schema: str,
    source_codes: list[str],
    mentions_path: Path | None,
    business_signals_path: Path | None,
    ranking_path: Path | None,
    max_rows: int,
    max_unique_ids: int,
) -> tuple[dict[str, Any], list[str], list[str]]:
    schema = validate_schema_name(schema)
    source_codes = [normalize_lower(code) for code in source_codes if normalize_lower(code)]

    errors: list[str] = []
    warnings: list[str] = []

    report: dict[str, Any] = {
        "schema": schema,
        "source_codes_checked": source_codes,
        "settings_pgdatabase": getattr(settings, "pgdatabase", None),
        "settings_pghost": getattr(settings, "pghost", None),
        "settings_pgport": getattr(settings, "pgport", None),
        "files": {
            "mentions_path": str(mentions_path) if mentions_path else None,
            "business_signals_path": str(business_signals_path) if business_signals_path else None,
            "ranking_path": str(ranking_path) if ranking_path else None,
            "max_rows": max_rows,
            "max_unique_ids": max_unique_ids,
        },
    }

    with engine.connect() as conn:
        print_section("1. Required tables")
        table_rows, missing_tables = check_tables(conn, schema)
        report["required_tables"] = table_rows
        report["missing_tables"] = missing_tables
        print_table(table_rows)

        if missing_tables:
            errors.append(f"Missing required tables: {missing_tables}")

        print_section("2. Source system summary")
        source_summary = fetch_source_system_summary(conn, schema)
        report["source_system_summary"] = source_summary
        print_table(source_summary[:30])

        existing_source_codes = {row["source_code"] for row in source_summary}
        missing_source_codes = [code for code in source_codes if code not in existing_source_codes]
        report["missing_source_codes"] = missing_source_codes

        if len(source_codes) > 0 and len(missing_source_codes) == len(source_codes):
            warnings.append(
                "None of the requested source codes exist in source_system. "
                "Downstream Yelp artifact mapping may fail unless source codes are different in your DB."
            )

        print_section("3. AI catalog and run summary")
        ai_catalog_summary = fetch_ai_catalog_summary(conn, schema)
        report["ai_catalog_summary"] = ai_catalog_summary
        print(json.dumps(ai_catalog_summary, indent=2, ensure_ascii=False, default=str))

        if ai_catalog_summary["dish_count"] <= 0:
            errors.append("No rows found in dish. Load the AI dish catalog before downstream AI artifacts.")
        if ai_catalog_summary["dish_alias_count"] <= 0:
            errors.append("No rows found in dish_alias. Load aliases before downstream AI artifacts.")
        if ai_catalog_summary["expected_model_codes_missing"]:
            warnings.append(
                f"Missing expected ai_model_version rows: {ai_catalog_summary['expected_model_codes_missing']}"
            )

        print_section("4. Core place/review counts")
        core_counts = fetch_core_counts(conn, schema)
        report["core_counts"] = core_counts
        print(json.dumps(core_counts, indent=2, ensure_ascii=False))

        if core_counts["place_count"] <= 0:
            warnings.append("No places found. dish_place_signal and ranking cannot be loaded canonically yet.")
        if core_counts["review_count"] <= 0:
            warnings.append("No reviews found. dish_mention and dish_mention_sentiment cannot be loaded canonically yet.")

        artifact_reports: dict[str, Any] = {}

        if mentions_path is not None:
            print_section("5. Mentions/sentiment artifact mapping")
            mentions_df = read_jsonl_sample(mentions_path, max_rows=max_rows)
            mentions_sample = extract_id_sample_from_df(
                mentions_df,
                total_rows=int(mentions_df.attrs.get("total_rows", len(mentions_df))),
                max_unique_ids=max_unique_ids,
            )
            mentions_mapping = check_artifact_ids_against_db(
                conn,
                schema=schema,
                sample=mentions_sample,
                source_codes=source_codes,
            )
            mentions_mapping["invalid_jsonl_lines_in_sample_reader"] = int(mentions_df.attrs.get("invalid_lines", 0))
            mentions_mapping["columns_detected"] = list(mentions_df.columns)
            artifact_reports["mentions_sentiment"] = mentions_mapping
            print(json.dumps(mentions_mapping, indent=2, ensure_ascii=False, default=str))

            if mentions_mapping["review_uuid_match_pct"] < 90 and mentions_mapping["review_source_id_match_pct"] < 90:
                warnings.append(
                    "Mentions artifact review IDs do not strongly match review.review_id or review.source_review_id. "
                    "Do not load dish_mention until the review mapping is resolved."
                )
            if mentions_mapping["business_place_source_ref_match_pct"] < 90 and mentions_mapping["business_review_source_place_match_pct"] < 90:
                warnings.append(
                    "Mentions artifact business IDs do not strongly match place_source_ref.source_record_id or review.source_place_record_id."
                )
            if mentions_mapping["dish_name_match_pct"] < 80:
                warnings.append(
                    "Mentions artifact dish names have low match rate against dish.normalized_name. Check catalog loading/version alignment."
                )

        if business_signals_path is not None:
            print_section("6. Business-dish signals artifact mapping")
            signals_df = read_csv_sample(business_signals_path, max_rows=max_rows)
            signals_sample = extract_id_sample_from_df(
                signals_df,
                total_rows=int(signals_df.attrs.get("total_rows", len(signals_df))),
                max_unique_ids=max_unique_ids,
            )
            signals_mapping = check_artifact_ids_against_db(
                conn,
                schema=schema,
                sample=signals_sample,
                source_codes=source_codes,
            )
            signals_mapping["columns_detected"] = list(signals_df.columns)
            artifact_reports["business_signals"] = signals_mapping
            print(json.dumps(signals_mapping, indent=2, ensure_ascii=False, default=str))

            if signals_mapping["business_place_source_ref_match_pct"] < 90:
                warnings.append(
                    "Business signals artifact business IDs do not strongly map to place_source_ref.source_record_id. "
                    "Do not load dish_place_signal until Yelp business_id -> place_id mapping is resolved."
                )
            if signals_mapping["dish_name_match_pct"] < 80:
                warnings.append(
                    "Business signals dish names have low match rate against dish.normalized_name."
                )

        if ranking_path is not None:
            print_section("7. Hidden Gems ranking artifact mapping")
            ranking_df = read_csv_sample(ranking_path, max_rows=max_rows)
            ranking_sample = extract_id_sample_from_df(
                ranking_df,
                total_rows=int(ranking_df.attrs.get("total_rows", len(ranking_df))),
                max_unique_ids=max_unique_ids,
            )
            ranking_mapping = check_artifact_ids_against_db(
                conn,
                schema=schema,
                sample=ranking_sample,
                source_codes=source_codes,
            )
            ranking_mapping["columns_detected"] = list(ranking_df.columns)
            artifact_reports["ranking"] = ranking_mapping
            print(json.dumps(ranking_mapping, indent=2, ensure_ascii=False, default=str))

            if ranking_mapping["business_place_source_ref_match_pct"] < 90:
                warnings.append(
                    "Ranking artifact business IDs do not strongly map to place_source_ref.source_record_id. "
                    "Do not load hidden_gem_candidate until business_id -> place_id mapping is resolved."
                )
            if ranking_mapping["dish_name_match_pct"] < 80:
                warnings.append(
                    "Ranking artifact dish names have low match rate against dish.normalized_name."
                )

        report["artifact_mapping"] = artifact_reports

    # Derived readiness decisions
    dish_catalog_ready = (
        report.get("ai_catalog_summary", {}).get("dish_count", 0) > 0
        and report.get("ai_catalog_summary", {}).get("dish_alias_count", 0) > 0
    )
    core_reviews_ready = report.get("core_counts", {}).get("review_count", 0) > 0
    core_places_ready = report.get("core_counts", {}).get("place_count", 0) > 0

    mentions_mapping = report.get("artifact_mapping", {}).get("mentions_sentiment")
    signals_mapping = report.get("artifact_mapping", {}).get("business_signals")
    ranking_mapping = report.get("artifact_mapping", {}).get("ranking")

    mentions_review_match_ready = False
    mentions_business_match_ready = False
    signals_business_match_ready = False
    ranking_business_match_ready = False

    if mentions_mapping:
        mentions_review_match_ready = (
            mentions_mapping["review_uuid_match_pct"] >= 90
            or mentions_mapping["review_source_id_match_pct"] >= 90
        )
        mentions_business_match_ready = (
            mentions_mapping["business_place_source_ref_match_pct"] >= 90
            or mentions_mapping["business_review_source_place_match_pct"] >= 90
        )

    if signals_mapping:
        signals_business_match_ready = signals_mapping["business_place_source_ref_match_pct"] >= 90

    if ranking_mapping:
        ranking_business_match_ready = ranking_mapping["business_place_source_ref_match_pct"] >= 90

    readiness = {
        "dish_catalog_ready": bool(dish_catalog_ready),
        "core_places_ready": bool(core_places_ready),
        "core_reviews_ready": bool(core_reviews_ready),
        "ready_to_design_dish_mentions_loader": bool(dish_catalog_ready),
        "ready_to_load_dish_mentions": bool(
            dish_catalog_ready and core_reviews_ready and mentions_review_match_ready and mentions_business_match_ready
        ) if mentions_mapping else False,
        "ready_to_load_dish_place_signals": bool(
            dish_catalog_ready and core_places_ready and signals_business_match_ready
        ) if signals_mapping else False,
        "ready_to_load_hidden_gem_candidates": bool(
            dish_catalog_ready and core_places_ready and ranking_business_match_ready
        ) if ranking_mapping else False,
    }

    report["readiness"] = readiness

    print_section("8. Readiness decision")
    print(json.dumps(readiness, indent=2, ensure_ascii=False))

    if not readiness["dish_catalog_ready"]:
        errors.append("AI dish catalog is not ready.")

    return report, errors, warnings


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check readiness before loading downstream AI artifacts."
    )

    parser.add_argument(
        "--schema",
        default=getattr(settings, "pgschema", "hidden_gems"),
        help="PostgreSQL schema name. Defaults to settings.pgschema or hidden_gems.",
    )

    parser.add_argument(
        "--source-code",
        dest="source_codes",
        action="append",
        default=None,
        help=(
            "Source system code to check for mapping. Can be repeated. "
            "Defaults to yelp_open_dataset, yelp and yelp_food_reviews."
        ),
    )

    parser.add_argument(
        "--mentions-path",
        type=Path,
        default=None,
        help="Optional JSONL artifact with dish mentions and sentiment.",
    )

    parser.add_argument(
        "--business-signals-path",
        type=Path,
        default=None,
        help="Optional CSV artifact with business-dish signals/ranking candidates.",
    )

    parser.add_argument(
        "--ranking-path",
        type=Path,
        default=None,
        help="Optional CSV artifact with selected Hidden Gems ranking candidates.",
    )

    parser.add_argument(
        "--max-rows",
        type=int,
        default=50000,
        help="Maximum rows to inspect from each artifact. Default: 50000.",
    )

    parser.add_argument(
        "--max-unique-ids",
        type=int,
        default=20000,
        help="Maximum unique IDs per artifact to compare against DB. Default: 20000.",
    )

    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Optional JSON report path.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    source_codes = args.source_codes if args.source_codes else DEFAULT_SOURCE_CODES

    try:
        report, errors, warnings = run_readiness_check(
            schema=args.schema,
            source_codes=source_codes,
            mentions_path=args.mentions_path,
            business_signals_path=args.business_signals_path,
            ranking_path=args.ranking_path,
            max_rows=args.max_rows,
            max_unique_ids=args.max_unique_ids,
        )
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    report["errors"] = errors
    report["warnings"] = warnings

    print_section("9. Warnings")
    if warnings:
        for warning in warnings:
            print(f"- WARNING: {warning}")
    else:
        print("No warnings.")

    print_section("10. Errors")
    if errors:
        for error in errors:
            print(f"- ERROR: {error}")
    else:
        print("No errors.")

    if args.report_path is not None:
        write_json(args.report_path, report)

    if errors:
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
