"""Export Sevilla reviews as an annotation dataset for dish NER.

Run from repository root:

python -m scripts.export_sevilla_ner_annotation_dataset `
  --output-dir data/artifacts/ai/sevilla/model_training/ner `
  --include-preannotations `
  --strict

The output contains review texts and optional weak preannotations from the
current hybrid `dish_mention` table. Do not commit exported review text to Git.
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
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_training/ner")
DEFAULT_VERSION = "sevilla_ner_annotation_dataset_v1"
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


def safe_text(x: Any) -> str:
    return "" if x is None else str(x).replace("\x00", " ").strip()


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


def place_coordinate_select_exprs(schema: str) -> tuple[str, str]:
    """Return latitude/longitude SQL expressions compatible with current place DDL.

    Some project DDL versions store coordinates as a geometry column, while others
    only expose them through views/artifacts. Coordinates are useful for context,
    but they are not required for NER annotation, so this function safely falls
    back to NULL when the column is not available.
    """
    p_cols = get_columns(schema, "place")

    for geom_col in ["location", "geom", "geometry", "point", "geo_point"]:
        if geom_col in p_cols:
            return (
                f"CASE WHEN p.{geom_col} IS NOT NULL THEN ST_Y(p.{geom_col}::geometry) END AS latitude",
                f"CASE WHEN p.{geom_col} IS NOT NULL THEN ST_X(p.{geom_col}::geometry) END AS longitude",
            )

    if {"latitude", "longitude"}.issubset(p_cols):
        return "p.latitude AS latitude", "p.longitude AS longitude"

    if {"lat", "lon"}.issubset(p_cols):
        return "p.lat AS latitude", "p.lon AS longitude"

    return "NULL::double precision AS latitude", "NULL::double precision AS longitude"


def load_reviews(args: argparse.Namespace) -> pd.DataFrame:
    schema = validate_schema(args.schema)
    latitude_expr, longitude_expr = place_coordinate_select_exprs(schema)

    where = [
        "ss.source_code = :source_system",
        "r.is_active = TRUE",
        "COALESCE(r.is_deleted_in_source, FALSE) = FALSE",
        "r.review_text_raw IS NOT NULL",
        "LENGTH(TRIM(r.review_text_raw)) >= :min_text_length",
    ]
    params: dict[str, Any] = {"source_system": args.source_system, "min_text_length": args.min_text_length}
    if args.language:
        where.append("LOWER(COALESCE(r.review_language, '')) = LOWER(:language)")
        params["language"] = args.language
    limit_sql = ""
    if args.max_reviews and args.max_reviews > 0:
        limit_sql = "LIMIT :max_reviews"
        params["max_reviews"] = args.max_reviews

    sql = f"""
        SELECT
            r.review_id::text AS review_id,
            r.place_id::text AS place_id,
            p.display_name AS place_name,
            p.address_text,
            {latitude_expr},
            {longitude_expr},
            pna.neighborhood_id::text AS neighborhood_id,
            n.official_name AS neighborhood_name,
            pna.district_id::text AS district_id,
            d.official_name AS district_name,
            r.rating_value,
            r.review_language,
            r.review_created_at,
            r.source_review_id,
            r.source_place_record_id,
            r.review_text_raw AS text
        FROM {qname(schema, 'review')} r
        JOIN {qname(schema, 'source_system')} ss ON ss.source_system_id = r.source_system_id
        JOIN {qname(schema, 'place')} p ON p.place_id = r.place_id
        LEFT JOIN {qname(schema, 'place_neighborhood_assignment')} pna
            ON pna.place_id = p.place_id AND pna.is_current = TRUE
        LEFT JOIN {qname(schema, 'neighborhood')} n ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN {qname(schema, 'district')} d ON d.district_id = pna.district_id
        WHERE {' AND '.join(where)}
        ORDER BY r.review_created_at DESC NULLS LAST, r.review_id
        {limit_sql}
    """
    return read_df(sql, params)


def load_preannotations(args: argparse.Namespace, review_ids: list[str]) -> pd.DataFrame:
    if not review_ids:
        return pd.DataFrame()
    schema = validate_schema(args.schema)
    dm_cols = get_columns(schema, "dish_mention")
    d_cols = get_columns(schema, "dish")

    # Keep the query compatible with slightly different DDL versions.
    mention_expr = "dm.mention_text" if "mention_text" in dm_cols else "dm.dish_mention_text" if "dish_mention_text" in dm_cols else "NULL"
    start_expr = "dm.start_char" if "start_char" in dm_cols else "NULL"
    end_expr = "dm.end_char" if "end_char" in dm_cols else "NULL"
    conf_expr = "dm.ner_confidence_mean" if "ner_confidence_mean" in dm_cols else "dm.confidence" if "confidence" in dm_cols else "NULL"
    method_expr = "dm.detection_method" if "detection_method" in dm_cols else "NULL"
    context_expr = "dm.context_sentence" if "context_sentence" in dm_cols else "NULL"
    display_expr = "d.display_name" if "display_name" in d_cols else "d.canonical_name" if "canonical_name" in d_cols else "d.normalized_name"
    normalized_expr = "d.normalized_name" if "normalized_name" in d_cols else display_expr

    sql = f"""
        SELECT
            dm.review_id::text AS review_id,
            dm.dish_mention_id::text AS dish_mention_id,
            dm.dish_id::text AS dish_id,
            {display_expr} AS dish_display_name,
            {normalized_expr} AS dish_normalized_name,
            {mention_expr} AS mention_text,
            {start_expr} AS start_char,
            {end_expr} AS end_char,
            {conf_expr} AS confidence,
            {method_expr} AS detection_method,
            {context_expr} AS context_sentence
        FROM {qname(schema, 'dish_mention')} dm
        JOIN {qname(schema, 'dish')} d ON d.dish_id = dm.dish_id
        WHERE dm.review_id::text = ANY(:review_ids)
        ORDER BY dm.review_id, start_char NULLS LAST
    """
    return read_df(sql, {"review_ids": review_ids})


def find_span(text_value: str, mention_text: str) -> tuple[int | None, int | None]:
    if not mention_text:
        return None, None
    idx = text_value.lower().find(mention_text.lower())
    if idx < 0:
        return None, None
    return idx, idx + len(mention_text)


def build_records(reviews_df: pd.DataFrame, ann_df: pd.DataFrame, include_preannotations: bool) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    if include_preannotations and not ann_df.empty:
        for rid, g in ann_df.groupby("review_id"):
            groups[str(rid)] = g.to_dict(orient="records")

    records: list[dict[str, Any]] = []
    for _, row in reviews_df.iterrows():
        review_id = str(row["review_id"])
        text_value = safe_text(row["text"])
        entities = []
        for m in groups.get(review_id, []):
            mention = safe_text(m.get("mention_text"))
            start, end = None, None
            try:
                s, e = int(m.get("start_char")), int(m.get("end_char"))
                if 0 <= s < e <= len(text_value):
                    start, end = s, e
            except Exception:
                start, end = find_span(text_value, mention)
            entities.append({
                "start": start,
                "end": end,
                "label": "DISH",
                "text": text_value[start:end] if start is not None and end is not None else mention,
                "source": "hybrid_preannotation_v1",
                "dish_mention_id": m.get("dish_mention_id"),
                "dish_id": m.get("dish_id"),
                "dish_display_name": m.get("dish_display_name"),
                "dish_normalized_name": m.get("dish_normalized_name"),
                "confidence": m.get("confidence"),
                "detection_method": m.get("detection_method"),
            })
        records.append({
            "document_id": f"sevilla_google_review_{review_id}",
            "review_id": review_id,
            "text": text_value,
            "entities": entities,
            "manual_entities": [],
            "annotation_status": "pending",
            "metadata": {k: to_builtin(row.get(k)) for k in row.index if k not in {"text"}},
        })
    return records


def save_guidelines(path: Path) -> None:
    path.write_text("""# Sevilla Dish NER Annotation Guidelines v1

Annotate dish mentions with label `DISH`.

Annotate complete compound dishes when possible:
- `ensaladilla de gambas`, not just `gambas`.
- `croquetas de rabo de toro`, not just `rabo de toro`.
- `solomillo al whisky`, not just `solomillo`.

Do not annotate generic experience/service words such as `comida`, `cena`, `servicio`, `ambiente`, `precio`, `local`.

The `entities` field contains weak preannotations from the current hybrid system. They must be reviewed before training.

Do not commit exported review text to GitHub.
""", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export Sevilla dish NER annotation dataset.")
    p.add_argument("--schema", default=DEFAULT_SCHEMA)
    p.add_argument("--source-system", default=DEFAULT_SOURCE_SYSTEM)
    p.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--version", default=DEFAULT_VERSION)
    p.add_argument("--language", default=None)
    p.add_argument("--min-text-length", type=int, default=20)
    p.add_argument("--max-reviews", type=int, default=None)
    p.add_argument("--include-preannotations", action="store_true")
    p.add_argument("--strict", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    reviews = load_reviews(args)
    anns = load_preannotations(args, reviews["review_id"].astype(str).tolist()) if args.include_preannotations and not reviews.empty else pd.DataFrame()
    records = build_records(reviews, anns, args.include_preannotations)

    flat = pd.DataFrame([{
        "document_id": r["document_id"],
        "review_id": r["review_id"],
        "text": r["text"],
        "text_length_chars": len(r["text"]),
        "preannotation_count": len(r["entities"]),
        "preannotated_entities_json": json.dumps(to_builtin(r["entities"]), ensure_ascii=False, allow_nan=False),
        "manual_entities_json": "[]",
        "annotation_status": r["annotation_status"],
        **r["metadata"],
    } for r in records])

    jsonl_path = out / f"{args.version}.jsonl"
    csv_path = out / f"{args.version}.csv"
    summary_path = out / f"{args.version}_summary.json"
    guidelines_path = out / "sevilla_ner_annotation_guidelines_v1.md"

    write_jsonl(records, jsonl_path)
    flat.to_csv(csv_path, index=False, encoding="utf-8")
    save_guidelines(guidelines_path)

    checks = {
        "has_reviews": bool(len(reviews)),
        "has_records": bool(len(records)),
        "all_have_text": bool(len(flat) and flat["text"].astype(str).str.len().gt(0).all()),
        "all_have_review_id": bool(len(flat) and flat["review_id"].notna().all()),
        "preannotations_loaded_when_requested": bool(len(anns)) if args.include_preannotations else True,
        "csv_exists": csv_path.exists(),
        "jsonl_exists": jsonl_path.exists(),
    }
    summary = {
        "script": "export_sevilla_ner_annotation_dataset",
        "version": args.version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {
            "reviews": int(len(reviews)),
            "records": int(len(records)),
            "places": int(flat["place_id"].nunique()) if "place_id" in flat else 0,
            "districts": int(flat["district_name"].nunique()) if "district_name" in flat else 0,
            "neighborhoods": int(flat["neighborhood_name"].nunique()) if "neighborhood_name" in flat else 0,
            "preannotation_rows": int(len(anns)),
            "records_with_preannotations": int((flat["preannotation_count"] > 0).sum()) if "preannotation_count" in flat else 0,
            "total_preannotations": int(flat["preannotation_count"].sum()) if "preannotation_count" in flat else 0,
        },
        "checks": checks,
        "files": [jsonl_path.name, csv_path.name, summary_path.name, guidelines_path.name],
        "notes": ["Weak preannotations are not gold labels.", "Do not commit exported review text to Git."],
    }
    save_json(summary, summary_path)
    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, allow_nan=False))
    return 2 if args.strict and not all(checks.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
