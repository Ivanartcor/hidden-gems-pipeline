"""Compare Sevilla hybrid dish mentions against NER model mentions.

This script compares the current hybrid dish mention extraction used by the
Sevilla AI pilot with the output produced by the trained NER model:

    sevilla_dish_ner_beto_v1_2

It does not modify the database. It produces comparison artifacts to decide
whether the NER model should replace, complement or be ensembled with the
hybrid extractor in the next IA v2 pipeline.

Recommended execution from repository root:

    python -m scripts.compare_sevilla_hybrid_vs_ner_mentions `
      --ner-path data/artifacts/ai/sevilla/model_inference/ner_v1_2/sevilla_dish_mentions_ner_model_v1_2.jsonl `
      --output-dir data/artifacts/ai/sevilla/model_inference/ner_v1_2_comparison `
      --strict

If you already have a hybrid mentions artifact, you can compare against that
instead of loading from PostgreSQL:

    python -m scripts.compare_sevilla_hybrid_vs_ner_mentions `
      --hybrid-path data/artifacts/ai/sevilla/sentiment/sevilla_dish_mentions_with_sentiment_v1.jsonl `
      --ner-path data/artifacts/ai/sevilla/model_inference/ner_v1_2/sevilla_dish_mentions_ner_model_v1_2.jsonl `
      --strict

Expected outputs:

    hybrid_vs_ner_summary.json
    hybrid_vs_ner_review_level_comparison.csv
    hybrid_vs_ner_mention_text_comparison.csv
    matched_mentions.csv
    ner_only_mentions.csv
    hybrid_only_mentions.csv
    ner_only_compound_candidates.csv
    hybrid_only_compound_candidates.csv
    recommended_next_steps.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from sqlalchemy import text

from src.db.database import engine


# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------

DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_SOURCE_SYSTEM = "google_places"
DEFAULT_NER_PATH = Path(
    "data/artifacts/ai/sevilla/model_inference/ner_v1_2/"
    "sevilla_dish_mentions_ner_model_v1_2.jsonl"
)
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_inference/ner_v1_2_comparison")

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
WORD_RE = re.compile(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+", re.UNICODE)

CONNECTOR_ENDINGS = {
    "de", "del", "con", "y", "o", "u", "en", "al", "a", "para", "por", "que",
}

GENERIC_TERMS = {
    "comida", "cena", "almuerzo", "desayuno", "servicio", "ambiente", "precio", "local",
    "restaurante", "bar", "sitio", "mesa", "carta", "menú", "menu", "plato", "platos",
    "tapa", "tapas", "bebida", "bebidas",
}


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, table: str) -> str:
    return f'"{validate_schema_name(schema)}"."{table}"'


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def to_builtin(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]
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


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def load_table_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ["records", "data", "mentions"]:
                if key in data and isinstance(data[key], list):
                    return pd.DataFrame(data[key])
        raise ValueError(f"JSON no tiene formato tabular soportado: {path}")
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Formato no soportado: {path}")


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text_value = str(value).strip().lower()
    text_value = strip_accents(text_value)
    tokens = WORD_RE.findall(text_value)
    return " ".join(tokens)


def word_count(value: Any) -> int:
    norm = normalize_text(value)
    return len(norm.split()) if norm else 0


def is_compound(value: Any) -> bool:
    return word_count(value) >= 2


def ends_badly(value: Any) -> bool:
    norm = normalize_text(value)
    if not norm:
        return False
    return norm.split()[-1] in CONNECTOR_ENDINGS


def is_generic(value: Any) -> bool:
    return normalize_text(value) in GENERIC_TERMS


def choose_column(df: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def ensure_text_col(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([None] * len(df), index=df.index)
    return df[col]


def safe_to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def print_section(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


# -----------------------------------------------------------------------------
# DB metadata helpers
# -----------------------------------------------------------------------------


def get_table_columns(schema: str, table: str) -> set[str]:
    sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = :schema
          AND table_name = :table
    """
    df = read_df(sql, {"schema": schema, "table": table})
    return set(df["column_name"].astype(str).tolist())


def table_exists(schema: str, table: str) -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :table
        ) AS exists
    """
    df = read_df(sql, {"schema": schema, "table": table})
    return bool(df.iloc[0]["exists"])


def expr_for_column(
    columns: set[str],
    table_alias: str,
    candidates: list[str],
    alias: str,
    cast_text: bool = False,
    fallback_sql: str = "NULL",
) -> str:
    for col in candidates:
        if col in columns:
            expr = f"{table_alias}.{col}"
            if cast_text:
                expr = f"{expr}::text"
            return f"{expr} AS {alias}"
    return f"{fallback_sql} AS {alias}"


# -----------------------------------------------------------------------------
# Load hybrid mentions
# -----------------------------------------------------------------------------


def load_hybrid_from_file(path: Path) -> pd.DataFrame:
    raw = load_table_file(path)
    return standardize_hybrid_mentions(raw, source="file")


def load_hybrid_from_db(schema: str, source_system: str) -> pd.DataFrame:
    schema = validate_schema_name(schema)

    required_tables = ["dish_mention", "review", "source_system", "place", "dish"]
    missing_tables = [t for t in required_tables if not table_exists(schema, t)]
    if missing_tables:
        raise RuntimeError(f"Faltan tablas requeridas en {schema}: {missing_tables}")

    dm_cols = get_table_columns(schema, "dish_mention")
    r_cols = get_table_columns(schema, "review")
    p_cols = get_table_columns(schema, "place")
    d_cols = get_table_columns(schema, "dish")

    mention_expr = expr_for_column(
        dm_cols,
        "dm",
        ["dish_mention_text", "mention_text", "text", "dish_text", "raw_mention_text"],
        "mention_text",
    )
    normalized_expr = expr_for_column(
        dm_cols,
        "dm",
        ["dish_mention_normalized", "mention_normalized", "normalized_mention_text"],
        "mention_normalized",
    )
    context_expr = expr_for_column(
        dm_cols,
        "dm",
        ["context_sentence", "sentence_context", "window_context", "mention_context"],
        "context_sentence",
    )
    start_expr = expr_for_column(
        dm_cols,
        "dm",
        ["start_char", "start_offset", "char_start"],
        "start_char",
    )
    end_expr = expr_for_column(
        dm_cols,
        "dm",
        ["end_char", "end_offset", "char_end"],
        "end_char",
    )
    conf_expr = expr_for_column(
        dm_cols,
        "dm",
        ["confidence", "detection_confidence", "mention_confidence"],
        "confidence",
    )
    method_expr = expr_for_column(
        dm_cols,
        "dm",
        ["detection_method", "method", "candidate_type"],
        "detection_method",
    )

    review_text_expr = expr_for_column(
        r_cols,
        "r",
        ["review_text_raw", "text", "review_text"],
        "review_text",
    )

    place_name_expr = expr_for_column(
        p_cols,
        "p",
        ["display_name", "place_name", "name", "official_name"],
        "place_name",
    )
    address_expr = expr_for_column(
        p_cols,
        "p",
        ["address_text", "formatted_address", "address"],
        "address_text",
    )
    dish_name_expr = expr_for_column(
        d_cols,
        "d",
        ["display_name", "dish_display_name", "dish_name", "canonical_name", "name"],
        "dish_name",
    )
    dish_norm_expr = expr_for_column(
        d_cols,
        "d",
        ["normalized_name", "dish_normalized_name", "normalized_dish_name"],
        "dish_normalized_name",
    )

    # Geography tables are optional for this comparison.
    has_pna = table_exists(schema, "place_neighborhood_assignment")
    has_n = table_exists(schema, "neighborhood")
    has_dist = table_exists(schema, "district")

    geo_join = ""
    geo_select = "NULL AS neighborhood_id, NULL AS neighborhood_name, NULL AS district_id, NULL AS district_name"
    if has_pna and has_n and has_dist:
        pna_cols = get_table_columns(schema, "place_neighborhood_assignment")
        n_cols = get_table_columns(schema, "neighborhood")
        dist_cols = get_table_columns(schema, "district")
        current_filter = "AND COALESCE(pna.is_current, TRUE) = TRUE" if "is_current" in pna_cols else ""
        n_name_expr = expr_for_column(n_cols, "n", ["official_name", "name", "neighborhood_name"], "neighborhood_name")
        d_name_expr = expr_for_column(dist_cols, "dist", ["official_name", "name", "district_name"], "district_name")
        geo_select = f"""
            pna.neighborhood_id::text AS neighborhood_id,
            {n_name_expr},
            pna.district_id::text AS district_id,
            {d_name_expr}
        """
        geo_join = f"""
            LEFT JOIN {qname(schema, 'place_neighborhood_assignment')} pna
                ON pna.place_id = p.place_id {current_filter}
            LEFT JOIN {qname(schema, 'neighborhood')} n ON n.neighborhood_id = pna.neighborhood_id
            LEFT JOIN {qname(schema, 'district')} dist ON dist.district_id = pna.district_id
        """

    active_filter = ""
    if "is_active" in r_cols:
        active_filter += " AND COALESCE(r.is_active, TRUE) = TRUE"
    if "is_deleted_in_source" in r_cols:
        active_filter += " AND COALESCE(r.is_deleted_in_source, FALSE) = FALSE"

    sql = f"""
        SELECT
            dm.dish_mention_id::text AS hybrid_mention_id,
            dm.review_id::text AS review_id,
            dm.place_id::text AS place_id,
            dm.dish_id::text AS dish_id,
            ss.source_code AS source_system,
            {place_name_expr},
            {address_expr},
            {dish_name_expr},
            {dish_norm_expr},
            {mention_expr},
            {normalized_expr},
            {start_expr},
            {end_expr},
            {context_expr},
            {conf_expr},
            {method_expr},
            {review_text_expr},
            {geo_select}
        FROM {qname(schema, 'dish_mention')} dm
        JOIN {qname(schema, 'review')} r ON r.review_id = dm.review_id
        JOIN {qname(schema, 'source_system')} ss ON ss.source_system_id = r.source_system_id
        LEFT JOIN {qname(schema, 'place')} p ON p.place_id = dm.place_id
        LEFT JOIN {qname(schema, 'dish')} d ON d.dish_id = dm.dish_id
        {geo_join}
        WHERE ss.source_code = :source_system
          AND ({mention_expr.split(' AS ')[0]}) IS NOT NULL
          {active_filter}
        ORDER BY dm.review_id, dm.dish_mention_id
    """

    raw = read_df(sql, {"source_system": source_system})
    return standardize_hybrid_mentions(raw, source="database")


# -----------------------------------------------------------------------------
# Standardize mention dataframes
# -----------------------------------------------------------------------------


def standardize_ner_mentions(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    col_map = {
        "review_id": ["review_id"],
        "place_id": ["place_id"],
        "place_name": ["place_name"],
        "district_name": ["district_name"],
        "neighborhood_name": ["neighborhood_name"],
        "mention_text": ["mention_text", "text", "span_text"],
        "start_char": ["start_char", "start", "start_offset"],
        "end_char": ["end_char", "end", "end_offset"],
        "confidence": ["confidence", "score", "probability"],
        "threshold": ["threshold"],
        "review_text": ["review_text", "review_text_raw", "text_full"],
        "model_version": ["model_version"],
    }

    out = pd.DataFrame(index=df.index)
    for target, candidates in col_map.items():
        source_col = choose_column(df, candidates)
        out[target] = df[source_col] if source_col else None

    out["source"] = "ner"
    out["mention_id"] = [f"ner_{i+1}" for i in range(len(out))]
    return enrich_mentions(out)


def standardize_hybrid_mentions(raw: pd.DataFrame, source: str) -> pd.DataFrame:
    df = raw.copy()

    col_map = {
        "review_id": ["review_id"],
        "place_id": ["place_id"],
        "place_name": ["place_name"],
        "district_name": ["district_name"],
        "neighborhood_name": ["neighborhood_name"],
        "dish_id": ["dish_id", "dish_id_v1"],
        "dish_name": ["dish_name", "display_dish_name_es_v1", "dish_display_name", "canonical_dish_name_es_v1"],
        "dish_normalized_name": ["dish_normalized_name", "normalized_dish_name_es_v1", "normalized_dish_name"],
        "mention_text": ["mention_text", "dish_mention_text", "dish_mention_normalized", "mention", "text_mention"],
        "start_char": ["start_char", "start", "start_offset"],
        "end_char": ["end_char", "end", "end_offset"],
        "confidence": ["confidence", "detection_confidence"],
        "detection_method": ["detection_method", "method", "candidate_type"],
        "context_sentence": ["context_sentence", "sentence_context", "window_context"],
        "review_text": ["review_text", "review_text_raw", "text"],
        "hybrid_mention_id": ["hybrid_mention_id", "dish_mention_id", "mention_id"],
    }

    out = pd.DataFrame(index=df.index)
    for target, candidates in col_map.items():
        source_col = choose_column(df, candidates)
        out[target] = df[source_col] if source_col else None

    out["source"] = f"hybrid_{source}"
    out["mention_id"] = out["hybrid_mention_id"].fillna("")
    empty_mask = out["mention_id"].astype(str).str.strip().eq("")
    out.loc[empty_mask, "mention_id"] = [f"hybrid_{i+1}" for i in range(empty_mask.sum())]

    return enrich_mentions(out)


def enrich_mentions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in ["review_id", "place_id", "place_name", "district_name", "neighborhood_name", "mention_text"]:
        if col not in out.columns:
            out[col] = None

    out["review_id"] = out["review_id"].astype(str)
    out["place_id"] = out["place_id"].astype(str)
    out["mention_text"] = out["mention_text"].fillna("").astype(str).str.strip()
    out = out[out["mention_text"].str.len() > 0].copy()

    out["mention_norm"] = out["mention_text"].map(normalize_text)
    out["mention_word_count"] = out["mention_text"].map(word_count)
    out["is_compound"] = out["mention_text"].map(is_compound)
    out["is_generic_exact"] = out["mention_text"].map(is_generic)
    out["ends_with_connector"] = out["mention_text"].map(ends_badly)
    out["start_char"] = safe_to_numeric(out["start_char"]) if "start_char" in out.columns else pd.NA
    out["end_char"] = safe_to_numeric(out["end_char"]) if "end_char" in out.columns else pd.NA
    out["confidence"] = safe_to_numeric(out["confidence"]) if "confidence" in out.columns else pd.NA

    # Dedup exact within each extractor for fair comparison.
    out["dedup_key"] = (
        out["review_id"].astype(str)
        + "||" + out["mention_norm"].astype(str)
        + "||" + out["start_char"].fillna(-1).astype(int).astype(str)
        + "||" + out["end_char"].fillna(-1).astype(int).astype(str)
    )

    return out.reset_index(drop=True)


# -----------------------------------------------------------------------------
# Matching logic
# -----------------------------------------------------------------------------


def overlap_ratio(a_start: Any, a_end: Any, b_start: Any, b_end: Any) -> float:
    try:
        a0, a1, b0, b1 = int(a_start), int(a_end), int(b_start), int(b_end)
    except Exception:
        return 0.0
    if a1 <= a0 or b1 <= b0:
        return 0.0
    inter = max(0, min(a1, b1) - max(a0, b0))
    denom = max(a1 - a0, b1 - b0)
    if denom <= 0:
        return 0.0
    return inter / denom


def text_match_score(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) >= 3 and len(b) >= 3 and (a in b or b in a):
        return 0.90
    return SequenceMatcher(None, a, b).ratio()


def build_matches(
    hybrid_df: pd.DataFrame,
    ner_df: pd.DataFrame,
    fuzzy_threshold: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    hybrid_by_review: dict[str, list[int]] = defaultdict(list)
    ner_by_review: dict[str, list[int]] = defaultdict(list)

    for idx, review_id in hybrid_df["review_id"].items():
        hybrid_by_review[str(review_id)].append(idx)
    for idx, review_id in ner_df["review_id"].items():
        ner_by_review[str(review_id)].append(idx)

    candidate_rows: list[dict[str, Any]] = []

    common_reviews = sorted(set(hybrid_by_review) & set(ner_by_review))
    for review_id in common_reviews:
        for h_idx in hybrid_by_review[review_id]:
            h = hybrid_df.loc[h_idx]
            for n_idx in ner_by_review[review_id]:
                n = ner_df.loc[n_idx]
                txt_score = text_match_score(str(h["mention_norm"]), str(n["mention_norm"]))
                span_score = overlap_ratio(
                    h.get("start_char"),
                    h.get("end_char"),
                    n.get("start_char"),
                    n.get("end_char"),
                )

                match_type = None
                if h["mention_norm"] == n["mention_norm"]:
                    match_type = "exact_text"
                elif span_score >= 0.75:
                    match_type = "span_overlap"
                elif txt_score >= fuzzy_threshold:
                    match_type = "fuzzy_text"

                if match_type:
                    # Primary score favours exact text; span is secondary because hybrid offsets may be absent.
                    combined_score = max(txt_score, span_score * 0.95)
                    candidate_rows.append({
                        "review_id": review_id,
                        "hybrid_index": int(h_idx),
                        "ner_index": int(n_idx),
                        "match_type": match_type,
                        "text_score": round(float(txt_score), 5),
                        "span_overlap": round(float(span_score), 5),
                        "combined_score": round(float(combined_score), 5),
                    })

    candidates = pd.DataFrame(candidate_rows)
    if candidates.empty:
        return pd.DataFrame(), hybrid_df.copy(), ner_df.copy()

    # Greedy one-to-one matching by best score.
    candidates = candidates.sort_values(
        ["combined_score", "text_score", "span_overlap"],
        ascending=[False, False, False],
    )

    used_h: set[int] = set()
    used_n: set[int] = set()
    final_rows: list[dict[str, Any]] = []

    for row in candidates.to_dict(orient="records"):
        h_idx = int(row["hybrid_index"])
        n_idx = int(row["ner_index"])
        if h_idx in used_h or n_idx in used_n:
            continue
        used_h.add(h_idx)
        used_n.add(n_idx)
        final_rows.append(row)

    matches = pd.DataFrame(final_rows)

    matched_rows = []
    for row in matches.to_dict(orient="records"):
        h = hybrid_df.loc[int(row["hybrid_index"])]
        n = ner_df.loc[int(row["ner_index"])]
        matched_rows.append({
            **{f"hybrid_{c}": h.get(c) for c in hybrid_df.columns if c not in ["dedup_key"]},
            **{f"ner_{c}": n.get(c) for c in ner_df.columns if c not in ["dedup_key"]},
            "match_type": row["match_type"],
            "text_score": row["text_score"],
            "span_overlap": row["span_overlap"],
            "combined_score": row["combined_score"],
        })

    matched_df = pd.DataFrame(matched_rows)
    hybrid_only = hybrid_df.loc[~hybrid_df.index.isin(used_h)].copy().reset_index(drop=True)
    ner_only = ner_df.loc[~ner_df.index.isin(used_n)].copy().reset_index(drop=True)

    return matched_df, hybrid_only, ner_only


# -----------------------------------------------------------------------------
# Aggregations and recommendations
# -----------------------------------------------------------------------------


def review_level_comparison(hybrid_df: pd.DataFrame, ner_df: pd.DataFrame, matched_df: pd.DataFrame) -> pd.DataFrame:
    hybrid_counts = hybrid_df.groupby("review_id").agg(
        hybrid_mentions=("mention_norm", "count"),
        hybrid_unique_mentions=("mention_norm", "nunique"),
    ).reset_index()
    ner_counts = ner_df.groupby("review_id").agg(
        ner_mentions=("mention_norm", "count"),
        ner_unique_mentions=("mention_norm", "nunique"),
    ).reset_index()

    if not matched_df.empty:
        matched_counts = matched_df.groupby("hybrid_review_id").agg(
            matched_mentions=("match_type", "count"),
        ).reset_index().rename(columns={"hybrid_review_id": "review_id"})
    else:
        matched_counts = pd.DataFrame(columns=["review_id", "matched_mentions"])

    all_reviews = pd.DataFrame({
        "review_id": sorted(set(hybrid_df["review_id"]) | set(ner_df["review_id"]))
    })
    out = all_reviews.merge(hybrid_counts, on="review_id", how="left")
    out = out.merge(ner_counts, on="review_id", how="left")
    out = out.merge(matched_counts, on="review_id", how="left")

    for col in ["hybrid_mentions", "hybrid_unique_mentions", "ner_mentions", "ner_unique_mentions", "matched_mentions"]:
        out[col] = out[col].fillna(0).astype(int)

    out["mention_count_delta_ner_minus_hybrid"] = out["ner_mentions"] - out["hybrid_mentions"]
    out["has_hybrid"] = out["hybrid_mentions"] > 0
    out["has_ner"] = out["ner_mentions"] > 0
    out["has_both"] = out["has_hybrid"] & out["has_ner"]
    out["only_hybrid"] = out["has_hybrid"] & ~out["has_ner"]
    out["only_ner"] = out["has_ner"] & ~out["has_hybrid"]

    denom = (out["hybrid_unique_mentions"] + out["ner_unique_mentions"] - out["matched_mentions"]).replace(0, pd.NA)
    out["review_jaccard_approx"] = (out["matched_mentions"] / denom).fillna(0).round(5)

    return out.sort_values(["mention_count_delta_ner_minus_hybrid", "ner_mentions"], ascending=[False, False])


def mention_text_comparison(hybrid_df: pd.DataFrame, ner_df: pd.DataFrame) -> pd.DataFrame:
    h_counts = hybrid_df.groupby("mention_norm").agg(
        hybrid_count=("mention_norm", "count"),
        hybrid_reviews=("review_id", "nunique"),
        hybrid_example=("mention_text", "first"),
    ).reset_index()
    n_counts = ner_df.groupby("mention_norm").agg(
        ner_count=("mention_norm", "count"),
        ner_reviews=("review_id", "nunique"),
        ner_example=("mention_text", "first"),
    ).reset_index()

    out = h_counts.merge(n_counts, on="mention_norm", how="outer")
    for col in ["hybrid_count", "hybrid_reviews", "ner_count", "ner_reviews"]:
        out[col] = out[col].fillna(0).astype(int)
    out["count_delta_ner_minus_hybrid"] = out["ner_count"] - out["hybrid_count"]
    out["review_delta_ner_minus_hybrid"] = out["ner_reviews"] - out["hybrid_reviews"]
    out["mention_display"] = out["ner_example"].fillna(out["hybrid_example"])
    out["is_compound"] = out["mention_display"].map(is_compound)
    out["is_generic_exact"] = out["mention_display"].map(is_generic)

    return out.sort_values(["count_delta_ner_minus_hybrid", "ner_count"], ascending=[False, False])


def candidate_compound_cases(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    cols = [
        "review_id", "place_id", "place_name", "district_name", "neighborhood_name",
        "mention_text", "mention_norm", "start_char", "end_char", "confidence", "context_sentence",
        "review_text",
    ]
    available = [c for c in cols if c in df.columns]
    out = df[df["is_compound"]].copy()
    out["source_name"] = source_name
    out["word_count"] = out["mention_word_count"]
    return out[available + ["source_name", "word_count"]].sort_values(["word_count", "mention_text"], ascending=[False, True])


def build_recommendations(summary: dict[str, Any]) -> str:
    c = summary["counts"]
    q = summary["quality"]

    lines = [
        "# Hybrid vs NER comparison - Recommended next steps",
        "",
        "## Executive read",
        "",
        f"- Hybrid mentions: **{c['hybrid_mentions']}**.",
        f"- NER mentions: **{c['ner_mentions']}**.",
        f"- Matched mentions: **{c['matched_mentions']}**.",
        f"- NER-only mentions: **{c['ner_only_mentions']}**.",
        f"- Hybrid-only mentions: **{c['hybrid_only_mentions']}**.",
        f"- Approx mention-level overlap: **{q['mention_overlap_rate_pct']}%**.",
        "",
        "## Interpretation",
        "",
    ]

    if q["mention_overlap_rate_pct"] >= 70:
        lines.append("The NER model is broadly aligned with the hybrid extractor and can be considered a strong candidate for IA v2.")
    elif q["mention_overlap_rate_pct"] >= 45:
        lines.append("The NER model overlaps moderately with the hybrid extractor. It should probably be used as a complementary extractor first, not as a direct replacement.")
    else:
        lines.append("The NER model diverges strongly from the hybrid extractor. Review NER-only and hybrid-only cases before downstream use.")

    lines += [
        "",
        "## Recommended IA v2 strategy",
        "",
        "1. Use NER v1.2 as an additional mention source, not an immediate full replacement.",
        "2. Keep hybrid mentions that are high-confidence or have known curated dish aliases.",
        "3. Add NER-only compound mentions to the normalization review queue.",
        "4. Deduplicate downstream by `review_id + normalized mention text + span overlap`.",
        "5. Run dish normalization/entity linking over NER mentions before sentiment and ranking.",
        "6. Compare the final ranking produced by hybrid-only vs hybrid+NER before loading IA v2 into PostgreSQL.",
        "",
        "## Files to inspect first",
        "",
        "- `ner_only_mentions.csv`: potential new discoveries and possible false positives.",
        "- `hybrid_only_mentions.csv`: possible misses by the NER model.",
        "- `ner_only_compound_candidates.csv`: likely useful additions for better compound dish detection.",
        "- `top_mentions_comparison.csv`: terms whose frequency changed the most.",
        "",
    ]

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Sevilla hybrid dish mentions against NER v1.2 mentions.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--source-system", default=DEFAULT_SOURCE_SYSTEM)
    parser.add_argument("--ner-path", type=Path, default=DEFAULT_NER_PATH)
    parser.add_argument("--hybrid-path", type=Path, default=None, help="Optional hybrid mentions CSV/JSONL. If omitted, load from PostgreSQL.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fuzzy-threshold", type=float, default=0.86)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--no-review-text", action="store_true", help="Drop review_text from exported CSVs to reduce sensitive text output.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print_section("1. Loading NER mentions")
    ner_raw = load_table_file(args.ner_path)
    ner_df = standardize_ner_mentions(ner_raw)
    ner_duplicate_count = int(ner_df.duplicated("dedup_key").sum())
    ner_df = ner_df.drop_duplicates("dedup_key").reset_index(drop=True)
    print(f"NER mentions: {len(ner_df)} (removed duplicates: {ner_duplicate_count})")

    print_section("2. Loading hybrid mentions")
    if args.hybrid_path is not None:
        hybrid_df = load_hybrid_from_file(args.hybrid_path)
        hybrid_source = str(args.hybrid_path)
    else:
        hybrid_df = load_hybrid_from_db(args.schema, args.source_system)
        hybrid_source = "database"
    hybrid_duplicate_count = int(hybrid_df.duplicated("dedup_key").sum())
    hybrid_df = hybrid_df.drop_duplicates("dedup_key").reset_index(drop=True)
    print(f"Hybrid mentions: {len(hybrid_df)} (removed duplicates: {hybrid_duplicate_count})")

    if args.no_review_text:
        for df in [ner_df, hybrid_df]:
            if "review_text" in df.columns:
                df.drop(columns=["review_text"], inplace=True)

    print_section("3. Matching mentions")
    matched_df, hybrid_only_df, ner_only_df = build_matches(
        hybrid_df=hybrid_df,
        ner_df=ner_df,
        fuzzy_threshold=args.fuzzy_threshold,
    )
    print(f"Matched: {len(matched_df)}")
    print(f"Hybrid only: {len(hybrid_only_df)}")
    print(f"NER only: {len(ner_only_df)}")

    print_section("4. Building comparison tables")
    review_cmp_df = review_level_comparison(hybrid_df, ner_df, matched_df)
    mention_cmp_df = mention_text_comparison(hybrid_df, ner_df)
    ner_only_compounds_df = candidate_compound_cases(ner_only_df, "ner_only")
    hybrid_only_compounds_df = candidate_compound_cases(hybrid_only_df, "hybrid_only")

    # Sort high-value NER-only cases first.
    if not ner_only_df.empty:
        ner_only_df = ner_only_df.sort_values(
            ["is_compound", "confidence", "mention_word_count", "mention_text"],
            ascending=[False, False, False, True],
        ).reset_index(drop=True)
    if not hybrid_only_df.empty:
        hybrid_only_df = hybrid_only_df.sort_values(
            ["is_compound", "mention_word_count", "mention_text"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    print_section("5. Saving artifacts")
    matched_path = output_dir / "matched_mentions.csv"
    hybrid_only_path = output_dir / "hybrid_only_mentions.csv"
    ner_only_path = output_dir / "ner_only_mentions.csv"
    review_cmp_path = output_dir / "hybrid_vs_ner_review_level_comparison.csv"
    mention_cmp_path = output_dir / "hybrid_vs_ner_mention_text_comparison.csv"
    top_cmp_path = output_dir / "top_mentions_comparison.csv"
    ner_compound_path = output_dir / "ner_only_compound_candidates.csv"
    hybrid_compound_path = output_dir / "hybrid_only_compound_candidates.csv"
    summary_path = output_dir / "hybrid_vs_ner_summary.json"
    recommendations_path = output_dir / "recommended_next_steps.md"

    matched_df.to_csv(matched_path, index=False, encoding="utf-8")
    hybrid_only_df.to_csv(hybrid_only_path, index=False, encoding="utf-8")
    ner_only_df.to_csv(ner_only_path, index=False, encoding="utf-8")
    review_cmp_df.to_csv(review_cmp_path, index=False, encoding="utf-8")
    mention_cmp_df.to_csv(mention_cmp_path, index=False, encoding="utf-8")
    mention_cmp_df.head(200).to_csv(top_cmp_path, index=False, encoding="utf-8")
    ner_only_compounds_df.to_csv(ner_compound_path, index=False, encoding="utf-8")
    hybrid_only_compounds_df.to_csv(hybrid_compound_path, index=False, encoding="utf-8")

    matched_count = int(len(matched_df))
    hybrid_count = int(len(hybrid_df))
    ner_count = int(len(ner_df))
    union_count = hybrid_count + ner_count - matched_count
    overlap_rate = round(float(matched_count / union_count * 100), 2) if union_count else 0.0

    match_type_counts = matched_df["match_type"].value_counts().to_dict() if not matched_df.empty else {}

    review_counts = {
        "hybrid_reviews_with_mentions": int(hybrid_df["review_id"].nunique()),
        "ner_reviews_with_mentions": int(ner_df["review_id"].nunique()),
        "reviews_with_both": int(review_cmp_df["has_both"].sum()) if not review_cmp_df.empty else 0,
        "reviews_only_hybrid": int(review_cmp_df["only_hybrid"].sum()) if not review_cmp_df.empty else 0,
        "reviews_only_ner": int(review_cmp_df["only_ner"].sum()) if not review_cmp_df.empty else 0,
    }

    quality = {
        "mention_overlap_rate_pct": overlap_rate,
        "ner_only_compound_mentions": int(ner_only_df["is_compound"].sum()) if not ner_only_df.empty else 0,
        "hybrid_only_compound_mentions": int(hybrid_only_df["is_compound"].sum()) if not hybrid_only_df.empty else 0,
        "ner_only_generic_exact_mentions": int(ner_only_df["is_generic_exact"].sum()) if not ner_only_df.empty else 0,
        "hybrid_only_generic_exact_mentions": int(hybrid_only_df["is_generic_exact"].sum()) if not hybrid_only_df.empty else 0,
        "ner_only_bad_endings": int(ner_only_df["ends_with_connector"].sum()) if not ner_only_df.empty else 0,
        "hybrid_only_bad_endings": int(hybrid_only_df["ends_with_connector"].sum()) if not hybrid_only_df.empty else 0,
    }

    top_changes = mention_cmp_df[[
        "mention_norm", "mention_display", "hybrid_count", "ner_count", "count_delta_ner_minus_hybrid",
        "hybrid_reviews", "ner_reviews", "is_compound", "is_generic_exact",
    ]].head(30).to_dict(orient="records")

    summary = {
        "script": "compare_sevilla_hybrid_vs_ner_mentions",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "hybrid_source": hybrid_source,
            "ner_path": str(args.ner_path),
            "schema": args.schema,
            "source_system": args.source_system,
            "fuzzy_threshold": args.fuzzy_threshold,
            "no_review_text": args.no_review_text,
        },
        "counts": {
            "hybrid_mentions": hybrid_count,
            "ner_mentions": ner_count,
            "matched_mentions": matched_count,
            "hybrid_only_mentions": int(len(hybrid_only_df)),
            "ner_only_mentions": int(len(ner_only_df)),
            "mention_union": int(union_count),
            "hybrid_duplicates_removed": hybrid_duplicate_count,
            "ner_duplicates_removed": ner_duplicate_count,
            **review_counts,
        },
        "quality": quality,
        "match_type_counts": match_type_counts,
        "top_mentions_hybrid": Counter(hybrid_df["mention_norm"]).most_common(30),
        "top_mentions_ner": Counter(ner_df["mention_norm"]).most_common(30),
        "top_frequency_changes": top_changes,
        "checks": {
            "has_hybrid_mentions": bool(hybrid_count > 0),
            "has_ner_mentions": bool(ner_count > 0),
            "has_matches": bool(matched_count > 0),
            "json_summary_exists": True,
            "matched_csv_exists": bool(matched_path.exists()),
            "ner_only_csv_exists": bool(ner_only_path.exists()),
            "hybrid_only_csv_exists": bool(hybrid_only_path.exists()),
            "review_comparison_csv_exists": bool(review_cmp_path.exists()),
            "mention_comparison_csv_exists": bool(mention_cmp_path.exists()),
        },
        "files": {
            "summary_json": str(summary_path),
            "matched_mentions_csv": str(matched_path),
            "hybrid_only_mentions_csv": str(hybrid_only_path),
            "ner_only_mentions_csv": str(ner_only_path),
            "review_level_comparison_csv": str(review_cmp_path),
            "mention_text_comparison_csv": str(mention_cmp_path),
            "top_mentions_comparison_csv": str(top_cmp_path),
            "ner_only_compound_candidates_csv": str(ner_compound_path),
            "hybrid_only_compound_candidates_csv": str(hybrid_compound_path),
            "recommendations_md": str(recommendations_path),
        },
        "notes": [
            "This comparison is experimental and should guide IA v2 design.",
            "NER and hybrid outputs are compared mostly by review_id + normalized mention text, with fuzzy fallback.",
            "Do not commit outputs containing review_text to Git.",
        ],
    }

    recommendations_md = build_recommendations(summary)
    recommendations_path.write_text(recommendations_md, encoding="utf-8")
    save_json(summary, summary_path)

    print(json.dumps(to_builtin(summary["counts"]), indent=2, ensure_ascii=False))
    print(json.dumps(to_builtin(summary["quality"]), indent=2, ensure_ascii=False))
    print("Output dir:", output_dir)

    if args.strict:
        failed = [k for k, v in summary["checks"].items() if not bool(v)]
        if failed:
            print("Strict mode failed checks:", failed)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
