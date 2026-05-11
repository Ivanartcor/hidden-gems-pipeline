"""Check Sevilla AI pilot data loaded in PostgreSQL.

This script validates the database state after running:

    python -m scripts.load_sevilla_ai_pilot_outputs

It checks the complete Sevilla pilot AI flow:

1. ai_model_version
2. ai_pipeline_run
3. dish
4. dish_alias
5. dish_mention
6. dish_mention_sentiment
7. dish_place_signal
8. hidden_gem_candidate
9. optional AI views from 08_ai_views.sql

Recommended execution from repository root:

    python -m scripts.check_sevilla_ai_pilot_loaded `
      --report-path data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json

By default the loader stores the pilot ranking as ranking_scope='other' because the
current DB constraint does not allow 'sevilla_pilot' as a native value. The original
scope is preserved in hidden_gem_candidate.ranking_config_json->>'artifact_ranking_scope'.
This check therefore validates both values:

    db ranking_scope        = other
    artifact ranking_scope  = sevilla_pilot
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import text

from src.db.database import engine


# -----------------------------------------------------------------------------
# Defaults aligned with load_sevilla_ai_pilot_outputs.py
# -----------------------------------------------------------------------------

DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_REPORT_PATH = Path("data/artifacts/ai/sevilla/check_sevilla_ai_pilot_loaded_report.json")

DEFAULT_DISH_DETECTION_MODEL_CODE = "sevilla_dish_detection_hybrid_v1"
DEFAULT_DISH_NORMALIZATION_MODEL_CODE = "sevilla_dish_normalization_hybrid_v1"
DEFAULT_SENTIMENT_MODEL_CODE = "sevilla_mention_sentiment_hybrid_v1"
DEFAULT_AGGREGATION_MODEL_CODE = "sevilla_signal_aggregation_v1"
DEFAULT_RANKING_MODEL_CODE = "sevilla_hidden_gems_ranking_pilot_v1"

DEFAULT_CATALOG_RUN_CODE = "ai_run_sevilla_dish_catalog_v1"
DEFAULT_MENTION_RUN_CODE = "ai_run_sevilla_dish_mentions_v1"
DEFAULT_SENTIMENT_RUN_CODE = "ai_run_sevilla_mention_sentiment_v1"
DEFAULT_AGGREGATION_RUN_CODE = "ai_run_sevilla_signal_aggregation_v1"
DEFAULT_RANKING_RUN_CODE = "ai_run_sevilla_hidden_gems_ranking_pilot_v1"

DEFAULT_SIGNAL_VERSION = "sevilla_place_dish_signal_v1"
DEFAULT_RANKING_VERSION = "sevilla_hidden_gems_ranking_pilot_v1"
DEFAULT_DB_RANKING_SCOPE = "other"
DEFAULT_ARTIFACT_RANKING_SCOPE = "sevilla_pilot"

# Expected counts from the current Sevilla pilot v1 artifacts.
DEFAULT_EXPECTED_DISHES = 190
DEFAULT_EXPECTED_ALIASES = 243
DEFAULT_EXPECTED_MENTIONS = 2979
DEFAULT_EXPECTED_SENTIMENTS = 2979
DEFAULT_EXPECTED_SIGNALS = 2212
DEFAULT_EXPECTED_RANKING_CANDIDATES = 256
DEFAULT_EXPECTED_SELECTED = 150
DEFAULT_EXPECTED_MIN_DISTRICTS_SELECTED = 10
DEFAULT_EXPECTED_MIN_NEIGHBORHOODS_SELECTED = 40

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

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
    "review",
    "district",
    "neighborhood",
]

OPTIONAL_VIEWS = [
    "vw_ai_pipeline_run_summary",
    "vw_ai_dish_place_signals",
    "vw_ai_hidden_gem_candidate_detail",
    "vw_ai_hidden_gems_place_summary",
    "vw_ai_hidden_gems_dish_summary",
    "vw_ai_dish_mentions_with_sentiment",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, name: str) -> str:
    return f'"{validate_schema_name(schema)}"."{name}"'


def to_builtin(value: Any) -> Any:
    """Convert pandas/numpy/Decimal/date values into strict JSON-compatible values."""
    if value is None:
        return None

    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        if value.is_nan():
            return None
        return float(value)

    if hasattr(value, "item"):
        try:
            return to_builtin(value.item())
        except Exception:
            pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    try:
        # pd.isna on lists/dicts can be ambiguous, so keep this late.
        if pd.isna(value):
            return None
    except Exception:
        pass

    return value


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    return [to_builtin(row) for row in df.to_dict(orient="records")]


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def read_scalar(sql: str, params: dict[str, Any] | None = None) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


def print_section(title: str) -> None:
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)


def count_from_df(df: pd.DataFrame, column: str = "row_count") -> int:
    if df.empty or column not in df.columns:
        return 0
    value = df[column].iloc[0]
    if pd.isna(value):
        return 0
    return int(value)


def model_codes() -> list[str]:
    return [
        DEFAULT_DISH_DETECTION_MODEL_CODE,
        DEFAULT_DISH_NORMALIZATION_MODEL_CODE,
        DEFAULT_SENTIMENT_MODEL_CODE,
        DEFAULT_AGGREGATION_MODEL_CODE,
        DEFAULT_RANKING_MODEL_CODE,
    ]


def run_codes() -> list[str]:
    return [
        DEFAULT_CATALOG_RUN_CODE,
        DEFAULT_MENTION_RUN_CODE,
        DEFAULT_SENTIMENT_RUN_CODE,
        DEFAULT_AGGREGATION_RUN_CODE,
        DEFAULT_RANKING_RUN_CODE,
    ]


def build_values_cte(values: list[str], column_name: str = "code") -> tuple[str, dict[str, str]]:
    """Build a VALUES CTE-safe parameter list."""
    params: dict[str, str] = {}
    placeholders: list[str] = []
    for i, value in enumerate(values):
        key = f"{column_name}_{i}"
        placeholders.append(f"(:{key})")
        params[key] = value
    return ", ".join(placeholders), params


# -----------------------------------------------------------------------------
# Report builder
# -----------------------------------------------------------------------------


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    schema = validate_schema_name(args.schema)

    params = {
        "catalog_run_code": args.catalog_run_code,
        "mention_run_code": args.mention_run_code,
        "sentiment_run_code": args.sentiment_run_code,
        "aggregation_run_code": args.aggregation_run_code,
        "ranking_run_code": args.ranking_run_code,
        "signal_version": args.signal_version,
        "ranking_version": args.ranking_version,
        "db_ranking_scope": args.db_ranking_scope,
        "artifact_ranking_scope": args.artifact_ranking_scope,
        "top_n": args.top_n,
    }

    # ------------------------------------------------------------------
    # Required tables and optional views
    # ------------------------------------------------------------------
    table_rows: list[dict[str, Any]] = []
    for table_name in REQUIRED_TABLES:
        exists = read_scalar("SELECT to_regclass(:regclass_name) IS NOT NULL", {"regclass_name": f"{schema}.{table_name}"})
        table_rows.append({"object_name": table_name, "exists": bool(exists)})
    required_tables_df = pd.DataFrame(table_rows)

    view_rows: list[dict[str, Any]] = []
    for view_name in OPTIONAL_VIEWS:
        exists = read_scalar("SELECT to_regclass(:regclass_name) IS NOT NULL", {"regclass_name": f"{schema}.{view_name}"})
        view_rows.append({"object_name": view_name, "exists": bool(exists)})
    optional_views_df = pd.DataFrame(view_rows)

    # If critical tables are missing, return early with actionable report.
    missing_tables = required_tables_df.loc[~required_tables_df["exists"], "object_name"].tolist()
    if missing_tables:
        report = {
            "schema": schema,
            "status": "failed_missing_tables",
            "required_tables": df_to_records(required_tables_df),
            "optional_views": df_to_records(optional_views_df),
            "errors": [f"Missing required tables: {missing_tables}"],
            "warnings": [],
            "checks": {"required_tables_exist": False},
            "ready_for_queries": False,
        }
        return report

    # ------------------------------------------------------------------
    # Model versions and pipeline runs
    # ------------------------------------------------------------------
    model_values_sql, model_params = build_values_cte(model_codes(), "model_code")
    model_versions_sql = f"""
    WITH expected(model_code) AS (VALUES {model_values_sql})
    SELECT
        expected.model_code,
        amv.ai_model_version_id,
        amv.model_name,
        amv.model_type,
        amv.task_name,
        amv.version_label,
        amv.language_scope,
        amv.is_active,
        (amv.ai_model_version_id IS NOT NULL) AS exists_in_db
    FROM expected
    LEFT JOIN {qname(schema, 'ai_model_version')} amv
        ON amv.model_code = expected.model_code
    ORDER BY expected.model_code;
    """
    model_versions_df = read_df(model_versions_sql, model_params)

    run_values_sql, run_params = build_values_cte(run_codes(), "run_code")
    pipeline_runs_sql = f"""
    WITH expected(run_code) AS (VALUES {run_values_sql})
    SELECT
        expected.run_code,
        apr.ai_pipeline_run_id,
        apr.run_type,
        apr.status::text AS status,
        apr.started_at,
        apr.finished_at,
        apr.duration_seconds,
        (apr.ai_pipeline_run_id IS NOT NULL) AS exists_in_db
    FROM expected
    LEFT JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.run_code = expected.run_code
    ORDER BY expected.run_code;
    """
    pipeline_runs_df = read_df(pipeline_runs_sql, run_params)

    # ------------------------------------------------------------------
    # Scoped counts
    # ------------------------------------------------------------------
    scoped_counts_sql = f"""
    SELECT 'dish_catalog' AS entity_name, COUNT(*)::bigint AS row_count
    FROM {qname(schema, 'dish')} d
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = d.source_ai_run_id
    WHERE apr.run_code = :catalog_run_code

    UNION ALL
    SELECT 'dish_alias', COUNT(*)::bigint
    FROM {qname(schema, 'dish_alias')} da
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = da.source_ai_run_id
    WHERE apr.run_code = :catalog_run_code

    UNION ALL
    SELECT 'dish_mention', COUNT(*)::bigint
    FROM {qname(schema, 'dish_mention')} dm
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = dm.ai_pipeline_run_id
    WHERE apr.run_code = :mention_run_code

    UNION ALL
    SELECT 'dish_mention_sentiment', COUNT(*)::bigint
    FROM {qname(schema, 'dish_mention_sentiment')} dms
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = dms.ai_pipeline_run_id
    WHERE apr.run_code = :sentiment_run_code

    UNION ALL
    SELECT 'dish_place_signal', COUNT(*)::bigint
    FROM {qname(schema, 'dish_place_signal')} dps
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = dps.ai_pipeline_run_id
    WHERE apr.run_code = :aggregation_run_code
      AND dps.signal_version = :signal_version

    UNION ALL
    SELECT 'hidden_gem_candidate', COUNT(*)::bigint
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope

    UNION ALL
    SELECT 'hidden_gem_selected', COUNT(*)::bigint
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
      AND hgc.is_selected = TRUE
    ORDER BY entity_name;
    """
    scoped_counts_df = read_df(scoped_counts_sql, params)

    scoped_counts = {str(r["entity_name"]): int(r["row_count"] or 0) for r in df_to_records(scoped_counts_df)}

    # ------------------------------------------------------------------
    # Distributions and coverage
    # ------------------------------------------------------------------
    sentiment_distribution_sql = f"""
    SELECT
        dms.sentiment_label,
        dms.sentiment_reliability_tier,
        COUNT(*)::bigint AS row_count,
        AVG(dms.sentiment_score)::numeric(10,5) AS avg_sentiment_score,
        AVG(dms.sentiment_confidence)::numeric(10,5) AS avg_sentiment_confidence
    FROM {qname(schema, 'dish_mention_sentiment')} dms
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = dms.ai_pipeline_run_id
    WHERE apr.run_code = :sentiment_run_code
    GROUP BY dms.sentiment_label, dms.sentiment_reliability_tier
    ORDER BY dms.sentiment_label, dms.sentiment_reliability_tier;
    """
    sentiment_distribution_df = read_df(sentiment_distribution_sql, params)

    signal_tiers_sql = f"""
    SELECT
        dps.evidence_tier,
        dps.aggregate_quality_tier,
        dps.is_rankable_candidate,
        COUNT(*)::bigint AS row_count,
        MIN(dps.mention_count)::bigint AS min_mentions,
        AVG(dps.mention_count)::numeric(10,4) AS avg_mentions,
        MAX(dps.mention_count)::bigint AS max_mentions
    FROM {qname(schema, 'dish_place_signal')} dps
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = dps.ai_pipeline_run_id
    WHERE apr.run_code = :aggregation_run_code
      AND dps.signal_version = :signal_version
    GROUP BY dps.evidence_tier, dps.aggregate_quality_tier, dps.is_rankable_candidate
    ORDER BY dps.is_rankable_candidate DESC, row_count DESC;
    """
    signal_tiers_df = read_df(signal_tiers_sql, params)

    ranking_tiers_sql = f"""
    SELECT
        hgc.hidden_gem_tier,
        hgc.is_selected,
        COUNT(*)::bigint AS row_count,
        MIN(hgc.hidden_gem_score)::numeric(10,5) AS min_score,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_score
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
    GROUP BY hgc.hidden_gem_tier, hgc.is_selected
    ORDER BY hgc.is_selected DESC, avg_score DESC;
    """
    ranking_tiers_df = read_df(ranking_tiers_sql, params)

    selected_coverage_sql = f"""
    SELECT
        COUNT(*)::bigint AS selected_candidates,
        COUNT(DISTINCT hgc.place_id)::bigint AS selected_places,
        COUNT(DISTINCT hgc.dish_id)::bigint AS selected_dishes,
        COUNT(DISTINCT hgc.neighborhood_id)::bigint AS selected_neighborhoods,
        COUNT(DISTINCT hgc.district_id)::bigint AS selected_districts,
        MIN(hgc.hidden_gem_score)::numeric(10,5) AS min_selected_score,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_selected_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_selected_score,
        SUM(CASE WHEN hgc.is_production_ready THEN 1 ELSE 0 END)::bigint AS production_ready_selected
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
      AND hgc.is_selected = TRUE;
    """
    selected_coverage_df = read_df(selected_coverage_sql, params)

    top_candidates_sql = f"""
    SELECT
        hgc.hidden_gem_selected_rank,
        hgc.hidden_gem_rank,
        hgc.hidden_gem_tier,
        hgc.hidden_gem_score,
        p.canonical_name AS place_name,
        p.address_text,
        d.display_name AS dish_display_name,
        d.canonical_name AS dish_canonical_name,
        n.official_name AS neighborhood_name,
        dist.official_name AS district_name,
        dps.mention_count,
        dps.review_count,
        dps.positive_ratio,
        dps.negative_ratio,
        dps.avg_sentiment_confidence,
        dps.evidence_tier,
        dps.aggregate_quality_tier,
        hgc.ranking_explanation,
        hgc.ranking_config_json ->> 'artifact_ranking_scope' AS artifact_ranking_scope
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    JOIN {qname(schema, 'place')} p
        ON p.place_id = hgc.place_id
    JOIN {qname(schema, 'dish')} d
        ON d.dish_id = hgc.dish_id
    LEFT JOIN {qname(schema, 'dish_place_signal')} dps
        ON dps.dish_place_signal_id = hgc.dish_place_signal_id
    LEFT JOIN {qname(schema, 'neighborhood')} n
        ON n.neighborhood_id = hgc.neighborhood_id
    LEFT JOIN {qname(schema, 'district')} dist
        ON dist.district_id = hgc.district_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
      AND hgc.is_selected = TRUE
    ORDER BY hgc.hidden_gem_selected_rank NULLS LAST, hgc.hidden_gem_score DESC
    LIMIT :top_n;
    """
    top_candidates_df = read_df(top_candidates_sql, params)

    top_dishes_sql = f"""
    SELECT
        d.display_name AS dish_name,
        d.dish_family,
        COUNT(*)::bigint AS selected_count,
        COUNT(DISTINCT hgc.place_id)::bigint AS selected_places,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_score
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    JOIN {qname(schema, 'dish')} d
        ON d.dish_id = hgc.dish_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
      AND hgc.is_selected = TRUE
    GROUP BY d.display_name, d.dish_family
    ORDER BY selected_count DESC, max_score DESC
    LIMIT :top_n;
    """
    top_dishes_df = read_df(top_dishes_sql, params)

    top_districts_sql = f"""
    SELECT
        dist.official_name AS district_name,
        COUNT(*)::bigint AS selected_count,
        COUNT(DISTINCT hgc.place_id)::bigint AS selected_places,
        COUNT(DISTINCT hgc.dish_id)::bigint AS selected_dishes,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_score
    FROM {qname(schema, 'hidden_gem_candidate')} hgc
    JOIN {qname(schema, 'ai_pipeline_run')} apr
        ON apr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
    LEFT JOIN {qname(schema, 'district')} dist
        ON dist.district_id = hgc.district_id
    WHERE apr.run_code = :ranking_run_code
      AND hgc.ranking_version = :ranking_version
      AND hgc.ranking_scope = :db_ranking_scope
      AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
      AND hgc.is_selected = TRUE
    GROUP BY dist.official_name
    ORDER BY selected_count DESC, max_score DESC;
    """
    top_districts_df = read_df(top_districts_sql, params)

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    integrity_sql = f"""
    WITH
    mention_run AS (
        SELECT ai_pipeline_run_id FROM {qname(schema, 'ai_pipeline_run')} WHERE run_code = :mention_run_code
    ),
    sentiment_run AS (
        SELECT ai_pipeline_run_id FROM {qname(schema, 'ai_pipeline_run')} WHERE run_code = :sentiment_run_code
    ),
    aggregation_run AS (
        SELECT ai_pipeline_run_id FROM {qname(schema, 'ai_pipeline_run')} WHERE run_code = :aggregation_run_code
    ),
    ranking_run AS (
        SELECT ai_pipeline_run_id FROM {qname(schema, 'ai_pipeline_run')} WHERE run_code = :ranking_run_code
    ),
    scoped_mentions AS (
        SELECT dm.*
        FROM {qname(schema, 'dish_mention')} dm
        JOIN mention_run mr ON mr.ai_pipeline_run_id = dm.ai_pipeline_run_id
    ),
    scoped_sentiments AS (
        SELECT dms.*
        FROM {qname(schema, 'dish_mention_sentiment')} dms
        JOIN sentiment_run sr ON sr.ai_pipeline_run_id = dms.ai_pipeline_run_id
    ),
    scoped_signals AS (
        SELECT dps.*
        FROM {qname(schema, 'dish_place_signal')} dps
        JOIN aggregation_run ar ON ar.ai_pipeline_run_id = dps.ai_pipeline_run_id
        WHERE dps.signal_version = :signal_version
    ),
    scoped_ranking AS (
        SELECT hgc.*
        FROM {qname(schema, 'hidden_gem_candidate')} hgc
        JOIN ranking_run rr ON rr.ai_pipeline_run_id = hgc.ai_pipeline_run_id
        WHERE hgc.ranking_version = :ranking_version
          AND hgc.ranking_scope = :db_ranking_scope
          AND COALESCE(hgc.ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope
    )
    SELECT
        (SELECT COUNT(*) FROM scoped_mentions sm LEFT JOIN {qname(schema, 'review')} r ON r.review_id = sm.review_id WHERE r.review_id IS NULL)::bigint AS orphan_mentions_review,
        (SELECT COUNT(*) FROM scoped_mentions sm LEFT JOIN {qname(schema, 'place')} p ON p.place_id = sm.place_id WHERE p.place_id IS NULL)::bigint AS orphan_mentions_place,
        (SELECT COUNT(*) FROM scoped_mentions sm LEFT JOIN {qname(schema, 'dish')} d ON d.dish_id = sm.dish_id WHERE sm.dish_id IS NOT NULL AND d.dish_id IS NULL)::bigint AS orphan_mentions_dish,
        (SELECT COUNT(*) FROM scoped_mentions sm LEFT JOIN scoped_sentiments ss ON ss.dish_mention_id = sm.dish_mention_id WHERE ss.dish_mention_id IS NULL)::bigint AS mentions_without_sentiment,
        (SELECT COUNT(*) FROM scoped_sentiments ss LEFT JOIN scoped_mentions sm ON sm.dish_mention_id = ss.dish_mention_id WHERE sm.dish_mention_id IS NULL)::bigint AS sentiments_without_scoped_mention,
        (SELECT COUNT(*) FROM scoped_sentiments ss WHERE ss.sentiment_label NOT IN ('positive', 'neutral', 'negative'))::bigint AS invalid_sentiment_labels,
        (SELECT COUNT(*) FROM scoped_signals sg LEFT JOIN {qname(schema, 'place')} p ON p.place_id = sg.place_id WHERE p.place_id IS NULL)::bigint AS orphan_signals_place,
        (SELECT COUNT(*) FROM scoped_signals sg LEFT JOIN {qname(schema, 'dish')} d ON d.dish_id = sg.dish_id WHERE d.dish_id IS NULL)::bigint AS orphan_signals_dish,
        (SELECT COUNT(*) FROM scoped_signals sg WHERE sg.mention_count < 0 OR sg.review_count < 0)::bigint AS invalid_signal_counts,
        (SELECT COUNT(*) FROM scoped_ranking sr LEFT JOIN {qname(schema, 'place')} p ON p.place_id = sr.place_id WHERE p.place_id IS NULL)::bigint AS orphan_ranking_place,
        (SELECT COUNT(*) FROM scoped_ranking sr LEFT JOIN {qname(schema, 'dish')} d ON d.dish_id = sr.dish_id WHERE d.dish_id IS NULL)::bigint AS orphan_ranking_dish,
        (SELECT COUNT(*) FROM scoped_ranking sr LEFT JOIN scoped_signals sg ON sg.dish_place_signal_id = sr.dish_place_signal_id WHERE sr.dish_place_signal_id IS NOT NULL AND sg.dish_place_signal_id IS NULL)::bigint AS ranking_without_scoped_signal,
        (SELECT COUNT(*) FROM scoped_ranking sr LEFT JOIN {qname(schema, 'neighborhood')} n ON n.neighborhood_id = sr.neighborhood_id WHERE sr.neighborhood_id IS NOT NULL AND n.neighborhood_id IS NULL)::bigint AS orphan_ranking_neighborhood,
        (SELECT COUNT(*) FROM scoped_ranking sr LEFT JOIN {qname(schema, 'district')} d ON d.district_id = sr.district_id WHERE sr.district_id IS NOT NULL AND d.district_id IS NULL)::bigint AS orphan_ranking_district,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.hidden_gem_score < 0 OR sr.hidden_gem_score > 100)::bigint AS ranking_score_out_of_range,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE AND (sr.hidden_gem_selected_rank IS NULL OR sr.hidden_gem_tier = 'not_selected'))::bigint AS selected_consistency_errors,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE AND sr.is_production_ready = TRUE)::bigint AS selected_marked_production_ready,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE AND sr.neighborhood_id IS NULL)::bigint AS selected_without_neighborhood,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE AND sr.district_id IS NULL)::bigint AS selected_without_district,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE AND sr.ranking_explanation IS NULL)::bigint AS selected_without_explanation,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.ranking_config_json ->> 'artifact_ranking_scope' <> :artifact_ranking_scope)::bigint AS wrong_artifact_scope,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.ranking_scope <> :db_ranking_scope)::bigint AS wrong_db_ranking_scope,
        (SELECT COUNT(*) FROM scoped_ranking sr WHERE sr.is_selected = TRUE)::bigint AS selected_count,
        (SELECT COUNT(DISTINCT sr.hidden_gem_selected_rank) FROM scoped_ranking sr WHERE sr.is_selected = TRUE)::bigint AS distinct_selected_ranks
    ;
    """
    integrity_df = read_df(integrity_sql, params)

    # ------------------------------------------------------------------
    # Optional view checks
    # ------------------------------------------------------------------
    view_checks: dict[str, Any] = {}
    view_detail_exists = bool(optional_views_df.loc[optional_views_df["object_name"] == "vw_ai_hidden_gem_candidate_detail", "exists"].iloc[0])
    view_signals_exists = bool(optional_views_df.loc[optional_views_df["object_name"] == "vw_ai_dish_place_signals", "exists"].iloc[0])
    view_mentions_exists = bool(optional_views_df.loc[optional_views_df["object_name"] == "vw_ai_dish_mentions_with_sentiment", "exists"].iloc[0])

    if view_detail_exists:
        view_candidates_sql = f"""
        SELECT
            COUNT(*)::bigint AS view_ranking_rows,
            SUM(CASE WHEN is_selected THEN 1 ELSE 0 END)::bigint AS view_selected_rows
        FROM {qname(schema, 'vw_ai_hidden_gem_candidate_detail')}
        WHERE ai_run_code = :ranking_run_code
          AND ranking_version = :ranking_version
          AND ranking_scope = :db_ranking_scope
          AND COALESCE(ranking_config_json ->> 'artifact_ranking_scope', '') = :artifact_ranking_scope;
        """
        view_checks["vw_ai_hidden_gem_candidate_detail"] = df_to_records(read_df(view_candidates_sql, params))

    if view_signals_exists:
        view_signals_sql = f"""
        SELECT COUNT(*)::bigint AS view_signal_rows
        FROM {qname(schema, 'vw_ai_dish_place_signals')}
        WHERE ai_run_code = :aggregation_run_code
          AND signal_version = :signal_version;
        """
        view_checks["vw_ai_dish_place_signals"] = df_to_records(read_df(view_signals_sql, params))

    if view_mentions_exists:
        view_mentions_sql = f"""
        SELECT COUNT(*)::bigint AS view_mention_sentiment_rows
        FROM {qname(schema, 'vw_ai_dish_mentions_with_sentiment')}
        WHERE sentiment_ai_run_code = :sentiment_run_code;
        """
        try:
            view_checks["vw_ai_dish_mentions_with_sentiment"] = df_to_records(read_df(view_mentions_sql, params))
        except Exception as exc:
            view_checks["vw_ai_dish_mentions_with_sentiment_error"] = str(exc)

    # ------------------------------------------------------------------
    # Checks, errors, warnings
    # ------------------------------------------------------------------
    integrity = integrity_df.iloc[0].to_dict() if not integrity_df.empty else {}
    selected_coverage = selected_coverage_df.iloc[0].to_dict() if not selected_coverage_df.empty else {}

    expected_counts = {
        "dish_catalog": args.expected_dishes,
        "dish_alias": args.expected_aliases,
        "dish_mention": args.expected_mentions,
        "dish_mention_sentiment": args.expected_sentiments,
        "dish_place_signal": args.expected_signals,
        "hidden_gem_candidate": args.expected_ranking_candidates,
        "hidden_gem_selected": args.expected_selected,
    }

    count_checks = {
        f"{name}_matches_expected": (scoped_counts.get(name, 0) == expected)
        for name, expected in expected_counts.items()
        if expected is not None and not args.skip_expected_counts
    }

    checks = {
        "required_tables_exist": bool(required_tables_df["exists"].all()),
        "required_model_versions_exist": bool(model_versions_df["exists_in_db"].all()) if not model_versions_df.empty else False,
        "required_ai_runs_exist": bool(pipeline_runs_df["exists_in_db"].all()) if not pipeline_runs_df.empty else False,
        "all_ai_runs_completed": bool((pipeline_runs_df["status"] == "completed").all()) if not pipeline_runs_df.empty else False,
        "has_dishes": scoped_counts.get("dish_catalog", 0) > 0,
        "has_aliases": scoped_counts.get("dish_alias", 0) > 0,
        "has_mentions": scoped_counts.get("dish_mention", 0) > 0,
        "has_sentiments": scoped_counts.get("dish_mention_sentiment", 0) > 0,
        "has_signals": scoped_counts.get("dish_place_signal", 0) > 0,
        "has_ranking_candidates": scoped_counts.get("hidden_gem_candidate", 0) > 0,
        "has_selected_candidates": scoped_counts.get("hidden_gem_selected", 0) > 0,
        "no_orphan_mentions_review": int(integrity.get("orphan_mentions_review", 0) or 0) == 0,
        "no_orphan_mentions_place": int(integrity.get("orphan_mentions_place", 0) or 0) == 0,
        "no_orphan_mentions_dish": int(integrity.get("orphan_mentions_dish", 0) or 0) == 0,
        "no_mentions_without_sentiment": int(integrity.get("mentions_without_sentiment", 0) or 0) == 0,
        "no_sentiments_without_scoped_mention": int(integrity.get("sentiments_without_scoped_mention", 0) or 0) == 0,
        "no_invalid_sentiment_labels": int(integrity.get("invalid_sentiment_labels", 0) or 0) == 0,
        "no_orphan_signals_place": int(integrity.get("orphan_signals_place", 0) or 0) == 0,
        "no_orphan_signals_dish": int(integrity.get("orphan_signals_dish", 0) or 0) == 0,
        "no_invalid_signal_counts": int(integrity.get("invalid_signal_counts", 0) or 0) == 0,
        "no_orphan_ranking_place": int(integrity.get("orphan_ranking_place", 0) or 0) == 0,
        "no_orphan_ranking_dish": int(integrity.get("orphan_ranking_dish", 0) or 0) == 0,
        "no_ranking_without_scoped_signal": int(integrity.get("ranking_without_scoped_signal", 0) or 0) == 0,
        "no_orphan_ranking_neighborhood": int(integrity.get("orphan_ranking_neighborhood", 0) or 0) == 0,
        "no_orphan_ranking_district": int(integrity.get("orphan_ranking_district", 0) or 0) == 0,
        "score_in_0_100": int(integrity.get("ranking_score_out_of_range", 0) or 0) == 0,
        "selected_consistency_ok": int(integrity.get("selected_consistency_errors", 0) or 0) == 0,
        "selected_not_production_ready": int(integrity.get("selected_marked_production_ready", 0) or 0) == 0,
        "selected_have_neighborhood": int(integrity.get("selected_without_neighborhood", 0) or 0) == 0,
        "selected_have_district": int(integrity.get("selected_without_district", 0) or 0) == 0,
        "selected_have_explanation": int(integrity.get("selected_without_explanation", 0) or 0) == 0,
        "artifact_scope_ok": int(integrity.get("wrong_artifact_scope", 0) or 0) == 0,
        "db_ranking_scope_ok": int(integrity.get("wrong_db_ranking_scope", 0) or 0) == 0,
        "selected_global_ranks_unique": int(integrity.get("selected_count", 0) or 0) == int(integrity.get("distinct_selected_ranks", 0) or 0),
        "selected_district_coverage_ok": int(selected_coverage.get("selected_districts", 0) or 0) >= args.expected_min_districts_selected,
        "selected_neighborhood_coverage_ok": int(selected_coverage.get("selected_neighborhoods", 0) or 0) >= args.expected_min_neighborhoods_selected,
        **count_checks,
    }

    errors: list[str] = []
    warnings: list[str] = []

    # Critical checks that should fail the script.
    critical_check_keys = [
        "required_tables_exist",
        "required_model_versions_exist",
        "required_ai_runs_exist",
        "all_ai_runs_completed",
        "has_dishes",
        "has_aliases",
        "has_mentions",
        "has_sentiments",
        "has_signals",
        "has_ranking_candidates",
        "has_selected_candidates",
        "no_orphan_mentions_review",
        "no_orphan_mentions_place",
        "no_orphan_mentions_dish",
        "no_mentions_without_sentiment",
        "no_sentiments_without_scoped_mention",
        "no_invalid_sentiment_labels",
        "no_orphan_signals_place",
        "no_orphan_signals_dish",
        "no_invalid_signal_counts",
        "no_orphan_ranking_place",
        "no_orphan_ranking_dish",
        "no_ranking_without_scoped_signal",
        "no_orphan_ranking_neighborhood",
        "no_orphan_ranking_district",
        "score_in_0_100",
        "selected_consistency_ok",
        "selected_not_production_ready",
        "selected_have_neighborhood",
        "selected_have_district",
        "selected_have_explanation",
        "artifact_scope_ok",
        "db_ranking_scope_ok",
        "selected_global_ranks_unique",
    ]

    if not args.skip_expected_counts:
        critical_check_keys.extend(count_checks.keys())

    for key in critical_check_keys:
        if not bool(checks.get(key, False)):
            errors.append(f"Check failed: {key}")

    if not checks.get("selected_district_coverage_ok", False):
        warnings.append(
            f"Selected district coverage below expected minimum: "
            f"{selected_coverage.get('selected_districts', 0)} < {args.expected_min_districts_selected}"
        )

    if not checks.get("selected_neighborhood_coverage_ok", False):
        warnings.append(
            f"Selected neighborhood coverage below expected minimum: "
            f"{selected_coverage.get('selected_neighborhoods', 0)} < {args.expected_min_neighborhoods_selected}"
        )

    # View checks are useful but not critical: some environments may not have 08_ai_views.sql loaded yet.
    if not optional_views_df["exists"].all():
        missing_views = optional_views_df.loc[~optional_views_df["exists"], "object_name"].tolist()
        warnings.append(f"Some optional AI views are missing: {missing_views}")

    report = {
        "schema": schema,
        "version": "check_sevilla_ai_pilot_loaded_v1",
        "db_ranking_scope": args.db_ranking_scope,
        "artifact_ranking_scope": args.artifact_ranking_scope,
        "ranking_version": args.ranking_version,
        "signal_version": args.signal_version,
        "required_tables": df_to_records(required_tables_df),
        "optional_views": df_to_records(optional_views_df),
        "model_versions": df_to_records(model_versions_df),
        "pipeline_runs": df_to_records(pipeline_runs_df),
        "scoped_counts": df_to_records(scoped_counts_df),
        "expected_counts": to_builtin(expected_counts),
        "sentiment_distribution": df_to_records(sentiment_distribution_df),
        "signal_tiers": df_to_records(signal_tiers_df),
        "ranking_tiers": df_to_records(ranking_tiers_df),
        "selected_coverage": df_to_records(selected_coverage_df),
        "top_candidates": df_to_records(top_candidates_df),
        "top_dishes_selected": df_to_records(top_dishes_df),
        "selected_by_district": df_to_records(top_districts_df),
        "integrity": df_to_records(integrity_df),
        "view_checks": view_checks,
        "checks": to_builtin(checks),
        "errors": errors,
        "warnings": warnings,
        "ready_for_sevilla_pilot_queries": len(errors) == 0,
    }

    # ------------------------------------------------------------------
    # Human-readable output
    # ------------------------------------------------------------------
    print_section("1. Required tables")
    print(required_tables_df.to_string(index=False))

    print_section("2. Optional AI views")
    print(optional_views_df.to_string(index=False))

    print_section("3. Required model versions")
    print(model_versions_df.to_string(index=False))

    print_section("4. Required AI pipeline runs")
    print(pipeline_runs_df.to_string(index=False))

    print_section("5. Scoped counts")
    print(scoped_counts_df.to_string(index=False))

    print_section("6. Ranking tiers")
    print(ranking_tiers_df.to_string(index=False))

    print_section("7. Selected coverage")
    print(selected_coverage_df.to_string(index=False))

    print_section(f"8. Top {args.top_n} selected Hidden Gems")
    print(top_candidates_df.to_string(index=False))

    print_section("9. Integrity")
    print(integrity_df.to_string(index=False))

    print_section("10. Checks")
    print(json.dumps(to_builtin(checks), indent=2, ensure_ascii=False, allow_nan=False))

    print_section("11. Decision")
    print("ready_for_sevilla_pilot_queries:", report["ready_for_sevilla_pilot_queries"])
    print("errors:", errors)
    print("warnings:", warnings)

    return report


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Sevilla AI pilot data loaded in PostgreSQL.")

    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--top-n", type=int, default=30)

    parser.add_argument("--catalog-run-code", default=DEFAULT_CATALOG_RUN_CODE)
    parser.add_argument("--mention-run-code", default=DEFAULT_MENTION_RUN_CODE)
    parser.add_argument("--sentiment-run-code", default=DEFAULT_SENTIMENT_RUN_CODE)
    parser.add_argument("--aggregation-run-code", default=DEFAULT_AGGREGATION_RUN_CODE)
    parser.add_argument("--ranking-run-code", default=DEFAULT_RANKING_RUN_CODE)

    parser.add_argument("--signal-version", default=DEFAULT_SIGNAL_VERSION)
    parser.add_argument("--ranking-version", default=DEFAULT_RANKING_VERSION)
    parser.add_argument("--db-ranking-scope", default=DEFAULT_DB_RANKING_SCOPE)
    parser.add_argument("--artifact-ranking-scope", default=DEFAULT_ARTIFACT_RANKING_SCOPE)

    parser.add_argument("--expected-dishes", type=int, default=DEFAULT_EXPECTED_DISHES)
    parser.add_argument("--expected-aliases", type=int, default=DEFAULT_EXPECTED_ALIASES)
    parser.add_argument("--expected-mentions", type=int, default=DEFAULT_EXPECTED_MENTIONS)
    parser.add_argument("--expected-sentiments", type=int, default=DEFAULT_EXPECTED_SENTIMENTS)
    parser.add_argument("--expected-signals", type=int, default=DEFAULT_EXPECTED_SIGNALS)
    parser.add_argument("--expected-ranking-candidates", type=int, default=DEFAULT_EXPECTED_RANKING_CANDIDATES)
    parser.add_argument("--expected-selected", type=int, default=DEFAULT_EXPECTED_SELECTED)
    parser.add_argument("--expected-min-districts-selected", type=int, default=DEFAULT_EXPECTED_MIN_DISTRICTS_SELECTED)
    parser.add_argument("--expected-min-neighborhoods-selected", type=int, default=DEFAULT_EXPECTED_MIN_NEIGHBORHOODS_SELECTED)

    parser.add_argument(
        "--skip-expected-counts",
        action="store_true",
        help="Do not fail if scoped counts differ from the current v1 expected counts.",
    )
    parser.add_argument(
        "--no-fail-on-error",
        action="store_true",
        help="Always exit with code 0, even if checks fail. Useful while debugging.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(args)

    if args.report_path is not None:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        with args.report_path.open("w", encoding="utf-8") as f:
            json.dump(to_builtin(report), f, indent=2, ensure_ascii=False, allow_nan=False)
        print("\nReport saved to:", args.report_path)

    if report.get("errors") and not args.no_fail_on_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
