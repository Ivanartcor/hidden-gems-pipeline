from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


DEFAULT_TARGET_TYPES = ["business", "review"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Extrae de forma controlada ficheros seleccionados del Yelp Open Dataset TAR."
        )
    )

    parser.add_argument(
        "--tar-path",
        type=str,
        required=True,
        help="Ruta local al .tar del Yelp Open Dataset.",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/external/yelp_open_dataset/extracted",
        help="Directorio donde extraer los ficheros seleccionados.",
    )

    parser.add_argument(
        "--include-tip",
        action="store_true",
        help="También extrae tip.json. No necesario para la primera fase.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescribe ficheros si ya existen.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda manifest en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def classify_member(name: str) -> str:
    lower_name = name.lower()

    if "business" in lower_name and lower_name.endswith(".json"):
        return "business"
    if "review" in lower_name and lower_name.endswith(".json"):
        return "review"
    if "tip" in lower_name and lower_name.endswith(".json"):
        return "tip"
    if "user" in lower_name and lower_name.endswith(".json"):
        return "user"
    if "checkin" in lower_name and lower_name.endswith(".json"):
        return "checkin"
    if "photo" in lower_name and lower_name.endswith(".json"):
        return "photo"

    return "other"


def safe_output_path(output_dir: Path, member_name: str) -> Path:
    """
    Evita path traversal.

    Aunque el tar oficial debería ser seguro, nunca conviene extraer paths
    arbitrarios directamente.
    """
    filename = Path(member_name).name
    target_path = output_dir / filename

    resolved_output_dir = output_dir.resolve()
    resolved_target_path = target_path.resolve()

    if not str(resolved_target_path).startswith(str(resolved_output_dir)):
        raise ValueError(f"Ruta insegura detectada dentro del TAR: {member_name}")

    return target_path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def count_lines(path: Path, chunk_size: int = 1024 * 1024) -> int:
    count = 0

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            count += chunk.count(b"\n")

    return count


def extract_selected_files(
    *,
    tar_path: Path,
    output_dir: Path,
    target_types: set[str],
    overwrite: bool,
) -> dict[str, Any]:
    if not tar_path.exists():
        raise FileNotFoundError(f"No existe el TAR: {tar_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    extracted_files: list[dict[str, Any]] = []
    skipped_files: list[dict[str, Any]] = []
    available_members: list[dict[str, Any]] = []

    with tarfile.open(tar_path, mode="r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue

            member_type = classify_member(member.name)

            available_members.append(
                {
                    "name": member.name,
                    "type_guess": member_type,
                    "size_bytes": member.size,
                    "size_mb": round(member.size / (1024 * 1024), 3),
                }
            )

            if member_type not in target_types:
                skipped_files.append(
                    {
                        "name": member.name,
                        "type_guess": member_type,
                        "reason": "not_requested",
                    }
                )
                continue

            target_path = safe_output_path(output_dir, member.name)

            if target_path.exists() and not overwrite:
                file_info = {
                    "name": member.name,
                    "type_guess": member_type,
                    "output_path": str(target_path),
                    "size_bytes": target_path.stat().st_size,
                    "size_mb": round(target_path.stat().st_size / (1024 * 1024), 3),
                    "sha256": sha256_file(target_path),
                    "line_count": count_lines(target_path),
                    "status": "already_exists",
                }
                extracted_files.append(file_info)
                continue

            source_file = tar.extractfile(member)
            if source_file is None:
                skipped_files.append(
                    {
                        "name": member.name,
                        "type_guess": member_type,
                        "reason": "extractfile_returned_none",
                    }
                )
                continue

            logger.info(
                "Extrayendo miembro Yelp | member=%s | output=%s",
                member.name,
                target_path,
            )

            with source_file, target_path.open("wb") as output_file:
                shutil.copyfileobj(source_file, output_file)

            file_info = {
                "name": member.name,
                "type_guess": member_type,
                "output_path": str(target_path),
                "size_bytes": target_path.stat().st_size,
                "size_mb": round(target_path.stat().st_size / (1024 * 1024), 3),
                "sha256": sha256_file(target_path),
                "line_count": count_lines(target_path),
                "status": "extracted",
            }

            extracted_files.append(file_info)

    extracted_types = {
        file_info["type_guess"]
        for file_info in extracted_files
    }

    missing_requested_types = sorted(target_types - extracted_types)

    return {
        "tar_path": str(tar_path),
        "output_dir": str(output_dir),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_types": sorted(target_types),
        "available_member_count": len(available_members),
        "available_members": available_members,
        "extracted_files": extracted_files,
        "skipped_files": skipped_files,
        "missing_requested_types": missing_requested_types,
        "checks": {
            "all_requested_types_extracted": len(missing_requested_types) == 0,
            "has_business": "business" in extracted_types,
            "has_review": "review" in extracted_types,
        },
    }


def save_artifact(manifest: dict[str, Any], tar_path: Path) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = tar_path.stem.replace(" ", "_").lower()
    output_path = output_dir / f"{safe_name}_selected_extract_manifest.json"

    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    tar_path = Path(args.tar_path)
    output_dir = Path(args.output_dir)

    target_types = set(DEFAULT_TARGET_TYPES)
    if args.include_tip:
        target_types.add("tip")

    logger.info(
        "Iniciando extracción controlada Yelp | tar=%s | output_dir=%s | target_types=%s",
        tar_path,
        output_dir,
        sorted(target_types),
    )

    manifest = extract_selected_files(
        tar_path=tar_path,
        output_dir=output_dir,
        target_types=target_types,
        overwrite=args.overwrite,
    )

    if args.save_artifact:
        artifact_path = save_artifact(manifest, tar_path)
        manifest["artifact_path"] = str(artifact_path)

    print(json.dumps(manifest, ensure_ascii=False, indent=2, default=str))

    failed_checks = [
        check_name
        for check_name, passed in manifest["checks"].items()
        if not passed
    ]

    if failed_checks:
        logger.warning(
            "Extracción Yelp completada con checks fallidos: %s",
            failed_checks,
        )
        return 1

    logger.info("Extracción controlada Yelp completada correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())