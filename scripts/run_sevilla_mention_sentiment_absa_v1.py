"""Run Sevilla mention-level ABSA sentiment inference v1.

This script applies the trained model:

    sevilla_mention_sentiment_absa_beto_v1

on top of the normalized Hybrid + NER v2 mention layer produced by:

    run_sevilla_dish_normalization_reranker_v1_fast_progress.py

Expected input example:

    data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1_full/
    └── sevilla_dish_mentions_normalized_reranker_v1.jsonl

Outputs:

    sevilla_dish_mentions_with_absa_sentiment_v1.csv
    sevilla_dish_mentions_with_absa_sentiment_v1.jsonl
    sevilla_absa_sentiment_low_confidence_v1.csv
    sevilla_absa_sentiment_not_ready_v1.csv
    sevilla_absa_sentiment_summary_v1.json
    recommended_next_steps.md

Notes:
- This is an experimental IA v2 layer.
- Inputs may contain full review text. Do not commit generated artifacts to Git.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import UUID

import numpy as np
import pandas as pd
import torch
from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

PATCH_ID = "mention_sentiment_absa_v1_inference_2026_05_14"
VERSION = "sevilla_mention_sentiment_absa_v1"
MODEL_VERSION = "sevilla_mention_sentiment_absa_beto_v1"

DEFAULT_INPUT_PATH = (
    "data/artifacts/ai/sevilla/model_inference/normalization_reranker_v1_full/"
    "sevilla_dish_mentions_normalized_reranker_v1.jsonl"
)
DEFAULT_MODEL_DIR = "models/sevilla_mention_sentiment_absa_beto_v1"
DEFAULT_OUTPUT_DIR = "data/artifacts/ai/sevilla/model_inference/sentiment_absa_v1"

LABEL_LIST = ["negative", "neutral", "positive"]
DEFAULT_LABEL2ID = {label: i for i, label in enumerate(LABEL_LIST)}
DEFAULT_ID2LABEL = {i: label for label, i in DEFAULT_LABEL2ID.items()}


# ---------------------------------------------------------------------------
# Generic IO helpers
# ---------------------------------------------------------------------------


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


def clean_float(value: Any) -> Optional[float]:
    if is_missing(value):
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def clean_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if is_missing(value):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "si", "sí"}


def safe_str(value: Any, default: str = "") -> str:
    if is_missing(value):
        return default
    return str(value).strip()


def json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date, pd.Timestamp)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except Exception:
            return str(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        value = float(obj)
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return str(obj)


def to_builtin(value: Any) -> Any:
    """Convert pandas/numpy/python exotic values to strict JSON-compatible values."""
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(value, dict):
        return {str(k): to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_builtin(v) for v in value]
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        try:
            return float(value)
        except Exception:
            return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (str, int, bool)):
        return value

    return str(value)


def read_jsonl(path: Path, max_rows: Optional[int] = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if max_rows is not None and len(rows) >= max_rows:
                break
    return pd.DataFrame(rows)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            safe_row = to_builtin(row)
            f.write(json.dumps(safe_row, ensure_ascii=False, allow_nan=False, default=json_default) + "\n")


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(to_builtin(payload), f, indent=2, ensure_ascii=False, allow_nan=False, default=json_default)


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------


def resolve_label_maps(config: AutoConfig) -> Tuple[Dict[int, str], Dict[str, int]]:
    id2label_raw = getattr(config, "id2label", None) or {}
    label2id_raw = getattr(config, "label2id", None) or {}

    id2label: Dict[int, str] = {}
    for k, v in id2label_raw.items():
        try:
            idx = int(k)
        except Exception:
            idx = int(str(k))
        id2label[idx] = str(v).lower()

    # Some HF configs can have LABEL_0 style if not saved correctly.
    if sorted(id2label.values()) == ["label_0", "label_1", "label_2"] or set(id2label.values()) != set(LABEL_LIST):
        id2label = DEFAULT_ID2LABEL.copy()

    label2id: Dict[str, int] = {label: idx for idx, label in id2label.items()}

    # Ensure canonical labels exist.
    if set(label2id.keys()) != set(LABEL_LIST):
        id2label = DEFAULT_ID2LABEL.copy()
        label2id = DEFAULT_LABEL2ID.copy()

    return id2label, label2id


def softmax_np(logits: np.ndarray) -> np.ndarray:
    logits = logits - np.max(logits, axis=-1, keepdims=True)
    exp = np.exp(logits)
    return exp / np.sum(exp, axis=-1, keepdims=True)


class ABSAModel:
    def __init__(self, model_dir: Path, max_length: int, batch_size: int, device: Optional[str] = None) -> None:
        self.model_dir = model_dir
        self.max_length = max_length
        self.batch_size = batch_size

        if device:
            self.device = torch.device(device)
        else:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.config = AutoConfig.from_pretrained(str(model_dir))
        self.id2label, self.label2id = resolve_label_maps(self.config)
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir), use_fast=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(str(model_dir), config=self.config)
        self.model.to(self.device)
        self.model.eval()

    def predict_texts(self, texts: Sequence[str], show_progress: bool = True) -> np.ndarray:
        all_probs: List[np.ndarray] = []
        n = len(texts)
        start_time = time.time()

        for start in range(0, n, self.batch_size):
            batch_texts = list(texts[start : start + self.batch_size])
            encoded = self.tokenizer(
                batch_texts,
                truncation=True,
                max_length=self.max_length,
                padding=True,
                return_tensors="pt",
            )
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            with torch.no_grad():
                logits = self.model(**encoded).logits.detach().cpu().numpy()

            all_probs.append(softmax_np(logits))

            done = min(start + self.batch_size, n)
            if show_progress and (done == n or done % max(self.batch_size * 10, 100) == 0):
                elapsed = time.time() - start_time
                print(f"  scored sentiment {done}/{n} rows | elapsed={elapsed:.1f}s", flush=True)

        if not all_probs:
            return np.zeros((0, len(LABEL_LIST)), dtype=np.float32)

        return np.vstack(all_probs)


# ---------------------------------------------------------------------------
# ABSA feature construction
# ---------------------------------------------------------------------------


def build_absa_input(row: pd.Series, include_review_text: bool = False, review_text_max_chars: int = 700) -> str:
    mention = safe_str(row.get("selected_mention_text_v2")) or safe_str(row.get("normalized_dish_display_name_v1"))
    dish = safe_str(row.get("normalized_dish_display_name_v1")) or safe_str(row.get("normalized_dish_name_v1"))
    context = safe_str(row.get("context_sentence"))
    window = safe_str(row.get("window_context"))
    review_text = safe_str(row.get("review_text"))
    place = safe_str(row.get("place_name"))
    rating = safe_str(row.get("rating_value"))

    parts: List[str] = []
    if mention:
        parts.append(f"Mención: {mention}")
    if dish and dish.lower() != mention.lower():
        parts.append(f"Plato normalizado: {dish}")
    if context:
        parts.append(f"Contexto local: {context}")
    if window and window != context:
        parts.append(f"Ventana: {window}")
    if include_review_text and review_text:
        parts.append(f"Review: {review_text[:review_text_max_chars]}")
    elif not context and review_text:
        # Same policy as training: add full review fallback only if local context is unavailable.
        parts.append(f"Review: {review_text[:review_text_max_chars]}")
    if rating:
        parts.append(f"Rating: {rating}")
    if place:
        parts.append(f"Local: {place}")

    return " [SEP] ".join(parts)


def top_two_margin(probs: np.ndarray) -> np.ndarray:
    if probs.shape[1] < 2:
        return np.zeros(probs.shape[0], dtype=float)
    sorted_probs = np.sort(probs, axis=1)
    return sorted_probs[:, -1] - sorted_probs[:, -2]


def label_score(label: str, probs: Dict[str, float]) -> float:
    # Continuous score useful for aggregation: positive high, negative low.
    return float(probs.get("positive", 0.0) - probs.get("negative", 0.0))


def normalize_ready_for_sentiment(row: pd.Series) -> bool:
    # Primary flag generated by the normalization reranker script.
    ready = row.get("ready_for_sentiment_after_normalization_v1")
    if not is_missing(ready):
        return clean_bool(ready)

    # Fallbacks.
    if is_missing(row.get("normalized_dish_id_v1")):
        return False
    status = safe_str(row.get("normalization_status_v1")).lower()
    if status in {"no_candidate", "low_confidence"}:
        return False
    return True


def review_reason(row: pd.Series, confidence: Optional[float], margin: Optional[float], args: argparse.Namespace) -> str:
    reasons: List[str] = []

    if not normalize_ready_for_sentiment(row):
        reasons.append("not_ready_for_sentiment")

    if clean_bool(row.get("normalization_needs_manual_review_v1")):
        reasons.append("normalization_needs_review")

    if clean_bool(row.get("is_experimental_ner_only_v2")):
        reasons.append("experimental_ner_only")

    if clean_bool(row.get("is_likely_fragment_v2")):
        reasons.append("likely_fragment")

    norm_status = safe_str(row.get("normalization_status_v1")).lower()
    if norm_status in {"low_confidence", "no_candidate", "linked_needs_review"}:
        reasons.append(f"normalization_status_{norm_status}")

    if confidence is not None and confidence < args.low_confidence_threshold:
        reasons.append("low_absa_confidence")

    if margin is not None and margin < args.min_margin:
        reasons.append("low_absa_margin")

    return ";".join(dict.fromkeys(reasons)) if reasons else "none"


# ---------------------------------------------------------------------------
# Main inference
# ---------------------------------------------------------------------------


def infer_sentiment(df: pd.DataFrame, absa: ABSAModel, args: argparse.Namespace) -> pd.DataFrame:
    out = df.copy()

    out["ready_for_absa_input_v1"] = out.apply(normalize_ready_for_sentiment, axis=1)

    if not args.predict_not_ready:
        predict_mask = out["ready_for_absa_input_v1"] == True
    else:
        predict_mask = pd.Series([True] * len(out), index=out.index)

    print(f"Rows ready for ABSA prediction: {int(predict_mask.sum())}/{len(out)}", flush=True)

    out["absa_model_input_v1"] = ""
    out.loc[predict_mask, "absa_model_input_v1"] = out.loc[predict_mask].apply(
        lambda row: build_absa_input(
            row,
            include_review_text=args.include_review_text,
            review_text_max_chars=args.review_text_max_chars,
        ),
        axis=1,
    )

    texts = out.loc[predict_mask, "absa_model_input_v1"].fillna("").astype(str).tolist()

    probs = absa.predict_texts(texts, show_progress=True)

    # Initialize output columns.
    for label in LABEL_LIST:
        out[f"absa_prob_{label}_v1"] = None
    out["absa_sentiment_label_v1"] = None
    out["absa_sentiment_score_v1"] = None
    out["absa_sentiment_confidence_v1"] = None
    out["absa_sentiment_margin_v1"] = None
    out["absa_sentiment_status_v1"] = "not_ready_for_sentiment"
    out["absa_needs_manual_review_v1"] = True
    out["absa_review_reason_v1"] = "not_ready_for_sentiment"
    out["absa_model_version"] = MODEL_VERSION
    out["absa_version"] = VERSION
    out["absa_generated_at"] = datetime.now(timezone.utc).isoformat()

    if len(texts) == 0:
        return out

    pred_ids = probs.argmax(axis=1)
    confidence = probs.max(axis=1)
    margins = top_two_margin(probs)

    predict_indices = out.index[predict_mask].tolist()

    for local_i, df_idx in enumerate(predict_indices):
        row_probs = {absa.id2label[i]: float(probs[local_i, i]) for i in range(probs.shape[1])}
        pred_label = absa.id2label[int(pred_ids[local_i])]
        conf = float(confidence[local_i])
        margin = float(margins[local_i])

        for label in LABEL_LIST:
            out.at[df_idx, f"absa_prob_{label}_v1"] = row_probs.get(label)

        out.at[df_idx, "absa_sentiment_label_v1"] = pred_label
        out.at[df_idx, "absa_sentiment_score_v1"] = round(label_score(pred_label, row_probs), 6)
        out.at[df_idx, "absa_sentiment_confidence_v1"] = round(conf, 6)
        out.at[df_idx, "absa_sentiment_margin_v1"] = round(margin, 6)

        reason = review_reason(out.loc[df_idx], conf, margin, args)
        needs_review = reason != "none"

        if conf < args.low_confidence_threshold:
            status = "low_confidence"
        elif margin < args.min_margin:
            status = "low_margin"
        elif not normalize_ready_for_sentiment(out.loc[df_idx]):
            status = "not_ready_for_sentiment"
        elif needs_review:
            status = "predicted_needs_review"
        else:
            status = "predicted"

        out.at[df_idx, "absa_sentiment_status_v1"] = status
        out.at[df_idx, "absa_needs_manual_review_v1"] = bool(needs_review)
        out.at[df_idx, "absa_review_reason_v1"] = reason

    return out


def build_summary(df_in: pd.DataFrame, df_out: pd.DataFrame, args: argparse.Namespace, runtime_seconds: float, absa: ABSAModel, paths: Dict[str, Path]) -> Dict[str, Any]:
    predicted = df_out[df_out["absa_sentiment_label_v1"].notna()].copy()
    low_conf = df_out[df_out["absa_sentiment_status_v1"].isin(["low_confidence", "low_margin", "predicted_needs_review"])].copy()
    not_ready = df_out[df_out["absa_sentiment_status_v1"] == "not_ready_for_sentiment"].copy()

    confidence_summary: Dict[str, Any]
    if len(predicted):
        confidence_summary = predicted["absa_sentiment_confidence_v1"].astype(float).describe().round(6).to_dict()
    else:
        confidence_summary = {}

    score_summary: Dict[str, Any]
    if len(predicted):
        score_summary = predicted["absa_sentiment_score_v1"].astype(float).describe().round(6).to_dict()
    else:
        score_summary = {}

    reason_counts = Counter(df_out["absa_review_reason_v1"].fillna("none").astype(str))

    checks = {
        "input_exists": Path(args.input_path).exists(),
        "model_dir_exists": Path(args.model_dir).exists(),
        "has_input_rows": len(df_in) > 0,
        "has_predicted_rows": len(predicted) > 0,
        "all_predicted_have_label": bool(predicted["absa_sentiment_label_v1"].notna().all()) if len(predicted) else False,
        "all_predicted_have_confidence": bool(predicted["absa_sentiment_confidence_v1"].notna().all()) if len(predicted) else False,
        "csv_exists": paths["sentiment_csv"].exists(),
        "jsonl_exists": paths["sentiment_jsonl"].exists(),
        "low_confidence_csv_exists": paths["low_confidence_csv"].exists(),
    }

    warnings: List[str] = []
    if len(not_ready):
        warnings.append("Some rows were not ready for ABSA sentiment inference.")
    if len(low_conf):
        warnings.append("Some sentiment predictions are low-confidence, low-margin or need manual review.")
    if args.include_review_text:
        warnings.append("Full review text was included in model input/output; do not commit artifacts to Git.")

    return {
        "script": "run_sevilla_mention_sentiment_absa_v1",
        "patch_id": PATCH_ID,
        "version": VERSION,
        "model_version": MODEL_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(runtime_seconds, 3),
        "inputs": {
            "input_path": str(args.input_path),
            "model_dir": str(args.model_dir),
            "max_length": args.max_length,
            "batch_size": args.batch_size,
            "low_confidence_threshold": args.low_confidence_threshold,
            "min_margin": args.min_margin,
            "predict_not_ready": args.predict_not_ready,
            "include_review_text": args.include_review_text,
            "device": str(absa.device),
        },
        "counts": {
            "input_rows": int(len(df_in)),
            "predicted_rows": int(len(predicted)),
            "not_ready_rows": int(len(not_ready)),
            "low_confidence_or_review_rows": int(len(low_conf)),
            "ready_for_downstream_sentiment": int((df_out["absa_sentiment_status_v1"] == "predicted").sum()),
            "needs_manual_review": int(df_out["absa_needs_manual_review_v1"].fillna(False).astype(bool).sum()),
            "unique_reviews": int(df_out["review_id"].nunique()) if "review_id" in df_out.columns else None,
            "unique_places": int(df_out["place_id"].nunique()) if "place_id" in df_out.columns else None,
            "unique_dishes": int(df_out["normalized_dish_id_v1"].nunique()) if "normalized_dish_id_v1" in df_out.columns else None,
        },
        "label_counts": predicted["absa_sentiment_label_v1"].value_counts(dropna=False).to_dict() if len(predicted) else {},
        "status_counts": df_out["absa_sentiment_status_v1"].value_counts(dropna=False).to_dict(),
        "source_strategy_counts": df_out["source_strategy_v2"].value_counts(dropna=False).to_dict() if "source_strategy_v2" in df_out.columns else {},
        "review_reason_counts_top": dict(reason_counts.most_common(20)),
        "confidence_summary": confidence_summary,
        "sentiment_score_summary": score_summary,
        "label_mapping": {
            "id2label": absa.id2label,
            "label2id": absa.label2id,
        },
        "checks": checks,
        "errors": [],
        "warnings": warnings,
        "files": {k: str(v) for k, v in paths.items()},
        "notes": [
            "This is the ABSA mention-level sentiment layer for IA v2.",
            "It predicts sentiment toward the specific dish mention, not general review sentiment.",
            "Use predicted rows for place-dish signal aggregation v2; low-confidence rows should receive lower weight or manual review.",
            "Do not commit outputs containing review_text to Git.",
        ],
    }


def write_recommendations(path: Path, summary: Dict[str, Any]) -> None:
    counts = summary["counts"]
    label_counts = summary.get("label_counts", {})
    status_counts = summary.get("status_counts", {})

    content = f"""# Sevilla ABSA sentiment v1 - Recommended next steps

## Executive read

- Input rows: **{counts.get('input_rows')}**.
- Predicted rows: **{counts.get('predicted_rows')}**.
- Ready for downstream sentiment: **{counts.get('ready_for_downstream_sentiment')}**.
- Needs manual review: **{counts.get('needs_manual_review')}**.
- Not ready rows: **{counts.get('not_ready_rows')}**.

## Predicted label counts

```json
{json.dumps(label_counts, indent=2, ensure_ascii=False)}
```

## Status counts

```json
{json.dumps(status_counts, indent=2, ensure_ascii=False)}
```

## Recommended IA v2 strategy

1. Use rows with `absa_sentiment_status_v1 = predicted` for place-dish signal aggregation v2.
2. Keep `predicted_needs_review`, `low_confidence` and `low_margin` rows, but assign lower downstream weight.
3. Exclude or manually inspect rows marked `not_ready_for_sentiment` before ranking.
4. Aggregate sentiment using both `absa_sentiment_label_v1` and `absa_sentiment_score_v1`.
5. Compare ABSA sentiment v1 against the previous hybrid sentiment before producing ranking v2.
6. Do not commit generated files containing review text to Git.

## Next pipeline step

Create the place-dish signal aggregation v2 layer:

```text
normalized mentions + ABSA sentiment
→ place-dish signals v2
→ hidden gems ranking v2
```
"""
    path.write_text(content, encoding="utf-8")


def build_paths(output_dir: Path) -> Dict[str, Path]:
    return {
        "sentiment_csv": output_dir / "sevilla_dish_mentions_with_absa_sentiment_v1.csv",
        "sentiment_jsonl": output_dir / "sevilla_dish_mentions_with_absa_sentiment_v1.jsonl",
        "low_confidence_csv": output_dir / "sevilla_absa_sentiment_low_confidence_v1.csv",
        "not_ready_csv": output_dir / "sevilla_absa_sentiment_not_ready_v1.csv",
        "summary_json": output_dir / "sevilla_absa_sentiment_summary_v1.json",
        "recommendations_md": output_dir / "recommended_next_steps.md",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Sevilla mention-level ABSA sentiment inference v1.")
    parser.add_argument("--input-path", default=DEFAULT_INPUT_PATH, help="Input normalized mentions JSONL/CSV path.")
    parser.add_argument("--model-dir", default=DEFAULT_MODEL_DIR, help="Local HF model directory.")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory.")
    parser.add_argument("--max-rows", type=int, default=None, help="Optional max input rows for quick tests.")
    parser.add_argument("--batch-size", type=int, default=32, help="Inference batch size.")
    parser.add_argument("--max-length", type=int, default=256, help="Tokenizer max length.")
    parser.add_argument("--device", default=None, help="Force device: cpu, cuda, cuda:0, etc.")
    parser.add_argument("--low-confidence-threshold", type=float, default=0.70, help="Prediction confidence below this is flagged.")
    parser.add_argument("--min-margin", type=float, default=0.12, help="Top1-top2 probability margin below this is flagged.")
    parser.add_argument("--include-review-text", action="store_true", help="Include full review text in ABSA model input.")
    parser.add_argument("--review-text-max-chars", type=int, default=700, help="Max chars if review text is used.")
    parser.add_argument("--predict-not-ready", action="store_true", help="Also predict rows not ready for sentiment.")
    parser.add_argument("--strict", action="store_true", help="Fail if key checks fail.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    start = time.time()

    input_path = Path(args.input_path)
    model_dir = Path(args.model_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = build_paths(output_dir)

    print(f"Patch: {PATCH_ID}", flush=True)
    print("Loading normalized mention layer...", flush=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input path not found: {input_path}")
    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory not found: {model_dir}")

    if input_path.suffix.lower() == ".jsonl":
        df = read_jsonl(input_path, max_rows=args.max_rows)
    elif input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path, nrows=args.max_rows)
    else:
        raise ValueError("Input path must be .jsonl or .csv")

    print(f"Input rows: {len(df)}", flush=True)
    if len(df) == 0:
        raise ValueError("Input has no rows.")

    required_any = ["selected_mention_text_v2", "normalized_dish_display_name_v1", "context_sentence", "review_text"]
    if not any(c in df.columns for c in required_any):
        raise KeyError(f"Input does not contain expected columns. Need at least one of: {required_any}")

    print("Loading ABSA sentiment model...", flush=True)
    absa = ABSAModel(
        model_dir=model_dir,
        max_length=args.max_length,
        batch_size=args.batch_size,
        device=args.device,
    )
    print(f"Device: {absa.device}", flush=True)
    print(f"Labels: {absa.id2label}", flush=True)

    print("Running ABSA sentiment inference...", flush=True)
    out = infer_sentiment(df, absa, args)

    low_confidence = out[
        out["absa_sentiment_status_v1"].isin(["low_confidence", "low_margin", "predicted_needs_review"])
    ].copy()
    not_ready = out[out["absa_sentiment_status_v1"] == "not_ready_for_sentiment"].copy()

    print("Writing outputs...", flush=True)
    out.to_csv(paths["sentiment_csv"], index=False, encoding="utf-8")
    write_jsonl(paths["sentiment_jsonl"], out.to_dict(orient="records"))
    low_confidence.to_csv(paths["low_confidence_csv"], index=False, encoding="utf-8")
    not_ready.to_csv(paths["not_ready_csv"], index=False, encoding="utf-8")

    runtime = time.time() - start
    summary = build_summary(df, out, args, runtime, absa, paths)
    write_json(paths["summary_json"], summary)
    write_recommendations(paths["recommendations_md"], summary)

    print(json.dumps(to_builtin({
        "counts": summary["counts"],
        "label_counts": summary["label_counts"],
        "status_counts": summary["status_counts"],
        "checks": summary["checks"],
        "warnings": summary["warnings"],
        "summary_json": str(paths["summary_json"]),
    }), indent=2, ensure_ascii=False, allow_nan=False, default=json_default))

    if args.strict:
        failed = [name for name, ok in summary["checks"].items() if not ok]
        if failed:
            raise RuntimeError(f"Strict mode failed checks: {failed}")

    print("ABSA sentiment inference completed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
