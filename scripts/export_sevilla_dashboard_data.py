"""Export clean dashboard datasets for the Sevilla Hidden Gems AI pilot.

This script reads PostgreSQL AI views created by 08_ai_views.sql and exports a
stable set of CSV/JSON files intended for a Streamlit/BI dashboard.

It does not modify the database.

Recommended execution from repository root:

    python -m scripts.export_sevilla_dashboard_data `
      --output-dir data/artifacts/ai/sevilla/dashboard `
      --expected-selected 150 `
      --include-mentions `
      --include-full-review-text `
      --strict

By default the database ranking_scope is 'other' because the current DDL
constraint does not allow 'sevilla_pilot' as a native enum/check value. The
original artifact scope is preserved in ranking_config_json:

    ranking_config_json->>'artifact_ranking_scope' = 'sevilla_pilot'

Main outputs:

    dashboard_metadata.json
    kpi_summary.json
    candidates_all.csv
    candidates_detail.csv
    top_global.csv
    top_by_district.csv
    top_by_neighborhood.csv
    top_by_dish.csv
    district_summary.csv
    neighborhood_summary.csv
    dish_summary.csv
    place_summary.csv
    tier_summary.csv
    quality_summary.csv
    filter_options.json
    data_contract.json
    dashboard_export_summary.json
    mention_examples.csv              # optional with --include-mentions
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from sqlalchemy import text

from src.db.database import engine


# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_DB_RANKING_SCOPE = "other"
DEFAULT_ARTIFACT_RANKING_SCOPE = "sevilla_pilot"
DEFAULT_RANKING_VERSION = "sevilla_hidden_gems_ranking_pilot_v1"
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/dashboard")

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)

TIER_ORDER = {
    "top_hidden_gem": 4,
    "strong_hidden_gem": 3,
    "promising_hidden_gem": 2,
    "exploratory_hidden_gem": 1,
    "not_selected": 0,
}

DASHBOARD_SELECTED_COLUMNS = [
    "hidden_gem_candidate_id",
    "hidden_gem_selected_rank",
    "hidden_gem_rank",
    "hidden_gem_tier",
    "hidden_gem_tier_order",
    "hidden_gem_score",
    "hidden_gem_score_base",
    "is_selected",
    "is_production_ready",
    "human_review_status",
    "place_id",
    "place_name",
    "address_text",
    "latitude",
    "longitude",
    "dish_id",
    "dish_name",
    "dish_display_name",
    "dish_normalized_name",
    "district_id",
    "district_name",
    "neighborhood_id",
    "neighborhood_name",
    "dish_place_signal_id",
    "signal_version",
    "mention_count",
    "review_count",
    "positive_mentions",
    "neutral_mentions",
    "negative_mentions",
    "positive_ratio",
    "negative_ratio",
    "avg_sentiment_confidence",
    "avg_rating",
    "total_signal_weight",
    "confidence_weighted_sentiment",
    "bayesian_sentiment_score",
    "reliability_high_ratio",
    "aggregate_quality_tier",
    "evidence_tier",
    "is_rankable_candidate",
    "local_sentiment_component",
    "evidence_component",
    "confidence_component",
    "positive_balance_component",
    "rarity_component",
    "local_outperformance_component",
    "hiddenness_component",
    "negative_penalty_factor",
    "noise_penalty_factor",
    "low_evidence_penalty_factor",
    "ranking_explanation",
    "ranking_version",
    "ranking_scope",
    "artifact_ranking_scope",
]

TOP_GLOBAL_COLUMNS = [
    "hidden_gem_selected_rank",
    "hidden_gem_tier",
    "hidden_gem_score",
    "place_name",
    "dish_display_name",
    "district_name",
    "neighborhood_name",
    "mention_count",
    "review_count",
    "positive_ratio",
    "negative_ratio",
    "avg_sentiment_confidence",
    "evidence_tier",
    "aggregate_quality_tier",
    "ranking_explanation",
    "latitude",
    "longitude",
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def validate_uuid(value: str | None, arg_name: str) -> None:
    if value is None:
        return
    if not UUID_RE.match(value):
        raise ValueError(f"{arg_name} must be a UUID. Received: {value!r}")


def qname(schema: str, name: str) -> str:
    return f'"{validate_schema_name(schema)}"."{name}"'


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


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
        if pd.isna(value):
            return None
    except Exception:
        pass

    return value


def df_to_records(df: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    out = df.head(limit) if limit is not None else df
    return [to_builtin(row) for row in out.to_dict(orient="records")]


def coerce_bool_series(series: pd.Series) -> pd.Series:
    if series.empty:
        return series.astype(bool)
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "t", "yes", "y"])


def coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def safe_columns(df: pd.DataFrame, columns: list[str]) -> list[str]:
    return [col for col in columns if col in df.columns]


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")


def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


# -----------------------------------------------------------------------------
# Database loading
# -----------------------------------------------------------------------------


def validate_required_view_columns(schema: str) -> dict[str, Any]:
    """Return available columns for the two AI views used by the exporter."""
    schema = validate_schema_name(schema)

    sql = """
        SELECT table_name, column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name IN (
              'vw_ai_hidden_gem_candidate_detail',
              'vw_ai_dish_mentions_with_sentiment'
          )
        ORDER BY table_name, ordinal_position;
    """
    cols_df = read_df(sql, {"schema": schema})

    available: dict[str, list[str]] = {}
    for table_name, group in cols_df.groupby("table_name"):
        available[str(table_name)] = [str(c) for c in group["column_name"].tolist()]

    candidate_required = [
        "hidden_gem_candidate_id",
        "hidden_gem_score",
        "hidden_gem_tier",
        "is_selected",
        "place_id",
        "place_name",
        "dish_id",
        "dish_name",
        "ranking_scope",
        "ranking_config_json",
    ]
    candidate_cols = available.get("vw_ai_hidden_gem_candidate_detail", [])
    missing_candidate = [c for c in candidate_required if c not in candidate_cols]

    return {
        "available_columns": available,
        "missing_candidate_required_columns": missing_candidate,
        "candidate_view_available": bool(candidate_cols),
        "mentions_view_available": bool(available.get("vw_ai_dish_mentions_with_sentiment", [])),
    }


def load_candidates(args: argparse.Namespace) -> pd.DataFrame:
    schema = validate_schema_name(args.schema)
    view_name = qname(schema, "vw_ai_hidden_gem_candidate_detail")

    where_parts = [
        "ranking_scope = :db_ranking_scope",
        "COALESCE(ranking_config_json->>'artifact_ranking_scope', '') = :artifact_ranking_scope",
    ]
    params: dict[str, Any] = {
        "db_ranking_scope": args.db_ranking_scope,
        "artifact_ranking_scope": args.artifact_ranking_scope,
    }

    if args.ranking_version:
        where_parts.append("ranking_version = :ranking_version")
        params["ranking_version"] = args.ranking_version

    if args.min_score is not None:
        where_parts.append("hidden_gem_score >= :min_score")
        params["min_score"] = args.min_score

    sql = f"""
        SELECT
            *,
            ranking_config_json->>'artifact_ranking_scope' AS artifact_ranking_scope
        FROM {view_name}
        WHERE {' AND '.join(where_parts)}
        ORDER BY
            is_selected DESC,
            hidden_gem_selected_rank NULLS LAST,
            hidden_gem_score DESC,
            mention_count DESC NULLS LAST,
            review_count DESC NULLS LAST,
            place_name,
            dish_name;
    """

    df = read_df(sql, params)
    if df.empty:
        return df

    for col in ["is_selected", "is_production_ready", "is_rankable_candidate"]:
        if col in df.columns:
            df[col] = coerce_bool_series(df[col])

    numeric_cols = [
        "hidden_gem_selected_rank",
        "hidden_gem_rank",
        "hidden_gem_score",
        "hidden_gem_score_base",
        "latitude",
        "longitude",
        "mention_count",
        "review_count",
        "positive_mentions",
        "neutral_mentions",
        "negative_mentions",
        "positive_ratio",
        "negative_ratio",
        "avg_sentiment_confidence",
        "total_signal_weight",
        "avg_rating",
        "confidence_weighted_sentiment",
        "bayesian_sentiment_score",
        "reliability_high_ratio",
        "local_sentiment_component",
        "evidence_component",
        "confidence_component",
        "positive_balance_component",
        "rarity_component",
        "local_outperformance_component",
        "hiddenness_component",
        "negative_penalty_factor",
        "noise_penalty_factor",
        "low_evidence_penalty_factor",
    ]
    df = coerce_numeric(df, numeric_cols)

    if "hidden_gem_tier" in df.columns:
        df["hidden_gem_tier_order"] = df["hidden_gem_tier"].map(TIER_ORDER).fillna(0).astype(int)

    if "dish_display_name" not in df.columns and "dish_name" in df.columns:
        df["dish_display_name"] = df["dish_name"]

    if "dish_normalized_name" not in df.columns and "dish_name" in df.columns:
        df["dish_normalized_name"] = df["dish_name"].astype(str).str.lower().str.strip()

    return df


# -----------------------------------------------------------------------------
# Aggregations
# -----------------------------------------------------------------------------


def get_selected_df(candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df.empty or "is_selected" not in candidates_df.columns:
        return pd.DataFrame()

    selected = candidates_df[candidates_df["is_selected"]].copy()
    sort_cols = [c for c in ["hidden_gem_selected_rank", "hidden_gem_score", "mention_count", "review_count"] if c in selected.columns]
    ascending = [True if c == "hidden_gem_selected_rank" else False for c in sort_cols]
    if sort_cols:
        selected = selected.sort_values(sort_cols, ascending=ascending, na_position="last")
    return selected.reset_index(drop=True)


def top_global(selected_df: pd.DataFrame, limit: int | None = None) -> pd.DataFrame:
    if selected_df.empty:
        return selected_df
    sort_cols = [c for c in ["hidden_gem_selected_rank", "hidden_gem_score", "mention_count", "review_count"] if c in selected_df.columns]
    ascending = [True if c == "hidden_gem_selected_rank" else False for c in sort_cols]
    out = selected_df.sort_values(sort_cols, ascending=ascending, na_position="last").reset_index(drop=True)
    return out.head(limit) if limit is not None else out


def top_by_group(df: pd.DataFrame, group_cols: list[str], rank_col_name: str, per_group: int | None) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    available_group_cols = [c for c in group_cols if c in df.columns]
    if not available_group_cols:
        return pd.DataFrame()

    sort_cols = available_group_cols + ["hidden_gem_score", "hidden_gem_selected_rank"]
    ascending = [True] * len(available_group_cols) + [False, True]
    ordered = df.sort_values(sort_cols, ascending=ascending, na_position="last").copy()
    ordered[rank_col_name] = ordered.groupby(available_group_cols, dropna=False).cumcount() + 1
    if per_group is not None:
        ordered = ordered[ordered[rank_col_name] <= per_group]
    return ordered.reset_index(drop=True)


def summarize_by_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    available_group_cols = [c for c in group_cols if c in df.columns]
    if not available_group_cols:
        return pd.DataFrame()

    def tier_count(tier: str):
        return lambda s: int((s == tier).sum())

    grouped = (
        df.groupby(available_group_cols, dropna=False)
        .agg(
            selected_count=("hidden_gem_candidate_id", "count"),
            selected_places=("place_id", "nunique"),
            selected_dishes=("dish_id", "nunique"),
            selected_districts=("district_id", "nunique") if "district_id" in df.columns else ("place_id", "nunique"),
            selected_neighborhoods=("neighborhood_id", "nunique") if "neighborhood_id" in df.columns else ("place_id", "nunique"),
            top_hidden_gem_count=("hidden_gem_tier", tier_count("top_hidden_gem")),
            strong_hidden_gem_count=("hidden_gem_tier", tier_count("strong_hidden_gem")),
            promising_hidden_gem_count=("hidden_gem_tier", tier_count("promising_hidden_gem")),
            exploratory_hidden_gem_count=("hidden_gem_tier", tier_count("exploratory_hidden_gem")),
            avg_score=("hidden_gem_score", "mean"),
            min_score=("hidden_gem_score", "min"),
            max_score=("hidden_gem_score", "max"),
            total_mentions=("mention_count", "sum"),
            total_reviews=("review_count", "sum"),
            avg_positive_ratio=("positive_ratio", "mean"),
            avg_negative_ratio=("negative_ratio", "mean"),
        )
        .reset_index()
    )

    for col in ["avg_score", "min_score", "max_score", "avg_positive_ratio", "avg_negative_ratio"]:
        if col in grouped.columns:
            grouped[col] = grouped[col].round(5)

    return grouped.sort_values(["max_score", "selected_count"], ascending=[False, False]).reset_index(drop=True)


def summarize_tiers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    tier_summary = (
        df.groupby("hidden_gem_tier", dropna=False)
        .agg(
            candidate_count=("hidden_gem_candidate_id", "count"),
            place_count=("place_id", "nunique"),
            dish_count=("dish_id", "nunique"),
            neighborhood_count=("neighborhood_id", "nunique") if "neighborhood_id" in df.columns else ("place_id", "nunique"),
            district_count=("district_id", "nunique") if "district_id" in df.columns else ("place_id", "nunique"),
            avg_score=("hidden_gem_score", "mean"),
            min_score=("hidden_gem_score", "min"),
            max_score=("hidden_gem_score", "max"),
            total_mentions=("mention_count", "sum"),
            total_reviews=("review_count", "sum"),
        )
        .reset_index()
    )
    tier_summary["tier_order"] = tier_summary["hidden_gem_tier"].map(TIER_ORDER).fillna(0).astype(int)
    for col in ["avg_score", "min_score", "max_score"]:
        tier_summary[col] = tier_summary[col].round(5)
    return tier_summary.sort_values("tier_order", ascending=False).reset_index(drop=True)


def summarize_places(selected_df: pd.DataFrame) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()

    group_cols = safe_columns(selected_df, ["place_id", "place_name", "address_text", "district_name", "neighborhood_name", "latitude", "longitude"])
    if not group_cols:
        return pd.DataFrame()

    base = summarize_by_group(selected_df, group_cols)
    if base.empty:
        return base

    best = top_by_group(selected_df, ["place_id"], "rank_in_place", per_group=1)
    best_cols = safe_columns(best, ["place_id", "dish_display_name", "hidden_gem_score", "hidden_gem_tier", "ranking_explanation"])
    if "place_id" in best_cols:
        best = best[best_cols].rename(
            columns={
                "dish_display_name": "best_dish_name",
                "hidden_gem_score": "best_dish_score",
                "hidden_gem_tier": "best_dish_tier",
                "ranking_explanation": "best_dish_explanation",
            }
        )
        base = base.merge(best, on="place_id", how="left")

    return base.sort_values(["max_score", "selected_count"], ascending=[False, False]).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Mention examples
# -----------------------------------------------------------------------------


def load_mention_examples(
    schema: str,
    selected_df: pd.DataFrame,
    max_candidates: int,
    examples_per_candidate: int,
    include_full_review_text: bool,
) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()

    schema = validate_schema_name(schema)
    view_name = qname(schema, "vw_ai_dish_mentions_with_sentiment")
    top_pairs = selected_df[
        safe_columns(selected_df, [
            "hidden_gem_candidate_id",
            "hidden_gem_selected_rank",
            "place_id",
            "place_name",
            "dish_id",
            "dish_display_name",
        ])
    ].drop_duplicates(subset=["place_id", "dish_id"]).head(max_candidates)

    if top_pairs.empty:
        return pd.DataFrame()

    base_columns = [
        "place_id",
        "place_name",
        "dish_id",
        "dish_name",
        "review_id",
        "rating_value",
        "sentiment_label",
        "sentiment_score",
        "sentiment_confidence",
        "sentiment_reliability_tier",
        "sentiment_reason",
        "mention_text",
        "context_sentence",
    ]
    if include_full_review_text:
        base_columns.append("review_text_raw")

    select_columns = ",\n            ".join(base_columns)
    sql = f"""
        SELECT
            {select_columns}
        FROM {view_name}
        WHERE place_id = CAST(:place_id AS uuid)
          AND dish_id = CAST(:dish_id AS uuid)
        ORDER BY
            sentiment_confidence DESC NULLS LAST,
            ABS(COALESCE(sentiment_score, 0)) DESC,
            rating_value DESC NULLS LAST
        LIMIT :limit;
    """

    frames: list[pd.DataFrame] = []
    for _, pair in top_pairs.iterrows():
        df = read_df(
            sql,
            {
                "place_id": str(pair["place_id"]),
                "dish_id": str(pair["dish_id"]),
                "limit": examples_per_candidate,
            },
        )
        if df.empty:
            continue
        df.insert(0, "hidden_gem_candidate_id", pair.get("hidden_gem_candidate_id"))
        df.insert(1, "hidden_gem_selected_rank", pair.get("hidden_gem_selected_rank"))
        df.insert(2, "candidate_place_name", pair.get("place_name"))
        df.insert(3, "candidate_dish_display_name", pair.get("dish_display_name"))
        if "review_text_raw" in df.columns:
            df["review_text_preview"] = df["review_text_raw"].astype(str).str.replace("\n", " ", regex=False).str.slice(0, 400)
        frames.append(df)

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out = coerce_numeric(out, ["rating_value", "sentiment_score", "sentiment_confidence"])
    return out


# -----------------------------------------------------------------------------
# Dashboard JSON builders
# -----------------------------------------------------------------------------


def build_metadata(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "project_name": "Hidden Gems",
        "dashboard_name": "Hidden Gems Sevilla — Piloto IA",
        "dashboard_scope": args.artifact_ranking_scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranking_version": args.ranking_version,
        "db_ranking_scope": args.db_ranking_scope,
        "artifact_ranking_scope": args.artifact_ranking_scope,
        "is_production_ready": False,
        "source": "Google Places Reviews",
        "storage_mode": "exported_csv_json",
        "notes": [
            "Piloto basado en reseñas de Google Places asociadas a locales reales de Sevilla.",
            "No representa todavía un ranking productivo final.",
            "Los candidatos están marcados como is_production_ready = false.",
            "Google Places no devuelve necesariamente todas las reseñas históricas de cada local.",
            "Los resultados deben revisarse manualmente antes de considerarse producción.",
        ],
    }


def build_kpis(selected_df: pd.DataFrame, all_df: pd.DataFrame) -> dict[str, Any]:
    tier_counts = selected_df["hidden_gem_tier"].value_counts().to_dict() if not selected_df.empty else {}
    return {
        "total_candidates_scored": int(len(all_df)),
        "selected_candidates": int(len(selected_df)),
        "selected_places": int(selected_df["place_id"].nunique()) if "place_id" in selected_df.columns else 0,
        "selected_dishes": int(selected_df["dish_id"].nunique()) if "dish_id" in selected_df.columns else 0,
        "selected_neighborhoods": int(selected_df["neighborhood_id"].nunique()) if "neighborhood_id" in selected_df.columns else 0,
        "selected_districts": int(selected_df["district_id"].nunique()) if "district_id" in selected_df.columns else 0,
        "top_hidden_gem_count": int(tier_counts.get("top_hidden_gem", 0)),
        "strong_hidden_gem_count": int(tier_counts.get("strong_hidden_gem", 0)),
        "promising_hidden_gem_count": int(tier_counts.get("promising_hidden_gem", 0)),
        "exploratory_hidden_gem_count": int(tier_counts.get("exploratory_hidden_gem", 0)),
        "avg_score_selected": float(round(selected_df["hidden_gem_score"].mean(), 5)) if not selected_df.empty else None,
        "max_score": float(round(selected_df["hidden_gem_score"].max(), 5)) if not selected_df.empty else None,
        "min_score_selected": float(round(selected_df["hidden_gem_score"].min(), 5)) if not selected_df.empty else None,
        "total_mentions_selected": int(selected_df["mention_count"].fillna(0).sum()) if "mention_count" in selected_df.columns else 0,
        "total_reviews_selected": int(selected_df["review_count"].fillna(0).sum()) if "review_count" in selected_df.columns else 0,
        "production_ready_count": int(selected_df["is_production_ready"].sum()) if "is_production_ready" in selected_df.columns else 0,
    }


def build_filter_options(selected_df: pd.DataFrame) -> dict[str, Any]:
    def values(col: str) -> list[str]:
        if selected_df.empty or col not in selected_df.columns:
            return []
        return sorted([str(x) for x in selected_df[col].dropna().unique().tolist()])

    return {
        "districts": values("district_name"),
        "neighborhoods": values("neighborhood_name"),
        "dishes": values("dish_display_name"),
        "tiers": [tier for tier in TIER_ORDER if tier in values("hidden_gem_tier")],
        "places": values("place_name"),
        "evidence_tiers": values("evidence_tier"),
        "aggregate_quality_tiers": values("aggregate_quality_tier"),
    }


def build_quality_summary(
    selected_df: pd.DataFrame,
    all_df: pd.DataFrame,
    expected_selected: int | None,
) -> tuple[pd.DataFrame, dict[str, bool]]:
    checks = {
        "has_candidates": bool(len(all_df) > 0),
        "has_selected_candidates": bool(len(selected_df) > 0),
        "expected_selected_matches": bool(len(selected_df) == expected_selected) if expected_selected is not None else True,
        "score_in_0_100": bool(selected_df["hidden_gem_score"].between(0, 100).all()) if not selected_df.empty else True,
        "selected_have_place": bool(selected_df["place_id"].notna().all()) if not selected_df.empty and "place_id" in selected_df.columns else True,
        "selected_have_dish": bool(selected_df["dish_id"].notna().all()) if not selected_df.empty and "dish_id" in selected_df.columns else True,
        "selected_have_neighborhood": bool(selected_df["neighborhood_id"].notna().all()) if not selected_df.empty and "neighborhood_id" in selected_df.columns else True,
        "selected_have_district": bool(selected_df["district_id"].notna().all()) if not selected_df.empty and "district_id" in selected_df.columns else True,
        "selected_have_coordinates": bool(selected_df["latitude"].notna().all() and selected_df["longitude"].notna().all()) if not selected_df.empty and {"latitude", "longitude"}.issubset(selected_df.columns) else True,
        "global_ranks_are_unique": bool(selected_df["hidden_gem_selected_rank"].nunique(dropna=True) == len(selected_df)) if not selected_df.empty and "hidden_gem_selected_rank" in selected_df.columns else True,
        "all_selected_are_not_production_ready": bool((selected_df["is_production_ready"] == False).all()) if not selected_df.empty and "is_production_ready" in selected_df.columns else True,
        "artifact_scope_ok": bool((all_df["artifact_ranking_scope"] == DEFAULT_ARTIFACT_RANKING_SCOPE).all()) if not all_df.empty and "artifact_ranking_scope" in all_df.columns else False,
        "db_ranking_scope_ok": bool((all_df["ranking_scope"] == DEFAULT_DB_RANKING_SCOPE).all()) if not all_df.empty and "ranking_scope" in all_df.columns else False,
    }

    descriptions = {
        "has_candidates": "There are scored candidate rows for the selected ranking scope.",
        "has_selected_candidates": "There are selected Hidden Gems candidates.",
        "expected_selected_matches": "Selected candidate count matches the expected pilot count when provided.",
        "score_in_0_100": "All selected scores are inside the 0–100 range.",
        "selected_have_place": "Every selected candidate has a place_id.",
        "selected_have_dish": "Every selected candidate has a dish_id.",
        "selected_have_neighborhood": "Every selected candidate has a neighborhood_id.",
        "selected_have_district": "Every selected candidate has a district_id.",
        "selected_have_coordinates": "Every selected candidate has latitude and longitude.",
        "global_ranks_are_unique": "Selected global ranks are unique.",
        "all_selected_are_not_production_ready": "Selected candidates remain marked as not production-ready.",
        "artifact_scope_ok": "All exported rows belong to artifact_ranking_scope=sevilla_pilot.",
        "db_ranking_scope_ok": "All exported rows use db ranking_scope=other due to current DDL constraint.",
    }

    rows = []
    for name, value in checks.items():
        rows.append(
            {
                "check_name": name,
                "check_value": bool(value),
                "status": "pass" if value else "fail",
                "description": descriptions.get(name, ""),
            }
        )
    return pd.DataFrame(rows), checks


def build_data_contract(include_mentions: bool, include_full_review_text: bool) -> dict[str, Any]:
    files = {
        "dashboard_metadata.json": "General metadata for the dashboard.",
        "kpi_summary.json": "Top-level KPI cards for the dashboard.",
        "candidates_detail.csv": "Selected Hidden Gems candidates used by the dashboard.",
        "candidates_all.csv": "All scored candidates for the Sevilla pilot scope.",
        "top_global.csv": "Global selected ranking ordered by selected rank.",
        "top_by_district.csv": "Top candidates per district.",
        "top_by_neighborhood.csv": "Top candidates per neighborhood.",
        "top_by_dish.csv": "Top places for each dish.",
        "district_summary.csv": "District-level aggregation.",
        "neighborhood_summary.csv": "Neighborhood-level aggregation.",
        "dish_summary.csv": "Dish-level aggregation.",
        "place_summary.csv": "Place-level aggregation with best dish fields.",
        "tier_summary.csv": "Distribution by Hidden Gem tier.",
        "quality_summary.csv": "Dashboard quality checks.",
        "filter_options.json": "Precomputed dropdown/filter values.",
        "dashboard_export_summary.json": "Export execution summary.",
        "data_contract.json": "This file: data contract and intended use.",
    }
    if include_mentions:
        files["mention_examples.csv"] = (
            "Optional mention/review examples for candidate detail. Includes full review text only when "
            "include_full_review_text=true."
        )

    return {
        "version": "dashboard_data_contract_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "intended_dashboard": "Streamlit Sevilla Hidden Gems pilot dashboard",
        "files": files,
        "privacy_and_display_notes": [
            "The dashboard should show that the ranking is a pilot and is not production-ready.",
            "Full review text is optional and should only be displayed inside candidate/review detail views.",
            "Avoid publishing raw review text broadly; use previews or contextual snippets by default.",
        ],
        "include_mentions": include_mentions,
        "include_full_review_text": include_full_review_text,
    }


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export dashboard-ready data for Sevilla Hidden Gems pilot.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="PostgreSQL schema name.")
    parser.add_argument("--db-ranking-scope", default=DEFAULT_DB_RANKING_SCOPE)
    parser.add_argument("--artifact-ranking-scope", default=DEFAULT_ARTIFACT_RANKING_SCOPE)
    parser.add_argument("--ranking-version", default=DEFAULT_RANKING_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    parser.add_argument("--expected-selected", type=int, default=None, help="Expected selected candidate count, e.g. 150.")
    parser.add_argument("--min-score", type=float, default=None, help="Optional minimum score filter for exported candidates.")
    parser.add_argument("--top-global-limit", type=int, default=150, help="Rows exported in top_global.csv.")
    parser.add_argument("--top-per-group", type=int, default=10, help="Rows exported per district/neighborhood/dish group.")

    parser.add_argument("--include-mentions", action="store_true", help="Export mention examples for candidate detail views.")
    parser.add_argument("--mention-candidates", type=int, default=150, help="Number of selected candidates to fetch examples for.")
    parser.add_argument("--examples-per-candidate", type=int, default=5, help="Mention examples per candidate.")
    parser.add_argument(
        "--include-full-review-text",
        action="store_true",
        help="Include complete review_text_raw in mention_examples.csv. Use only for local/detail views.",
    )

    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if final checks fail.")
    return parser.parse_args()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> int:
    args = parse_args()
    validate_schema_name(args.schema)

    print_section("1. Validating AI views")
    view_info = validate_required_view_columns(args.schema)
    print(json.dumps(to_builtin(view_info), indent=2, ensure_ascii=False, allow_nan=False))
    if view_info["missing_candidate_required_columns"]:
        print("Missing required columns in vw_ai_hidden_gem_candidate_detail.")
        return 1

    print_section("2. Loading candidates")
    all_candidates_df = load_candidates(args)
    if all_candidates_df.empty:
        print("No candidate rows found for the requested Sevilla pilot scope.")
        return 1

    selected_df = get_selected_df(all_candidates_df)
    print(f"All candidates: {len(all_candidates_df)}")
    print(f"Selected candidates: {len(selected_df)}")
    print(f"Selected places: {selected_df['place_id'].nunique() if 'place_id' in selected_df.columns else 0}")
    print(f"Selected dishes: {selected_df['dish_id'].nunique() if 'dish_id' in selected_df.columns else 0}")
    print(f"Selected neighborhoods: {selected_df['neighborhood_id'].nunique() if 'neighborhood_id' in selected_df.columns else 0}")
    print(f"Selected districts: {selected_df['district_id'].nunique() if 'district_id' in selected_df.columns else 0}")

    print_section("3. Building dashboard datasets")
    top_global_df = top_global(selected_df, args.top_global_limit)
    top_by_district_df = top_by_group(selected_df, ["district_name"], "rank_in_district", args.top_per_group)
    top_by_neighborhood_df = top_by_group(selected_df, ["district_name", "neighborhood_name"], "rank_in_neighborhood", args.top_per_group)
    top_by_dish_df = top_by_group(selected_df, ["dish_display_name"], "rank_for_dish", args.top_per_group)

    district_summary_df = summarize_by_group(selected_df, ["district_name"])
    neighborhood_summary_df = summarize_by_group(selected_df, ["district_name", "neighborhood_name"])
    dish_summary_df = summarize_by_group(selected_df, ["dish_id", "dish_name", "dish_display_name"])
    place_summary_df = summarize_places(selected_df)
    tier_summary_df = summarize_tiers(selected_df)

    selected_export_df = selected_df[safe_columns(selected_df, DASHBOARD_SELECTED_COLUMNS)].copy()
    all_export_df = all_candidates_df[safe_columns(all_candidates_df, DASHBOARD_SELECTED_COLUMNS)].copy()
    top_global_export_df = top_global_df[safe_columns(top_global_df, TOP_GLOBAL_COLUMNS)].copy()

    mention_examples_df = pd.DataFrame()
    if args.include_mentions:
        if not view_info["mentions_view_available"]:
            print("Warning: vw_ai_dish_mentions_with_sentiment is not available. mention_examples.csv will not be exported.")
        else:
            print("Loading mention examples...")
            mention_examples_df = load_mention_examples(
                schema=args.schema,
                selected_df=top_global(selected_df, args.mention_candidates),
                max_candidates=args.mention_candidates,
                examples_per_candidate=args.examples_per_candidate,
                include_full_review_text=args.include_full_review_text,
            )
            print(f"Mention examples: {len(mention_examples_df)}")

    metadata = build_metadata(args)
    kpis = build_kpis(selected_df, all_candidates_df)
    filter_options = build_filter_options(selected_df)
    quality_summary_df, checks = build_quality_summary(selected_df, all_candidates_df, args.expected_selected)
    data_contract = build_data_contract(args.include_mentions, args.include_full_review_text)

    export_summary = {
        "script": "export_sevilla_dashboard_data",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(args.output_dir),
        "filters": {
            "schema": args.schema,
            "db_ranking_scope": args.db_ranking_scope,
            "artifact_ranking_scope": args.artifact_ranking_scope,
            "ranking_version": args.ranking_version,
            "min_score": args.min_score,
        },
        "counts": {
            "all_candidates": int(len(all_candidates_df)),
            "selected_candidates": int(len(selected_df)),
            "top_global_rows": int(len(top_global_export_df)),
            "top_by_district_rows": int(len(top_by_district_df)),
            "top_by_neighborhood_rows": int(len(top_by_neighborhood_df)),
            "top_by_dish_rows": int(len(top_by_dish_df)),
            "district_summary_rows": int(len(district_summary_df)),
            "neighborhood_summary_rows": int(len(neighborhood_summary_df)),
            "dish_summary_rows": int(len(dish_summary_df)),
            "place_summary_rows": int(len(place_summary_df)),
            "tier_summary_rows": int(len(tier_summary_df)),
            "mention_examples_rows": int(len(mention_examples_df)),
        },
        "checks": checks,
        "kpis": kpis,
        "files": [
            "dashboard_metadata.json",
            "kpi_summary.json",
            "candidates_detail.csv",
            "candidates_all.csv",
            "top_global.csv",
            "top_by_district.csv",
            "top_by_neighborhood.csv",
            "top_by_dish.csv",
            "district_summary.csv",
            "neighborhood_summary.csv",
            "dish_summary.csv",
            "place_summary.csv",
            "tier_summary.csv",
            "quality_summary.csv",
            "filter_options.json",
            "data_contract.json",
            "dashboard_export_summary.json",
        ] + (["mention_examples.csv"] if args.include_mentions and not mention_examples_df.empty else []),
    }

    print_section("4. Saving dashboard artifacts")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    save_json(metadata, output_dir / "dashboard_metadata.json")
    save_json(kpis, output_dir / "kpi_summary.json")
    save_csv(selected_export_df, output_dir / "candidates_detail.csv")
    save_csv(all_export_df, output_dir / "candidates_all.csv")
    save_csv(top_global_export_df, output_dir / "top_global.csv")
    save_csv(top_by_district_df, output_dir / "top_by_district.csv")
    save_csv(top_by_neighborhood_df, output_dir / "top_by_neighborhood.csv")
    save_csv(top_by_dish_df, output_dir / "top_by_dish.csv")
    save_csv(district_summary_df, output_dir / "district_summary.csv")
    save_csv(neighborhood_summary_df, output_dir / "neighborhood_summary.csv")
    save_csv(dish_summary_df, output_dir / "dish_summary.csv")
    save_csv(place_summary_df, output_dir / "place_summary.csv")
    save_csv(tier_summary_df, output_dir / "tier_summary.csv")
    save_csv(quality_summary_df, output_dir / "quality_summary.csv")
    save_json(filter_options, output_dir / "filter_options.json")
    save_json(data_contract, output_dir / "data_contract.json")

    if args.include_mentions and not mention_examples_df.empty:
        save_csv(mention_examples_df, output_dir / "mention_examples.csv")

    save_json(export_summary, output_dir / "dashboard_export_summary.json")

    print(f"Output dir: {output_dir}")
    for file_name in export_summary["files"]:
        print(f"- {file_name}")

    print_section("Final checks")
    print(json.dumps(to_builtin(checks), indent=2, ensure_ascii=False, allow_nan=False))

    if all(checks.values()):
        print("\nDashboard export completed successfully.")
        return 0

    print("\nDashboard export completed with warnings.")
    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
