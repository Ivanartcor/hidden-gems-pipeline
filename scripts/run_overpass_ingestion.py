from __future__ import annotations

import argparse
import json
from typing import Iterable

from src.connectors.overpass import OverpassConnector
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


'''
Modo de uso
Para sevilla completa:
python -m scripts.run_overpass_ingestion `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox

Acotando amenities:
python -m scripts.run_overpass_ingestion `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --amenity restaurant `
  --amenity cafe `
  --query-name sevilla_restaurants_cafes_bbox
'''


DEFAULT_GASTRO_AMENITIES = [
    "restaurant",
    "bar",
    "cafe",
    "fast_food",
    "pub",
]

DEFAULT_ELEMENT_TYPES = [
    "node",
    "way",
    "relation",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta una ingesta raw en OSM Overpass para POIs gastronómicos "
            "dentro de un bounding box."
        )
    )

    parser.add_argument("--south", type=float, required=True, help="Límite sur del bbox.")
    parser.add_argument("--west", type=float, required=True, help="Límite oeste del bbox.")
    parser.add_argument("--north", type=float, required=True, help="Límite norte del bbox.")
    parser.add_argument("--east", type=float, required=True, help="Límite este del bbox.")

    parser.add_argument(
        "--amenity",
        action="append",
        default=None,
        help=(
            "Amenity gastronómico a consultar. "
            "Se puede repetir varias veces. "
            "Si no se indica, se usan los valores por defecto."
        ),
    )

    parser.add_argument(
        "--element-type",
        action="append",
        default=None,
        help=(
            "Tipo OSM a consultar: node, way, relation. "
            "Se puede repetir varias veces. "
            "Si no se indica, se usan los tres."
        ),
    )

    parser.add_argument(
        "--query-name",
        type=str,
        default="overpass_gastronomy_bbox",
        help="Nombre lógico de la consulta para trazabilidad.",
    )

    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=90,
        help="Timeout de Overpass para la query. Por defecto: 90.",
    )

    parser.add_argument(
        "--trigger-type",
        type=str,
        default="cli",
        help="Tipo de trigger para source_run. Por defecto: cli.",
    )

    parser.add_argument(
        "--run-type",
        type=str,
        default="full_refresh",
        help="Tipo de run para source_run. Por defecto: full_refresh.",
    )

    return parser


def normalize_list(values: list[str] | None, fallback: list[str]) -> list[str]:
    if not values:
        return fallback.copy()

    normalized = []
    seen = set()

    for value in values:
        clean_value = value.strip().lower()
        if clean_value and clean_value not in seen:
            normalized.append(clean_value)
            seen.add(clean_value)

    return normalized or fallback.copy()


def validate_bbox(*, south: float, west: float, north: float, east: float) -> None:
    if south >= north:
        raise ValueError("El bbox es inválido: south debe ser menor que north.")

    if west >= east:
        raise ValueError("El bbox es inválido: west debe ser menor que east.")

    if not (-90 <= south <= 90 and -90 <= north <= 90):
        raise ValueError("Latitudes fuera de rango válido.")

    if not (-180 <= west <= 180 and -180 <= east <= 180):
        raise ValueError("Longitudes fuera de rango válido.")


def build_gastronomy_bbox_query(
    *,
    south: float,
    west: float,
    north: float,
    east: float,
    amenities: Iterable[str],
    element_types: Iterable[str],
    timeout_seconds: int,
) -> str:
    lines = [f"[out:json][timeout:{timeout_seconds}];", "("]

    for amenity in amenities:
        for element_type in element_types:
            lines.append(
                f'  {element_type}["amenity"="{amenity}"]({south},{west},{north},{east});'
            )

    lines.append(");")
    lines.append("out center tags;")

    return "\n".join(lines)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    validate_bbox(
        south=args.south,
        west=args.west,
        north=args.north,
        east=args.east,
    )

    amenities = normalize_list(args.amenity, DEFAULT_GASTRO_AMENITIES)
    element_types = normalize_list(args.element_type, DEFAULT_ELEMENT_TYPES)

    connector = OverpassConnector()

    overpass_query = build_gastronomy_bbox_query(
        south=args.south,
        west=args.west,
        north=args.north,
        east=args.east,
        amenities=amenities,
        element_types=element_types,
        timeout_seconds=args.timeout_seconds,
    )

    logger.info(
        "Lanzando Overpass | query_name=%s | amenities=%s | element_types=%s",
        args.query_name,
        amenities,
        element_types,
    )

    result = connector.run(
        overpass_query=overpass_query,
        query_name=args.query_name,
        trigger_type=args.trigger_type,
        run_type=args.run_type,
    )

    output = {
        "source_code": result["source_code"],
        "run_code": result["run_context"].run_code,
        "source_run_id": result["run_context"].source_run_id,
        "raw_asset_id": result["raw_asset"]["raw_asset_id"],
        "storage_path": result["raw_asset"]["storage_path"],
        "query_name": args.query_name,
        "bbox": {
            "south": args.south,
            "west": args.west,
            "north": args.north,
            "east": args.east,
        },
        "amenities": amenities,
        "element_types": element_types,
        "element_count": result["summary"]["element_count"],
        "element_type_counts": result["summary"]["element_type_counts"],
        "sample_tag_keys": result["summary"]["sample_tag_keys"],
        "warnings": result["warnings"],
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Ingesta Overpass completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())