from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

# script para obtener infromación sobre estructuras de datos obtenidos en api osm_overpass 

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Perfila un raw JSON de Overpass para analizar fields y tags antes de normalizar."
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
        "--top-n",
        type=int,
        default=50,
        help="Número máximo de valores frecuentes a mostrar por sección.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el perfilado como JSON en data/artifacts/overpass_profiles.",
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

    return full_path, dict(row)


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


def split_multi_value_tag(value: str) -> list[str]:
    parts = [part.strip() for part in value.split(";")]
    return [part for part in parts if part]


def profile_overpass_payload(payload: dict[str, Any], top_n: int) -> dict[str, Any]:
    elements = payload.get("elements")
    if not isinstance(elements, list):
        raise ValueError("El payload no contiene una lista válida en 'elements'.")

    element_type_counter: Counter[str] = Counter()
    top_level_key_counter: Counter[str] = Counter()
    tag_key_counter: Counter[str] = Counter()

    amenity_counter: Counter[str] = Counter()
    cuisine_counter: Counter[str] = Counter()
    brand_counter: Counter[str] = Counter()

    has_name_count = 0
    missing_name_count = 0
    has_address_count = 0
    has_phone_count = 0
    has_website_count = 0
    has_opening_hours_count = 0
    has_cuisine_count = 0
    has_brand_count = 0

    for element in elements:
        if not isinstance(element, dict):
            continue

        for key in element.keys():
            top_level_key_counter[key] += 1

        element_type = element.get("type")
        if isinstance(element_type, str):
            element_type_counter[element_type] += 1

        tags = element.get("tags", {})
        if not isinstance(tags, dict):
            tags = {}

        for tag_key in tags.keys():
            tag_key_counter[tag_key] += 1

        name = tags.get("name")
        official_name = tags.get("official_name")
        brand = tags.get("brand")

        if any(isinstance(value, str) and value.strip() for value in (name, official_name, brand)):
            has_name_count += 1
        else:
            missing_name_count += 1

        if any(key.startswith("addr:") for key in tags.keys()):
            has_address_count += 1

        if isinstance(tags.get("phone"), str) and tags.get("phone").strip():
            has_phone_count += 1

        if isinstance(tags.get("website"), str) and tags.get("website").strip():
            has_website_count += 1

        if isinstance(tags.get("opening_hours"), str) and tags.get("opening_hours").strip():
            has_opening_hours_count += 1

        amenity = tags.get("amenity")
        if isinstance(amenity, str) and amenity.strip():
            amenity_counter[amenity.strip()] += 1

        cuisine = tags.get("cuisine")
        if isinstance(cuisine, str) and cuisine.strip():
            has_cuisine_count += 1
            for cuisine_value in split_multi_value_tag(cuisine):
                cuisine_counter[cuisine_value] += 1

        if isinstance(brand, str) and brand.strip():
            has_brand_count += 1
            brand_counter[brand.strip()] += 1

    return {
        "total_elements": len(elements),
        "element_type_counts": dict(element_type_counter),
        "top_level_keys": sorted(top_level_key_counter.keys()),
        "top_level_key_frequency": dict(top_level_key_counter.most_common(top_n)),
        "tag_keys": sorted(tag_key_counter.keys()),
        "tag_key_frequency": dict(tag_key_counter.most_common(top_n)),
        "amenity_frequency": dict(amenity_counter.most_common(top_n)),
        "cuisine_frequency": dict(cuisine_counter.most_common(top_n)),
        "brand_frequency": dict(brand_counter.most_common(top_n)),
        "quality_signals": {
            "has_name_count": has_name_count,
            "missing_name_count": missing_name_count,
            "has_address_count": has_address_count,
            "has_phone_count": has_phone_count,
            "has_website_count": has_website_count,
            "has_opening_hours_count": has_opening_hours_count,
            "has_cuisine_count": has_cuisine_count,
            "has_brand_count": has_brand_count,
        },
    }


def maybe_save_artifact(profile: dict[str, Any], file_path: Path) -> Path:
    output_dir = settings.data_artifacts_path / "overpass_profiles"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{file_path.stem}_profile.json"
    output_file.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return output_file


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    metadata: dict[str, Any] = {}

    if args.raw_asset_id:
        file_path, metadata = resolve_raw_path_from_asset_id(args.raw_asset_id)
        logger.info("Raw resuelto desde raw_asset_id=%s -> %s", args.raw_asset_id, file_path)
    else:
        file_path = Path(args.file_path)

    payload = load_json_payload(file_path)
    profile = profile_overpass_payload(payload, top_n=args.top_n)

    output = {
        "file_path": str(file_path),
        "raw_asset_metadata": metadata or None,
        "profile": profile,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    if args.save_artifact:
        artifact_path = maybe_save_artifact(output, file_path)
        logger.info("Perfil guardado en: %s", artifact_path)

    logger.info("Perfilado de Overpass completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())