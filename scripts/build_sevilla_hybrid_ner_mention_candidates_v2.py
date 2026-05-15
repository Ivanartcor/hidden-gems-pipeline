"""Build Sevilla Hybrid + NER mention candidates for IA v2.

This script creates an intermediate, auditable mention layer that combines:

1. Hybrid v1 dish mentions already loaded in PostgreSQL.
2. NER v1.2 dish mentions exported by ``run_sevilla_dish_ner_inference.py``.

The output is NOT meant to be loaded directly as final dish mentions. It is a
candidate layer for the next IA v2 phases:

    hybrid + ner candidates -> dish normalization/entity linking -> sentiment -> ranking v2

Typical usage from repository root:

    python -m scripts.build_sevilla_hybrid_ner_mention_candidates_v2 `
      --ner-path data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/sevilla_dish_mentions_ner_model_v1_2.jsonl `
      --output-dir data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2 `
      --strict

The script keeps all source information, deduplicates by review and mention, and
marks which rows require normalization/manual review.

Patch note: JSON exports defensively serialize UUID/date/Decimal/pandas values.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from decimal import Decimal
from uuid import UUID
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text


SCRIPT_NAME = "build_sevilla_hybrid_ner_mention_candidates_v2_uuid_safe"
PATCH_ID = "uuid_safe_json_export_2026_05_12"
VERSION = "sevilla_hybrid_ner_mentions_v2"

DEFAULT_NER_PATH = (
    "data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned/"
    "sevilla_dish_mentions_ner_model_v1_2.jsonl"
)
DEFAULT_OUTPUT_DIR = "data/artifacts/ai/sevilla/model_inference/hybrid_ner_v2"

GENERIC_TERMS = {
    "comida", "cena", "almuerzo", "desayuno", "servicio", "ambiente",
    "precio", "local", "restaurante", "bar", "sitio", "mesa", "carta",
    "menu", "menú", "plato", "platos", "tapa", "tapas", "racion", "ración",
}

LOW_VALUE_SINGLE_TERMS = {
    "queso", "whisky", "ajillo", "adobo", "frito", "frita", "alioli",
    "patatas", "ensalada", "setas", "iberica", "ibérica",
}

COMPOUND_MARKERS = (
    " de ", " del ", " al ", " a la ", " a las ", " con ", " en ", " a ",
)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def to_builtin(value: Any) -> Any:
    """Recursively convert values to strict JSON-serializable Python types.

    This is intentionally defensive because pandas rows coming from PostgreSQL
    may contain UUID, Decimal, Timestamp, date/datetime, pd.NA, NaN or other
    driver-specific objects. JSONL export must never fail because of those.
    """
    if value is None:
        return None

    if isinstance(value, (str, int, bool)):
        return value

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)

    if isinstance(value, (pd.Timestamp, datetime, date)):
        if pd.isna(value):
            return None
        return value.isoformat()

    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]

    # numpy scalar / pandas scalar
    if hasattr(value, "item"):
        try:
            return to_builtin(value.item())
        except Exception:
            pass

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    # Last-resort fallback for driver-specific types.
    return str(value)


def json_default(value: Any) -> Any:
    return to_builtin(value)


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(
            to_builtin(payload),
            f,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
            default=json_default,
        )


def read_jsonl(path: Path) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            # UUID_SAFE_PATCH: do not allow JSON export to fail on UUID/Timestamp/Decimal/pandas objects.
            safe_row = to_builtin(row)
            f.write(
                json.dumps(
                    safe_row,
                    ensure_ascii=False,
                    allow_nan=False,
                    default=json_default,
                )
                + "\n"
            )


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    s = str(value).strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9ñü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return int(value)
    except Exception:
        return None


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    try:
        return float(value)
    except Exception:
        return None


def stable_id(*parts: Any, prefix: str = "hgnm") -> str:
    raw = "||".join(safe_str(p) for p in parts)
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def fuzzy_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def span_overlap_ratio(a_start: Any, a_end: Any, b_start: Any, b_end: Any) -> float:
    a_s, a_e, b_s, b_e = map(safe_int, [a_start, a_end, b_start, b_end])
    if a_s is None or a_e is None or b_s is None or b_e is None:
        return 0.0
    if a_e <= a_s or b_e <= b_s:
        return 0.0
    inter = max(0, min(a_e, b_e) - max(a_s, b_s))
    union = max(a_e, b_e) - min(a_s, b_s)
    return inter / union if union else 0.0


def is_compound_mention(norm_text: str) -> bool:
    if not norm_text:
        return False
    words = norm_text.split()
    if len(words) >= 3:
        return True
    padded = f" {norm_text} "
    return any(marker in padded for marker in COMPOUND_MARKERS)


def is_generic_exact(norm_text: str) -> bool:
    return norm_text in {normalize_text(x) for x in GENERIC_TERMS}


def is_low_value_single(norm_text: str) -> bool:
    return norm_text in {normalize_text(x) for x in LOW_VALUE_SINGLE_TERMS}


def likely_fragment(norm_text: str) -> bool:
    if not norm_text:
        return True
    if len(norm_text) <= 2:
        return True
    if len(norm_text) <= 4 and len(norm_text.split()) == 1:
        # Short single-token strings are often tokenization fragments.
        return norm_text not in {"pan", "bao", "pez"}
    return False


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def build_engine():
    try:
        from src.config.settings import settings  # type: ignore

        user = quote_plus(str(settings.pguser))
        password = quote_plus(str(settings.pgpassword))
        host = settings.pghost
        port = settings.pgport
        database = settings.pgdatabase
    except Exception as exc:  # pragma: no cover - fallback for unusual local runs
        raise RuntimeError(
            "No se pudo cargar src.config.settings.settings. Ejecuta el script desde "
            "la raíz del repositorio y asegúrate de tener configurado el .env."
        ) from exc

    dsn = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(dsn, future=True, pool_pre_ping=True)


def read_sql_df(sql: str, params: Dict[str, Any]) -> pd.DataFrame:
    engine = build_engine()
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)


# ---------------------------------------------------------------------------
# Loading and standardization
# ---------------------------------------------------------------------------


def load_hybrid_from_db(schema: str, source_system: str) -> pd.DataFrame:
    sql = f'''
        SELECT
            v.*
        FROM "{schema}"."vw_ai_dish_mentions_with_sentiment" v
        JOIN "{schema}"."review" r
            ON r.review_id::text = v.review_id::text
        JOIN "{schema}"."source_system" ss
            ON ss.source_system_id = r.source_system_id
        WHERE ss.source_code = :source_system
    '''
    return read_sql_df(sql, {"source_system": source_system})


def load_table_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict) and "records" in payload:
            return pd.DataFrame(payload["records"])
        raise ValueError(f"JSON no soportado para tabla: {path}")
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Formato no soportado: {path}")


def first_existing(row: pd.Series, names: List[str], default: Any = None) -> Any:
    for name in names:
        if name in row.index:
            value = row.get(name)
            if value is not None and not (isinstance(value, float) and math.isnan(value)):
                return value
    return default


def standardize_hybrid(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        mention_text = first_existing(row, ["dish_mention_text", "mention_text", "text_mention"])
        start_char = first_existing(row, ["start_char", "start", "mention_start"])
        end_char = first_existing(row, ["end_char", "end", "mention_end"])
        review_id = first_existing(row, ["review_id"])
        place_id = first_existing(row, ["place_id"])
        dish_id = first_existing(row, ["dish_id_v1", "dish_id", "current_dish_id"])
        normalized_dish_name = first_existing(row, ["normalized_dish_name_es_v1", "normalized_dish_name", "dish_normalized_name"])
        display_dish_name = first_existing(row, ["display_dish_name_es_v1", "display_dish_name", "dish_display_name"])
        confidence = first_existing(row, ["confidence", "mention_confidence", "detection_confidence"], 0.0)

        rows.append({
            "source": "hybrid",
            "source_mention_id": first_existing(row, ["mention_id", "dish_mention_id"], f"hybrid_row_{idx}"),
            "review_id": review_id,
            "place_id": place_id,
            "place_name": first_existing(row, ["place_name"]),
            "district_id": first_existing(row, ["district_id"]),
            "district_name": first_existing(row, ["district_name"]),
            "neighborhood_id": first_existing(row, ["neighborhood_id"]),
            "neighborhood_name": first_existing(row, ["neighborhood_name"]),
            "rating_value": first_existing(row, ["rating_value"]),
            "review_language": first_existing(row, ["review_language"]),
            "source_review_id": first_existing(row, ["source_review_id"]),
            "source_place_record_id": first_existing(row, ["source_place_record_id"]),
            "review_text": first_existing(row, ["text", "review_text", "review_text_raw"]),
            "mention_text": mention_text,
            "mention_norm": normalize_text(mention_text),
            "start_char": safe_int(start_char),
            "end_char": safe_int(end_char),
            "confidence": safe_float(confidence),
            "context_sentence": first_existing(row, ["context_sentence"]),
            "window_context": first_existing(row, ["window_context"]),
            "dish_id": dish_id,
            "display_dish_name": display_dish_name,
            "normalized_dish_name": normalized_dish_name,
            "dish_group": first_existing(row, ["dish_group_es_v1", "dish_group"]),
            "dish_family": first_existing(row, ["dish_family_es_v1", "dish_family"]),
            "dish_specificity": first_existing(row, ["dish_specificity_v1", "dish_specificity"]),
            "candidate_type": first_existing(row, ["candidate_type"]),
            "lexicon_group": first_existing(row, ["lexicon_group"]),
            "detection_method": first_existing(row, ["detection_method"], "hybrid"),
            "pattern_name": first_existing(row, ["pattern_name"]),
            "mention_quality_tier": first_existing(row, ["mention_quality_tier_v1", "mention_quality_tier"]),
            "ranking_eligible": first_existing(row, ["ranking_eligible_v1", "ranking_eligible"]),
            "eligibility_status": first_existing(row, ["eligibility_status_v1", "eligibility_status"]),
            "eligibility_reason": first_existing(row, ["eligibility_reason_v1", "eligibility_reason"]),
            "needs_manual_review_original": first_existing(row, ["needs_manual_review_v1", "needs_manual_review"]),
            "normalization_method": first_existing(row, ["normalization_method_v1", "normalization_method"]),
        })
    out = pd.DataFrame(rows)
    if len(out):
        out = out[out["review_id"].notna() & out["mention_norm"].ne("")].copy()
    return out.reset_index(drop=True)


def standardize_ner(df: pd.DataFrame) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        mention_text = first_existing(row, ["mention_text", "text", "entity_text"])
        start_char = first_existing(row, ["start_char", "start", "start_offset"])
        end_char = first_existing(row, ["end_char", "end", "end_offset"])
        review_id = first_existing(row, ["review_id"])
        confidence = first_existing(row, ["confidence", "entity_confidence", "score"], 0.0)

        rows.append({
            "source": "ner",
            "source_mention_id": first_existing(row, ["mention_id", "ner_mention_id"], f"ner_row_{idx}"),
            "review_id": review_id,
            "place_id": first_existing(row, ["place_id"]),
            "place_name": first_existing(row, ["place_name"]),
            "district_id": first_existing(row, ["district_id"]),
            "district_name": first_existing(row, ["district_name"]),
            "neighborhood_id": first_existing(row, ["neighborhood_id"]),
            "neighborhood_name": first_existing(row, ["neighborhood_name"]),
            "rating_value": first_existing(row, ["rating_value"]),
            "review_language": first_existing(row, ["review_language"]),
            "source_review_id": first_existing(row, ["source_review_id"]),
            "source_place_record_id": first_existing(row, ["source_place_record_id"]),
            "review_text": first_existing(row, ["review_text", "text", "review_text_raw"]),
            "mention_text": mention_text,
            "mention_norm": normalize_text(mention_text),
            "start_char": safe_int(start_char),
            "end_char": safe_int(end_char),
            "confidence": safe_float(confidence),
            "threshold": first_existing(row, ["threshold"]),
            "model_version": first_existing(row, ["model_version"], "sevilla_dish_ner_beto_v1_2"),
            "span_was_cleaned": first_existing(row, ["span_was_cleaned"], False),
            "context_sentence": first_existing(row, ["context_sentence"]),
            "window_context": first_existing(row, ["window_context"]),
        })
    out = pd.DataFrame(rows)
    if len(out):
        out = out[out["review_id"].notna() & out["mention_norm"].ne("")].copy()
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Matching and unification
# ---------------------------------------------------------------------------


@dataclass
class MatchResult:
    hybrid_idx: int
    ner_idx: int
    match_type: str
    match_score: float


def build_matches(
    hybrid_df: pd.DataFrame,
    ner_df: pd.DataFrame,
    fuzzy_threshold: float,
    span_overlap_threshold: float,
) -> List[MatchResult]:
    matches: List[MatchResult] = []
    used_hybrid: set[int] = set()
    used_ner: set[int] = set()

    hybrid_by_review: Dict[str, List[int]] = defaultdict(list)
    for idx, row in hybrid_df.iterrows():
        hybrid_by_review[safe_str(row["review_id"])].append(idx)

    ner_by_review: Dict[str, List[int]] = defaultdict(list)
    for idx, row in ner_df.iterrows():
        ner_by_review[safe_str(row["review_id"])].append(idx)

    # 1. Exact normalized text within same review.
    for review_id, ner_indices in ner_by_review.items():
        hybrid_indices = hybrid_by_review.get(review_id, [])
        if not hybrid_indices:
            continue

        by_norm: Dict[str, List[int]] = defaultdict(list)
        for h_idx in hybrid_indices:
            if h_idx not in used_hybrid:
                by_norm[safe_str(hybrid_df.at[h_idx, "mention_norm"])].append(h_idx)

        for n_idx in ner_indices:
            if n_idx in used_ner:
                continue
            norm = safe_str(ner_df.at[n_idx, "mention_norm"])
            candidates = [h for h in by_norm.get(norm, []) if h not in used_hybrid]
            if not candidates:
                continue
            # Prefer best span overlap if available.
            best_h = max(
                candidates,
                key=lambda h: span_overlap_ratio(
                    hybrid_df.at[h, "start_char"], hybrid_df.at[h, "end_char"],
                    ner_df.at[n_idx, "start_char"], ner_df.at[n_idx, "end_char"],
                ),
            )
            matches.append(MatchResult(best_h, n_idx, "exact_text", 1.0))
            used_hybrid.add(best_h)
            used_ner.add(n_idx)

    # 2. Fuzzy text within same review.
    for review_id, ner_indices in ner_by_review.items():
        hybrid_indices = hybrid_by_review.get(review_id, [])
        if not hybrid_indices:
            continue
        for n_idx in ner_indices:
            if n_idx in used_ner:
                continue
            n_norm = safe_str(ner_df.at[n_idx, "mention_norm"])
            best: Optional[Tuple[int, float]] = None
            for h_idx in hybrid_indices:
                if h_idx in used_hybrid:
                    continue
                h_norm = safe_str(hybrid_df.at[h_idx, "mention_norm"])
                score = fuzzy_ratio(n_norm, h_norm)
                if score >= fuzzy_threshold and (best is None or score > best[1]):
                    best = (h_idx, score)
            if best is not None:
                h_idx, score = best
                matches.append(MatchResult(h_idx, n_idx, "fuzzy_text", score))
                used_hybrid.add(h_idx)
                used_ner.add(n_idx)

    # 3. Span overlap fallback within same review.
    for review_id, ner_indices in ner_by_review.items():
        hybrid_indices = hybrid_by_review.get(review_id, [])
        if not hybrid_indices:
            continue
        for n_idx in ner_indices:
            if n_idx in used_ner:
                continue
            best: Optional[Tuple[int, float]] = None
            for h_idx in hybrid_indices:
                if h_idx in used_hybrid:
                    continue
                score = span_overlap_ratio(
                    hybrid_df.at[h_idx, "start_char"], hybrid_df.at[h_idx, "end_char"],
                    ner_df.at[n_idx, "start_char"], ner_df.at[n_idx, "end_char"],
                )
                if score >= span_overlap_threshold and (best is None or score > best[1]):
                    best = (h_idx, score)
            if best is not None:
                h_idx, score = best
                matches.append(MatchResult(h_idx, n_idx, "span_overlap", score))
                used_hybrid.add(h_idx)
                used_ner.add(n_idx)

    return matches


def make_candidate_row(
    strategy: str,
    match_type: str,
    match_score: Optional[float],
    hybrid_row: Optional[pd.Series],
    ner_row: Optional[pd.Series],
) -> Dict[str, Any]:
    h = hybrid_row
    n = ner_row

    # Prefer hybrid normalized dish metadata when available, but prefer cleaned NER span text
    # for NER-only rows.
    if strategy == "hybrid_and_ner":
        primary = h if h is not None else n
        mention_text = safe_str(h.get("mention_text") if h is not None else n.get("mention_text"))
        mention_text_ner = safe_str(n.get("mention_text") if n is not None else "")
        # If the NER text is compound and the hybrid text is shorter, preserve the NER span as alternative.
        selected_mention_text = mention_text
        if mention_text_ner and len(normalize_text(mention_text_ner).split()) > len(normalize_text(mention_text).split()):
            selected_mention_text = mention_text_ner
    elif strategy == "ner_only":
        primary = n
        selected_mention_text = safe_str(n.get("mention_text")) if n is not None else ""
    else:
        primary = h
        selected_mention_text = safe_str(h.get("mention_text")) if h is not None else ""

    if primary is None:
        raise ValueError("Candidate row requires at least one source row")

    selected_norm = normalize_text(selected_mention_text)
    h_norm = normalize_text(h.get("mention_text")) if h is not None else ""
    n_norm = normalize_text(n.get("mention_text")) if n is not None else ""

    # Confidence policy: agreement is stronger than either source alone.
    hybrid_conf = safe_float(h.get("confidence")) if h is not None else None
    ner_conf = safe_float(n.get("confidence")) if n is not None else None

    if strategy == "hybrid_and_ner":
        source_confidence = max([x for x in [hybrid_conf, ner_conf] if x is not None] or [0.0])
        agreement_boost = 0.15
        combined_confidence = min(1.0, source_confidence + agreement_boost)
    elif strategy == "hybrid_only":
        combined_confidence = hybrid_conf if hybrid_conf is not None else 0.50
    else:
        combined_confidence = ner_conf if ner_conf is not None else 0.50

    compound = is_compound_mention(selected_norm)
    generic = is_generic_exact(selected_norm)
    low_value = is_low_value_single(selected_norm)
    fragment = likely_fragment(selected_norm)

    needs_normalization = (
        strategy == "ner_only"
        or (strategy == "hybrid_and_ner" and h_norm != n_norm)
        or compound
        or low_value
    )

    needs_manual_review = (
        strategy == "ner_only"
        or fragment
        or low_value
        or generic
        or (strategy == "hybrid_and_ner" and h_norm != n_norm)
    )

    if strategy == "hybrid_and_ner" and not needs_manual_review:
        review_priority = "low"
    elif compound or strategy == "ner_only":
        review_priority = "high"
    elif low_value or generic or fragment:
        review_priority = "high"
    else:
        review_priority = "medium"

    candidate_id = stable_id(
        primary.get("review_id"),
        selected_norm,
        primary.get("start_char"),
        primary.get("end_char"),
        strategy,
        prefix="mention_candidate_v2",
    )

    return {
        "mention_candidate_id_v2": candidate_id,
        "source_strategy_v2": strategy,
        "match_type_v2": match_type,
        "match_score_v2": match_score,
        "combined_confidence_v2": round(float(combined_confidence), 6) if combined_confidence is not None else None,
        "agreement_boost_applied_v2": strategy == "hybrid_and_ner",

        "review_id": primary.get("review_id"),
        "place_id": first_non_empty(primary.get("place_id"), h.get("place_id") if h is not None else None, n.get("place_id") if n is not None else None),
        "place_name": first_non_empty(primary.get("place_name"), h.get("place_name") if h is not None else None, n.get("place_name") if n is not None else None),
        "district_id": first_non_empty(primary.get("district_id"), h.get("district_id") if h is not None else None, n.get("district_id") if n is not None else None),
        "district_name": first_non_empty(primary.get("district_name"), h.get("district_name") if h is not None else None, n.get("district_name") if n is not None else None),
        "neighborhood_id": first_non_empty(primary.get("neighborhood_id"), h.get("neighborhood_id") if h is not None else None, n.get("neighborhood_id") if n is not None else None),
        "neighborhood_name": first_non_empty(primary.get("neighborhood_name"), h.get("neighborhood_name") if h is not None else None, n.get("neighborhood_name") if n is not None else None),
        "rating_value": first_non_empty(primary.get("rating_value"), h.get("rating_value") if h is not None else None, n.get("rating_value") if n is not None else None),
        "review_language": first_non_empty(primary.get("review_language"), h.get("review_language") if h is not None else None, n.get("review_language") if n is not None else None),
        "source_review_id": first_non_empty(primary.get("source_review_id"), h.get("source_review_id") if h is not None else None, n.get("source_review_id") if n is not None else None),
        "source_place_record_id": first_non_empty(primary.get("source_place_record_id"), h.get("source_place_record_id") if h is not None else None, n.get("source_place_record_id") if n is not None else None),

        "selected_mention_text_v2": selected_mention_text,
        "selected_mention_norm_v2": selected_norm,
        "selected_start_char_v2": first_non_empty(n.get("start_char") if n is not None else None, h.get("start_char") if h is not None else None),
        "selected_end_char_v2": first_non_empty(n.get("end_char") if n is not None else None, h.get("end_char") if h is not None else None),
        "context_sentence": first_non_empty(n.get("context_sentence") if n is not None else None, h.get("context_sentence") if h is not None else None),
        "window_context": first_non_empty(n.get("window_context") if n is not None else None, h.get("window_context") if h is not None else None),
        "review_text": first_non_empty(n.get("review_text") if n is not None else None, h.get("review_text") if h is not None else None),

        "hybrid_mention_id": h.get("source_mention_id") if h is not None else None,
        "hybrid_mention_text": h.get("mention_text") if h is not None else None,
        "hybrid_mention_norm": h_norm or None,
        "hybrid_start_char": h.get("start_char") if h is not None else None,
        "hybrid_end_char": h.get("end_char") if h is not None else None,
        "hybrid_confidence": hybrid_conf,
        "hybrid_detection_method": h.get("detection_method") if h is not None else None,
        "hybrid_pattern_name": h.get("pattern_name") if h is not None else None,
        "hybrid_mention_quality_tier": h.get("mention_quality_tier") if h is not None else None,
        "hybrid_ranking_eligible": h.get("ranking_eligible") if h is not None else None,

        "ner_mention_id": n.get("source_mention_id") if n is not None else None,
        "ner_mention_text": n.get("mention_text") if n is not None else None,
        "ner_mention_norm": n_norm or None,
        "ner_start_char": n.get("start_char") if n is not None else None,
        "ner_end_char": n.get("end_char") if n is not None else None,
        "ner_confidence": ner_conf,
        "ner_threshold": n.get("threshold") if n is not None else None,
        "ner_model_version": n.get("model_version") if n is not None else None,
        "ner_span_was_cleaned": n.get("span_was_cleaned") if n is not None else None,

        "current_dish_id_from_hybrid": h.get("dish_id") if h is not None else None,
        "current_display_dish_name_from_hybrid": h.get("display_dish_name") if h is not None else None,
        "current_normalized_dish_name_from_hybrid": h.get("normalized_dish_name") if h is not None else None,
        "current_dish_group_from_hybrid": h.get("dish_group") if h is not None else None,
        "current_dish_family_from_hybrid": h.get("dish_family") if h is not None else None,
        "current_dish_specificity_from_hybrid": h.get("dish_specificity") if h is not None else None,
        "hybrid_normalization_method": h.get("normalization_method") if h is not None else None,

        "is_compound_mention_v2": compound,
        "is_generic_exact_v2": generic,
        "is_low_value_single_v2": low_value,
        "is_likely_fragment_v2": fragment,
        "needs_dish_normalization_v2": needs_normalization,
        "needs_manual_review_v2": needs_manual_review,
        "normalization_review_priority_v2": review_priority,
        "is_ready_for_sentiment_v2": not fragment and not generic,
        "is_experimental_ner_only_v2": strategy == "ner_only",
        "build_version_v2": VERSION,
        "built_at": utc_now_iso(),
    }


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, float) and math.isnan(value):
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def build_unified_candidates(
    hybrid_df: pd.DataFrame,
    ner_df: pd.DataFrame,
    matches: List[MatchResult],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    matched_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []

    matched_hybrid = {m.hybrid_idx for m in matches}
    matched_ner = {m.ner_idx for m in matches}

    for match in matches:
        h = hybrid_df.loc[match.hybrid_idx]
        n = ner_df.loc[match.ner_idx]
        row = make_candidate_row(
            strategy="hybrid_and_ner",
            match_type=match.match_type,
            match_score=match.match_score,
            hybrid_row=h,
            ner_row=n,
        )
        candidate_rows.append(row)
        matched_rows.append(row)

    hybrid_only_rows: List[Dict[str, Any]] = []
    for h_idx, h in hybrid_df.iterrows():
        if h_idx in matched_hybrid:
            continue
        row = make_candidate_row(
            strategy="hybrid_only",
            match_type="hybrid_only",
            match_score=None,
            hybrid_row=h,
            ner_row=None,
        )
        candidate_rows.append(row)
        hybrid_only_rows.append(row)

    ner_only_rows: List[Dict[str, Any]] = []
    for n_idx, n in ner_df.iterrows():
        if n_idx in matched_ner:
            continue
        row = make_candidate_row(
            strategy="ner_only",
            match_type="ner_only",
            match_score=None,
            hybrid_row=None,
            ner_row=n,
        )
        candidate_rows.append(row)
        ner_only_rows.append(row)

    candidates = pd.DataFrame(candidate_rows)

    if len(candidates):
        # Final safety deduplication. Keep agreement rows first, then higher confidence.
        strategy_order = {"hybrid_and_ner": 0, "hybrid_only": 1, "ner_only": 2}
        candidates["_strategy_order"] = candidates["source_strategy_v2"].map(strategy_order).fillna(99)
        candidates = candidates.sort_values(
            ["review_id", "selected_mention_norm_v2", "_strategy_order", "combined_confidence_v2"],
            ascending=[True, True, True, False],
        )
        duplicates = candidates[candidates.duplicated(["review_id", "selected_mention_norm_v2"], keep="first")].copy()
        candidates = candidates.drop_duplicates(["review_id", "selected_mention_norm_v2"], keep="first").copy()
        candidates = candidates.drop(columns=["_strategy_order"])
    else:
        duplicates = pd.DataFrame()

    matched_df = pd.DataFrame(matched_rows)
    hybrid_only_df = pd.DataFrame(hybrid_only_rows)
    ner_only_df = pd.DataFrame(ner_only_rows)

    return candidates.reset_index(drop=True), matched_df, hybrid_only_df, ner_only_df if len(ner_only_df) else pd.DataFrame(), duplicates


# ---------------------------------------------------------------------------
# Outputs and reports
# ---------------------------------------------------------------------------


def build_normalization_queue(candidates: pd.DataFrame) -> pd.DataFrame:
    if len(candidates) == 0:
        return pd.DataFrame()
    queue = candidates[
        candidates["needs_dish_normalization_v2"].fillna(False)
        | candidates["needs_manual_review_v2"].fillna(False)
        | candidates["is_experimental_ner_only_v2"].fillna(False)
    ].copy()

    if len(queue):
        priority_order = {"high": 0, "medium": 1, "low": 2}
        queue["_priority_order"] = queue["normalization_review_priority_v2"].map(priority_order).fillna(9)
        queue = queue.sort_values(
            ["_priority_order", "source_strategy_v2", "combined_confidence_v2"],
            ascending=[True, True, False],
        ).drop(columns=["_priority_order"])
    return queue.reset_index(drop=True)


def build_summary(
    args: argparse.Namespace,
    hybrid_df: pd.DataFrame,
    ner_df: pd.DataFrame,
    matches: List[MatchResult],
    candidates: pd.DataFrame,
    normalization_queue: pd.DataFrame,
    duplicates: pd.DataFrame,
    output_paths: Dict[str, Path],
) -> Dict[str, Any]:
    strategy_counts = Counter(candidates["source_strategy_v2"]) if len(candidates) else Counter()
    priority_counts = Counter(candidates["normalization_review_priority_v2"]) if len(candidates) else Counter()
    match_counts = Counter(m.match_type for m in matches)

    top_selected_mentions = (
        candidates["selected_mention_norm_v2"].value_counts().head(30).to_dict()
        if len(candidates)
        else {}
    )

    checks = {
        "has_hybrid_mentions": len(hybrid_df) > 0,
        "has_ner_mentions": len(ner_df) > 0,
        "has_candidates": len(candidates) > 0,
        "has_matches": len(matches) > 0,
        "candidate_ids_unique": bool(candidates["mention_candidate_id_v2"].is_unique) if len(candidates) else False,
        "all_candidates_have_review_id": bool(candidates["review_id"].notna().all()) if len(candidates) else False,
        "all_candidates_have_selected_text": bool(candidates["selected_mention_text_v2"].notna().all()) if len(candidates) else False,
        "all_candidates_have_strategy": bool(candidates["source_strategy_v2"].notna().all()) if len(candidates) else False,
        "jsonl_exists": output_paths["candidates_jsonl"].exists(),
        "csv_exists": output_paths["candidates_csv"].exists(),
        "normalization_queue_exists": output_paths["normalization_queue_csv"].exists(),
    }

    errors = [name for name, ok in checks.items() if not ok]
    warnings: List[str] = []
    if len(duplicates):
        warnings.append("Some candidate duplicates were removed by review_id + selected_mention_norm_v2.")
    if int(strategy_counts.get("ner_only", 0)) > 0:
        warnings.append("NER-only candidates are experimental and require dish normalization before downstream use.")

    return {
        "script": SCRIPT_NAME,
        "version": VERSION,
        "generated_at": utc_now_iso(),
        "inputs": {
            "hybrid_source": str(args.hybrid_path) if args.hybrid_path else "database",
            "ner_path": str(args.ner_path),
            "schema": args.schema,
            "source_system": args.source_system,
            "fuzzy_threshold": args.fuzzy_threshold,
            "span_overlap_threshold": args.span_overlap_threshold,
            "no_review_text": args.no_review_text,
        },
        "counts": {
            "hybrid_mentions": int(len(hybrid_df)),
            "ner_mentions": int(len(ner_df)),
            "matched_mentions": int(len(matches)),
            "candidate_rows_final": int(len(candidates)),
            "duplicates_removed": int(len(duplicates)),
            "normalization_queue_rows": int(len(normalization_queue)),
            "reviews_with_candidates": int(candidates["review_id"].nunique()) if len(candidates) else 0,
            "places_with_candidates": int(candidates["place_id"].nunique()) if len(candidates) and "place_id" in candidates else 0,
        },
        "strategy_counts": dict(strategy_counts),
        "match_type_counts": dict(match_counts),
        "quality_flags": {
            "compound_mentions": int(candidates["is_compound_mention_v2"].sum()) if len(candidates) else 0,
            "generic_exact_mentions": int(candidates["is_generic_exact_v2"].sum()) if len(candidates) else 0,
            "low_value_single_mentions": int(candidates["is_low_value_single_v2"].sum()) if len(candidates) else 0,
            "likely_fragment_mentions": int(candidates["is_likely_fragment_v2"].sum()) if len(candidates) else 0,
            "needs_manual_review": int(candidates["needs_manual_review_v2"].sum()) if len(candidates) else 0,
            "needs_dish_normalization": int(candidates["needs_dish_normalization_v2"].sum()) if len(candidates) else 0,
            "ready_for_sentiment": int(candidates["is_ready_for_sentiment_v2"].sum()) if len(candidates) else 0,
        },
        "normalization_priority_counts": dict(priority_counts),
        "top_selected_mentions": top_selected_mentions,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "files": {name: str(path) for name, path in output_paths.items()},
        "notes": [
            "This is an intermediate candidate layer for IA v2, not the final dish_mention table.",
            "NER-only rows should pass dish normalization/entity linking before sentiment and ranking.",
            "Do not commit outputs containing review_text to Git.",
        ],
    }


def write_recommendations(path: Path, summary: Dict[str, Any]) -> None:
    counts = summary["counts"]
    strategies = summary["strategy_counts"]
    quality = summary["quality_flags"]
    checks = summary["checks"]

    content = f"""# Sevilla Hybrid + NER Mention Candidates v2 - Recommended next steps

## Executive read

- Hybrid mentions loaded: **{counts['hybrid_mentions']}**.
- NER mentions loaded: **{counts['ner_mentions']}**.
- Matched mentions: **{counts['matched_mentions']}**.
- Final candidate rows: **{counts['candidate_rows_final']}**.
- Normalization queue rows: **{counts['normalization_queue_rows']}**.

## Source strategy distribution

```json
{json.dumps(strategies, indent=2, ensure_ascii=False)}
```

## Quality flags

```json
{json.dumps(quality, indent=2, ensure_ascii=False)}
```

## Interpretation

This artifact combines the deterministic hybrid extractor with the trained NER v1.2 model.
Rows with `source_strategy_v2 = hybrid_and_ner` are the strongest candidates because both systems agree.
Rows with `source_strategy_v2 = ner_only` are useful for discovery, but they must go through dish normalization/entity linking before sentiment and ranking.

## Recommended next steps

1. Inspect `recommended_normalization_queue_v2.csv`, prioritizing `normalization_review_priority_v2 = high`.
2. Run the dish normalization/entity-linking model over all candidates, especially NER-only and compound mentions.
3. Deduplicate normalized mentions by `review_id + normalized_dish_id + span overlap`.
4. Run mention sentiment/ABSA on the normalized candidate layer.
5. Build place-dish signals v2 and compare ranking v1 vs IA v2 before loading to PostgreSQL.

## Checks

```json
{json.dumps(checks, indent=2, ensure_ascii=False)}
```
"""
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build unified Sevilla Hybrid + NER mention candidates for IA v2."
    )
    parser.add_argument("--schema", default="hidden_gems")
    parser.add_argument("--source-system", default="google_places")
    parser.add_argument("--hybrid-path", default=None, help="Optional CSV/JSONL hybrid mentions artifact. If omitted, DB view is used.")
    parser.add_argument("--ner-path", default=DEFAULT_NER_PATH)
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--fuzzy-threshold", type=float, default=0.86)
    parser.add_argument("--span-overlap-threshold", type=float, default=0.50)
    parser.add_argument("--no-review-text", action="store_true", help="Drop full review_text from output artifacts.")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero code if checks fail.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    ner_path = Path(args.ner_path)
    if not ner_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo NER: {ner_path}")

    print("Loading NER mentions...")
    raw_ner = load_table_file(ner_path)
    ner_df = standardize_ner(raw_ner)

    print("Loading hybrid mentions...")
    if args.hybrid_path:
        hybrid_path = Path(args.hybrid_path)
        if not hybrid_path.exists():
            raise FileNotFoundError(f"No se encontró el archivo híbrido: {hybrid_path}")
        raw_hybrid = load_table_file(hybrid_path)
    else:
        raw_hybrid = load_hybrid_from_db(schema=args.schema, source_system=args.source_system)
    hybrid_df = standardize_hybrid(raw_hybrid)

    if args.no_review_text:
        for df in [hybrid_df, ner_df]:
            if "review_text" in df.columns:
                df["review_text"] = None

    print(f"Hybrid mentions: {len(hybrid_df)}")
    print(f"NER mentions: {len(ner_df)}")

    print("Matching hybrid and NER mentions...")
    matches = build_matches(
        hybrid_df=hybrid_df,
        ner_df=ner_df,
        fuzzy_threshold=args.fuzzy_threshold,
        span_overlap_threshold=args.span_overlap_threshold,
    )
    print(f"Matches: {len(matches)}")

    print("Building unified candidate layer...")
    candidates, matched_df, hybrid_only_df, ner_only_df, duplicates = build_unified_candidates(
        hybrid_df=hybrid_df,
        ner_df=ner_df,
        matches=matches,
    )
    normalization_queue = build_normalization_queue(candidates)

    # Stable sort for readability.
    if len(candidates):
        candidates = candidates.sort_values(
            ["source_strategy_v2", "review_id", "selected_start_char_v2", "selected_mention_norm_v2"],
            ascending=[True, True, True, True],
        ).reset_index(drop=True)

    paths = {
        "candidates_csv": output_dir / "sevilla_dish_mentions_hybrid_ner_candidates_v2.csv",
        "candidates_jsonl": output_dir / "sevilla_dish_mentions_hybrid_ner_candidates_v2.jsonl",
        "matched_csv": output_dir / "sevilla_dish_mentions_hybrid_ner_matched_v2.csv",
        "hybrid_only_csv": output_dir / "sevilla_dish_mentions_hybrid_only_v2.csv",
        "ner_only_csv": output_dir / "sevilla_dish_mentions_ner_only_v2.csv",
        "duplicates_csv": output_dir / "sevilla_dish_mentions_hybrid_ner_duplicates_v2.csv",
        "normalization_queue_csv": output_dir / "recommended_normalization_queue_v2.csv",
        "summary_json": output_dir / "sevilla_dish_mentions_hybrid_ner_summary_v2.json",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }

    print("Writing outputs...")
    candidates.to_csv(paths["candidates_csv"], index=False, encoding="utf-8")
    write_jsonl(paths["candidates_jsonl"], candidates.to_dict(orient="records"))
    matched_df.to_csv(paths["matched_csv"], index=False, encoding="utf-8")
    hybrid_only_df.to_csv(paths["hybrid_only_csv"], index=False, encoding="utf-8")
    ner_only_df.to_csv(paths["ner_only_csv"], index=False, encoding="utf-8")
    duplicates.to_csv(paths["duplicates_csv"], index=False, encoding="utf-8")
    normalization_queue.to_csv(paths["normalization_queue_csv"], index=False, encoding="utf-8")

    summary = build_summary(
        args=args,
        hybrid_df=hybrid_df,
        ner_df=ner_df,
        matches=matches,
        candidates=candidates,
        normalization_queue=normalization_queue,
        duplicates=duplicates,
        output_paths=paths,
    )

    write_json(paths["summary_json"], summary)
    write_recommendations(paths["recommendations_md"], summary)

    print(json.dumps(to_builtin(summary), indent=2, ensure_ascii=False, allow_nan=False))

    if args.strict and summary.get("errors"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
