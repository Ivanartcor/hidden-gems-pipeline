from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.connectors.google_places import GooglePlacesConnector
from src.db.database import engine
from src.normalization.google_places_deduplicator import GooglePlacesDeduplicator
from src.normalization.google_places_importer import GooglePlacesImporter
from src.normalization.google_places_transformer import GooglePlacesTransformer
from src.normalization.place_candidate import NormalizedPlaceCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


'''
Modo de uso
python -m scripts.load_google_places_pipeline `
  --text-query "consulta" `
  --query-name "nombre de la ejecución" `
  --max-result-count "numero de resultados" `
  --skip-import (opcional si no se quiere escribir en place)

ejemplo:
python -m scripts.load_google_places_pipeline `
  --text-query "restaurantes en Sevilla, España" `
  --query-name sevilla_restaurantes_pipeline_test `
  --max-result-count 3  
'''



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta el flujo completo de Google Places de extremo a extremo: "
            "raw ingestion + check raw + transformación + check staging + "
            "deduplicación + check dedup + importación canónica + check import."
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
        help="Número máximo de resultados. Para esta fase se recomienda 3-10.",
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

    parser.add_argument(
        "--include-needs-review-in-dedup",
        action="store_true",
        help="Incluye también candidates needs_review en la deduplicación.",
    )

    parser.add_argument(
        "--skip-import",
        action="store_true",
        help="Ejecuta hasta deduplicación, pero no importa a tablas canónicas.",
    )

    return parser


def write_json_file(output_path: Path, data: Any) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


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
            "place_index": getattr(issue, "place_index", None),
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
        "member_candidates": [
            serialize_candidate(candidate)
            for candidate in group.member_candidates
        ],
        "evidences": [
            serialize_pair_evidence(evidence)
            for evidence in group.evidences
        ],
    }


def validate_raw_asset(
    *,
    raw_asset: dict[str, Any],
    payload: dict[str, Any],
    run_context: Any,
) -> dict[str, bool]:
    raw_path = settings.data_raw_path / raw_asset["storage_path"]

    if not raw_path.exists():
        raise FileNotFoundError(f"No existe el raw generado: {raw_path}")

    file_size_actual = raw_path.stat().st_size
    checksum_actual = compute_sha256(raw_path)

    places = payload.get("places", [])
    if places is None:
        places = []

    checks = {
        "file_exists": raw_path.exists(),
        "file_size_matches": file_size_actual == raw_asset["file_size_bytes"],
        "checksum_matches": checksum_actual == raw_asset["checksum_sha256"],
        "payload_is_dict": isinstance(payload, dict),
        "payload_has_places_list": isinstance(places, list),
        "run_context_has_source_run_id": bool(run_context.source_run_id),
        "run_context_has_run_code": bool(run_context.run_code),
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check raw Google Places fallido: {failed_checks}")

    return checks


def validate_staging_outputs(
    *,
    transform_summary: dict[str, Any],
    accepted_candidates: list[NormalizedPlaceCandidate],
    needs_review_candidates: list[NormalizedPlaceCandidate],
    rejected_candidates: list[NormalizedPlaceCandidate],
    issues: list[Any],
) -> dict[str, bool]:
    accepted_count = len(accepted_candidates)
    needs_review_count = len(needs_review_candidates)
    rejected_count = len(rejected_candidates)
    skipped_count = int(transform_summary.get("skipped_count") or 0)
    total_places = int(transform_summary.get("total_places") or 0)

    accepted_missing_coordinates = sum(
        1 for candidate in accepted_candidates
        if not candidate.quality.has_coordinates
    )
    accepted_missing_category = sum(
        1 for candidate in accepted_candidates
        if not candidate.quality.has_category
    )
    accepted_wrong_source = sum(
        1 for candidate in accepted_candidates
        if candidate.provenance.source_system_code != "google_places"
    )

    checks = {
        "accepted_count_matches": (
            int(transform_summary.get("accepted_count") or 0) == accepted_count
        ),
        "needs_review_count_matches": (
            int(transform_summary.get("needs_review_count") or 0) == needs_review_count
        ),
        "rejected_count_matches": (
            int(transform_summary.get("rejected_count") or 0) == rejected_count
        ),
        "total_places_matches_candidates_plus_skipped": (
            total_places == accepted_count + needs_review_count + rejected_count + skipped_count
        ),
        "issue_count_matches": (
            int(transform_summary.get("issue_count") or 0) == len(issues)
        ),
        "accepted_candidates_are_google_places": accepted_wrong_source == 0,
        "accepted_candidates_have_coordinates": accepted_missing_coordinates == 0,
        "accepted_candidates_have_category": accepted_missing_category == 0,
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check staging Google Places fallido: {failed_checks}")

    return checks


def validate_dedup_outputs(
    *,
    dedup_summary: dict[str, Any],
    unique_candidates: list[NormalizedPlaceCandidate],
    duplicate_groups: list[Any],
    pair_evidences: list[Any],
) -> dict[str, bool]:
    duplicate_group_member_extra_count = 0

    for group in duplicate_groups:
        if len(group.member_keys) > 1:
            duplicate_group_member_extra_count += len(group.member_keys) - 1

    source_record_id_counter: Counter[str] = Counter(
        candidate.provenance.source_record_id
        for candidate in unique_candidates
        if candidate.provenance.source_record_id
    )

    duplicate_source_record_ids = [
        source_record_id
        for source_record_id, total in source_record_id_counter.items()
        if total > 1
    ]

    missing_coordinates = sum(
        1 for candidate in unique_candidates
        if not candidate.quality.has_coordinates
    )
    missing_category = sum(
        1 for candidate in unique_candidates
        if not candidate.quality.has_category
    )
    wrong_source = sum(
        1 for candidate in unique_candidates
        if candidate.provenance.source_system_code != "google_places"
    )

    checks = {
        "dedup_output_count_matches_unique_candidates": (
            int(dedup_summary.get("output_count") or 0) == len(unique_candidates)
        ),
        "dedup_duplicate_group_count_matches": (
            int(dedup_summary.get("duplicate_group_count") or 0) == len(duplicate_groups)
        ),
        "dedup_pair_evidence_count_matches": (
            int(dedup_summary.get("pair_evidence_count") or 0) == len(pair_evidences)
        ),
        "dedup_grouped_duplicate_count_matches_groups": (
            int(dedup_summary.get("grouped_duplicate_count") or 0)
            == duplicate_group_member_extra_count
        ),
        "unique_candidates_are_google_places": wrong_source == 0,
        "unique_candidates_have_no_duplicate_source_record_id": (
            len(duplicate_source_record_ids) == 0
        ),
        "unique_candidates_have_coordinates": missing_coordinates == 0,
        "unique_candidates_have_category": missing_category == 0,
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check dedup Google Places fallido: {failed_checks}")

    return checks


def fetch_scalar(connection, query: str, params: dict[str, Any] | None = None) -> int:
    result = connection.execute(text(query), params or {}).scalar_one()
    return int(result)


def fetch_rows(connection, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    result = connection.execute(text(query), params or {})
    return [dict(row._mapping) for row in result]


def build_import_check(
    *,
    source_run_id: str,
    raw_asset_id: str,
) -> dict[str, Any]:
    params = {
        "source_code": "google_places",
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
    }

    source_ref_extra_filter = """
        AND psr.source_run_id = :source_run_id
        AND psr.raw_asset_id = :raw_asset_id
    """
    validation_extra_filter = """
        AND vi.source_run_id = :source_run_id
        AND vi.raw_asset_id = :raw_asset_id
    """

    with engine.connect() as connection:
        source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            """,
            params,
        )

        distinct_place_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(DISTINCT psr.place_id)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            """,
            params,
        )

        current_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.is_current = TRUE
            {source_ref_extra_filter}
            """,
            params,
        )

        deleted_source_ref_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.is_deleted_in_source = TRUE
            {source_ref_extra_filter}
            """,
            params,
        )

        missing_geom_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND psr.source_geom_point IS NULL
            {source_ref_extra_filter}
            """,
            params,
        )

        missing_name_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
              AND (psr.source_name_raw IS NULL OR BTRIM(psr.source_name_raw) = '')
            {source_ref_extra_filter}
            """,
            params,
        )

        places_without_primary_category_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
            WHERE NOT EXISTS (
                SELECT 1
                FROM hidden_gems.place_category pc
                WHERE pc.place_id = linked_places.place_id
                  AND pc.is_active = TRUE
                  AND pc.is_primary = TRUE
            )
            """,
            params,
        )

        places_without_current_neighborhood_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
            WHERE NOT EXISTS (
                SELECT 1
                FROM hidden_gems.place_neighborhood_assignment pna
                WHERE pna.place_id = linked_places.place_id
                  AND pna.is_current = TRUE
            )
            """,
            params,
        )

        validation_issue_count = fetch_scalar(
            connection,
            f"""
            SELECT COUNT(*)
            FROM hidden_gems.validation_issue vi
            WHERE 1=1
            {validation_extra_filter}
            """,
            params,
        )

        match_methods = fetch_rows(
            connection,
            f"""
            SELECT
                psr.match_method,
                COUNT(*) AS total,
                ROUND(AVG(psr.match_confidence)::numeric, 4) AS avg_match_confidence
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            GROUP BY psr.match_method
            ORDER BY total DESC, psr.match_method
            """,
            params,
        )

        assignment_methods = fetch_rows(
            connection,
            f"""
            SELECT pna.assignment_method, COUNT(*) AS total
            FROM hidden_gems.place_neighborhood_assignment pna
            JOIN (
                SELECT DISTINCT psr.place_id
                FROM hidden_gems.place_source_ref psr
                JOIN hidden_gems.source_system ss
                  ON ss.source_system_id = psr.source_system_id
                WHERE ss.source_code = :source_code
                {source_ref_extra_filter}
            ) linked_places
              ON linked_places.place_id = pna.place_id
            WHERE pna.is_current = TRUE
            GROUP BY pna.assignment_method
            ORDER BY total DESC, pna.assignment_method
            """,
            params,
        )

        sample_places = fetch_rows(
            connection,
            f"""
            SELECT
                p.place_id,
                p.display_name,
                p.address_text,
                psr.source_name_raw,
                psr.source_record_id,
                psr.source_primary_category_raw,
                psr.source_status_raw,
                psr.match_method,
                psr.match_confidence
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.place p
              ON p.place_id = psr.place_id
            JOIN hidden_gems.source_system ss
              ON ss.source_system_id = psr.source_system_id
            WHERE ss.source_code = :source_code
            {source_ref_extra_filter}
            ORDER BY psr.created_at DESC, p.display_name
            LIMIT 20
            """,
            params,
        )

    checks = {
        "has_google_place_source_refs": source_ref_count > 0,
        "all_source_refs_current": source_ref_count == current_source_ref_count,
        "no_deleted_source_refs": deleted_source_ref_count == 0,
        "no_missing_source_geometry": missing_geom_count == 0,
        "no_missing_source_name": missing_name_count == 0,
        "all_places_have_primary_category": places_without_primary_category_count == 0,
        "all_places_have_current_neighborhood": places_without_current_neighborhood_count == 0,
        "no_validation_issues_for_filtered_scope": validation_issue_count == 0,
    }

    failed_checks = [
        check_name
        for check_name, passed in checks.items()
        if not passed
    ]

    if failed_checks:
        raise ValueError(f"Check import Google Places fallido: {failed_checks}")

    return {
        "place_source_ref": {
            "count": source_ref_count,
            "distinct_place_count": distinct_place_count,
            "current_count": current_source_ref_count,
            "deleted_in_source_count": deleted_source_ref_count,
            "missing_geom_count": missing_geom_count,
            "missing_name_count": missing_name_count,
            "match_methods": match_methods,
        },
        "place": {
            "without_primary_category_count": places_without_primary_category_count,
            "without_current_neighborhood_count": places_without_current_neighborhood_count,
            "sample_places": sample_places,
        },
        "place_neighborhood_assignment": {
            "assignment_methods": assignment_methods,
        },
        "validation_issue": {
            "count": validation_issue_count,
        },
        "checks": checks,
    }


def summarize_candidate_statuses(
    candidates: list[NormalizedPlaceCandidate],
) -> dict[str, int]:
    counter = Counter(
        candidate.quality.candidate_status
        for candidate in candidates
    )
    return dict(counter)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logger.info(
        "Iniciando flujo completo Google Places | query_name=%s | text_query=%s | max_result_count=%s",
        args.query_name,
        args.text_query,
        args.max_result_count,
    )

    # 1. RAW INGESTION
    connector = GooglePlacesConnector()
    connector_result = connector.run_text_search(
        text_query=args.text_query,
        query_name=args.query_name,
        max_result_count=args.max_result_count,
        language_code=args.language_code,
        region_code=args.region_code,
        trigger_type=args.trigger_type,
        run_type=args.run_type,
    )

    run_context = connector_result["run_context"]
    raw_asset = connector_result["raw_asset"]
    payload = connector_result["payload"]

    raw_asset_id = raw_asset["raw_asset_id"]
    source_run_id = run_context.source_run_id

    staging_dir = settings.data_staging_path / "google_places" / raw_asset_id
    dedup_dir = staging_dir / "deduplication"
    import_dir = dedup_dir / "import"

    raw_checks = validate_raw_asset(
        raw_asset=raw_asset,
        payload=payload,
        run_context=run_context,
    )

    # 2. TRANSFORMACIÓN A STAGING
    transformer = GooglePlacesTransformer()
    transform_result = transformer.transform_payload(
        payload,
        source_run_id=source_run_id,
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

    transform_summary = {
        "file_path": raw_asset["storage_path"],
        "raw_asset_metadata": {
            "raw_asset_id": raw_asset_id,
            "storage_path": raw_asset["storage_path"],
            "asset_name": f"google_places_text_search_{args.query_name}",
            "query_name": args.query_name,
            "source_run_id": source_run_id,
        },
        "payload_metadata": transform_result.payload_metadata,
        "total_places": transform_result.total_places,
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

    staging_checks = validate_staging_outputs(
        transform_summary=transform_summary,
        accepted_candidates=accepted_candidates,
        needs_review_candidates=needs_review_candidates,
        rejected_candidates=rejected_candidates,
        issues=transform_result.issues,
    )

    # 3. DEDUPLICACIÓN
    dedup_candidates = accepted_candidates
    include_statuses = ["accepted"]

    if args.include_needs_review_in_dedup:
        dedup_candidates = accepted_candidates + needs_review_candidates
        include_statuses.append("needs_review")

    deduplicator = GooglePlacesDeduplicator()
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

    dedup_checks = validate_dedup_outputs(
        dedup_summary=dedup_summary,
        unique_candidates=dedup_result.unique_candidates,
        duplicate_groups=dedup_result.duplicate_groups,
        pair_evidences=dedup_result.pair_evidences,
    )

    # 4. IMPORTACIÓN CANÓNICA
    import_summary: dict[str, Any] | None = None
    import_check: dict[str, Any] | None = None

    if not args.skip_import:
        importer = GooglePlacesImporter()
        import_result = importer.import_candidates(
            candidates=dedup_result.unique_candidates,
            source_run_id=source_run_id,
            raw_asset_id=raw_asset_id,
        )

        import_summary = {
            "dedup_dir": str(dedup_dir),
            "source_run_id": source_run_id,
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

        import_check = build_import_check(
            source_run_id=source_run_id,
            raw_asset_id=raw_asset_id,
        )

    # 5. RESUMEN FINAL
    final_output = {
        "source_code": "google_places",
        "run_code": run_context.run_code,
        "source_run_id": source_run_id,
        "raw_asset_id": raw_asset_id,
        "storage_path": raw_asset["storage_path"],
        "query": {
            "text_query": args.text_query,
            "query_name": args.query_name,
            "max_result_count": args.max_result_count,
            "language_code": args.language_code,
            "region_code": args.region_code,
        },
        "raw_summary": connector_result["summary"],
        "checks": {
            "raw": raw_checks,
            "staging": staging_checks,
            "deduplication": dedup_checks,
            "import": import_check["checks"] if import_check else None,
        },
        "transform_summary": {
            "total_places": transform_result.total_places,
            "accepted_count": transform_result.accepted_count,
            "needs_review_count": transform_result.needs_review_count,
            "rejected_count": transform_result.rejected_count,
            "skipped_count": transform_result.skipped_count,
            "issue_count": len(transform_result.issues),
            "candidate_status_counts": summarize_candidate_statuses(transform_result.candidates),
        },
        "dedup_summary": {
            "processed_count": dedup_result.processed_count,
            "grouped_duplicate_count": dedup_result.grouped_duplicate_count,
            "duplicate_group_count": len(dedup_result.duplicate_groups),
            "pair_evidence_count": len(dedup_result.pair_evidences),
            "output_count": dedup_result.output_count,
        },
        "import_summary": import_summary["import_result"] if import_summary else None,
        "import_check": import_check,
        "paths": {
            "staging_dir": str(staging_dir),
            "dedup_dir": str(dedup_dir),
            "import_dir": str(import_dir) if not args.skip_import else None,
        },
        "skip_import": args.skip_import,
    }

    write_json_file(import_dir / "pipeline_summary.json", final_output)

    artifact_path = (
        settings.data_artifacts_path
        / "google_places_pipeline"
        / f"{raw_asset_id}_pipeline_summary.json"
    )
    write_json_file(artifact_path, final_output)

    print(json.dumps(final_output, ensure_ascii=False, indent=2, default=str))

    logger.info(
        "Flujo completo Google Places finalizado correctamente | raw_asset_id=%s | source_run_id=%s",
        raw_asset_id,
        source_run_id,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())