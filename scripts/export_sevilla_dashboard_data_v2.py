"""Export dashboard-ready datasets for Hidden Gems Sevilla Ranking v2.

This script converts the experimental IA v2 ranking artifacts into a clean,
Streamlit/BI-friendly dashboard contract.

Typical usage:

python -m scripts.export_sevilla_dashboard_data_v2 `
  --ranking-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_ranking_v2.jsonl `
  --selected-path data/artifacts/ai/sevilla/model_inference/ranking_v2/sevilla_hidden_gems_selected_v2.jsonl `
  --signals-path data/artifacts/ai/sevilla/model_inference/place_dish_signals_v2/sevilla_place_dish_signals_v2.jsonl `
  --mentions-path data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1/sevilla_dish_mentions_with_absa_sentiment_v1.jsonl `
  --comparison-dir data/artifacts/ai/sevilla/model_inference/ranking_v2_comparison `
  --coordinates-path data/artifacts/ai/sevilla/dashboard/candidates_detail.csv `
  --output-dir data/artifacts/ai/sevilla/dashboard_v2 `
  --expected-selected 268 `
  --include-mentions `
  --examples-per-candidate 5 `
  --strict
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import Counter
from datetime import datetime, date, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

import numpy as np
import pandas as pd

PATCH_ID = "dashboard_export_v2_real_coordinates_patch_2026_05_15"
SCRIPT_NAME = "export_sevilla_dashboard_data_v2"
VERSION = "sevilla_dashboard_export_v2"


# ---------------------------------------------------------------------------
# Generic IO / serialization helpers
# ---------------------------------------------------------------------------


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    if isinstance(value, str) and value.strip().lower() in {"", "nan", "none", "null", "na", "nat"}:
        return True
    return False


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    if is_missing(value):
        return default
    try:
        out = float(value)
        if not math.isfinite(out):
            return default
        return out
    except Exception:
        return default


def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if is_missing(value):
        return default
    try:
        out = int(float(value))
        return out
    except Exception:
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    if is_missing(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "t", "1", "yes", "y", "si", "sí"}:
        return True
    if text in {"false", "f", "0", "no", "n"}:
        return False
    return default


def json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return str(obj)


def to_builtin(obj: Any) -> Any:
    """Recursively convert pandas/numpy/UUID values into JSON-safe values."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, bool)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        value = float(obj)
        return value if math.isfinite(value) else None
    if isinstance(obj, dict):
        return {str(k): to_builtin(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [to_builtin(v) for v in obj]
    try:
        if pd.isna(obj):
            return None
    except Exception:
        pass
    return str(obj)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, default=json_default)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_builtin(row), ensure_ascii=False, allow_nan=False, default=json_default) + "\n")


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return pd.DataFrame(rows)


def read_table(path: Optional[Path], required: bool = True) -> pd.DataFrame:
    if path is None:
        if required:
            raise FileNotFoundError("Missing required path")
        return pd.DataFrame()
    if not path.exists():
        if required:
            raise FileNotFoundError(f"File does not exist: {path}")
        return pd.DataFrame()
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            return pd.DataFrame([data])
        raise ValueError(f"Unsupported JSON content in {path}")
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix in {".parquet"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file extension: {path}")


def write_df(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].map(lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else x)
    out.to_csv(path, index=False, encoding="utf-8")


# ---------------------------------------------------------------------------
# Column handling
# ---------------------------------------------------------------------------


def first_col(df: pd.DataFrame, candidates: Sequence[str], required: bool = False) -> Optional[str]:
    for col in candidates:
        if col in df.columns:
            return col
    if required:
        raise KeyError(f"None of these columns were found: {list(candidates)}")
    return None


def add_coalesced(df: pd.DataFrame, output_col: str, candidates: Sequence[str], default: Any = None) -> pd.Series:
    existing = [c for c in candidates if c in df.columns]
    if not existing:
        df[output_col] = default
        return df[output_col]
    series = df[existing[0]].copy()
    for col in existing[1:]:
        series = series.where(~series.map(is_missing), df[col])
    series = series.where(~series.map(is_missing), default)
    df[output_col] = series
    return df[output_col]


def normalize_dashboard_columns(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Create stable dashboard columns from v2/v1 artifacts."""
    out = df.copy()

    add_coalesced(out, "place_id_std", ["place_id", "v2_place_id", "v1_place_id"])
    add_coalesced(out, "place_name_std", ["place_name", "place_name_v2", "v2_place_name", "v1_place_name"])
    add_coalesced(out, "dish_id_std", ["dish_id_v2", "dish_id", "v2_dish_id", "v1_dish_id"])
    add_coalesced(out, "dish_name_std", ["dish_display_name_v2", "dish_name", "dish_name_v2", "v2_dish_name", "v1_dish_name"])
    add_coalesced(out, "district_id_std", ["district_id", "v2_district_id", "v1_district_id"])
    add_coalesced(out, "district_name_std", ["district_name", "district_name_v2", "v2_district_name", "v1_district_name"])
    add_coalesced(out, "neighborhood_id_std", ["neighborhood_id", "v2_neighborhood_id", "v1_neighborhood_id"])
    add_coalesced(out, "neighborhood_name_std", ["neighborhood_name", "neighborhood_name_v2", "v2_neighborhood_name", "v1_neighborhood_name"])

    # Geographic coordinates. These are optional in intermediate IA v2 artifacts,
    # so the export can enrich them later from v1 dashboard artifacts or any
    # user-provided coordinate reference.
    add_coalesced(
        out,
        "latitude_std",
        [
            "latitude_std",
            "place_latitude_std",
            "latitude",
            "lat",
            "place_latitude",
            "place_lat",
            "location_latitude",
            "centroid_latitude",
            "y",
        ],
    )
    add_coalesced(
        out,
        "longitude_std",
        [
            "longitude_std",
            "place_longitude_std",
            "longitude",
            "lon",
            "lng",
            "place_longitude",
            "place_lon",
            "place_lng",
            "location_longitude",
            "centroid_longitude",
            "x",
        ],
    )
    add_coalesced(out, "coordinate_source_std", ["coordinate_source_std", "coordinate_source", "geo_source"], None)

    add_coalesced(out, "score_std", ["hidden_gem_score_v2", "hidden_gem_score", "score", "v2_score", "v1_score"], 0.0)
    add_coalesced(out, "tier_std", ["hidden_gem_tier_v2", "hidden_gem_tier", "tier", "v2_tier", "v1_tier"], "not_selected")
    add_coalesced(out, "global_rank_std", ["hidden_gem_global_rank_v2", "global_rank", "rank", "v2_rank", "v1_rank"])
    add_coalesced(out, "selected_rank_std", ["hidden_gem_selected_rank_v2", "selected_rank", "v2_selected_rank"])
    add_coalesced(out, "selected_std", ["selected_hidden_gem_v2", "selected", "is_selected"], True if source == "selected_v2" else False)

    add_coalesced(out, "mention_count_std", ["mention_count_v2", "mention_count", "v2_mention_count", "v1_mention_count"], 0)
    add_coalesced(out, "review_count_std", ["review_count_v2", "review_count", "v2_review_count", "v1_review_count"], 0)
    add_coalesced(out, "positive_ratio_std", ["positive_ratio_v2", "positive_ratio", "v2_positive_ratio", "v1_positive_ratio"], 0.0)
    add_coalesced(out, "negative_ratio_std", ["negative_ratio_v2", "negative_ratio", "v2_negative_ratio", "v1_negative_ratio"], 0.0)
    add_coalesced(out, "neutral_ratio_std", ["neutral_ratio_v2", "neutral_ratio"], 0.0)
    add_coalesced(out, "weighted_sentiment_std", ["weighted_sentiment_score_v2", "weighted_sentiment", "v2_weighted_sentiment"], None)
    add_coalesced(out, "evidence_tier_std", ["evidence_tier_v2", "evidence_tier", "v2_evidence_tier", "v1_evidence_tier"], "unknown")
    add_coalesced(out, "quality_tier_std", ["aggregate_quality_tier_v2", "quality_tier", "v2_quality_tier"], "unknown")
    add_coalesced(out, "explanation_std", ["ranking_explanation_v2", "explanation", "v2_explanation"], "")
    add_coalesced(out, "is_production_ready_std", ["is_production_ready_v2", "is_production_ready"], False)
    add_coalesced(out, "ready_for_ranking_std", ["ready_for_ranking_v2", "ready_for_ranking"], None)

    numeric_cols = [
        "score_std",
        "global_rank_std",
        "selected_rank_std",
        "mention_count_std",
        "review_count_std",
        "positive_ratio_std",
        "neutral_ratio_std",
        "negative_ratio_std",
        "weighted_sentiment_std",
        "latitude_std",
        "longitude_std",
    ]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    # Coordinates outside valid latitude/longitude ranges are treated as missing.
    if "latitude_std" in out.columns:
        out.loc[~out["latitude_std"].between(-90, 90), "latitude_std"] = np.nan
    if "longitude_std" in out.columns:
        out.loc[~out["longitude_std"].between(-180, 180), "longitude_std"] = np.nan
    if "coordinate_source_std" in out.columns:
        has_coords = out.get("latitude_std", pd.Series(index=out.index, dtype=float)).notna() & out.get("longitude_std", pd.Series(index=out.index, dtype=float)).notna()
        out["coordinate_source_std"] = out["coordinate_source_std"].where(~out["coordinate_source_std"].map(is_missing), None)
        out.loc[has_coords & out["coordinate_source_std"].isna(), "coordinate_source_std"] = source

    out["selected_std"] = out["selected_std"].map(lambda x: safe_bool(x, default=(source == "selected_v2")))
    out["is_production_ready_std"] = out["is_production_ready_std"].map(lambda x: safe_bool(x, default=False))

    # Stable key used across dashboard datasets.
    out["dashboard_candidate_key"] = (
        "place::"
        + out["place_id_std"].fillna("").astype(str)
        + "::dish::"
        + out["dish_id_std"].fillna(out["dish_name_std"]).fillna("").astype(str)
    )

    return out


def preferred_dashboard_columns(df: pd.DataFrame) -> List[str]:
    preferred = [
        "dashboard_candidate_key",
        "place_id_std",
        "place_name_std",
        "dish_id_std",
        "dish_name_std",
        "district_id_std",
        "district_name_std",
        "neighborhood_id_std",
        "neighborhood_name_std",
        "latitude_std",
        "longitude_std",
        "coordinate_source_std",
        "score_std",
        "tier_std",
        "global_rank_std",
        "selected_rank_std",
        "selected_std",
        "mention_count_std",
        "review_count_std",
        "positive_ratio_std",
        "neutral_ratio_std",
        "negative_ratio_std",
        "weighted_sentiment_std",
        "evidence_tier_std",
        "quality_tier_std",
        "ready_for_ranking_std",
        "is_production_ready_std",
        "explanation_std",
    ]
    return [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]


# ---------------------------------------------------------------------------
# Aggregations
# ---------------------------------------------------------------------------


def sort_ranking(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "selected_rank_std" in out.columns and out["selected_rank_std"].notna().any():
        out = out.sort_values(["selected_rank_std", "global_rank_std", "score_std"], ascending=[True, True, False])
    elif "global_rank_std" in out.columns and out["global_rank_std"].notna().any():
        out = out.sort_values(["global_rank_std", "score_std"], ascending=[True, False])
    else:
        out = out.sort_values("score_std", ascending=False)
    return out.reset_index(drop=True)


def top_by_group(df: pd.DataFrame, group_col: str, top_n: int) -> pd.DataFrame:
    if group_col not in df.columns or df.empty:
        return pd.DataFrame()
    out = sort_ranking(df)
    out = out[~out[group_col].map(is_missing)].copy()
    if out.empty:
        return out
    out["rank_within_group"] = out.groupby(group_col).cumcount() + 1
    return out[out["rank_within_group"] <= top_n].reset_index(drop=True)


def summary_by_group(df: pd.DataFrame, group_cols: Sequence[str], label: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    missing = [c for c in group_cols if c not in df.columns]
    if missing:
        return pd.DataFrame()

    work = df.copy()
    for col in group_cols:
        work[col] = work[col].fillna("Unknown")

    grouped = work.groupby(list(group_cols), dropna=False)
    rows = []
    for key, group in grouped:
        if not isinstance(key, tuple):
            key = (key,)
        row = {col: value for col, value in zip(group_cols, key)}
        row.update({
            f"{label}_candidate_count": int(len(group)),
            "selected_places": int(group["place_id_std"].nunique(dropna=True)) if "place_id_std" in group.columns else None,
            "selected_dishes": int(group["dish_id_std"].nunique(dropna=True)) if "dish_id_std" in group.columns else None,
            "selected_neighborhoods": int(group["neighborhood_id_std"].nunique(dropna=True)) if "neighborhood_id_std" in group.columns else None,
            "total_mentions": int(pd.to_numeric(group.get("mention_count_std", 0), errors="coerce").fillna(0).sum()),
            "total_reviews": int(pd.to_numeric(group.get("review_count_std", 0), errors="coerce").fillna(0).sum()),
            "avg_score": round(float(pd.to_numeric(group["score_std"], errors="coerce").mean()), 6) if "score_std" in group.columns else None,
            "max_score": round(float(pd.to_numeric(group["score_std"], errors="coerce").max()), 6) if "score_std" in group.columns else None,
            "avg_positive_ratio": round(float(pd.to_numeric(group.get("positive_ratio_std", 0), errors="coerce").mean()), 6),
            "avg_negative_ratio": round(float(pd.to_numeric(group.get("negative_ratio_std", 0), errors="coerce").mean()), 6),
            "avg_latitude": round(float(pd.to_numeric(group.get("latitude_std", pd.Series(dtype=float)), errors="coerce").mean()), 8) if "latitude_std" in group.columns and pd.to_numeric(group.get("latitude_std"), errors="coerce").notna().any() else None,
            "avg_longitude": round(float(pd.to_numeric(group.get("longitude_std", pd.Series(dtype=float)), errors="coerce").mean()), 8) if "longitude_std" in group.columns and pd.to_numeric(group.get("longitude_std"), errors="coerce").notna().any() else None,
        })
        top = sort_ranking(group).head(1)
        if not top.empty:
            row.update({
                "top_place_name": top.iloc[0].get("place_name_std"),
                "top_dish_name": top.iloc[0].get("dish_name_std"),
                "top_score": safe_float(top.iloc[0].get("score_std")),
                "top_tier": top.iloc[0].get("tier_std"),
            })
        rows.append(row)
    out = pd.DataFrame(rows)
    if not out.empty and "max_score" in out.columns:
        out = out.sort_values(["max_score", f"{label}_candidate_count"], ascending=[False, False]).reset_index(drop=True)
    return out


def value_count_summary(df: pd.DataFrame, col: str, count_col_name: str = "count") -> pd.DataFrame:
    if df.empty or col not in df.columns:
        return pd.DataFrame(columns=[col, count_col_name])
    out = df[col].fillna("Unknown").astype(str).value_counts().reset_index()
    out.columns = [col, count_col_name]
    return out


def describe_series(series: pd.Series) -> Dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {"count": 0}
    desc = values.describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
    return {k: round(float(v), 6) for k, v in desc.items()}


# ---------------------------------------------------------------------------
# Mention examples
# ---------------------------------------------------------------------------


def normalize_mention_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    add_coalesced(out, "place_id_std", ["place_id", "place_id_v2"])
    add_coalesced(out, "place_name_std", ["place_name", "place_name_v2"])
    add_coalesced(out, "dish_id_std", ["dish_id_v2", "dish_id", "normalized_dish_id_v1", "current_dish_id"])
    add_coalesced(out, "dish_name_std", ["dish_display_name_v2", "dish_name", "canonical_dish_name", "normalized_dish_name", "current_dish_display_name"])
    add_coalesced(out, "mention_text_std", ["selected_mention_text_v2", "selected_mention_text", "mention_text", "dish_mention_text"])
    add_coalesced(out, "context_std", ["context_sentence", "target_clause_context", "window_context", "context_window"])
    add_coalesced(out, "review_text_std", ["review_text_raw", "review_text", "text"])
    add_coalesced(out, "sentiment_label_std", ["absa_sentiment_label_v1", "pred_label", "sentiment_label", "mention_sentiment_label_v1"])
    add_coalesced(out, "sentiment_confidence_std", ["absa_sentiment_confidence_v1", "pred_confidence", "sentiment_confidence"], None)
    add_coalesced(out, "absa_status_std", ["absa_status_v1", "sentiment_status_v1", "status"], None)
    add_coalesced(out, "normalization_status_std", ["normalization_status_v1", "normalization_status", "normalization_status_v2"], None)
    add_coalesced(out, "review_id_std", ["review_id"])
    add_coalesced(out, "rating_value_std", ["rating_value", "review_rating", "stars"])
    add_coalesced(out, "latitude_std", ["latitude_std", "latitude", "lat", "place_latitude", "place_lat", "location_latitude", "centroid_latitude", "y"])
    add_coalesced(out, "longitude_std", ["longitude_std", "longitude", "lon", "lng", "place_longitude", "place_lon", "place_lng", "location_longitude", "centroid_longitude", "x"])
    add_coalesced(out, "coordinate_source_std", ["coordinate_source_std", "coordinate_source", "geo_source"], None)

    out["sentiment_confidence_std"] = pd.to_numeric(out["sentiment_confidence_std"], errors="coerce")
    out["latitude_std"] = pd.to_numeric(out["latitude_std"], errors="coerce")
    out["longitude_std"] = pd.to_numeric(out["longitude_std"], errors="coerce")
    out.loc[~out["latitude_std"].between(-90, 90), "latitude_std"] = np.nan
    out.loc[~out["longitude_std"].between(-180, 180), "longitude_std"] = np.nan
    out["dashboard_candidate_key"] = (
        "place::"
        + out["place_id_std"].fillna("").astype(str)
        + "::dish::"
        + out["dish_id_std"].fillna(out["dish_name_std"]).fillna("").astype(str)
    )
    return out


def build_mention_examples(
    mentions: pd.DataFrame,
    selected: pd.DataFrame,
    examples_per_candidate: int,
    mention_candidates: int,
    include_full_review_text: bool,
) -> pd.DataFrame:
    if mentions.empty or selected.empty:
        return pd.DataFrame()

    mentions = normalize_mention_columns(mentions)
    selected_keys = sort_ranking(selected).head(mention_candidates)["dashboard_candidate_key"].dropna().astype(str).tolist()
    selected_key_set = set(selected_keys)

    work = mentions[mentions["dashboard_candidate_key"].isin(selected_key_set)].copy()
    if work.empty:
        return pd.DataFrame()

    work["sentiment_confidence_sort"] = pd.to_numeric(work["sentiment_confidence_std"], errors="coerce").fillna(0)
    work = work.sort_values(
        ["dashboard_candidate_key", "sentiment_label_std", "sentiment_confidence_sort"],
        ascending=[True, True, False],
    )
    work["example_rank_for_candidate"] = work.groupby("dashboard_candidate_key").cumcount() + 1
    out = work[work["example_rank_for_candidate"] <= examples_per_candidate].copy()

    selected_meta = selected[
        [
            "dashboard_candidate_key",
            "selected_rank_std",
            "score_std",
            "tier_std",
            "place_name_std",
            "dish_name_std",
            "district_name_std",
            "neighborhood_name_std",
            "latitude_std",
            "longitude_std",
            "coordinate_source_std",
        ]
    ].drop_duplicates("dashboard_candidate_key")
    out = out.merge(selected_meta, on="dashboard_candidate_key", how="left", suffixes=("", "_candidate"))

    keep_cols = [
        "dashboard_candidate_key",
        "selected_rank_std",
        "score_std",
        "tier_std",
        "place_id_std",
        "place_name_std",
        "dish_id_std",
        "dish_name_std",
        "district_name_std",
        "neighborhood_name_std",
        "latitude_std",
        "longitude_std",
        "coordinate_source_std",
        "review_id_std",
        "mention_text_std",
        "sentiment_label_std",
        "sentiment_confidence_std",
        "rating_value_std",
        "context_std",
        "absa_status_std",
        "normalization_status_std",
        "example_rank_for_candidate",
    ]
    if include_full_review_text:
        keep_cols.append("review_text_std")

    keep_cols = [c for c in keep_cols if c in out.columns]
    out = out[keep_cols].copy()
    out = out.sort_values(["selected_rank_std", "example_rank_for_candidate"], ascending=[True, True]).reset_index(drop=True)
    return out



# ---------------------------------------------------------------------------
# Coordinate enrichment
# ---------------------------------------------------------------------------


def auto_coordinate_reference_paths() -> List[Path]:
    """Default coordinate references, ordered by preference.

    The v1 dashboard export usually contains place coordinates because it was
    built directly from the database. IA v2 artifacts can lose those columns
    during model/ranking stages, so this export tries to recover them here.
    """
    return [
        Path("data/artifacts/ai/sevilla/dashboard/candidates_detail.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/candidates_all.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/top_global.csv"),
        Path("data/artifacts/ai/sevilla/dashboard/selected_candidates.csv"),
        Path("data/artifacts/ai/sevilla/dashboard_v1/candidates_detail.csv"),
        Path("data/artifacts/ai/sevilla/dashboard_v1/top_global.csv"),
    ]


def build_coordinate_reference_from_df(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    tmp = normalize_dashboard_columns(df.copy(), source=source_name)
    required = ["place_id_std", "place_name_std", "latitude_std", "longitude_std"]
    for col in required:
        if col not in tmp.columns:
            return pd.DataFrame()

    tmp = tmp[required + (["coordinate_source_std"] if "coordinate_source_std" in tmp.columns else [])].copy()
    tmp["latitude_std"] = pd.to_numeric(tmp["latitude_std"], errors="coerce")
    tmp["longitude_std"] = pd.to_numeric(tmp["longitude_std"], errors="coerce")
    tmp = tmp[
        tmp["latitude_std"].between(-90, 90)
        & tmp["longitude_std"].between(-180, 180)
    ].copy()
    if tmp.empty:
        return pd.DataFrame()

    tmp["coordinate_source_std"] = tmp.get("coordinate_source_std", pd.Series(index=tmp.index, dtype=object))
    tmp["coordinate_source_std"] = tmp["coordinate_source_std"].where(~tmp["coordinate_source_std"].map(is_missing), source_name)
    tmp["coordinate_priority"] = range(len(tmp))
    tmp = tmp.drop_duplicates(subset=["place_id_std"], keep="first")
    return tmp


def load_coordinate_reference(
    explicit_path: Optional[Path],
    auto_lookup: bool,
    ranking_raw: pd.DataFrame,
    selected_raw: pd.DataFrame,
    signals: pd.DataFrame,
    mentions: pd.DataFrame,
) -> pd.DataFrame:
    sources: List[Tuple[str, pd.DataFrame]] = [
        ("ranking_input", ranking_raw),
        ("selected_input", selected_raw),
        ("signals_input", signals),
        ("mentions_input", mentions),
    ]

    if explicit_path is not None:
        if explicit_path.exists():
            try:
                sources.append((f"coordinates_path:{explicit_path.name}", read_table(explicit_path, required=True)))
            except Exception as exc:
                print(f"Warning: could not read explicit coordinate path {explicit_path}: {exc}")
        else:
            print(f"Warning: explicit coordinate path does not exist: {explicit_path}")

    if auto_lookup:
        for path in auto_coordinate_reference_paths():
            if path.exists():
                try:
                    sources.append((f"auto:{path.as_posix()}", read_table(path, required=True)))
                    print(f"Coordinate reference candidate found: {path}")
                except Exception as exc:
                    print(f"Warning: could not read auto coordinate path {path}: {exc}")

    refs = []
    for source_name, frame in sources:
        ref = build_coordinate_reference_from_df(frame, source_name)
        if not ref.empty:
            refs.append(ref)

    if not refs:
        return pd.DataFrame(columns=["place_id_std", "place_name_std", "latitude_std", "longitude_std", "coordinate_source_std"])

    out = pd.concat(refs, ignore_index=True)
    out["place_id_std"] = out["place_id_std"].astype(str)
    out = out.drop_duplicates(subset=["place_id_std"], keep="first")
    return out[["place_id_std", "place_name_std", "latitude_std", "longitude_std", "coordinate_source_std"]].copy()


def enrich_with_coordinates(df: pd.DataFrame, coordinate_ref: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "latitude_std" not in out.columns:
        out["latitude_std"] = np.nan
    if "longitude_std" not in out.columns:
        out["longitude_std"] = np.nan
    if "coordinate_source_std" not in out.columns:
        out["coordinate_source_std"] = None

    out["latitude_std"] = pd.to_numeric(out["latitude_std"], errors="coerce")
    out["longitude_std"] = pd.to_numeric(out["longitude_std"], errors="coerce")
    out.loc[~out["latitude_std"].between(-90, 90), "latitude_std"] = np.nan
    out.loc[~out["longitude_std"].between(-180, 180), "longitude_std"] = np.nan

    if coordinate_ref is None or coordinate_ref.empty or "place_id_std" not in out.columns:
        return out

    ref = coordinate_ref.dropna(subset=["place_id_std", "latitude_std", "longitude_std"]).copy()
    ref["place_id_std"] = ref["place_id_std"].astype(str)
    out["place_id_std"] = out["place_id_std"].astype(str)

    merged = out.merge(
        ref[["place_id_std", "latitude_std", "longitude_std", "coordinate_source_std"]],
        on="place_id_std",
        how="left",
        suffixes=("", "__coord"),
    )

    missing_coords = merged["latitude_std"].isna() | merged["longitude_std"].isna()
    merged.loc[missing_coords, "latitude_std"] = merged.loc[missing_coords, "latitude_std__coord"]
    merged.loc[missing_coords, "longitude_std"] = merged.loc[missing_coords, "longitude_std__coord"]

    missing_source = merged["coordinate_source_std"].map(is_missing)
    merged.loc[missing_source, "coordinate_source_std"] = merged.loc[missing_source, "coordinate_source_std__coord"]

    drop_cols = [c for c in merged.columns if c.endswith("__coord")]
    merged = merged.drop(columns=drop_cols)
    return merged


def coordinate_coverage(df: pd.DataFrame) -> Dict[str, Any]:
    if df.empty or "latitude_std" not in df.columns or "longitude_std" not in df.columns:
        return {"rows": int(len(df)), "rows_with_coordinates": 0, "coverage_ratio": 0.0}
    has_coords = pd.to_numeric(df["latitude_std"], errors="coerce").notna() & pd.to_numeric(df["longitude_std"], errors="coerce").notna()
    total = int(len(df))
    count = int(has_coords.sum())
    return {
        "rows": total,
        "rows_with_coordinates": count,
        "coverage_ratio": round(count / total, 6) if total else 0.0,
    }

# ---------------------------------------------------------------------------
# Comparison export
# ---------------------------------------------------------------------------


def load_comparison_summary(comparison_dir: Optional[Path]) -> Dict[str, Any]:
    if comparison_dir is None or not comparison_dir.exists():
        return {}
    summary_path = comparison_dir / "sevilla_ranking_v1_vs_v2_summary.json"
    if not summary_path.exists():
        return {}
    with summary_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def copy_comparison_files(comparison_dir: Optional[Path], output_dir: Path) -> List[str]:
    copied: List[str] = []
    if comparison_dir is None or not comparison_dir.exists():
        return copied

    comparison_out = output_dir / "comparison"
    comparison_out.mkdir(parents=True, exist_ok=True)
    for name in [
        "sevilla_ranking_v1_vs_v2_summary.json",
        "ranking_overlap.csv",
        "v2_only_candidates.csv",
        "v1_only_candidates.csv",
        "score_shift_comparison.csv",
        "top_district_shift.csv",
        "top_neighborhood_shift.csv",
        "top_dish_shift.csv",
        "tier_shift_summary.csv",
    ]:
        src = comparison_dir / name
        if src.exists():
            dst = comparison_out / name
            shutil.copy2(src, dst)
            copied.append(str(dst.relative_to(output_dir)))
    return copied


# ---------------------------------------------------------------------------
# Dashboard metadata / contract
# ---------------------------------------------------------------------------


def build_filter_options(selected: pd.DataFrame, ranking: pd.DataFrame) -> Dict[str, Any]:
    data = selected if not selected.empty else ranking

    def unique_values(col: str) -> List[str]:
        if col not in data.columns:
            return []
        values = sorted([str(v) for v in data[col].dropna().unique() if str(v).strip()])
        return values

    neighborhoods = []
    if {"neighborhood_id_std", "neighborhood_name_std", "district_name_std"}.issubset(data.columns):
        tmp = data[["neighborhood_id_std", "neighborhood_name_std", "district_name_std"]].drop_duplicates()
        tmp = tmp.dropna(subset=["neighborhood_name_std"])
        neighborhoods = tmp.sort_values(["district_name_std", "neighborhood_name_std"]).to_dict(orient="records")

    return {
        "districts": unique_values("district_name_std"),
        "neighborhoods": neighborhoods,
        "dishes": unique_values("dish_name_std"),
        "places": unique_values("place_name_std"),
        "tiers": unique_values("tier_std"),
        "evidence_tiers": unique_values("evidence_tier_std"),
        "quality_tiers": unique_values("quality_tier_std"),
        "score_range": {
            "min": safe_float(pd.to_numeric(data.get("score_std", pd.Series(dtype=float)), errors="coerce").min(), 0.0),
            "max": safe_float(pd.to_numeric(data.get("score_std", pd.Series(dtype=float)), errors="coerce").max(), 100.0),
        },
    }


def build_data_contract(include_mentions: bool, include_comparison: bool) -> Dict[str, Any]:
    files = {
        "dashboard_metadata.json": "Run metadata and source artifact paths.",
        "kpi_summary.json": "Main dashboard KPIs for Ranking IA v2.",
        "ranking_detail.csv": "All scored ranking rows with stable dashboard columns.",
        "selected_candidates.csv": "Selected Hidden Gem candidates only.",
        "top_global.csv": "Top selected candidates ordered by selected/global rank.",
        "top_by_district.csv": "Top selected candidates per district.",
        "top_by_neighborhood.csv": "Top selected candidates per neighborhood.",
        "top_by_dish.csv": "Top selected candidates per dish.",
        "district_summary.csv": "Aggregated candidate metrics by district.",
        "neighborhood_summary.csv": "Aggregated candidate metrics by neighborhood.",
        "dish_summary.csv": "Aggregated candidate metrics by dish.",
        "place_summary.csv": "Aggregated candidate metrics by place.",
        "tier_summary.csv": "Selected candidate counts by Hidden Gem tier.",
        "evidence_summary.csv": "Selected candidate counts by evidence tier.",
        "quality_summary.csv": "Selected candidate counts by aggregate quality tier.",
        "place_coordinates.csv": "Place-level coordinate reference used by map visualizations.",
        "filter_options.json": "Values intended for dashboard filters.",
        "data_contract.json": "This data contract.",
        "dashboard_export_summary.json": "Export summary, checks and warnings.",
    }
    if include_mentions:
        files["mention_examples.csv"] = "Optional review/context examples for selected place-dish candidates."
    if include_comparison:
        files["comparison/"] = "Copied v1 vs v2 comparison artifacts."

    return {
        "version": VERSION,
        "grain": {
            "ranking_detail.csv": "one row per place-dish signal/candidate",
            "selected_candidates.csv": "one row per selected place-dish candidate",
            "mention_examples.csv": "zero-to-many mention/review examples per selected candidate",
        },
        "core_columns": {
            "dashboard_candidate_key": "Stable key built from place_id and dish_id/name.",
            "place_id_std": "Canonical place identifier.",
            "place_name_std": "Display place name.",
            "dish_id_std": "Canonical dish identifier when available.",
            "dish_name_std": "Display dish name.",
            "district_name_std": "District name.",
            "neighborhood_name_std": "Neighborhood name.",
            "latitude_std": "Place latitude, enriched from IA v2 artifacts or coordinate reference when available.",
            "longitude_std": "Place longitude, enriched from IA v2 artifacts or coordinate reference when available.",
            "coordinate_source_std": "Source artifact used to populate coordinates.",
            "score_std": "Hidden Gem score v2, normalized to 0-100.",
            "tier_std": "Hidden Gem tier v2.",
            "mention_count_std": "Number of mentions behind the signal.",
            "review_count_std": "Number of reviews behind the signal.",
            "positive_ratio_std": "Share of positive ABSA mentions.",
            "negative_ratio_std": "Share of negative ABSA mentions.",
            "evidence_tier_std": "Evidence strength tier.",
            "quality_tier_std": "Aggregate quality tier.",
            "explanation_std": "Human-readable ranking explanation when available.",
        },
        "files": files,
        "notes": [
            "Ranking IA v2 is experimental and should be presented as model-assisted, not production-ready.",
            "Scores are comparable within v2, but not directly equivalent to v1 scores because the formula changed.",
            "Dashboard should expose evidence_tier and quality_tier to avoid overclaiming weak signals.",
            "If latitude_std/longitude_std are present, they represent place-level coordinates suitable for map visualizations.",
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export dashboard datasets for Hidden Gems Sevilla Ranking IA v2.")
    parser.add_argument("--ranking-path", type=Path, required=True, help="Path to sevilla_hidden_gems_ranking_v2 csv/jsonl.")
    parser.add_argument("--selected-path", type=Path, default=None, help="Optional path to sevilla_hidden_gems_selected_v2 csv/jsonl.")
    parser.add_argument("--signals-path", type=Path, default=None, help="Optional path to place-dish signals v2.")
    parser.add_argument("--mentions-path", type=Path, default=None, help="Optional path to ABSA mention output jsonl/csv.")
    parser.add_argument("--comparison-dir", type=Path, default=None, help="Optional ranking_v2_comparison directory.")
    parser.add_argument("--coordinates-path", type=Path, default=None, help="Optional table with place coordinates. If omitted, the script tries v1 dashboard artifacts automatically.")
    parser.add_argument("--no-auto-coordinate-lookup", action="store_true", help="Disable automatic coordinate lookup from v1 dashboard artifacts.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Output directory for dashboard export.")
    parser.add_argument("--expected-selected", type=int, default=None, help="Optional expected selected candidate count.")
    parser.add_argument("--top-global-limit", type=int, default=300, help="Rows for top_global.csv.")
    parser.add_argument("--top-per-group", type=int, default=10, help="Rows per group for top_by_*.csv.")
    parser.add_argument("--include-mentions", action="store_true", help="Generate mention_examples.csv if mentions path is provided.")
    parser.add_argument("--mention-candidates", type=int, default=150, help="How many selected candidates should receive examples.")
    parser.add_argument("--examples-per-candidate", type=int, default=5, help="Max mention examples per selected candidate.")
    parser.add_argument("--include-full-review-text", action="store_true", help="Include full review text in mention_examples.csv if available.")
    parser.add_argument("--strict", action="store_true", help="Fail on critical checks.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    generated_at = datetime.now(timezone.utc).isoformat()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Patch: {PATCH_ID}")
    print("Loading ranking v2...")
    ranking_raw = read_table(args.ranking_path, required=True)
    print(f"Ranking rows: {len(ranking_raw)}")

    ranking = normalize_dashboard_columns(ranking_raw, source="ranking_v2")
    ranking = sort_ranking(ranking)

    selected_raw = pd.DataFrame()
    if args.selected_path and args.selected_path.exists():
        print("Loading selected v2...")
        selected_raw = read_table(args.selected_path, required=True)
        selected = normalize_dashboard_columns(selected_raw, source="selected_v2")
        selected["selected_std"] = True
    else:
        print("Selected path not provided/found. Deriving selected rows from ranking...")
        selected = ranking[ranking["selected_std"] == True].copy()
        if selected.empty and "tier_std" in ranking.columns:
            selected = ranking[ranking["tier_std"].fillna("not_selected") != "not_selected"].copy()
    selected = sort_ranking(selected)
    print(f"Selected rows: {len(selected)}")

    # Optional load for metadata/enrichment. Dashboard export primarily uses ranking/selected.
    signals = read_table(args.signals_path, required=False) if args.signals_path else pd.DataFrame()
    if not signals.empty:
        print(f"Signals rows: {len(signals)}")

    mentions_raw = read_table(args.mentions_path, required=False) if args.mentions_path else pd.DataFrame()
    if not mentions_raw.empty:
        print(f"Mentions rows: {len(mentions_raw)}")

    print("Loading/enriching place coordinates...")
    coordinate_ref = load_coordinate_reference(
        explicit_path=args.coordinates_path,
        auto_lookup=not args.no_auto_coordinate_lookup,
        ranking_raw=ranking_raw,
        selected_raw=selected_raw,
        signals=signals,
        mentions=mentions_raw,
    )
    print(f"Coordinate reference places: {len(coordinate_ref)}")
    ranking = enrich_with_coordinates(ranking, coordinate_ref)
    selected = enrich_with_coordinates(selected, coordinate_ref)

    comparison_summary = load_comparison_summary(args.comparison_dir)
    copied_comparison_files = copy_comparison_files(args.comparison_dir, output_dir)

    print("Building dashboard datasets...")
    ranking_detail = ranking[preferred_dashboard_columns(ranking)].copy()
    selected_candidates = selected[preferred_dashboard_columns(selected)].copy()
    top_global = sort_ranking(selected).head(args.top_global_limit).copy()

    top_by_district = top_by_group(selected, "district_name_std", args.top_per_group)
    top_by_neighborhood = top_by_group(selected, "neighborhood_name_std", args.top_per_group)
    top_by_dish = top_by_group(selected, "dish_name_std", args.top_per_group)

    district_summary = summary_by_group(selected, ["district_id_std", "district_name_std"], "district")
    neighborhood_summary = summary_by_group(
        selected,
        ["district_id_std", "district_name_std", "neighborhood_id_std", "neighborhood_name_std"],
        "neighborhood",
    )
    dish_summary = summary_by_group(selected, ["dish_id_std", "dish_name_std"], "dish")
    place_summary = summary_by_group(selected, ["place_id_std", "place_name_std", "district_name_std", "neighborhood_name_std"], "place")

    tier_summary = value_count_summary(selected, "tier_std", "selected_count")
    evidence_summary = value_count_summary(selected, "evidence_tier_std", "selected_count")
    quality_summary = value_count_summary(selected, "quality_tier_std", "selected_count")

    mention_examples = pd.DataFrame()
    if args.include_mentions:
        if not mentions_raw.empty:
            print("Building mention examples...")
            mention_examples = build_mention_examples(
                mentions=mentions_raw,
                selected=selected,
                examples_per_candidate=args.examples_per_candidate,
                mention_candidates=args.mention_candidates,
                include_full_review_text=args.include_full_review_text,
            )
            print(f"Mention examples rows: {len(mention_examples)}")
        else:
            print("Mention examples requested but mentions path was not found. Skipping.")

    # KPIs.
    selected_score = pd.to_numeric(selected.get("score_std", pd.Series(dtype=float)), errors="coerce")
    kpis = {
        "total_candidates_scored_v2": int(len(ranking)),
        "selected_candidates_v2": int(len(selected)),
        "selected_places_v2": int(selected["place_id_std"].nunique(dropna=True)) if "place_id_std" in selected.columns else 0,
        "selected_dishes_v2": int(selected["dish_id_std"].nunique(dropna=True)) if "dish_id_std" in selected.columns else 0,
        "selected_neighborhoods_v2": int(selected["neighborhood_id_std"].nunique(dropna=True)) if "neighborhood_id_std" in selected.columns else 0,
        "selected_districts_v2": int(selected["district_id_std"].nunique(dropna=True)) if "district_id_std" in selected.columns else 0,
        "selected_candidates_with_coordinates_v2": coordinate_coverage(selected)["rows_with_coordinates"],
        "selected_coordinate_coverage_ratio_v2": coordinate_coverage(selected)["coverage_ratio"],
        "ranking_candidates_with_coordinates_v2": coordinate_coverage(ranking)["rows_with_coordinates"],
        "ranking_coordinate_coverage_ratio_v2": coordinate_coverage(ranking)["coverage_ratio"],
        "top_hidden_gem_count_v2": int((selected["tier_std"] == "top_hidden_gem").sum()) if "tier_std" in selected.columns else 0,
        "strong_hidden_gem_count_v2": int((selected["tier_std"] == "strong_hidden_gem").sum()) if "tier_std" in selected.columns else 0,
        "promising_hidden_gem_count_v2": int((selected["tier_std"] == "promising_hidden_gem").sum()) if "tier_std" in selected.columns else 0,
        "exploratory_hidden_gem_count_v2": int((selected["tier_std"] == "exploratory_hidden_gem").sum()) if "tier_std" in selected.columns else 0,
        "avg_score_selected_v2": round(float(selected_score.mean()), 6) if selected_score.notna().any() else None,
        "max_score_selected_v2": round(float(selected_score.max()), 6) if selected_score.notna().any() else None,
        "min_score_selected_v2": round(float(selected_score.min()), 6) if selected_score.notna().any() else None,
        "total_mentions_selected_v2": int(pd.to_numeric(selected.get("mention_count_std", 0), errors="coerce").fillna(0).sum()),
        "total_reviews_selected_v2": int(pd.to_numeric(selected.get("review_count_std", 0), errors="coerce").fillna(0).sum()),
        "production_ready_count_v2": int(selected.get("is_production_ready_std", pd.Series(dtype=bool)).map(lambda x: safe_bool(x, False)).sum()) if "is_production_ready_std" in selected.columns else 0,
    }

    if comparison_summary:
        kpis["comparison"] = {
            "v1_selected_unique": comparison_summary.get("counts", {}).get("v1_selected_unique"),
            "v2_selected_unique": comparison_summary.get("counts", {}).get("v2_selected_unique"),
            "matched_candidates": comparison_summary.get("counts", {}).get("matched_candidates"),
            "v1_coverage_in_v2": comparison_summary.get("quality", {}).get("v1_coverage_in_v2"),
            "jaccard_overlap": comparison_summary.get("quality", {}).get("jaccard_overlap"),
            "selected_places_delta_v2_minus_v1": comparison_summary.get("diversity_delta", {}).get("selected_places", {}).get("delta_v2_minus_v1"),
            "selected_neighborhoods_delta_v2_minus_v1": comparison_summary.get("diversity_delta", {}).get("selected_neighborhoods", {}).get("delta_v2_minus_v1"),
        }

    checks = {
        "has_ranking": bool(len(ranking) > 0),
        "has_selected_candidates": bool(len(selected) > 0),
        "expected_selected_matches": True if args.expected_selected is None else int(len(selected)) == int(args.expected_selected),
        "score_in_0_100": bool(pd.to_numeric(ranking.get("score_std", pd.Series(dtype=float)), errors="coerce").dropna().between(0, 100).all()),
        "selected_have_place": bool(selected["place_id_std"].notna().all()) if "place_id_std" in selected.columns and len(selected) else False,
        "selected_have_dish": bool((selected["dish_id_std"].notna() | selected["dish_name_std"].notna()).all()) if len(selected) else False,
        "selected_have_neighborhood": bool(selected["neighborhood_name_std"].notna().all()) if "neighborhood_name_std" in selected.columns and len(selected) else False,
        "selected_have_district": bool(selected["district_name_std"].notna().all()) if "district_name_std" in selected.columns and len(selected) else False,
        "selected_have_coordinates": bool((pd.to_numeric(selected.get("latitude_std", pd.Series(dtype=float)), errors="coerce").notna() & pd.to_numeric(selected.get("longitude_std", pd.Series(dtype=float)), errors="coerce").notna()).all()) if len(selected) else False,
        "ranking_has_any_coordinates": bool((pd.to_numeric(ranking.get("latitude_std", pd.Series(dtype=float)), errors="coerce").notna() & pd.to_numeric(ranking.get("longitude_std", pd.Series(dtype=float)), errors="coerce").notna()).any()) if len(ranking) else False,
        "selected_ranks_are_unique": bool(selected["selected_rank_std"].dropna().is_unique) if "selected_rank_std" in selected.columns else True,
        "all_selected_are_not_production_ready": bool((selected.get("is_production_ready_std", pd.Series(False, index=selected.index)).map(lambda x: safe_bool(x, False)) == False).all()) if len(selected) else True,
        "comparison_loaded": bool(comparison_summary),
    }

    warnings: List[str] = []
    if not checks["expected_selected_matches"]:
        warnings.append(f"Expected selected={args.expected_selected}, found selected={len(selected)}.")
    if kpis["production_ready_count_v2"] == 0:
        warnings.append("Ranking IA v2 has zero production-ready rows; present it as experimental/model-assisted.")
    if comparison_summary:
        v2_coverage = comparison_summary.get("quality", {}).get("v2_coverage_in_v1")
        if isinstance(v2_coverage, (int, float)) and v2_coverage < 0.5:
            warnings.append("V2 expands strongly beyond v1; dashboard should explain v2-only candidates and evidence tiers.")
    if int(kpis.get("exploratory_hidden_gem_count_v2", 0)) > 0:
        warnings.append("Selected candidates include exploratory tier rows; expose tier filters in dashboard.")
    if not checks.get("ranking_has_any_coordinates"):
        warnings.append("No coordinates were found in IA v2 artifacts or coordinate references; map visualizations will need fallback centroids.")
    elif not checks.get("selected_have_coordinates"):
        warnings.append("Some selected candidates are missing coordinates; map visualizations may be partially incomplete.")

    strict_failures = [
        name
        for name, ok in checks.items()
        if name not in {
            "comparison_loaded",
            "all_selected_are_not_production_ready",
            "selected_have_coordinates",
            "ranking_has_any_coordinates",
        }
        and not ok
    ]
    if args.strict and strict_failures:
        raise RuntimeError(f"Strict mode failed checks: {strict_failures}")

    print("Writing outputs...")
    outputs: Dict[str, Path] = {
        "dashboard_metadata.json": output_dir / "dashboard_metadata.json",
        "kpi_summary.json": output_dir / "kpi_summary.json",
        "ranking_detail.csv": output_dir / "ranking_detail.csv",
        "selected_candidates.csv": output_dir / "selected_candidates.csv",
        "top_global.csv": output_dir / "top_global.csv",
        "top_by_district.csv": output_dir / "top_by_district.csv",
        "top_by_neighborhood.csv": output_dir / "top_by_neighborhood.csv",
        "top_by_dish.csv": output_dir / "top_by_dish.csv",
        "district_summary.csv": output_dir / "district_summary.csv",
        "neighborhood_summary.csv": output_dir / "neighborhood_summary.csv",
        "dish_summary.csv": output_dir / "dish_summary.csv",
        "place_summary.csv": output_dir / "place_summary.csv",
        "tier_summary.csv": output_dir / "tier_summary.csv",
        "evidence_summary.csv": output_dir / "evidence_summary.csv",
        "quality_summary.csv": output_dir / "quality_summary.csv",
        "place_coordinates.csv": output_dir / "place_coordinates.csv",
        "filter_options.json": output_dir / "filter_options.json",
        "data_contract.json": output_dir / "data_contract.json",
        "dashboard_export_summary.json": output_dir / "dashboard_export_summary.json",
    }
    if args.include_mentions:
        outputs["mention_examples.csv"] = output_dir / "mention_examples.csv"

    write_df(ranking_detail, outputs["ranking_detail.csv"])
    write_df(selected_candidates, outputs["selected_candidates.csv"])
    write_df(top_global, outputs["top_global.csv"])
    write_df(top_by_district, outputs["top_by_district.csv"])
    write_df(top_by_neighborhood, outputs["top_by_neighborhood.csv"])
    write_df(top_by_dish, outputs["top_by_dish.csv"])
    write_df(district_summary, outputs["district_summary.csv"])
    write_df(neighborhood_summary, outputs["neighborhood_summary.csv"])
    write_df(dish_summary, outputs["dish_summary.csv"])
    write_df(place_summary, outputs["place_summary.csv"])
    write_df(tier_summary, outputs["tier_summary.csv"])
    write_df(evidence_summary, outputs["evidence_summary.csv"])
    write_df(quality_summary, outputs["quality_summary.csv"])
    write_df(coordinate_ref, outputs["place_coordinates.csv"])
    if args.include_mentions:
        write_df(mention_examples, outputs["mention_examples.csv"])

    metadata = {
        "script": SCRIPT_NAME,
        "patch_id": PATCH_ID,
        "version": VERSION,
        "generated_at": generated_at,
        "inputs": {
            "ranking_path": str(args.ranking_path),
            "selected_path": str(args.selected_path) if args.selected_path else None,
            "signals_path": str(args.signals_path) if args.signals_path else None,
            "mentions_path": str(args.mentions_path) if args.mentions_path else None,
            "comparison_dir": str(args.comparison_dir) if args.comparison_dir else None,
            "coordinates_path": str(args.coordinates_path) if args.coordinates_path else None,
            "auto_coordinate_lookup": not args.no_auto_coordinate_lookup,
            "output_dir": str(output_dir),
        },
        "parameters": {
            "expected_selected": args.expected_selected,
            "top_global_limit": args.top_global_limit,
            "top_per_group": args.top_per_group,
            "include_mentions": args.include_mentions,
            "mention_candidates": args.mention_candidates,
            "examples_per_candidate": args.examples_per_candidate,
            "include_full_review_text": args.include_full_review_text,
            "strict": args.strict,
        },
    }

    filter_options = build_filter_options(selected, ranking)
    data_contract = build_data_contract(include_mentions=args.include_mentions, include_comparison=bool(copied_comparison_files))

    summary = {
        "script": SCRIPT_NAME,
        "patch_id": PATCH_ID,
        "version": VERSION,
        "generated_at": generated_at,
        "output_dir": str(output_dir),
        "counts": {
            "ranking_rows": int(len(ranking)),
            "selected_rows": int(len(selected)),
            "signals_rows_loaded": int(len(signals)),
            "top_global_rows": int(len(top_global)),
            "top_by_district_rows": int(len(top_by_district)),
            "top_by_neighborhood_rows": int(len(top_by_neighborhood)),
            "top_by_dish_rows": int(len(top_by_dish)),
            "district_summary_rows": int(len(district_summary)),
            "neighborhood_summary_rows": int(len(neighborhood_summary)),
            "dish_summary_rows": int(len(dish_summary)),
            "place_summary_rows": int(len(place_summary)),
            "mention_examples_rows": int(len(mention_examples)),
            "comparison_files_copied": int(len(copied_comparison_files)),
            "coordinate_reference_places": int(len(coordinate_ref)),
            "selected_rows_with_coordinates": coordinate_coverage(selected)["rows_with_coordinates"],
            "ranking_rows_with_coordinates": coordinate_coverage(ranking)["rows_with_coordinates"],
        },
        "kpis": kpis,
        "score_summary_selected": describe_series(selected.get("score_std", pd.Series(dtype=float))),
        "tier_counts": selected.get("tier_std", pd.Series(dtype=str)).fillna("Unknown").value_counts().to_dict() if len(selected) else {},
        "evidence_tier_counts": selected.get("evidence_tier_std", pd.Series(dtype=str)).fillna("Unknown").value_counts().to_dict() if len(selected) else {},
        "quality_tier_counts": selected.get("quality_tier_std", pd.Series(dtype=str)).fillna("Unknown").value_counts().to_dict() if len(selected) else {},
        "comparison_snapshot": kpis.get("comparison", {}),
        "checks": checks,
        "warnings": warnings,
        "files": sorted([str(path.relative_to(output_dir)) for path in outputs.values()] + copied_comparison_files),
    }

    write_json(outputs["dashboard_metadata.json"], metadata)
    write_json(outputs["kpi_summary.json"], kpis)
    write_json(outputs["filter_options.json"], filter_options)
    write_json(outputs["data_contract.json"], data_contract)
    write_json(outputs["dashboard_export_summary.json"], summary)

    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, default=json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
