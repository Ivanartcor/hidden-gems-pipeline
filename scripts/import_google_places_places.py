from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.normalization.google_places_importer import GooglePlacesImporter
from src.normalization.place_candidate import NormalizedPlaceCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta la importación canónica de candidatos deduplicados de "
            "Google Places hacia place, place_source_ref, place_category y "
            "place_neighborhood_assignment."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--dedup-dir",
        type=str,
        help="Ruta directa al directorio de deduplicación.",
    )
    source_group.add_argument(
        "--raw-asset-id",
        type=str,
        help=(
            "raw_asset_id usado para resolver automáticamente "
            "data/staging/google_places/<raw_asset_id>/deduplication."
        ),
    )

    return parser


def resolve_dedup_dir(args: argparse.Namespace) -> Path:
    if args.dedup_dir:
        dedup_dir = Path(args.dedup_dir)
    else:
        dedup_dir = (
            settings.data_staging_path
            / "google_places"
            / args.raw_asset_id
            / "deduplication"
        )

    if not dedup_dir.exists():
        raise FileNotFoundError(f"No existe el directorio de deduplicación: {dedup_dir}")

    if not dedup_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {dedup_dir}")

    return dedup_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def deserialize_candidates(rows: list[dict[str, Any]]) -> list[NormalizedPlaceCandidate]:
    return [NormalizedPlaceCandidate.model_validate(row) for row in rows]


def build_output_dir(dedup_dir: Path) -> Path:
    output_dir = dedup_dir / "import"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json_file(output_path: Path, data: Any) -> None:
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    dedup_dir = resolve_dedup_dir(args)
    output_dir = build_output_dir(dedup_dir)

    dedup_summary = load_json_file(dedup_dir / "dedup_summary.json")
    unique_candidates_rows = load_json_file(dedup_dir / "unique_candidates.json")

    candidates = deserialize_candidates(unique_candidates_rows)

    input_summary = dedup_summary.get("input_summary", {})
    raw_asset_metadata = input_summary.get("raw_asset_metadata", {}) or {}

    source_run_id = raw_asset_metadata.get("source_run_id")
    raw_asset_id = raw_asset_metadata.get("raw_asset_id")

    if not source_run_id:
        raise ValueError(
            "No se pudo resolver source_run_id desde dedup_summary.json."
        )

    importer = GooglePlacesImporter()

    logger.info(
        "Lanzando importador canónico Google Places | source_run_id=%s | raw_asset_id=%s | candidates=%s",
        source_run_id,
        raw_asset_id,
        len(candidates),
    )

    result = importer.import_candidates(
        candidates=candidates,
        source_run_id=source_run_id,
        raw_asset_id=raw_asset_id,
    )

    output = {
        "dedup_dir": str(dedup_dir),
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
        "input_candidate_count": len(candidates),
        "import_result": {
            "input_count": result.input_count,
            "imported_count": result.imported_count,
            "skipped_count": result.skipped_count,
            "place_created_count": result.place_created_count,
            "place_updated_count": result.place_updated_count,
            "place_source_ref_created_count": result.place_source_ref_created_count,
            "place_source_ref_updated_count": result.place_source_ref_updated_count,
            "place_category_upserted_count": result.place_category_upserted_count,
            "place_neighborhood_assignment_upserted_count": result.place_neighborhood_assignment_upserted_count,
            "validation_issue_count": result.validation_issue_count,
        },
        "output_dir": str(output_dir),
    }

    write_json_file(output_dir / "import_summary.json", output)

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Importación canónica Google Places completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())