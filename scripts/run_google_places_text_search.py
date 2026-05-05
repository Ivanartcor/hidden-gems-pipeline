from __future__ import annotations

import argparse
import json

from src.connectors.google_places import GooglePlacesConnector
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta una ingesta raw controlada en Google Places Text Search."
        )
    )

    parser.add_argument(
        "--text-query",
        type=str,
        required=True,
        help="Consulta textual para Google Places, por ejemplo: restaurantes en Sevilla, España.",
    )

    parser.add_argument(
        "--query-name",
        type=str,
        default="google_places_text_search",
        help="Nombre lógico de la consulta para trazabilidad.",
    )

    parser.add_argument(
        "--max-result-count",
        type=int,
        default=3,
        help="Número máximo de resultados. Para esta fase inicial se recomienda 3-10.",
    )

    parser.add_argument(
        "--language-code",
        type=str,
        default="es",
        help="Código de idioma de respuesta. Por defecto: es.",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        default="ES",
        help="Código regional. Por defecto: ES.",
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
        default="incremental",
        help="Tipo de run para source_run. Por defecto: incremental.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    connector = GooglePlacesConnector()

    logger.info(
        "Lanzando Google Places Text Search | query_name=%s | text_query=%s | max_result_count=%s",
        args.query_name,
        args.text_query,
        args.max_result_count,
    )

    result = connector.run_text_search(
        text_query=args.text_query,
        query_name=args.query_name,
        max_result_count=args.max_result_count,
        language_code=args.language_code,
        region_code=args.region_code,
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
        "text_query": args.text_query,
        "max_result_count": args.max_result_count,
        "summary": result["summary"],
        "warnings": result["warnings"],
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    logger.info("Ingesta Google Places Text Search completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())