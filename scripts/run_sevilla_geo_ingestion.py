from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.connectors.sevilla_geo import SevillaGeoConnector
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


# Ejemplos de uso
#
# Para barrios usando directamente la URL por defecto:
# python -m scripts.run_sevilla_geo_ingestion --layer-name neighborhood --source-version 2024_06
#
# Para distritos indicando la URL explícitamente:
# python -m scripts.run_sevilla_geo_ingestion --layer-name district --download-url "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson" --source-version 2026_04
#
# Para barrios desde archivo local:
# python -m scripts.run_sevilla_geo_ingestion --layer-name neighborhood --local-file-path "data/reference/Barrios.geojson" --source-version 2024_06



DEFAULT_NEIGHBORHOODS_URL = (
    "https://services1.arcgis.com/hcmP7kr0Cx3AcTJk/arcgis/rest/services/"
    "Barrios_de_Sevilla/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ejecuta la ingesta raw del dataset geográfico de Sevilla."
    )

    parser.add_argument(
        "--layer-name",
        required=True,
        choices=("district", "neighborhood"),
        help="Capa geográfica que se quiere ingerir.",
    )

    parser.add_argument(
        "--local-file-path",
        type=str,
        default=None,
        help="Ruta local al fichero GeoJSON/JSON.",
    )

    parser.add_argument(
        "--download-url",
        type=str,
        default=None,
        help="URL pública desde la que descargar el GeoJSON/JSON.",
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

    if args.layer_name == "neighborhood":
        logger.info(
            "No se indicó fuente explícita para neighborhood; "
            "se usará el endpoint público por defecto de barrios."
        )
        return {"download_url": DEFAULT_NEIGHBORHOODS_URL}

    raise ValueError(
        "Para layer_name='district' debes indicar --local-file-path o --download-url."
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    connector = SevillaGeoConnector()
    source_kwargs = resolve_source_args(args)

    logger.info(
        "Lanzando ingesta Sevilla Geo | layer=%s | source_version=%s",
        args.layer_name,
        args.source_version,
    )

    result = connector.run(
        layer_name=args.layer_name,
        source_version=args.source_version,
        trigger_type=args.trigger_type,
        **source_kwargs,
    )

    output = {
        "source_code": result["source_code"],
        "run_code": result["run_context"].run_code,
        "source_run_id": result["run_context"].source_run_id,
        "raw_asset_id": result["raw_asset"]["raw_asset_id"],
        "storage_path": result["raw_asset"]["storage_path"],
        "feature_count": result["summary"]["feature_count"],
        "geometry_types": result["summary"]["geometry_types"],
        "property_keys_sample": result["summary"]["property_keys_sample"],
        "warnings": result["warnings"],
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Ingesta Sevilla Geo completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())