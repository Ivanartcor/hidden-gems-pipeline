from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.normalization.osm_overpass_transformer import OSMOverpassTransformer
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

'''
Cómo ejecutarlo

segun id:
python -m scripts.transform_overpass_candidates --raw-asset-id b805fd54-df1e-4326-b674-90ea4147ce2b

O usando el fichero raw:
python -m scripts.transform_overpass_candidates --file-path "data/raw/osm_overpass/2026/04/09/osm_overpass_20260409T183029Z_301e8bbd/20260409T183031Z_osm_overpass_sevilla_gastronomy_bbox_1ae148a3.json"
'''

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta la transformación de raw Overpass a NormalizedPlaceCandidate "
            "y guarda la salida en data/staging."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--file-path",
        type=str,
        help="Ruta directa al raw JSON de Overpass.",
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
        SELECT raw_asset_id, storage_path, asset_name, query_name, source_run_id
        FROM hidden_gems.raw_asset
        WHERE raw_asset_id = :raw_asset_id
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, {"raw_asset_id": raw_asset_id}).mappings().first()

    if row is None:
        raise ValueError(f"No existe raw_asset con id={raw_asset_id}")

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

    with file_path.open("r", encoding="utf-8-sig") as f:
        payload = json.load(f)

    if not isinstance(payload, dict):
        raise ValueError("El raw de Overpass no contiene un objeto JSON válido.")

    return payload


def build_output_dir(file_path: Path, metadata: dict[str, Any]) -> Path:
    folder_name = metadata.get("raw_asset_id") or file_path.stem
    output_dir = settings.data_staging_path / "osm_overpass" / folder_name
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
            "element_index": issue.element_index,
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
                "primary_category": candidate.classification.source_primary_category_raw,
                "cuisine_raw": candidate.classification.cuisine_raw,
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
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
            "Raw resuelto desde raw_asset_id=%s -> %s",
            args.raw_asset_id,
            file_path,
        )
    else:
        file_path = Path(args.file_path)

    payload = load_json_payload(file_path)

    transformer = OSMOverpassTransformer()
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
        "total_elements": result.total_elements,
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
    logger.info("Transformación Overpass completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())