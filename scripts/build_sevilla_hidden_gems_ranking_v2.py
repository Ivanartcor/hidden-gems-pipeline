#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Build Sevilla Hidden Gems Ranking v2.

This script builds the IA v2 Hidden Gems ranking from the place-dish signal layer
generated after:
    Hybrid + NER v2 -> Normalization reranker -> ABSA sentiment -> place-dish signals v2

Input:
    data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl

Outputs:
    data/artifacts/ai/sevilla/model_inference/ranking_v2/
        sevilla_hidden_gems_ranking_v2.csv
        sevilla_hidden_gems_ranking_v2.jsonl
        sevilla_hidden_gems_selected_v2.csv
        sevilla_hidden_gems_selected_v2.jsonl
        sevilla_hidden_gems_top_global_v2.csv
        sevilla_hidden_gems_top_by_district_v2.csv
        sevilla_hidden_gems_top_by_neighborhood_v2.csv
        sevilla_hidden_gems_top_by_dish_v2.csv
        sevilla_hidden_gems_manual_review_v2.csv
        sevilla_hidden_gems_tier_summary_v2.csv
        sevilla_hidden_gems_district_summary_v2.csv
        sevilla_hidden_gems_neighborhood_summary_v2.csv
        sevilla_hidden_gems_dish_summary_v2.csv
        sevilla_hidden_gems_ranking_v2_summary.json
        recommended_next_steps.md
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


PATCH_ID = "hidden_gems_ranking_v2_scoring_2026_05_14"
SCRIPT_NAME = "build_sevilla_hidden_gems_ranking_v2"
VERSION = "sevilla_hidden_gems_ranking_v2"
RANKING_SCOPE = "sevilla_ai_v2"


# ---------------------------------------------------------------------------
# IO and safe serialization
# ---------------------------------------------------------------------------

def json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return str(obj)
    try:
        import uuid
        if isinstance(obj, uuid.UUID):
            return str(obj)
    except Exception:
        pass
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if pd.isna(obj):
        return None
    return str(obj)


def to_builtin(value: Any) -> Any:
    """Recursively convert values into JSON-safe Python primitives."""
    if value is None:
        return None

    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]

    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()

    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)

    try:
        import uuid
        if isinstance(value, uuid.UUID):
            return str(value)
    except Exception:
        pass

    if isinstance(value, np.bool_):
        return bool(value)

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating, float)):
        value_f = float(value)
        if math.isnan(value_f) or math.isinf(value_f):
            return None
        return value_f

    if pd.isna(value):
        return None

    if isinstance(value, (str, int, bool)):
        return value

    return str(value)


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False, default=json_default)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            safe_row = to_builtin(row)
            f.write(json.dumps(safe_row, ensure_ascii=False, allow_nan=False, default=json_default) + "\n")


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data if isinstance(data, list) else data.get("rows", []))
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported input extension: {path.suffix}")


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def coerce_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.astype(str).str.lower().isin({"true", "1", "yes", "y", "t"})


def coerce_numeric(df: pd.DataFrame, columns: List[str], default: float = 0.0) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = default
        df[col] = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default)
    return df


def clip01(value: Any) -> Any:
    return np.clip(value, 0.0, 1.0)


def safe_divide(num: pd.Series, den: pd.Series, default: float = 0.0) -> pd.Series:
    den_safe = den.replace(0, np.nan)
    out = num / den_safe
    return out.replace([np.inf, -np.inf], np.nan).fillna(default)


def ensure_columns(df: pd.DataFrame, required_columns: List[str], strict: bool = True) -> List[str]:
    missing = [c for c in required_columns if c not in df.columns]
    if missing and strict:
        raise KeyError(f"Missing required input columns: {missing}")
    return missing


def value_counts_dict(series: pd.Series) -> Dict[str, int]:
    if len(series) == 0:
        return {}
    return {str(k): int(v) for k, v in series.value_counts(dropna=False).to_dict().items()}


def describe_numeric(series: pd.Series) -> Dict[str, float]:
    if len(series) == 0:
        return {}
    desc = pd.to_numeric(series, errors="coerce").dropna().describe()
    return {str(k): round(float(v), 6) for k, v in desc.to_dict().items()}


def parse_json_counter(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Ranking scoring
# ---------------------------------------------------------------------------

NUMERIC_COLUMNS = [
    "mention_count_v2",
    "review_count_v2",
    "weighted_mention_count_v2",
    "positive_count_v2",
    "neutral_count_v2",
    "negative_count_v2",
    "weighted_positive_count_v2",
    "weighted_neutral_count_v2",
    "weighted_negative_count_v2",
    "positive_ratio_v2",
    "neutral_ratio_v2",
    "negative_ratio_v2",
    "weighted_positive_ratio_v2",
    "weighted_neutral_ratio_v2",
    "weighted_negative_ratio_v2",
    "avg_absa_confidence_v2",
    "avg_absa_margin_v2",
    "avg_normalization_confidence_v2",
    "avg_combined_mention_confidence_v2",
    "avg_mention_weight_v2",
    "min_mention_weight_v2",
    "avg_rating_v2",
    "weighted_sentiment_score_v2",
    "raw_avg_sentiment_score_v2",
    "hybrid_and_ner_count_v2",
    "hybrid_only_count_v2",
    "ner_only_count_v2",
    "ner_only_ratio_v2",
    "compound_mention_ratio_v2",
    "generic_exact_ratio_v2",
    "likely_fragment_ratio_v2",
    "needs_review_count_v2",
    "needs_review_ratio_v2",
]


REQUIRED_COLUMNS = [
    "place_id",
    "place_name",
    "district_id",
    "district_name",
    "neighborhood_id",
    "neighborhood_name",
    "dish_id_v2",
    "dish_display_name_v2",
    "signal_id_v2",
    "mention_count_v2",
    "review_count_v2",
    "weighted_mention_count_v2",
    "positive_ratio_v2",
    "negative_ratio_v2",
    "avg_absa_confidence_v2",
    "avg_normalization_confidence_v2",
    "weighted_sentiment_score_v2",
    "ready_for_ranking_v2",
    "evidence_tier_v2",
    "aggregate_quality_tier_v2",
]


def add_rank_components(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out = coerce_numeric(out, NUMERIC_COLUMNS, default=0.0)

    evidence_tier_map = {
        "weak": 0.25,
        "emerging": 0.55,
        "solid": 0.80,
        "strong": 1.00,
    }
    quality_tier_map = {
        "low": 0.25,
        "weak": 0.45,
        "medium": 0.72,
        "high": 0.92,
    }

    out["evidence_tier_score_v2"] = (
        out["evidence_tier_v2"].astype(str).str.lower().map(evidence_tier_map).fillna(0.25)
    )
    out["aggregate_quality_tier_score_v2"] = (
        out["aggregate_quality_tier_v2"].astype(str).str.lower().map(quality_tier_map).fillna(0.45)
    )

    # Sentiment component:
    # -1..1 -> 0..1. A strongly positive ABSA score is close to 1.
    out["ranking_sentiment_component_v2"] = clip01((out["weighted_sentiment_score_v2"] + 1.0) / 2.0)

    # Evidence: reviews matter more than raw mentions; tier captures the operational thresholds.
    review_score = clip01(np.log1p(out["review_count_v2"]) / np.log1p(6.0))
    mention_score = clip01(np.log1p(out["weighted_mention_count_v2"]) / np.log1p(8.0))
    out["ranking_evidence_component_v2"] = clip01(
        0.45 * review_score
        + 0.30 * mention_score
        + 0.25 * out["evidence_tier_score_v2"]
    )

    # Model/signal quality.
    out["ranking_quality_component_v2"] = clip01(
        0.35 * out["avg_absa_confidence_v2"]
        + 0.30 * out["avg_normalization_confidence_v2"]
        + 0.15 * out["avg_combined_mention_confidence_v2"]
        + 0.20 * out["aggregate_quality_tier_score_v2"]
    )

    # Consensus: both extractors agreeing is stronger than NER-only.
    total_strategy_count = (
        out["hybrid_and_ner_count_v2"]
        + out["hybrid_only_count_v2"]
        + out["ner_only_count_v2"]
    )
    hybrid_and_ner_ratio = safe_divide(out["hybrid_and_ner_count_v2"], total_strategy_count)
    hybrid_only_ratio = safe_divide(out["hybrid_only_count_v2"], total_strategy_count)
    ner_only_ratio = safe_divide(out["ner_only_count_v2"], total_strategy_count)

    out["ranking_consensus_component_v2"] = clip01(
        1.00 * hybrid_and_ner_ratio
        + 0.78 * hybrid_only_ratio
        + 0.55 * ner_only_ratio
    )

    # Uniqueness / hiddenness:
    # A dish found in fewer places gets a small bonus. Compounds also get a modest bonus.
    dish_place_counts = out.groupby("dish_id_v2")["place_id"].nunique()
    dish_signal_counts = out.groupby("dish_id_v2")["signal_id_v2"].nunique()

    out["dish_global_place_count_v2"] = out["dish_id_v2"].map(dish_place_counts).fillna(1).astype(float)
    out["dish_global_signal_count_v2"] = out["dish_id_v2"].map(dish_signal_counts).fillna(1).astype(float)

    max_dish_place_count = max(float(out["dish_global_place_count_v2"].max()), 2.0)
    dish_rarity = clip01(
        1.0 - (np.log1p(out["dish_global_place_count_v2"]) / np.log1p(max_dish_place_count))
    )
    compound_bonus = clip01(0.75 + 0.25 * out["compound_mention_ratio_v2"])

    out["ranking_uniqueness_component_v2"] = clip01(
        0.65 * dish_rarity
        + 0.35 * compound_bonus
    )

    # Rating is a weak prior, not the main signal.
    out["ranking_rating_component_v2"] = clip01((out["avg_rating_v2"] - 3.0) / 2.0)

    # Penalties.
    out["negative_sentiment_penalty_v2"] = clip01(
        0.14 * out["negative_ratio_v2"]
        + 0.08 * out["weighted_negative_ratio_v2"]
    )

    out["quality_risk_penalty_v2"] = clip01(
        0.12 * out["needs_review_ratio_v2"]
        + 0.12 * out["likely_fragment_ratio_v2"]
        + 0.06 * out["ner_only_ratio_v2"]
        + 0.05 * out["generic_exact_ratio_v2"]
    )

    out["low_evidence_penalty_v2"] = 0.0
    out.loc[out["review_count_v2"] < 2, "low_evidence_penalty_v2"] += 0.08
    out.loc[out["weighted_mention_count_v2"] < 1.2, "low_evidence_penalty_v2"] += 0.06

    # Main score.
    raw_score_0_1 = (
        0.34 * out["ranking_sentiment_component_v2"]
        + 0.22 * out["ranking_evidence_component_v2"]
        + 0.20 * out["ranking_quality_component_v2"]
        + 0.10 * out["ranking_consensus_component_v2"]
        + 0.09 * out["ranking_uniqueness_component_v2"]
        + 0.05 * out["ranking_rating_component_v2"]
        - out["negative_sentiment_penalty_v2"]
        - out["quality_risk_penalty_v2"]
        - out["low_evidence_penalty_v2"]
    )

    out["hidden_gem_score_v2"] = (clip01(raw_score_0_1) * 100.0).round(4)

    # Component scores for explainability.
    for col in [
        "ranking_sentiment_component_v2",
        "ranking_evidence_component_v2",
        "ranking_quality_component_v2",
        "ranking_consensus_component_v2",
        "ranking_uniqueness_component_v2",
        "ranking_rating_component_v2",
        "negative_sentiment_penalty_v2",
        "quality_risk_penalty_v2",
        "low_evidence_penalty_v2",
    ]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0).round(6)

    return out


def assign_tiers(
    df: pd.DataFrame,
    args: argparse.Namespace,
) -> pd.DataFrame:
    out = df.copy()

    out["ready_for_ranking_v2_bool"] = coerce_bool_series(out["ready_for_ranking_v2"])

    out["ranking_eligible_v2"] = (
        out["ready_for_ranking_v2_bool"]
        & (out["hidden_gem_score_v2"] >= args.min_score)
        & (out["review_count_v2"] >= args.min_reviews)
        & (out["mention_count_v2"] >= args.min_mentions)
        & (out["weighted_mention_count_v2"] >= args.min_weighted_mentions)
        & (out["negative_ratio_v2"] <= args.max_negative_ratio)
        & (out["needs_review_ratio_v2"] <= args.max_needs_review_ratio)
    )

    reasons: List[str] = []
    for _, row in out.iterrows():
        row_reasons = []
        if not bool(row["ready_for_ranking_v2_bool"]):
            row_reasons.append("input_signal_not_ready")
        if float(row["hidden_gem_score_v2"]) < args.min_score:
            row_reasons.append("score_below_min")
        if float(row["review_count_v2"]) < args.min_reviews:
            row_reasons.append("insufficient_reviews")
        if float(row["mention_count_v2"]) < args.min_mentions:
            row_reasons.append("insufficient_mentions")
        if float(row["weighted_mention_count_v2"]) < args.min_weighted_mentions:
            row_reasons.append("insufficient_weighted_mentions")
        if float(row["negative_ratio_v2"]) > args.max_negative_ratio:
            row_reasons.append("negative_ratio_too_high")
        if float(row["needs_review_ratio_v2"]) > args.max_needs_review_ratio:
            row_reasons.append("needs_review_ratio_too_high")
        reasons.append(";".join(row_reasons) if row_reasons else "eligible")

    out["ranking_eligibility_reasons_v2"] = reasons

    def tier(row: pd.Series) -> str:
        if not bool(row["ranking_eligible_v2"]):
            return "not_selected"
        score = float(row["hidden_gem_score_v2"])
        if score >= args.top_threshold:
            return "top_hidden_gem"
        if score >= args.strong_threshold:
            return "strong_hidden_gem"
        if score >= args.promising_threshold:
            return "promising_hidden_gem"
        if score >= args.exploratory_threshold:
            return "exploratory_hidden_gem"
        return "not_selected"

    out["hidden_gem_tier_v2"] = out.apply(tier, axis=1)
    out["selected_hidden_gem_v2"] = (
        out["ranking_eligible_v2"]
        & (out["hidden_gem_tier_v2"] != "not_selected")
    )

    # Production flag remains false for pilot IA v2.
    out["is_production_ready_v2"] = False

    return out


def add_ranks(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    sort_cols = [
        "selected_hidden_gem_v2",
        "hidden_gem_score_v2",
        "review_count_v2",
        "mention_count_v2",
        "weighted_sentiment_score_v2",
        "avg_absa_confidence_v2",
    ]
    ascending = [False, False, False, False, False, False]

    out = out.sort_values(sort_cols, ascending=ascending).reset_index(drop=True)

    out["hidden_gem_global_rank_v2"] = np.arange(1, len(out) + 1)

    selected_mask = coerce_bool_series(out["selected_hidden_gem_v2"])
    out["hidden_gem_selected_rank_v2"] = pd.NA
    out.loc[selected_mask, "hidden_gem_selected_rank_v2"] = np.arange(1, int(selected_mask.sum()) + 1)

    # Group ranks among selected rows. Non-selected remain NA.
    out["hidden_gem_district_rank_v2"] = pd.NA
    out["hidden_gem_neighborhood_rank_v2"] = pd.NA
    out["hidden_gem_dish_rank_v2"] = pd.NA

    selected_idx = out.index[selected_mask].tolist()
    selected = out.loc[selected_idx].copy()

    if len(selected):
        selected["hidden_gem_district_rank_v2"] = (
            selected.groupby("district_name")["hidden_gem_score_v2"]
            .rank(method="first", ascending=False)
            .astype(int)
        )
        selected["hidden_gem_neighborhood_rank_v2"] = (
            selected.groupby("neighborhood_name")["hidden_gem_score_v2"]
            .rank(method="first", ascending=False)
            .astype(int)
        )
        selected["hidden_gem_dish_rank_v2"] = (
            selected.groupby("dish_display_name_v2")["hidden_gem_score_v2"]
            .rank(method="first", ascending=False)
            .astype(int)
        )

        out.loc[selected.index, "hidden_gem_district_rank_v2"] = selected["hidden_gem_district_rank_v2"]
        out.loc[selected.index, "hidden_gem_neighborhood_rank_v2"] = selected["hidden_gem_neighborhood_rank_v2"]
        out.loc[selected.index, "hidden_gem_dish_rank_v2"] = selected["hidden_gem_dish_rank_v2"]

    return out


def build_explanation(row: pd.Series) -> str:
    dish = row.get("dish_display_name_v2", "plato")
    place = row.get("place_name", "local")
    score = float(row.get("hidden_gem_score_v2", 0.0))
    tier = row.get("hidden_gem_tier_v2", "not_selected")
    mentions = int(row.get("mention_count_v2", 0) or 0)
    reviews = int(row.get("review_count_v2", 0) or 0)
    pos_ratio = float(row.get("positive_ratio_v2", 0.0) or 0.0)
    neg_ratio = float(row.get("negative_ratio_v2", 0.0) or 0.0)
    evidence = row.get("evidence_tier_v2", "unknown")
    quality = row.get("aggregate_quality_tier_v2", "unknown")
    district = row.get("district_name", "")
    neighborhood = row.get("neighborhood_name", "")

    if tier == "not_selected":
        base = (
            f"{dish} en {place} obtiene {score:.1f}/100, pero no queda seleccionado en v2; "
            f"evidencia {evidence}, calidad {quality}, {mentions} menciones en {reviews} reviews."
        )
    else:
        base = (
            f"{dish} en {place} obtiene {score:.1f}/100 como {tier}; "
            f"{mentions} menciones en {reviews} reviews; "
            f"{pos_ratio * 100:.1f}% positivas y {neg_ratio * 100:.1f}% negativas; "
            f"evidencia {evidence}, calidad {quality}; "
            f"barrio {neighborhood}; distrito {district}."
        )

    risk_reasons = []
    if float(row.get("needs_review_ratio_v2", 0.0) or 0.0) > 0:
        risk_reasons.append("contiene señales revisables")
    if float(row.get("ner_only_ratio_v2", 0.0) or 0.0) > 0:
        risk_reasons.append("incluye menciones NER-only")
    if float(row.get("negative_ratio_v2", 0.0) or 0.0) > 0:
        risk_reasons.append("hay menciones negativas")

    if risk_reasons:
        base += " Atención: " + ", ".join(risk_reasons) + "."

    return base


def build_ranking(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    ranked = add_rank_components(df)
    ranked = assign_tiers(ranked, args)
    ranked = add_ranks(ranked)
    ranked["ranking_explanation_v2"] = ranked.apply(build_explanation, axis=1)
    ranked["ranking_scope_v2"] = args.ranking_scope
    ranked["ranking_version_v2"] = VERSION
    ranked["generated_at_utc_v2"] = datetime.now(timezone.utc).isoformat()
    return ranked


# ---------------------------------------------------------------------------
# Summaries and outputs
# ---------------------------------------------------------------------------

def build_tier_summary(ranking_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tier, group in ranking_df.groupby("hidden_gem_tier_v2", dropna=False):
        rows.append(
            {
                "hidden_gem_tier_v2": tier,
                "signal_count": int(len(group)),
                "selected_count": int(coerce_bool_series(group["selected_hidden_gem_v2"]).sum()),
                "place_count": int(group["place_id"].nunique()),
                "dish_count": int(group["dish_id_v2"].nunique()),
                "avg_score": round(float(group["hidden_gem_score_v2"].mean()), 6),
                "max_score": round(float(group["hidden_gem_score_v2"].max()), 6),
                "avg_review_count": round(float(group["review_count_v2"].mean()), 6),
                "avg_mention_count": round(float(group["mention_count_v2"].mean()), 6),
            }
        )
    return pd.DataFrame(rows).sort_values(["selected_count", "avg_score"], ascending=[False, False])


def summarize_group(ranking_df: pd.DataFrame, group_cols: List[str], top_n: int) -> pd.DataFrame:
    selected = ranking_df[coerce_bool_series(ranking_df["selected_hidden_gem_v2"])].copy()
    if len(selected) == 0:
        return pd.DataFrame(columns=group_cols)

    rows = []
    for keys, group in selected.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        record = {col: key for col, key in zip(group_cols, keys)}
        record.update(
            {
                "selected_count": int(len(group)),
                "selected_places": int(group["place_id"].nunique()),
                "selected_dishes": int(group["dish_id_v2"].nunique()),
                "avg_score": round(float(group["hidden_gem_score_v2"].mean()), 6),
                "max_score": round(float(group["hidden_gem_score_v2"].max()), 6),
                "avg_weighted_sentiment": round(float(group["weighted_sentiment_score_v2"].mean()), 6),
                "strong_or_top_count": int(group["hidden_gem_tier_v2"].isin(["top_hidden_gem", "strong_hidden_gem"]).sum()),
            }
        )
        rows.append(record)

    out = pd.DataFrame(rows)
    return out.sort_values(["strong_or_top_count", "max_score", "selected_count"], ascending=[False, False, False]).head(top_n)


def top_by_group(ranking_df: pd.DataFrame, group_cols: List[str], rank_col: str, top_per_group: int) -> pd.DataFrame:
    selected = ranking_df[coerce_bool_series(ranking_df["selected_hidden_gem_v2"])].copy()
    if len(selected) == 0:
        return selected

    selected = selected.sort_values(
        group_cols + ["hidden_gem_score_v2", "review_count_v2", "mention_count_v2"],
        ascending=[True] * len(group_cols) + [False, False, False],
    ).copy()
    selected[rank_col] = selected.groupby(group_cols).cumcount() + 1
    return selected[selected[rank_col] <= top_per_group].copy()


def choose_output_columns(df: pd.DataFrame) -> List[str]:
    preferred = [
        "hidden_gem_global_rank_v2",
        "hidden_gem_selected_rank_v2",
        "hidden_gem_district_rank_v2",
        "hidden_gem_neighborhood_rank_v2",
        "hidden_gem_dish_rank_v2",
        "selected_hidden_gem_v2",
        "hidden_gem_tier_v2",
        "hidden_gem_score_v2",
        "ranking_eligible_v2",
        "ranking_eligibility_reasons_v2",
        "place_id",
        "place_name",
        "district_id",
        "district_name",
        "neighborhood_id",
        "neighborhood_name",
        "dish_id_v2",
        "dish_display_name_v2",
        "dish_name_norm_v2",
        "signal_id_v2",
        "mention_count_v2",
        "review_count_v2",
        "weighted_mention_count_v2",
        "positive_count_v2",
        "neutral_count_v2",
        "negative_count_v2",
        "positive_ratio_v2",
        "neutral_ratio_v2",
        "negative_ratio_v2",
        "weighted_positive_ratio_v2",
        "weighted_negative_ratio_v2",
        "weighted_sentiment_score_v2",
        "avg_absa_confidence_v2",
        "avg_normalization_confidence_v2",
        "avg_combined_mention_confidence_v2",
        "avg_mention_weight_v2",
        "avg_rating_v2",
        "evidence_tier_v2",
        "aggregate_quality_tier_v2",
        "ready_for_ranking_v2",
        "source_strategy_mix_json",
        "hybrid_and_ner_count_v2",
        "hybrid_only_count_v2",
        "ner_only_count_v2",
        "ner_only_ratio_v2",
        "compound_mention_ratio_v2",
        "likely_fragment_ratio_v2",
        "needs_review_count_v2",
        "needs_review_ratio_v2",
        "dish_global_place_count_v2",
        "ranking_sentiment_component_v2",
        "ranking_evidence_component_v2",
        "ranking_quality_component_v2",
        "ranking_consensus_component_v2",
        "ranking_uniqueness_component_v2",
        "ranking_rating_component_v2",
        "negative_sentiment_penalty_v2",
        "quality_risk_penalty_v2",
        "low_evidence_penalty_v2",
        "example_mentions_v2",
        "example_review_ids_v2",
        "ranking_explanation_v2",
        "is_production_ready_v2",
        "ranking_scope_v2",
        "ranking_version_v2",
        "generated_at_utc_v2",
    ]
    return [c for c in preferred if c in df.columns]


def build_manual_review_df(ranking_df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    df = ranking_df.copy()

    needs_review = (
        (pd.to_numeric(df["needs_review_ratio_v2"], errors="coerce").fillna(0) > 0)
        | (pd.to_numeric(df["likely_fragment_ratio_v2"], errors="coerce").fillna(0) > 0)
        | (pd.to_numeric(df["ner_only_ratio_v2"], errors="coerce").fillna(0) > 0.5)
        | (pd.to_numeric(df["negative_ratio_v2"], errors="coerce").fillna(0) > 0.25)
        | (df["hidden_gem_score_v2"].between(args.exploratory_threshold - 3, args.exploratory_threshold + 3))
        | (df["hidden_gem_tier_v2"].isin(["top_hidden_gem", "strong_hidden_gem"]))
    )

    out = df[needs_review].copy()
    out["manual_review_priority_v2"] = "low"
    out.loc[
        out["hidden_gem_tier_v2"].isin(["top_hidden_gem", "strong_hidden_gem"])
        | (out["needs_review_ratio_v2"] > 0.4)
        | (out["negative_ratio_v2"] > 0.25),
        "manual_review_priority_v2",
    ] = "high"
    out.loc[
        (out["manual_review_priority_v2"] != "high")
        & (
            (out["hidden_gem_tier_v2"] == "promising_hidden_gem")
            | (out["ner_only_ratio_v2"] > 0.0)
            | (out["likely_fragment_ratio_v2"] > 0.0)
        ),
        "manual_review_priority_v2",
    ] = "medium"

    return out.sort_values(
        ["manual_review_priority_v2", "hidden_gem_score_v2", "needs_review_ratio_v2"],
        ascending=[True, False, False],
    )


def build_recommendations(summary: Dict[str, Any]) -> str:
    counts = summary.get("counts", {})
    selected = counts.get("selected_hidden_gem_candidates", 0)
    top = counts.get("top_hidden_gem_count", 0)
    strong = counts.get("strong_hidden_gem_count", 0)
    manual = counts.get("manual_review_rows", 0)

    return f"""# Sevilla Hidden Gems Ranking v2 - Recommended next steps

## Executive read

- Total place-dish signals scored: **{counts.get("total_signals_scored", 0)}**.
- Selected Hidden Gem candidates: **{selected}**.
- Top candidates: **{top}**.
- Strong candidates: **{strong}**.
- Manual review rows: **{manual}**.

## Interpretation

This is the IA v2 ranking built from trained model outputs:

```text
Hybrid + NER v2
→ normalization reranker
→ ABSA sentiment
→ place-dish signals v2
→ Hidden Gems ranking v2
```

The ranking is still experimental and should not be marked as production-ready.

## Recommended workflow

1. Review `sevilla_hidden_gems_selected_v2.csv`, especially `top_hidden_gem` and `strong_hidden_gem`.
2. Inspect `sevilla_hidden_gems_manual_review_v2.csv` before loading results into PostgreSQL.
3. Compare this ranking against the Sevilla ranking v1.
4. Check whether the new model pipeline improved:
   - compound dish preservation,
   - sentiment around the specific dish,
   - NER-only useful discoveries,
   - fewer false positives.
5. After review, create a loader script for IA v2 outputs or keep this as an artifact-only experiment.

## Files to inspect first

- `sevilla_hidden_gems_selected_v2.csv`
- `sevilla_hidden_gems_top_global_v2.csv`
- `sevilla_hidden_gems_manual_review_v2.csv`
- `sevilla_hidden_gems_top_by_district_v2.csv`
- `sevilla_hidden_gems_ranking_v2_summary.json`
"""


def create_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build Sevilla Hidden Gems ranking v2 from place-dish signals v2.")

    parser.add_argument(
        "--input-path",
        type=Path,
        default=Path("data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl"),
        help="Input place-dish signals v2 JSONL/CSV path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/artifacts/ai/sevilla/model_inference/ranking_v2"),
        help="Output directory.",
    )
    parser.add_argument("--ranking-scope", default=RANKING_SCOPE)

    # Eligibility thresholds.
    parser.add_argument("--min-score", type=float, default=55.0)
    parser.add_argument("--min-selected-score", type=float, default=65.0)
    parser.add_argument("--min-mentions", type=int, default=2)
    parser.add_argument("--min-reviews", type=int, default=2)
    parser.add_argument("--min-weighted-mentions", type=float, default=1.2)
    parser.add_argument("--max-negative-ratio", type=float, default=0.50)
    parser.add_argument("--max-needs-review-ratio", type=float, default=0.60)

    # Tier thresholds.
    parser.add_argument("--top-threshold", type=float, default=88.0)
    parser.add_argument("--strong-threshold", type=float, default=82.0)
    parser.add_argument("--promising-threshold", type=float, default=75.0)
    parser.add_argument("--exploratory-threshold", type=float, default=65.0)

    # Output controls.
    parser.add_argument("--top-global-limit", type=int, default=150)
    parser.add_argument("--top-per-group", type=int, default=10)
    parser.add_argument("--summary-group-limit", type=int, default=9999)
    parser.add_argument("--strict", action="store_true", help="Fail if critical checks fail.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = create_arg_parser().parse_args(argv)

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "ranking_csv": output_dir / "sevilla_hidden_gems_ranking_v2.csv",
        "ranking_jsonl": output_dir / "sevilla_hidden_gems_ranking_v2.jsonl",
        "selected_csv": output_dir / "sevilla_hidden_gems_selected_v2.csv",
        "selected_jsonl": output_dir / "sevilla_hidden_gems_selected_v2.jsonl",
        "top_global_csv": output_dir / "sevilla_hidden_gems_top_global_v2.csv",
        "top_by_district_csv": output_dir / "sevilla_hidden_gems_top_by_district_v2.csv",
        "top_by_neighborhood_csv": output_dir / "sevilla_hidden_gems_top_by_neighborhood_v2.csv",
        "top_by_dish_csv": output_dir / "sevilla_hidden_gems_top_by_dish_v2.csv",
        "manual_review_csv": output_dir / "sevilla_hidden_gems_manual_review_v2.csv",
        "tier_summary_csv": output_dir / "sevilla_hidden_gems_tier_summary_v2.csv",
        "district_summary_csv": output_dir / "sevilla_hidden_gems_district_summary_v2.csv",
        "neighborhood_summary_csv": output_dir / "sevilla_hidden_gems_neighborhood_summary_v2.csv",
        "dish_summary_csv": output_dir / "sevilla_hidden_gems_dish_summary_v2.csv",
        "summary_json": output_dir / "sevilla_hidden_gems_ranking_v2_summary.json",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }

    print(f"Patch: {PATCH_ID}")
    print("Loading place-dish signals...")
    signals = read_table(args.input_path)
    print(f"Input rows: {len(signals)}")

    missing = ensure_columns(signals, REQUIRED_COLUMNS, strict=args.strict)
    if missing:
        print(f"WARNING: Missing columns: {missing}")

    if len(signals) == 0:
        raise ValueError("Input signals are empty.")

    print("Building ranking score...")
    ranking_df = build_ranking(signals, args)

    # Apply final selected score threshold.
    # A row can be eligible but still not selected if below exploratory threshold.
    ranking_df["selected_hidden_gem_v2"] = (
        coerce_bool_series(ranking_df["selected_hidden_gem_v2"])
        & (ranking_df["hidden_gem_score_v2"] >= args.min_selected_score)
    )
    ranking_df.loc[~coerce_bool_series(ranking_df["selected_hidden_gem_v2"]), "hidden_gem_tier_v2"] = "not_selected"

    # Re-rank after final selection.
    ranking_df = add_ranks(ranking_df)
    ranking_df["ranking_explanation_v2"] = ranking_df.apply(build_explanation, axis=1)

    selected_df = ranking_df[coerce_bool_series(ranking_df["selected_hidden_gem_v2"])].copy()

    out_cols = choose_output_columns(ranking_df)
    ranking_out = ranking_df[out_cols].copy()
    selected_out = selected_df[out_cols].copy()

    print("Building summaries...")
    top_global_df = selected_out.head(args.top_global_limit).copy()

    top_by_district_df = top_by_group(ranking_df, ["district_name"], "top_by_district_rank_v2", args.top_per_group)
    top_by_neighborhood_df = top_by_group(ranking_df, ["district_name", "neighborhood_name"], "top_by_neighborhood_rank_v2", args.top_per_group)
    top_by_dish_df = top_by_group(ranking_df, ["dish_display_name_v2"], "top_by_dish_rank_v2", args.top_per_group)

    top_by_district_df = top_by_district_df[choose_output_columns(top_by_district_df) + ["top_by_district_rank_v2"] if "top_by_district_rank_v2" in top_by_district_df.columns else choose_output_columns(top_by_district_df)]
    top_by_neighborhood_df = top_by_neighborhood_df[choose_output_columns(top_by_neighborhood_df) + ["top_by_neighborhood_rank_v2"] if "top_by_neighborhood_rank_v2" in top_by_neighborhood_df.columns else choose_output_columns(top_by_neighborhood_df)]
    top_by_dish_df = top_by_dish_df[choose_output_columns(top_by_dish_df) + ["top_by_dish_rank_v2"] if "top_by_dish_rank_v2" in top_by_dish_df.columns else choose_output_columns(top_by_dish_df)]

    manual_review_df = build_manual_review_df(ranking_df, args)
    manual_review_out = manual_review_df[["manual_review_priority_v2"] + choose_output_columns(manual_review_df)].copy()

    tier_summary_df = build_tier_summary(ranking_df)
    district_summary_df = summarize_group(ranking_df, ["district_name"], args.summary_group_limit)
    neighborhood_summary_df = summarize_group(ranking_df, ["district_name", "neighborhood_name"], args.summary_group_limit)
    dish_summary_df = summarize_group(ranking_df, ["dish_display_name_v2"], args.summary_group_limit)

    print("Writing outputs...")
    write_csv(paths["ranking_csv"], ranking_out)
    write_jsonl(paths["ranking_jsonl"], ranking_out.to_dict(orient="records"))

    write_csv(paths["selected_csv"], selected_out)
    write_jsonl(paths["selected_jsonl"], selected_out.to_dict(orient="records"))

    write_csv(paths["top_global_csv"], top_global_df)
    write_csv(paths["top_by_district_csv"], top_by_district_df)
    write_csv(paths["top_by_neighborhood_csv"], top_by_neighborhood_df)
    write_csv(paths["top_by_dish_csv"], top_by_dish_df)
    write_csv(paths["manual_review_csv"], manual_review_out)

    write_csv(paths["tier_summary_csv"], tier_summary_df)
    write_csv(paths["district_summary_csv"], district_summary_df)
    write_csv(paths["neighborhood_summary_csv"], neighborhood_summary_df)
    write_csv(paths["dish_summary_csv"], dish_summary_df)

    selected_score_summary = describe_numeric(selected_df["hidden_gem_score_v2"]) if len(selected_df) else {}

    checks = {
        "input_exists": args.input_path.exists(),
        "has_input_rows": bool(len(signals) > 0),
        "has_ranking_rows": bool(len(ranking_df) > 0),
        "has_selected_candidates": bool(len(selected_df) > 0),
        "score_in_0_100": bool(ranking_df["hidden_gem_score_v2"].between(0, 100).all()),
        "selected_have_place": bool(selected_df["place_id"].notna().all()) if len(selected_df) else True,
        "selected_have_dish": bool(selected_df["dish_id_v2"].notna().all()) if len(selected_df) else True,
        "selected_have_neighborhood": bool(selected_df["neighborhood_id"].notna().all()) if len(selected_df) else True,
        "selected_have_district": bool(selected_df["district_id"].notna().all()) if len(selected_df) else True,
        "selected_ranks_are_unique": bool(
            selected_df["hidden_gem_selected_rank_v2"].nunique(dropna=True) == len(selected_df)
        ) if len(selected_df) else True,
        "all_selected_are_not_production_ready": bool((selected_df["is_production_ready_v2"] == False).all()) if len(selected_df) else True,
        "ranking_csv_exists": paths["ranking_csv"].exists(),
        "ranking_jsonl_exists": paths["ranking_jsonl"].exists(),
        "selected_csv_exists": paths["selected_csv"].exists(),
        "manual_review_csv_exists": paths["manual_review_csv"].exists(),
    }

    errors: List[str] = []
    warnings: List[str] = []

    if not checks["has_selected_candidates"]:
        warnings.append("No selected Hidden Gem candidates were produced.")
    if len(manual_review_out) > 0:
        warnings.append("Some ranking rows should be manually reviewed before downstream loading.")
    if selected_df["evidence_tier_v2"].isin(["weak", "emerging"]).mean() > 0.7 if len(selected_df) else False:
        warnings.append("Most selected candidates have weak/emerging evidence; keep IA v2 as experimental.")
    if not checks["score_in_0_100"]:
        errors.append("Some scores are outside 0-100.")

    summary = {
        "script": SCRIPT_NAME,
        "patch_id": PATCH_ID,
        "version": VERSION,
        "ranking_scope": args.ranking_scope,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "input_path": str(args.input_path),
            "min_score": args.min_score,
            "min_selected_score": args.min_selected_score,
            "min_mentions": args.min_mentions,
            "min_reviews": args.min_reviews,
            "min_weighted_mentions": args.min_weighted_mentions,
            "max_negative_ratio": args.max_negative_ratio,
            "max_needs_review_ratio": args.max_needs_review_ratio,
            "top_threshold": args.top_threshold,
            "strong_threshold": args.strong_threshold,
            "promising_threshold": args.promising_threshold,
            "exploratory_threshold": args.exploratory_threshold,
        },
        "counts": {
            "input_signals": int(len(signals)),
            "total_signals_scored": int(len(ranking_df)),
            "selected_hidden_gem_candidates": int(len(selected_df)),
            "selected_places": int(selected_df["place_id"].nunique()) if len(selected_df) else 0,
            "selected_dishes": int(selected_df["dish_id_v2"].nunique()) if len(selected_df) else 0,
            "selected_neighborhoods": int(selected_df["neighborhood_id"].nunique()) if len(selected_df) else 0,
            "selected_districts": int(selected_df["district_id"].nunique()) if len(selected_df) else 0,
            "top_hidden_gem_count": int((selected_df["hidden_gem_tier_v2"] == "top_hidden_gem").sum()) if len(selected_df) else 0,
            "strong_hidden_gem_count": int((selected_df["hidden_gem_tier_v2"] == "strong_hidden_gem").sum()) if len(selected_df) else 0,
            "promising_hidden_gem_count": int((selected_df["hidden_gem_tier_v2"] == "promising_hidden_gem").sum()) if len(selected_df) else 0,
            "exploratory_hidden_gem_count": int((selected_df["hidden_gem_tier_v2"] == "exploratory_hidden_gem").sum()) if len(selected_df) else 0,
            "manual_review_rows": int(len(manual_review_out)),
            "production_ready_count": int((ranking_df["is_production_ready_v2"] == True).sum()),
        },
        "tier_counts": value_counts_dict(ranking_df["hidden_gem_tier_v2"]),
        "selected_tier_counts": value_counts_dict(selected_df["hidden_gem_tier_v2"]) if len(selected_df) else {},
        "evidence_tier_counts_selected": value_counts_dict(selected_df["evidence_tier_v2"]) if len(selected_df) else {},
        "aggregate_quality_tier_counts_selected": value_counts_dict(selected_df["aggregate_quality_tier_v2"]) if len(selected_df) else {},
        "score_summary_all": describe_numeric(ranking_df["hidden_gem_score_v2"]),
        "score_summary_selected": selected_score_summary,
        "weighted_sentiment_summary_selected": describe_numeric(selected_df["weighted_sentiment_score_v2"]) if len(selected_df) else {},
        "component_weights": {
            "ranking_sentiment_component": 0.34,
            "ranking_evidence_component": 0.22,
            "ranking_quality_component": 0.20,
            "ranking_consensus_component": 0.10,
            "ranking_uniqueness_component": 0.09,
            "ranking_rating_component": 0.05,
            "negative_sentiment_penalty": "up to ~0.22",
            "quality_risk_penalty": "up to ~0.28",
            "low_evidence_penalty": "up to 0.14",
        },
        "top_30": selected_out.head(30).to_dict(orient="records") if len(selected_out) else [],
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "files": {k: str(v) for k, v in paths.items()},
        "notes": [
            "This is the IA v2 Hidden Gems ranking based on trained model outputs.",
            "is_production_ready_v2 is intentionally false for all rows.",
            "Ranking v2 should be compared against ranking v1 before loading into PostgreSQL.",
            "Do not commit artifacts containing review/context text to Git.",
        ],
    }

    write_json(paths["summary_json"], summary)
    paths["recommendations_md"].write_text(build_recommendations(summary), encoding="utf-8")

    print(json.dumps(to_builtin(summary["counts"]), indent=2, ensure_ascii=False))
    print(json.dumps(to_builtin(summary["checks"]), indent=2, ensure_ascii=False))

    if errors:
        print("Errors:")
        for error in errors:
            print(f"- {error}")
        if args.strict:
            return 1

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    print(f"Summary saved to: {paths['summary_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
