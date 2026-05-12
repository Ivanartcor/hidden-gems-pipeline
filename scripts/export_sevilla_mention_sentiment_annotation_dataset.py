"""Export Sevilla mention-level sentiment annotation dataset.

This dataset is designed for targeted dish sentiment / ABSA training:

    review context + dish mention -> positive / neutral / negative

Run from repository root:

python -m scripts.export_sevilla_mention_sentiment_annotation_dataset `
  --output-dir data/artifacts/ai/sevilla/model_training/sentiment `
  --include-full-review-text `
  --strict

Do not commit exported full review text to GitHub.
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
DEFAULT_SOURCE_SYSTEM = "google_places"
DEFAULT_VIEW = "vw_ai_dish_mentions_with_sentiment"
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_training/sentiment")
DEFAULT_VERSION = "sevilla_mention_sentiment_annotation_dataset_v1"
SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_schema(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid schema name: {schema!r}")
    return schema


def qname(schema: str, name: str) -> str:
    return f'"{validate_schema(schema)}"."{name}"'


def to_builtin(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, dict):
        return {str(k): to_builtin(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, set)):
        return [to_builtin(v) for v in x]
    if isinstance(x, UUID):
        return str(x)
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    if isinstance(x, Decimal):
        return None if x.is_nan() else float(x)
    if hasattr(x, "item"):
        try:
            return to_builtin(x.item())
        except Exception:
            pass
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    return x


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def save_json(obj: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(to_builtin(obj), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def write_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(to_builtin(r), ensure_ascii=False, allow_nan=False) + "\n")


def get_columns(schema: str, relation: str) -> set[str]:
    df = read_df(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema AND table_name = :relation
        """,
        {"schema": schema, "relation": relation},
    )
    return set(df["column_name"].tolist()) if not df.empty else set()


def select_expr(cols: set[str], col: str, alias: str | None = None, fallback: str = "NULL") -> str:
    out = alias or col
    return f"v.{col} AS {out}" if col in cols else f"{fallback} AS {out}"


def load_mentions(args: argparse.Namespace) -> pd.DataFrame:
    schema = validate_schema(args.schema)
    cols = get_columns(schema, args.view)
    if not cols:
        raise RuntimeError(f"No columns found for {schema}.{args.view}. Is 08_ai_views.sql loaded?")
    for required in ["review_id", "place_id", "dish_id"]:
        if required not in cols:
            raise RuntimeError(f"Required column missing in {schema}.{args.view}: {required}")

    select_list = [
        select_expr(cols, "place_id"),
        select_expr(cols, "place_name"),
        select_expr(cols, "dish_id"),
        select_expr(cols, "dish_name"),
        select_expr(cols, "dish_display_name"),
        select_expr(cols, "review_id"),
        select_expr(cols, "rating_value"),
        select_expr(cols, "sentiment_label", "weak_sentiment_label"),
        select_expr(cols, "sentiment_score", "weak_sentiment_score"),
        select_expr(cols, "sentiment_confidence", "weak_sentiment_confidence"),
        select_expr(cols, "sentiment_reliability_tier", "weak_sentiment_reliability_tier"),
        select_expr(cols, "sentiment_reason", "weak_sentiment_reason"),
        select_expr(cols, "mention_text"),
        select_expr(cols, "context_sentence"),
        select_expr(cols, "target_clause_context"),
        select_expr(cols, "review_text_raw"),
    ]

    where = [
        f"EXISTS (SELECT 1 FROM {qname(schema, 'review')} r JOIN {qname(schema, 'source_system')} ss ON ss.source_system_id = r.source_system_id WHERE r.review_id = v.review_id AND ss.source_code = :source_system)"
    ]
    params: dict[str, Any] = {"source_system": args.source_system}
    if args.label and "sentiment_label" in cols:
        where.append("LOWER(COALESCE(v.sentiment_label, '')) = LOWER(:label)")
        params["label"] = args.label
    if args.min_confidence is not None and "sentiment_confidence" in cols:
        where.append("v.sentiment_confidence >= :min_confidence")
        params["min_confidence"] = args.min_confidence
    limit_sql = ""
    if args.max_rows and args.max_rows > 0:
        limit_sql = "LIMIT :max_rows"
        params["max_rows"] = args.max_rows

    sql = f"""
        SELECT {', '.join(select_list)}
        FROM {qname(schema, args.view)} v
        WHERE {' AND '.join(where)}
        ORDER BY v.review_id, v.place_id, v.dish_id
        {limit_sql}
    """
    return read_df(sql, params)


def build_dataset(df: pd.DataFrame, include_full_review_text: bool) -> pd.DataFrame:
    out = df.copy()
    dedup_cols = [c for c in ["review_id", "place_id", "dish_id", "mention_text", "context_sentence"] if c in out.columns]
    if dedup_cols:
        out = out.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    out["annotation_id"] = [f"sevilla_sentiment_{i:06d}" for i in range(1, len(out) + 1)]
    out["dish_mention"] = out.get("mention_text", "").fillna("").astype(str)
    context = out.get("context_sentence", pd.Series([""] * len(out))).fillna("").astype(str)
    if include_full_review_text and "review_text_raw" in out.columns:
        review_text = out["review_text_raw"].fillna("").astype(str)
    else:
        review_text = context
        if "review_text_raw" in out.columns:
            out = out.drop(columns=["review_text_raw"])
    out["model_input_text"] = "[REVIEW] " + review_text + "\n[DISH] " + out["dish_mention"]
    out["manual_sentiment_label"] = ""
    out["manual_sentiment_confidence"] = ""
    out["manual_sentiment_notes"] = ""
    out["annotation_status"] = "pending"
    return out


def save_guidelines(path: Path) -> None:
    path.write_text("""# Sevilla Mention Sentiment Annotation Guidelines v1

Classify the sentiment toward the specific dish mention, not the whole restaurant.

Valid labels:
- `positive`
- `neutral`
- `negative`

Use `positive` only when the dish is explicitly praised.
Use `negative` when the dish is explicitly criticized.
Use `neutral` when the dish is mentioned without clear evaluation.

Do not let the star rating override the local text around the dish.
Do not commit exported full reviews to GitHub.
""", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export Sevilla targeted dish sentiment annotation dataset.")
    p.add_argument("--schema", default=DEFAULT_SCHEMA)
    p.add_argument("--view", default=DEFAULT_VIEW)
    p.add_argument("--source-system", default=DEFAULT_SOURCE_SYSTEM)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--version", default=DEFAULT_VERSION)
    p.add_argument("--label", default=None)
    p.add_argument("--min-confidence", type=float, default=None)
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--include-full-review-text", action="store_true")
    p.add_argument("--strict", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    raw = load_mentions(args)
    data = build_dataset(raw, args.include_full_review_text)

    csv_path = out / f"{args.version}.csv"
    jsonl_path = out / f"{args.version}.jsonl"
    summary_path = out / f"{args.version}_summary.json"
    guidelines_path = out / "sevilla_mention_sentiment_annotation_guidelines_v1.md"

    data.to_csv(csv_path, index=False, encoding="utf-8")
    write_jsonl([to_builtin(r) for r in data.to_dict(orient="records")], jsonl_path)
    save_guidelines(guidelines_path)

    checks = {
        "has_rows": bool(len(data)),
        "all_have_review_id": bool("review_id" in data and data["review_id"].notna().all()),
        "all_have_place_id": bool("place_id" in data and data["place_id"].notna().all()),
        "all_have_dish_id": bool("dish_id" in data and data["dish_id"].notna().all()),
        "all_have_model_input": bool(len(data) and data["model_input_text"].astype(str).str.len().gt(0).all()),
        "csv_exists": csv_path.exists(),
        "jsonl_exists": jsonl_path.exists(),
    }
    summary = {
        "script": "export_sevilla_mention_sentiment_annotation_dataset",
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "raw_rows": int(len(raw)),
            "annotation_rows": int(len(data)),
            "places": int(data["place_id"].nunique()) if "place_id" in data else 0,
            "dishes": int(data["dish_id"].nunique()) if "dish_id" in data else 0,
            "reviews": int(data["review_id"].nunique()) if "review_id" in data else 0,
            "weak_sentiment_distribution": data["weak_sentiment_label"].value_counts(dropna=False).to_dict() if "weak_sentiment_label" in data else {},
        },
        "checks": checks,
        "files": [csv_path.name, jsonl_path.name, summary_path.name, guidelines_path.name],
        "notes": ["Weak labels are not gold labels.", "Fill manual_sentiment_label before supervised training."],
    }
    save_json(summary, summary_path)
    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if args.strict and not all(checks.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
