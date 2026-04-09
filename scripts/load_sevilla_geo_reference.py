from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.connectors.sevilla_geo import SevillaGeoConnector
from src.geo.sevilla_geo_importer import SevillaGeoImporter
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

# Ejemplos de uso
#
# Usando directamente la URL por defecto:
# python -m scripts.load_sevilla_geo_reference --source-version 2024_06
#
# Indicando la URL explícitamente:
# python -m scripts.load_sevilla_geo_reference --download-url "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson" --source-version 2026_04
#
# Desde archivo local:
# python -m scripts.load_sevilla_geo_reference --local-file-path "data/reference/Barrios.geojson" --source-version 2024_06



DEFAULT_NEIGHBORHOODS_URL = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/"
    "Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta el flujo completo de Sevilla Geo: "
            "ingesta raw + transformación + carga a district y neighborhood."
        )
    )

    parser.add_argument(
        "--local-file-path",
        type=str,
        default=None,
        help="Ruta local al GeoJSON/JSON de barrios.",
    )

    parser.add_argument(
        "--download-url",
        type=str,
        default=None,
        help="URL pública desde la que descargar el GeoJSON de barrios.",
    )

    parser.add_argument(
        "--source-version",
        type=str,
        default=None,
        help="Versión lógica del dataset, por ejemplo 2026_04.",
    )

    parser.add_argument(
        "--trigger-type",
        type=str,
        default="cli",
        help="Tipo de trigger para source_run. Por defecto: cli.",
    )

    return parser


def resolve_source_args(args: argparse.Namespace) -> dict[str, str | Path]:
    if args.local_file_path and args.download_url:
        raise ValueError(
            "No puedes usar a la vez --local-file-path y --download-url."
        )

    if args.local_file_path:
        return {"local_file_path": Path(args.local_file_path)}

    if args.download_url:
        return {"download_url": args.download_url}

    logger.info(
        "No se indicó fuente explícita; se usará el endpoint público por defecto de barrios."
    )
    return {"download_url": DEFAULT_NEIGHBORHOODS_URL}


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    connector = SevillaGeoConnector()
    importer = SevillaGeoImporter()

    source_kwargs = resolve_source_args(args)

    logger.info(
        "Iniciando flujo completo Sevilla Geo | source_version=%s",
        args.source_version,
    )

    connector_result = connector.run(
        layer_name="neighborhood",
        source_version=args.source_version,
        trigger_type=args.trigger_type,
        **source_kwargs,
    )

    run_context = connector_result["run_context"]
    raw_asset = connector_result["raw_asset"]
    payload = connector_result["payload"]

    import_result = importer.import_payload(
        payload=payload,
        source_run_id=run_context.source_run_id,
        raw_asset_id=raw_asset["raw_asset_id"],
        source_version=args.source_version,
    )

    output = {
        "source_code": connector_result["source_code"],
        "run_code": run_context.run_code,
        "source_run_id": run_context.source_run_id,
        "raw_asset_id": raw_asset["raw_asset_id"],
        "storage_path": raw_asset["storage_path"],
        "feature_count": connector_result["summary"]["feature_count"],
        "geometry_types": connector_result["summary"]["geometry_types"],
        "raw_warnings": connector_result["warnings"],
        "district_inserted_count": import_result.district_inserted_count,
        "district_updated_count": import_result.district_updated_count,
        "neighborhood_inserted_count": import_result.neighborhood_inserted_count,
        "neighborhood_updated_count": import_result.neighborhood_updated_count,
        "validation_issue_count": import_result.validation_issue_count,
        "staged_count": import_result.staged_count,
        "rejected_count": import_result.rejected_count,
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Flujo completo Sevilla Geo finalizado correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())