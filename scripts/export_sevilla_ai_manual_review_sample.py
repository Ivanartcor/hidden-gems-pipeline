"""Export a manual review sample for the Sevilla Hidden Gems AI pilot.

This script creates a reviewable CSV/JSONL sample from the Sevilla pilot ranking
already loaded in PostgreSQL. It is intended to support the next IA improvement
phase: manual audit, error taxonomy and v2 improvement planning.

It does not modify the database.

Recommended execution from repository root:

    python -m scripts.export_sevilla_ai_manual_review_sample `
      --output-dir data/artifacts/ai/sevilla/evaluation `
      --promising-sample 30 `
      --exploratory-sample 30 `
      --not-selected-sample 30 `
      --include-mentions `
      --examples-per-candidate 3 `
      --strict

If you want full review text for deeper manual inspection:

    python -m scripts.export_sevilla_ai_manual_review_sample `
      --output-dir data/artifacts/ai/sevilla/evaluation `
      --include-mentions `
      --include-full-review-text `
      --strict

Important:
- If --include-full-review-text is used, do not commit the mentions CSV to Git.
- The output is an evaluation artifact, not a production ranking.
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

import numpy as np
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
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/evaluation")
DEFAULT_SAMPLE_NAME = "sevilla_ai_manual_review_sample_v1"

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

MANUAL_COLUMNS = [
    "manual_decision",
    "manual_error_type",
    "manual_dish_is_correct",
    "manual_place_dish_association_is_correct",
    "manual_sentiment_is_correct",
    "manual_evidence_is_sufficient",
    "manual_ranking_position_is_reasonable",
    "manual_corrected_dish_name",
    "manual_should_keep_for_v2",
    "manual_notes",
    "reviewer_name",
    "reviewed_at",
]

MANUAL_DECISION_OPTIONS = [
    "correct",
    "doubtful",
    "false_positive",
    "should_rank_higher",
    "should_rank_lower",
    "needs_more_evidence",
]

ERROR_TYPE_OPTIONS = [
    "none",
    "dish_detection_error",
    "dish_normalization_error",
    "sentiment_error",
    "evidence_too_weak",
    "generic_dish_too_broad",
    "ranking_score_issue",
    "place_duplicate_or_wrong_place",
    "review_context_not_about_dish",
    "other",
]

GENERIC_DISH_TERMS = {
    "comida",
    "food",
    "plato",
    "menu",
    "menú",
    "tapa",
    "tapas",
    "pizza",
    "burger",
    "hamburguesa",
    "sandwich",
    "bocadillo",
    "pasta",
    "carne",
    "pescado",
    "postre",
    "dessert",
    "breakfast",
    "desayuno",
    "cafe",
    "café",
}

PREFERRED_COLUMNS = [
    "manual_review_priority",
    "manual_review_reason",
    "suggested_review_focus",
    "hidden_gem_candidate_id",
    "hidden_gem_selected_rank",
    "hidden_gem_rank",
    "hidden_gem_tier",
    "is_selected",
    "is_production_ready",
    "hidden_gem_score",
    "place_id",
    "place_name",
    "address_text",
    "district_id",
    "district_name",
    "neighborhood_id",
    "neighborhood_name",
    "latitude",
    "longitude",
    "dish_id",
    "dish_name",
    "dish_display_name",
    "dish_normalized_name",
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
    "evidence_tier",
    "aggregate_quality_tier",
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
    "low_evidence_flag",
    "low_confidence_flag",
    "negative_signal_flag",
    "generic_dish_flag",
    "possible_overranking_flag",
    "possible_underranking_flag",
    "ranking_explanation",
    "ranking_version",
    "ranking_scope",
    "artifact_ranking_scope",
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


def validate_uuid_or_empty(value: str | None, label: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    if not UUID_RE.match(value):
        raise ValueError(f"{label} must be a valid UUID. Received: {value!r}")
    return value


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


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def save_json(data: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def save_jsonl(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for record in df.to_dict(orient="records"):
            f.write(json.dumps(to_builtin(record), ensure_ascii=False, allow_nan=False) + "\n")


def save_csv(df: pd.DataFrame, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8")


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


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------


def load_candidate_detail(args: argparse.Namespace) -> pd.DataFrame:
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
            mention_count DESC,
            review_count DESC,
            place_name,
            dish_display_name;
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

    return df


# -----------------------------------------------------------------------------
# Sampling logic
# -----------------------------------------------------------------------------


def systematic_sample(df: pd.DataFrame, n: int, score_col: str = "hidden_gem_score") -> pd.DataFrame:
    """Deterministic sample across the full score range, not only the top rows."""
    if df.empty or n <= 0:
        return df.head(0).copy()
    if len(df) <= n:
        return df.copy()

    ordered = df.sort_values(score_col, ascending=False, na_position="last").reset_index(drop=True)
    indices = np.linspace(0, len(ordered) - 1, num=n, dtype=int)
    return ordered.iloc[sorted(set(indices))].copy()


def random_sample(df: pd.DataFrame, n: int, random_state: int) -> pd.DataFrame:
    if df.empty or n <= 0:
        return df.head(0).copy()
    if len(df) <= n:
        return df.copy()
    return df.sample(n=n, random_state=random_state).copy()


def build_manual_review_sample(args: argparse.Namespace, candidates_df: pd.DataFrame) -> pd.DataFrame:
    if candidates_df.empty:
        return candidates_df.copy()

    frames: list[pd.DataFrame] = []

    def add_frame(df: pd.DataFrame, priority: str, reason: str) -> None:
        if df.empty:
            return
        out = df.copy()
        out["manual_review_priority"] = priority
        out["manual_review_reason"] = reason
        frames.append(out)

    top_strong = candidates_df[
        candidates_df["hidden_gem_tier"].isin(["top_hidden_gem", "strong_hidden_gem"])
    ].copy()
    add_frame(
        top_strong,
        "mandatory_top_strong",
        "Todos los candidatos top_hidden_gem y strong_hidden_gem deben revisarse manualmente.",
    )

    promising = candidates_df[candidates_df["hidden_gem_tier"] == "promising_hidden_gem"].copy()
    if args.sample_method == "random":
        promising_sample = random_sample(promising, args.promising_sample, args.random_state)
    else:
        promising_sample = systematic_sample(promising, args.promising_sample)
    add_frame(
        promising_sample,
        "sample_promising",
        "Muestra de candidatos promising para estimar precisión en el rango medio-alto.",
    )

    exploratory = candidates_df[candidates_df["hidden_gem_tier"] == "exploratory_hidden_gem"].copy()
    if args.sample_method == "random":
        exploratory_sample = random_sample(exploratory, args.exploratory_sample, args.random_state + 1)
    else:
        exploratory_sample = systematic_sample(exploratory, args.exploratory_sample)
    add_frame(
        exploratory_sample,
        "sample_exploratory",
        "Muestra de candidatos exploratory para revisar ruido, evidencia débil y falsos positivos.",
    )

    not_selected = candidates_df[candidates_df["hidden_gem_tier"] == "not_selected"].copy()
    if args.not_selected_strategy == "random":
        not_selected_sample = random_sample(not_selected, args.not_selected_sample, args.random_state + 2)
        not_selected_reason = "Muestra aleatoria de candidatos no seleccionados."
    else:
        not_selected_sample = not_selected.sort_values(
            ["hidden_gem_score", "mention_count", "review_count"],
            ascending=[False, False, False],
            na_position="last",
        ).head(args.not_selected_sample)
        not_selected_reason = "Candidatos no seleccionados cercanos al umbral para detectar posibles falsos negativos."
    add_frame(not_selected_sample, "sample_not_selected", not_selected_reason)

    if not frames:
        return candidates_df.head(0).copy()

    sample_df = pd.concat(frames, ignore_index=True)
    if "hidden_gem_candidate_id" in sample_df.columns:
        sample_df = sample_df.drop_duplicates(subset=["hidden_gem_candidate_id"], keep="first")

    sample_df = enrich_review_flags(sample_df)
    sample_df = add_manual_review_columns(sample_df)
    sample_df = reorder_columns(sample_df)
    return sample_df.reset_index(drop=True)


def enrich_review_flags(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    mention_count = pd.to_numeric(out.get("mention_count", pd.Series(dtype=float)), errors="coerce").fillna(0)
    review_count = pd.to_numeric(out.get("review_count", pd.Series(dtype=float)), errors="coerce").fillna(0)
    confidence = pd.to_numeric(out.get("avg_sentiment_confidence", pd.Series(dtype=float)), errors="coerce").fillna(0)
    negative_ratio = pd.to_numeric(out.get("negative_ratio", pd.Series(dtype=float)), errors="coerce").fillna(0)
    score = pd.to_numeric(out.get("hidden_gem_score", pd.Series(dtype=float)), errors="coerce").fillna(0)

    dish_col = "dish_display_name" if "dish_display_name" in out.columns else "dish_name"
    dish_values = out.get(dish_col, pd.Series(dtype=str)).fillna("").astype(str).str.lower().str.strip()

    out["low_evidence_flag"] = (mention_count < 3) | (review_count < 2)
    out["low_confidence_flag"] = confidence < 0.55
    out["negative_signal_flag"] = negative_ratio >= 0.25
    out["generic_dish_flag"] = dish_values.isin(GENERIC_DISH_TERMS)
    out["possible_overranking_flag"] = (score >= 70) & (out["low_evidence_flag"] | out["low_confidence_flag"])
    out["possible_underranking_flag"] = (score < 60) & (mention_count >= 3) & (confidence >= 0.60) & (negative_ratio < 0.20)

    focus_parts: list[str] = []
    for _, row in out.iterrows():
        parts: list[str] = []
        if bool(row.get("low_evidence_flag", False)):
            parts.append("revisar evidencia baja")
        if bool(row.get("low_confidence_flag", False)):
            parts.append("revisar confianza de sentimiento")
        if bool(row.get("negative_signal_flag", False)):
            parts.append("revisar señales negativas")
        if bool(row.get("generic_dish_flag", False)):
            parts.append("revisar plato genérico")
        if bool(row.get("possible_overranking_flag", False)):
            parts.append("posible sobre-ranking")
        if bool(row.get("possible_underranking_flag", False)):
            parts.append("posible infra-ranking")
        if not parts:
            parts.append("revisión general")
        focus_parts.append("; ".join(parts))

    out["suggested_review_focus"] = focus_parts
    return out


def add_manual_review_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in MANUAL_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    return out


def reorder_columns(df: pd.DataFrame) -> pd.DataFrame:
    existing_preferred = [c for c in PREFERRED_COLUMNS if c in df.columns]
    existing_manual = [c for c in MANUAL_COLUMNS if c in df.columns]
    remaining = [c for c in df.columns if c not in existing_preferred and c not in existing_manual]
    return df[existing_preferred + existing_manual + remaining]


# -----------------------------------------------------------------------------
# Mention examples
# -----------------------------------------------------------------------------


def load_mentions_for_sample(
    schema: str,
    sample_df: pd.DataFrame,
    examples_per_candidate: int,
    include_full_review_text: bool,
) -> pd.DataFrame:
    if sample_df.empty:
        return pd.DataFrame()

    schema = validate_schema_name(schema)
    view_name = qname(schema, "vw_ai_dish_mentions_with_sentiment")

    select_review_text = "review_text_raw" if include_full_review_text else "LEFT(review_text_raw, 350) AS review_text_preview"

    sql = f"""
        SELECT
            CAST(:hidden_gem_candidate_id AS text) AS hidden_gem_candidate_id,
            CAST(:manual_review_priority AS text) AS manual_review_priority,
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
            {select_review_text}
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
    for _, row in sample_df.iterrows():
        place_id = str(row.get("place_id", ""))
        dish_id = str(row.get("dish_id", ""))
        candidate_id = str(row.get("hidden_gem_candidate_id", ""))
        priority = str(row.get("manual_review_priority", ""))

        if not UUID_RE.match(place_id) or not UUID_RE.match(dish_id):
            continue

        df = read_df(
            sql,
            {
                "hidden_gem_candidate_id": candidate_id,
                "manual_review_priority": priority,
                "place_id": place_id,
                "dish_id": dish_id,
                "limit": examples_per_candidate,
            },
        )
        if not df.empty:
            frames.append(df)

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


# -----------------------------------------------------------------------------
# Summary and outputs
# -----------------------------------------------------------------------------


def build_summary(
    args: argparse.Namespace,
    candidates_df: pd.DataFrame,
    sample_df: pd.DataFrame,
    mentions_df: pd.DataFrame,
    output_files: list[str],
) -> dict[str, Any]:
    selected_df = candidates_df[candidates_df.get("is_selected", pd.Series(dtype=bool))].copy()

    sample_by_priority = (
        sample_df["manual_review_priority"].value_counts().to_dict()
        if "manual_review_priority" in sample_df.columns else {}
    )
    sample_by_tier = (
        sample_df["hidden_gem_tier"].value_counts().to_dict()
        if "hidden_gem_tier" in sample_df.columns else {}
    )

    checks = {
        "has_candidates": bool(len(candidates_df) > 0),
        "has_sample_rows": bool(len(sample_df) > 0),
        "top_and_strong_included": bool(
            len(sample_df[sample_df["hidden_gem_tier"].isin(["top_hidden_gem", "strong_hidden_gem"])])
            == len(candidates_df[candidates_df["hidden_gem_tier"].isin(["top_hidden_gem", "strong_hidden_gem"])])
        ) if len(candidates_df) and "hidden_gem_tier" in candidates_df.columns else False,
        "sample_candidate_ids_unique": bool(
            sample_df["hidden_gem_candidate_id"].nunique(dropna=True) == len(sample_df)
        ) if len(sample_df) and "hidden_gem_candidate_id" in sample_df.columns else True,
        "sample_has_manual_columns": bool(all(col in sample_df.columns for col in MANUAL_COLUMNS)),
        "score_in_0_100": bool(sample_df["hidden_gem_score"].between(0, 100).all())
        if len(sample_df) and "hidden_gem_score" in sample_df.columns else True,
        "artifact_scope_ok": bool((candidates_df["artifact_ranking_scope"] == args.artifact_ranking_scope).all())
        if len(candidates_df) and "artifact_ranking_scope" in candidates_df.columns else False,
        "db_ranking_scope_ok": bool((candidates_df["ranking_scope"] == args.db_ranking_scope).all())
        if len(candidates_df) and "ranking_scope" in candidates_df.columns else False,
    }

    if args.include_mentions:
        checks["has_mention_examples"] = bool(len(mentions_df) > 0)
        checks["mention_examples_link_to_sample"] = bool(
            set(mentions_df["hidden_gem_candidate_id"].astype(str)).issubset(
                set(sample_df["hidden_gem_candidate_id"].astype(str))
            )
        ) if len(mentions_df) and "hidden_gem_candidate_id" in mentions_df.columns else False

    return {
        "script": "export_sevilla_ai_manual_review_sample",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ranking_scope_note": {
            "db_ranking_scope": args.db_ranking_scope,
            "artifact_ranking_scope": args.artifact_ranking_scope,
            "ranking_version": args.ranking_version,
            "is_production_ready": False,
        },
        "filters": {
            "schema": args.schema,
            "min_score": args.min_score,
            "sample_method": args.sample_method,
            "not_selected_strategy": args.not_selected_strategy,
            "promising_sample": args.promising_sample,
            "exploratory_sample": args.exploratory_sample,
            "not_selected_sample": args.not_selected_sample,
            "random_state": args.random_state,
            "include_mentions": args.include_mentions,
            "examples_per_candidate": args.examples_per_candidate,
            "include_full_review_text": args.include_full_review_text,
        },
        "source_counts": {
            "all_candidates": int(len(candidates_df)),
            "selected_candidates": int(len(selected_df)),
            "places": int(candidates_df["place_id"].nunique()) if "place_id" in candidates_df.columns else 0,
            "dishes": int(candidates_df["dish_id"].nunique()) if "dish_id" in candidates_df.columns else 0,
            "neighborhoods": int(candidates_df["neighborhood_id"].nunique()) if "neighborhood_id" in candidates_df.columns else 0,
            "districts": int(candidates_df["district_id"].nunique()) if "district_id" in candidates_df.columns else 0,
        },
        "sample_counts": {
            "sample_rows": int(len(sample_df)),
            "sample_places": int(sample_df["place_id"].nunique()) if "place_id" in sample_df.columns else 0,
            "sample_dishes": int(sample_df["dish_id"].nunique()) if "dish_id" in sample_df.columns else 0,
            "sample_neighborhoods": int(sample_df["neighborhood_id"].nunique()) if "neighborhood_id" in sample_df.columns else 0,
            "sample_districts": int(sample_df["district_id"].nunique()) if "district_id" in sample_df.columns else 0,
            "sample_by_priority": sample_by_priority,
            "sample_by_tier": sample_by_tier,
            "mention_examples_rows": int(len(mentions_df)),
        },
        "manual_review_options": {
            "manual_decision_options": MANUAL_DECISION_OPTIONS,
            "manual_error_type_options": ERROR_TYPE_OPTIONS,
            "recommended_review_values": {
                "manual_dish_is_correct": "yes/no/unclear",
                "manual_place_dish_association_is_correct": "yes/no/unclear",
                "manual_sentiment_is_correct": "yes/no/unclear",
                "manual_evidence_is_sufficient": "yes/no/unclear",
                "manual_ranking_position_is_reasonable": "yes/no/unclear",
                "manual_should_keep_for_v2": "yes/no/unclear",
            },
        },
        "checks": checks,
        "files": output_files,
        "notes": [
            "This sample is intended for manual QA and IA v2 planning.",
            "Review top_hidden_gem and strong_hidden_gem first.",
            "Use manual_error_type to build an error taxonomy before changing models or scoring.",
            "If mention examples include full review text, do not commit them to Git.",
        ],
    }


def write_review_instructions(output_path: Path) -> None:
    content = f"""# Sevilla AI Manual Review Sample - Instructions

This folder contains a manual review sample for the Sevilla Hidden Gems AI pilot.

## Main file

```text
{DEFAULT_SAMPLE_NAME}.csv
```

Open this file in a spreadsheet tool and fill the manual columns:

| Column | Recommended values |
|---|---|
| `manual_decision` | `{', '.join(MANUAL_DECISION_OPTIONS)}` |
| `manual_error_type` | `{', '.join(ERROR_TYPE_OPTIONS)}` |
| `manual_dish_is_correct` | `yes`, `no`, `unclear` |
| `manual_place_dish_association_is_correct` | `yes`, `no`, `unclear` |
| `manual_sentiment_is_correct` | `yes`, `no`, `unclear` |
| `manual_evidence_is_sufficient` | `yes`, `no`, `unclear` |
| `manual_ranking_position_is_reasonable` | `yes`, `no`, `unclear` |
| `manual_should_keep_for_v2` | `yes`, `no`, `unclear` |

## Suggested review order

1. Review all `mandatory_top_strong` rows first.
2. Review `sample_promising` rows.
3. Review `sample_exploratory` rows.
4. Review `sample_not_selected` rows to find possible false negatives.

## How to interpret priorities

- `mandatory_top_strong`: all top and strong candidates; these are the most visible results.
- `sample_promising`: representative sample of promising candidates.
- `sample_exploratory`: representative sample of lower-confidence selected candidates.
- `sample_not_selected`: non-selected candidates close to the threshold or random, depending on export settings.

## Important

If the mentions file includes full review text, do not commit it to GitHub.
"""
    output_path.write_text(content, encoding="utf-8")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a manual review sample for the Sevilla Hidden Gems AI pilot."
    )
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--db-ranking-scope", default=DEFAULT_DB_RANKING_SCOPE)
    parser.add_argument("--artifact-ranking-scope", default=DEFAULT_ARTIFACT_RANKING_SCOPE)
    parser.add_argument("--ranking-version", default=DEFAULT_RANKING_VERSION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--sample-name", default=DEFAULT_SAMPLE_NAME)

    parser.add_argument("--promising-sample", type=int, default=30)
    parser.add_argument("--exploratory-sample", type=int, default=30)
    parser.add_argument("--not-selected-sample", type=int, default=30)
    parser.add_argument(
        "--sample-method",
        choices=["systematic", "random"],
        default="systematic",
        help="How to sample promising/exploratory candidates.",
    )
    parser.add_argument(
        "--not-selected-strategy",
        choices=["near_threshold", "random"],
        default="near_threshold",
        help="How to sample not_selected candidates.",
    )
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--min-score", type=float, default=None)

    parser.add_argument("--include-mentions", action="store_true")
    parser.add_argument("--examples-per-candidate", type=int, default=3)
    parser.add_argument(
        "--include-full-review-text",
        action="store_true",
        help="Include full review_text_raw in the mention examples file. Do not commit this output.",
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with status 1 if critical checks fail.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validate_schema_name(args.schema)

    print_section("1. Loading Sevilla pilot candidates")
    candidates_df = load_candidate_detail(args)
    if candidates_df.empty:
        print("No candidates found for the provided filters.")
        return 1

    print(f"Candidates loaded: {len(candidates_df)}")
    print(candidates_df["hidden_gem_tier"].value_counts(dropna=False).to_string())

    print_section("2. Building manual review sample")
    sample_df = build_manual_review_sample(args, candidates_df)
    print(f"Sample rows: {len(sample_df)}")
    if not sample_df.empty:
        print(sample_df["manual_review_priority"].value_counts().to_string())
        print("\nBy tier:")
        print(sample_df["hidden_gem_tier"].value_counts().to_string())

    print_section("3. Loading mention examples")
    mentions_df = pd.DataFrame()
    if args.include_mentions:
        mentions_df = load_mentions_for_sample(
            schema=args.schema,
            sample_df=sample_df,
            examples_per_candidate=args.examples_per_candidate,
            include_full_review_text=args.include_full_review_text,
        )
        print(f"Mention example rows: {len(mentions_df)}")
    else:
        print("Mention examples disabled. Use --include-mentions to export them.")

    print_section("4. Saving outputs")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    sample_csv = output_dir / f"{args.sample_name}.csv"
    sample_jsonl = output_dir / f"{args.sample_name}.jsonl"
    summary_json = output_dir / f"{args.sample_name}_summary.json"
    instructions_md = output_dir / f"{args.sample_name}_instructions.md"
    mentions_csv = output_dir / f"{args.sample_name}_mention_examples.csv"

    output_files: list[str] = []
    save_csv(sample_df, sample_csv)
    output_files.append(sample_csv.name)
    save_jsonl(sample_df, sample_jsonl)
    output_files.append(sample_jsonl.name)

    if args.include_mentions:
        save_csv(mentions_df, mentions_csv)
        output_files.append(mentions_csv.name)

    write_review_instructions(instructions_md)
    output_files.append(instructions_md.name)

    summary = build_summary(args, candidates_df, sample_df, mentions_df, output_files)
    save_json(summary, summary_json)
    output_files.append(summary_json.name)

    print(f"Output dir: {output_dir}")
    for file_name in output_files:
        print(f"- {file_name}")

    print_section("Final checks")
    print(json.dumps(to_builtin(summary["checks"]), indent=2, ensure_ascii=False, allow_nan=False))

    critical_ok = all(bool(v) for v in summary["checks"].values())
    if critical_ok:
        print("\nManual review sample export completed successfully.")
        return 0

    print("\nManual review sample export completed with warnings.")
    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
