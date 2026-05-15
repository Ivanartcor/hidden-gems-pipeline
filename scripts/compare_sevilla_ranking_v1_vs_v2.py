#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Compare Sevilla Hidden Gems ranking v1 vs v2.

This script compares the selected candidates from:
- Ranking v1: pilot / hybrid rule-based AI pipeline.
- Ranking v2: trained-model pipeline with NER + normalization reranker + ABSA sentiment.

It produces overlap, v1-only/v2-only candidates, score shifts, diversity shifts
by district/neighborhood/dish, and a summary JSON.

Recommended usage:

python -m scripts.compare_sevilla_ranking_v1_vs_v2 ^
  --v1-path data/artifacts/ai/sevilla/ranking_pilot/sevilla_hidden_gems_selected_v1.csv ^
  --v2-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.csv ^
  --output-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison ^
  --strict

If --v1-path is omitted, the script tries several common locations.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


SCRIPT_NAME = "compare_sevilla_ranking_v1_vs_v2"
PATCH_ID = "ranking_v1_vs_v2_comparison_2026_05_14"


# ---------------------------------------------------------------------
# IO utilities
# ---------------------------------------------------------------------

def to_builtin(value: Any) -> Any:
    """Convert pandas/numpy values into JSON-safe Python primitives."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]

    return value


def json_default(value: Any) -> str:
    return str(value)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(obj), f, indent=2, ensure_ascii=False, default=json_default)


def write_markdown(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def read_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict) and "rows" in data:
            return pd.DataFrame(data["rows"])
        raise ValueError(f"JSON no tabular: {path}")
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)

    raise ValueError(f"Formato no soportado: {path}")


def find_first_existing(paths: Iterable[Path]) -> Optional[Path]:
    for path in paths:
        if path.exists():
            return path
    return None


# ---------------------------------------------------------------------
# Text / key normalization
# ---------------------------------------------------------------------

def strip_accents(text: str) -> str:
    text = str(text or "")
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def normalize_text(text: Any) -> str:
    text = strip_accents(str(text or "").lower())
    text = re.sub(r"[^a-z0-9ñ\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        v = float(value)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except Exception:
        return default


def safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "si", "sí"}


# ---------------------------------------------------------------------
# Column detection
# ---------------------------------------------------------------------

def first_existing_col(df: pd.DataFrame, candidates: List[str], required: bool = False) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    if required:
        raise KeyError(f"No se encontró ninguna columna entre: {candidates}")
    return None


def detect_ranking_columns(df: pd.DataFrame, version: str) -> Dict[str, Optional[str]]:
    suffix = "_v1" if version == "v1" else "_v2"

    return {
        "place_id": first_existing_col(df, [f"place_id{suffix}", "place_id"], required=True),
        "place_name": first_existing_col(df, [f"place_name{suffix}", "place_name"], required=True),
        "dish_id": first_existing_col(df, [f"dish_id{suffix}", "dish_id_v1", "dish_id_v2", "dish_id"]),
        "dish_name": first_existing_col(
            df,
            [
                f"dish_display_name{suffix}",
                f"display_dish_name_es{suffix}",
                "display_dish_name_es_v1",
                "dish_display_name_v2",
                "dish_name",
                "dish_name_norm_v2",
            ],
            required=True,
        ),
        "district_id": first_existing_col(df, [f"district_id{suffix}", "district_id"]),
        "district_name": first_existing_col(df, [f"district_name{suffix}", "district_name"]),
        "neighborhood_id": first_existing_col(df, [f"neighborhood_id{suffix}", "neighborhood_id"]),
        "neighborhood_name": first_existing_col(df, [f"neighborhood_name{suffix}", "neighborhood_name"]),
        "score": first_existing_col(df, [f"hidden_gem_score{suffix}", "hidden_gem_score_v1", "hidden_gem_score_v2", "hidden_gem_score"], required=True),
        "tier": first_existing_col(df, [f"hidden_gem_tier{suffix}", "hidden_gem_tier_v1", "hidden_gem_tier_v2", "hidden_gem_tier"]),
        "global_rank": first_existing_col(df, [f"hidden_gem_global_rank{suffix}", "hidden_gem_global_rank_v1", "hidden_gem_global_rank_v2"]),
        "selected_rank": first_existing_col(df, [f"hidden_gem_selected_rank{suffix}", "hidden_gem_selected_rank_v1", "hidden_gem_selected_rank_v2"]),
        "selected": first_existing_col(df, [f"selected_hidden_gem{suffix}", "selected_hidden_gem_v1", "selected_hidden_gem_v2"]),
        "mention_count": first_existing_col(df, [f"mention_count{suffix}", "mention_count_v1", "mention_count_v2", "mention_count"]),
        "review_count": first_existing_col(df, [f"review_count{suffix}", "review_count_v1", "review_count_v2", "review_count"]),
        "positive_ratio": first_existing_col(df, [f"positive_ratio{suffix}", "positive_ratio_v1", "positive_ratio_v2", "positive_ratio"]),
        "negative_ratio": first_existing_col(df, [f"negative_ratio{suffix}", "negative_ratio_v1", "negative_ratio_v2", "negative_ratio"]),
        "weighted_sentiment": first_existing_col(df, [f"weighted_sentiment_score{suffix}", "weighted_sentiment_score_v2", "mention_sentiment_score_v1"]),
        "evidence_tier": first_existing_col(df, [f"evidence_tier{suffix}", "evidence_tier_v1", "evidence_tier_v2", "evidence_tier"]),
        "quality_tier": first_existing_col(df, [f"aggregate_quality_tier{suffix}", f"signal_quality_tier{suffix}", "aggregate_quality_tier_v2", "signal_quality_tier_v1"]),
        "explanation": first_existing_col(df, [f"ranking_explanation{suffix}", "ranking_explanation_v1", "ranking_explanation_v2"]),
    }


def filter_selected(df: pd.DataFrame, cols: Dict[str, Optional[str]]) -> pd.DataFrame:
    out = df.copy()

    selected_col = cols.get("selected")
    tier_col = cols.get("tier")

    if selected_col and selected_col in out.columns:
        mask = out[selected_col].map(safe_bool)
        return out[mask].copy().reset_index(drop=True)

    if tier_col and tier_col in out.columns:
        return out[out[tier_col].fillna("").astype(str) != "not_selected"].copy().reset_index(drop=True)

    return out.copy().reset_index(drop=True)


def make_match_key(row: pd.Series, cols: Dict[str, Optional[str]], mode: str) -> str:
    place_id = safe_str(row.get(cols["place_id"]))
    dish_id = safe_str(row.get(cols["dish_id"])) if cols.get("dish_id") else ""
    dish_name_norm = normalize_text(row.get(cols["dish_name"]))

    if mode == "place_dish_id":
        return f"place::{place_id}::dish_id::{dish_id}"

    if mode == "place_dish_name":
        return f"place::{place_id}::dish_name::{dish_name_norm}"

    # Hybrid fallback. Prefer ID when available, but append name to reduce false matches
    # if catalogs diverge.
    if dish_id:
        return f"place::{place_id}::dish_id::{dish_id}::name::{dish_name_norm}"

    return f"place::{place_id}::dish_name::{dish_name_norm}"


def standardize_ranking_df(
    df: pd.DataFrame,
    version: str,
    match_mode: str,
    selected_only: bool = True,
) -> Tuple[pd.DataFrame, Dict[str, Optional[str]]]:
    cols = detect_ranking_columns(df, version)

    work = filter_selected(df, cols) if selected_only else df.copy()
    work = work.reset_index(drop=True)

    rows: List[Dict[str, Any]] = []

    for idx, row in work.iterrows():
        rank = safe_float(row.get(cols["selected_rank"]), default=0.0)
        if rank == 0.0:
            rank = safe_float(row.get(cols["global_rank"]), default=float(idx + 1))

        std = {
            "match_key": make_match_key(row, cols, match_mode),
            f"{version}_source_row_index": int(idx),
            f"{version}_place_id": safe_str(row.get(cols["place_id"])),
            f"{version}_place_name": safe_str(row.get(cols["place_name"])),
            f"{version}_dish_id": safe_str(row.get(cols["dish_id"])) if cols.get("dish_id") else "",
            f"{version}_dish_name": safe_str(row.get(cols["dish_name"])),
            f"{version}_dish_name_norm": normalize_text(row.get(cols["dish_name"])),
            f"{version}_district_id": safe_str(row.get(cols["district_id"])) if cols.get("district_id") else "",
            f"{version}_district_name": safe_str(row.get(cols["district_name"])) if cols.get("district_name") else "",
            f"{version}_neighborhood_id": safe_str(row.get(cols["neighborhood_id"])) if cols.get("neighborhood_id") else "",
            f"{version}_neighborhood_name": safe_str(row.get(cols["neighborhood_name"])) if cols.get("neighborhood_name") else "",
            f"{version}_score": safe_float(row.get(cols["score"])),
            f"{version}_tier": safe_str(row.get(cols["tier"])) if cols.get("tier") else "",
            f"{version}_rank": int(rank) if rank else int(idx + 1),
            f"{version}_mention_count": safe_float(row.get(cols["mention_count"]), default=0.0) if cols.get("mention_count") else 0.0,
            f"{version}_review_count": safe_float(row.get(cols["review_count"]), default=0.0) if cols.get("review_count") else 0.0,
            f"{version}_positive_ratio": safe_float(row.get(cols["positive_ratio"]), default=0.0) if cols.get("positive_ratio") else 0.0,
            f"{version}_negative_ratio": safe_float(row.get(cols["negative_ratio"]), default=0.0) if cols.get("negative_ratio") else 0.0,
            f"{version}_weighted_sentiment": safe_float(row.get(cols["weighted_sentiment"]), default=0.0) if cols.get("weighted_sentiment") else 0.0,
            f"{version}_evidence_tier": safe_str(row.get(cols["evidence_tier"])) if cols.get("evidence_tier") else "",
            f"{version}_quality_tier": safe_str(row.get(cols["quality_tier"])) if cols.get("quality_tier") else "",
            f"{version}_explanation": safe_str(row.get(cols["explanation"])) if cols.get("explanation") else "",
        }

        rows.append(std)

    out = pd.DataFrame(rows)

    # Deduplicate selected rows by match_key, keeping the best rank / highest score.
    if len(out):
        out = (
            out.sort_values([f"{version}_rank", f"{version}_score"], ascending=[True, False])
            .drop_duplicates(subset=["match_key"], keep="first")
            .reset_index(drop=True)
        )

    return out, cols


# ---------------------------------------------------------------------
# Comparison logic
# ---------------------------------------------------------------------

def summarize_numeric(series: pd.Series) -> Dict[str, Any]:
    if series is None or len(series) == 0:
        return {}

    numeric = pd.to_numeric(series, errors="coerce").dropna()
    if len(numeric) == 0:
        return {}

    return {
        "count": int(len(numeric)),
        "mean": round(float(numeric.mean()), 6),
        "std": round(float(numeric.std(ddof=1)), 6) if len(numeric) > 1 else 0.0,
        "min": round(float(numeric.min()), 6),
        "25%": round(float(numeric.quantile(0.25)), 6),
        "50%": round(float(numeric.quantile(0.50)), 6),
        "75%": round(float(numeric.quantile(0.75)), 6),
        "max": round(float(numeric.max()), 6),
    }


def group_count_shift(
    v1: pd.DataFrame,
    v2: pd.DataFrame,
    group_col_v1: str,
    group_col_v2: str,
    label: str,
) -> pd.DataFrame:
    v1_counts = (
        v1[group_col_v1].fillna("").astype(str).replace("", "UNKNOWN")
        .value_counts()
        .rename("v1_selected_count")
        .reset_index()
        .rename(columns={"index": label, group_col_v1: label})
    )

    # pandas value_counts reset_index names may vary
    v1_counts.columns = [label, "v1_selected_count"]

    v2_counts = (
        v2[group_col_v2].fillna("").astype(str).replace("", "UNKNOWN")
        .value_counts()
        .rename("v2_selected_count")
        .reset_index()
    )
    v2_counts.columns = [label, "v2_selected_count"]

    out = v1_counts.merge(v2_counts, on=label, how="outer").fillna(0)
    out["v1_selected_count"] = out["v1_selected_count"].astype(int)
    out["v2_selected_count"] = out["v2_selected_count"].astype(int)
    out["delta_v2_minus_v1"] = out["v2_selected_count"] - out["v1_selected_count"]

    out = out.sort_values(["delta_v2_minus_v1", "v2_selected_count"], ascending=[False, False]).reset_index(drop=True)
    return out


def build_overlap(v1: pd.DataFrame, v2: pd.DataFrame) -> pd.DataFrame:
    overlap = v1.merge(v2, on="match_key", how="inner")

    if len(overlap):
        overlap["score_delta_v2_minus_v1"] = overlap["v2_score"] - overlap["v1_score"]
        overlap["rank_delta_v2_minus_v1"] = overlap["v2_rank"] - overlap["v1_rank"]
        overlap["rank_improved_in_v2"] = overlap["rank_delta_v2_minus_v1"] < 0
        overlap["tier_changed"] = overlap["v1_tier"] != overlap["v2_tier"]
        overlap["review_count_delta_v2_minus_v1"] = overlap["v2_review_count"] - overlap["v1_review_count"]
        overlap["mention_count_delta_v2_minus_v1"] = overlap["v2_mention_count"] - overlap["v1_mention_count"]

    return overlap


def select_display_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    if kind == "overlap":
        cols = [
            "match_key",
            "v1_rank", "v2_rank", "rank_delta_v2_minus_v1",
            "v1_score", "v2_score", "score_delta_v2_minus_v1",
            "v1_tier", "v2_tier", "tier_changed",
            "v1_place_name", "v2_place_name",
            "v1_dish_name", "v2_dish_name",
            "v1_district_name", "v2_district_name",
            "v1_neighborhood_name", "v2_neighborhood_name",
            "v1_mention_count", "v2_mention_count",
            "v1_review_count", "v2_review_count",
            "v1_positive_ratio", "v2_positive_ratio",
            "v1_negative_ratio", "v2_negative_ratio",
            "v1_evidence_tier", "v2_evidence_tier",
            "v1_quality_tier", "v2_quality_tier",
            "v1_explanation", "v2_explanation",
        ]
    elif kind == "v1":
        cols = [
            "match_key",
            "v1_rank", "v1_score", "v1_tier",
            "v1_place_id", "v1_place_name",
            "v1_dish_id", "v1_dish_name",
            "v1_district_name", "v1_neighborhood_name",
            "v1_mention_count", "v1_review_count",
            "v1_positive_ratio", "v1_negative_ratio",
            "v1_evidence_tier", "v1_quality_tier",
            "v1_explanation",
        ]
    else:
        cols = [
            "match_key",
            "v2_rank", "v2_score", "v2_tier",
            "v2_place_id", "v2_place_name",
            "v2_dish_id", "v2_dish_name",
            "v2_district_name", "v2_neighborhood_name",
            "v2_mention_count", "v2_review_count",
            "v2_positive_ratio", "v2_negative_ratio",
            "v2_weighted_sentiment",
            "v2_evidence_tier", "v2_quality_tier",
            "v2_explanation",
        ]

    return df[[c for c in cols if c in df.columns]].copy()


def build_recommendations(summary: Dict[str, Any], top_v2_only: pd.DataFrame, top_v1_only: pd.DataFrame) -> str:
    counts = summary["counts"]
    diversity = summary["diversity_delta"]
    quality = summary["quality"]

    lines = [
        "# Ranking v1 vs v2 — Recommended Next Steps",
        "",
        "## Executive summary",
        "",
        f"- V1 selected candidates: **{counts['v1_selected_unique']}**.",
        f"- V2 selected candidates: **{counts['v2_selected_unique']}**.",
        f"- Matched candidates: **{counts['matched_candidates']}**.",
        f"- V2-only candidates: **{counts['v2_only_candidates']}**.",
        f"- V1-only candidates: **{counts['v1_only_candidates']}**.",
        f"- Jaccard overlap: **{quality['jaccard_overlap']:.3f}**.",
        "",
        "## Diversity shift",
        "",
        f"- Selected places: {diversity['selected_places']['v1']} → {diversity['selected_places']['v2']} ({diversity['selected_places']['delta_v2_minus_v1']:+d}).",
        f"- Selected dishes: {diversity['selected_dishes']['v1']} → {diversity['selected_dishes']['v2']} ({diversity['selected_dishes']['delta_v2_minus_v1']:+d}).",
        f"- Selected neighborhoods: {diversity['selected_neighborhoods']['v1']} → {diversity['selected_neighborhoods']['v2']} ({diversity['selected_neighborhoods']['delta_v2_minus_v1']:+d}).",
        f"- Selected districts: {diversity['selected_districts']['v1']} → {diversity['selected_districts']['v2']} ({diversity['selected_districts']['delta_v2_minus_v1']:+d}).",
        "",
        "## Recommended actions",
        "",
        "1. Review the top V2-only candidates first. These are the main new discoveries introduced by the trained-model pipeline.",
        "2. Review V1-only high-score candidates to check whether V2 is losing useful candidates or filtering weak/noisy ones correctly.",
        "3. Inspect generic dishes that dominate the top ranks, especially hamburger, pizza, churros, montadito, croquetas and similar broad categories.",
        "4. Keep V2 marked as experimental until a manual review sample is completed.",
        "5. If the comparison looks good, use V2 for the dashboard as the main experimental ranking, while keeping V1 as a baseline tab.",
        "",
    ]

    if len(top_v2_only):
        lines.extend([
            "## Top V2-only candidates to review",
            "",
        ])
        for _, row in top_v2_only.head(10).iterrows():
            lines.append(
                f"- {row.get('v2_place_name', '')} → {row.get('v2_dish_name', '')} "
                f"({row.get('v2_score', 0):.2f}, {row.get('v2_tier', '')})"
            )
        lines.append("")

    if len(top_v1_only):
        lines.extend([
            "## Top V1-only candidates to review",
            "",
        ])
        for _, row in top_v1_only.head(10).iterrows():
            lines.append(
                f"- {row.get('v1_place_name', '')} → {row.get('v1_dish_name', '')} "
                f"({row.get('v1_score', 0):.2f}, {row.get('v1_tier', '')})"
            )
        lines.append("")

    lines.extend([
        "## Interpretation",
        "",
        "A high V2-only count is not necessarily bad: V2 uses NER, entity linking and ABSA sentiment, so it can surface candidates that V1 did not detect.",
        "A low overlap should trigger manual inspection before replacing V1 in any final presentation.",
        "The safest approach is to present V2 as `IA v2 experimental` and explicitly state that `is_production_ready_v2 = false`.",
        "",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare Sevilla Hidden Gems ranking v1 vs v2."
    )

    parser.add_argument(
        "--v1-path",
        type=str,
        default=None,
        help="Path to ranking v1 selected CSV/JSONL. If omitted, tries common locations.",
    )
    parser.add_argument(
        "--v2-path",
        type=str,
        default="data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.csv",
        help="Path to ranking v2 selected CSV/JSONL.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison",
        help="Output directory for comparison artifacts.",
    )
    parser.add_argument(
        "--match-mode",
        type=str,
        default="place_dish_name",
        choices=["place_dish_name", "place_dish_id", "place_dish_name_or_id"],
        help="How to match candidates across ranking versions.",
    )
    parser.add_argument(
        "--compare-selected-only",
        action="store_true",
        default=True,
        help="Compare selected candidates only. Enabled by default.",
    )
    parser.add_argument(
        "--include-all-if-no-selected-column",
        action="store_true",
        default=True,
        help="Use all rows if no selected/tier column exists.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=50,
        help="Number of top records to include in summary previews.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with non-zero status if key checks fail.",
    )

    return parser.parse_args()


def resolve_v1_path(v1_path_arg: Optional[str]) -> Path:
    if v1_path_arg:
        path = Path(v1_path_arg)
        if not path.exists():
            raise FileNotFoundError(f"No existe --v1-path: {path}")
        return path

    candidates = [
        Path("data/artifacts/ai/sevilla/ranking_pilot/sevilla_hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/ranking_pilot/sevilla_hidden_gems_ranking_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/ranking_v1/sevilla_hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/hidden_gems_ranking_v1/sevilla_hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/sevilla_hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/ranking/sevilla_hidden_gems_selected_v1.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/candidates_detail.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/top_global.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/candidates_all.csv"),
    ]

    found = find_first_existing(candidates)
    if found:
        return found

    msg = [
        "No se pudo localizar automáticamente el ranking v1.",
        "Pasa la ruta explícitamente con --v1-path.",
        "",
        "Rutas probadas:",
    ]
    msg.extend([f"- {p}" for p in candidates])
    raise FileNotFoundError("\n".join(msg))


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    v1_path = resolve_v1_path(args.v1_path)
    v2_path = Path(args.v2_path)

    print(f"Patch: {PATCH_ID}")
    print(f"Loading v1 ranking: {v1_path}")
    print(f"Loading v2 ranking: {v2_path}")

    v1_raw = read_table(v1_path)
    v2_raw = read_table(v2_path)

    print(f"V1 raw rows: {len(v1_raw)}")
    print(f"V2 raw rows: {len(v2_raw)}")

    v1, v1_cols = standardize_ranking_df(v1_raw, "v1", args.match_mode, selected_only=args.compare_selected_only)
    v2, v2_cols = standardize_ranking_df(v2_raw, "v2", args.match_mode, selected_only=args.compare_selected_only)

    print(f"V1 selected unique: {len(v1)}")
    print(f"V2 selected unique: {len(v2)}")

    overlap = build_overlap(v1, v2)

    v1_keys = set(v1["match_key"].tolist())
    v2_keys = set(v2["match_key"].tolist())
    overlap_keys = set(overlap["match_key"].tolist())

    v1_only = v1[~v1["match_key"].isin(overlap_keys)].copy()
    v2_only = v2[~v2["match_key"].isin(overlap_keys)].copy()

    v1_only = v1_only.sort_values(["v1_score", "v1_rank"], ascending=[False, True]).reset_index(drop=True)
    v2_only = v2_only.sort_values(["v2_score", "v2_rank"], ascending=[False, True]).reset_index(drop=True)

    score_shift = overlap.sort_values("score_delta_v2_minus_v1", ascending=False).reset_index(drop=True)

    district_shift = group_count_shift(v1, v2, "v1_district_name", "v2_district_name", "district_name")
    neighborhood_shift = group_count_shift(v1, v2, "v1_neighborhood_name", "v2_neighborhood_name", "neighborhood_name")
    dish_shift = group_count_shift(v1, v2, "v1_dish_name_norm", "v2_dish_name_norm", "dish_name_norm")

    # Tier shift for matched rows.
    if len(overlap):
        tier_shift = (
            overlap.groupby(["v1_tier", "v2_tier"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
            .reset_index(drop=True)
        )
    else:
        tier_shift = pd.DataFrame(columns=["v1_tier", "v2_tier", "count"])

    paths = {
        "summary_json": output_dir / "sevilla_ranking_v1_vs_v2_summary.json",
        "overlap_csv": output_dir / "ranking_overlap.csv",
        "v1_only_csv": output_dir / "v1_only_candidates.csv",
        "v2_only_csv": output_dir / "v2_only_candidates.csv",
        "score_shift_csv": output_dir / "score_shift_comparison.csv",
        "district_shift_csv": output_dir / "top_district_shift.csv",
        "neighborhood_shift_csv": output_dir / "top_neighborhood_shift.csv",
        "dish_shift_csv": output_dir / "top_dish_shift.csv",
        "tier_shift_csv": output_dir / "tier_shift_summary.csv",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }

    select_display_columns(overlap, "overlap").to_csv(paths["overlap_csv"], index=False, encoding="utf-8")
    select_display_columns(v1_only, "v1").to_csv(paths["v1_only_csv"], index=False, encoding="utf-8")
    select_display_columns(v2_only, "v2").to_csv(paths["v2_only_csv"], index=False, encoding="utf-8")
    select_display_columns(score_shift, "overlap").to_csv(paths["score_shift_csv"], index=False, encoding="utf-8")
    district_shift.to_csv(paths["district_shift_csv"], index=False, encoding="utf-8")
    neighborhood_shift.to_csv(paths["neighborhood_shift_csv"], index=False, encoding="utf-8")
    dish_shift.to_csv(paths["dish_shift_csv"], index=False, encoding="utf-8")
    tier_shift.to_csv(paths["tier_shift_csv"], index=False, encoding="utf-8")

    union_count = len(v1_keys | v2_keys)
    matched_count = len(overlap_keys)

    def diversity_block(version_df: pd.DataFrame, prefix: str) -> Dict[str, int]:
        return {
            "selected_places": int(version_df[f"{prefix}_place_id"].replace("", np.nan).nunique(dropna=True)),
            "selected_dishes": int(version_df[f"{prefix}_dish_name_norm"].replace("", np.nan).nunique(dropna=True)),
            "selected_neighborhoods": int(version_df[f"{prefix}_neighborhood_name"].replace("", np.nan).nunique(dropna=True)),
            "selected_districts": int(version_df[f"{prefix}_district_name"].replace("", np.nan).nunique(dropna=True)),
        }

    v1_div = diversity_block(v1, "v1")
    v2_div = diversity_block(v2, "v2")

    diversity_delta = {
        "selected_places": {
            "v1": v1_div["selected_places"],
            "v2": v2_div["selected_places"],
            "delta_v2_minus_v1": v2_div["selected_places"] - v1_div["selected_places"],
        },
        "selected_dishes": {
            "v1": v1_div["selected_dishes"],
            "v2": v2_div["selected_dishes"],
            "delta_v2_minus_v1": v2_div["selected_dishes"] - v1_div["selected_dishes"],
        },
        "selected_neighborhoods": {
            "v1": v1_div["selected_neighborhoods"],
            "v2": v2_div["selected_neighborhoods"],
            "delta_v2_minus_v1": v2_div["selected_neighborhoods"] - v1_div["selected_neighborhoods"],
        },
        "selected_districts": {
            "v1": v1_div["selected_districts"],
            "v2": v2_div["selected_districts"],
            "delta_v2_minus_v1": v2_div["selected_districts"] - v1_div["selected_districts"],
        },
    }

    top_v2_only_preview = select_display_columns(v2_only, "v2").head(args.top_n)
    top_v1_only_preview = select_display_columns(v1_only, "v1").head(args.top_n)

    checks = {
        "v1_path_exists": v1_path.exists(),
        "v2_path_exists": v2_path.exists(),
        "has_v1_rows": len(v1_raw) > 0,
        "has_v2_rows": len(v2_raw) > 0,
        "has_v1_selected": len(v1) > 0,
        "has_v2_selected": len(v2) > 0,
        "has_overlap": matched_count > 0,
        "overlap_csv_exists": paths["overlap_csv"].exists(),
        "v1_only_csv_exists": paths["v1_only_csv"].exists(),
        "v2_only_csv_exists": paths["v2_only_csv"].exists(),
    }

    warnings: List[str] = []
    errors: List[str] = []

    if not checks["has_overlap"]:
        warnings.append("No overlap found between v1 and v2 using current match mode. Try --match-mode place_dish_name if using place_dish_id, or inspect IDs.")
    if matched_count and len(v2) and (matched_count / len(v2)) < 0.25:
        warnings.append("Low v2 overlap with v1. Manual review recommended before using v2 as replacement.")
    if len(v2_only) > len(v2) * 0.60:
        warnings.append("Most v2 candidates are new vs v1. Review v2-only candidates carefully.")
    if v2_div["selected_dishes"] < v1_div["selected_dishes"]:
        warnings.append("V2 has fewer selected dish types than v1. Check whether generic dishes dominate.")
    if v2_div["selected_neighborhoods"] < v1_div["selected_neighborhoods"]:
        warnings.append("V2 has lower neighborhood diversity than v1.")

    if args.strict:
        required_checks = [
            "v1_path_exists",
            "v2_path_exists",
            "has_v1_rows",
            "has_v2_rows",
            "has_v1_selected",
            "has_v2_selected",
            "overlap_csv_exists",
            "v1_only_csv_exists",
            "v2_only_csv_exists",
        ]
        for check in required_checks:
            if not checks.get(check):
                errors.append(f"Strict check failed: {check}")

    summary = {
        "script": SCRIPT_NAME,
        "patch_id": PATCH_ID,
        "version": "sevilla_ranking_v1_vs_v2_comparison",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "v1_path": str(v1_path),
            "v2_path": str(v2_path),
            "output_dir": str(output_dir),
            "match_mode": args.match_mode,
            "compare_selected_only": args.compare_selected_only,
        },
        "column_mapping": {
            "v1": v1_cols,
            "v2": v2_cols,
        },
        "counts": {
            "v1_raw_rows": int(len(v1_raw)),
            "v2_raw_rows": int(len(v2_raw)),
            "v1_selected_unique": int(len(v1)),
            "v2_selected_unique": int(len(v2)),
            "matched_candidates": int(matched_count),
            "v1_only_candidates": int(len(v1_only)),
            "v2_only_candidates": int(len(v2_only)),
            "union_candidates": int(union_count),
        },
        "quality": {
            "jaccard_overlap": round(float(matched_count / union_count), 6) if union_count else 0.0,
            "v1_coverage_in_v2": round(float(matched_count / len(v1)), 6) if len(v1) else 0.0,
            "v2_coverage_in_v1": round(float(matched_count / len(v2)), 6) if len(v2) else 0.0,
            "score_shift_summary_matched_v2_minus_v1": summarize_numeric(overlap["score_delta_v2_minus_v1"]) if len(overlap) else {},
            "rank_shift_summary_matched_v2_minus_v1": summarize_numeric(overlap["rank_delta_v2_minus_v1"]) if len(overlap) else {},
        },
        "diversity": {
            "v1": v1_div,
            "v2": v2_div,
        },
        "diversity_delta": diversity_delta,
        "tier_counts": {
            "v1": v1["v1_tier"].value_counts().to_dict() if "v1_tier" in v1.columns else {},
            "v2": v2["v2_tier"].value_counts().to_dict() if "v2_tier" in v2.columns else {},
        },
        "score_summary": {
            "v1_selected": summarize_numeric(v1["v1_score"]),
            "v2_selected": summarize_numeric(v2["v2_score"]),
        },
        "top_v2_only": top_v2_only_preview.to_dict(orient="records"),
        "top_v1_only": top_v1_only_preview.to_dict(orient="records"),
        "top_score_increases_matched": select_display_columns(
            score_shift.sort_values("score_delta_v2_minus_v1", ascending=False).head(args.top_n),
            "overlap",
        ).to_dict(orient="records") if len(score_shift) else [],
        "top_score_decreases_matched": select_display_columns(
            score_shift.sort_values("score_delta_v2_minus_v1", ascending=True).head(args.top_n),
            "overlap",
        ).to_dict(orient="records") if len(score_shift) else [],
        "top_district_shift": district_shift.head(args.top_n).to_dict(orient="records"),
        "top_neighborhood_shift": neighborhood_shift.head(args.top_n).to_dict(orient="records"),
        "top_dish_shift": dish_shift.head(args.top_n).to_dict(orient="records"),
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "files": {k: str(v) for k, v in paths.items()},
        "notes": [
            "This comparison is intended to validate the experimental IA v2 ranking against the v1 pilot baseline.",
            "The default match key is place_id + normalized dish name, because dish IDs may change between versions.",
            "V2 should remain experimental until v2-only and v1-only candidates are manually reviewed.",
        ],
    }

    write_json(paths["summary_json"], summary)

    recommendations_md = build_recommendations(
        summary=summary,
        top_v2_only=top_v2_only_preview,
        top_v1_only=top_v1_only_preview,
    )
    write_markdown(paths["recommendations_md"], recommendations_md)

    print(json.dumps(to_builtin({
        "counts": summary["counts"],
        "quality": summary["quality"],
        "diversity_delta": summary["diversity_delta"],
        "checks": summary["checks"],
        "warnings": summary["warnings"],
        "errors": summary["errors"],
        "summary_json": str(paths["summary_json"]),
    }), indent=2, ensure_ascii=False, default=json_default))

    if args.strict and errors:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
