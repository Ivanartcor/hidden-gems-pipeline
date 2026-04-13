from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from src.config.settings import settings
from src.connectors.overpass import OverpassConnector
from src.normalization.osm_overpass_transformer import OSMOverpassTransformer
from src.normalization.osm_overpass_deduplicator import OSMOverpassDeduplicator
from src.normalization.osm_overpass_importer import OSMOverpassImporter
from src.normalization.place_candidate import NormalizedPlaceCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)

'''
Modo de uso
Para sevilla completa:
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox

Acotando amenities:
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --amenity restaurant `
  --amenity cafe `
  --query-name sevilla_restaurants_cafes_bbox

si queremos incluir también los needs_review en la deduplicación:
python -m scripts.load_overpass_pipeline `
  --south 37.3400 `
  --west -6.0400 `
  --north 37.4300 `
  --east -5.9200 `
  --query-name sevilla_gastronomy_bbox `
  --include-needs-review-in-dedup
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
            "Ejecuta el flujo completo de Overpass de extremo a extremo: "
            "raw ingestion + transformación + deduplicación + importación canónica."
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

    parser.add_argument(
        "--include-needs-review-in-dedup",
        action="store_true",
        help="Incluye también los candidates needs_review en la deduplicación.",
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


def write_json_file(output_path: Path, data: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def serialize_candidate(candidate: NormalizedPlaceCandidate) -> dict[str, Any]:
    return candidate.model_dump(mode="json")


def serialize_candidates(candidates: list[NormalizedPlaceCandidate]) -> list[dict[str, Any]]:
    return [serialize_candidate(candidate) for candidate in candidates]


def serialize_issues(issues: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "issue_code": issue.issue_code,
            "severity": issue.severity,
            "message": issue.message,
            "element_index": getattr(issue, "element_index", None),
            "source_entity_type": getattr(issue, "source_entity_type", None),
            "source_record_id": getattr(issue, "source_record_id", None),
            "field_name": getattr(issue, "field_name", None),
            "received_value": getattr(issue, "received_value", None),
        }
        for issue in issues
    ]


def serialize_pair_evidence(evidence: Any) -> dict[str, Any]:
    return {
        "left_candidate_key": evidence.left_candidate_key,
        "right_candidate_key": evidence.right_candidate_key,
        "score": evidence.score,
        "distance_m": evidence.distance_m,
        "signals": evidence.signals,
        "hard_rule_triggered": evidence.hard_rule_triggered,
    }


def serialize_duplicate_group(group: Any) -> dict[str, Any]:
    return {
        "group_id": group.group_id,
        "representative_key": group.representative_key,
        "representative_candidate": serialize_candidate(group.representative_candidate),
        "member_keys": group.member_keys,
        "member_candidates": [serialize_candidate(candidate) for candidate in group.member_candidates],
        "evidences": [
            serialize_pair_evidence(evidence)
            for evidence in group.evidences
        ],
    }


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

    overpass_query = build_gastronomy_bbox_query(
        south=args.south,
        west=args.west,
        north=args.north,
        east=args.east,
        amenities=amenities,
        element_types=element_types,
        timeout_seconds=args.timeout_seconds,
    )

    # 1. RAW INGESTION
    connector = OverpassConnector()
    connector_result = connector.run(
        overpass_query=overpass_query,
        query_name=args.query_name,
        trigger_type=args.trigger_type,
        run_type=args.run_type,
    )

    run_context = connector_result["run_context"]
    raw_asset = connector_result["raw_asset"]
    payload = connector_result["payload"]

    raw_asset_id = raw_asset["raw_asset_id"]
    staging_dir = settings.data_staging_path / "osm_overpass" / raw_asset_id
    dedup_dir = staging_dir / "deduplication"
    import_dir = dedup_dir / "import"

    # 2. TRANSFORMACIÓN
    transformer = OSMOverpassTransformer()
    transform_result = transformer.transform_payload(
        payload,
        source_run_id=run_context.source_run_id,
        raw_asset_id=raw_asset_id,
    )

    accepted_candidates = [
        candidate
        for candidate in transform_result.candidates
        if candidate.quality.candidate_status == "accepted"
    ]
    needs_review_candidates = [
        candidate
        for candidate in transform_result.candidates
        if candidate.quality.candidate_status == "needs_review"
    ]
    rejected_candidates = [
        candidate
        for candidate in transform_result.candidates
        if candidate.quality.candidate_status == "rejected"
    ]

    resolved_asset_name = raw_asset.get(
        "asset_name",
        f"osm_overpass_{args.query_name.strip().lower().replace(' ', '_')}",
    )

    transform_summary = {
        "file_path": raw_asset["storage_path"],
        "raw_asset_metadata": {
            "raw_asset_id": raw_asset_id,
            "storage_path": raw_asset["storage_path"],
            "asset_name": resolved_asset_name,
            "query_name": args.query_name,
            "source_run_id": run_context.source_run_id,
        },
        "payload_metadata": transform_result.payload_metadata,
        "total_elements": transform_result.total_elements,
        "accepted_count": transform_result.accepted_count,
        "needs_review_count": transform_result.needs_review_count,
        "rejected_count": transform_result.rejected_count,
        "skipped_count": transform_result.skipped_count,
        "issue_count": len(transform_result.issues),
        "output_dir": str(staging_dir),
    }

    write_json_file(staging_dir / "summary.json", transform_summary)
    write_json_file(staging_dir / "accepted_candidates.json", serialize_candidates(accepted_candidates))
    write_json_file(staging_dir / "needs_review_candidates.json", serialize_candidates(needs_review_candidates))
    write_json_file(staging_dir / "rejected_candidates.json", serialize_candidates(rejected_candidates))
    write_json_file(staging_dir / "issues.json", serialize_issues(transform_result.issues))

    # 3. DEDUPLICACIÓN
    dedup_candidates = accepted_candidates
    include_statuses = ["accepted"]

    if args.include_needs_review_in_dedup:
        dedup_candidates = accepted_candidates + needs_review_candidates
        include_statuses.append("needs_review")

    deduplicator = OSMOverpassDeduplicator()
    dedup_result = deduplicator.deduplicate_candidates(
        dedup_candidates,
        include_statuses=tuple(include_statuses),
    )

    dedup_summary = {
        "staging_dir": str(staging_dir),
        "input_summary": transform_summary,
        "include_statuses": include_statuses,
        "input_count": dedup_result.input_count,
        "processed_count": dedup_result.processed_count,
        "grouped_duplicate_count": dedup_result.grouped_duplicate_count,
        "duplicate_group_count": len(dedup_result.duplicate_groups),
        "pair_evidence_count": len(dedup_result.pair_evidences),
        "output_count": dedup_result.output_count,
        "output_dir": str(dedup_dir),
    }

    write_json_file(dedup_dir / "dedup_summary.json", dedup_summary)
    write_json_file(dedup_dir / "unique_candidates.json", serialize_candidates(dedup_result.unique_candidates))
    write_json_file(
        dedup_dir / "duplicate_groups.json",
        [serialize_duplicate_group(group) for group in dedup_result.duplicate_groups],
    )
    write_json_file(
        dedup_dir / "pair_evidences.json",
        [serialize_pair_evidence(evidence) for evidence in dedup_result.pair_evidences],
    )

    # 4. IMPORTACIÓN CANÓNICA
    importer = OSMOverpassImporter()
    import_result = importer.import_candidates(
        candidates=dedup_result.unique_candidates,
        source_run_id=run_context.source_run_id,
        raw_asset_id=raw_asset_id,
    )

    import_summary = {
        "dedup_dir": str(dedup_dir),
        "source_run_id": run_context.source_run_id,
        "raw_asset_id": raw_asset_id,
        "input_candidate_count": len(dedup_result.unique_candidates),
        "import_result": {
            "input_count": import_result.input_count,
            "imported_count": import_result.imported_count,
            "skipped_count": import_result.skipped_count,
            "place_created_count": import_result.place_created_count,
            "place_updated_count": import_result.place_updated_count,
            "place_source_ref_created_count": import_result.place_source_ref_created_count,
            "place_source_ref_updated_count": import_result.place_source_ref_updated_count,
            "place_category_upserted_count": import_result.place_category_upserted_count,
            "place_neighborhood_assignment_upserted_count": import_result.place_neighborhood_assignment_upserted_count,
            "validation_issue_count": import_result.validation_issue_count,
        },
        "output_dir": str(import_dir),
    }

    write_json_file(import_dir / "import_summary.json", import_summary)

    final_output = {
        "source_code": connector_result["source_code"],
        "run_code": run_context.run_code,
        "source_run_id": run_context.source_run_id,
        "raw_asset_id": raw_asset_id,
        "storage_path": raw_asset["storage_path"],
        "bbox": {
            "south": args.south,
            "west": args.west,
            "north": args.north,
            "east": args.east,
        },
        "amenities": amenities,
        "element_types": element_types,
        "raw_summary": connector_result["summary"],
        "transform_summary": {
            "accepted_count": transform_result.accepted_count,
            "needs_review_count": transform_result.needs_review_count,
            "rejected_count": transform_result.rejected_count,
            "skipped_count": transform_result.skipped_count,
            "issue_count": len(transform_result.issues),
        },
        "dedup_summary": {
            "processed_count": dedup_result.processed_count,
            "grouped_duplicate_count": dedup_result.grouped_duplicate_count,
            "duplicate_group_count": len(dedup_result.duplicate_groups),
            "output_count": dedup_result.output_count,
        },
        "import_summary": import_summary["import_result"],
        "staging_dir": str(staging_dir),
        "dedup_dir": str(dedup_dir),
        "import_dir": str(import_dir),
    }

    print(json.dumps(final_output, ensure_ascii=False, indent=2, default=str))
    logger.info("Flujo completo Overpass finalizado correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())