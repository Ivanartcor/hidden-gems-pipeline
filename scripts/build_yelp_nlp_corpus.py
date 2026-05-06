from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_FOOD_REVIEWS_PATH = "data/staging/yelp_open_dataset/food_reviews.jsonl"
DEFAULT_OUTPUT_DIR = "data/artifacts/nlp_corpus"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Construye un corpus NLP inicial a partir de Yelp food_reviews.jsonl."
    )

    parser.add_argument(
        "--food-reviews-path",
        type=str,
        default=DEFAULT_FOOD_REVIEWS_PATH,
        help="Ruta a food_reviews.jsonl.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio de salida del corpus NLP.",
    )

    parser.add_argument(
        "--corpus-name",
        type=str,
        default="yelp_food_reviews_corpus",
        help="Nombre base del corpus.",
    )

    parser.add_argument(
        "--min-text-length",
        type=int,
        default=80,
        help="Longitud mínima del texto para el corpus final. Por defecto: 80.",
    )

    parser.add_argument(
        "--max-text-length",
        type=int,
        default=5000,
        help="Longitud máxima del texto para el corpus final. Por defecto: 5000.",
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help="Máximo de documentos a guardar. 0 significa sin límite.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Número de ejemplos a guardar en el summary.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda summary también en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    text = re.sub(r"\s+", " ", text)
    return text or None


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def assign_split(source_review_id: str) -> str:
    """
    Split determinista para evitar depender de random y poder regenerar el corpus.

    80% train
    10% validation
    10% test
    """
    digest = stable_hash(source_review_id)
    bucket = int(digest[:8], 16) % 100

    if bucket < 80:
        return "train"

    if bucket < 90:
        return "validation"

    return "test"


def derive_sentiment_label(rating_value: Any) -> str | None:
    if rating_value is None:
        return None

    try:
        rating = float(rating_value)
    except (TypeError, ValueError):
        return None

    if rating >= 4:
        return "positive"

    if rating <= 2:
        return "negative"

    return "neutral"


def build_corpus_document(row: dict[str, Any]) -> dict[str, Any] | None:
    source_review_id = row.get("source_review_id")
    source_business_id = row.get("source_business_id")
    text = clean_text(row.get("review_text_raw"))

    if not source_review_id or not source_business_id or not text:
        return None

    business = row.get("business") or {}
    rating_value = row.get("rating_value")
    split = assign_split(str(source_review_id))
    sentiment_label = derive_sentiment_label(rating_value)

    corpus_document_id = f"yelp_{stable_hash(str(source_review_id))[:24]}"

    return {
        "corpus_document_id": corpus_document_id,
        "source_system_code": "yelp_open_dataset",
        "source_dataset": "yelp_open_dataset",
        "source_entity_type": "yelp_review",
        "source_review_id": source_review_id,
        "source_business_id": source_business_id,
        "source_user_id": row.get("source_user_id"),
        "text": text,
        "text_normalized": text,
        "language": "en",
        "rating_value": rating_value,
        "sentiment_label_from_rating": sentiment_label,
        "review_date": row.get("review_date"),
        "corpus_split": split,
        "task_scope": [
            "dish_extraction",
            "review_sentiment",
            "dish_sentiment",
            "recommendation_signal",
        ],
        "is_training_eligible": True,
        "quality_flags": {
            "has_text": bool(text),
            "has_rating": rating_value is not None,
            "has_business_metadata": bool(business),
            "text_length_chars": len(text),
            "label_is_weak": True,
            "label_source": "rating_value",
        },
        "business_metadata": {
            "business_name": business.get("business_name"),
            "city": business.get("city"),
            "state": business.get("state"),
            "stars_business": business.get("stars_business"),
            "review_count_business": business.get("review_count_business"),
            "is_open": business.get("is_open"),
            "categories_list": business.get("categories_list") or [],
            "food_category_tags": business.get("food_category_tags") or [],
            "food_confidence": business.get("food_confidence"),
        },
        "source_metrics": {
            "useful_count": row.get("useful_count"),
            "funny_count": row.get("funny_count"),
            "cool_count": row.get("cool_count"),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def write_jsonl_line(file: Any, row: dict[str, Any]) -> None:
    file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def build_corpus(
    *,
    food_reviews_path: Path,
    output_dir: Path,
    corpus_name: str,
    min_text_length: int,
    max_text_length: int,
    max_documents: int,
    sample_size: int,
) -> dict[str, Any]:
    if not food_reviews_path.exists():
        raise FileNotFoundError(f"No existe food_reviews.jsonl: {food_reviews_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    corpus_path = output_dir / f"{corpus_name}.jsonl"
    summary_path = output_dir / f"{corpus_name}_summary.json"

    processed_count = 0
    invalid_json_count = 0
    skipped_missing_required_count = 0
    skipped_short_text_count = 0
    skipped_long_text_count = 0
    kept_count = 0

    unique_document_ids: set[str] = set()
    unique_review_ids: set[str] = set()
    unique_business_ids: set[str] = set()

    split_counts: Counter[str] = Counter()
    sentiment_counts: Counter[str] = Counter()
    rating_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    food_tag_counts: Counter[str] = Counter()

    text_length_values: list[int] = []
    examples: list[dict[str, Any]] = []

    min_date: str | None = None
    max_date: str | None = None

    with food_reviews_path.open("r", encoding="utf-8") as input_file, corpus_path.open(
        "w", encoding="utf-8"
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if max_documents and kept_count >= max_documents:
                break

            line = line.strip()
            if not line:
                continue

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid_json_count += 1
                continue

            if not isinstance(row, dict):
                invalid_json_count += 1
                continue

            processed_count += 1

            document = build_corpus_document(row)
            if document is None:
                skipped_missing_required_count += 1
                continue

            text_length = len(document["text"])

            if text_length < min_text_length:
                skipped_short_text_count += 1
                continue

            if text_length > max_text_length:
                skipped_long_text_count += 1
                continue

            write_jsonl_line(output_file, document)

            kept_count += 1

            unique_document_ids.add(document["corpus_document_id"])
            unique_review_ids.add(str(document["source_review_id"]))
            unique_business_ids.add(str(document["source_business_id"]))

            split_counts[document["corpus_split"]] += 1

            if document["sentiment_label_from_rating"]:
                sentiment_counts[str(document["sentiment_label_from_rating"])] += 1

            if document["rating_value"] is not None:
                rating_counts[str(document["rating_value"])] += 1

            review_date = document.get("review_date")
            if isinstance(review_date, str) and review_date:
                year = review_date[:4]
                year_counts[year] += 1

                if min_date is None or review_date < min_date:
                    min_date = review_date

                if max_date is None or review_date > max_date:
                    max_date = review_date

            business_metadata = document["business_metadata"]
            state = business_metadata.get("state")
            city = business_metadata.get("city")

            if state:
                state_counts[str(state)] += 1

            if city:
                city_counts[str(city)] += 1

            for tag in business_metadata.get("food_category_tags") or []:
                food_tag_counts[str(tag)] += 1

            text_length_values.append(text_length)

            if len(examples) < sample_size:
                examples.append(
                    {
                        "corpus_document_id": document["corpus_document_id"],
                        "source_review_id": document["source_review_id"],
                        "source_business_id": document["source_business_id"],
                        "business_name": business_metadata.get("business_name"),
                        "city": business_metadata.get("city"),
                        "state": business_metadata.get("state"),
                        "rating_value": document["rating_value"],
                        "sentiment_label_from_rating": document[
                            "sentiment_label_from_rating"
                        ],
                        "corpus_split": document["corpus_split"],
                        "text_length_chars": text_length,
                        "text_sample": document["text"][:300],
                        "food_category_tags": business_metadata.get("food_category_tags"),
                    }
                )

    text_length_summary = {
        "count": len(text_length_values),
        "min": min(text_length_values) if text_length_values else None,
        "max": max(text_length_values) if text_length_values else None,
        "avg": round(sum(text_length_values) / len(text_length_values), 4)
        if text_length_values
        else None,
    }

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "food_reviews_path": str(food_reviews_path),
            "min_text_length": min_text_length,
            "max_text_length": max_text_length,
            "max_documents": max_documents,
        },
        "output": {
            "corpus_path": str(corpus_path),
            "summary_path": str(summary_path),
        },
        "counts": {
            "processed_count": processed_count,
            "invalid_json_count": invalid_json_count,
            "skipped_missing_required_count": skipped_missing_required_count,
            "skipped_short_text_count": skipped_short_text_count,
            "skipped_long_text_count": skipped_long_text_count,
            "kept_count": kept_count,
            "unique_document_id_count": len(unique_document_ids),
            "unique_review_id_count": len(unique_review_ids),
            "unique_business_id_count": len(unique_business_ids),
        },
        "date_range": {
            "min_date": min_date,
            "max_date": max_date,
        },
        "split_counts": dict(split_counts),
        "sentiment_counts": dict(sentiment_counts),
        "rating_counts": dict(rating_counts),
        "year_counts": dict(sorted(year_counts.items())),
        "top_states": [
            {"state": key, "total": value}
            for key, value in state_counts.most_common(20)
        ],
        "top_cities": [
            {"city": key, "total": value}
            for key, value in city_counts.most_common(20)
        ],
        "top_food_tags": [
            {"tag": key, "total": value}
            for key, value in food_tag_counts.most_common(50)
        ],
        "text_length_summary": text_length_summary,
        "examples": examples,
        "checks": {
            "food_reviews_file_exists": food_reviews_path.exists(),
            "processed_records": processed_count > 0,
            "invalid_json_is_zero": invalid_json_count == 0,
            "has_corpus_documents": kept_count > 0,
            "document_ids_are_unique": len(unique_document_ids) == kept_count,
            "review_ids_are_unique": len(unique_review_ids) == kept_count,
            "has_train_split": split_counts.get("train", 0) > 0,
            "has_validation_split": split_counts.get("validation", 0) > 0,
            "has_test_split": split_counts.get("test", 0) > 0,
            "has_positive_examples": sentiment_counts.get("positive", 0) > 0,
            "has_neutral_examples": sentiment_counts.get("neutral", 0) > 0,
            "has_negative_examples": sentiment_counts.get("negative", 0) > 0,
            "output_corpus_exists": corpus_path.exists(),
        },
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return summary


def save_artifact(summary: dict[str, Any], corpus_name: str) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{corpus_name}_summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    food_reviews_path = Path(args.food_reviews_path)
    output_dir = Path(args.output_dir)

    logger.info(
        "Construyendo Yelp NLP corpus | food_reviews_path=%s | corpus_name=%s | max_documents=%s",
        food_reviews_path,
        args.corpus_name,
        args.max_documents,
    )

    summary = build_corpus(
        food_reviews_path=food_reviews_path,
        output_dir=output_dir,
        corpus_name=args.corpus_name,
        min_text_length=args.min_text_length,
        max_text_length=args.max_text_length,
        max_documents=args.max_documents,
        sample_size=args.sample_size,
    )

    if args.save_artifact:
        artifact_path = save_artifact(summary, args.corpus_name)
        summary["artifact_path"] = str(artifact_path)

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in summary["checks"].items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Construcción Yelp NLP corpus completada con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Construcción Yelp NLP corpus completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())