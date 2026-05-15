"""Run Sevilla dish normalization/entity-linking reranker v1.

This script consumes the Hybrid + NER v2 mention candidate layer and applies the
trained BETO cross-encoder reranker to link each mention to the best dish in the
catalog.

Typical usage from repository root:

python -m scripts.run_sevilla_dish_normalization_reranker_v1 \
  --input-path data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl \
  --model-dir models/sevilla_dish_normalization_reranker_beto_v1 \
  --output-dir data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1 \
  --strict

The output is an experimental IA v2 normalization layer. It should be reviewed
before loading downstream sentiment/ranking tables.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
import torch
from sqlalchemy import create_engine, inspect, text
from transformers import AutoModelForSequenceClassification, AutoTokenizer

PATCH_ID = "normalization_reranker_v1_fast_candidate_index_progress_2026_05_14"
MODEL_VERSION = "sevilla_dish_normalization_reranker_beto_v1"
OUTPUT_VERSION = "sevilla_dish_normalization_reranker_v1"

DEFAULT_INPUT_PATH = Path(
    "data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2/"
    "sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl"
)
DEFAULT_MODEL_DIR = Path("models/sevilla_dish_normalization_reranker_beto_v1")
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1")

# A few generic/low-value exact terms may still be linkable, but should be reviewed.
LOW_VALUE_EXACT = {
    "tapa",
    "tapas",
    "plato",
    "platos",
    "comida",
    "cena",
    "menu",
    "menú",
    "postre",
    "postres",
}

SPAN_CONNECTORS = {
    "de",
    "del",
    "con",
    "en",
    "al",
    "a",
    "y",
    "o",
    "u",
    "para",
    "por",
}


# -----------------------------------------------------------------------------
# JSON / type utilities
# -----------------------------------------------------------------------------

def is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    if isinstance(value, str):
        return value.strip().lower() in {"", "nan", "none", "null", "na", "<na>"}
    return False


def json_default(value: Any) -> Any:
    if isinstance(value, (UUID,)):
        return str(value)
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
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return str(value)
    return str(value)


def to_builtin(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (UUID,)):
        return str(value)
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if math.isnan(float(value)) or math.isinf(float(value)):
            return None
        return float(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, (str, int)):
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


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            safe_row = to_builtin(row)
            f.write(json.dumps(safe_row, ensure_ascii=False, allow_nan=False, default=json_default) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False, default=json_default)


# -----------------------------------------------------------------------------
# Text normalization
# -----------------------------------------------------------------------------

def strip_accents(value: str) -> str:
    value = str(value or "")
    return "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )


def normalize_text(value: Any) -> str:
    text_value = strip_accents(str(value or "").lower())
    text_value = re.sub(r"[^a-z0-9ñ\s]", " ", text_value)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def token_set(value: str) -> set[str]:
    return {t for t in normalize_text(value).split() if t and len(t) > 1}


def token_overlap(a: str, b: str) -> float:
    ta = token_set(a)
    tb = token_set(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), len(tb))


def fuzzy_ratio(a: str, b: str) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def is_compound(text_value: Any) -> bool:
    norm = normalize_text(text_value)
    parts = norm.split()
    return len(parts) >= 2 or any(conn in parts for conn in ["de", "del", "con", "al"])


def is_likely_fragment(text_value: Any) -> bool:
    norm = normalize_text(text_value)
    if not norm:
        return True
    parts = norm.split()
    if len(norm) <= 2:
        return True
    if parts and (parts[0] in SPAN_CONNECTORS or parts[-1] in SPAN_CONNECTORS):
        return True
    # Single short fragments likely created by bad span cuts.
    if len(parts) == 1 and len(norm) <= 4 and norm not in {"pan", "ajo", "pez"}:
        return True
    return False


# -----------------------------------------------------------------------------
# Database/catalog loading
# -----------------------------------------------------------------------------

def build_engine_from_env():
    """Build SQLAlchemy engine using project settings if available, else env vars."""
    try:
        from src.config.settings import settings  # type: ignore

        dsn = (
            f"postgresql+psycopg2://{settings.pguser}:{settings.pgpassword}"
            f"@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
        )
        return create_engine(dsn, future=True, pool_pre_ping=True)
    except Exception:
        pass

    pguser = os.getenv("PGUSER") or os.getenv("POSTGRES_USER") or "postgres"
    pgpassword = os.getenv("PGPASSWORD") or os.getenv("POSTGRES_PASSWORD") or "postgres"
    pghost = os.getenv("PGHOST") or os.getenv("POSTGRES_HOST") or "localhost"
    pgport = os.getenv("PGPORT") or os.getenv("POSTGRES_PORT") or "5433"
    pgdatabase = os.getenv("PGDATABASE") or os.getenv("POSTGRES_DB") or "postgres"

    dsn = f"postgresql+psycopg2://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgdatabase}"
    return create_engine(dsn, future=True, pool_pre_ping=True)


def table_exists(engine, schema: str, table: str) -> bool:
    try:
        return inspect(engine).has_table(table, schema=schema)
    except Exception:
        return False


def get_columns(engine, schema: str, table: str) -> set[str]:
    try:
        return {c["name"] for c in inspect(engine).get_columns(table, schema=schema)}
    except Exception:
        return set()


def find_first(cols: set[str], options: Sequence[str]) -> Optional[str]:
    for option in options:
        if option in cols:
            return option
    return None


@dataclass
class DishCatalog:
    dishes: pd.DataFrame
    aliases: pd.DataFrame
    entries: List[Dict[str, Any]]


def load_catalog_from_database(schema: str) -> DishCatalog:
    engine = build_engine_from_env()

    if not table_exists(engine, schema, "dish"):
        raise RuntimeError(f"No existe la tabla {schema}.dish. No se puede cargar el catálogo.")

    dish_cols = get_columns(engine, schema, "dish")
    alias_cols = get_columns(engine, schema, "dish_alias") if table_exists(engine, schema, "dish_alias") else set()

    dish_id_col = find_first(dish_cols, ["dish_id", "id"])
    display_col = find_first(dish_cols, [
        "display_dish_name_es_v1",
        "display_dish_name_es",
        "dish_display_name",
        "display_name",
        "canonical_dish_name_es_v1",
        "canonical_dish_name_es",
        "canonical_name",
        "name",
    ])
    normalized_col = find_first(dish_cols, [
        "normalized_dish_name_es_v1",
        "normalized_dish_name_es",
        "dish_normalized_name",
        "normalized_name",
        "canonical_dish_name_es_v1",
        "canonical_dish_name_es",
        "name",
    ])
    family_col = find_first(dish_cols, ["dish_family_es_v1", "dish_family_es", "family", "dish_family"])
    group_col = find_first(dish_cols, ["dish_group_es_v1", "dish_group_es", "group", "dish_group"])
    is_active_col = find_first(dish_cols, ["is_active", "active"])

    if not dish_id_col or not display_col:
        raise RuntimeError(f"No se han encontrado columnas mínimas en {schema}.dish: {dish_cols}")

    where = ""
    if is_active_col:
        where = f"WHERE COALESCE({is_active_col}, TRUE) = TRUE"

    query = f'''
        SELECT
            {dish_id_col}::text AS dish_id,
            {display_col}::text AS dish_display_name,
            {normalized_col + '::text' if normalized_col else 'NULL'} AS dish_normalized_name,
            {family_col + '::text' if family_col else 'NULL'} AS dish_family,
            {group_col + '::text' if group_col else 'NULL'} AS dish_group
        FROM "{schema}"."dish"
        {where}
    '''

    with engine.connect() as conn:
        dishes = pd.read_sql_query(text(query), conn)

    aliases = pd.DataFrame(columns=["dish_id", "alias_text", "alias_normalized"])
    if alias_cols:
        alias_dish_id_col = find_first(alias_cols, ["dish_id"])
        alias_text_col = find_first(alias_cols, ["alias_text", "alias", "name", "alias_name", "dish_alias"])
        alias_norm_col = find_first(alias_cols, ["normalized_alias_text", "alias_normalized", "normalized_alias", "normalized_name"])
        alias_active_col = find_first(alias_cols, ["is_active", "active"])

        if alias_dish_id_col and alias_text_col:
            alias_where = ""
            if alias_active_col:
                alias_where = f"WHERE COALESCE({alias_active_col}, TRUE) = TRUE"
            alias_query = f'''
                SELECT
                    {alias_dish_id_col}::text AS dish_id,
                    {alias_text_col}::text AS alias_text,
                    {alias_norm_col + '::text' if alias_norm_col else 'NULL'} AS alias_normalized
                FROM "{schema}"."dish_alias"
                {alias_where}
            '''
            with engine.connect() as conn:
                aliases = pd.read_sql_query(text(alias_query), conn)

    # Build lexical entries. One entry can represent canonical display or alias.
    entries: List[Dict[str, Any]] = []
    dish_map = dishes.set_index("dish_id").to_dict(orient="index") if len(dishes) else {}

    for _, row in dishes.iterrows():
        display = row.get("dish_display_name")
        normalized = row.get("dish_normalized_name") or display
        if is_missing(display):
            continue
        entries.append({
            "dish_id": str(row["dish_id"]),
            "dish_display_name": str(display),
            "dish_normalized_name": normalize_text(normalized),
            "entry_text": str(display),
            "entry_norm": normalize_text(display),
            "entry_type": "canonical",
            "dish_family": row.get("dish_family"),
            "dish_group": row.get("dish_group"),
        })
        if not is_missing(normalized) and normalize_text(normalized) != normalize_text(display):
            entries.append({
                "dish_id": str(row["dish_id"]),
                "dish_display_name": str(display),
                "dish_normalized_name": normalize_text(normalized),
                "entry_text": str(normalized),
                "entry_norm": normalize_text(normalized),
                "entry_type": "normalized",
                "dish_family": row.get("dish_family"),
                "dish_group": row.get("dish_group"),
            })

    for _, row in aliases.iterrows():
        did = str(row.get("dish_id"))
        dish = dish_map.get(did, {})
        alias = row.get("alias_text")
        alias_norm = row.get("alias_normalized") or alias
        if is_missing(alias):
            continue
        entries.append({
            "dish_id": did,
            "dish_display_name": str(dish.get("dish_display_name") or alias),
            "dish_normalized_name": normalize_text(dish.get("dish_normalized_name") or dish.get("dish_display_name") or alias),
            "entry_text": str(alias),
            "entry_norm": normalize_text(alias_norm),
            "entry_type": "alias",
            "dish_family": dish.get("dish_family"),
            "dish_group": dish.get("dish_group"),
        })

    # Dedupe entries by dish + entry norm.
    seen = set()
    unique_entries = []
    for entry in entries:
        key = (entry["dish_id"], entry["entry_norm"])
        if key not in seen and entry["entry_norm"]:
            unique_entries.append(entry)
            seen.add(key)

    return DishCatalog(dishes=dishes, aliases=aliases, entries=unique_entries)


# -----------------------------------------------------------------------------
# Candidate generation
# -----------------------------------------------------------------------------

def lexical_score(mention: str, context: str, entry: Dict[str, Any]) -> float:
    mention_norm = normalize_text(mention)
    context_norm = normalize_text(context)
    entry_norm = entry.get("entry_norm") or normalize_text(entry.get("entry_text", ""))

    if not mention_norm or not entry_norm:
        return 0.0

    score = 0.0

    if mention_norm == entry_norm:
        score += 100.0
    elif mention_norm in entry_norm or entry_norm in mention_norm:
        # Good for plural/singular or compound variations.
        score += 72.0

    score += 45.0 * token_overlap(mention_norm, entry_norm)
    score += 20.0 * fuzzy_ratio(mention_norm, entry_norm)

    if context_norm and entry_norm in context_norm:
        score += 10.0

    if entry.get("entry_type") == "alias":
        score += 2.0

    # Prefer compounds when the mention is compound and the candidate preserves it.
    if is_compound(mention_norm) and is_compound(entry_norm):
        score += 6.0

    return float(score)


def candidate_from_row_if_available(row: pd.Series) -> List[Dict[str, Any]]:
    """Recover existing hybrid/current dish candidates from the unified layer if present."""
    candidates: List[Dict[str, Any]] = []

    possible_prefixes = [
        "hybrid_",
        "current_",
        "selected_",
        "",
    ]

    id_cols = [
        "dish_id_v1", "dish_id", "current_dish_id", "hybrid_dish_id", "selected_dish_id",
        "canonical_dish_id", "normalized_dish_id",
    ]
    name_cols = [
        "display_dish_name_es_v1", "dish_display_name", "current_dish_display_name",
        "hybrid_display_dish_name_es_v1", "selected_dish_name", "canonical_dish_name_es_v1",
        "normalized_dish_name_es_v1", "dish_name",
    ]

    for id_col in id_cols:
        if id_col not in row.index or is_missing(row.get(id_col)):
            continue
        did = str(row.get(id_col))
        name = None
        for name_col in name_cols:
            if name_col in row.index and not is_missing(row.get(name_col)):
                name = str(row.get(name_col))
                break
        if name:
            candidates.append({
                "dish_id": did,
                "dish_display_name": name,
                "dish_normalized_name": normalize_text(name),
                "entry_text": name,
                "entry_norm": normalize_text(name),
                "entry_type": "input_existing",
                "lexical_score": 120.0,
                "candidate_source": "input_existing_dish",
            })

    # Some scripts may store candidate options already.
    for opt_col in ["candidate_dish_options_json", "candidate_options_json", "top_candidates_json"]:
        if opt_col in row.index and not is_missing(row.get(opt_col)):
            parsed = parse_json_list(row.get(opt_col))
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                did = item.get("dish_id") or item.get("candidate_dish_id")
                name = item.get("dish_display_name") or item.get("candidate_dish_name") or item.get("display_name")
                if did and name:
                    candidates.append({
                        "dish_id": str(did),
                        "dish_display_name": str(name),
                        "dish_normalized_name": normalize_text(item.get("dish_normalized_name") or name),
                        "entry_text": str(name),
                        "entry_norm": normalize_text(name),
                        "entry_type": "input_option",
                        "lexical_score": float(item.get("score_hint") or item.get("lexical_score") or 80.0),
                        "candidate_source": "input_candidate_options",
                    })

    return dedupe_candidate_entries(candidates)


def parse_json_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    try:
        text_value = str(value).strip()
        if not text_value or text_value.lower() in {"nan", "none", "null"}:
            return []
        parsed = json.loads(text_value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def dedupe_candidate_entries(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for cand in candidates:
        key = cand.get("dish_id") or f"name::{normalize_text(cand.get('dish_display_name', ''))}"
        if key and key not in seen:
            out.append(cand)
            seen.add(key)
    return out


INDEX_STOP_TOKENS = {
    "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
    "con", "en", "al", "a", "y", "o", "u", "para", "por", "muy", "mas",
    "sin", "sobre", "su", "sus", "mi", "mis", "tu", "tus", "que", "es", "son",
}


def token_variants(token: str) -> set[str]:
    token = normalize_text(token)
    variants = {token} if token else set()
    if len(token) > 4 and token.endswith("es"):
        variants.add(token[:-2])
    if len(token) > 3 and token.endswith("s"):
        variants.add(token[:-1])
    return {v for v in variants if len(v) > 1 and v not in INDEX_STOP_TOKENS}


def build_catalog_candidate_index(catalog: DishCatalog) -> Dict[str, Any]:
    """Build a token/prefix index so candidate generation does not scan all catalog entries.

    The previous implementation compared every mention against every catalog entry
    (roughly 3k x 12k with SequenceMatcher), which can take a very long time on CPU.
    This index reduces scoring to entries sharing at least one meaningful token/prefix.
    """

    token_index: Dict[str, set[int]] = defaultdict(set)
    prefix_index: Dict[str, set[int]] = defaultdict(set)

    for idx, entry in enumerate(catalog.entries):
        entry_norm = entry.get("entry_norm") or normalize_text(entry.get("entry_text", ""))
        toks = [t for t in entry_norm.split() if len(t) > 1 and t not in INDEX_STOP_TOKENS]
        for tok in toks:
            for variant in token_variants(tok):
                token_index[variant].add(idx)
                if len(variant) >= 4:
                    prefix_index[variant[:4]].add(idx)

    return {
        "token_index": token_index,
        "prefix_index": prefix_index,
    }


def lookup_catalog_entry_indices(
    mention: str,
    context: str,
    candidate_index: Optional[Dict[str, Any]],
    max_context_tokens: int = 8,
) -> List[int]:
    if not candidate_index:
        return []

    token_index = candidate_index.get("token_index", {})
    prefix_index = candidate_index.get("prefix_index", {})

    mention_norm = normalize_text(mention)
    context_norm = normalize_text(context)

    mention_tokens = [t for t in mention_norm.split() if len(t) > 1 and t not in INDEX_STOP_TOKENS]

    # Use mention tokens first. If the mention is very short, add a few context tokens
    # as weak anchors, but avoid exploding the candidate pool.
    context_tokens: List[str] = []
    if len(mention_tokens) <= 1 and context_norm:
        for tok in context_norm.split():
            if tok not in mention_tokens and len(tok) > 3 and tok not in INDEX_STOP_TOKENS:
                context_tokens.append(tok)
            if len(context_tokens) >= max_context_tokens:
                break

    lookup_tokens = mention_tokens + context_tokens
    indices: set[int] = set()

    for tok in lookup_tokens:
        for variant in token_variants(tok):
            indices.update(token_index.get(variant, set()))
            if len(variant) >= 4:
                indices.update(prefix_index.get(variant[:4], set()))

    return list(indices)


def generate_candidates_for_row(
    row: pd.Series,
    catalog: DishCatalog,
    top_k: int,
    min_lexical_score: float,
    candidate_index: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    mention = get_mention_text(row)
    context = get_context_text(row)

    candidates = candidate_from_row_if_available(row)

    candidate_indices = lookup_catalog_entry_indices(mention, context, candidate_index)

    # Fallback: if the index finds nothing, do a tiny exact/prefix fallback instead of
    # scanning all catalog entries with fuzzy matching. This keeps the script fast.
    entries_to_score: List[Dict[str, Any]] = []
    if candidate_indices:
        entries_to_score = [catalog.entries[i] for i in candidate_indices]
    else:
        mention_norm = normalize_text(mention)
        if mention_norm:
            for entry in catalog.entries:
                entry_norm = entry.get("entry_norm") or ""
                if mention_norm == entry_norm or (len(mention_norm) >= 4 and mention_norm in entry_norm):
                    entries_to_score.append(entry)

    scored_entries: List[Dict[str, Any]] = []
    for entry in entries_to_score:
        score = lexical_score(mention, context, entry)
        if score >= min_lexical_score:
            scored = dict(entry)
            scored["lexical_score"] = score
            scored["candidate_source"] = f"catalog_{entry.get('entry_type', 'entry')}"
            scored_entries.append(scored)

    scored_entries = sorted(scored_entries, key=lambda x: x.get("lexical_score", 0), reverse=True)
    candidates.extend(scored_entries[: max(top_k * 3, top_k)])

    candidates = dedupe_candidate_entries(candidates)
    candidates = sorted(candidates, key=lambda x: x.get("lexical_score", 0), reverse=True)
    return candidates[:top_k]


# -----------------------------------------------------------------------------
# Model scoring
# -----------------------------------------------------------------------------

def get_mention_text(row: pd.Series) -> str:
    options = [
        "selected_mention_text_v2",
        "selected_mention_text",
        "mention_text",
        "dish_mention_text",
        "ner_mention_text",
        "hybrid_mention_text",
    ]
    for col in options:
        if col in row.index and not is_missing(row.get(col)):
            return str(row.get(col))
    return ""


def get_context_text(row: pd.Series) -> str:
    options = [
        "context_sentence",
        "selected_context_sentence_v2",
        "window_context",
        "review_text",
        "review_text_raw",
        "text",
    ]
    for col in options:
        if col in row.index and not is_missing(row.get(col)):
            return str(row.get(col))
    return ""


def get_place_name(row: pd.Series) -> str:
    for col in ["place_name", "selected_place_name", "hybrid_place_name", "ner_place_name"]:
        if col in row.index and not is_missing(row.get(col)):
            return str(row.get(col))
    return ""


def get_candidate_id(row: pd.Series, idx: int) -> str:
    for col in ["mention_candidate_id_v2", "candidate_id", "mention_id", "selected_mention_id_v2"]:
        if col in row.index and not is_missing(row.get(col)):
            return str(row.get(col))
    return f"mention_candidate_{idx:06d}"


def build_query_text(row: pd.Series) -> str:
    mention = get_mention_text(row).strip()
    context = get_context_text(row).strip()
    place = get_place_name(row).strip()

    parts = [f"Mención: {mention}"]
    if context:
        parts.append(f"Contexto: {context}")
    if place:
        parts.append(f"Local: {place}")
    return " | ".join(parts)


def build_candidate_text(candidate: Dict[str, Any]) -> str:
    display = str(candidate.get("dish_display_name") or "").strip()
    normalized = str(candidate.get("dish_normalized_name") or "").strip()
    if normalized and normalize_text(display) != normalize_text(normalized):
        return f"Plato candidato: {display} | Nombre normalizado: {normalized}"
    return f"Plato candidato: {display}"


@dataclass
class RerankerModel:
    tokenizer: Any
    model: Any
    device: str


def load_reranker(model_dir: Path, device_arg: str = "auto") -> RerankerModel:
    if not model_dir.exists():
        raise FileNotFoundError(f"No existe model-dir: {model_dir}")

    if device_arg == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = device_arg

    tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=True)
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir))
    model.to(device)
    model.eval()
    return RerankerModel(tokenizer=tokenizer, model=model, device=device)


def softmax(logits: torch.Tensor) -> torch.Tensor:
    return torch.softmax(logits, dim=-1)


def score_pairs(
    reranker: RerankerModel,
    text_a: List[str],
    text_b: List[str],
    max_length: int,
    batch_size: int,
) -> List[float]:
    scores: List[float] = []
    tokenizer = reranker.tokenizer
    model = reranker.model
    device = reranker.device

    total_pairs = len(text_a)
    total_batches = math.ceil(total_pairs / max(batch_size, 1))
    start_time = time.time()

    print(
        f"Scoring candidate pairs with reranker: pairs={total_pairs}, "
        f"batch_size={batch_size}, max_length={max_length}, device={device}"
    )

    for batch_idx, start in enumerate(range(0, total_pairs, batch_size), start=1):
        batch_a = text_a[start:start + batch_size]
        batch_b = text_b[start:start + batch_size]
        encoded = tokenizer(
            batch_a,
            batch_b,
            truncation=True,
            max_length=max_length,
            padding=True,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.inference_mode():
            logits = model(**encoded).logits
            probs = softmax(logits)[:, 1].detach().cpu().numpy().tolist()

        scores.extend(float(x) for x in probs)

        if batch_idx == 1 or batch_idx % 20 == 0 or batch_idx == total_batches:
            elapsed = time.time() - start_time
            done_pairs = min(start + batch_size, total_pairs)
            pairs_per_sec = done_pairs / elapsed if elapsed > 0 else 0.0
            remaining_pairs = max(total_pairs - done_pairs, 0)
            eta_sec = remaining_pairs / pairs_per_sec if pairs_per_sec > 0 else 0.0
            print(
                f"  scored {done_pairs}/{total_pairs} pairs "
                f"({batch_idx}/{total_batches} batches) | "
                f"elapsed={elapsed:.1f}s | eta={eta_sec:.1f}s"
            )

    return scores


# -----------------------------------------------------------------------------
# Main normalization
# -----------------------------------------------------------------------------

def normalize_candidates(
    mentions: pd.DataFrame,
    catalog: DishCatalog,
    reranker: RerankerModel,
    args: argparse.Namespace,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    output_rows: List[Dict[str, Any]] = []
    low_conf_rows: List[Dict[str, Any]] = []
    no_candidate_rows: List[Dict[str, Any]] = []

    all_pair_text_a: List[str] = []
    all_pair_text_b: List[str] = []
    pair_refs: List[Tuple[int, int]] = []  # row_idx, candidate_idx
    row_candidates: Dict[int, List[Dict[str, Any]]] = {}
    row_query: Dict[int, str] = {}

    print("Building fast catalog candidate index...")
    candidate_index = build_catalog_candidate_index(catalog)
    print(
        "Candidate index ready:",
        f"tokens={len(candidate_index.get('token_index', {}))}",
        f"prefixes={len(candidate_index.get('prefix_index', {}))}",
    )

    print("Generating candidate dishes...")
    start_candidate_generation = time.time()
    for position, (idx, row) in enumerate(mentions.iterrows(), start=1):
        if position % 250 == 0 or position == len(mentions):
            elapsed = time.time() - start_candidate_generation
            print(f"  generated candidates for {position}/{len(mentions)} rows | elapsed={elapsed:.1f}s")

        candidates = generate_candidates_for_row(
            row,
            catalog=catalog,
            top_k=args.top_k_candidates,
            min_lexical_score=args.min_lexical_score,
            candidate_index=candidate_index,
        )
        row_candidates[idx] = candidates
        query_text = build_query_text(row)
        row_query[idx] = query_text

        if not candidates:
            no_candidate_rows.append({
                "candidate_row_index": idx,
                "mention_candidate_id_v2": get_candidate_id(row, idx),
                "selected_mention_text_v2": get_mention_text(row),
                "context_sentence": get_context_text(row),
                "place_name": get_place_name(row),
                "reason": "no_candidate_generated",
            })
            continue

        for cidx, candidate in enumerate(candidates):
            all_pair_text_a.append(query_text)
            all_pair_text_b.append(build_candidate_text(candidate))
            pair_refs.append((idx, cidx))

    print(f"Candidate pairs to score: {len(all_pair_text_a)}")
    pair_scores = score_pairs(
        reranker,
        all_pair_text_a,
        all_pair_text_b,
        max_length=args.max_length,
        batch_size=args.batch_size,
    ) if all_pair_text_a else []

    # Attach scores.
    for (row_idx, cidx), score in zip(pair_refs, pair_scores):
        row_candidates[row_idx][cidx]["reranker_score"] = float(score)

    print("Selecting best candidate per mention...")
    for idx, row in mentions.iterrows():
        candidates = row_candidates.get(idx, [])
        original = row.to_dict()
        mention_text = get_mention_text(row)
        mention_norm = normalize_text(mention_text)
        strategy = str(row.get("source_strategy_v2") or row.get("source_strategy") or "unknown")

        if not candidates:
            out = dict(original)
            out.update({
                "normalization_version": OUTPUT_VERSION,
                "normalization_model_version": MODEL_VERSION,
                "normalization_status_v1": "no_candidate",
                "normalization_confidence_v1": 0.0,
                "normalized_dish_id_v1": None,
                "normalized_dish_name_v1": None,
                "normalized_dish_display_name_v1": None,
                "normalization_method_v1": "reranker_no_candidate",
                "normalization_needs_manual_review_v1": True,
                "normalization_review_reason_v1": "no_candidate_generated",
                "normalization_top_candidates_json": "[]",
                "ready_for_sentiment_after_normalization_v1": False,
            })
            output_rows.append(out)
            continue

        candidates = sorted(candidates, key=lambda c: c.get("reranker_score", 0.0), reverse=True)
        best = candidates[0]
        second_score = float(candidates[1].get("reranker_score", 0.0)) if len(candidates) > 1 else 0.0
        best_score = float(best.get("reranker_score", 0.0))
        margin = best_score - second_score

        review_reasons: List[str] = []
        needs_review = False

        if best_score < args.accept_threshold:
            needs_review = True
            review_reasons.append("low_reranker_score")
        if margin < args.min_margin and len(candidates) > 1:
            needs_review = True
            review_reasons.append("low_score_margin")
        if strategy == "ner_only":
            # NER-only is useful but still experimental.
            needs_review = True
            review_reasons.append("experimental_ner_only")
        if mention_norm in LOW_VALUE_EXACT:
            needs_review = True
            review_reasons.append("low_value_mention")
        if is_likely_fragment(mention_text):
            needs_review = True
            review_reasons.append("likely_fragment")

        status = "linked"
        if needs_review:
            status = "linked_needs_review"
        if best_score < args.low_confidence_threshold:
            status = "low_confidence"

        top_candidates_for_json = []
        for rank, cand in enumerate(candidates[: args.output_top_k], start=1):
            top_candidates_for_json.append({
                "rank": rank,
                "dish_id": cand.get("dish_id"),
                "dish_display_name": cand.get("dish_display_name"),
                "dish_normalized_name": cand.get("dish_normalized_name"),
                "reranker_score": round(float(cand.get("reranker_score", 0.0)), 6),
                "lexical_score": round(float(cand.get("lexical_score", 0.0)), 4),
                "candidate_source": cand.get("candidate_source"),
                "entry_type": cand.get("entry_type"),
            })

        out = dict(original)
        out.update({
            "normalization_version": OUTPUT_VERSION,
            "normalization_model_version": MODEL_VERSION,
            "normalization_status_v1": status,
            "normalization_confidence_v1": round(best_score, 6),
            "normalization_second_best_score_v1": round(second_score, 6),
            "normalization_score_margin_v1": round(margin, 6),
            "normalized_dish_id_v1": best.get("dish_id"),
            "normalized_dish_name_v1": best.get("dish_normalized_name") or normalize_text(best.get("dish_display_name", "")),
            "normalized_dish_display_name_v1": best.get("dish_display_name"),
            "normalization_candidate_source_v1": best.get("candidate_source"),
            "normalization_method_v1": "beto_cross_encoder_reranker",
            "normalization_needs_manual_review_v1": bool(needs_review or status == "low_confidence"),
            "normalization_review_reason_v1": ";".join(review_reasons) if review_reasons else "none",
            "normalization_candidate_count_v1": len(candidates),
            "normalization_top_candidates_json": json.dumps(top_candidates_for_json, ensure_ascii=False),
            "ready_for_sentiment_after_normalization_v1": bool(status == "linked" or status == "linked_needs_review"),
        })
        output_rows.append(out)

        if out["normalization_needs_manual_review_v1"] or status == "low_confidence":
            low_conf_rows.append({
                "mention_candidate_id_v2": get_candidate_id(row, idx),
                "source_strategy_v2": strategy,
                "selected_mention_text_v2": mention_text,
                "context_sentence": get_context_text(row),
                "place_name": get_place_name(row),
                "normalization_status_v1": status,
                "normalization_confidence_v1": best_score,
                "normalization_score_margin_v1": margin,
                "normalized_dish_id_v1": best.get("dish_id"),
                "normalized_dish_display_name_v1": best.get("dish_display_name"),
                "normalization_review_reason_v1": out["normalization_review_reason_v1"],
                "normalization_top_candidates_json": out["normalization_top_candidates_json"],
            })

    return pd.DataFrame(output_rows), pd.DataFrame(low_conf_rows), pd.DataFrame(no_candidate_rows)


# -----------------------------------------------------------------------------
# CLI and reporting
# -----------------------------------------------------------------------------

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sevilla dish normalization reranker v1.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--schema", default="hidden_gems")
    parser.add_argument("--top-k-candidates", type=int, default=12)
    parser.add_argument("--output-top-k", type=int, default=5)
    parser.add_argument("--min-lexical-score", type=float, default=18.0)
    parser.add_argument("--accept-threshold", type=float, default=0.70)
    parser.add_argument("--low-confidence-threshold", type=float, default=0.50)
    parser.add_argument("--min-margin", type=float, default=0.08)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args(argv)


def paths_for(output_dir: Path) -> Dict[str, Path]:
    return {
        "normalized_csv": output_dir / "sevilla_dish_mentions_normalized_reranker_v1.csv",
        "normalized_jsonl": output_dir / "sevilla_dish_mentions_normalized_reranker_v1.jsonl",
        "low_confidence_csv": output_dir / "sevilla_dish_normalization_low_confidence_v1.csv",
        "no_candidate_csv": output_dir / "sevilla_dish_normalization_no_candidate_v1.csv",
        "summary_json": output_dir / "sevilla_dish_normalization_summary_v1.json",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }


def write_recommendations(path: Path, summary: Dict[str, Any]) -> None:
    counts = summary.get("counts", {})
    status_counts = summary.get("status_counts", {})
    text_md = f"""# Sevilla dish normalization reranker v1 - Recommended next steps

## Executive read

- Input mention candidates: **{counts.get('input_rows', 0)}**.
- Normalized rows: **{counts.get('normalized_rows', 0)}**.
- Linked rows: **{status_counts.get('linked', 0)}**.
- Linked but needs review: **{status_counts.get('linked_needs_review', 0)}**.
- Low confidence rows: **{status_counts.get('low_confidence', 0)}**.
- No-candidate rows: **{status_counts.get('no_candidate', 0)}**.

## Recommended strategy

1. Use rows with `normalization_status_v1 = linked` as the cleanest input for sentiment v2.
2. Keep `linked_needs_review` rows available, but mark them as lower-confidence downstream.
3. Review `sevilla_dish_normalization_low_confidence_v1.csv` before loading any low-confidence row into ranking.
4. Pay special attention to `ner_only` rows and rows with low score margin.
5. After sentiment v2, compare final ranking v1 vs v2 before loading results into PostgreSQL.

## Important note

This is an intermediate IA v2 artifact. It should not be treated as a final production dish mention table.
"""
    path.write_text(text_md, encoding="utf-8")


def main(argv: Optional[Sequence[str]] = None) -> int:
    started = time.time()
    args = parse_args(argv)
    out_paths = paths_for(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Patch: {PATCH_ID}")
    print("Loading input mention candidates...")
    if not args.input_path.exists():
        raise FileNotFoundError(f"No existe input-path: {args.input_path}")

    mentions = read_jsonl(args.input_path) if args.input_path.suffix.lower() == ".jsonl" else pd.read_csv(args.input_path)
    if args.max_rows:
        mentions = mentions.head(args.max_rows).copy()

    print(f"Input rows: {len(mentions)}")

    print("Loading dish catalog...")
    catalog = load_catalog_from_database(args.schema)
    print(f"Catalog dishes: {len(catalog.dishes)}")
    print(f"Catalog aliases: {len(catalog.aliases)}")
    print(f"Catalog lexical entries: {len(catalog.entries)}")

    print("Loading reranker model...")
    reranker = load_reranker(args.model_dir, args.device)
    print(f"Device: {reranker.device}")

    normalized, low_confidence, no_candidate = normalize_candidates(mentions, catalog, reranker, args)

    print("Writing outputs...")
    normalized.to_csv(out_paths["normalized_csv"], index=False, encoding="utf-8")
    write_jsonl(out_paths["normalized_jsonl"], normalized.to_dict(orient="records"))

    low_confidence.to_csv(out_paths["low_confidence_csv"], index=False, encoding="utf-8")
    no_candidate.to_csv(out_paths["no_candidate_csv"], index=False, encoding="utf-8")

    status_counts = normalized["normalization_status_v1"].value_counts(dropna=False).to_dict() if len(normalized) else {}
    strategy_counts = normalized["source_strategy_v2"].value_counts(dropna=False).to_dict() if "source_strategy_v2" in normalized.columns else {}
    review_reason_counts = normalized["normalization_review_reason_v1"].value_counts(dropna=False).head(30).to_dict() if len(normalized) else {}

    checks = {
        "input_exists": args.input_path.exists(),
        "model_dir_exists": args.model_dir.exists(),
        "has_input_rows": len(mentions) > 0,
        "has_catalog_entries": len(catalog.entries) > 0,
        "has_normalized_rows": len(normalized) > 0,
        "all_rows_have_status": bool(normalized["normalization_status_v1"].notna().all()) if len(normalized) else False,
        "all_linked_have_dish_id": bool(
            normalized.loc[
                normalized["normalization_status_v1"].isin(["linked", "linked_needs_review"]),
                "normalized_dish_id_v1",
            ].notna().all()
        ) if len(normalized) else False,
        "csv_exists": out_paths["normalized_csv"].exists(),
        "jsonl_exists": out_paths["normalized_jsonl"].exists(),
        "low_confidence_csv_exists": out_paths["low_confidence_csv"].exists(),
    }

    errors: List[str] = []
    warnings: List[str] = []

    if status_counts.get("no_candidate", 0) > 0:
        warnings.append("Some rows had no candidate dish generated.")
    if status_counts.get("low_confidence", 0) > 0:
        warnings.append("Some rows are low-confidence and should be reviewed before downstream use.")
    if status_counts.get("linked_needs_review", 0) > 0:
        warnings.append("Some linked rows need manual review or lower downstream weight.")

    if args.strict:
        strict_checks = [
            checks["has_input_rows"],
            checks["has_catalog_entries"],
            checks["has_normalized_rows"],
            checks["all_rows_have_status"],
            checks["csv_exists"],
            checks["jsonl_exists"],
        ]
        if not all(strict_checks):
            errors.append("Strict checks failed. See checks block.")

    summary = {
        "script": "run_sevilla_dish_normalization_reranker_v1",
        "patch_id": PATCH_ID,
        "version": OUTPUT_VERSION,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.time() - started, 3),
        "inputs": {
            "input_path": str(args.input_path),
            "model_dir": str(args.model_dir),
            "schema": args.schema,
            "top_k_candidates": args.top_k_candidates,
            "accept_threshold": args.accept_threshold,
            "low_confidence_threshold": args.low_confidence_threshold,
            "min_margin": args.min_margin,
            "device": reranker.device,
        },
        "counts": {
            "input_rows": int(len(mentions)),
            "normalized_rows": int(len(normalized)),
            "low_confidence_or_review_rows": int(len(low_confidence)),
            "no_candidate_rows": int(len(no_candidate)),
            "catalog_dishes": int(len(catalog.dishes)),
            "catalog_aliases": int(len(catalog.aliases)),
            "catalog_entries": int(len(catalog.entries)),
            "ready_for_sentiment": int(normalized["ready_for_sentiment_after_normalization_v1"].sum()) if len(normalized) else 0,
            "needs_manual_review": int(normalized["normalization_needs_manual_review_v1"].sum()) if len(normalized) else 0,
        },
        "status_counts": status_counts,
        "strategy_counts": strategy_counts,
        "review_reason_counts_top": review_reason_counts,
        "score_summary": normalized["normalization_confidence_v1"].describe().round(6).to_dict() if len(normalized) else {},
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "files": {k: str(v) for k, v in out_paths.items()},
        "notes": [
            "This is an experimental IA v2 normalization layer.",
            "Use linked rows for sentiment v2; review low-confidence and NER-only rows before ranking.",
            "Do not commit outputs containing review text to Git.",
        ],
    }

    write_json(out_paths["summary_json"], summary)
    write_recommendations(out_paths["recommendations_md"], summary)

    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, default=json_default))

    if errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
