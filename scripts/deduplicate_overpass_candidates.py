from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.normalization.osm_overpass_deduplicator import OSMOverpassDeduplicator
from src.normalization.place_candidate import NormalizedPlaceCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Ejecuta la deduplicación intra-fuente sobre candidatos de Overpass ya transformados."
    )

    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--staging-dir",
        type=str,
        help="Ruta directa al directorio staging generado por transform_overpass_candidates.",
    )
    source_group.add_argument(
        "--raw-asset-id",
        type=str,
        help="raw_asset_id usado como carpeta staging en data/staging/osm_overpass.",
    )

    parser.add_argument(
        "--include-needs-review",
        action="store_true",
        help="Incluye también los candidatos needs_review en el proceso de deduplicación.",
    )

    parser.add_argument(
        "--preview-count",
        type=int,
        default=10,
        help="Número de grupos duplicados a mostrar por consola.",
    )

    return parser


def resolve_staging_dir(args: argparse.Namespace) -> Path:
    if args.staging_dir:
        staging_dir = Path(args.staging_dir)
    else:
        staging_dir = settings.data_staging_path / "osm_overpass" / args.raw_asset_id

    if not staging_dir.exists():
        raise FileNotFoundError(f"No existe el directorio staging: {staging_dir}")

    if not staging_dir.is_dir():
        raise ValueError(f"La ruta no es un directorio válido: {staging_dir}")

    return staging_dir


def load_json_file(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"No existe el fichero requerido: {path}")

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_output_dir(staging_dir: Path) -> Path:
    output_dir = staging_dir / "deduplication"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def deserialize_candidates(rows: list[dict[str, Any]]) -> list[NormalizedPlaceCandidate]:
    return [NormalizedPlaceCandidate.model_validate(row) for row in rows]


def serialize_candidate(candidate: NormalizedPlaceCandidate) -> dict[str, Any]:
    return candidate.model_dump(mode="json")


def serialize_duplicate_group(group: Any) -> dict[str, Any]:
    return {
        "group_id": group.group_id,
        "representative_key": group.representative_key,
        "representative_candidate": serialize_candidate(group.representative_candidate),
        "member_keys": group.member_keys,
        "member_candidates": [serialize_candidate(candidate) for candidate in group.member_candidates],
        "evidences": [
            {
                "left_candidate_key": evidence.left_candidate_key,
                "right_candidate_key": evidence.right_candidate_key,
                "score": evidence.score,
                "distance_m": evidence.distance_m,
                "signals": evidence.signals,
                "hard_rule_triggered": evidence.hard_rule_triggered,
            }
            for evidence in group.evidences
        ],
    }


def serialize_pair_evidence(evidence: Any) -> dict[str, Any]:
    return {
        "left_candidate_key": evidence.left_candidate_key,
        "right_candidate_key": evidence.right_candidate_key,
        "score": evidence.score,
        "distance_m": evidence.distance_m,
        "signals": evidence.signals,
        "hard_rule_triggered": evidence.hard_rule_triggered,
    }


def write_json_file(output_path: Path, data: Any) -> None:
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def build_preview(duplicate_groups: list[Any], preview_count: int) -> list[dict[str, Any]]:
    preview_rows: list[dict[str, Any]] = []

    for group in duplicate_groups[:preview_count]:
        preview_rows.append(
            {
                "group_id": group.group_id,
                "representative_key": group.representative_key,
                "representative_name": group.representative_candidate.names.display_name,
                "member_count": len(group.member_keys),
                "member_names": [
                    candidate.names.display_name
                    for candidate in group.member_candidates[:5]
                ],
                "signals": [
                    {
                        "score": evidence.score,
                        "distance_m": evidence.distance_m,
                        "signals": evidence.signals,
                        "hard_rule_triggered": evidence.hard_rule_triggered,
                    }
                    for evidence in group.evidences[:5]
                ],
            }
        )

    return preview_rows


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    staging_dir = resolve_staging_dir(args)
    output_dir = build_output_dir(staging_dir)

    summary = load_json_file(staging_dir / "summary.json")
    accepted_rows = load_json_file(staging_dir / "accepted_candidates.json")
    needs_review_rows = load_json_file(staging_dir / "needs_review_candidates.json")

    accepted_candidates = deserialize_candidates(accepted_rows)
    needs_review_candidates = deserialize_candidates(needs_review_rows)

    include_statuses = ["accepted"]
    input_candidates = accepted_candidates

    if args.include_needs_review:
        include_statuses.append("needs_review")
        input_candidates = accepted_candidates + needs_review_candidates

    deduplicator = OSMOverpassDeduplicator()
    result = deduplicator.deduplicate_candidates(
        input_candidates,
        include_statuses=tuple(include_statuses),
    )

    unique_candidates_payload = [
        serialize_candidate(candidate)
        for candidate in result.unique_candidates
    ]

    duplicate_groups_payload = [
        serialize_duplicate_group(group)
        for group in result.duplicate_groups
    ]

    pair_evidences_payload = [
        serialize_pair_evidence(evidence)
        for evidence in result.pair_evidences
    ]

    dedup_summary = {
        "staging_dir": str(staging_dir),
        "input_summary": summary,
        "include_statuses": include_statuses,
        "input_count": result.input_count,
        "processed_count": result.processed_count,
        "grouped_duplicate_count": result.grouped_duplicate_count,
        "duplicate_group_count": len(result.duplicate_groups),
        "pair_evidence_count": len(result.pair_evidences),
        "output_count": result.output_count,
        "output_dir": str(output_dir),
    }

    write_json_file(output_dir / "dedup_summary.json", dedup_summary)
    write_json_file(output_dir / "unique_candidates.json", unique_candidates_payload)
    write_json_file(output_dir / "duplicate_groups.json", duplicate_groups_payload)
    write_json_file(output_dir / "pair_evidences.json", pair_evidences_payload)

    console_output = {
        **dedup_summary,
        "duplicate_groups_preview": build_preview(
            result.duplicate_groups,
            args.preview_count,
        ),
    }

    print(json.dumps(console_output, ensure_ascii=False, indent=2, default=str))
    logger.info("Deduplicación Overpass completada correctamente.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())