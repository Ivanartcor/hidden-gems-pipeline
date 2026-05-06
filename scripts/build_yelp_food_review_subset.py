from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_REVIEW_PATH = (
    "data/external/yelp_open_dataset/extracted/yelp_academic_dataset_review.json"
)
DEFAULT_FOOD_BUSINESS_IDS_PATH = (
    "data/staging/yelp_open_dataset/food_business_ids.txt"
)
DEFAULT_FOOD_BUSINESSES_PATH = (
    "data/staging/yelp_open_dataset/food_businesses.jsonl"
)
DEFAULT_OUTPUT_DIR = "data/staging/yelp_open_dataset"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Construye un subset de reviews de Yelp asociadas a negocios gastronómicos."
        )
    )

    parser.add_argument(
        "--review-path",
        type=str,
        default=DEFAULT_REVIEW_PATH,
        help="Ruta a yelp_academic_dataset_review.json.",
    )

    parser.add_argument(
        "--food-business-ids-path",
        type=str,
        default=DEFAULT_FOOD_BUSINESS_IDS_PATH,
        help="Ruta a food_business_ids.txt.",
    )

    parser.add_argument(
        "--food-businesses-path",
        type=str,
        default=DEFAULT_FOOD_BUSINESSES_PATH,
        help="Ruta a food_businesses.jsonl para enriquecer metadata.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio de salida.",
    )

    parser.add_argument(
        "--min-text-length",
        type=int,
        default=40,
        help="Longitud mínima del texto de review para conservarla. Por defecto: 40.",
    )

    parser.add_argument(
        "--max-reviews",
        type=int,
        default=0,
        help="Máximo de reviews a guardar. 0 significa sin límite.",
    )

    parser.add_argument(
        "--max-lines",
        type=int,
        default=0,
        help="Máximo de líneas de review.json a escanear. 0 significa todo el fichero.",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Número de ejemplos a guardar en summary.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda summary también en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def load_food_business_ids(path: Path) -> set[str]:
    if not path.exists():
        raise FileNotFoundError(f"No existe food_business_ids.txt: {path}")

    business_ids = {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }

    if not business_ids:
        raise ValueError("food_business_ids.txt está vacío.")

    return business_ids


def load_food_business_metadata(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"No existe food_businesses.jsonl: {path}")

    metadata: dict[str, dict[str, Any]] = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue

            row = json.loads(line)
            if not isinstance(row, dict):
                continue

            business_id = row.get("business_id")
            if not business_id:
                continue

            metadata[str(business_id)] = {
                "business_id": row.get("business_id"),
                "business_name": row.get("name"),
                "city": row.get("city"),
                "state": row.get("state"),
                "stars_business": row.get("stars"),
                "review_count_business": row.get("review_count"),
                "is_open": row.get("is_open"),
                "categories_list": row.get("categories_list") or [],
                "food_category_tags": row.get("food_category_tags") or [],
                "food_confidence": row.get("food_confidence"),
            }

    return metadata


def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def build_review_record(
    *,
    row: dict[str, Any],
    business_metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    text = clean_text(row.get("text"))

    return {
        "source_system_code": "yelp_open_dataset",
        "source_dataset": "yelp_open_dataset",
        "source_entity_type": "yelp_review",
        "source_review_id": row.get("review_id"),
        "source_business_id": row.get("business_id"),
        "source_user_id": row.get("user_id"),
        "rating_value": row.get("stars"),
        "review_text_raw": text,
        "review_text_normalized": text,
        "review_date": row.get("date"),
        "useful_count": row.get("useful"),
        "funny_count": row.get("funny"),
        "cool_count": row.get("cool"),
        "text_length_chars": len(text) if text else 0,
        "business": business_metadata or {},
        "is_food_review_candidate": True,
        "is_training_eligible": True,
    }


def write_jsonl_line(file: Any, row: dict[str, Any]) -> None:
    file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def build_subset(
    *,
    review_path: Path,
    food_business_ids_path: Path,
    food_businesses_path: Path,
    output_dir: Path,
    min_text_length: int,
    max_reviews: int,
    max_lines: int,
    sample_size: int,
) -> dict[str, Any]:
    if not review_path.exists():
        raise FileNotFoundError(f"No existe review file: {review_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    food_business_ids = load_food_business_ids(food_business_ids_path)
    food_business_metadata = load_food_business_metadata(food_businesses_path)

    food_reviews_path = output_dir / "food_reviews.jsonl"
    summary_path = output_dir / "food_reviews_summary.json"

    processed_lines = 0
    invalid_json_count = 0
    matched_business_count = 0
    kept_review_count = 0
    skipped_short_text_count = 0
    skipped_missing_text_count = 0
    skipped_missing_business_metadata_count = 0

    unique_review_ids: set[str] = set()
    unique_business_ids_with_reviews: set[str] = set()

    stars_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    food_tag_counts: Counter[str] = Counter()

    text_length_values: list[int] = []
    examples: list[dict[str, Any]] = []

    min_date: str | None = None
    max_date: str | None = None

    with review_path.open("r", encoding="utf-8") as input_file, food_reviews_path.open(
        "w", encoding="utf-8"
    ) as output_file:
        for line_number, line in enumerate(input_file, start=1):
            if max_lines and processed_lines >= max_lines:
                break

            if max_reviews and kept_review_count >= max_reviews:
                break

            line = line.strip()
            if not line:
                continue

            processed_lines += 1

            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                invalid_json_count += 1
                continue

            if not isinstance(row, dict):
                invalid_json_count += 1
                continue

            business_id = row.get("business_id")
            if not business_id or str(business_id) not in food_business_ids:
                continue

            matched_business_count += 1

            text = clean_text(row.get("text"))
            if not text:
                skipped_missing_text_count += 1
                continue

            if len(text) < min_text_length:
                skipped_short_text_count += 1
                continue

            business_metadata = food_business_metadata.get(str(business_id))
            if not business_metadata:
                skipped_missing_business_metadata_count += 1
                continue

            record = build_review_record(
                row=row,
                business_metadata=business_metadata,
            )

            write_jsonl_line(output_file, record)

            kept_review_count += 1
            unique_review_ids.add(str(record["source_review_id"]))
            unique_business_ids_with_reviews.add(str(business_id))

            if record.get("rating_value") is not None:
                stars_counts[str(record["rating_value"])] += 1

            review_date = record.get("review_date")
            if isinstance(review_date, str) and review_date:
                year = review_date[:4]
                year_counts[year] += 1

                if min_date is None or review_date < min_date:
                    min_date = review_date

                if max_date is None or review_date > max_date:
                    max_date = review_date

            text_length_values.append(int(record["text_length_chars"]))

            state = business_metadata.get("state")
            city = business_metadata.get("city")

            if state:
                state_counts[str(state)] += 1

            if city:
                city_counts[str(city)] += 1

            for category in business_metadata.get("categories_list") or []:
                category_counts[str(category)] += 1

            for tag in business_metadata.get("food_category_tags") or []:
                food_tag_counts[str(tag)] += 1

            if len(examples) < sample_size:
                examples.append(
                    {
                        "source_review_id": record["source_review_id"],
                        "source_business_id": record["source_business_id"],
                        "business_name": business_metadata.get("business_name"),
                        "city": business_metadata.get("city"),
                        "state": business_metadata.get("state"),
                        "rating_value": record["rating_value"],
                        "review_date": record["review_date"],
                        "text_length_chars": record["text_length_chars"],
                        "text_sample": record["review_text_raw"][:300],
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
            "review_path": str(review_path),
            "food_business_ids_path": str(food_business_ids_path),
            "food_businesses_path": str(food_businesses_path),
            "min_text_length": min_text_length,
            "max_reviews": max_reviews,
            "max_lines": max_lines,
        },
        "output": {
            "food_reviews_path": str(food_reviews_path),
            "summary_path": str(summary_path),
        },
        "counts": {
            "food_business_id_count": len(food_business_ids),
            "business_metadata_count": len(food_business_metadata),
            "processed_lines": processed_lines,
            "invalid_json_count": invalid_json_count,
            "matched_business_count": matched_business_count,
            "kept_review_count": kept_review_count,
            "unique_review_id_count": len(unique_review_ids),
            "unique_business_ids_with_reviews": len(unique_business_ids_with_reviews),
            "skipped_missing_text_count": skipped_missing_text_count,
            "skipped_short_text_count": skipped_short_text_count,
            "skipped_missing_business_metadata_count": skipped_missing_business_metadata_count,
        },
        "date_range": {
            "min_date": min_date,
            "max_date": max_date,
        },
        "stars_counts": dict(stars_counts),
        "year_counts": dict(sorted(year_counts.items())),
        "top_states": [
            {"state": key, "total": value}
            for key, value in state_counts.most_common(20)
        ],
        "top_cities": [
            {"city": key, "total": value}
            for key, value in city_counts.most_common(20)
        ],
        "top_categories": [
            {"category": key, "total": value}
            for key, value in category_counts.most_common(50)
        ],
        "top_food_tags": [
            {"tag": key, "total": value}
            for key, value in food_tag_counts.most_common(50)
        ],
        "text_length_summary": text_length_summary,
        "examples": examples,
        "checks": {
            "review_file_exists": review_path.exists(),
            "food_business_ids_loaded": len(food_business_ids) > 0,
            "business_metadata_loaded": len(food_business_metadata) > 0,
            "processed_lines": processed_lines > 0,
            "invalid_json_is_zero": invalid_json_count == 0,
            "has_matched_reviews": matched_business_count > 0,
            "has_kept_reviews": kept_review_count > 0,
            "review_ids_are_unique": len(unique_review_ids) == kept_review_count,
            "business_metadata_complete_for_kept_reviews": (
                skipped_missing_business_metadata_count == 0
            ),
            "output_food_reviews_exists": food_reviews_path.exists(),
        },
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return summary


def save_artifact(summary: dict[str, Any]) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "food_reviews_summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    review_path = Path(args.review_path)
    food_business_ids_path = Path(args.food_business_ids_path)
    food_businesses_path = Path(args.food_businesses_path)
    output_dir = Path(args.output_dir)

    logger.info(
        "Construyendo subset Yelp food reviews | review_path=%s | min_text_length=%s | max_reviews=%s | max_lines=%s",
        review_path,
        args.min_text_length,
        args.max_reviews,
        args.max_lines,
    )

    summary = build_subset(
        review_path=review_path,
        food_business_ids_path=food_business_ids_path,
        food_businesses_path=food_businesses_path,
        output_dir=output_dir,
        min_text_length=args.min_text_length,
        max_reviews=args.max_reviews,
        max_lines=args.max_lines,
        sample_size=args.sample_size,
    )

    if args.save_artifact:
        artifact_path = save_artifact(summary)
        summary["artifact_path"] = str(artifact_path)

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in summary["checks"].items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Subset de Yelp food reviews completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Subset de Yelp food reviews completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())