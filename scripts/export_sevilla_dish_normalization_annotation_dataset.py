"""Export Sevilla dish normalization / entity-linking annotation dataset.

This dataset supports the task:

    dish mention + context -> correct canonical dish_id

It is especially useful for fixing errors like:
- `ensaladilla de gambas` normalized as `gambas`
- `croquetas de rabo de toro` normalized as `rabo de toro`
- `tarta de manzana` normalized as `tarta de queso`

Run from repository root:

python -m scripts.export_sevilla_dish_normalization_annotation_dataset `
  --output-dir data/artifacts/ai/sevilla/model_training/normalization `
  --include-candidate-dishes `
  --strict
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
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
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_training/normalization")
DEFAULT_VERSION = "sevilla_dish_normalization_annotation_dataset_v1"
SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
PROBLEM_TERMS = [
    "tarta", "gamba", "gambas", "ensaladilla", "rabo", "toro", "croqueta", "croquetas",
    "adobo", "cazón", "atun", "atún", "hamburguesa", "pizza", "tortilla", "pringa", "pringá",
]


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
        select_expr(cols, "dish_id", "current_dish_id"),
        select_expr(cols, "dish_name", "current_dish_name"),
        select_expr(cols, "dish_display_name", "current_dish_display_name"),
        select_expr(cols, "review_id"),
        select_expr(cols, "rating_value"),
        select_expr(cols, "mention_text"),
        select_expr(cols, "context_sentence"),
        select_expr(cols, "target_clause_context"),
        select_expr(cols, "review_text_raw"),
        select_expr(cols, "sentiment_label", "weak_sentiment_label"),
        select_expr(cols, "sentiment_confidence", "weak_sentiment_confidence"),
    ]

    where = [
        f"EXISTS (SELECT 1 FROM {qname(schema, 'review')} r JOIN {qname(schema, 'source_system')} ss ON ss.source_system_id = r.source_system_id WHERE r.review_id = v.review_id AND ss.source_code = :source_system)"
    ]
    params: dict[str, Any] = {"source_system": args.source_system}
    if args.focus_problem_terms:
        patterns = [f"%{t.lower()}%" for t in PROBLEM_TERMS]
        # The LIKE ANY syntax works with psycopg2 arrays.
        where.append("(LOWER(COALESCE(v.mention_text, '')) LIKE ANY(:patterns) OR LOWER(COALESCE(v.dish_name, '')) LIKE ANY(:patterns) OR LOWER(COALESCE(v.dish_display_name, '')) LIKE ANY(:patterns))")
        params["patterns"] = patterns
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


def load_catalog(schema: str) -> pd.DataFrame:
    d_cols = get_columns(schema, "dish")
    da_cols = get_columns(schema, "dish_alias")
    display_expr = "d.display_name" if "display_name" in d_cols else "d.canonical_name" if "canonical_name" in d_cols else "d.normalized_name"
    normalized_expr = "d.normalized_name" if "normalized_name" in d_cols else display_expr
    alias_text = "da.alias_text" if "alias_text" in da_cols else "da.alias" if "alias" in da_cols else "NULL"
    alias_norm = "da.alias_normalized" if "alias_normalized" in da_cols else "NULL"
    active_filter = "WHERE d.is_active = TRUE" if "is_active" in d_cols else ""
    sql = f"""
        SELECT
            d.dish_id::text AS dish_id,
            {display_expr} AS dish_display_name,
            {normalized_expr} AS dish_normalized_name,
            {alias_text} AS alias_text,
            {alias_norm} AS alias_normalized
        FROM {qname(schema, 'dish')} d
        LEFT JOIN {qname(schema, 'dish_alias')} da ON da.dish_id = d.dish_id
        {active_filter}
    """
    return read_df(sql)


def normalize_for_match(value: Any) -> str:
    text_value = "" if value is None else str(value).lower().strip()
    text_value = unicodedata.normalize("NFKD", text_value)
    text_value = "".join(ch for ch in text_value if not unicodedata.combining(ch))
    text_value = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def terms_from_row(row: pd.Series) -> list[str]:
    raw_terms = [
        row.get("dish_display_name"),
        row.get("dish_normalized_name"),
        row.get("alias_text"),
        row.get("alias_normalized"),
    ]
    terms = []
    for value in raw_terms:
        term = normalize_for_match(value)
        if term and term not in terms:
            terms.append(term)
    return terms


def build_catalog_index(catalog: pd.DataFrame) -> dict[str, Any]:
    """Build a lightweight inverted index so candidate generation is fast.

    The first version scanned the full dish catalog for every mention. With the
    combined Yelp + Sevilla catalog this can feel like the script is stuck. This
    index restricts each row to plausible candidates sharing a relevant token or
    the current dish_id.
    """
    dishes: dict[str, dict[str, Any]] = {}
    token_index: dict[str, set[str]] = {}

    for _, row in catalog.iterrows():
        dish_id = str(row.get("dish_id") or "").strip()
        if not dish_id:
            continue

        entry = dishes.setdefault(
            dish_id,
            {
                "dish_id": dish_id,
                "dish_display_name": to_builtin(row.get("dish_display_name")),
                "dish_normalized_name": to_builtin(row.get("dish_normalized_name")),
                "terms": set(),
            },
        )
        for term in terms_from_row(row):
            entry["terms"].add(term)
            for token in re.findall(r"\w+", term):
                if len(token) >= 3:
                    token_index.setdefault(token, set()).add(dish_id)

    return {"dishes": dishes, "token_index": token_index}


def candidate_options(row: pd.Series, catalog_index: dict[str, Any], max_options: int) -> list[dict[str, Any]]:
    if not catalog_index:
        return []

    dishes: dict[str, dict[str, Any]] = catalog_index.get("dishes", {})
    token_index: dict[str, set[str]] = catalog_index.get("token_index", {})
    if not dishes:
        return []

    current_id = str(row.get("current_dish_id") or "").strip()
    mention = normalize_for_match(row.get("mention_text"))
    current = normalize_for_match(row.get("current_dish_name") or row.get("current_dish_display_name"))
    context = normalize_for_match(row.get("context_sentence") or row.get("target_clause_context"))
    haystack = f"{mention} {current} {context}".strip()
    tokens = {t for t in re.findall(r"\w+", haystack) if len(t) >= 3}

    candidate_ids: set[str] = set()
    for token in tokens:
        candidate_ids.update(token_index.get(token, set()))
    if current_id in dishes:
        candidate_ids.add(current_id)

    scored: list[tuple[int, dict[str, Any]]] = []
    for dish_id in candidate_ids:
        d = dishes[dish_id]
        score = 0
        if dish_id == current_id:
            score += 6
        for term in d.get("terms", []):
            if not term:
                continue
            if term == mention:
                score += 8
            elif term and term in haystack:
                score += 5
            else:
                term_tokens = {t for t in re.findall(r"\w+", term) if len(t) >= 3}
                score += len(tokens.intersection(term_tokens))
        if score > 0:
            scored.append((score, d))

    scored.sort(key=lambda x: (x[0], x[1].get("dish_display_name") or ""), reverse=True)
    return [
        {
            "dish_id": to_builtin(d.get("dish_id")),
            "dish_display_name": to_builtin(d.get("dish_display_name")),
            "dish_normalized_name": to_builtin(d.get("dish_normalized_name")),
            "score_hint": int(score),
        }
        for score, d in scored[:max_options]
    ]


def build_dataset(raw: pd.DataFrame, catalog: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = raw.copy()
    dedup_cols = [c for c in ["review_id", "place_id", "mention_text", "context_sentence", "current_dish_id"] if c in out]
    if dedup_cols:
        out = out.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
    out["annotation_id"] = [f"sevilla_norm_{i:06d}" for i in range(1, len(out) + 1)]
    if args.include_candidate_dishes:
        print(f"Building dish candidate index from {len(catalog)} catalog rows...")
        catalog_index = build_catalog_index(catalog)
        print(f"Generating candidate dish options for {len(out)} mentions...")
        options = []
        for i, (_, row) in enumerate(out.iterrows(), start=1):
            if i % 500 == 0:
                print(f"  processed {i}/{len(out)} mentions...")
            options.append(
                json.dumps(candidate_options(row, catalog_index, args.max_candidate_options), ensure_ascii=False, allow_nan=False)
            )
        out["candidate_dish_options_json"] = options
    else:
        out["candidate_dish_options_json"] = "[]"
    out["manual_normalization_status"] = ""  # correct/wrong/too_generic/needs_new_dish/unclear
    out["manual_correct_dish_id"] = ""
    out["manual_correct_dish_name"] = ""
    out["manual_should_create_new_dish"] = ""
    out["manual_new_dish_name"] = ""
    out["manual_notes"] = ""
    out["annotation_status"] = "pending"
    return out


def save_guidelines(path: Path) -> None:
    path.write_text("""# Sevilla Dish Normalization Annotation Guidelines v1

For each row, decide if the current canonical dish is correct.

Recommended `manual_normalization_status` values:
- `correct`
- `wrong`
- `too_generic`
- `needs_new_dish`
- `unclear`

Preserve meaningful compound dishes:
- `ensaladilla de gambas` should not automatically become `gambas`.
- `croquetas de rabo de toro` should not automatically become `rabo de toro`.
- `tarta de manzana` should not become `tarta de queso`.

Use `needs_new_dish` if the correct dish does not exist in the catalog.
""", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export Sevilla dish normalization annotation dataset.")
    p.add_argument("--schema", default=DEFAULT_SCHEMA)
    p.add_argument("--view", default=DEFAULT_VIEW)
    p.add_argument("--source-system", default=DEFAULT_SOURCE_SYSTEM)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--version", default=DEFAULT_VERSION)
    p.add_argument("--max-rows", type=int, default=None)
    p.add_argument("--focus-problem-terms", action="store_true")
    p.add_argument("--include-candidate-dishes", action="store_true")
    p.add_argument("--max-candidate-options", type=int, default=8)
    p.add_argument("--strict", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    raw = load_mentions(args)
    catalog = load_catalog(args.schema) if args.include_candidate_dishes else pd.DataFrame()
    data = build_dataset(raw, catalog, args)

    csv_path = out / f"{args.version}.csv"
    jsonl_path = out / f"{args.version}.jsonl"
    summary_path = out / f"{args.version}_summary.json"
    guidelines_path = out / "sevilla_dish_normalization_annotation_guidelines_v1.md"

    data.to_csv(csv_path, index=False, encoding="utf-8")
    write_jsonl([to_builtin(r) for r in data.to_dict(orient="records")], jsonl_path)
    save_guidelines(guidelines_path)

    checks = {
        "has_rows": bool(len(data)),
        "all_have_review_id": bool("review_id" in data and data["review_id"].notna().all()),
        "all_have_place_id": bool("place_id" in data and data["place_id"].notna().all()),
        "all_have_current_dish_id": bool("current_dish_id" in data and data["current_dish_id"].notna().all()),
        "all_have_mention_text": bool("mention_text" in data and data["mention_text"].notna().all()),
        "candidate_options_loaded_when_requested": bool(len(catalog)) if args.include_candidate_dishes else True,
        "csv_exists": csv_path.exists(),
        "jsonl_exists": jsonl_path.exists(),
    }
    summary = {
        "script": "export_sevilla_dish_normalization_annotation_dataset",
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "raw_rows": int(len(raw)),
            "annotation_rows": int(len(data)),
            "places": int(data["place_id"].nunique()) if "place_id" in data else 0,
            "reviews": int(data["review_id"].nunique()) if "review_id" in data else 0,
            "current_dishes": int(data["current_dish_id"].nunique()) if "current_dish_id" in data else 0,
            "catalog_rows_for_options": int(len(catalog)),
        },
        "checks": checks,
        "files": [csv_path.name, jsonl_path.name, summary_path.name, guidelines_path.name],
        "notes": ["Candidate dish options are hints, not gold labels.", "Fill manual normalization columns before supervised training."],
    }
    save_json(summary, summary_path)
    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if args.strict and not all(checks.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
