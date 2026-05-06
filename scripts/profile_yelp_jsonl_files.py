from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_BUSINESS_PATH = (
    "data/external/yelp_open_dataset/extracted/yelp_academic_dataset_business.json"
)
DEFAULT_REVIEW_PATH = (
    "data/external/yelp_open_dataset/extracted/yelp_academic_dataset_review.json"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Perfila los ficheros JSON Lines extraídos del Yelp Open Dataset "
            "sin cargarlos completos en memoria."
        )
    )

    parser.add_argument(
        "--business-path",
        type=str,
        default=DEFAULT_BUSINESS_PATH,
        help="Ruta a yelp_academic_dataset_business.json.",
    )

    parser.add_argument(
        "--review-path",
        type=str,
        default=DEFAULT_REVIEW_PATH,
        help="Ruta a yelp_academic_dataset_review.json.",
    )

    parser.add_argument(
        "--max-business-lines",
        type=int,
        default=0,
        help=(
            "Número máximo de líneas de business a perfilar. "
            "0 significa escaneo completo. Recomendado completo porque pesa ~113 MB."
        ),
    )

    parser.add_argument(
        "--max-review-lines",
        type=int,
        default=100_000,
        help=(
            "Número máximo de líneas de review a perfilar. "
            "0 significa escaneo completo, pero puede tardar bastante por ser ~5 GB."
        ),
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=5,
        help="Número de ejemplos a guardar por fichero.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el perfil en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def infer_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def safe_len_text(value: Any) -> int:
    if not isinstance(value, str):
        return 0
    return len(value)


def parse_categories(value: Any) -> list[str]:
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


def update_field_profile(
    *,
    row: dict[str, Any],
    key_counter: Counter[str],
    null_counter: Counter[str],
    type_counter: dict[str, Counter[str]],
) -> None:
    for key, value in row.items():
        key_counter[key] += 1

        if value is None:
            null_counter[key] += 1

        if isinstance(value, str) and value.strip() == "":
            null_counter[key] += 1

        type_counter[key][infer_type(value)] += 1


def finalize_field_profile(
    *,
    processed_count: int,
    key_counter: Counter[str],
    null_counter: Counter[str],
    type_counter: dict[str, Counter[str]],
) -> list[dict[str, Any]]:
    fields: list[dict[str, Any]] = []

    for key in sorted(key_counter.keys()):
        present_count = key_counter[key]
        null_like_count = null_counter[key]

        fields.append(
            {
                "field": key,
                "present_count": present_count,
                "present_ratio": round(present_count / processed_count, 6)
                if processed_count
                else 0,
                "null_like_count": null_like_count,
                "null_like_ratio": round(null_like_count / processed_count, 6)
                if processed_count
                else 0,
                "types": dict(type_counter[key]),
            }
        )

    return fields


def compute_numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "avg": None,
        }

    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "avg": round(sum(values) / len(values), 4),
    }


def count_physical_lines(path: Path, chunk_size: int = 1024 * 1024) -> int:
    count = 0

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            count += chunk.count(b"\n")

    return count


def profile_business_file(
    *,
    path: Path,
    max_lines: int,
    sample_size: int,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe business file: {path}")

    key_counter: Counter[str] = Counter()
    null_counter: Counter[str] = Counter()
    type_counter: dict[str, Counter[str]] = defaultdict(Counter)

    state_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    is_open_counts: Counter[str] = Counter()
    stars_counts: Counter[str] = Counter()

    review_count_values: list[float] = []
    latitude_values: list[float] = []
    longitude_values: list[float] = []

    examples: list[dict[str, Any]] = []
    invalid_json_count = 0
    processed_count = 0
    physical_line_count = count_physical_lines(path)

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if max_lines and processed_count >= max_lines:
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

            update_field_profile(
                row=row,
                key_counter=key_counter,
                null_counter=null_counter,
                type_counter=type_counter,
            )

            state = row.get("state")
            city = row.get("city")
            is_open = row.get("is_open")
            stars = row.get("stars")
            review_count = row.get("review_count")
            latitude = row.get("latitude")
            longitude = row.get("longitude")

            if state is not None:
                state_counts[str(state)] += 1

            if city is not None:
                city_counts[str(city)] += 1

            if is_open is not None:
                is_open_counts[str(is_open)] += 1

            if stars is not None:
                stars_counts[str(stars)] += 1

            if isinstance(review_count, (int, float)):
                review_count_values.append(float(review_count))

            if isinstance(latitude, (int, float)):
                latitude_values.append(float(latitude))

            if isinstance(longitude, (int, float)):
                longitude_values.append(float(longitude))

            for category in parse_categories(row.get("categories")):
                category_counts[category] += 1

            if len(examples) < sample_size:
                examples.append(
                    {
                        "business_id": row.get("business_id"),
                        "name": row.get("name"),
                        "city": row.get("city"),
                        "state": row.get("state"),
                        "stars": row.get("stars"),
                        "review_count": row.get("review_count"),
                        "is_open": row.get("is_open"),
                        "categories": row.get("categories"),
                    }
                )

    return {
        "file_path": str(path),
        "file_size_bytes": path.stat().st_size,
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 3),
        "physical_line_count": physical_line_count,
        "processed_count": processed_count,
        "scan_is_complete": max_lines == 0 or processed_count < max_lines,
        "invalid_json_count": invalid_json_count,
        "field_profile": finalize_field_profile(
            processed_count=processed_count,
            key_counter=key_counter,
            null_counter=null_counter,
            type_counter=type_counter,
        ),
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
        "is_open_counts": dict(is_open_counts),
        "stars_counts": dict(stars_counts),
        "review_count_summary": compute_numeric_summary(review_count_values),
        "latitude_summary": compute_numeric_summary(latitude_values),
        "longitude_summary": compute_numeric_summary(longitude_values),
        "examples": examples,
    }


def profile_review_file(
    *,
    path: Path,
    max_lines: int,
    sample_size: int,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"No existe review file: {path}")

    key_counter: Counter[str] = Counter()
    null_counter: Counter[str] = Counter()
    type_counter: dict[str, Counter[str]] = defaultdict(Counter)

    stars_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()

    useful_values: list[float] = []
    funny_values: list[float] = []
    cool_values: list[float] = []
    text_length_values: list[float] = []

    examples: list[dict[str, Any]] = []
    invalid_json_count = 0
    processed_count = 0
    physical_line_count = count_physical_lines(path)

    min_date: str | None = None
    max_date: str | None = None

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if max_lines and processed_count >= max_lines:
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

            update_field_profile(
                row=row,
                key_counter=key_counter,
                null_counter=null_counter,
                type_counter=type_counter,
            )

            stars = row.get("stars")
            date = row.get("date")
            useful = row.get("useful")
            funny = row.get("funny")
            cool = row.get("cool")
            text = row.get("text")

            if stars is not None:
                stars_counts[str(stars)] += 1

            if isinstance(date, str) and date:
                date_prefix = date[:4]
                year_counts[date_prefix] += 1

                if min_date is None or date < min_date:
                    min_date = date

                if max_date is None or date > max_date:
                    max_date = date

            if isinstance(useful, (int, float)):
                useful_values.append(float(useful))

            if isinstance(funny, (int, float)):
                funny_values.append(float(funny))

            if isinstance(cool, (int, float)):
                cool_values.append(float(cool))

            if isinstance(text, str):
                text_length_values.append(float(len(text)))

            if len(examples) < sample_size:
                examples.append(
                    {
                        "review_id": row.get("review_id"),
                        "business_id": row.get("business_id"),
                        "stars": row.get("stars"),
                        "date": row.get("date"),
                        "text_sample": str(row.get("text") or "")[:300],
                        "useful": row.get("useful"),
                        "funny": row.get("funny"),
                        "cool": row.get("cool"),
                    }
                )

    return {
        "file_path": str(path),
        "file_size_bytes": path.stat().st_size,
        "file_size_mb": round(path.stat().st_size / (1024 * 1024), 3),
        "physical_line_count": physical_line_count,
        "processed_count": processed_count,
        "scan_is_complete": max_lines == 0 or processed_count < max_lines,
        "invalid_json_count": invalid_json_count,
        "field_profile": finalize_field_profile(
            processed_count=processed_count,
            key_counter=key_counter,
            null_counter=null_counter,
            type_counter=type_counter,
        ),
        "stars_counts": dict(stars_counts),
        "year_counts": dict(year_counts.most_common()),
        "date_range": {
            "min_date": min_date,
            "max_date": max_date,
        },
        "text_length_summary": compute_numeric_summary(text_length_values),
        "useful_summary": compute_numeric_summary(useful_values),
        "funny_summary": compute_numeric_summary(funny_values),
        "cool_summary": compute_numeric_summary(cool_values),
        "examples": examples,
    }


def save_artifact(profile: dict[str, Any]) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "yelp_jsonl_profile.json"
    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    business_path = Path(args.business_path)
    review_path = Path(args.review_path)

    logger.info(
        "Perfilando Yelp JSONL | business=%s | review=%s | max_review_lines=%s",
        business_path,
        review_path,
        args.max_review_lines,
    )

    business_profile = profile_business_file(
        path=business_path,
        max_lines=args.max_business_lines,
        sample_size=args.sample_size,
    )

    review_profile = profile_review_file(
        path=review_path,
        max_lines=args.max_review_lines,
        sample_size=args.sample_size,
    )

    profile = {
        "profiled_at": datetime.now(timezone.utc).isoformat(),
        "business_profile": business_profile,
        "review_profile": review_profile,
        "checks": {
            "business_file_exists": business_path.exists(),
            "review_file_exists": review_path.exists(),
            "business_has_records": business_profile["processed_count"] > 0,
            "review_has_records": review_profile["processed_count"] > 0,
            "business_invalid_json_is_zero": business_profile["invalid_json_count"] == 0,
            "review_invalid_json_is_zero": review_profile["invalid_json_count"] == 0,
            "business_has_business_id_field": any(
                field["field"] == "business_id"
                for field in business_profile["field_profile"]
            ),
            "business_has_categories_field": any(
                field["field"] == "categories"
                for field in business_profile["field_profile"]
            ),
            "review_has_review_id_field": any(
                field["field"] == "review_id"
                for field in review_profile["field_profile"]
            ),
            "review_has_business_id_field": any(
                field["field"] == "business_id"
                for field in review_profile["field_profile"]
            ),
            "review_has_text_field": any(
                field["field"] == "text"
                for field in review_profile["field_profile"]
            ),
        },
    }

    if args.save_artifact:
        artifact_path = save_artifact(profile)
        profile["artifact_path"] = str(artifact_path)

    print(json.dumps(profile, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in profile["checks"].items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Perfilado Yelp JSONL completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Perfilado Yelp JSONL completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())