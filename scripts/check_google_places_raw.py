from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Comprueba un raw_asset de Google Places Text Search."
    )

    parser.add_argument(
        "--raw-asset-id",
        type=str,
        required=True,
        help="Identificador del raw_asset generado por Google Places.",
    )

    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Número máximo de tipos a mostrar en rankings.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el resultado del QA en data/artifacts/google_places_raw_qa.",
    )

    return parser


def fetch_raw_asset_metadata(raw_asset_id: str) -> dict[str, Any]:
    sql = text(
        """
        SELECT
            ra.raw_asset_id::text AS raw_asset_id,
            ra.asset_code,
            ra.asset_name,
            ra.asset_type,
            ra.storage_path,
            ra.file_format,
            ra.mime_type,
            ra.file_size_bytes,
            ra.checksum_sha256,
            ra.query_name,
            ra.request_signature_hash,
            ra.created_at,
            ra.source_run_id::text AS source_run_id,
            sr.run_code,
            sr.status AS run_status,
            sr.records_extracted_count,
            sr.records_staged_count,
            sr.records_rejected_count,
            sr.raw_asset_count,
            sr.warning_count,
            sr.error_count,
            ss.source_code,
            ss.source_name
        FROM hidden_gems.raw_asset ra
        JOIN hidden_gems.source_run sr
            ON sr.source_run_id = ra.source_run_id
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = ra.source_system_id
        WHERE ra.raw_asset_id = :raw_asset_id
        """
    )

    with engine.connect() as connection:
        row = connection.execute(
            sql,
            {"raw_asset_id": raw_asset_id},
        ).mappings().one_or_none()

    if row is None:
        raise ValueError(f"No existe raw_asset con id={raw_asset_id}")

    return dict(row)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_place(place: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    if not place.get("id"):
        issues.append("missing_id")

    display_name = place.get("displayName")
    if not isinstance(display_name, dict) or not display_name.get("text"):
        issues.append("missing_display_name")

    if not place.get("formattedAddress"):
        issues.append("missing_formatted_address")

    location = place.get("location")
    if not isinstance(location, dict):
        issues.append("missing_location")
    else:
        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None:
            issues.append("missing_latitude")
        elif not (-90 <= float(latitude) <= 90):
            issues.append("invalid_latitude")

        if longitude is None:
            issues.append("missing_longitude")
        elif not (-180 <= float(longitude) <= 180):
            issues.append("invalid_longitude")

    types = place.get("types")
    if not isinstance(types, list) or not types:
        issues.append("missing_types")

    if not place.get("businessStatus"):
        issues.append("missing_business_status")

    return issues


def profile_google_places_payload(payload: Any, top_n: int) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("El payload no es un objeto JSON válido.")

    places = payload.get("places")

    if places is None:
        places = []

    if not isinstance(places, list):
        raise ValueError("La clave 'places' existe, pero no es una lista.")

    business_status_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    issue_counter: Counter[str] = Counter()

    examples: list[dict[str, Any]] = []

    for place in places:
        if not isinstance(place, dict):
            issue_counter["invalid_place_object"] += 1
            continue

        for issue in validate_place(place):
            issue_counter[issue] += 1

        business_status = place.get("businessStatus")
        if isinstance(business_status, str):
            business_status_counter[business_status] += 1

        types = place.get("types")
        if isinstance(types, list):
            for place_type in types:
                if isinstance(place_type, str):
                    type_counter[place_type] += 1

        if len(examples) < 5:
            location = place.get("location") or {}
            display_name = place.get("displayName") or {}

            examples.append(
                {
                    "id": place.get("id"),
                    "display_name": display_name.get("text"),
                    "formatted_address": place.get("formattedAddress"),
                    "latitude": location.get("latitude"),
                    "longitude": location.get("longitude"),
                    "business_status": place.get("businessStatus"),
                    "types": place.get("types"),
                    "google_maps_uri": place.get("googleMapsUri"),
                }
            )

    return {
        "place_count": len(places),
        "business_status_counts": dict(business_status_counter),
        "top_types": dict(type_counter.most_common(top_n)),
        "issue_counts": dict(issue_counter.most_common()),
        "examples": examples,
    }


def maybe_save_artifact(result: dict[str, Any], raw_asset_id: str) -> Path:
    output_dir = settings.data_artifacts_path / "google_places_raw_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{raw_asset_id}_raw_check.json"
    output_file.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_file


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    metadata = fetch_raw_asset_metadata(args.raw_asset_id)

    if metadata["source_code"] != "google_places":
        raise ValueError(
            f"El raw_asset no pertenece a google_places, sino a {metadata['source_code']}."
        )

    raw_path = settings.data_raw_path / metadata["storage_path"]

    file_exists = raw_path.exists()
    if not file_exists:
        raise FileNotFoundError(f"No existe el fichero raw esperado: {raw_path}")

    file_size_actual = raw_path.stat().st_size
    checksum_actual = compute_sha256(raw_path)

    payload = load_json(raw_path)
    profile = profile_google_places_payload(payload, args.top_n)

    checks = {
        "file_exists": file_exists,
        "file_size_matches": file_size_actual == metadata["file_size_bytes"],
        "checksum_matches": checksum_actual == metadata["checksum_sha256"],
        "run_completed": metadata["run_status"] in {
            "completed",
            "completed_with_warnings",
        },
        "records_extracted_matches": (
            metadata["records_extracted_count"] == profile["place_count"]
        ),
        "json_has_places_list": isinstance(payload, dict)
        and isinstance(payload.get("places", []), list),
        "has_no_place_validation_issues": len(profile["issue_counts"]) == 0,
    }

    result = {
        "raw_asset": {
            "raw_asset_id": metadata["raw_asset_id"],
            "asset_code": metadata["asset_code"],
            "asset_name": metadata["asset_name"],
            "storage_path": metadata["storage_path"],
            "resolved_path": str(raw_path),
            "file_format": metadata["file_format"],
            "mime_type": metadata["mime_type"],
            "query_name": metadata["query_name"],
        },
        "source_run": {
            "source_run_id": metadata["source_run_id"],
            "run_code": metadata["run_code"],
            "run_status": metadata["run_status"],
            "records_extracted_count": metadata["records_extracted_count"],
            "records_staged_count": metadata["records_staged_count"],
            "records_rejected_count": metadata["records_rejected_count"],
            "raw_asset_count": metadata["raw_asset_count"],
            "warning_count": metadata["warning_count"],
            "error_count": metadata["error_count"],
        },
        "integrity": {
            "file_size_expected": metadata["file_size_bytes"],
            "file_size_actual": file_size_actual,
            "checksum_expected": metadata["checksum_sha256"],
            "checksum_actual": checksum_actual,
        },
        "checks": checks,
        "profile": profile,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name for check_name, passed in checks.items()
        if not passed
    ]

    if args.save_artifact:
        artifact_path = maybe_save_artifact(result, args.raw_asset_id)
        logger.info("QA raw Google Places guardado en: %s", artifact_path)

    if failed_checks:
        logger.warning(
            "Comprobación raw Google Places completada con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Comprobación raw Google Places completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())