"""Export dashboard-ready files for the Hidden Gems Yelp prototype.

Read-only script. It reads PostgreSQL views from db/ddl/08_ai_views.sql and
writes clean CSV/JSON files for a Streamlit dashboard.

Recommended:

python -m scripts.export_yelp_dashboard_data `
  --output-dir data/artifacts/ai/yelp/dashboard `
  --expected-selected 622 `
  --top-global-limit 9999 `
  --top-per-group 9999 `
  --include-mentions `
  --mention-candidates 100 `
  --examples-per-candidate 3 `
  --strict

Use --include-full-review-text only for local/private dashboard details. Do not
commit outputs containing full review text.
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

DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_RANKING_SCOPE = "yelp_prototype"
DEFAULT_RANKING_VERSION = "hidden_gems_ranking_v1"
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/yelp/dashboard")
SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
TIER_ORDER = {"top_hidden_gem": 4, "strong_hidden_gem": 3, "promising_hidden_gem": 2, "exploratory_hidden_gem": 1, "not_selected": 0}

DETAIL_COLUMNS = [
    "hidden_gem_candidate_id", "ai_pipeline_run_id", "ai_run_code", "ranking_version", "ranking_scope",
    "hidden_gem_rank", "hidden_gem_selected_rank", "hidden_gem_tier", "is_selected", "is_production_ready",
    "human_review_status", "hidden_gem_score", "hidden_gem_score_base", "place_id", "place_name",
    "place_canonical_name", "place_normalized_name", "address_text", "latitude", "longitude", "place_is_active",
    "place_confidence", "dish_id", "dish_name", "dish_normalized_name", "dish_display_name", "dish_language_code",
    "dish_is_reviewed", "dish_review_status", "neighborhood_id", "neighborhood_name", "district_id", "district_name",
    "dish_place_signal_id", "signal_version", "mention_count", "review_count", "positive_mentions", "neutral_mentions",
    "negative_mentions", "positive_ratio", "negative_ratio", "avg_ner_confidence", "avg_sentiment_confidence",
    "avg_signal_weight", "total_signal_weight", "avg_rating", "confidence_weighted_sentiment", "bayesian_sentiment_score",
    "reliability_high_ratio", "high_reliability_mentions", "medium_reliability_mentions", "low_reliability_mentions",
    "aggregate_quality_tier", "evidence_tier", "is_rankable_candidate", "local_sentiment_component", "evidence_component",
    "confidence_component", "positive_balance_component", "rarity_component", "local_outperformance_component", "hiddenness_component",
    "preliminary_component", "negative_penalty_factor", "beverage_penalty_factor", "noise_penalty_factor",
    "low_evidence_penalty_factor", "ranking_explanation", "ranking_config_json", "quality_flags", "hidden_gem_tier_order",
    "evidence_tier_order", "created_at", "updated_at"
]
NUMERIC_COLUMNS = [
    "hidden_gem_rank", "hidden_gem_selected_rank", "hidden_gem_score", "hidden_gem_score_base", "latitude", "longitude",
    "place_confidence", "mention_count", "review_count", "positive_mentions", "neutral_mentions", "negative_mentions",
    "positive_ratio", "negative_ratio", "avg_ner_confidence", "avg_sentiment_confidence", "avg_signal_weight",
    "total_signal_weight", "avg_rating", "confidence_weighted_sentiment", "bayesian_sentiment_score", "reliability_high_ratio",
    "high_reliability_mentions", "medium_reliability_mentions", "low_reliability_mentions", "local_sentiment_component",
    "evidence_component", "confidence_component", "positive_balance_component", "rarity_component", "local_outperformance_component",
    "hiddenness_component", "preliminary_component", "negative_penalty_factor", "beverage_penalty_factor", "noise_penalty_factor",
    "low_evidence_penalty_factor", "hidden_gem_tier_order", "evidence_tier_order"
]


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, name: str) -> str:
    return f'"{validate_schema_name(schema)}"."{name}"'


def to_builtin(value: Any) -> Any:
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
        return None if value.is_nan() else float(value)
    if hasattr(value, "item"):
        try:
            return to_builtin(value.item())
        except Exception:
            pass
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    return value


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if col in {"ranking_config_json", "quality_flags", "sentiment_flags", "positive_terms", "negative_terms"} or col.endswith("_json"):
            out[col] = out[col].map(lambda v: json.dumps(to_builtin(v), ensure_ascii=False, allow_nan=False) if not isinstance(to_builtin(v), str) else to_builtin(v))
    out.to_csv(path, index=False, encoding="utf-8")


def coerce_bool(series: pd.Series) -> pd.Series:
    if series.empty:
        return series.astype(bool)
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin(["true", "1", "t", "yes", "y"])


def coerce_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def parse_address(address: Any) -> tuple[str | None, str | None, str | None]:
    if address is None:
        return None, None, None
    parts = [p.strip() for p in str(address).split(",") if p.strip()]
    city = parts[1] if len(parts) >= 2 else None
    state_zip = parts[2] if len(parts) >= 3 else None
    state = state_zip.split()[0] if state_zip else None
    return city, state, state_zip


def add_location(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    parsed = out["address_text"].map(parse_address) if "address_text" in out.columns else pd.Series([], dtype=object)
    out["inferred_city"] = parsed.map(lambda x: x[0]) if len(parsed) else None
    out["inferred_state"] = parsed.map(lambda x: x[1]) if len(parsed) else None
    out["inferred_state_zip"] = parsed.map(lambda x: x[2]) if len(parsed) else None
    out["dish_dashboard_name"] = out.get("dish_display_name", pd.Series(dtype=object)).fillna(out.get("dish_name", pd.Series(dtype=object)))
    return out


def safe_unique(series: pd.Series) -> list[Any]:
    return sorted([to_builtin(v) for v in series.dropna().unique().tolist() if str(v).strip()]) if not series.empty else []


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def load_candidates(args: argparse.Namespace) -> pd.DataFrame:
    view = qname(args.schema, "vw_ai_hidden_gem_candidate_detail")
    where = ["ranking_scope = :ranking_scope"]
    params: dict[str, Any] = {"ranking_scope": args.ranking_scope}
    if args.ranking_version:
        where.append("ranking_version = :ranking_version")
        params["ranking_version"] = args.ranking_version
    if args.min_score is not None:
        where.append("hidden_gem_score >= :min_score")
        params["min_score"] = args.min_score
    sql = f"""
        SELECT {', '.join(DETAIL_COLUMNS)}
        FROM {view}
        WHERE {' AND '.join(where)}
        ORDER BY is_selected DESC, hidden_gem_selected_rank NULLS LAST, hidden_gem_score DESC;
    """
    df = read_df(sql, params)
    if df.empty:
        return df
    for col in ["is_selected", "is_production_ready", "place_is_active", "dish_is_reviewed", "is_rankable_candidate"]:
        if col in df.columns:
            df[col] = coerce_bool(df[col])
    df = coerce_numeric(df, NUMERIC_COLUMNS)
    return add_location(df)


def load_mentions(schema: str, selected: pd.DataFrame, max_candidates: int, examples_per_candidate: int, include_full_text: bool) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    view = qname(schema, "vw_ai_dish_mentions_with_sentiment")
    pairs = selected[["hidden_gem_candidate_id", "place_id", "dish_id"]].drop_duplicates().head(max_candidates)
    full_text_expr = "review_text_raw" if include_full_text else "NULL::text AS review_text_raw"
    sql = f"""
        SELECT
            :candidate_id AS hidden_gem_candidate_id,
            place_id, place_name, dish_id, dish_name, review_id, source_review_id,
            rating_value, review_language, review_created_at, mention_text,
            sentiment_label, sentiment_score, sentiment_confidence,
            sentiment_reliability_tier, sentiment_reason,
            target_clause_context, near_mention_context, context_sentence, context_window,
            {full_text_expr}
        FROM {view}
        WHERE place_id = CAST(:place_id AS uuid)
          AND dish_id = CAST(:dish_id AS uuid)
        ORDER BY
            CASE sentiment_reliability_tier WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
            sentiment_confidence DESC NULLS LAST,
            ABS(COALESCE(sentiment_score, 0)) DESC
        LIMIT :limit;
    """
    frames = []
    for _, row in pairs.iterrows():
        df = read_df(sql, {"candidate_id": str(row["hidden_gem_candidate_id"]), "place_id": str(row["place_id"]), "dish_id": str(row["dish_id"]), "limit": examples_per_candidate})
        if not df.empty:
            frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def top_global(df: pd.DataFrame, limit: int) -> pd.DataFrame:
    return df.sort_values(["hidden_gem_selected_rank", "hidden_gem_score"], ascending=[True, False], na_position="last").head(limit).reset_index(drop=True) if not df.empty else df


def top_by_group(df: pd.DataFrame, group_cols: list[str], rank_col: str, per_group: int) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = [c for c in group_cols if c in df.columns]
    if not cols:
        return pd.DataFrame()
    out = df.sort_values(cols + ["hidden_gem_score", "hidden_gem_selected_rank"], ascending=[True] * len(cols) + [False, True], na_position="last").copy()
    out[rank_col] = out.groupby(cols, dropna=False).cumcount() + 1
    return out[out[rank_col] <= per_group].reset_index(drop=True)


def summarize(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    cols = [c for c in group_cols if c in df.columns]
    if not cols:
        return pd.DataFrame()
    out = df.groupby(cols, dropna=False).agg(
        selected_count=("hidden_gem_candidate_id", "count"),
        selected_places=("place_id", "nunique"),
        selected_dishes=("dish_id", "nunique"),
        top_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "top_hidden_gem").sum())),
        strong_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "strong_hidden_gem").sum())),
        promising_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "promising_hidden_gem").sum())),
        exploratory_hidden_gem_count=("hidden_gem_tier", lambda s: int((s == "exploratory_hidden_gem").sum())),
        avg_score=("hidden_gem_score", "mean"), max_score=("hidden_gem_score", "max"), min_score=("hidden_gem_score", "min"),
        total_mentions=("mention_count", "sum"), total_reviews=("review_count", "sum"),
        avg_positive_ratio=("positive_ratio", "mean"), avg_negative_ratio=("negative_ratio", "mean"),
    ).reset_index()
    for c in ["avg_score", "max_score", "min_score", "avg_positive_ratio", "avg_negative_ratio"]:
        out[c] = out[c].round(5)
    return out.sort_values(["max_score", "selected_count"], ascending=[False, False]).reset_index(drop=True)


def place_summary(selected: pd.DataFrame) -> pd.DataFrame:
    base = summarize(selected, ["place_id", "place_name", "address_text", "inferred_city", "inferred_state", "latitude", "longitude"])
    if base.empty:
        return base
    best = selected.sort_values(["hidden_gem_score", "hidden_gem_selected_rank"], ascending=[False, True]).drop_duplicates("place_id")
    best = best[["place_id", "dish_dashboard_name", "hidden_gem_score", "hidden_gem_tier", "ranking_explanation"]].rename(columns={"dish_dashboard_name": "best_dish_name", "hidden_gem_score": "best_dish_score", "hidden_gem_tier": "best_dish_tier", "ranking_explanation": "best_ranking_explanation"})
    return base.merge(best, on="place_id", how="left").sort_values(["best_dish_score", "selected_count"], ascending=[False, False]).reset_index(drop=True)


def tier_summary(selected: pd.DataFrame) -> pd.DataFrame:
    if selected.empty:
        return pd.DataFrame()
    out = selected.groupby("hidden_gem_tier", dropna=False).agg(
        candidate_count=("hidden_gem_candidate_id", "count"), place_count=("place_id", "nunique"), dish_count=("dish_id", "nunique"),
        city_count=("inferred_city", "nunique"), state_count=("inferred_state", "nunique"),
        avg_score=("hidden_gem_score", "mean"), min_score=("hidden_gem_score", "min"), max_score=("hidden_gem_score", "max"),
        total_mentions=("mention_count", "sum"), total_reviews=("review_count", "sum"),
    ).reset_index()
    out["tier_order"] = out["hidden_gem_tier"].map(TIER_ORDER).fillna(0).astype(int)
    for c in ["avg_score", "min_score", "max_score"]:
        out[c] = out[c].round(5)
    return out.sort_values("tier_order", ascending=False).reset_index(drop=True)


def build_kpis(all_df: pd.DataFrame, selected: pd.DataFrame, mentions: pd.DataFrame) -> dict[str, Any]:
    tier_counts = selected["hidden_gem_tier"].value_counts().to_dict() if not selected.empty else {}
    return {
        "total_candidates_scored": int(len(all_df)),
        "selected_candidates": int(len(selected)),
        "selected_places": int(selected["place_id"].nunique()) if not selected.empty else 0,
        "selected_dishes": int(selected["dish_id"].nunique()) if not selected.empty else 0,
        "selected_cities": int(selected["inferred_city"].nunique(dropna=True)) if not selected.empty else 0,
        "selected_states": int(selected["inferred_state"].nunique(dropna=True)) if not selected.empty else 0,
        "top_hidden_gem_count": int(tier_counts.get("top_hidden_gem", 0)),
        "strong_hidden_gem_count": int(tier_counts.get("strong_hidden_gem", 0)),
        "promising_hidden_gem_count": int(tier_counts.get("promising_hidden_gem", 0)),
        "exploratory_hidden_gem_count": int(tier_counts.get("exploratory_hidden_gem", 0)),
        "avg_score_selected": round(float(selected["hidden_gem_score"].mean()), 5) if not selected.empty else None,
        "max_score": round(float(selected["hidden_gem_score"].max()), 5) if not selected.empty else None,
        "min_score_selected": round(float(selected["hidden_gem_score"].min()), 5) if not selected.empty else None,
        "total_mentions_selected": int(selected["mention_count"].sum()) if not selected.empty else 0,
        "total_reviews_selected": int(selected["review_count"].sum()) if not selected.empty else 0,
        "production_ready_count": int((selected["is_production_ready"] == True).sum()) if not selected.empty else 0,
        "mention_examples_rows": int(len(mentions)),
    }


def quality_summary(checks: dict[str, bool], selected: pd.DataFrame) -> pd.DataFrame:
    descriptions = {
        "has_candidates": "Candidate rows exist for the requested Yelp scope.",
        "has_selected_candidates": "Selected Hidden Gems candidates exist.",
        "expected_selected_matches": "Selected count matches expected value.",
        "score_in_0_100": "All selected scores are in [0, 100].",
        "selected_have_place": "All selected rows have place_id.",
        "selected_have_dish": "All selected rows have dish_id.",
        "global_ranks_are_unique": "Selected ranks are unique.",
        "all_selected_are_not_production_ready": "Yelp prototype is not production ready.",
        "ranking_scope_ok": "Rows use requested ranking_scope.",
    }
    rows = [{"check_name": k, "check_value": bool(v), "status": "ok" if v else "error", "description": descriptions.get(k, k)} for k, v in checks.items()]
    if not selected.empty:
        rows += [
            {"check_name": "average_mentions_per_candidate", "check_value": round(float(selected["mention_count"].mean()), 5), "status": "info", "description": "Average mentions among selected candidates."},
            {"check_name": "average_reviews_per_candidate", "check_value": round(float(selected["review_count"].mean()), 5), "status": "info", "description": "Average reviews among selected candidates."},
            {"check_name": "strong_evidence_count", "check_value": int((selected["evidence_tier"] == "strong").sum()), "status": "info", "description": "Selected candidates with strong evidence."},
        ]
    return pd.DataFrame(rows)


def data_contract(include_mentions: bool, include_full_text: bool) -> dict[str, Any]:
    files = {
        "dashboard_metadata.json": "General metadata for the Yelp prototype dashboard.",
        "kpi_summary.json": "Top-level KPI cards.",
        "candidates_detail.csv": "Selected candidate details.",
        "candidates_all.csv": "All candidate rows for the ranking scope.",
        "top_global.csv": "Global selected ranking.",
        "top_by_city.csv": "Top candidates per inferred city.",
        "top_by_state.csv": "Top candidates per inferred state.",
        "top_by_dish.csv": "Top places for each dish.",
        "city_summary.csv": "Summary by city/state.",
        "state_summary.csv": "Summary by state.",
        "dish_summary.csv": "Summary by dish.",
        "place_summary.csv": "Summary by place.",
        "tier_summary.csv": "Summary by tier.",
        "quality_summary.csv": "Checks and quality indicators.",
        "filter_options.json": "Filter values for the dashboard.",
        "data_contract.json": "Dashboard data contract.",
        "dashboard_export_summary.json": "Export run summary.",
    }
    if include_mentions:
        files["mention_examples.csv"] = "Optional mention evidence. Contains full review text only if --include-full-review-text is used."
    return {"dashboard_scope": "yelp_prototype", "purpose": "AI benchmark/prototype dashboard export.", "files": files, "full_review_text_included": bool(include_mentions and include_full_text), "git_notes": ["Do not commit raw Yelp data.", "Do not commit mention_examples.csv if it includes full review text.", "This is not a Sevilla production ranking."]}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export dashboard-ready files for the Yelp Hidden Gems prototype.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--ranking-scope", default=DEFAULT_RANKING_SCOPE)
    parser.add_argument("--ranking-version", default=DEFAULT_RANKING_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--expected-selected", type=int, default=622)
    parser.add_argument("--min-score", type=float, default=None)
    parser.add_argument("--top-global-limit", type=int, default=100)
    parser.add_argument("--top-per-group", type=int, default=20)
    parser.add_argument("--include-mentions", action="store_true")
    parser.add_argument("--mention-candidates", type=int, default=50)
    parser.add_argument("--examples-per-candidate", type=int, default=3)
    parser.add_argument("--include-full-review-text", action="store_true")
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_schema_name(args.schema)
    print_section("1. Loading Yelp prototype candidates")
    all_df = load_candidates(args)
    if all_df.empty:
        print("No candidates found for the requested scope/version.")
        return 1
    selected = all_df[all_df["is_selected"]].copy().sort_values(["hidden_gem_selected_rank", "hidden_gem_score"], ascending=[True, False], na_position="last").reset_index(drop=True)
    print(f"All candidates: {len(all_df)}")
    print(f"Selected candidates: {len(selected)}")
    print(f"Selected places: {selected['place_id'].nunique() if not selected.empty else 0}")
    print(f"Selected dishes: {selected['dish_id'].nunique() if not selected.empty else 0}")
    print(f"Selected cities: {selected['inferred_city'].nunique(dropna=True) if not selected.empty else 0}")

    top_global_df = top_global(selected, args.top_global_limit)
    top_by_city_df = top_by_group(selected, ["inferred_city"], "rank_in_city", args.top_per_group)
    top_by_state_df = top_by_group(selected, ["inferred_state"], "rank_in_state", args.top_per_group)
    top_by_dish_df = top_by_group(selected, ["dish_dashboard_name"], "rank_for_dish", args.top_per_group)
    city_summary_df = summarize(selected, ["inferred_city", "inferred_state"])
    state_summary_df = summarize(selected, ["inferred_state"])
    dish_summary_df = summarize(selected, ["dish_id", "dish_name", "dish_dashboard_name"])
    place_summary_df = place_summary(selected)
    tier_summary_df = tier_summary(selected)

    mentions_df = pd.DataFrame()
    if args.include_mentions:
        print_section("2. Loading mention examples")
        mentions_df = load_mentions(args.schema, selected, args.mention_candidates, args.examples_per_candidate, args.include_full_review_text)
        print(f"Mention examples: {len(mentions_df)}")

    checks = {
        "has_candidates": bool(len(all_df) > 0),
        "has_selected_candidates": bool(len(selected) > 0),
        "expected_selected_matches": bool(len(selected) == args.expected_selected) if args.expected_selected is not None else True,
        "score_in_0_100": bool(selected["hidden_gem_score"].between(0, 100).all()) if not selected.empty else True,
        "selected_have_place": bool(selected["place_id"].notna().all()) if not selected.empty else True,
        "selected_have_dish": bool(selected["dish_id"].notna().all()) if not selected.empty else True,
        "global_ranks_are_unique": bool(selected["hidden_gem_selected_rank"].nunique(dropna=True) == len(selected)) if not selected.empty else True,
        "all_selected_are_not_production_ready": bool((selected["is_production_ready"] == False).all()) if not selected.empty else True,
        "ranking_scope_ok": bool((all_df["ranking_scope"] == args.ranking_scope).all()) if "ranking_scope" in all_df.columns else False,
    }
    kpis = build_kpis(all_df, selected, mentions_df)
    filters = {
        "cities": safe_unique(selected["inferred_city"]),
        "states": safe_unique(selected["inferred_state"]),
        "dishes": safe_unique(selected["dish_dashboard_name"]),
        "tiers": [t for t in TIER_ORDER if t in set(selected["hidden_gem_tier"].dropna())],
        "places": safe_unique(selected["place_name"]),
        "evidence_tiers": safe_unique(selected["evidence_tier"]),
        "aggregate_quality_tiers": safe_unique(selected["aggregate_quality_tier"]),
    }
    metadata = {
        "project_name": "Hidden Gems",
        "dashboard_scope": "yelp_prototype",
        "dashboard_title": "Hidden Gems — Yelp AI Prototype Dashboard",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranking_scope": args.ranking_scope,
        "ranking_version": args.ranking_version,
        "is_production_ready": False,
        "source": "Yelp Open Dataset",
        "purpose": "AI benchmark/prototype dashboard for validating dish detection, sentiment, signal aggregation and ranking.",
        "notes": ["This is not a Sevilla production ranking.", "Yelp is used as a broad AI corpus/prototype dataset.", "Candidates are intentionally not production ready."],
    }
    summary = {
        "script": "export_yelp_dashboard_data",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(args.output_dir),
        "filters": {"schema": args.schema, "ranking_scope": args.ranking_scope, "ranking_version": args.ranking_version, "min_score": args.min_score},
        "counts": {
            "all_candidates": int(len(all_df)), "selected_candidates": int(len(selected)), "top_global_rows": int(len(top_global_df)),
            "top_by_city_rows": int(len(top_by_city_df)), "top_by_state_rows": int(len(top_by_state_df)), "top_by_dish_rows": int(len(top_by_dish_df)),
            "city_summary_rows": int(len(city_summary_df)), "state_summary_rows": int(len(state_summary_df)), "dish_summary_rows": int(len(dish_summary_df)),
            "place_summary_rows": int(len(place_summary_df)), "tier_summary_rows": int(len(tier_summary_df)), "mention_examples_rows": int(len(mentions_df)),
        },
        "checks": checks,
        "kpis": kpis,
        "files": ["dashboard_metadata.json", "kpi_summary.json", "candidates_detail.csv", "candidates_all.csv", "top_global.csv", "top_by_city.csv", "top_by_state.csv", "top_by_dish.csv", "city_summary.csv", "state_summary.csv", "dish_summary.csv", "place_summary.csv", "tier_summary.csv", "quality_summary.csv", "filter_options.json", "data_contract.json", "dashboard_export_summary.json"] + (["mention_examples.csv"] if args.include_mentions else []),
    }

    print_section("3. Saving dashboard artifacts")
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    save_json(metadata, out / "dashboard_metadata.json")
    save_json(kpis, out / "kpi_summary.json")
    save_csv(selected, out / "candidates_detail.csv")
    save_csv(all_df, out / "candidates_all.csv")
    save_csv(top_global_df, out / "top_global.csv")
    save_csv(top_by_city_df, out / "top_by_city.csv")
    save_csv(top_by_state_df, out / "top_by_state.csv")
    save_csv(top_by_dish_df, out / "top_by_dish.csv")
    save_csv(city_summary_df, out / "city_summary.csv")
    save_csv(state_summary_df, out / "state_summary.csv")
    save_csv(dish_summary_df, out / "dish_summary.csv")
    save_csv(place_summary_df, out / "place_summary.csv")
    save_csv(tier_summary_df, out / "tier_summary.csv")
    save_csv(quality_summary(checks, selected), out / "quality_summary.csv")
    save_json(filters, out / "filter_options.json")
    save_json(data_contract(args.include_mentions, args.include_full_review_text), out / "data_contract.json")
    if args.include_mentions:
        save_csv(mentions_df, out / "mention_examples.csv")
    save_json(summary, out / "dashboard_export_summary.json")
    print(f"Output dir: {out}")

    print_section("Final checks")
    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, allow_nan=False))
    if args.strict and not all(checks.values()):
        print("\nExport completed with failed checks and --strict enabled.")
        return 1
    print("\nYelp dashboard export completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
