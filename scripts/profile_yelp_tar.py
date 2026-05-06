from __future__ import annotations

import argparse
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config.settings import settings
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Perfila el archivo .tar del Yelp Open Dataset sin extraerlo completo."
    )

    parser.add_argument(
        "--tar-path",
        type=str,
        required=True,
        help="Ruta local al .tar del Yelp Open Dataset.",
    )

    parser.add_argument(
        "--save-artifact",
        action="store_true",
        help="Guarda el perfilado en data/artifacts/yelp_open_dataset_qa.",
    )

    return parser


def classify_member(name: str) -> str:
    lower_name = name.lower()

    if "business" in lower_name and lower_name.endswith(".json"):
        return "business"
    if "review" in lower_name and lower_name.endswith(".json"):
        return "review"
    if "user" in lower_name and lower_name.endswith(".json"):
        return "user"
    if "checkin" in lower_name and lower_name.endswith(".json"):
        return "checkin"
    if "tip" in lower_name and lower_name.endswith(".json"):
        return "tip"
    if "photo" in lower_name and lower_name.endswith(".json"):
        return "photo"
    if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
        return "photo_file"

    return "other"


def profile_tar(tar_path: Path) -> dict[str, Any]:
    if not tar_path.exists():
        raise FileNotFoundError(f"No existe el archivo tar: {tar_path}")

    if not tar_path.is_file():
        raise ValueError(f"La ruta no es un archivo: {tar_path}")

    members_profile: list[dict[str, Any]] = []
    total_size_bytes = 0

    with tarfile.open(tar_path, mode="r:*") as tar:
        members = tar.getmembers()

        for member in members:
            if not member.isfile():
                continue

            total_size_bytes += member.size

            members_profile.append(
                {
                    "name": member.name,
                    "size_bytes": member.size,
                    "size_mb": round(member.size / (1024 * 1024), 3),
                    "type_guess": classify_member(member.name),
                }
            )

    type_counts: dict[str, int] = {}
    type_sizes: dict[str, int] = {}

    for member in members_profile:
        type_guess = member["type_guess"]
        type_counts[type_guess] = type_counts.get(type_guess, 0) + 1
        type_sizes[type_guess] = type_sizes.get(type_guess, 0) + int(member["size_bytes"])

    expected_files = {
        "business": any(member["type_guess"] == "business" for member in members_profile),
        "review": any(member["type_guess"] == "review" for member in members_profile),
        "user": any(member["type_guess"] == "user" for member in members_profile),
        "checkin": any(member["type_guess"] == "checkin" for member in members_profile),
        "tip": any(member["type_guess"] == "tip" for member in members_profile),
        "photo": any(member["type_guess"] == "photo" for member in members_profile),
    }

    return {
        "tar_path": str(tar_path),
        "profiled_at": datetime.now(timezone.utc).isoformat(),
        "member_file_count": len(members_profile),
        "total_size_bytes": total_size_bytes,
        "total_size_gb": round(total_size_bytes / (1024**3), 3),
        "type_counts": type_counts,
        "type_sizes_mb": {
            key: round(value / (1024 * 1024), 3)
            for key, value in type_sizes.items()
        },
        "expected_files": expected_files,
        "members": members_profile,
    }


def save_artifact(profile: dict[str, Any], tar_path: Path) -> Path:
    output_dir = settings.data_artifacts_path / "yelp_open_dataset_qa"
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_name = tar_path.stem.replace(" ", "_").lower()
    output_path = output_dir / f"{safe_name}_tar_profile.json"

    output_path.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return output_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    tar_path = Path(args.tar_path)

    logger.info("Perfilando Yelp Open Dataset TAR | path=%s", tar_path)

    profile = profile_tar(tar_path)

    if args.save_artifact:
        artifact_path = save_artifact(profile, tar_path)
        profile["artifact_path"] = str(artifact_path)

    print(json.dumps(profile, ensure_ascii=False, indent=2, default=str))

    logger.info("Perfilado del TAR de Yelp completado correctamente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())