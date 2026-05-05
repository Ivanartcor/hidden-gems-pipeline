from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.normalization.google_places_reviews_transformer import (
    GooglePlacesReviewsTransformer,
)
from src.normalization.review_candidate import NormalizedReviewCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Transforma un raw de Google Places Place Details en candidatos "
            "normalizados de review."
        )
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        required=True,
        help="raw_asset_id generado por run_google_places_place_details.",
    )

    return parser


def fetch_raw_asset_metadata(raw_asset_id: str) -> dict[str, Any]:
    query = text(
        """
        SELECT
            ra.raw_asset_id::text AS raw_asset_id,
            ra.source_run_id::text AS source_run_id,
            ra.storage_path,
            ra.asset_name,
            ra.query_name,
            sr.request_summary,
            ss.source_code
        FROM hidden_gems.raw_asset ra
        JOIN hidden_gems.source_run sr
            ON sr.source_run_id = ra.source_run_id
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = ra.source_system_id
        WHERE ra.raw_asset_id = :raw_asset_id
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            query,
            {"raw_asset_id": raw_asset_id},
        ).mappings().first()

    if row is None:
        raise ValueError(f"No existe raw_asset_id={raw_asset_id}")

    metadata = dict(row)

    if metadata["source_code"] != "google_places":
        raise ValueError(
            f"El raw_asset no pertenece a google_places: {metadata['source_code']}"
        )

    request_summary = metadata.get("request_summary") or {}

    if not isinstance(request_summary, dict):
        request_summary = {}

    metadata["request_summary"] = request_summary

    return metadata


def load_payload(storage_path: str) -> dict[str, Any]:
    path = settings.data_raw_path / storage_path

    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero raw: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("El payload raw no es un objeto JSON.")

    return payload


def build_output_dir(raw_asset_id: str) -> Path:
    output_dir = settings.data_staging_path / "google_places_reviews" / raw_asset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def serialize_candidate(candidate: NormalizedReviewCandidate) -> dict[str, Any]:
    return candidate.model_dump(mode="json")


def serialize_issue(issue: Any) -> dict[str, Any]:
    return {
        "issue_code": issue.issue_code,
        "severity": issue.severity,
        "message": issue.message,
        "review_index": issue.review_index,
        "source_entity_type": issue.source_entity_type,
        "source_record_id": issue.source_record_id,
        "field_name": issue.field_name,
        "received_value": issue.received_value,
    }


def write_json_file(path: Path, data: Any) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_asset_metadata = fetch_raw_asset_metadata(args.raw_asset_id)
    payload = load_payload(raw_asset_metadata["storage_path"])

    request_summary = raw_asset_metadata["request_summary"]

    place_id = request_summary.get("place_id")
    place_source_ref_id = request_summary.get("place_source_ref_id")

    transformer = GooglePlacesReviewsTransformer()
    result = transformer.transform_payload(
        payload,
        source_run_id=raw_asset_metadata["source_run_id"],
        raw_asset_id=raw_asset_metadata["raw_asset_id"],
        place_id=place_id,
        place_source_ref_id=place_source_ref_id,
    )

    accepted_reviews = [
        candidate
        for candidate in result.candidates
        if candidate.quality.candidate_status == "accepted"
    ]

    rejected_reviews = [
        candidate
        for candidate in result.candidates
        if candidate.quality.candidate_status == "rejected"
    ]

    output_dir = build_output_dir(args.raw_asset_id)

    summary = {
        "raw_asset_metadata": raw_asset_metadata,
        "payload_metadata": result.payload_metadata,
        "total_reviews": result.total_reviews,
        "accepted_count": result.accepted_count,
        "rejected_count": result.rejected_count,
        "skipped_count": result.skipped_count,
        "issue_count": len(result.issues),
        "output_dir": str(output_dir),
    }

    write_json_file(output_dir / "summary.json", summary)
    write_json_file(
        output_dir / "accepted_reviews.json",
        [serialize_candidate(candidate) for candidate in accepted_reviews],
    )
    write_json_file(
        output_dir / "rejected_reviews.json",
        [serialize_candidate(candidate) for candidate in rejected_reviews],
    )
    write_json_file(
        output_dir / "issues.json",
        [serialize_issue(issue) for issue in result.issues],
    )

    console_output = {
        **summary,
        "accepted_examples": [
            {
                "source_review_id": candidate.provenance.source_record_id,
                "rating_value": candidate.rating.rating_value,
                "review_language": candidate.text.review_language,
                "author_name_raw": candidate.author.author_name_raw,
                "review_text_raw": (
                    candidate.text.review_text_raw[:250]
                    if candidate.text.review_text_raw
                    else None
                ),
            }
            for candidate in accepted_reviews[:3]
        ],
    }

    print(json.dumps(console_output, ensure_ascii=False, indent=2, default=str))
    logger.info("Transformación Google Places Reviews completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())