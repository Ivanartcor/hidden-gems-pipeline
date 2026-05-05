from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.normalization.google_places_reviews_importer import (
    GooglePlacesReviewsImporter,
)
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa reviews normalizadas de Google Places hacia hidden_gems.review."
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        required=True,
        help="raw_asset_id transformado previamente a staging de reviews.",
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


def load_json(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def get_staging_dir(raw_asset_id: str) -> Path:
    return settings.data_staging_path / "google_places_reviews" / raw_asset_id


def write_json_file(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    raw_asset_metadata = fetch_raw_asset_metadata(args.raw_asset_id)
    staging_dir = get_staging_dir(args.raw_asset_id)

    summary = load_json(staging_dir / "summary.json")
    accepted_reviews = load_json(staging_dir / "accepted_reviews.json")

    if not isinstance(summary, dict):
        raise ValueError("summary.json no contiene un objeto válido.")

    if not isinstance(accepted_reviews, list):
        raise ValueError("accepted_reviews.json no contiene una lista válida.")

    source_run_id = raw_asset_metadata["source_run_id"]
    raw_asset_id = raw_asset_metadata["raw_asset_id"]

    logger.info(
        "Lanzando importación Google Places Reviews | source_run_id=%s | raw_asset_id=%s | accepted_reviews=%s",
        source_run_id,
        raw_asset_id,
        len(accepted_reviews),
    )

    importer = GooglePlacesReviewsImporter()
    import_result = importer.import_reviews(
        reviews=accepted_reviews,
        source_run_id=source_run_id,
        raw_asset_id=raw_asset_id,
    )

    output_dir = staging_dir / "import"

    output = {
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
        "staging_dir": str(staging_dir),
        "input_summary": {
            "total_reviews": summary.get("total_reviews"),
            "accepted_count": summary.get("accepted_count"),
            "rejected_count": summary.get("rejected_count"),
            "skipped_count": summary.get("skipped_count"),
            "issue_count": summary.get("issue_count"),
        },
        "import_result": {
            "input_count": import_result.input_count,
            "imported_count": import_result.imported_count,
            "inserted_count": import_result.inserted_count,
            "updated_count": import_result.updated_count,
            "skipped_count": import_result.skipped_count,
            "validation_issue_count": import_result.validation_issue_count,
        },
        "output_dir": str(output_dir),
    }

    write_json_file(output_dir / "import_summary.json", output)

    artifact_path = (
        settings.data_artifacts_path
        / "google_places_reviews_import"
        / f"{raw_asset_id}_reviews_import_summary.json"
    )
    write_json_file(artifact_path, output)

    console_output = {
        **output,
        "artifact_path": str(artifact_path),
    }

    print(json.dumps(console_output, ensure_ascii=False, indent=2, default=str))

    logger.info("Importación Google Places Reviews completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())