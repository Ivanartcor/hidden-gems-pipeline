from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_BUSINESS_PATH = (
    "data/external/yelp_open_dataset/extracted/yelp_academic_dataset_business.json"
)

DEFAULT_OUTPUT_DIR = "data/staging/yelp_open_dataset"


FOOD_INCLUDE_CATEGORIES = {
    "restaurants",
    "food",
    "bars",
    "cafes",
    "coffee & tea",
    "breakfast & brunch",
    "bakeries",
    "desserts",
    "ice cream & frozen yogurt",
    "pizza",
    "burgers",
    "sandwiches",
    "seafood",
    "steakhouses",
    "sushi bars",
    "japanese",
    "chinese",
    "thai",
    "vietnamese",
    "korean",
    "mexican",
    "spanish",
    "italian",
    "mediterranean",
    "indian",
    "greek",
    "french",
    "american (traditional)",
    "american (new)",
    "gastropubs",
    "tapas bars",
    "wine bars",
    "cocktail bars",
    "sports bars",
    "pubs",
    "breweries",
    "delis",
    "diners",
    "food trucks",
    "specialty food",
    "chicken wings",
    "barbeque",
    "bbq",
    "latin american",
    "caribbean",
    "middle eastern",
    "vegetarian",
    "vegan",
    "salad",
    "soup",
    "ramen",
    "noodles",
    "food delivery services",
    "juice bars & smoothies",
    "comfort food",
    "ethnic food",
    "dive bars",
    "beer bar",
    "bubble tea",
    "brewpubs",
    "hot dogs",
}

NON_FOOD_EXCLUDE_CATEGORIES = {
    "dentists",
    "doctors",
    "medical centers",
    "health & medical",
    "hospitals",
    "veterinarians",
    "traditional chinese medicine",
    "naturopathic/holistic",
    "acupuncture",
    "nutritionists",
    "real estate",
    "home services",
    "auto repair",
    "automotive",
    "car dealers",
    "hotels",
    "travel services",
    "beauty & spas",
    "hair salons",
    "nail salons",
    "barbers",
    "gyms",
    "fitness & instruction",
    "education",
    "schools",
    "banks & credit unions",
    "financial services",
    "insurance",
    "lawyers",
    "professional services",
    "shopping centers",
    "apartments",
    "religious organizations",
    "drugstores",
}

STRONG_FOOD_CATEGORIES = {
    "restaurants",
    "food",
    "bars",
    "cafes",
    "coffee & tea",
    "breakfast & brunch",
    "bakeries",
    "pizza",
    "mexican",
    "italian",
    "spanish",
    "mediterranean",
    "tapas bars",
    "sushi bars",
    "seafood",
    "burgers",
    "sandwiches",
    "food trucks",
    "diners",
    "delis",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Construye un subset de negocios gastronómicos del Yelp Open Dataset."
    )

    parser.add_argument(
        "--business-path",
        type=str,
        default=DEFAULT_BUSINESS_PATH,
        help="Ruta a yelp_academic_dataset_business.json.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Directorio de salida para food_businesses.jsonl y food_business_ids.txt.",
    )

    parser.add_argument(
        "--open-only",
        action="store_true",
        help="Conserva solo negocios con is_open = 1.",
    )

    parser.add_argument(
        "--min-review-count",
        type=int,
        default=1,
        help="Mínimo de reviews del negocio para incluirlo. Por defecto: 1.",
    )

    parser.add_argument(
        "--max-businesses",
        type=int,
        default=0,
        help="Máximo de negocios a guardar. 0 significa sin límite.",
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


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def parse_categories(value: Any) -> list[str]:
    """
    La documentación de Yelp presenta categories como array, pero algunas
    versiones del dataset pueden traerlo como string separado por comas.
    Este parser soporta ambos formatos.
    """
    if value is None:
        return []

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    if isinstance(value, str):
        return [
            item.strip()
            for item in value.split(",")
            if item.strip()
        ]

    return []


def normalize_category(value: Any) -> str:
    text = normalize_text(value)
    text = text.replace("&amp;", "&")
    return text


def category_matches_exact(category: str, allowed_categories: set[str]) -> bool:
    category_norm = normalize_category(category)
    return category_norm in allowed_categories


def classify_food_business(categories: list[str]) -> tuple[bool, list[str], list[str], float]:
    normalized_categories = [
        normalize_category(category)
        for category in categories
    ]

    include_matches: list[str] = []
    exclude_matches: list[str] = []

    for original_category, normalized_category in zip(categories, normalized_categories):
        if normalized_category in FOOD_INCLUDE_CATEGORIES:
            include_matches.append(original_category)

        if normalized_category in NON_FOOD_EXCLUDE_CATEGORIES:
            exclude_matches.append(original_category)

    strong_matches = [
        original_category
        for original_category, normalized_category in zip(categories, normalized_categories)
        if normalized_category in STRONG_FOOD_CATEGORIES
    ]

    has_strong_food_signal = bool(strong_matches)
    has_food_signal = bool(include_matches)
    has_non_food_signal = bool(exclude_matches)

    # Caso claro: negocio gastronómico.
    if has_strong_food_signal:
        return True, sorted(set(include_matches)), sorted(set(exclude_matches)), 0.95

    # Caso aceptable: tiene categoría food pero no señales no-food.
    if has_food_signal and not has_non_food_signal:
        return True, sorted(set(include_matches)), sorted(set(exclude_matches)), 0.85

    # Caso mixto: si solo hay señales débiles y además señales no-food, se descarta.
    if has_food_signal and has_non_food_signal:
        return False, sorted(set(include_matches)), sorted(set(exclude_matches)), 0.40

    return False, [], sorted(set(exclude_matches)), 0.0



def build_food_business_record(row: dict[str, Any]) -> dict[str, Any]:
    categories = parse_categories(row.get("categories"))
    is_food, food_matches, non_food_matches, confidence = classify_food_business(categories)

    return {
        "business_id": row.get("business_id"),
        "name": row.get("name"),
        "address": row.get("address"),
        "city": row.get("city"),
        "state": row.get("state"),
        "postal_code": row.get("postal_code") or row.get("postal code"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
        "stars": row.get("stars"),
        "review_count": row.get("review_count"),
        "is_open": row.get("is_open"),
        "categories_raw": row.get("categories"),
        "categories_list": categories,
        "attributes": row.get("attributes"),
        "hours": row.get("hours"),
        "is_food_business": is_food,
        "food_category_tags": food_matches,
        "non_food_category_tags": non_food_matches,
        "food_confidence": confidence,
        "source_payload": row,
    }


def should_keep_business(
    *,
    record: dict[str, Any],
    open_only: bool,
    min_review_count: int,
) -> bool:
    if not record["is_food_business"]:
        return False

    if open_only and int(record.get("is_open") or 0) != 1:
        return False

    review_count = record.get("review_count")
    if isinstance(review_count, (int, float)):
        if int(review_count) < min_review_count:
            return False
    else:
        if min_review_count > 0:
            return False

    return True


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def write_ids(path: Path, business_ids: list[str]) -> None:
    path.write_text(
        "\n".join(business_ids) + ("\n" if business_ids else ""),
        encoding="utf-8",
    )


def build_subset(
    *,
    business_path: Path,
    output_dir: Path,
    open_only: bool,
    min_review_count: int,
    max_businesses: int,
    sample_size: int,
) -> dict[str, Any]:
    if not business_path.exists():
        raise FileNotFoundError(f"No existe business file: {business_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    food_businesses_path = output_dir / "food_businesses.jsonl"
    food_business_ids_path = output_dir / "food_business_ids.txt"
    summary_path = output_dir / "food_businesses_summary.json"

    processed_count = 0
    invalid_json_count = 0
    food_candidate_count = 0
    kept_count = 0

    kept_rows: list[dict[str, Any]] = []
    business_ids: list[str] = []

    state_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    food_tag_counts: Counter[str] = Counter()
    stars_counts: Counter[str] = Counter()
    is_open_counts: Counter[str] = Counter()

    examples: list[dict[str, Any]] = []

    with business_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
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

            record = build_food_business_record(row)

            if record["is_food_business"]:
                food_candidate_count += 1

            if not should_keep_business(
                record=record,
                open_only=open_only,
                min_review_count=min_review_count,
            ):
                continue

            business_id = record.get("business_id")
            if not business_id:
                continue

            kept_rows.append(record)
            business_ids.append(str(business_id))
            kept_count += 1

            if record.get("state"):
                state_counts[str(record["state"])] += 1

            if record.get("city"):
                city_counts[str(record["city"])] += 1

            if record.get("stars") is not None:
                stars_counts[str(record["stars"])] += 1

            if record.get("is_open") is not None:
                is_open_counts[str(record["is_open"])] += 1

            for category in record["categories_list"]:
                category_counts[category] += 1

            for tag in record["food_category_tags"]:
                food_tag_counts[tag] += 1

            if len(examples) < sample_size:
                examples.append(
                    {
                        "business_id": record["business_id"],
                        "name": record["name"],
                        "city": record["city"],
                        "state": record["state"],
                        "stars": record["stars"],
                        "review_count": record["review_count"],
                        "is_open": record["is_open"],
                        "categories_list": record["categories_list"],
                        "food_category_tags": record["food_category_tags"],
                        "food_confidence": record["food_confidence"],
                    }
                )

            if max_businesses and kept_count >= max_businesses:
                break

    write_jsonl(food_businesses_path, kept_rows)
    write_ids(food_business_ids_path, business_ids)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "business_path": str(business_path),
            "open_only": open_only,
            "min_review_count": min_review_count,
            "max_businesses": max_businesses,
        },
        "output": {
            "food_businesses_path": str(food_businesses_path),
            "food_business_ids_path": str(food_business_ids_path),
            "summary_path": str(summary_path),
        },
        "counts": {
            "processed_count": processed_count,
            "invalid_json_count": invalid_json_count,
            "food_candidate_count": food_candidate_count,
            "kept_count": kept_count,
            "unique_business_id_count": len(set(business_ids)),
        },
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
        "stars_counts": dict(stars_counts),
        "is_open_counts": dict(is_open_counts),
        "examples": examples,
        "checks": {
            "input_file_exists": business_path.exists(),
            "processed_records": processed_count > 0,
            "invalid_json_is_zero": invalid_json_count == 0,
            "has_food_businesses": kept_count > 0,
            "business_ids_are_unique": len(set(business_ids)) == len(business_ids),
            "output_food_businesses_exists": food_businesses_path.exists(),
            "output_food_business_ids_exists": food_business_ids_path.exists(),
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

    output_path = output_dir / "food_businesses_summary.json"
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    business_path = Path(args.business_path)
    output_dir = Path(args.output_dir)

    logger.info(
        "Construyendo subset Yelp food businesses | business_path=%s | open_only=%s | min_review_count=%s | max_businesses=%s",
        business_path,
        args.open_only,
        args.min_review_count,
        args.max_businesses,
    )

    summary = build_subset(
        business_path=business_path,
        output_dir=output_dir,
        open_only=args.open_only,
        min_review_count=args.min_review_count,
        max_businesses=args.max_businesses,
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
            "Subset de Yelp food businesses completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Subset de Yelp food businesses completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())