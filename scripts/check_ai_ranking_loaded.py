"""Check loaded AI signals and Hidden Gems ranking in PostgreSQL.

This script validates the final state after loading:

- hidden_gems.dish_mention
- hidden_gems.dish_mention_sentiment
- hidden_gems.dish_place_signal
- hidden_gems.hidden_gem_candidate

Recommended PowerShell execution from repository root:

    python -m scripts.check_ai_ranking_loaded

With JSON report:

    python -m scripts.check_ai_ranking_loaded `
      --report-path data/artifacts/ai/ranking/check_ai_ranking_loaded_report.json

Optional filters:

    python -m scripts.check_ai_ranking_loaded `
      --ranking-scope yelp_prototype `
      --top-n 50
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

from src.db.database import engine


DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_RANKING_SCOPE = "yelp_prototype"
DEFAULT_TOP_N = 30


def make_json_safe(value: Any) -> Any:
    if pd.isna(value) if not isinstance(value, (list, dict, tuple, set)) else False:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, Path):
        return str(value)
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
    print("\n" + "=" * 96)
    print(title)
    print("=" * 96)


def build_report(schema: str, ranking_scope: str, top_n: int) -> dict[str, Any]:
    params = {"schema": schema, "ranking_scope": ranking_scope, "top_n": top_n}

    # ------------------------------------------------------------------
    # Basic counts
    # ------------------------------------------------------------------
    counts_sql = f"""
    SELECT 'dish' AS table_name, COUNT(*)::bigint AS row_count FROM {schema}.dish
    UNION ALL
    SELECT 'dish_alias', COUNT(*)::bigint FROM {schema}.dish_alias
    UNION ALL
    SELECT 'dish_mention', COUNT(*)::bigint FROM {schema}.dish_mention
    UNION ALL
    SELECT 'dish_mention_sentiment', COUNT(*)::bigint FROM {schema}.dish_mention_sentiment
    UNION ALL
    SELECT 'dish_place_signal', COUNT(*)::bigint FROM {schema}.dish_place_signal
    UNION ALL
    SELECT 'hidden_gem_candidate', COUNT(*)::bigint FROM {schema}.hidden_gem_candidate
    UNION ALL
    SELECT 'place', COUNT(*)::bigint FROM {schema}.place
    UNION ALL
    SELECT 'review', COUNT(*)::bigint FROM {schema}.review
    ORDER BY table_name;
    """
    basic_counts_df = read_df(counts_sql)

    # ------------------------------------------------------------------
    # Mention and sentiment distribution
    # ------------------------------------------------------------------
    mention_summary_sql = f"""
    SELECT
        COUNT(DISTINCT dm.dish_mention_id)::bigint AS dish_mentions,
        COUNT(DISTINCT dm.review_id)::bigint AS reviews_with_mentions,
        COUNT(DISTINCT dm.place_id)::bigint AS places_with_mentions,
        COUNT(DISTINCT dm.dish_id)::bigint AS dishes_mentioned,
        AVG(dm.ner_confidence_mean)::numeric(10,5) AS avg_ner_confidence
    FROM {schema}.dish_mention dm;
    """
    mention_summary_df = read_df(mention_summary_sql)

    sentiment_distribution_sql = f"""
    SELECT
        dms.sentiment_label,
        dms.sentiment_reliability_tier,
        COUNT(*)::bigint AS count_rows,
        AVG(dms.sentiment_confidence)::numeric(10,5) AS avg_sentiment_confidence
    FROM {schema}.dish_mention_sentiment dms
    GROUP BY dms.sentiment_label, dms.sentiment_reliability_tier
    ORDER BY dms.sentiment_label, dms.sentiment_reliability_tier;
    """
    sentiment_distribution_df = read_df(sentiment_distribution_sql)

    # ------------------------------------------------------------------
    # Signal distribution
    # ------------------------------------------------------------------
    signal_summary_sql = f"""
    SELECT
        COUNT(*)::bigint AS total_signals,
        COUNT(DISTINCT place_id)::bigint AS places_with_signals,
        COUNT(DISTINCT dish_id)::bigint AS dishes_with_signals,
        SUM(CASE WHEN is_rankable_candidate THEN 1 ELSE 0 END)::bigint AS rankable_signals,
        AVG(confidence_weighted_sentiment)::numeric(10,5) AS avg_confidence_weighted_sentiment,
        AVG(bayesian_sentiment_score)::numeric(10,5) AS avg_bayesian_sentiment_score
    FROM {schema}.dish_place_signal;
    """
    signal_summary_df = read_df(signal_summary_sql)

    signal_tiers_sql = f"""
    SELECT
        evidence_tier,
        aggregate_quality_tier,
        is_rankable_candidate,
        COUNT(*)::bigint AS count_rows
    FROM {schema}.dish_place_signal
    GROUP BY evidence_tier, aggregate_quality_tier, is_rankable_candidate
    ORDER BY count_rows DESC;
    """
    signal_tiers_df = read_df(signal_tiers_sql)

    # ------------------------------------------------------------------
    # Ranking distribution
    # ------------------------------------------------------------------
    ranking_summary_sql = f"""
    SELECT
        ranking_scope,
        ranking_version,
        COUNT(*)::bigint AS total_candidates,
        SUM(CASE WHEN is_selected THEN 1 ELSE 0 END)::bigint AS selected_candidates,
        MIN(hidden_gem_score)::numeric(10,5) AS min_score,
        AVG(hidden_gem_score)::numeric(10,5) AS avg_score,
        MAX(hidden_gem_score)::numeric(10,5) AS max_score,
        SUM(CASE WHEN is_production_ready THEN 1 ELSE 0 END)::bigint AS production_ready_rows
    FROM {schema}.hidden_gem_candidate
    GROUP BY ranking_scope, ranking_version
    ORDER BY ranking_scope, ranking_version;
    """
    ranking_summary_df = read_df(ranking_summary_sql)

    ranking_tiers_sql = f"""
    SELECT
        hidden_gem_tier,
        is_selected,
        COUNT(*)::bigint AS count_rows,
        MIN(hidden_gem_score)::numeric(10,5) AS min_score,
        AVG(hidden_gem_score)::numeric(10,5) AS avg_score,
        MAX(hidden_gem_score)::numeric(10,5) AS max_score
    FROM {schema}.hidden_gem_candidate
    WHERE ranking_scope = :ranking_scope
    GROUP BY hidden_gem_tier, is_selected
    ORDER BY is_selected DESC, avg_score DESC;
    """
    ranking_tiers_df = read_df(ranking_tiers_sql, {"ranking_scope": ranking_scope})

    top_candidates_sql = f"""
    SELECT
        hgc.hidden_gem_selected_rank,
        hgc.hidden_gem_tier,
        p.canonical_name AS place_name,
        p.address_text,
        d.canonical_name AS dish_name,
        hgc.hidden_gem_score,
        hgc.hidden_gem_score_base,
        dps.mention_count,
        dps.review_count,
        dps.positive_ratio,
        dps.negative_ratio,
        dps.bayesian_sentiment_score,
        dps.evidence_tier,
        dps.aggregate_quality_tier,
        hgc.ranking_explanation
    FROM {schema}.hidden_gem_candidate hgc
    JOIN {schema}.place p
        ON p.place_id = hgc.place_id
    JOIN {schema}.dish d
        ON d.dish_id = hgc.dish_id
    LEFT JOIN {schema}.dish_place_signal dps
        ON dps.dish_place_signal_id = hgc.dish_place_signal_id
    WHERE hgc.ranking_scope = :ranking_scope
      AND hgc.is_selected = TRUE
    ORDER BY hgc.hidden_gem_selected_rank NULLS LAST, hgc.hidden_gem_score DESC
    LIMIT :top_n;
    """
    top_candidates_df = read_df(top_candidates_sql, {"ranking_scope": ranking_scope, "top_n": top_n})

    # ------------------------------------------------------------------
    # Integrity checks
    # ------------------------------------------------------------------
    integrity_sql = f"""
    SELECT
        (SELECT COUNT(*) FROM {schema}.dish_mention dm
         LEFT JOIN {schema}.review r ON r.review_id = dm.review_id
         WHERE r.review_id IS NULL)::bigint AS orphan_dish_mentions_review,

        (SELECT COUNT(*) FROM {schema}.dish_mention dm
         LEFT JOIN {schema}.place p ON p.place_id = dm.place_id
         WHERE p.place_id IS NULL)::bigint AS orphan_dish_mentions_place,

        (SELECT COUNT(*) FROM {schema}.dish_mention dm
         LEFT JOIN {schema}.dish d ON d.dish_id = dm.dish_id
         WHERE dm.dish_id IS NOT NULL AND d.dish_id IS NULL)::bigint AS orphan_dish_mentions_dish,

        (SELECT COUNT(*) FROM {schema}.dish_mention_sentiment dms
         LEFT JOIN {schema}.dish_mention dm ON dm.dish_mention_id = dms.dish_mention_id
         WHERE dm.dish_mention_id IS NULL)::bigint AS orphan_sentiments_mention,

        (SELECT COUNT(*) FROM {schema}.dish_place_signal dps
         LEFT JOIN {schema}.place p ON p.place_id = dps.place_id
         WHERE p.place_id IS NULL)::bigint AS orphan_signals_place,

        (SELECT COUNT(*) FROM {schema}.dish_place_signal dps
         LEFT JOIN {schema}.dish d ON d.dish_id = dps.dish_id
         WHERE d.dish_id IS NULL)::bigint AS orphan_signals_dish,

        (SELECT COUNT(*) FROM {schema}.hidden_gem_candidate hgc
         LEFT JOIN {schema}.dish_place_signal dps ON dps.dish_place_signal_id = hgc.dish_place_signal_id
         WHERE hgc.dish_place_signal_id IS NOT NULL AND dps.dish_place_signal_id IS NULL)::bigint AS orphan_candidates_signal,

        (SELECT COUNT(*) FROM {schema}.hidden_gem_candidate hgc
         WHERE hgc.ranking_scope = :ranking_scope AND hgc.neighborhood_id IS NOT NULL)::bigint AS candidates_with_neighborhood,

        (SELECT COUNT(*) FROM {schema}.hidden_gem_candidate hgc
         WHERE hgc.ranking_scope = :ranking_scope AND hgc.is_production_ready = TRUE)::bigint AS production_ready_candidates
    ;
    """
    integrity_df = read_df(integrity_sql, {"ranking_scope": ranking_scope})

    # ------------------------------------------------------------------
    # Top dishes and places in selected ranking
    # ------------------------------------------------------------------
    top_dishes_sql = f"""
    SELECT
        d.canonical_name AS dish_name,
        COUNT(*)::bigint AS selected_count,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_hidden_gem_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_hidden_gem_score
    FROM {schema}.hidden_gem_candidate hgc
    JOIN {schema}.dish d ON d.dish_id = hgc.dish_id
    WHERE hgc.ranking_scope = :ranking_scope
      AND hgc.is_selected = TRUE
    GROUP BY d.canonical_name
    ORDER BY selected_count DESC, max_hidden_gem_score DESC
    LIMIT :top_n;
    """
    top_dishes_df = read_df(top_dishes_sql, {"ranking_scope": ranking_scope, "top_n": top_n})

    top_places_sql = f"""
    SELECT
        p.canonical_name AS place_name,
        COUNT(*)::bigint AS selected_count,
        AVG(hgc.hidden_gem_score)::numeric(10,5) AS avg_hidden_gem_score,
        MAX(hgc.hidden_gem_score)::numeric(10,5) AS max_hidden_gem_score
    FROM {schema}.hidden_gem_candidate hgc
    JOIN {schema}.place p ON p.place_id = hgc.place_id
    WHERE hgc.ranking_scope = :ranking_scope
      AND hgc.is_selected = TRUE
    GROUP BY p.canonical_name
    ORDER BY selected_count DESC, max_hidden_gem_score DESC
    LIMIT :top_n;
    """
    top_places_df = read_df(top_places_sql, {"ranking_scope": ranking_scope, "top_n": top_n})

    errors: list[str] = []
    warnings: list[str] = []

    integrity_record = integrity_df.iloc[0].to_dict() if len(integrity_df) else {}
    for key, value in integrity_record.items():
        numeric_value = int(value or 0)
        if key.startswith("orphan_") and numeric_value > 0:
            errors.append(f"Integrity issue: {key} = {numeric_value}")

    if int(integrity_record.get("production_ready_candidates", 0) or 0) > 0 and ranking_scope == "yelp_prototype":
        warnings.append("Yelp prototype ranking contains production-ready rows. Expected 0.")

    if int(integrity_record.get("candidates_with_neighborhood", 0) or 0) > 0 and ranking_scope == "yelp_prototype":
        warnings.append("Yelp prototype ranking contains neighborhood-linked rows. This may be unexpected for prototype data.")

    selected_count = 0
    if len(ranking_summary_df):
        scoped_rows = ranking_summary_df[ranking_summary_df["ranking_scope"] == ranking_scope]
        if len(scoped_rows):
            selected_count = int(scoped_rows["selected_candidates"].iloc[0] or 0)
    if selected_count == 0:
        warnings.append(f"No selected candidates found for ranking_scope={ranking_scope}.")

    report = {
        "schema": schema,
        "ranking_scope": ranking_scope,
        "top_n": top_n,
        "basic_counts": df_to_records(basic_counts_df),
        "mention_summary": df_to_records(mention_summary_df),
        "sentiment_distribution": df_to_records(sentiment_distribution_df),
        "signal_summary": df_to_records(signal_summary_df),
        "signal_tiers": df_to_records(signal_tiers_df),
        "ranking_summary": df_to_records(ranking_summary_df),
        "ranking_tiers": df_to_records(ranking_tiers_df),
        "top_candidates": df_to_records(top_candidates_df),
        "top_dishes_selected": df_to_records(top_dishes_df),
        "top_places_selected": df_to_records(top_places_df),
        "integrity": df_to_records(integrity_df),
        "errors": errors,
        "warnings": warnings,
        "ready_for_querying_ai_ranking": len(errors) == 0 and selected_count > 0,
    }

    # Print human-readable output
    print_section("1. Basic counts")
    print(basic_counts_df.to_string(index=False))

    print_section("2. Mention summary")
    print(mention_summary_df.to_string(index=False))

    print_section("3. Sentiment distribution")
    print(sentiment_distribution_df.to_string(index=False))

    print_section("4. Signal summary")
    print(signal_summary_df.to_string(index=False))

    print_section("5. Ranking summary")
    print(ranking_summary_df.to_string(index=False))

    print_section(f"6. Ranking tiers for scope={ranking_scope}")
    print(ranking_tiers_df.to_string(index=False))

    print_section(f"7. Top {top_n} selected candidates")
    print(top_candidates_df.to_string(index=False))

    print_section("8. Integrity")
    print(integrity_df.to_string(index=False))

    print_section("9. Decision")
    print("ready_for_querying_ai_ranking:", report["ready_for_querying_ai_ranking"])
    print("errors:", errors)
    print("warnings:", warnings)

    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check loaded AI ranking data.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--ranking-scope", default=DEFAULT_RANKING_SCOPE)
    parser.add_argument("--top-n", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--report-path", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report(
        schema=args.schema,
        ranking_scope=args.ranking_scope,
        top_n=args.top_n,
    )

    if args.report_path is not None:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        with args.report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print("\nReport saved to:", args.report_path)


if __name__ == "__main__":
    main()
