"""Query demo for the Sevilla Hidden Gems AI pilot.

This script reads the PostgreSQL AI views created by 08_ai_views.sql and produces
human-friendly query outputs for the Sevilla pilot ranking loaded with:

    python -m scripts.load_sevilla_ai_pilot_outputs

It is intended as a lightweight demo/query layer, not as a data loader. It does
not modify the database.

Recommended execution from repository root:

    python -m scripts.query_sevilla_hidden_gems_demo `
      --limit 30 `
      --top-per-group 5 `
      --expected-selected 150 `
      --strict

Useful filtered examples:

    python -m scripts.query_sevilla_hidden_gems_demo `
      --district "Casco Antiguo" `
      --limit 20 `
      --strict

    python -m scripts.query_sevilla_hidden_gems_demo `
      --neighborhood "TRIANA" `
      --limit 20

    python -m scripts.query_sevilla_hidden_gems_demo `
      --dish "tarta de queso" `
      --limit 20

    python -m scripts.query_sevilla_hidden_gems_demo `
      --only-tier strong_hidden_gem `
      --limit 20

    python -m scripts.query_sevilla_hidden_gems_demo `
      --place-name "Golondrinas" `
      --include-mentions `
      --limit 10

By default the database ranking_scope is 'other' because the current DDL
constraint does not allow 'sevilla_pilot' as a native enum/check value. The
original artifact scope is preserved in ranking_config_json:

    ranking_config_json->>'artifact_ranking_scope' = 'sevilla_pilot'
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import date, datetime
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
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/query_demo")

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

TIER_ORDER = {
    "top_hidden_gem": 4,
    "strong_hidden_gem": 3,
    "promising_hidden_gem": 2,
    "exploratory_hidden_gem": 1,
    "not_selected": 0,
}

BASE_DETAIL_COLUMNS = [
    "hidden_gem_candidate_id",
    "hidden_gem_selected_rank",
    "hidden_gem_rank",
    "hidden_gem_tier",
    "is_selected",
    "is_production_ready",
    "human_review_status",
    "hidden_gem_score",
    "hidden_gem_score_base",
    "place_id",
    "place_name",
    "address_text",
    "latitude",
    "longitude",
    "dish_id",
    "dish_name",
    "dish_normalized_name",
    "dish_display_name",
    "neighborhood_id",
    "neighborhood_name",
    "district_id",
    "district_name",
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
    "total_signal_weight",
    "avg_rating",
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
    "ranking_config_json",
    "quality_flags",
]

MENTIONS_COLUMNS = [
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
    "review_text_raw",
]

TOP_DISPLAY_COLUMNS = [
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
]


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def validate_uuid(value: str | None, arg_name: str) -> str | None:
    if value in (None, ""):
        return None
    try:
        return str(UUID(str(value)))
    except ValueError as exc:
        raise ValueError(f"{arg_name} must be a valid UUID. Received: {value!r}") from exc


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


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


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


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def truncate_text(value: Any, max_len: int = 120) -> str:
    if value is None:
        return ""
    text_value = str(value).replace("\n", " ").replace("\r", " ").strip()
    if len(text_value) <= max_len:
        return text_value
    return text_value[: max_len - 1] + "…"


def print_table(df: pd.DataFrame, columns: list[str], limit: int, max_col_width: int = 90) -> None:
    if df.empty:
        print("Sin resultados.")
        return

    available = [c for c in columns if c in df.columns]
    if not available:
        print("Sin columnas disponibles para mostrar.")
        return

    view = df[available].head(limit).copy()
    for col in view.columns:
        if view[col].dtype == object:
            view[col] = view[col].map(lambda x: truncate_text(x, max_col_width))

    print(view.to_string(index=False))


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")


def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def get_view_columns(schema: str, view_name: str) -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :view_name
        ORDER BY ordinal_position;
    """
    df = read_df(sql, {"schema": schema, "view_name": view_name})
    return set(df["column_name"].tolist()) if not df.empty else set()


def assert_view_columns(schema: str, view_name: str, required_columns: list[str]) -> None:
    available = get_view_columns(schema, view_name)
    if not available:
        raise RuntimeError(
            f"No se encontró la vista {schema}.{view_name} en information_schema.columns. "
            "Comprueba que db/ddl/08_ai_views.sql está cargado."
        )

    missing = [col for col in required_columns if col not in available]
    if missing:
        raise RuntimeError(
            f"La vista {schema}.{view_name} no contiene las columnas esperadas: {missing}. "
            "Revisa que la vista esté actualizada."
        )


# -----------------------------------------------------------------------------
# Query builders
# -----------------------------------------------------------------------------


def load_candidate_detail(args: argparse.Namespace) -> pd.DataFrame:
    schema = validate_schema_name(args.schema)
    assert_view_columns(schema, "vw_ai_hidden_gem_candidate_detail", BASE_DETAIL_COLUMNS)

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

    if not args.include_not_selected:
        where_parts.append("is_selected = TRUE")

    if args.only_tier:
        where_parts.append("hidden_gem_tier = :only_tier")
        params["only_tier"] = args.only_tier

    if args.district:
        where_parts.append("district_name ILIKE :district")
        params["district"] = f"%{args.district}%"

    if args.neighborhood:
        where_parts.append("neighborhood_name ILIKE :neighborhood")
        params["neighborhood"] = f"%{args.neighborhood}%"

    if args.dish:
        where_parts.append("(dish_display_name ILIKE :dish OR dish_name ILIKE :dish OR dish_normalized_name ILIKE :dish)")
        params["dish"] = f"%{args.dish}%"

    if args.place_name:
        where_parts.append("place_name ILIKE :place_name")
        params["place_name"] = f"%{args.place_name}%"

    if args.place_id:
        where_parts.append("place_id = CAST(:place_id AS uuid)")
        params["place_id"] = args.place_id

    if args.candidate_id:
        where_parts.append("hidden_gem_candidate_id = CAST(:candidate_id AS uuid)")
        params["candidate_id"] = args.candidate_id

    if args.min_score is not None:
        where_parts.append("hidden_gem_score >= :min_score")
        params["min_score"] = args.min_score

    select_columns = ",\n        ".join(BASE_DETAIL_COLUMNS)
    sql = f"""
        SELECT
            {select_columns},
            ranking_config_json->>'artifact_ranking_scope' AS artifact_ranking_scope
        FROM {view_name}
        WHERE {' AND '.join(where_parts)}
        ORDER BY
            hidden_gem_selected_rank NULLS LAST,
            hidden_gem_score DESC,
            mention_count DESC,
            review_count DESC,
            place_name,
            dish_display_name;
    """

    df = read_df(sql, params)
    if df.empty:
        return df

    for bool_col in ["is_selected", "is_production_ready", "is_rankable_candidate"]:
        if bool_col in df.columns:
            df[bool_col] = coerce_bool_series(df[bool_col])

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
    df["hidden_gem_tier_order"] = df["hidden_gem_tier"].map(TIER_ORDER).fillna(0).astype(int)
    return df


def load_mentions_for_candidates(
    schema: str,
    selected_df: pd.DataFrame,
    max_candidates: int,
    examples_per_candidate: int,
) -> pd.DataFrame:
    if selected_df.empty:
        return pd.DataFrame()

    schema = validate_schema_name(schema)
    assert_view_columns(schema, "vw_ai_dish_mentions_with_sentiment", MENTIONS_COLUMNS)
    view_name = qname(schema, "vw_ai_dish_mentions_with_sentiment")

    top_pairs = selected_df[["place_id", "dish_id"]].drop_duplicates().head(max_candidates)
    if top_pairs.empty:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []
    sql = f"""
        SELECT
            place_id,
            place_name,
            dish_id,
            dish_name,
            review_id,
            rating_value,
            sentiment_label,
            sentiment_score,
            sentiment_confidence,
            sentiment_reliability_tier,
            sentiment_reason,
            mention_text,
            context_sentence,
            review_text_raw
        FROM {view_name}
        WHERE place_id = CAST(:place_id AS uuid)
          AND dish_id = CAST(:dish_id AS uuid)
        ORDER BY
            sentiment_confidence DESC NULLS LAST,
            ABS(COALESCE(sentiment_score, 0)) DESC,
            rating_value DESC NULLS LAST
        LIMIT :limit;
    """

    for _, row in top_pairs.iterrows():
        df = read_df(
            sql,
            {
                "place_id": str(row["place_id"]),
                "dish_id": str(row["dish_id"]),
                "limit": examples_per_candidate,
            },
        )
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# -----------------------------------------------------------------------------
# Aggregations
# -----------------------------------------------------------------------------


def top_global(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    if df.empty:
        return df
    return (
        df.sort_values(
            ["hidden_gem_selected_rank", "hidden_gem_score", "mention_count", "review_count"],
            ascending=[True, False, False, False],
            na_position="last",
        )
        .head(limit)
        .reset_index(drop=True)
    )


def top_by_group(df: pd.DataFrame, group_cols: str | list[str], per_group: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    if isinstance(group_cols, str):
        group_cols = [group_cols]

    available_group_cols = [col for col in group_cols if col in df.columns]
    if not available_group_cols:
        return pd.DataFrame()

    ordered = df.sort_values(
        available_group_cols + ["hidden_gem_score", "hidden_gem_selected_rank"],
        ascending=[True] * len(available_group_cols) + [False, True],
        na_position="last",
    ).copy()
    ordered["rank_in_group"] = ordered.groupby(available_group_cols, dropna=False).cumcount() + 1
    return ordered[ordered["rank_in_group"] <= per_group].reset_index(drop=True)


def summarize_by_group(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    available_group_cols = [c for c in group_cols if c in df.columns]
    if not available_group_cols:
        return pd.DataFrame()

    grouped = (
        df.groupby(available_group_cols, dropna=False)
        .agg(
            selected_count=("hidden_gem_candidate_id", "count"),
            selected_places=("place_id", "nunique"),
            selected_dishes=("dish_id", "nunique"),
            top_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "top_hidden_gem").sum())),
            strong_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "strong_hidden_gem").sum())),
            promising_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "promising_hidden_gem").sum())),
            exploratory_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "exploratory_hidden_gem").sum())),
            avg_score=("hidden_gem_score", "mean"),
            max_score=("hidden_gem_score", "max"),
            total_mentions=("mention_count", "sum"),
            total_reviews=("review_count", "sum"),
            avg_positive_ratio=("positive_ratio", "mean"),
            avg_negative_ratio=("negative_ratio", "mean"),
        )
        .reset_index()
    )

    for col in ["avg_score", "max_score", "avg_positive_ratio", "avg_negative_ratio"]:
        if col in grouped.columns:
            grouped[col] = grouped[col].round(5)

    return grouped.sort_values(["max_score", "selected_count"], ascending=[False, False]).reset_index(drop=True)


def summarize_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "hidden_gem_tier" not in df.columns:
        return pd.DataFrame()

    grouped = (
        df.groupby("hidden_gem_tier", dropna=False)
        .agg(
            selected_count=("hidden_gem_candidate_id", "count"),
            selected_places=("place_id", "nunique"),
            selected_dishes=("dish_id", "nunique"),
            selected_neighborhoods=("neighborhood_id", "nunique"),
            selected_districts=("district_id", "nunique"),
            avg_score=("hidden_gem_score", "mean"),
            min_score=("hidden_gem_score", "min"),
            max_score=("hidden_gem_score", "max"),
            total_mentions=("mention_count", "sum"),
            total_reviews=("review_count", "sum"),
        )
        .reset_index()
    )
    grouped["tier_order"] = grouped["hidden_gem_tier"].map(TIER_ORDER).fillna(0).astype(int)

    for col in ["avg_score", "min_score", "max_score"]:
        grouped[col] = grouped[col].round(5)

    return grouped.sort_values("tier_order", ascending=False).drop(columns=["tier_order"]).reset_index(drop=True)


def build_filter_options(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "districts": [],
            "neighborhoods": [],
            "dishes": [],
            "tiers": [],
            "score_range": None,
        }

    def unique_sorted(col: str) -> list[str]:
        if col not in df.columns:
            return []
        return sorted([str(v) for v in df[col].dropna().unique().tolist()])

    score_range = None
    if "hidden_gem_score" in df.columns and df["hidden_gem_score"].notna().any():
        score_range = {
            "min": float(df["hidden_gem_score"].min()),
            "max": float(df["hidden_gem_score"].max()),
        }

    neighborhoods = []
    if {"district_name", "neighborhood_name"}.issubset(df.columns):
        neighborhoods_df = (
            df[["district_name", "neighborhood_name"]]
            .dropna()
            .drop_duplicates()
            .sort_values(["district_name", "neighborhood_name"])
        )
        neighborhoods = df_to_records(neighborhoods_df)

    return {
        "districts": unique_sorted("district_name"),
        "neighborhoods": neighborhoods,
        "dishes": unique_sorted("dish_display_name"),
        "tiers": unique_sorted("hidden_gem_tier"),
        "score_range": score_range,
    }


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query/demo layer for Sevilla Hidden Gems pilot ranking.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="PostgreSQL schema name.")
    parser.add_argument("--db-ranking-scope", default=DEFAULT_DB_RANKING_SCOPE)
    parser.add_argument("--artifact-ranking-scope", default=DEFAULT_ARTIFACT_RANKING_SCOPE)
    parser.add_argument("--ranking-version", default=DEFAULT_RANKING_VERSION)

    parser.add_argument("--limit", type=int, default=30, help="Number of global top rows to show/save in the report.")
    parser.add_argument("--top-per-group", type=int, default=5, help="Rows per district/neighborhood/dish group.")
    parser.add_argument("--min-score", type=float, default=None, help="Optional minimum hidden_gem_score filter.")
    parser.add_argument(
        "--only-tier",
        choices=sorted(TIER_ORDER.keys()),
        default=None,
        help="Optional exact hidden_gem_tier filter.",
    )

    parser.add_argument("--district", default=None, help="Optional district name filter, partial match.")
    parser.add_argument("--neighborhood", default=None, help="Optional neighborhood name filter, partial match.")
    parser.add_argument("--dish", default=None, help="Optional dish name filter, partial match.")
    parser.add_argument("--place-name", default=None, help="Optional place name filter, partial match.")
    parser.add_argument("--place-id", default=None, help="Optional exact place_id filter.")
    parser.add_argument("--candidate-id", default=None, help="Optional exact hidden_gem_candidate_id filter.")

    parser.add_argument(
        "--include-not-selected",
        action="store_true",
        help="Include non-selected candidates in the base detail export. Demo summaries still prioritize selected rows.",
    )
    parser.add_argument(
        "--include-mentions",
        action="store_true",
        help="Also export mention examples for the top selected candidates.",
    )
    parser.add_argument("--mention-candidates", type=int, default=10, help="How many top candidates to fetch mention examples for.")
    parser.add_argument("--examples-per-candidate", type=int, default=3, help="Mention examples per selected candidate.")

    parser.add_argument(
        "--expected-selected",
        type=int,
        default=None,
        help="Optional expected number of selected candidates after applying filters. Useful for full pilot validation.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code if final checks are not all true.",
    )

    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-save", action="store_true", help="Do not save CSV/JSON artifacts.")

    args = parser.parse_args()

    validate_schema_name(args.schema)
    args.place_id = validate_uuid(args.place_id, "--place-id")
    args.candidate_id = validate_uuid(args.candidate_id, "--candidate-id")

    if args.limit <= 0:
        raise ValueError("--limit must be greater than 0.")
    if args.top_per_group <= 0:
        raise ValueError("--top-per-group must be greater than 0.")
    if args.mention_candidates <= 0:
        raise ValueError("--mention-candidates must be greater than 0.")
    if args.examples_per_candidate <= 0:
        raise ValueError("--examples-per-candidate must be greater than 0.")

    return args


def main() -> int:
    args = parse_args()

    print_section("1. Loading Sevilla Hidden Gems candidate detail")
    detail_df = load_candidate_detail(args)

    if detail_df.empty:
        print("No se encontraron candidatos con los filtros indicados.")
        print("Revisa ranking_scope, artifact_ranking_scope, ranking_version o filtros de distrito/barrio/plato/local.")
        return 2 if args.strict else 1

    selected_df = detail_df[detail_df["is_selected"]].copy()
    selected_df = selected_df.sort_values(
        ["hidden_gem_selected_rank", "hidden_gem_score", "mention_count", "review_count"],
        ascending=[True, False, False, False],
        na_position="last",
    ).reset_index(drop=True)

    print(f"Candidatos cargados: {len(detail_df)}")
    print(f"Candidatos seleccionados: {len(selected_df)}")
    print(f"Lugares seleccionados: {selected_df['place_id'].nunique() if not selected_df.empty else 0}")
    print(f"Platos seleccionados: {selected_df['dish_id'].nunique() if not selected_df.empty else 0}")
    print(f"Barrios seleccionados: {selected_df['neighborhood_id'].nunique() if not selected_df.empty else 0}")
    print(f"Distritos seleccionados: {selected_df['district_id'].nunique() if not selected_df.empty else 0}")

    top_global_df = top_global(selected_df, args.limit)
    top_district_df = top_by_group(selected_df, ["district_name"], args.top_per_group)
    top_neighborhood_df = top_by_group(selected_df, ["district_name", "neighborhood_name"], args.top_per_group)
    top_dish_df = top_by_group(selected_df, ["dish_display_name"], args.top_per_group)

    district_summary_df = summarize_by_group(selected_df, ["district_name"])
    neighborhood_summary_df = summarize_by_group(selected_df, ["district_name", "neighborhood_name"])
    dish_summary_df = summarize_by_group(selected_df, ["dish_display_name", "dish_name"])
    place_summary_df = summarize_by_group(selected_df, ["place_id", "place_name", "address_text", "district_name", "neighborhood_name"])
    tier_summary_df = summarize_by_tier(selected_df)
    filter_options = build_filter_options(selected_df)

    print_section("2. Top global Sevilla pilot")
    print_table(top_global_df, TOP_DISPLAY_COLUMNS, args.limit)

    print_section("3. Resumen por distrito")
    print_table(
        district_summary_df,
        ["district_name", "selected_count", "selected_places", "selected_dishes", "avg_score", "max_score"],
        30,
    )

    print_section("4. Top por distrito")
    print_table(
        top_district_df,
        ["district_name", "rank_in_group", "hidden_gem_score", "place_name", "dish_display_name", "hidden_gem_tier", "neighborhood_name"],
        max(args.limit, 30),
    )

    print_section("5. Top por barrio")
    print_table(
        top_neighborhood_df,
        ["district_name", "neighborhood_name", "rank_in_group", "hidden_gem_score", "place_name", "dish_display_name", "hidden_gem_tier"],
        max(args.limit, 30),
    )

    print_section("6. Top platos seleccionados")
    print_table(
        dish_summary_df,
        ["dish_display_name", "selected_count", "selected_places", "avg_score", "max_score", "total_mentions", "total_reviews"],
        30,
    )

    print_section("7. Resumen por tier")
    print_table(
        tier_summary_df,
        ["hidden_gem_tier", "selected_count", "selected_places", "selected_dishes", "selected_neighborhoods", "avg_score", "min_score", "max_score"],
        20,
    )

    mentions_examples_df = pd.DataFrame()
    if args.include_mentions and not top_global_df.empty:
        print_section("8. Mention examples for top candidates")
        mentions_examples_df = load_mentions_for_candidates(
            schema=args.schema,
            selected_df=top_global_df,
            max_candidates=args.mention_candidates,
            examples_per_candidate=args.examples_per_candidate,
        )
        print_table(
            mentions_examples_df,
            ["place_name", "dish_name", "sentiment_label", "sentiment_confidence", "mention_text", "context_sentence"],
            args.mention_candidates * args.examples_per_candidate,
            max_col_width=110,
        )

    tier_counts = (
        selected_df["hidden_gem_tier"].value_counts().to_dict()
        if "hidden_gem_tier" in selected_df.columns
        else {}
    )

    expected_selected_ok = True
    if args.expected_selected is not None:
        expected_selected_ok = int(len(selected_df)) == int(args.expected_selected)

    checks = {
        "has_candidates": bool(len(detail_df) > 0),
        "has_selected_candidates": bool(len(selected_df) > 0),
        "expected_selected_matches": bool(expected_selected_ok),
        "score_in_0_100": bool(selected_df["hidden_gem_score"].between(0, 100).all()) if not selected_df.empty else True,
        "selected_have_place": bool(selected_df["place_id"].notna().all()) if not selected_df.empty else True,
        "selected_have_dish": bool(selected_df["dish_id"].notna().all()) if not selected_df.empty else True,
        "selected_have_neighborhood": bool(selected_df["neighborhood_id"].notna().all()) if not selected_df.empty else True,
        "selected_have_district": bool(selected_df["district_id"].notna().all()) if not selected_df.empty else True,
        "artifact_scope_ok": bool((detail_df["artifact_ranking_scope"] == args.artifact_ranking_scope).all())
        if "artifact_ranking_scope" in detail_df.columns else False,
        "db_ranking_scope_ok": bool((detail_df["ranking_scope"] == args.db_ranking_scope).all())
        if "ranking_scope" in detail_df.columns else False,
        "has_district_summary": bool(len(district_summary_df) > 0),
        "has_neighborhood_summary": bool(len(neighborhood_summary_df) > 0),
        "has_dish_summary": bool(len(dish_summary_df) > 0),
        "has_tier_summary": bool(len(tier_summary_df) > 0),
    }

    report = {
        "script": "query_sevilla_hidden_gems_demo",
        "generated_at": datetime.now().astimezone().isoformat(),
        "filters": {
            "schema": args.schema,
            "db_ranking_scope": args.db_ranking_scope,
            "artifact_ranking_scope": args.artifact_ranking_scope,
            "ranking_version": args.ranking_version,
            "district": args.district,
            "neighborhood": args.neighborhood,
            "dish": args.dish,
            "place_name": args.place_name,
            "place_id": args.place_id,
            "candidate_id": args.candidate_id,
            "min_score": args.min_score,
            "only_tier": args.only_tier,
            "include_not_selected": args.include_not_selected,
            "expected_selected": args.expected_selected,
        },
        "counts": {
            "detail_rows": int(len(detail_df)),
            "selected_rows": int(len(selected_df)),
            "selected_places": int(selected_df["place_id"].nunique()) if not selected_df.empty else 0,
            "selected_dishes": int(selected_df["dish_id"].nunique()) if not selected_df.empty else 0,
            "selected_neighborhoods": int(selected_df["neighborhood_id"].nunique()) if not selected_df.empty else 0,
            "selected_districts": int(selected_df["district_id"].nunique()) if not selected_df.empty else 0,
            "tier_counts": tier_counts,
        },
        "checks": checks,
        "filter_options": filter_options,
        "top_global": df_to_records(top_global_df, args.limit),
        "district_summary": df_to_records(district_summary_df, 50),
        "top_by_district": df_to_records(top_district_df, 100),
        "top_by_neighborhood": df_to_records(top_neighborhood_df, 200),
        "top_by_dish": df_to_records(top_dish_df, 100),
        "tier_summary": df_to_records(tier_summary_df, 20),
    }

    if args.include_mentions:
        report["mention_examples"] = df_to_records(mentions_examples_df, args.mention_candidates * args.examples_per_candidate)

    if not args.no_save:
        output_dir = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        save_csv(detail_df, output_dir / "sevilla_demo_candidate_detail.csv")
        save_csv(selected_df, output_dir / "sevilla_demo_selected_candidates.csv")
        save_csv(top_global_df, output_dir / "sevilla_demo_top_global.csv")
        save_csv(top_district_df, output_dir / "sevilla_demo_top_by_district.csv")
        save_csv(top_neighborhood_df, output_dir / "sevilla_demo_top_by_neighborhood.csv")
        save_csv(top_dish_df, output_dir / "sevilla_demo_top_by_dish.csv")
        save_csv(district_summary_df, output_dir / "sevilla_demo_district_summary.csv")
        save_csv(neighborhood_summary_df, output_dir / "sevilla_demo_neighborhood_summary.csv")
        save_csv(dish_summary_df, output_dir / "sevilla_demo_dish_summary.csv")
        save_csv(place_summary_df, output_dir / "sevilla_demo_place_summary.csv")
        save_csv(tier_summary_df, output_dir / "sevilla_demo_tier_summary.csv")
        save_json(filter_options, output_dir / "sevilla_demo_filter_options.json")

        if args.include_mentions:
            save_csv(mentions_examples_df, output_dir / "sevilla_demo_mention_examples.csv")

        save_json(report, output_dir / "sevilla_hidden_gems_query_demo_report.json")

        saved_files = [
            "sevilla_demo_candidate_detail.csv",
            "sevilla_demo_selected_candidates.csv",
            "sevilla_demo_top_global.csv",
            "sevilla_demo_top_by_district.csv",
            "sevilla_demo_top_by_neighborhood.csv",
            "sevilla_demo_top_by_dish.csv",
            "sevilla_demo_district_summary.csv",
            "sevilla_demo_neighborhood_summary.csv",
            "sevilla_demo_dish_summary.csv",
            "sevilla_demo_place_summary.csv",
            "sevilla_demo_tier_summary.csv",
            "sevilla_demo_filter_options.json",
            "sevilla_hidden_gems_query_demo_report.json",
        ]
        if args.include_mentions:
            saved_files.insert(-1, "sevilla_demo_mention_examples.csv")

        print_section("9. Saved artifacts")
        print(f"Output dir: {output_dir}")
        for file_name in saved_files:
            print(f"- {file_name}")

    print_section("Final checks")
    print(json.dumps(to_builtin(checks), indent=2, ensure_ascii=False, allow_nan=False))

    if all(checks.values()):
        print("\nDemo query layer completed successfully.")
        return 0

    print("\nDemo query layer completed with warnings. Review checks above.")
    return 2 if args.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
