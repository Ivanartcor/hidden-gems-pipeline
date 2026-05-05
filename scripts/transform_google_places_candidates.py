from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.normalization.google_places_transformer import GooglePlacesTransformer
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta la transformación de raw Google Places a "
            "NormalizedPlaceCandidate y guarda la salida en data/staging."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--file-path",
        type=str,
        help="Ruta directa al raw JSON de Google Places.",
    )
    source_group.add_argument(
        "--raw-asset-id",
        type=str,
        help="raw_asset_id registrado en hidden_gems.raw_asset.",
    )

    parser.add_argument(
        "--preview-count",
        type=int,
        default=5,
        help="Número de ejemplos a mostrar por consola.",
    )

    return parser


def resolve_raw_path_from_asset_id(raw_asset_id: str) -> tuple[Path, dict[str, Any]]:
    query = text(
        """
        SELECT
            ra.raw_asset_id,
            ra.storage_path,
            ra.asset_name,
            ra.query_name,
            ra.source_run_id,
            ss.source_code
        FROM hidden_gems.raw_asset ra
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
        raise ValueError(f"No existe raw_asset con id={raw_asset_id}")

    if row["source_code"] != "google_places":
        raise ValueError(
            f"El raw_asset no pertenece a google_places, sino a {row['source_code']}."
        )

    relative_path = Path(row["storage_path"])
    full_path = settings.data_raw_path / relative_path

    metadata = dict(row)
    metadata["raw_asset_id"] = str(metadata["raw_asset_id"])
    metadata["source_run_id"] = str(metadata["source_run_id"])

    return full_path, metadata


def load_json_payload(file_path: Path) -> dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"No existe el fichero: {file_path}")

    if not file_path.is_file():
        raise ValueError(f"La ruta no es un fichero válido: {file_path}")

    with file_path.open("r", encoding="utf-8-sig") as file:
        payload = json.load(file)

    if not isinstance(payload, dict):
        raise ValueError("El raw de Google Places no contiene un objeto JSON válido.")

    return payload


def build_output_dir(file_path: Path, metadata: dict[str, Any]) -> Path:
    folder_name = metadata.get("raw_asset_id") or file_path.stem
    output_dir = settings.data_staging_path / "google_places" / folder_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json_file(output_path: Path, data: Any) -> None:
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def serialize_candidates(candidates: list[Any]) -> list[dict[str, Any]]:
    return [candidate.model_dump(mode="json") for candidate in candidates]


def serialize_issues(issues: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "issue_code": issue.issue_code,
            "severity": issue.severity,
            "message": issue.message,
            "place_index": issue.place_index,
            "source_entity_type": issue.source_entity_type,
            "source_record_id": issue.source_record_id,
            "field_name": issue.field_name,
            "received_value": issue.received_value,
        }
        for issue in issues
    ]


def build_preview(candidates: list[Any], preview_count: int) -> list[dict[str, Any]]:
    preview_rows: list[dict[str, Any]] = []

    for candidate in candidates[:preview_count]:
        preview_rows.append(
            {
                "source_entity_type": candidate.provenance.source_entity_type,
                "source_record_id": candidate.provenance.source_record_id,
                "display_name": candidate.names.display_name,
                "normalized_name": candidate.names.normalized_name,
                "source_address_raw": candidate.address.source_address_raw,
                "primary_category": candidate.classification.source_primary_category_raw,
                "source_categories_raw": candidate.classification.source_categories_raw,
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
                "source_status_raw": candidate.provenance.source_status_raw,
                "source_url": candidate.provenance.source_url,
                "candidate_status": candidate.quality.candidate_status,
                "completeness_score": candidate.quality.completeness_score,
                "rejection_reasons": candidate.quality.rejection_reasons,
                "warning_messages": candidate.quality.warning_messages,
            }
        )

    return preview_rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    metadata: dict[str, Any] = {}

    if args.raw_asset_id:
        file_path, metadata = resolve_raw_path_from_asset_id(args.raw_asset_id)
        logger.info(
            "Raw Google Places resuelto desde raw_asset_id=%s -> %s",
            args.raw_asset_id,
            file_path,
        )
    else:
        file_path = Path(args.file_path)

    payload = load_json_payload(file_path)

    transformer = GooglePlacesTransformer()
    result = transformer.transform_payload(
        payload,
        source_run_id=metadata.get("source_run_id"),
        raw_asset_id=metadata.get("raw_asset_id"),
    )

    accepted_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.quality.candidate_status == "accepted"
    ]
    needs_review_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.quality.candidate_status == "needs_review"
    ]
    rejected_candidates = [
        candidate
        for candidate in result.candidates
        if candidate.quality.candidate_status == "rejected"
    ]

    output_dir = build_output_dir(file_path, metadata)

    summary = {
        "file_path": str(file_path),
        "raw_asset_metadata": metadata or None,
        "payload_metadata": result.payload_metadata,
        "total_places": result.total_places,
        "accepted_count": result.accepted_count,
        "needs_review_count": result.needs_review_count,
        "rejected_count": result.rejected_count,
        "skipped_count": result.skipped_count,
        "issue_count": len(result.issues),
        "output_dir": str(output_dir),
    }

    write_json_file(output_dir / "summary.json", summary)
    write_json_file(
        output_dir / "accepted_candidates.json",
        serialize_candidates(accepted_candidates),
    )
    write_json_file(
        output_dir / "needs_review_candidates.json",
        serialize_candidates(needs_review_candidates),
    )
    write_json_file(
        output_dir / "rejected_candidates.json",
        serialize_candidates(rejected_candidates),
    )
    write_json_file(
        output_dir / "issues.json",
        serialize_issues(result.issues),
    )

    console_output = {
        **summary,
        "accepted_preview": build_preview(accepted_candidates, args.preview_count),
        "needs_review_preview": build_preview(needs_review_candidates, args.preview_count),
        "rejected_preview": build_preview(rejected_candidates, args.preview_count),
    }

    print(json.dumps(console_output, ensure_ascii=False, indent=2, default=str))
    logger.info("Transformación Google Places completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())