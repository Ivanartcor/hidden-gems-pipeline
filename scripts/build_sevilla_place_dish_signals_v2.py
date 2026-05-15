#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build Sevilla place-dish signal aggregation v2 from ABSA sentiment outputs.

Input:
    data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/
    └── sevilla_dish_mentions_with_absa_sentiment_v1.jsonl

Output:
    data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/
    ├── sevilla_place_dish_signals_v2.csv
    ├── sevilla_place_dish_signals_v2.jsonl
    ├── sevilla_top_place_dish_signals_v2.csv
    ├── sevilla_place_dish_signals_by_district_v2.csv
    ├── sevilla_place_dish_signals_by_neighborhood_v2.csv
    ├── sevilla_place_dish_signals_by_dish_v2.csv
    ├── sevilla_place_dish_signals_manual_review_v2.csv
    ├── sevilla_place_dish_signal_tier_summary_v2.csv
    ├── sevilla_place_dish_signal_summary_v2.json
    └── recommended_next_steps.md

This is an intermediate IA v2 layer:
Hybrid + NER mentions -> normalization reranker -> ABSA sentiment -> place-dish signals.
It does NOT load data into PostgreSQL.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


PATCH_ID = "place_dish_signals_v2_absa_aggregation_2026_05_14"
SCRIPT_NAME = "build_sevilla_place_dish_signals_v2"
VERSION = "sevilla_place_dish_signals_v2"

VALID_SENTIMENT_LABELS = {"positive", "neutral", "negative"}


# ---------------------------------------------------------------------------
# IO / serialization
# ---------------------------------------------------------------------------

def is_nullish(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null", "na", "<na>"}:
        return True
    return False


def to_builtin(value: Any) -> Any:
    """Convert pandas/numpy/date/decimal and odd DB values into JSON-safe values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

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

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if not np.isfinite(value):
            return None
        return float(value)

    if isinstance(value, (np.ndarray,)):
        return value.tolist()

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
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


def read_input(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input path not found: {path}")

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".csv":
        return pd.read_csv(path)

    raise ValueError(f"Unsupported input extension: {suffix}. Use .jsonl or .csv")


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(to_builtin(row), ensure_ascii=False, allow_nan=False, default=str) + "\n")


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(obj), f, indent=2, ensure_ascii=False, allow_nan=False, default=str)


# ---------------------------------------------------------------------------
# Coercion helpers
# ---------------------------------------------------------------------------

def first_existing(df: pd.DataFrame, names: List[str], required: bool = False) -> Optional[str]:
    for name in names:
        if name in df.columns:
            return name
    if required:
        raise KeyError(f"Missing required column. Tried: {names}")
    return None


def coerce_numeric(series: pd.Series, default: float = 0.0) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).fillna(default)


def coerce_bool(series: pd.Series, default: bool = False) -> pd.Series:
    def parse(v: Any) -> bool:
        if is_nullish(v):
            return default
        if isinstance(v, bool):
            return v
        if isinstance(v, (int, np.integer)):
            return bool(v)
        text = str(v).strip().lower()
        if text in {"true", "1", "yes", "y", "si", "sí"}:
            return True
        if text in {"false", "0", "no", "n"}:
            return False
        return default

    return series.map(parse)


def clean_text(value: Any) -> str:
    if is_nullish(value):
        return ""
    return str(value).strip()


def normalize_label(value: Any) -> Optional[str]:
    if is_nullish(value):
        return None
    text = str(value).strip().lower()
    mapping = {
        "pos": "positive",
        "positivo": "positive",
        "positiva": "positive",
        "positive": "positive",
        "neu": "neutral",
        "neutro": "neutral",
        "neutra": "neutral",
        "neutral": "neutral",
        "neg": "negative",
        "negativo": "negative",
        "negativa": "negative",
        "negative": "negative",
    }
    return mapping.get(text)


def clipped(value: Any, low: float = 0.0, high: float = 1.0, default: float = 0.0) -> float:
    try:
        if is_nullish(value):
            return default
        x = float(value)
        if not math.isfinite(x):
            return default
        return max(low, min(high, x))
    except Exception:
        return default


def safe_ratio(num: float, den: float) -> float:
    if den == 0:
        return 0.0
    return float(num) / float(den)


def weighted_average(values: pd.Series, weights: pd.Series, default: float = 0.0) -> float:
    v = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    w = pd.to_numeric(weights, errors="coerce").replace([np.inf, -np.inf], np.nan)

    mask = v.notna() & w.notna() & (w > 0)
    if not mask.any():
        return default
    return float(np.average(v[mask], weights=w[mask]))


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def prepare_mentions(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    required = [
        "review_id",
        "place_id",
        "selected_mention_text_v2",
        "normalized_dish_id_v1",
        "normalized_dish_display_name_v1",
        "absa_sentiment_label_v1",
        "absa_sentiment_score_v1",
        "absa_sentiment_confidence_v1",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Missing required columns in ABSA input: {missing}")

    out = df.copy()

    # Standard identifiers and text columns.
    for col in [
        "review_id",
        "place_id",
        "place_name",
        "district_id",
        "district_name",
        "neighborhood_id",
        "neighborhood_name",
        "source_strategy_v2",
        "selected_mention_text_v2",
        "selected_mention_norm_v2",
        "normalized_dish_id_v1",
        "normalized_dish_name_v1",
        "normalized_dish_display_name_v1",
        "normalization_status_v1",
        "absa_sentiment_status_v1",
        "absa_review_reason_v1",
        "normalization_review_reason_v1",
        "review_language",
    ]:
        if col not in out.columns:
            out[col] = ""
        out[col] = out[col].map(clean_text)

    # Numeric columns.
    numeric_defaults = {
        "rating_value": np.nan,
        "combined_confidence_v2": 0.75,
        "hybrid_confidence": np.nan,
        "ner_confidence": np.nan,
        "normalization_confidence_v1": 0.0,
        "normalization_score_margin_v1": 0.0,
        "absa_prob_negative_v1": 0.0,
        "absa_prob_neutral_v1": 0.0,
        "absa_prob_positive_v1": 0.0,
        "absa_sentiment_score_v1": 0.0,
        "absa_sentiment_confidence_v1": 0.0,
        "absa_sentiment_margin_v1": 0.0,
    }

    for col, default in numeric_defaults.items():
        if col not in out.columns:
            out[col] = default
        out[col] = coerce_numeric(out[col], default=default if not pd.isna(default) else np.nan)

    # Boolean columns.
    bool_defaults = {
        "is_compound_mention_v2": False,
        "is_generic_exact_v2": False,
        "is_low_value_single_v2": False,
        "is_likely_fragment_v2": False,
        "is_experimental_ner_only_v2": False,
        "normalization_needs_manual_review_v1": False,
        "ready_for_sentiment_after_normalization_v1": True,
        "ready_for_absa_input_v1": True,
        "absa_needs_manual_review_v1": False,
    }

    for col, default in bool_defaults.items():
        if col not in out.columns:
            out[col] = default
        out[col] = coerce_bool(out[col], default=default)

    # Labels.
    out["absa_sentiment_label_v1"] = out["absa_sentiment_label_v1"].map(normalize_label)

    valid = out["absa_sentiment_label_v1"].isin(VALID_SENTIMENT_LABELS)
    ready = out["ready_for_absa_input_v1"] & out["ready_for_sentiment_after_normalization_v1"]

    if not args.include_not_ready:
        out = out[valid & ready].copy()
    else:
        out = out[valid].copy()

    # Drop rows without essential identifiers.
    out = out[
        out["review_id"].astype(str).str.len().gt(0)
        & out["place_id"].astype(str).str.len().gt(0)
        & out["normalized_dish_id_v1"].astype(str).str.len().gt(0)
    ].copy()

    # Mention-level weights.
    source_weight_map = {
        "hybrid_and_ner": 1.00,
        "hybrid_only": 0.90,
        "ner_only": 0.75,
    }
    out["source_weight_v2"] = out["source_strategy_v2"].map(source_weight_map).fillna(0.75).astype(float)

    # Confidence components.
    out["combined_conf_component_v2"] = out["combined_confidence_v2"].map(lambda x: clipped(x, 0.20, 1.00, 0.75))
    out["normalization_conf_component_v2"] = out["normalization_confidence_v1"].map(lambda x: clipped(x, 0.10, 1.00, 0.50))
    out["absa_conf_component_v2"] = out["absa_sentiment_confidence_v1"].map(lambda x: clipped(x, 0.10, 1.00, 0.50))

    # Penalties for review flags.
    out["review_flag_weight_v2"] = 1.0
    out.loc[out["normalization_needs_manual_review_v1"], "review_flag_weight_v2"] *= 0.65
    out.loc[out["absa_needs_manual_review_v1"], "review_flag_weight_v2"] *= 0.70
    out.loc[out["is_likely_fragment_v2"], "review_flag_weight_v2"] *= 0.50
    out.loc[out["is_low_value_single_v2"], "review_flag_weight_v2"] *= 0.70
    out.loc[out["is_experimental_ner_only_v2"], "review_flag_weight_v2"] *= 0.80

    # ABSA margin penalty.
    out["margin_weight_v2"] = np.where(out["absa_sentiment_margin_v1"] >= args.min_sentiment_margin, 1.0, 0.75)

    out["mention_weight_v2"] = (
        out["source_weight_v2"]
        * out["combined_conf_component_v2"]
        * out["normalization_conf_component_v2"]
        * out["absa_conf_component_v2"]
        * out["review_flag_weight_v2"]
        * out["margin_weight_v2"]
    )

    out["mention_weight_v2"] = out["mention_weight_v2"].clip(lower=args.min_mention_weight, upper=1.0)

    out["is_positive_v2"] = out["absa_sentiment_label_v1"] == "positive"
    out["is_neutral_v2"] = out["absa_sentiment_label_v1"] == "neutral"
    out["is_negative_v2"] = out["absa_sentiment_label_v1"] == "negative"

    out["weighted_positive_v2"] = out["mention_weight_v2"] * out["is_positive_v2"].astype(float)
    out["weighted_neutral_v2"] = out["mention_weight_v2"] * out["is_neutral_v2"].astype(float)
    out["weighted_negative_v2"] = out["mention_weight_v2"] * out["is_negative_v2"].astype(float)

    out["weighted_sentiment_value_v2"] = out["mention_weight_v2"] * out["absa_sentiment_score_v1"]

    # Useful display fields.
    out["dish_id_v2"] = out["normalized_dish_id_v1"]
    out["dish_display_name_v2"] = out["normalized_dish_display_name_v1"].where(
        out["normalized_dish_display_name_v1"].astype(str).str.len().gt(0),
        out["normalized_dish_name_v1"],
    )
    out["dish_name_norm_v2"] = out["normalized_dish_name_v1"]

    out["mention_ready_for_signal_v2"] = True

    return out.reset_index(drop=True)


def evidence_tier(mention_count: int, review_count: int, weighted_mention_count: float) -> str:
    if review_count >= 5 and mention_count >= 6 and weighted_mention_count >= 4.0:
        return "strong"
    if review_count >= 3 and mention_count >= 3 and weighted_mention_count >= 2.0:
        return "solid"
    if review_count >= 2 and mention_count >= 2:
        return "emerging"
    return "weak"


def quality_tier(row: pd.Series) -> str:
    evidence = row.get("evidence_tier_v2", "weak")
    positive_ratio = float(row.get("positive_ratio_v2", 0.0))
    weighted_sentiment = float(row.get("weighted_sentiment_score_v2", 0.0))
    neg_ratio = float(row.get("negative_ratio_v2", 0.0))
    conf = float(row.get("avg_absa_confidence_v2", 0.0))
    review_flags_ratio = float(row.get("needs_review_ratio_v2", 0.0))

    if (
        evidence in {"strong", "solid"}
        and positive_ratio >= 0.70
        and weighted_sentiment >= 0.45
        and neg_ratio <= 0.20
        and conf >= 0.80
        and review_flags_ratio <= 0.35
    ):
        return "high"

    if (
        evidence in {"solid", "emerging"}
        and positive_ratio >= 0.55
        and weighted_sentiment >= 0.20
        and neg_ratio <= 0.35
        and conf >= 0.70
    ):
        return "medium"

    if evidence != "weak" and weighted_sentiment >= 0.0 and neg_ratio <= 0.50:
        return "low"

    return "weak"


def ranking_eligibility(row: pd.Series, args: argparse.Namespace) -> Dict[str, Any]:
    reasons: List[str] = []

    if int(row.get("mention_count_v2", 0)) < args.min_mentions_for_ranking:
        reasons.append("too_few_mentions")

    if int(row.get("review_count_v2", 0)) < args.min_reviews_for_ranking:
        reasons.append("too_few_reviews")

    if float(row.get("weighted_mention_count_v2", 0.0)) < args.min_weighted_mentions_for_ranking:
        reasons.append("too_low_weighted_evidence")

    if float(row.get("negative_ratio_v2", 0.0)) > args.max_negative_ratio_for_ranking:
        reasons.append("negative_ratio_too_high")

    if float(row.get("weighted_sentiment_score_v2", 0.0)) < args.min_weighted_sentiment_for_ranking:
        reasons.append("sentiment_too_low")

    if float(row.get("needs_review_ratio_v2", 0.0)) > args.max_needs_review_ratio_for_ranking:
        reasons.append("too_many_review_flags")

    if str(row.get("aggregate_quality_tier_v2", "")) == "weak":
        reasons.append("weak_aggregate_quality")

    return {
        "ready_for_ranking_v2": len(reasons) == 0,
        "ranking_eligibility_status_v2": "eligible" if len(reasons) == 0 else "not_eligible",
        "ranking_eligibility_reasons_v2": ";".join(reasons) if reasons else "none",
    }


def aggregate_place_dish(mentions: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    group_cols = [
        "place_id",
        "place_name",
        "district_id",
        "district_name",
        "neighborhood_id",
        "neighborhood_name",
        "dish_id_v2",
        "dish_display_name_v2",
        "dish_name_norm_v2",
    ]

    # Ensure columns exist.
    for col in group_cols:
        if col not in mentions.columns:
            mentions[col] = ""

    rows: List[Dict[str, Any]] = []

    grouped = mentions.groupby(group_cols, dropna=False, sort=False)

    for group_key, group in grouped:
        if not isinstance(group_key, tuple):
            group_key = (group_key,)

        base = dict(zip(group_cols, group_key))

        mention_count = int(len(group))
        review_count = int(group["review_id"].nunique())
        weighted_mention_count = float(group["mention_weight_v2"].sum())

        positive_count = int(group["is_positive_v2"].sum())
        neutral_count = int(group["is_neutral_v2"].sum())
        negative_count = int(group["is_negative_v2"].sum())

        weighted_positive = float(group["weighted_positive_v2"].sum())
        weighted_neutral = float(group["weighted_neutral_v2"].sum())
        weighted_negative = float(group["weighted_negative_v2"].sum())

        weight_sum = max(weighted_mention_count, 1e-9)

        source_strategy_mix = group["source_strategy_v2"].value_counts(dropna=False).to_dict()
        sentiment_counts = group["absa_sentiment_label_v1"].value_counts(dropna=False).to_dict()

        row: Dict[str, Any] = {
            **base,
            "signal_id_v2": f"signal_v2::{base.get('place_id')}::{base.get('dish_id_v2')}",
            "mention_count_v2": mention_count,
            "review_count_v2": review_count,
            "weighted_mention_count_v2": round(weighted_mention_count, 6),
            "positive_count_v2": positive_count,
            "neutral_count_v2": neutral_count,
            "negative_count_v2": negative_count,
            "weighted_positive_count_v2": round(weighted_positive, 6),
            "weighted_neutral_count_v2": round(weighted_neutral, 6),
            "weighted_negative_count_v2": round(weighted_negative, 6),
            "positive_ratio_v2": round(safe_ratio(positive_count, mention_count), 6),
            "neutral_ratio_v2": round(safe_ratio(neutral_count, mention_count), 6),
            "negative_ratio_v2": round(safe_ratio(negative_count, mention_count), 6),
            "weighted_positive_ratio_v2": round(weighted_positive / weight_sum, 6),
            "weighted_neutral_ratio_v2": round(weighted_neutral / weight_sum, 6),
            "weighted_negative_ratio_v2": round(weighted_negative / weight_sum, 6),
            "avg_absa_confidence_v2": round(float(group["absa_sentiment_confidence_v1"].mean()), 6),
            "avg_absa_margin_v2": round(float(group["absa_sentiment_margin_v1"].mean()), 6),
            "avg_normalization_confidence_v2": round(float(group["normalization_confidence_v1"].mean()), 6),
            "avg_combined_mention_confidence_v2": round(float(group["combined_confidence_v2"].mean()), 6),
            "avg_mention_weight_v2": round(float(group["mention_weight_v2"].mean()), 6),
            "min_mention_weight_v2": round(float(group["mention_weight_v2"].min()), 6),
            "avg_rating_v2": round(float(pd.to_numeric(group["rating_value"], errors="coerce").mean()), 6) if group["rating_value"].notna().any() else None,
            "weighted_sentiment_score_v2": round(weighted_average(group["absa_sentiment_score_v1"], group["mention_weight_v2"], 0.0), 6),
            "raw_avg_sentiment_score_v2": round(float(group["absa_sentiment_score_v1"].mean()), 6),
            "source_strategy_mix_json": json.dumps(to_builtin(source_strategy_mix), ensure_ascii=False),
            "sentiment_counts_json": json.dumps(to_builtin(sentiment_counts), ensure_ascii=False),
            "hybrid_and_ner_count_v2": int((group["source_strategy_v2"] == "hybrid_and_ner").sum()),
            "hybrid_only_count_v2": int((group["source_strategy_v2"] == "hybrid_only").sum()),
            "ner_only_count_v2": int((group["source_strategy_v2"] == "ner_only").sum()),
            "ner_only_ratio_v2": round(float((group["source_strategy_v2"] == "ner_only").mean()), 6),
            "compound_mention_ratio_v2": round(float(group["is_compound_mention_v2"].mean()), 6),
            "generic_exact_ratio_v2": round(float(group["is_generic_exact_v2"].mean()), 6),
            "likely_fragment_ratio_v2": round(float(group["is_likely_fragment_v2"].mean()), 6),
            "needs_review_count_v2": int(
                (
                    group["normalization_needs_manual_review_v1"]
                    | group["absa_needs_manual_review_v1"]
                    | group["is_likely_fragment_v2"]
                ).sum()
            ),
            "needs_review_ratio_v2": round(float(
                (
                    group["normalization_needs_manual_review_v1"]
                    | group["absa_needs_manual_review_v1"]
                    | group["is_likely_fragment_v2"]
                ).mean()
            ), 6),
            "example_mentions_v2": " | ".join(group["selected_mention_text_v2"].dropna().astype(str).head(args.max_examples_per_signal).tolist()),
            "example_review_ids_v2": " | ".join(group["review_id"].dropna().astype(str).head(args.max_examples_per_signal).tolist()),
        }

        row["evidence_tier_v2"] = evidence_tier(
            mention_count=mention_count,
            review_count=review_count,
            weighted_mention_count=weighted_mention_count,
        )
        row["aggregate_quality_tier_v2"] = quality_tier(pd.Series(row))
        row.update(ranking_eligibility(pd.Series(row), args))

        rows.append(row)

    signals = pd.DataFrame(rows)

    if len(signals) == 0:
        return signals

    # Sort for usability.
    signals = signals.sort_values(
        [
            "ready_for_ranking_v2",
            "weighted_sentiment_score_v2",
            "weighted_mention_count_v2",
            "review_count_v2",
            "mention_count_v2",
        ],
        ascending=[False, False, False, False, False],
    ).reset_index(drop=True)

    signals.insert(0, "signal_rank_preview_v2", np.arange(1, len(signals) + 1))

    return signals


def summarize_group(signals: pd.DataFrame, group_cols: List[str], entity_name: str) -> pd.DataFrame:
    if len(signals) == 0:
        return pd.DataFrame()

    for col in group_cols:
        if col not in signals.columns:
            signals[col] = ""

    rows = []
    for key, group in signals.groupby(group_cols, dropna=False, sort=False):
        if not isinstance(key, tuple):
            key = (key,)
        base = dict(zip(group_cols, key))

        eligible = group[group["ready_for_ranking_v2"] == True]
        rows.append({
            **base,
            f"{entity_name}_signal_count_v2": int(len(group)),
            f"{entity_name}_eligible_signal_count_v2": int(len(eligible)),
            f"{entity_name}_place_count_v2": int(group["place_id"].nunique()) if "place_id" in group.columns else None,
            f"{entity_name}_dish_count_v2": int(group["dish_id_v2"].nunique()) if "dish_id_v2" in group.columns else None,
            f"{entity_name}_mention_count_v2": int(group["mention_count_v2"].sum()),
            f"{entity_name}_review_count_sum_v2": int(group["review_count_v2"].sum()),
            f"{entity_name}_avg_weighted_sentiment_v2": round(float(group["weighted_sentiment_score_v2"].mean()), 6),
            f"{entity_name}_max_weighted_sentiment_v2": round(float(group["weighted_sentiment_score_v2"].max()), 6),
            f"{entity_name}_avg_positive_ratio_v2": round(float(group["positive_ratio_v2"].mean()), 6),
            f"{entity_name}_avg_negative_ratio_v2": round(float(group["negative_ratio_v2"].mean()), 6),
            f"{entity_name}_ready_ratio_v2": round(float(group["ready_for_ranking_v2"].mean()), 6),
        })

    out = pd.DataFrame(rows)
    sort_cols = [f"{entity_name}_eligible_signal_count_v2", f"{entity_name}_max_weighted_sentiment_v2", f"{entity_name}_mention_count_v2"]
    out = out.sort_values(sort_cols, ascending=[False, False, False]).reset_index(drop=True)
    return out


def build_manual_review(signals: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    if len(signals) == 0:
        return pd.DataFrame()

    mask = (
        (~signals["ready_for_ranking_v2"].astype(bool))
        | (signals["needs_review_ratio_v2"] >= args.manual_review_ratio_threshold)
        | (signals["ner_only_ratio_v2"] >= args.manual_review_ner_only_ratio_threshold)
        | (signals["negative_ratio_v2"] >= args.manual_review_negative_ratio_threshold)
    )

    review = signals[mask].copy()

    if len(review) == 0:
        return review

    def priority(row: pd.Series) -> str:
        if row["review_count_v2"] >= 3 and row["weighted_mention_count_v2"] >= 2.0:
            return "high"
        if row["mention_count_v2"] >= 2:
            return "medium"
        return "low"

    review["manual_review_priority_v2"] = review.apply(priority, axis=1)
    review["manual_decision"] = ""
    review["manual_should_keep_for_ranking_v2"] = ""
    review["manual_corrected_dish_id"] = ""
    review["manual_corrected_dish_name"] = ""
    review["manual_notes"] = ""

    review = review.sort_values(
        ["manual_review_priority_v2", "weighted_mention_count_v2", "review_count_v2"],
        ascending=[True, False, False],
    ).reset_index(drop=True)

    return review


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Sevilla place-dish signals v2 from normalized ABSA mention-level sentiment."
    )

    parser.add_argument(
        "--input-path",
        default="data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl",
        help="Input ABSA sentiment JSONL/CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2",
        help="Output directory.",
    )
    parser.add_argument("--include-not-ready", action="store_true", help="Include not-ready rows if they have labels.")
    parser.add_argument("--min-mentions-for-ranking", type=int, default=2)
    parser.add_argument("--min-reviews-for-ranking", type=int, default=2)
    parser.add_argument("--min-weighted-mentions-for-ranking", type=float, default=1.20)
    parser.add_argument("--min-weighted-sentiment-for-ranking", type=float, default=0.10)
    parser.add_argument("--max-negative-ratio-for-ranking", type=float, default=0.50)
    parser.add_argument("--max-needs-review-ratio-for-ranking", type=float, default=0.60)
    parser.add_argument("--min-sentiment-margin", type=float, default=0.12)
    parser.add_argument("--min-mention-weight", type=float, default=0.05)
    parser.add_argument("--max-examples-per-signal", type=int, default=3)
    parser.add_argument("--manual-review-ratio-threshold", type=float, default=0.50)
    parser.add_argument("--manual-review-ner-only-ratio-threshold", type=float, default=0.50)
    parser.add_argument("--manual-review-negative-ratio-threshold", type=float, default=0.50)
    parser.add_argument("--top-limit", type=int, default=300)
    parser.add_argument("--strict", action="store_true", help="Fail if critical checks do not pass.")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "signals_csv": output_dir / "sevilla_place_dish_signals_v2.csv",
        "signals_jsonl": output_dir / "sevilla_place_dish_signals_v2.jsonl",
        "top_signals_csv": output_dir / "sevilla_top_place_dish_signals_v2.csv",
        "district_csv": output_dir / "sevilla_place_dish_signals_by_district_v2.csv",
        "neighborhood_csv": output_dir / "sevilla_place_dish_signals_by_neighborhood_v2.csv",
        "dish_csv": output_dir / "sevilla_place_dish_signals_by_dish_v2.csv",
        "manual_review_csv": output_dir / "sevilla_place_dish_signals_manual_review_v2.csv",
        "tier_summary_csv": output_dir / "sevilla_place_dish_signal_tier_summary_v2.csv",
        "summary_json": output_dir / "sevilla_place_dish_signal_summary_v2.json",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }

    print(f"Patch: {PATCH_ID}")
    print("Loading ABSA mention-level sentiment...")
    raw_df = read_input(input_path)
    print(f"Input rows: {len(raw_df)}")

    print("Preparing mentions...")
    mentions = prepare_mentions(raw_df, args)
    print(f"Usable mention rows for signal aggregation: {len(mentions)}")

    print("Aggregating place-dish signals...")
    signals = aggregate_place_dish(mentions, args)
    print(f"Place-dish signals: {len(signals)}")

    top_signals = signals[signals["ready_for_ranking_v2"] == True].head(args.top_limit).copy()

    district_summary = summarize_group(signals, ["district_id", "district_name"], "district")
    neighborhood_summary = summarize_group(
        signals,
        ["district_id", "district_name", "neighborhood_id", "neighborhood_name"],
        "neighborhood",
    )
    dish_summary = summarize_group(signals, ["dish_id_v2", "dish_display_name_v2", "dish_name_norm_v2"], "dish")

    manual_review = build_manual_review(signals, args)

    if len(signals):
        tier_summary = (
            signals.groupby(["evidence_tier_v2", "aggregate_quality_tier_v2", "ready_for_ranking_v2"], dropna=False)
            .agg(
                signal_count=("signal_id_v2", "count"),
                mention_count=("mention_count_v2", "sum"),
                review_count_sum=("review_count_v2", "sum"),
                avg_sentiment=("weighted_sentiment_score_v2", "mean"),
                avg_positive_ratio=("positive_ratio_v2", "mean"),
                avg_negative_ratio=("negative_ratio_v2", "mean"),
            )
            .reset_index()
            .sort_values(["ready_for_ranking_v2", "signal_count"], ascending=[False, False])
        )
    else:
        tier_summary = pd.DataFrame()

    print("Writing outputs...")
    signals.to_csv(paths["signals_csv"], index=False, encoding="utf-8")
    write_jsonl(paths["signals_jsonl"], signals.to_dict(orient="records"))
    top_signals.to_csv(paths["top_signals_csv"], index=False, encoding="utf-8")
    district_summary.to_csv(paths["district_csv"], index=False, encoding="utf-8")
    neighborhood_summary.to_csv(paths["neighborhood_csv"], index=False, encoding="utf-8")
    dish_summary.to_csv(paths["dish_csv"], index=False, encoding="utf-8")
    manual_review.to_csv(paths["manual_review_csv"], index=False, encoding="utf-8")
    tier_summary.to_csv(paths["tier_summary_csv"], index=False, encoding="utf-8")

    ready_count = int(signals["ready_for_ranking_v2"].sum()) if len(signals) else 0
    not_ready_count = int(len(signals) - ready_count)

    status_counts = signals["ranking_eligibility_status_v2"].value_counts(dropna=False).to_dict() if len(signals) else {}
    evidence_counts = signals["evidence_tier_v2"].value_counts(dropna=False).to_dict() if len(signals) else {}
    quality_counts = signals["aggregate_quality_tier_v2"].value_counts(dropna=False).to_dict() if len(signals) else {}

    label_counts = mentions["absa_sentiment_label_v1"].value_counts(dropna=False).to_dict() if len(mentions) else {}
    source_counts = mentions["source_strategy_v2"].value_counts(dropna=False).to_dict() if len(mentions) else {}

    score_summary = (
        signals["weighted_sentiment_score_v2"].describe().round(6).to_dict()
        if len(signals)
        else {}
    )

    checks = {
        "input_exists": input_path.exists(),
        "has_input_rows": len(raw_df) > 0,
        "has_usable_mentions": len(mentions) > 0,
        "has_signals": len(signals) > 0,
        "all_signals_have_place": bool(signals["place_id"].astype(str).str.len().gt(0).all()) if len(signals) else False,
        "all_signals_have_dish": bool(signals["dish_id_v2"].astype(str).str.len().gt(0).all()) if len(signals) else False,
        "csv_exists": paths["signals_csv"].exists(),
        "jsonl_exists": paths["signals_jsonl"].exists(),
        "top_signals_exists": paths["top_signals_csv"].exists(),
        "manual_review_exists": paths["manual_review_csv"].exists(),
    }

    errors: List[str] = []
    warnings: List[str] = []

    if not checks["has_usable_mentions"]:
        errors.append("No usable ABSA mentions found.")
    if not checks["has_signals"]:
        errors.append("No place-dish signals were generated.")
    if len(manual_review):
        warnings.append("Some place-dish signals require manual review or are not ranking-ready.")
    if not_ready_count:
        warnings.append("Some place-dish signals are not eligible for ranking v2 under current thresholds.")
    if args.include_not_ready:
        warnings.append("include_not_ready was enabled; downstream outputs may include weaker rows.")

    summary = {
        "script": SCRIPT_NAME,
        "patch_id": PATCH_ID,
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "input_path": str(input_path),
            "include_not_ready": bool(args.include_not_ready),
            "min_mentions_for_ranking": args.min_mentions_for_ranking,
            "min_reviews_for_ranking": args.min_reviews_for_ranking,
            "min_weighted_mentions_for_ranking": args.min_weighted_mentions_for_ranking,
            "min_weighted_sentiment_for_ranking": args.min_weighted_sentiment_for_ranking,
            "max_negative_ratio_for_ranking": args.max_negative_ratio_for_ranking,
            "max_needs_review_ratio_for_ranking": args.max_needs_review_ratio_for_ranking,
        },
        "counts": {
            "input_rows": int(len(raw_df)),
            "usable_mention_rows": int(len(mentions)),
            "place_dish_signals": int(len(signals)),
            "ready_for_ranking_signals": ready_count,
            "not_ready_for_ranking_signals": not_ready_count,
            "top_signals_rows": int(len(top_signals)),
            "manual_review_rows": int(len(manual_review)),
            "unique_reviews": int(mentions["review_id"].nunique()) if len(mentions) else 0,
            "unique_places": int(mentions["place_id"].nunique()) if len(mentions) else 0,
            "unique_dishes": int(mentions["dish_id_v2"].nunique()) if len(mentions) else 0,
            "districts": int(mentions["district_id"].nunique()) if len(mentions) else 0,
            "neighborhoods": int(mentions["neighborhood_id"].nunique()) if len(mentions) else 0,
        },
        "mention_label_counts": label_counts,
        "mention_source_strategy_counts": source_counts,
        "signal_status_counts": status_counts,
        "evidence_tier_counts": evidence_counts,
        "aggregate_quality_tier_counts": quality_counts,
        "weighted_sentiment_score_summary": score_summary,
        "top_ready_signals_preview": top_signals[
            [
                "signal_rank_preview_v2",
                "place_name",
                "district_name",
                "neighborhood_name",
                "dish_display_name_v2",
                "mention_count_v2",
                "review_count_v2",
                "positive_ratio_v2",
                "negative_ratio_v2",
                "weighted_sentiment_score_v2",
                "evidence_tier_v2",
                "aggregate_quality_tier_v2",
            ]
        ].head(20).to_dict(orient="records") if len(top_signals) else [],
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "files": {k: str(v) for k, v in paths.items()},
        "notes": [
            "This is the IA v2 place-dish signal aggregation layer.",
            "It aggregates mention-level ABSA sentiment after NER + normalization reranker.",
            "Use ready_for_ranking_v2 rows for the next Hidden Gems ranking v2 script.",
            "Do not commit artifacts containing review text or full context to Git.",
        ],
    }

    write_json(paths["summary_json"], summary)

    recommendations = f"""# Sevilla Place-Dish Signals v2 - Recommended next steps

## Executive read

- Usable mention rows: **{len(mentions)}**
- Place-dish signals: **{len(signals)}**
- Ready for ranking v2: **{ready_count}**
- Not ready for ranking v2: **{not_ready_count}**
- Manual review rows: **{len(manual_review)}**

## Recommended next step

Create the ranking script:

```text
scripts/build_sevilla_hidden_gems_ranking_v2.py
```

It should consume:

```text
{paths["signals_jsonl"]}
```

and compare the new IA v2 ranking against the existing Sevilla pilot ranking v1.

## Suggested ranking policy

1. Use only `ready_for_ranking_v2 = true` for the main ranking.
2. Downweight signals with high `needs_review_ratio_v2`.
3. Reward:
   - strong/solid evidence,
   - high weighted sentiment,
   - several distinct reviews,
   - agreement between Hybrid and NER,
   - neighborhood diversity.
4. Penalize:
   - high negative ratio,
   - weak evidence,
   - excessive NER-only ratio,
   - likely fragments or low-confidence normalizations.

## Files to inspect first

- `sevilla_top_place_dish_signals_v2.csv`
- `sevilla_place_dish_signals_manual_review_v2.csv`
- `sevilla_place_dish_signal_tier_summary_v2.csv`
"""
    paths["recommendations_md"].write_text(recommendations, encoding="utf-8")

    print(json.dumps(to_builtin({
        "counts": summary["counts"],
        "signal_status_counts": signal_status_counts if False else status_counts,
        "evidence_tier_counts": evidence_counts,
        "aggregate_quality_tier_counts": quality_counts,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
    }), indent=2, ensure_ascii=False))

    print(f"Summary saved to: {paths['summary_json']}")

    if args.strict and errors:
        raise SystemExit(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
