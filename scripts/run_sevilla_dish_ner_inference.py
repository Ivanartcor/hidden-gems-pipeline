"""Run Sevilla DISH NER inference with the trained BETO model v1.2.

This script applies the local model trained in Kaggle:

    sevilla_dish_ner_beto_v1_2

It reads Sevilla reviews either from PostgreSQL or from a CSV/JSONL file and
exports detected dish mentions as JSONL/CSV artifacts. It does not modify the
database.

Recommended model location inside the repository, kept local and ignored by Git:

    models/sevilla_dish_ner_beto_v1_2/
        config.json
        model.safetensors
        tokenizer.json / vocab.txt / tokenizer_config.json
        label_mapping.json

Recommended execution from repository root:

    python -m scripts.run_sevilla_dish_ner_inference `
      --model-dir models/sevilla_dish_ner_beto_v1_2 `
      --output-dir data/artifacts/ai/sevilla/model_inference/ner_v1_2 `
      --threshold 0.675 `
      --strict

Quick test:

    python -m scripts.run_sevilla_dish_ner_inference `
      --model-dir models/sevilla_dish_ner_beto_v1_2 `
      --output-dir data/artifacts/ai/sevilla/model_inference/ner_v1_2_test `
      --max-reviews 100 `
      --strict
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import NAMESPACE_URL, UUID, uuid5

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.db.database import engine

try:
    import torch
    from transformers import AutoModelForTokenClassification, AutoTokenizer
except ImportError as exc:  # pragma: no cover - user environment issue
    raise SystemExit(
        "Missing ML dependencies. Install them with: pip install transformers torch"
    ) from exc


DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_SOURCE_SYSTEM = "google_places"
DEFAULT_MODEL_DIR = Path("models/sevilla_dish_ner_beto_v1_2")
DEFAULT_OUTPUT_DIR = Path("data/artifacts/ai/sevilla/model_inference/ner_v1_2_cleaned")
DEFAULT_MODEL_VERSION = "sevilla_dish_ner_beto_v1_2"
DEFAULT_THRESHOLD = 0.675
DEFAULT_MAX_LENGTH = 384
DEFAULT_BATCH_SIZE = 16

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
LABEL_FALLBACK = {0: "O", 1: "B-DISH", 2: "I-DISH"}

LEADING_WORDS_TO_STRIP = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "del", "de", "al",
    "su", "sus", "mi", "mis", "con", "sin",
}
TRAILING_WORDS_TO_STRIP = {
    "de", "del", "con", "y", "o", "u", "en", "al", "a", "para", "por", "que",
    "muy", "más", "menos",
}
BAD_SPAN_EXACT = {
    "comida", "cena", "almuerzo", "desayuno", "servicio", "ambiente", "precio",
    "local", "restaurante", "bar", "sitio", "mesa", "carta", "menú", "menu",
    "plato", "platos", "tapas", "tapa", "whisky", "ajillo", "frito",
}
BAD_FRAGMENT_EXACT = {
    # Fragments observed in the first NER v1.2 inference/comparison.
    "ga", "gá", "bas", "alao", "rillada", "adilla", "illo", "ebab",
    "fre", "gam", "taki", "whisk", "bras",
}
WORD_CHARS_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9]")

OUTPUT_JSONL = "sevilla_dish_mentions_ner_model_v1_2.jsonl"
OUTPUT_CSV = "sevilla_dish_mentions_ner_model_v1_2.csv"
OUTPUT_SUMMARY = "sevilla_dish_ner_inference_summary_v1_2.json"
OUTPUT_EXAMPLES = "sevilla_dish_ner_inference_examples_v1_2.csv"


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid PostgreSQL schema name: {schema!r}")
    return schema


def qname(schema: str, table: str) -> str:
    return f'"{validate_schema_name(schema)}"."{table}"'


def to_builtin(value: Any) -> Any:
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
    if isinstance(value, np.generic):
        return to_builtin(value.item())
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


def save_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(data), f, indent=2, ensure_ascii=False, allow_nan=False)


def write_jsonl(rows: Iterable[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(to_builtin(row), ensure_ascii=False, allow_nan=False) + "\n")
            count += 1
    return count


def stable_mention_id(review_id: str, start: int, end: int, text_value: str, model_version: str) -> str:
    raw = f"{model_version}|{review_id}|{start}|{end}|{text_value.lower().strip()}"
    return str(uuid5(NAMESPACE_URL, raw))


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def read_df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params or {})


def load_reviews_from_db(args: argparse.Namespace) -> pd.DataFrame:
    schema = validate_schema_name(args.schema)
    where_parts = [
        "ss.source_code = :source_system",
        "r.is_active = TRUE",
        "COALESCE(r.is_deleted_in_source, FALSE) = FALSE",
        "r.review_text_raw IS NOT NULL",
        "LENGTH(TRIM(r.review_text_raw)) >= :min_text_length",
    ]
    params: dict[str, Any] = {"source_system": args.source_system, "min_text_length": args.min_text_length}
    if args.review_language:
        where_parts.append("COALESCE(r.review_language, '') ILIKE :review_language")
        params["review_language"] = f"%{args.review_language}%"
    limit_sql = ""
    if args.max_reviews is not None:
        limit_sql = "LIMIT :max_reviews"
        params["max_reviews"] = int(args.max_reviews)
    sql = f"""
        SELECT
            r.review_id::text AS review_id,
            r.place_id::text AS place_id,
            p.display_name AS place_name,
            p.address_text,
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
        FROM {qname(schema, "review")} r
        JOIN {qname(schema, "source_system")} ss ON ss.source_system_id = r.source_system_id
        JOIN {qname(schema, "place")} p ON p.place_id = r.place_id
        LEFT JOIN {qname(schema, "place_neighborhood_assignment")} pna
            ON pna.place_id = p.place_id AND pna.is_current = TRUE
        LEFT JOIN {qname(schema, "neighborhood")} n ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN {qname(schema, "district")} d ON d.district_id = pna.district_id
        WHERE {' AND '.join(where_parts)}
        ORDER BY r.review_created_at DESC NULLS LAST, r.review_id
        {limit_sql};
    """
    return read_df(sql, params)


def read_jsonl(path: Path) -> pd.DataFrame:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return pd.DataFrame(rows)


def load_reviews_from_file(path: Path, max_reviews: int | None = None, min_text_length: int = 20) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")
    if path.suffix.lower() == ".jsonl":
        df = read_jsonl(path)
    elif path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
    else:
        raise ValueError("Only .jsonl and .csv input files are supported.")
    if "text" not in df.columns:
        if "review_text_raw" in df.columns:
            df = df.rename(columns={"review_text_raw": "text"})
        else:
            raise KeyError("Input file must contain a 'text' column or 'review_text_raw'.")
    for col in ["review_id", "place_id", "place_name", "address_text", "neighborhood_id", "neighborhood_name", "district_id", "district_name", "rating_value", "review_language", "review_created_at", "source_review_id", "source_place_record_id"]:
        if col not in df.columns:
            df[col] = None
    df["text"] = df["text"].fillna("").astype(str)
    df = df[df["text"].str.strip().str.len() >= min_text_length].copy()
    if max_reviews is not None:
        df = df.head(int(max_reviews)).copy()
    return df.reset_index(drop=True)


def maybe_extract_model_zip(model_dir: Path, model_zip: Path | None) -> None:
    if model_dir.exists():
        return
    if model_zip is None:
        return
    if not model_zip.exists():
        raise FileNotFoundError(f"Model directory does not exist and model zip was not found: {model_zip}")
    print(f"Model dir not found. Extracting {model_zip} into {model_dir.parent} ...")
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(model_zip, "r") as zipf:
        zipf.extractall(model_dir.parent)


def load_label_mapping(model_dir: Path) -> dict[int, str]:
    mapping_path = model_dir / "label_mapping.json"
    if mapping_path.exists():
        with mapping_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        id2label = data.get("id2label") or {}
        if id2label:
            return {int(k): str(v) for k, v in id2label.items()}
    return LABEL_FALLBACK.copy()


def choose_device(device_arg: str) -> torch.device:
    if device_arg == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device_arg == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("--device cuda requested but CUDA is not available.")
    return torch.device(device_arg)


def softmax_np(logits: np.ndarray) -> np.ndarray:
    logits = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(logits)
    return exp / np.sum(exp, axis=-1, keepdims=True)


def is_word_char(char: str) -> bool:
    return bool(char and WORD_CHARS_RE.match(char))


def expand_to_word_boundaries(text_value: str, start: int, end: int) -> tuple[int, int]:
    """Expand a predicted subword span to full word boundaries.

    This fixes common token-classification fragments such as:
    - "rillada" -> "carrillada"
    - "adilla" -> "ensaladilla"
    - "bas al ajillo" -> "gambas al ajillo"
    - "solomillo al whisk" -> "solomillo al whisky"
    """
    text_len = len(text_value)
    start = max(0, min(int(start), text_len))
    end = max(start, min(int(end), text_len))

    while start > 0 and is_word_char(text_value[start - 1]) and (start < text_len and is_word_char(text_value[start])):
        start -= 1

    while end < text_len and end > 0 and is_word_char(text_value[end - 1]) and is_word_char(text_value[end]):
        end += 1

    return start, end


def has_enough_alpha(text_value: str, min_alpha: int = 3) -> bool:
    return sum(1 for ch in text_value if ch.isalpha()) >= min_alpha


def clean_predicted_span(text_value: str, start: int, end: int) -> dict[str, Any] | None:
    original_start, original_end = int(start), int(end)

    # 1) Basic whitespace/punctuation trimming.
    while start < end and text_value[start].isspace():
        start += 1
    while end > start and text_value[end - 1].isspace():
        end -= 1
    while start < end and text_value[start] in ".,;:¡!¿?()[]{}\"'“”‘’":
        start += 1
    while end > start and text_value[end - 1] in ".,;:¡!¿?()[]{}\"'“”‘’":
        end -= 1

    if end <= start:
        return None

    # 2) Expand partial-word spans to full words. This is the most important
    # postprocessing improvement over the first inference version.
    start, end = expand_to_word_boundaries(text_value, start, end)

    # 3) Trim again after expansion.
    while start < end and text_value[start].isspace():
        start += 1
    while end > start and text_value[end - 1].isspace():
        end -= 1
    while start < end and text_value[start] in ".,;:¡!¿?()[]{}\"'“”‘’":
        start += 1
    while end > start and text_value[end - 1] in ".,;:¡!¿?()[]{}\"'“”‘’":
        end -= 1

    if end <= start:
        return None

    # 4) Remove leading articles/determiners and trailing connectors.
    span_text = text_value[start:end].strip()
    words = span_text.split()

    while words and words[0].lower().strip(".,;:") in LEADING_WORDS_TO_STRIP:
        removed = words.pop(0)
        start += len(removed)
        while start < end and text_value[start].isspace():
            start += 1

    while words and words[-1].lower().strip(".,;:") in TRAILING_WORDS_TO_STRIP:
        removed = words.pop()
        end -= len(removed)
        while end > start and text_value[end - 1].isspace():
            end -= 1

    if end <= start:
        return None

    cleaned_text = text_value[start:end].strip()
    cleaned_norm = cleaned_text.lower()

    if not cleaned_text:
        return None

    # 5) Conservative filters for noisy fragments and non-dish generic terms.
    if cleaned_norm in BAD_SPAN_EXACT or cleaned_norm in BAD_FRAGMENT_EXACT:
        return None

    if len(cleaned_text) < 3 or not has_enough_alpha(cleaned_text, min_alpha=3):
        return None

    if len(cleaned_text.split()) > 8:
        return None

    # Avoid spans that still look like they begin/end with an unfinished connector.
    first_word = cleaned_text.split()[0].lower().strip(".,;:")
    last_word = cleaned_text.split()[-1].lower().strip(".,;:")
    if first_word in {"con", "sin", "de", "del", "al"}:
        return None
    if last_word in TRAILING_WORDS_TO_STRIP:
        return None

    return {
        "start": int(start),
        "end": int(end),
        "text": cleaned_text,
        "label": "DISH",
        "original_start": int(original_start),
        "original_end": int(original_end),
        "original_text": text_value[original_start:original_end],
        "span_was_cleaned": bool(start != original_start or end != original_end or cleaned_text != text_value[original_start:original_end].strip()),
    }

def bio_to_spans(text_value: str, offsets: list[tuple[int, int]], pred_ids: list[int], token_confidences: list[float], id2label: dict[int, str]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    current_start: int | None = None
    current_end: int | None = None
    current_confidences: list[float] = []
    def close_current() -> None:
        nonlocal current_start, current_end, current_confidences
        if current_start is None or current_end is None:
            return
        cleaned = clean_predicted_span(text_value, current_start, current_end)
        if cleaned is not None:
            cleaned["confidence"] = float(np.mean(current_confidences)) if current_confidences else None
            cleaned["token_count"] = len(current_confidences)
            spans.append(cleaned)
        current_start = None
        current_end = None
        current_confidences = []
    for (start, end), pred_id, token_conf in zip(offsets, pred_ids, token_confidences):
        if start == end:
            continue
        label = id2label.get(int(pred_id), "O")
        if label == "B-DISH":
            close_current()
            current_start = int(start)
            current_end = int(end)
            current_confidences = [float(token_conf)]
        elif label == "I-DISH":
            if current_start is None:
                current_start = int(start)
                current_end = int(end)
                current_confidences = [float(token_conf)]
            else:
                current_end = int(end)
                current_confidences.append(float(token_conf))
        else:
            close_current()
    close_current()
    unique: list[dict[str, Any]] = []
    seen: set[tuple[int, int, str]] = set()
    for span in spans:
        key = (int(span["start"]), int(span["end"]), str(span["text"]).lower())
        if key not in seen:
            unique.append(span)
            seen.add(key)
    return unique


def predict_batch(texts: list[str], tokenizer: Any, model: Any, device: torch.device, id2label: dict[int, str], threshold: float, max_length: int) -> list[list[dict[str, Any]]]:
    encoded = tokenizer(texts, return_offsets_mapping=True, truncation=True, max_length=max_length, padding=True, return_tensors="pt")
    offsets_batch = encoded.pop("offset_mapping").cpu().numpy().tolist()
    attention_mask = encoded["attention_mask"].cpu().numpy()
    encoded = {k: v.to(device) for k, v in encoded.items()}
    model.eval()
    with torch.no_grad():
        outputs = model(**encoded)
        logits = outputs.logits.detach().cpu().numpy()
    probs = softmax_np(logits)
    pred_ids = np.argmax(probs, axis=-1)
    pred_conf = np.max(probs, axis=-1)
    results: list[list[dict[str, Any]]] = []
    dish_label_ids = {idx for idx, label in id2label.items() if label in {"B-DISH", "I-DISH"}}
    for i, text_value in enumerate(texts):
        sequence_pred_ids = pred_ids[i].copy()
        sequence_conf = pred_conf[i].copy()
        sequence_offsets = [(int(a), int(b)) for a, b in offsets_batch[i]]
        for j in range(len(sequence_pred_ids)):
            if attention_mask[i, j] == 0:
                sequence_pred_ids[j] = 0
                continue
            if int(sequence_pred_ids[j]) in dish_label_ids and float(sequence_conf[j]) < threshold:
                sequence_pred_ids[j] = 0
        spans = bio_to_spans(text_value, sequence_offsets, sequence_pred_ids.tolist(), sequence_conf.tolist(), id2label)
        results.append(spans)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sevilla DISH NER inference with BETO v1.2.")
    parser.add_argument("--schema", default=DEFAULT_SCHEMA)
    parser.add_argument("--source-system", default=DEFAULT_SOURCE_SYSTEM)
    parser.add_argument("--input-path", type=Path, default=None, help="Optional CSV/JSONL with reviews. If omitted, reads PostgreSQL.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--model-zip", type=Path, default=None, help="Optional zip to extract if model-dir is missing.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--model-version", default=DEFAULT_MODEL_VERSION)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--max-length", type=int, default=DEFAULT_MAX_LENGTH)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-reviews", type=int, default=None)
    parser.add_argument("--min-text-length", type=int, default=20)
    parser.add_argument("--review-language", default=None, help="Optional review_language partial filter.")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--examples", type=int, default=100)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if final checks fail.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = datetime.now(timezone.utc)
    maybe_extract_model_zip(args.model_dir, args.model_zip)
    if not args.model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {args.model_dir}. Unzip the Kaggle model under models/sevilla_dish_ner_beto_v1_2/ or pass --model-zip.")
    if args.input_path:
        print(f"Reading reviews from file: {args.input_path}")
        reviews_df = load_reviews_from_file(args.input_path, args.max_reviews, args.min_text_length)
        input_source = "file"
    else:
        print("Reading reviews from PostgreSQL...")
        reviews_df = load_reviews_from_db(args)
        input_source = "database"
    if reviews_df.empty:
        print("No reviews found.")
        return 1
    reviews_df["text"] = reviews_df["text"].fillna("").astype(str)
    reviews_df = reviews_df[reviews_df["text"].str.strip().str.len() >= args.min_text_length].reset_index(drop=True)
    print(f"Reviews loaded: {len(reviews_df)}")
    print(f"Model dir: {args.model_dir}")
    print(f"Threshold: {args.threshold}")
    id2label = load_label_mapping(args.model_dir)
    label2id = {v: k for k, v in id2label.items()}
    tokenizer = AutoTokenizer.from_pretrained(args.model_dir, use_fast=True)
    model = AutoModelForTokenClassification.from_pretrained(args.model_dir)
    device = choose_device(args.device)
    model.to(device)
    print(f"Device: {device}")
    print(f"Labels: {id2label}")
    mentions: list[dict[str, Any]] = []
    review_mentions_count: list[int] = []
    total = len(reviews_df)
    batch_size = int(args.batch_size)
    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch_df = reviews_df.iloc[start_idx:end_idx]
        texts = batch_df["text"].tolist()
        batch_spans = predict_batch(texts, tokenizer, model, device, id2label, float(args.threshold), int(args.max_length))
        for (_, row), spans in zip(batch_df.iterrows(), batch_spans):
            review_id = str(row.get("review_id") or "")
            place_id = str(row.get("place_id") or "")
            text_value = str(row.get("text") or "")
            review_mentions_count.append(len(spans))
            for span_index, span in enumerate(spans, start=1):
                mention_text = normalize_space(span["text"])
                mention_id = stable_mention_id(review_id, int(span["start"]), int(span["end"]), mention_text, args.model_version)
                mentions.append({
                    "mention_id": mention_id,
                    "model_version": args.model_version,
                    "detection_method": "transformer_ner_beto_token_classification",
                    "entity_label": "DISH",
                    "confidence": span.get("confidence"),
                    "threshold": float(args.threshold),
                    "review_id": review_id,
                    "place_id": place_id,
                    "place_name": row.get("place_name"),
                    "address_text": row.get("address_text"),
                    "district_id": row.get("district_id"),
                    "district_name": row.get("district_name"),
                    "neighborhood_id": row.get("neighborhood_id"),
                    "neighborhood_name": row.get("neighborhood_name"),
                    "rating_value": row.get("rating_value"),
                    "review_language": row.get("review_language"),
                    "review_created_at": row.get("review_created_at"),
                    "source_review_id": row.get("source_review_id"),
                    "source_place_record_id": row.get("source_place_record_id"),
                    "mention_text": mention_text,
                    "mention_normalized": mention_text.lower(),
                    "start_char": int(span["start"]),
                    "end_char": int(span["end"]),
                    "original_start_char": int(span.get("original_start", span["start"])),
                    "original_end_char": int(span.get("original_end", span["end"])),
                    "original_text": span.get("original_text"),
                    "span_was_cleaned": span.get("span_was_cleaned"),
                    "token_count": span.get("token_count"),
                    "span_index_in_review": span_index,
                    "review_text": text_value,
                })
        if (end_idx % (batch_size * 10) == 0) or end_idx == total:
            print(f"Processed {end_idx}/{total} reviews | mentions={len(mentions)}")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    mentions_jsonl = output_dir / OUTPUT_JSONL
    mentions_csv = output_dir / OUTPUT_CSV
    examples_csv = output_dir / OUTPUT_EXAMPLES
    summary_json = output_dir / OUTPUT_SUMMARY
    write_jsonl(mentions, mentions_jsonl)
    mentions_df = pd.DataFrame(mentions)
    if not mentions_df.empty:
        mentions_df.to_csv(mentions_csv, index=False, encoding="utf-8")
        examples_df = mentions_df.sort_values(["confidence", "mention_text"], ascending=[False, True]).head(args.examples)
        examples_df.to_csv(examples_csv, index=False, encoding="utf-8")
    else:
        pd.DataFrame().to_csv(mentions_csv, index=False, encoding="utf-8")
        pd.DataFrame().to_csv(examples_csv, index=False, encoding="utf-8")
    reviews_with_mentions = int(sum(1 for c in review_mentions_count if c > 0))
    exact_duplicate_mentions = 0
    if not mentions_df.empty:
        exact_duplicate_mentions = int(mentions_df.duplicated(subset=["review_id", "place_id", "mention_text", "start_char", "end_char"], keep=False).sum())
    by_mention = mentions_df["mention_text"].value_counts().head(30).to_dict() if not mentions_df.empty else {}
    by_district = mentions_df["district_name"].value_counts(dropna=False).head(30).to_dict() if not mentions_df.empty else {}
    cleaned_span_count = int(mentions_df["span_was_cleaned"].fillna(False).astype(bool).sum()) if not mentions_df.empty and "span_was_cleaned" in mentions_df.columns else 0
    checks = {
        "model_dir_exists": bool(args.model_dir.exists()),
        "has_reviews": bool(len(reviews_df) > 0),
        "jsonl_exists": bool(mentions_jsonl.exists()),
        "csv_exists": bool(mentions_csv.exists()),
        "all_mentions_have_review_id": bool(mentions_df["review_id"].notna().all()) if not mentions_df.empty else True,
        "all_mentions_have_offsets": bool((mentions_df["end_char"] > mentions_df["start_char"]).all()) if not mentions_df.empty else True,
        "no_exact_duplicate_mentions": bool(exact_duplicate_mentions == 0),
    }
    finished_at = datetime.now(timezone.utc)
    summary = {
        "script": "run_sevilla_dish_ner_inference",
        "model_version": args.model_version,
        "generated_at": finished_at.isoformat(),
        "runtime_seconds": round((finished_at - started_at).total_seconds(), 3),
        "input": {
            "input_source": input_source,
            "input_path": str(args.input_path) if args.input_path else None,
            "source_system": args.source_system,
            "schema": args.schema,
            "reviews_loaded": int(len(reviews_df)),
            "min_text_length": int(args.min_text_length),
            "max_reviews": args.max_reviews,
        },
        "model": {
            "model_dir": str(args.model_dir),
            "threshold": float(args.threshold),
            "max_length": int(args.max_length),
            "batch_size": int(args.batch_size),
            "device": str(device),
            "id2label": id2label,
            "label2id": label2id,
        },
        "results": {
            "reviews_processed": int(len(reviews_df)),
            "reviews_with_mentions": reviews_with_mentions,
            "reviews_without_mentions": int(len(reviews_df) - reviews_with_mentions),
            "mentions_detected": int(len(mentions)),
            "avg_mentions_per_review": round(float(np.mean(review_mentions_count)), 5) if review_mentions_count else 0.0,
            "exact_duplicate_mentions": exact_duplicate_mentions,
            "mentions_with_cleaned_span": cleaned_span_count,
            "top_mentions": by_mention,
            "top_districts": by_district,
        },
        "checks": checks,
        "files": {
            "mentions_jsonl": str(mentions_jsonl),
            "mentions_csv": str(mentions_csv),
            "examples_csv": str(examples_csv),
            "summary_json": str(summary_json),
        },
        "notes": [
            "This inference output is experimental and should be compared against hybrid mentions before loading downstream.",
            "The review_text field may contain full review text; do not commit these artifacts to Git.",
            "This version includes stricter span postprocessing: word-boundary expansion, fragment filtering and connector cleanup.",
            "Recommended next step: compare this output with the hybrid v1 dish mentions.",
        ],
    }
    save_json(summary, summary_json)
    print("\nFinal summary:")
    print(json.dumps(to_builtin({"results": summary["results"], "checks": summary["checks"], "files": summary["files"]}), indent=2, ensure_ascii=False, allow_nan=False))
    if args.strict and not all(checks.values()):
        print("\nStrict mode failed. Review checks above.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
