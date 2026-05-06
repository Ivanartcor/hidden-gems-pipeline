from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_CORPUS_PATH = (
    "data/artifacts/nlp_corpus/yelp_food_reviews_corpus_sample_100k_lines.jsonl"
)


REQUIRED_FIELDS = {
    "corpus_document_id",
    "source_system_code",
    "source_dataset",
    "source_entity_type",
    "source_review_id",
    "source_business_id",
    "text",
    "text_normalized",
    "language",
    "rating_value",
    "sentiment_label_from_rating",
    "review_date",
    "corpus_split",
    "task_scope",
    "is_training_eligible",
    "quality_flags",
    "business_metadata",
    "source_metrics",
    "created_at",
}


VALID_SPLITS = {"train", "validation", "test"}
VALID_SENTIMENT_LABELS = {"positive", "neutral", "negative"}
VALID_SOURCE_SYSTEM_CODE = "yelp_open_dataset"
VALID_SOURCE_ENTITY_TYPE = "yelp_review"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba la calidad del corpus NLP construido desde Yelp Open Dataset."
    )

    parser.add_argument(
        "--corpus-path",
        type=str,
        default=DEFAULT_CORPUS_PATH,
        help="Ruta al corpus JSONL generado por build_yelp_nlp_corpus.",
    )

    parser.add_argument(
        "--summary-path",
        type=str,
        default=None,
        help=(
            "Ruta opcional al summary del corpus. "
            "Si no se indica, se intenta inferir como <corpus_path>_summary.json."
        ),
    )

    parser.add_argument(
        "--min-text-length",
        type=int,
        default=80,
        help="Longitud mínima esperada del texto. Por defecto: 80.",
    )

    parser.add_argument(
        "--max-text-length",
        type=int,
        default=5000,
        help="Longitud máxima esperada del texto. Por defecto: 5000.",
    )

    parser.add_argument(
        "--max-documents",
        type=int,
        default=0,
        help=(
            "Número máximo de documentos a revisar. "
            "0 significa revisar todo el corpus."
        ),
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=20,
        help="Número de ejemplos e incidencias a incluir en la salida.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el check en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def infer_summary_path(corpus_path: Path) -> Path:
    return corpus_path.with_name(f"{corpus_path.stem}_summary.json")


def load_summary(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None

    if not path.exists():
        return None

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        return None

    return data


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def expected_sentiment_from_rating(rating_value: Any) -> str | None:
    rating = as_float(rating_value)

    if rating is None:
        return None

    if rating >= 4:
        return "positive"

    if rating <= 2:
        return "negative"

    return "neutral"


def validate_document(
    *,
    document: dict[str, Any],
    line_number: int,
    min_text_length: int,
    max_text_length: int,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    missing_fields = [
        field
        for field in REQUIRED_FIELDS
        if field not in document
    ]

    if missing_fields:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_required_fields",
                "severity": "error",
                "message": "El documento no contiene todos los campos requeridos.",
                "fields": missing_fields,
                "corpus_document_id": document.get("corpus_document_id"),
            }
        )

    corpus_document_id = document.get("corpus_document_id")
    source_review_id = document.get("source_review_id")
    source_business_id = document.get("source_business_id")
    text = document.get("text")
    text_normalized = document.get("text_normalized")
    language = document.get("language")
    rating_value = document.get("rating_value")
    sentiment_label = document.get("sentiment_label_from_rating")
    corpus_split = document.get("corpus_split")
    task_scope = document.get("task_scope")
    quality_flags = document.get("quality_flags")
    business_metadata = document.get("business_metadata")

    if not is_non_empty_string(corpus_document_id):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_corpus_document_id",
                "severity": "error",
                "message": "corpus_document_id está vacío.",
            }
        )

    if not is_non_empty_string(source_review_id):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_source_review_id",
                "severity": "error",
                "message": "source_review_id está vacío.",
                "corpus_document_id": corpus_document_id,
            }
        )

    if not is_non_empty_string(source_business_id):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_source_business_id",
                "severity": "error",
                "message": "source_business_id está vacío.",
                "corpus_document_id": corpus_document_id,
            }
        )

    if document.get("source_system_code") != VALID_SOURCE_SYSTEM_CODE:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_source_system_code",
                "severity": "error",
                "message": "source_system_code no coincide con yelp_open_dataset.",
                "value": document.get("source_system_code"),
                "corpus_document_id": corpus_document_id,
            }
        )

    if document.get("source_entity_type") != VALID_SOURCE_ENTITY_TYPE:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_source_entity_type",
                "severity": "error",
                "message": "source_entity_type no coincide con yelp_review.",
                "value": document.get("source_entity_type"),
                "corpus_document_id": corpus_document_id,
            }
        )

    if not is_non_empty_string(text):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_text",
                "severity": "error",
                "message": "El texto está vacío.",
                "corpus_document_id": corpus_document_id,
            }
        )
    else:
        text_length = len(text)

        if text_length < min_text_length:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "text_too_short",
                    "severity": "warning",
                    "message": "El texto está por debajo de la longitud mínima.",
                    "text_length": text_length,
                    "min_text_length": min_text_length,
                    "corpus_document_id": corpus_document_id,
                }
            )

        if text_length > max_text_length:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "text_too_long",
                    "severity": "warning",
                    "message": "El texto supera la longitud máxima.",
                    "text_length": text_length,
                    "max_text_length": max_text_length,
                    "corpus_document_id": corpus_document_id,
                }
            )

    if not is_non_empty_string(text_normalized):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_text_normalized",
                "severity": "warning",
                "message": "text_normalized está vacío.",
                "corpus_document_id": corpus_document_id,
            }
        )

    if not is_non_empty_string(language):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_language",
                "severity": "warning",
                "message": "language está vacío.",
                "corpus_document_id": corpus_document_id,
            }
        )

    rating = as_float(rating_value)
    if rating is None or not (1 <= rating <= 5):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_rating_value",
                "severity": "error",
                "message": "rating_value no es válido.",
                "value": rating_value,
                "corpus_document_id": corpus_document_id,
            }
        )

    if corpus_split not in VALID_SPLITS:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_corpus_split",
                "severity": "error",
                "message": "corpus_split no pertenece a train/validation/test.",
                "value": corpus_split,
                "corpus_document_id": corpus_document_id,
            }
        )

    if sentiment_label not in VALID_SENTIMENT_LABELS:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_sentiment_label",
                "severity": "error",
                "message": "sentiment_label_from_rating no es válido.",
                "value": sentiment_label,
                "corpus_document_id": corpus_document_id,
            }
        )
    else:
        expected_label = expected_sentiment_from_rating(rating_value)
        if expected_label is not None and sentiment_label != expected_label:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "sentiment_label_mismatch",
                    "severity": "error",
                    "message": "El sentimiento derivado no coincide con el rating.",
                    "rating_value": rating_value,
                    "expected_label": expected_label,
                    "received_label": sentiment_label,
                    "corpus_document_id": corpus_document_id,
                }
            )

    if not isinstance(task_scope, list) or not task_scope:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_task_scope",
                "severity": "warning",
                "message": "task_scope no es una lista válida.",
                "corpus_document_id": corpus_document_id,
            }
        )

    if document.get("is_training_eligible") is not True:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "not_training_eligible",
                "severity": "warning",
                "message": "is_training_eligible no está marcado como true.",
                "corpus_document_id": corpus_document_id,
            }
        )

    if not isinstance(quality_flags, dict):
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "invalid_quality_flags",
                "severity": "warning",
                "message": "quality_flags no es un objeto válido.",
                "corpus_document_id": corpus_document_id,
            }
        )
    else:
        if quality_flags.get("has_text") is not True:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "quality_flag_has_text_false",
                    "severity": "warning",
                    "message": "quality_flags.has_text no es true.",
                    "corpus_document_id": corpus_document_id,
                }
            )

        if quality_flags.get("has_rating") is not True:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "quality_flag_has_rating_false",
                    "severity": "warning",
                    "message": "quality_flags.has_rating no es true.",
                    "corpus_document_id": corpus_document_id,
                }
            )

    if not isinstance(business_metadata, dict) or not business_metadata:
        issues.append(
            {
                "line_number": line_number,
                "issue_code": "missing_business_metadata",
                "severity": "warning",
                "message": "business_metadata está vacío o no es objeto.",
                "corpus_document_id": corpus_document_id,
            }
        )
    else:
        categories = business_metadata.get("categories_list")
        tags = business_metadata.get("food_category_tags")

        if not isinstance(categories, list) or not categories:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "missing_business_categories",
                    "severity": "warning",
                    "message": "business_metadata.categories_list está vacío.",
                    "corpus_document_id": corpus_document_id,
                }
            )

        if not isinstance(tags, list) or not tags:
            issues.append(
                {
                    "line_number": line_number,
                    "issue_code": "missing_food_category_tags",
                    "severity": "warning",
                    "message": "business_metadata.food_category_tags está vacío.",
                    "corpus_document_id": corpus_document_id,
                }
            )

    return issues


def compute_text_length_summary(values: list[int]) -> dict[str, Any]:
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


def check_corpus(
    *,
    corpus_path: Path,
    summary: dict[str, Any] | None,
    min_text_length: int,
    max_text_length: int,
    max_documents: int,
    sample_size: int,
) -> dict[str, Any]:
    if not corpus_path.exists():
        raise FileNotFoundError(f"No existe el corpus: {corpus_path}")

    processed_count = 0
    invalid_json_count = 0

    document_ids: set[str] = set()
    review_ids: set[str] = set()
    business_ids: set[str] = set()

    duplicate_document_ids: list[str] = []
    duplicate_review_ids: list[str] = []

    split_counts: Counter[str] = Counter()
    sentiment_counts: Counter[str] = Counter()
    rating_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    year_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    city_counts: Counter[str] = Counter()
    food_tag_counts: Counter[str] = Counter()
    issue_code_counts: Counter[str] = Counter()
    issue_severity_counts: Counter[str] = Counter()

    text_length_values: list[int] = []

    issues_sample: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    with corpus_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if max_documents and processed_count >= max_documents:
                break

            line = line.strip()
            if not line:
                continue

            try:
                document = json.loads(line)
            except json.JSONDecodeError as exc:
                invalid_json_count += 1

                issue = {
                    "line_number": line_number,
                    "issue_code": "invalid_json",
                    "severity": "error",
                    "message": str(exc),
                }

                issue_code_counts["invalid_json"] += 1
                issue_severity_counts["error"] += 1

                if len(issues_sample) < sample_size:
                    issues_sample.append(issue)

                continue

            if not isinstance(document, dict):
                invalid_json_count += 1

                issue = {
                    "line_number": line_number,
                    "issue_code": "invalid_document_structure",
                    "severity": "error",
                    "message": "La línea JSON no contiene un objeto.",
                }

                issue_code_counts["invalid_document_structure"] += 1
                issue_severity_counts["error"] += 1

                if len(issues_sample) < sample_size:
                    issues_sample.append(issue)

                continue

            processed_count += 1

            corpus_document_id = document.get("corpus_document_id")
            source_review_id = document.get("source_review_id")
            source_business_id = document.get("source_business_id")
            text = document.get("text")
            rating_value = document.get("rating_value")
            sentiment_label = document.get("sentiment_label_from_rating")
            corpus_split = document.get("corpus_split")
            language = document.get("language")
            review_date = document.get("review_date")
            business_metadata = document.get("business_metadata") or {}

            if isinstance(corpus_document_id, str):
                if corpus_document_id in document_ids:
                    duplicate_document_ids.append(corpus_document_id)
                document_ids.add(corpus_document_id)

            if isinstance(source_review_id, str):
                if source_review_id in review_ids:
                    duplicate_review_ids.append(source_review_id)
                review_ids.add(source_review_id)

            if isinstance(source_business_id, str):
                business_ids.add(source_business_id)

            if isinstance(text, str):
                text_length_values.append(len(text))

            if corpus_split:
                split_counts[str(corpus_split)] += 1

            if sentiment_label:
                sentiment_counts[str(sentiment_label)] += 1

            if rating_value is not None:
                rating_counts[str(rating_value)] += 1

            if language:
                language_counts[str(language)] += 1

            if isinstance(review_date, str) and review_date:
                year_counts[review_date[:4]] += 1

            state = business_metadata.get("state")
            city = business_metadata.get("city")

            if state:
                state_counts[str(state)] += 1

            if city:
                city_counts[str(city)] += 1

            for tag in business_metadata.get("food_category_tags") or []:
                food_tag_counts[str(tag)] += 1

            document_issues = validate_document(
                document=document,
                line_number=line_number,
                min_text_length=min_text_length,
                max_text_length=max_text_length,
            )

            for issue in document_issues:
                issue_code_counts[issue["issue_code"]] += 1
                issue_severity_counts[issue["severity"]] += 1

                if len(issues_sample) < sample_size:
                    issues_sample.append(issue)

            if len(examples) < sample_size:
                examples.append(
                    {
                        "corpus_document_id": corpus_document_id,
                        "source_review_id": source_review_id,
                        "source_business_id": source_business_id,
                        "business_name": business_metadata.get("business_name"),
                        "city": business_metadata.get("city"),
                        "state": business_metadata.get("state"),
                        "rating_value": rating_value,
                        "sentiment_label_from_rating": sentiment_label,
                        "corpus_split": corpus_split,
                        "language": language,
                        "text_length_chars": len(text) if isinstance(text, str) else None,
                        "text_sample": text[:300] if isinstance(text, str) else None,
                        "food_category_tags": business_metadata.get("food_category_tags"),
                    }
                )

    summary_counts = (summary or {}).get("counts") or {}
    expected_kept_count = summary_counts.get("kept_count")

    scanned_all = max_documents == 0

    checks = {
        "corpus_file_exists": corpus_path.exists(),
        "processed_documents": processed_count > 0,
        "invalid_json_is_zero": invalid_json_count == 0,
        "document_ids_are_unique": len(document_ids) == processed_count,
        "review_ids_are_unique": len(review_ids) == processed_count,
        "has_business_ids": len(business_ids) > 0,
        "has_train_split": split_counts.get("train", 0) > 0,
        "has_validation_split": split_counts.get("validation", 0) > 0,
        "has_test_split": split_counts.get("test", 0) > 0,
        "has_positive_examples": sentiment_counts.get("positive", 0) > 0,
        "has_neutral_examples": sentiment_counts.get("neutral", 0) > 0,
        "has_negative_examples": sentiment_counts.get("negative", 0) > 0,
        "has_language": sum(language_counts.values()) == processed_count,
        "has_no_error_issues": issue_severity_counts.get("error", 0) == 0,
        "has_no_warning_issues": issue_severity_counts.get("warning", 0) == 0,
        "matches_summary_kept_count_when_full_scan": (
            True
            if not scanned_all or expected_kept_count is None
            else int(expected_kept_count) == processed_count
        ),
    }

    return {
        "corpus_path": str(corpus_path),
        "summary_loaded": summary is not None,
        "scan": {
            "max_documents": max_documents,
            "scanned_all": scanned_all,
        },
        "counts": {
            "processed_count": processed_count,
            "invalid_json_count": invalid_json_count,
            "unique_document_id_count": len(document_ids),
            "unique_review_id_count": len(review_ids),
            "unique_business_id_count": len(business_ids),
            "duplicate_document_id_count": len(duplicate_document_ids),
            "duplicate_review_id_count": len(duplicate_review_ids),
        },
        "summary_counts": summary_counts,
        "split_counts": dict(split_counts),
        "sentiment_counts": dict(sentiment_counts),
        "rating_counts": dict(rating_counts),
        "language_counts": dict(language_counts),
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
        "text_length_summary": compute_text_length_summary(text_length_values),
        "issue_profile": {
            "by_code": dict(issue_code_counts),
            "by_severity": dict(issue_severity_counts),
            "issues_sample": issues_sample,
        },
        "duplicate_samples": {
            "document_ids": duplicate_document_ids[:sample_size],
            "review_ids": duplicate_review_ids[:sample_size],
        },
        "examples": examples,
        "checks": checks,
    }


def save_artifact(output: dict[str, Any], corpus_path: Path) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"{corpus_path.stem}_check.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    corpus_path = Path(args.corpus_path)

    if args.summary_path:
        summary_path = Path(args.summary_path)
    else:
        summary_path = infer_summary_path(corpus_path)

    summary = load_summary(summary_path)

    logger.info(
        "Comprobando Yelp NLP corpus | corpus_path=%s | summary_path=%s | max_documents=%s",
        corpus_path,
        summary_path,
        args.max_documents,
    )

    output = check_corpus(
        corpus_path=corpus_path,
        summary=summary,
        min_text_length=args.min_text_length,
        max_text_length=args.max_text_length,
        max_documents=args.max_documents,
        sample_size=args.sample_size,
    )

    output["summary_path"] = str(summary_path) if summary_path else None

    if args.save_artifact:
        artifact_path = save_artifact(output, corpus_path)
        output["artifact_path"] = str(artifact_path)

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in output["checks"].items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Check Yelp NLP corpus completado con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Check Yelp NLP corpus completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())