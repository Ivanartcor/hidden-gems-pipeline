"""Run demo queries over the Hidden Gems AI ranking views.

This script assumes that db/ddl/08_ai_views.sql has already been executed and
that the AI prototype data has been loaded into PostgreSQL.

It is intended as a lightweight demo / validation layer, not as a loader.

Recommended PowerShell execution from repository root:

    python -m scripts.query_ai_ranking_demo

With custom top size:

    python -m scripts.query_ai_ranking_demo `
      --top-n 20

Export CSV outputs:

    python -m scripts.query_ai_ranking_demo `
      --top-n 50 `
      --export-dir data/artifacts/ai/query_demo

Inspect a concrete candidate and its supporting mentions:

    python -m scripts.query_ai_ranking_demo `
      --place-name "Sushi Ushi" `
      --dish-name "sushi" `
      --include-mentions `
      --mentions-top-n 25

Filter by text contained in address/city:

    python -m scripts.query_ai_ranking_demo `
      --city "New Orleans" `
      --top-n 30
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from src.db.database import engine


DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_RANKING_SCOPE = "yelp_prototype"
DEFAULT_TOP_N = 30
DEFAULT_MENTIONS_TOP_N = 25

ALLOWED_SCHEMA_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------

def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not ALLOWED_SCHEMA_PATTERN.match(schema):
        raise ValueError(f"Invalid schema name: {schema!r}")
    return schema


def make_json_safe(value: Any) -> Any:
    if isinstance(value, (list, dict, tuple, set)):
        return value

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    if isinstance(value, Path):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def df_to_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for record in df.to_dict(orient="records"):
        records.append({str(k): make_json_safe(v) for k, v in record.items()})
    return records


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def print_df(df: pd.DataFrame, title: str, max_rows: int | None = None) -> None:
    print_section(title)
    if df.empty:
        print("No rows returned.")
        return

    if max_rows is not None:
        print(df.head(max_rows).to_string(index=False))
    else:
        print(df.to_string(index=False))


def save_outputs(export_dir: Path, outputs: dict[str, pd.DataFrame], summary: dict[str, Any]) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)

    for name, df in outputs.items():
        path = export_dir / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"CSV saved: {path}")

    summary_path = export_dir / "query_ai_ranking_demo_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"JSON summary saved: {summary_path}")


# -----------------------------------------------------------------------------
# Query builders
# -----------------------------------------------------------------------------

def build_text_filters(
    *,
    place_name: str | None = None,
    dish_name: str | None = None,
    city: str | None = None,
    tier: str | None = None,
    prefix: str = "",
) -> tuple[str, dict[str, Any]]:
    clauses: list[str] = []
    params: dict[str, Any] = {}

    col_prefix = f"{prefix}." if prefix else ""

    if place_name:
        clauses.append(f"{col_prefix}place_name ILIKE :place_name")
        params["place_name"] = f"%{place_name.strip()}%"

    if dish_name:
        clauses.append(f"{col_prefix}dish_name ILIKE :dish_name")
        params["dish_name"] = f"%{dish_name.strip()}%"

    if city:
        # The Yelp prototype does not have normalized city/state columns in the core place table.
        # The city filter is therefore applied as text search over address_text.
        clauses.append(f"{col_prefix}address_text ILIKE :city")
        params["city"] = f"%{city.strip()}%"

    if tier:
        clauses.append(f"{col_prefix}hidden_gem_tier = :tier")
        params["tier"] = tier.strip()

    if not clauses:
        return "", params

    return " AND " + " AND ".join(clauses), params


def query_health(schema: str, ranking_scope: str) -> pd.DataFrame:
    sql = f"""
    SELECT
        'selected_candidates' AS metric,
        COUNT(*)::bigint AS value
    FROM {schema}.vw_ai_hidden_gem_candidate_detail
    WHERE ranking_scope = :ranking_scope
      AND is_selected = TRUE

    UNION ALL

    SELECT
        'places_with_selected_candidates' AS metric,
        COUNT(DISTINCT place_id)::bigint AS value
    FROM {schema}.vw_ai_hidden_gem_candidate_detail
    WHERE ranking_scope = :ranking_scope
      AND is_selected = TRUE

    UNION ALL

    SELECT
        'dishes_with_selected_candidates' AS metric,
        COUNT(DISTINCT dish_id)::bigint AS value
    FROM {schema}.vw_ai_hidden_gem_candidate_detail
    WHERE ranking_scope = :ranking_scope
      AND is_selected = TRUE

    UNION ALL

    SELECT
        'mentions_with_sentiment' AS metric,
        COUNT(*)::bigint AS value
    FROM {schema}.vw_ai_dish_mentions_with_sentiment

    UNION ALL

    SELECT
        'rankable_place_dish_signals' AS metric,
        COUNT(*)::bigint AS value
    FROM {schema}.vw_ai_dish_place_signals
    WHERE is_rankable_candidate = TRUE;
    """
    return read_df(sql, {"ranking_scope": ranking_scope})


def query_top_candidates(
    schema: str,
    ranking_scope: str,
    top_n: int,
    *,
    place_name: str | None = None,
    dish_name: str | None = None,
    city: str | None = None,
    tier: str | None = None,
) -> pd.DataFrame:
    extra_where, filter_params = build_text_filters(
        place_name=place_name,
        dish_name=dish_name,
        city=city,
        tier=tier,
    )

    sql = f"""
    SELECT
        hidden_gem_selected_rank,
        hidden_gem_tier,
        place_name,
        address_text,
        dish_name,
        hidden_gem_score,
        mention_count,
        review_count,
        positive_ratio,
        negative_ratio,
        bayesian_sentiment_score,
        confidence_weighted_sentiment,
        evidence_tier,
        aggregate_quality_tier,
        ranking_explanation
    FROM {schema}.vw_ai_hidden_gems_yelp_top
    WHERE ranking_scope = :ranking_scope
      {extra_where}
    ORDER BY hidden_gem_selected_rank NULLS LAST, hidden_gem_score DESC
    LIMIT :top_n;
    """

    params = {
        "ranking_scope": ranking_scope,
        "top_n": top_n,
        **filter_params,
    }
    return read_df(sql, params)


def query_place_summary(
    schema: str,
    ranking_scope: str,
    top_n: int,
    *,
    city: str | None = None,
) -> pd.DataFrame:
    extra_where = ""
    params: dict[str, Any] = {"ranking_scope": ranking_scope, "top_n": top_n}

    if city:
        extra_where = " AND address_text ILIKE :city"
        params["city"] = f"%{city.strip()}%"

    sql = f"""
    SELECT
        place_name,
        address_text,
        selected_candidate_count,
        top_hidden_gem_count,
        strong_hidden_gem_count,
        promising_hidden_gem_count,
        exploratory_hidden_gem_count,
        avg_hidden_gem_score,
        max_hidden_gem_score,
        top_dish_name,
        top_hidden_gem_tier,
        top_ranking_explanation
    FROM {schema}.vw_ai_hidden_gems_place_summary
    WHERE ranking_scope = :ranking_scope
      {extra_where}
    ORDER BY max_hidden_gem_score DESC, selected_candidate_count DESC, place_name
    LIMIT :top_n;
    """
    return read_df(sql, params)


def query_dish_summary(schema: str, ranking_scope: str, top_n: int) -> pd.DataFrame:
    sql = f"""
    SELECT
        dish_name,
        selected_place_count,
        distinct_places,
        top_hidden_gem_count,
        strong_hidden_gem_count,
        promising_hidden_gem_count,
        exploratory_hidden_gem_count,
        avg_hidden_gem_score,
        max_hidden_gem_score,
        total_mentions,
        total_reviews,
        avg_positive_ratio,
        avg_negative_ratio,
        top_place_name,
        top_place_address,
        top_ranking_explanation
    FROM {schema}.vw_ai_hidden_gems_dish_summary
    WHERE ranking_scope = :ranking_scope
    ORDER BY max_hidden_gem_score DESC, selected_place_count DESC, dish_name
    LIMIT :top_n;
    """
    return read_df(sql, {"ranking_scope": ranking_scope, "top_n": top_n})


def query_city_summary(schema: str, ranking_scope: str, top_n: int) -> pd.DataFrame:
    sql = f"""
    SELECT
        inferred_city,
        inferred_state_zip,
        selected_candidate_count,
        distinct_places,
        distinct_dishes,
        top_hidden_gem_count,
        strong_hidden_gem_count,
        promising_hidden_gem_count,
        exploratory_hidden_gem_count,
        avg_hidden_gem_score,
        max_hidden_gem_score,
        top_place_name,
        top_dish_name,
        top_ranking_explanation
    FROM {schema}.vw_ai_hidden_gems_city_summary
    WHERE ranking_scope = :ranking_scope
    ORDER BY max_hidden_gem_score DESC, selected_candidate_count DESC
    LIMIT :top_n;
    """
    return read_df(sql, {"ranking_scope": ranking_scope, "top_n": top_n})


def query_candidate_detail(
    schema: str,
    ranking_scope: str,
    top_n: int,
    *,
    place_name: str | None = None,
    dish_name: str | None = None,
    city: str | None = None,
    tier: str | None = None,
) -> pd.DataFrame:
    extra_where, filter_params = build_text_filters(
        place_name=place_name,
        dish_name=dish_name,
        city=city,
        tier=tier,
    )

    sql = f"""
    SELECT
        hidden_gem_candidate_id,
        hidden_gem_selected_rank,
        hidden_gem_tier,
        is_selected,
        is_production_ready,
        human_review_status,
        place_id,
        place_name,
        address_text,
        dish_id,
        dish_name,
        hidden_gem_score,
        hidden_gem_score_base,
        mention_count,
        review_count,
        positive_mentions,
        neutral_mentions,
        negative_mentions,
        positive_ratio,
        negative_ratio,
        avg_ner_confidence,
        avg_sentiment_confidence,
        total_signal_weight,
        confidence_weighted_sentiment,
        bayesian_sentiment_score,
        evidence_tier,
        aggregate_quality_tier,
        local_sentiment_component,
        evidence_component,
        confidence_component,
        positive_balance_component,
        rarity_component,
        local_outperformance_component,
        hiddenness_component,
        ranking_explanation
    FROM {schema}.vw_ai_hidden_gem_candidate_detail
    WHERE ranking_scope = :ranking_scope
      AND is_selected = TRUE
      {extra_where}
    ORDER BY hidden_gem_selected_rank NULLS LAST, hidden_gem_score DESC
    LIMIT :top_n;
    """
    params = {"ranking_scope": ranking_scope, "top_n": top_n, **filter_params}
    return read_df(sql, params)


def query_mentions_for_candidate(
    schema: str,
    place_id: str,
    dish_id: str,
    top_n: int,
) -> pd.DataFrame:
    sql = f"""
    SELECT
        place_name,
        dish_name,
        source_review_id,
        rating_value,
        review_created_at,
        mention_text,
        sentiment_label,
        sentiment_score,
        sentiment_confidence,
        sentiment_reliability_tier,
        sentiment_reason,
        target_clause_context,
        near_mention_context,
        review_text_raw
    FROM {schema}.vw_ai_dish_mentions_with_sentiment
    WHERE place_id = CAST(:place_id AS uuid)
      AND dish_id = CAST(:dish_id AS uuid)
    ORDER BY
        CASE sentiment_reliability_tier
            WHEN 'high' THEN 3
            WHEN 'medium' THEN 2
            WHEN 'low' THEN 1
            ELSE 0
        END DESC,
        sentiment_confidence DESC NULLS LAST
    LIMIT :top_n;
    """
    return read_df(sql, {"place_id": place_id, "dish_id": dish_id, "top_n": top_n})


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run demo queries over the Hidden Gems AI ranking views."
    )
    parser.add_argument("--schema", default=DEFAULT_SCHEMA, help="Database schema name.")
    parser.add_argument(
        "--ranking-scope",
        default=DEFAULT_RANKING_SCOPE,
        help="Ranking scope to query. Default: yelp_prototype.",
    )
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N, help="Rows per top query.")
    parser.add_argument(
        "--place-name",
        default=None,
        help="Optional text filter over place_name for candidate/detail queries.",
    )
    parser.add_argument(
        "--dish-name",
        default=None,
        help="Optional text filter over dish_name for candidate/detail queries.",
    )
    parser.add_argument(
        "--city",
        default=None,
        help="Optional text filter over address_text for city-like filtering in Yelp prototype.",
    )
    parser.add_argument(
        "--tier",
        default=None,
        choices=[
            "top_hidden_gem",
            "strong_hidden_gem",
            "promising_hidden_gem",
            "exploratory_hidden_gem",
        ],
        help="Optional hidden_gem_tier filter.",
    )
    parser.add_argument(
        "--include-mentions",
        action="store_true",
        help="Also print supporting mentions for the first matching candidate.",
    )
    parser.add_argument(
        "--mentions-top-n",
        type=int,
        default=DEFAULT_MENTIONS_TOP_N,
        help="Number of supporting mentions to print when --include-mentions is used.",
    )
    parser.add_argument(
        "--export-dir",
        type=Path,
        default=None,
        help="Optional directory where CSV outputs and JSON summary will be saved.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    schema = validate_schema_name(args.schema)
    ranking_scope = str(args.ranking_scope).strip()
    top_n = max(1, int(args.top_n))
    mentions_top_n = max(1, int(args.mentions_top_n))

    print_section("Hidden Gems AI ranking demo")
    print(f"schema: {schema}")
    print(f"ranking_scope: {ranking_scope}")
    print(f"top_n: {top_n}")
    print(f"place_name filter: {args.place_name}")
    print(f"dish_name filter: {args.dish_name}")
    print(f"city/address filter: {args.city}")
    print(f"tier filter: {args.tier}")

    outputs: dict[str, pd.DataFrame] = {}

    health_df = query_health(schema, ranking_scope)
    outputs["health"] = health_df
    print_df(health_df, "1. Health summary")

    top_candidates_df = query_top_candidates(
        schema,
        ranking_scope,
        top_n,
        place_name=args.place_name,
        dish_name=args.dish_name,
        city=args.city,
        tier=args.tier,
    )
    outputs["top_candidates"] = top_candidates_df
    print_df(top_candidates_df, "2. Top Hidden Gems candidates")

    place_summary_df = query_place_summary(
        schema,
        ranking_scope,
        top_n,
        city=args.city,
    )
    outputs["place_summary"] = place_summary_df
    print_df(place_summary_df, "3. Top places by selected candidates")

    dish_summary_df = query_dish_summary(schema, ranking_scope, top_n)
    outputs["dish_summary"] = dish_summary_df
    print_df(dish_summary_df, "4. Top dishes in selected candidates")

    city_summary_df = query_city_summary(schema, ranking_scope, top_n)
    outputs["city_summary"] = city_summary_df
    print_df(city_summary_df, "5. Top city/address summaries")

    candidate_detail_df = query_candidate_detail(
        schema,
        ranking_scope,
        top_n,
        place_name=args.place_name,
        dish_name=args.dish_name,
        city=args.city,
        tier=args.tier,
    )
    outputs["candidate_detail"] = candidate_detail_df
    print_df(candidate_detail_df, "6. Candidate detail")

    mentions_df = pd.DataFrame()
    if args.include_mentions:
        if candidate_detail_df.empty:
            print_section("7. Supporting mentions")
            print("No matching candidate found; supporting mentions were not queried.")
        else:
            first_candidate = candidate_detail_df.iloc[0]
            place_id = str(first_candidate["place_id"])
            dish_id = str(first_candidate["dish_id"])
            mentions_df = query_mentions_for_candidate(schema, place_id, dish_id, mentions_top_n)
            outputs["supporting_mentions"] = mentions_df
            print_df(
                mentions_df,
                "7. Supporting mentions for first matching candidate",
            )

    summary = {
        "script": "query_ai_ranking_demo",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "schema": schema,
        "ranking_scope": ranking_scope,
        "filters": {
            "top_n": top_n,
            "place_name": args.place_name,
            "dish_name": args.dish_name,
            "city": args.city,
            "tier": args.tier,
            "include_mentions": bool(args.include_mentions),
            "mentions_top_n": mentions_top_n,
        },
        "row_counts": {
            name: int(len(df))
            for name, df in outputs.items()
        },
        "top_candidate_preview": df_to_records(top_candidates_df.head(5)),
        "candidate_detail_preview": df_to_records(candidate_detail_df.head(5)),
    }

    if args.export_dir is not None:
        save_outputs(args.export_dir, outputs, summary)

    print_section("Done")
    print("AI ranking demo queries completed successfully.")


if __name__ == "__main__":
    main()
