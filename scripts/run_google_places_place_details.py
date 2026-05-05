from __future__ import annotations

import argparse
import json
from typing import Any

from sqlalchemy import text

from src.connectors.google_places import GooglePlacesConnector
from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

# -----------------------------------------------------------------------------
# USO DEL BATCH DE GOOGLE PLACES TEXT SEARCH POR BARRIOS
# -----------------------------------------------------------------------------
#
# Este script ejecuta un lote controlado de búsquedas en Google Places usando
# Text Search sobre barrios o distritos oficiales ya cargados en la base de datos.
#
# Su objetivo es descubrir/enriquecer locales gastronómicos y llevarlos por el
# flujo completo del pipeline:
#
#   barrio/distrito oficial
#   → alias/search_name desde google_places_query_plan.yaml
#   → Google Places Text Search
#   → raw_asset
#   → staging candidates
#   → deduplicación
#   → importación en modelo canónico
#   → place / place_source_ref / category / place_neighborhood_assignment
#   → checks internos
#
# El script usa como unidad operativa:
#
#   scripts.load_google_places_pipeline
#
# Por tanto, cada consulta individual genera su propio:
#
#   source_run
#   raw_asset
#   staging
#   deduplication
#   import_summary
#   pipeline_summary
#
# MODO 1: Solo ver el plan, sin llamar a Google
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_alias_dry_run_v1 `
#     --neighborhood "TRIANA CASCO ANTIGUO" `
#     --neighborhood "NERVION" `
#     --queries-per-neighborhood 2 `
#     --dry-run
#
# MODO 2: Ejecutar llamadas a Google, transformar y deduplicar, pero sin importar
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_alias_no_import_v1 `
#     --neighborhood "TRIANA CASCO ANTIGUO" `
#     --neighborhood "NERVION" `
#     --queries-per-neighborhood 2 `
#     --max-result-count 5 `
#     --skip-import `
#     --max-errors 10
#
# MODO 3: Ejecutar batch completo con importación canónica
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_alias_import_v1 `
#     --neighborhood "TRIANA CASCO ANTIGUO" `
#     --neighborhood "NERVION" `
#     --queries-per-neighborhood 2 `
#     --max-result-count 5 `
#     --max-errors 10
#
# MODO 4: Ejecutar un piloto ampliado de 5 barrios
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_pilot_5_barrios_import_v1 `
#     --neighborhood "TRIANA CASCO ANTIGUO" `
#     --neighborhood "NERVION" `
#     --neighborhood "SANTA CRUZ" `
#     --neighborhood "ARENAL" `
#     --neighborhood "LOS REMEDIOS" `
#     --queries-per-neighborhood 2 `
#     --max-result-count 5 `
#     --max-total-queries 10 `
#     --max-errors 10
#
# MODO 5: Ejecutar por distrito completo
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_distrito_triana_import_v1 `
#     --district Triana `
#     --queries-per-neighborhood 2 `
#     --max-result-count 5 `
#     --max-total-queries 10 `
#     --max-errors 10
#
# MODO 6: Usar una plantilla de búsqueda personalizada
#
#   python -m scripts.run_google_places_neighborhood_batch `
#     --batch-name gp_tapas_santa_cruz_v1 `
#     --neighborhood "SANTA CRUZ" `
#     --query-template "bares de tapas en {search_name}, Sevilla" `
#     --queries-per-neighborhood 1 `
#     --max-result-count 5
#
# Opciones importantes:
#
#   --dry-run
#       Solo construye plan.json. No llama a Google Places.
#
#   --skip-import
#       Ejecuta hasta deduplicación/checks, pero no inserta ni actualiza tablas
#       canónicas como place, place_source_ref, category o place_category.
#
#   --neighborhood
#       Selecciona barrios concretos. Se puede repetir.
#       Ejemplo:
#         --neighborhood "SANTA CRUZ" --neighborhood "ARENAL"
#
#   --district
#       Selecciona todos los barrios de un distrito.
#       Ejemplo:
#         --district Triana
#
#   --query-template
#       Permite definir plantillas manuales. Puede contener:
#         {search_name}
#         {neighborhood}
#         {district}
#
#       Ejemplo:
#         "restaurantes en {search_name}, Sevilla"
#
#   --queries-per-neighborhood
#       Número máximo de plantillas ejecutadas por barrio.
#
#   --max-result-count
#       Número máximo de resultados por consulta individual.
#       En desarrollo conviene mantenerlo bajo: 3, 5 o 10.
#
#   --max-total-queries
#       Límite de seguridad para evitar lanzar demasiadas consultas por error.
#
#   --allow-large-batch
#       Permite superar max-total-queries. Usar solo si el flujo ya está validado.
#
#   --allow-large-page-size
#       Permite max-result-count > 10. No recomendado en desarrollo.
#
#   --config-path
#       Permite usar un YAML alternativo de configuración.
#       Por defecto:
#         src/config/google_places_query_plan.yaml
#
#   --ignore-query-plan
#       Ignora el YAML y usa solo defaults internos/argumentos CLI.
#
# Configuración externa:
#
#   El script puede leer:
#
#     src/config/google_places_query_plan.yaml
#
#   Ahí se definen:
#
#     defaults:
#       language_code
#       region_code
#       max_result_count
#       queries_per_neighborhood
#       sleep_seconds
#
#     text_search.query_templates
#       Plantillas de búsqueda.
#
#     neighborhood_aliases
#       Alias para convertir nombres oficiales de barrio en nombres naturales
#       para Google Places.
#
#   Ejemplo:
#
#     neighborhood_name = TRIANA CASCO ANTIGUO
#     search_name = Triana
#     text_query = restaurantes en Triana, Sevilla
#
# Validación posterior:
#
#   Después de ejecutar un batch real, validar con:
#
#   python -m scripts.check_google_places_batch `
#     --batch-name <BATCH_NAME> `
#     --save-artifact
#
# Artefactos generados:
#
#   data/artifacts/google_places_batches/<batch_name>/plan.json
#   data/artifacts/google_places_batches/<batch_name>/results.json
#   data/artifacts/google_places_batches/<batch_name>/batch_summary.json
#
# Si se ejecuta el check:
#
#   data/artifacts/google_places_batches/<batch_name>/batch_check.json
#
# Reglas recomendadas de uso:
#
#   1. Empezar siempre con --dry-run.
#   2. Probar después con --skip-import.
#   3. Importar solo cuando el batch sin importación sea correcto.
#   4. Mantener max-result-count bajo.
#   5. No usar FieldMask amplio ni pedir reviews en esta vertical.
#   6. No lanzar toda Sevilla de golpe.
#   7. Escalar por tandas pequeñas de barrios o distritos.
#   8. Revisar Google Cloud usage tras tandas reales.
#
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta Google Places Place Details para un local ya vinculado "
            "por place_source_ref o para un Google Place ID explícito."
        )
    )

    source_group = parser.add_mutually_exclusive_group(required=False)

    source_group.add_argument(
        "--place-source-ref-id",
        type=str,
        default=None,
        help="ID de hidden_gems.place_source_ref de Google Places.",
    )

    source_group.add_argument(
        "--google-place-id",
        type=str,
        default=None,
        help="Google Place ID explícito.",
    )

    parser.add_argument(
        "--query-name",
        type=str,
        default=None,
        help="Nombre lógico de la consulta. Si no se indica, se genera automáticamente.",
    )

    parser.add_argument(
        "--language-code",
        type=str,
        default="es",
        help="Idioma de respuesta. Por defecto: es.",
    )

    parser.add_argument(
        "--region-code",
        type=str,
        default="ES",
        help="Región de respuesta. Por defecto: ES.",
    )

    parser.add_argument(
        "--limit-first",
        action="store_true",
        help=(
            "Si no se pasa place-source-ref-id ni google-place-id, "
            "selecciona automáticamente el primer place_source_ref actual de Google Places."
        ),
    )

    parser.add_argument(
        "--include-rating-summary",
        action="store_true",
        help=(
            "Incluye rating y userRatingCount en FieldMask. "
            "Úsalo solo en pruebas controladas."
        ),
    )

    return parser


def fetch_place_source_ref(place_source_ref_id: str | None) -> dict[str, Any]:
    extra_filter = ""
    params: dict[str, Any] = {
        "source_code": "google_places",
    }

    if place_source_ref_id:
        extra_filter = "AND psr.place_source_ref_id = :place_source_ref_id"
        params["place_source_ref_id"] = place_source_ref_id

    query = text(
        f"""
        SELECT
            psr.place_source_ref_id::text AS place_source_ref_id,
            psr.place_id::text AS place_id,
            psr.source_record_id AS google_place_id,
            psr.source_name_raw,
            p.display_name AS place_display_name,
            n.official_name AS neighborhood_name,
            d.official_name AS district_name
        FROM hidden_gems.place_source_ref psr
        JOIN hidden_gems.source_system ss
            ON ss.source_system_id = psr.source_system_id
        JOIN hidden_gems.place p
            ON p.place_id = psr.place_id
        LEFT JOIN hidden_gems.place_neighborhood_assignment pna
            ON pna.place_id = p.place_id
           AND pna.is_current = TRUE
        LEFT JOIN hidden_gems.neighborhood n
            ON n.neighborhood_id = pna.neighborhood_id
        LEFT JOIN hidden_gems.district d
            ON d.district_id = pna.district_id
        WHERE ss.source_code = :source_code
          AND psr.is_current = TRUE
          AND psr.is_deleted_in_source = FALSE
          AND psr.source_record_id IS NOT NULL
          {extra_filter}
        ORDER BY psr.updated_at DESC NULLS LAST, psr.created_at DESC
        LIMIT 1
        """
    )

    with engine.connect() as connection:
        row = connection.execute(query, params).mappings().first()

    if row is None:
        if place_source_ref_id:
            raise ValueError(
                f"No se encontró place_source_ref actual de Google Places con id={place_source_ref_id}"
            )
        raise ValueError("No se encontró ningún place_source_ref actual de Google Places.")

    return dict(row)


def build_field_mask(include_rating_summary: bool) -> list[str]:
    fields = [
        "id",
        "displayName",
        "reviews",
    ]

    if include_rating_summary:
        fields.extend(
            [
                "rating",
                "userRatingCount",
            ]
        )

    return fields


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    place_context: dict[str, Any] = {}

    if args.place_source_ref_id:
        place_context = fetch_place_source_ref(args.place_source_ref_id)
        google_place_id = place_context["google_place_id"]

    elif args.google_place_id:
        google_place_id = args.google_place_id.strip()

    elif args.limit_first:
        place_context = fetch_place_source_ref(None)
        google_place_id = place_context["google_place_id"]

    else:
        raise ValueError(
            "Debes indicar --place-source-ref-id, --google-place-id o --limit-first."
        )

    clean_google_place_id = google_place_id.removeprefix("places/").strip()

    query_name = args.query_name
    if not query_name:
        query_name = f"google_places_details_{clean_google_place_id[:24]}"

    connector = GooglePlacesConnector()

    logger.info(
        "Lanzando Google Places Place Details | query_name=%s | google_place_id=%s | place_source_ref_id=%s",
        query_name,
        clean_google_place_id,
        place_context.get("place_source_ref_id"),
    )

    result = connector.run_place_details(
        google_place_id=clean_google_place_id,
        query_name=query_name,
        language_code=args.language_code,
        region_code=args.region_code,
        field_mask=build_field_mask(args.include_rating_summary),
        place_id=place_context.get("place_id"),
        place_source_ref_id=place_context.get("place_source_ref_id"),
    )

    output = {
        "source_code": result["source_code"],
        "run_code": result["run_context"].run_code,
        "source_run_id": result["run_context"].source_run_id,
        "raw_asset_id": result["raw_asset"]["raw_asset_id"],
        "storage_path": result["raw_asset"]["storage_path"],
        "google_place_id": result["google_place_id"],
        "place_context": place_context or None,
        "summary": result["summary"],
        "warnings": result["warnings"],
    }

    print(json.dumps(output, ensure_ascii=False, indent=2, default=str))

    logger.info("Google Places Place Details completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())