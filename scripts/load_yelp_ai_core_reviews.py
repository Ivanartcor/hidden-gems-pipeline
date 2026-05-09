"""Load the Yelp AI prototype core places and reviews into PostgreSQL.

This script creates the canonical bridge needed before loading downstream AI artifacts:

Yelp business_id -> hidden_gems.place_source_ref -> hidden_gems.place
Yelp review_id   -> hidden_gems.review.source_review_id -> hidden_gems.review

It is intended for the Yelp-based AI prototype corpus used by Hidden Gems.
It does NOT load dish mentions, sentiment, signal aggregation or ranking. Those
loaders should run only after this script makes the Yelp business/review mapping
available in the core model.

Required input files from the Yelp filtering/AI preparation stage:

- food_businesses.jsonl
  One row per Yelp food business, including latitude/longitude.

- food_reviews.jsonl
  One row per Yelp food review, including source_review_id, source_business_id,
  rating_value, review_text_raw and review_date.

Recommended execution from the repository root.

Windows PowerShell:
    python -m scripts.load_yelp_ai_core_reviews `
      --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
      --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl `
      --dry-run

    python -m scripts.load_yelp_ai_core_reviews `
      --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl `
      --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl

Linux/macOS:
    python -m scripts.load_yelp_ai_core_reviews \
      --businesses-path data/artifacts/ai/yelp/food_businesses.jsonl \
      --reviews-path data/artifacts/ai/yelp/food_reviews.jsonl \
      --dry-run

The script is idempotent. It reuses existing place_source_ref rows for Yelp
businesses and upserts reviews by (source_system_id, source_place_record_id,
source_review_id).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy import text
from sqlalchemy.engine import Connection

try:
    from tqdm.auto import tqdm
except Exception:  # pragma: no cover
    def tqdm(iterable: Iterable, **_: Any):
        return iterable

from src.db.database import engine


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_SCHEMA = "hidden_gems"
DEFAULT_SOURCE_CODE = "yelp_open_dataset"
DEFAULT_RUN_CODE = "yelp_ai_core_reviews_import_v1"
DEFAULT_BUSINESS_ENTITY_TYPE = "yelp_business"
DEFAULT_REVIEW_ENTITY_TYPE = "yelp_review"

SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


# -----------------------------------------------------------------------------
# Data classes
# -----------------------------------------------------------------------------

@dataclass
class FileStats:
    path: str
    exists: bool
    size_bytes: int | None
    checksum_sha256: str | None
    line_count: int | None


@dataclass
class LoadStats:
    source_system_code: str
    run_code: str
    businesses_seen_in_reviews: int
    businesses_loaded_from_file: int
    businesses_missing_from_business_file: int
    businesses_skipped_missing_coordinates: int
    places_created: int
    place_source_refs_created: int
    place_source_refs_updated_or_reused: int
    reviews_seen: int
    reviews_skipped_missing_required_fields: int
    reviews_skipped_missing_place_mapping: int
    reviews_upserted: int
    dry_run: bool


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_schema_name(schema: str) -> str:
    schema = str(schema).strip()
    if not SCHEMA_RE.match(schema):
        raise ValueError(f"Invalid schema name: {schema!r}")
    return schema


def qname(schema: str, table: str) -> str:
    schema = validate_schema_name(schema)
    return f'"{schema}"."{table}"'


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def truncate(value: Any, max_len: int) -> str | None:
    value = normalize_space(value)
    if not value:
        return None
    return value[:max_len]


def normalize_for_match(value: Any) -> str:
    value = normalize_space(value).lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9áéíóúüñ]+", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return default


def safe_float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except Exception:
        return default


def clamp(value: float | None, min_value: float, max_value: float) -> float | None:
    if value is None:
        return None
    return max(min_value, min(max_value, value))


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def sha256_text(value: Any) -> str:
    return hashlib.sha256(json_dumps(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count(path: Path) -> int:
    count = 0
    with path.open("rb") as f:
        for _ in f:
            count += 1
    return count


def iter_jsonl(path: Path, desc: str | None = None) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        iterator = tqdm(f, desc=desc or path.name)
        for line_number, line in enumerate(iterator, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {path} line {line_number}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"Expected JSON object in {path} line {line_number}")
            yield obj


def build_full_address(business: dict[str, Any]) -> str | None:
    parts = [
        normalize_space(business.get("address")),
        normalize_space(business.get("city")),
        normalize_space(business.get("state")),
        normalize_space(business.get("postal_code")),
    ]
    parts = [p for p in parts if p]
    return ", ".join(parts) if parts else None


def get_categories_list(business: dict[str, Any]) -> list[str]:
    categories = business.get("categories_list")
    if isinstance(categories, list):
        return [normalize_space(x) for x in categories if normalize_space(x)]

    raw = business.get("categories_raw") or business.get("categories")
    if isinstance(raw, str):
        return [normalize_space(x) for x in raw.split(",") if normalize_space(x)]

    return []


def get_primary_category(business: dict[str, Any]) -> str | None:
    food_tags = business.get("food_category_tags")
    if isinstance(food_tags, list) and food_tags:
        return truncate(food_tags[0], 255)

    categories = get_categories_list(business)
    if categories:
        return truncate(categories[0], 255)

    return None


def source_status_from_is_open(value: Any) -> str | None:
    parsed = safe_int(value, default=None)
    if parsed is None:
        return None
    return "open" if parsed == 1 else "closed"


def file_stats(path: Path, calculate_checksum: bool = True, calculate_lines: bool = True) -> FileStats:
    path = Path(path)
    exists = path.exists()
    if not exists:
        return FileStats(str(path), False, None, None, None)

    return FileStats(
        path=str(path),
        exists=True,
        size_bytes=path.stat().st_size,
        checksum_sha256=sha256_file(path) if calculate_checksum else None,
        line_count=line_count(path) if calculate_lines else None,
    )


# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------


def fetch_one_uuid(conn: Connection, sql: str, params: dict[str, Any]) -> str | None:
    row = conn.execute(text(sql), params).mappings().first()
    if row is None:
        return None
    value = next(iter(row.values()))
    return str(value) if value is not None else None


def ensure_source_system(conn: Connection, schema: str, source_code: str) -> str:
    sql = f"""
        INSERT INTO {qname(schema, 'source_system')} (
            source_code,
            source_name,
            source_type,
            description,
            base_url,
            auth_type,
            data_format_default,
            refresh_mode_default,
            supports_incremental,
            is_active,
            notes
        ) VALUES (
            :source_code,
            'Yelp Open Dataset',
            'bulk_dataset',
            'Yelp Open Dataset imported as an AI prototype corpus for Hidden Gems.',
            'https://www.yelp.com/dataset',
            'none',
            'jsonl',
            'manual_snapshot',
            FALSE,
            TRUE,
            'Prototype source used for AI module development and validation. Not Sevilla production data.'
        )
        ON CONFLICT (source_code)
        DO UPDATE SET
            source_name = EXCLUDED.source_name,
            source_type = EXCLUDED.source_type,
            description = EXCLUDED.description,
            base_url = EXCLUDED.base_url,
            auth_type = EXCLUDED.auth_type,
            data_format_default = EXCLUDED.data_format_default,
            refresh_mode_default = EXCLUDED.refresh_mode_default,
            supports_incremental = EXCLUDED.supports_incremental,
            is_active = EXCLUDED.is_active,
            notes = EXCLUDED.notes
        RETURNING source_system_id;
    """
    return str(conn.execute(text(sql), {"source_code": source_code}).scalar_one())


def ensure_source_run(
    conn: Connection,
    schema: str,
    run_code: str,
    source_system_id: str,
    request_summary: dict[str, Any],
    notes: str,
    dry_run: bool,
) -> str:
    if dry_run:
        existing = fetch_one_uuid(
            conn,
            f"SELECT source_run_id FROM {qname(schema, 'source_run')} WHERE run_code = :run_code",
            {"run_code": run_code},
        )
        return existing or "DRY_RUN_SOURCE_RUN_ID"

    now = utc_now()
    sql = f"""
        INSERT INTO {qname(schema, 'source_run')} (
            run_code,
            source_system_id,
            run_type,
            trigger_type,
            status,
            started_at,
            finished_at,
            duration_seconds,
            request_summary,
            notes,
            raw_asset_count
        ) VALUES (
            :run_code,
            :source_system_id,
            'manual_import',
            'cli',
            'running',
            :now,
            NULL,
            NULL,
            CAST(:request_summary AS jsonb),
            :notes,
            0
        )
        ON CONFLICT (run_code)
        DO UPDATE SET
            source_system_id = EXCLUDED.source_system_id,
            run_type = EXCLUDED.run_type,
            trigger_type = EXCLUDED.trigger_type,
            status = 'running',
            started_at = EXCLUDED.started_at,
            finished_at = NULL,
            duration_seconds = NULL,
            request_summary = EXCLUDED.request_summary,
            notes = EXCLUDED.notes,
            raw_asset_count = 0,
            records_extracted_count = 0,
            records_staged_count = 0,
            records_rejected_count = 0,
            error_count = 0,
            warning_count = 0
        RETURNING source_run_id;
    """
    return str(
        conn.execute(
            text(sql),
            {
                "run_code": run_code,
                "source_system_id": source_system_id,
                "now": now,
                "request_summary": json_dumps(request_summary),
                "notes": notes,
            },
        ).scalar_one()
    )


def upsert_raw_asset(
    conn: Connection,
    schema: str,
    *,
    asset_code: str,
    source_system_id: str,
    source_run_id: str,
    asset_name: str,
    storage_path: str,
    file_format: str,
    file_size_bytes: int | None,
    record_count_estimated: int | None,
    checksum_sha256: str | None,
    notes: str,
    dry_run: bool,
) -> str | None:
    if dry_run:
        existing = fetch_one_uuid(
            conn,
            f"SELECT raw_asset_id FROM {qname(schema, 'raw_asset')} WHERE asset_code = :asset_code",
            {"asset_code": asset_code},
        )
        return existing

    sql = f"""
        INSERT INTO {qname(schema, 'raw_asset')} (
            asset_code,
            source_system_id,
            source_run_id,
            asset_name,
            asset_type,
            storage_path,
            file_format,
            file_size_bytes,
            record_count_estimated,
            checksum_sha256,
            retention_class,
            is_available,
            notes
        ) VALUES (
            :asset_code,
            :source_system_id,
            :source_run_id,
            :asset_name,
            'bulk_file',
            :storage_path,
            :file_format,
            :file_size_bytes,
            :record_count_estimated,
            :checksum_sha256,
            'long_term',
            TRUE,
            :notes
        )
        ON CONFLICT (asset_code)
        DO UPDATE SET
            source_system_id = EXCLUDED.source_system_id,
            source_run_id = EXCLUDED.source_run_id,
            asset_name = EXCLUDED.asset_name,
            asset_type = EXCLUDED.asset_type,
            storage_path = EXCLUDED.storage_path,
            file_format = EXCLUDED.file_format,
            file_size_bytes = EXCLUDED.file_size_bytes,
            record_count_estimated = EXCLUDED.record_count_estimated,
            checksum_sha256 = EXCLUDED.checksum_sha256,
            retention_class = EXCLUDED.retention_class,
            is_available = EXCLUDED.is_available,
            notes = EXCLUDED.notes
        RETURNING raw_asset_id;
    """
    return str(
        conn.execute(
            text(sql),
            {
                "asset_code": asset_code,
                "source_system_id": source_system_id,
                "source_run_id": source_run_id,
                "asset_name": asset_name,
                "storage_path": storage_path,
                "file_format": file_format,
                "file_size_bytes": file_size_bytes,
                "record_count_estimated": record_count_estimated,
                "checksum_sha256": checksum_sha256 if checksum_sha256 and SHA256_RE.match(checksum_sha256) else None,
                "notes": notes,
            },
        ).scalar_one()
    )


def get_existing_place_ref(
    conn: Connection,
    schema: str,
    source_system_id: str,
    business_id: str,
) -> dict[str, Any] | None:
    sql = f"""
        SELECT place_source_ref_id, place_id
        FROM {qname(schema, 'place_source_ref')}
        WHERE source_system_id = :source_system_id
          AND source_entity_type = :source_entity_type
          AND source_record_id = :business_id
    """
    row = conn.execute(
        text(sql),
        {
            "source_system_id": source_system_id,
            "source_entity_type": DEFAULT_BUSINESS_ENTITY_TYPE,
            "business_id": business_id,
        },
    ).mappings().first()
    return dict(row) if row else None


def insert_place(conn: Connection, schema: str, business: dict[str, Any]) -> str:
    name = truncate(business.get("name"), 255) or f"Yelp business {business['business_id']}"
    address = build_full_address(business)
    lat = safe_float(business.get("latitude"))
    lon = safe_float(business.get("longitude"))

    sql = f"""
        INSERT INTO {qname(schema, 'place')} (
            canonical_name,
            normalized_name,
            display_name,
            address_text,
            address_normalized,
            geom_point,
            latitude,
            longitude,
            place_confidence,
            is_active
        ) VALUES (
            :canonical_name,
            :normalized_name,
            :display_name,
            :address_text,
            :address_normalized,
            ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326),
            :latitude,
            :longitude,
            :place_confidence,
            TRUE
        )
        RETURNING place_id;
    """
    return str(
        conn.execute(
            text(sql),
            {
                "canonical_name": name,
                "normalized_name": normalize_for_match(name)[:255] or name.lower(),
                "display_name": name,
                "address_text": truncate(address, 500),
                "address_normalized": truncate(normalize_for_match(address), 500),
                "latitude": lat,
                "longitude": lon,
                "place_confidence": clamp(safe_float(business.get("food_confidence"), 0.95), 0, 1),
            },
        ).scalar_one()
    )


def upsert_place_source_ref(
    conn: Connection,
    schema: str,
    *,
    place_id: str,
    source_system_id: str,
    source_run_id: str,
    raw_asset_id: str | None,
    business: dict[str, Any],
) -> tuple[str, bool]:
    business_id = normalize_space(business.get("business_id"))
    name = truncate(business.get("name"), 255) or f"Yelp business {business_id}"
    address = build_full_address(business)
    lat = safe_float(business.get("latitude"))
    lon = safe_float(business.get("longitude"))
    categories_list = get_categories_list(business)
    source_payload = business.get("source_payload") if isinstance(business.get("source_payload"), dict) else business

    existed = get_existing_place_ref(conn, schema, source_system_id, business_id) is not None

    sql = f"""
        INSERT INTO {qname(schema, 'place_source_ref')} (
            place_id,
            source_system_id,
            source_run_id,
            raw_asset_id,
            source_entity_type,
            source_record_id,
            source_name_raw,
            source_address_raw,
            source_geom_point,
            source_latitude,
            source_longitude,
            source_rating,
            source_review_count,
            source_primary_category_raw,
            source_categories_raw,
            source_status_raw,
            source_payload_hash,
            match_method,
            match_confidence,
            is_current,
            is_deleted_in_source,
            first_seen_run_id,
            last_seen_run_id
        ) VALUES (
            :place_id,
            :source_system_id,
            :source_run_id,
            :raw_asset_id,
            :source_entity_type,
            :source_record_id,
            :source_name_raw,
            :source_address_raw,
            ST_SetSRID(ST_MakePoint(:source_longitude, :source_latitude), 4326),
            :source_latitude,
            :source_longitude,
            :source_rating,
            :source_review_count,
            :source_primary_category_raw,
            CAST(:source_categories_raw AS jsonb),
            :source_status_raw,
            :source_payload_hash,
            'source_record_seed',
            :match_confidence,
            TRUE,
            :is_deleted_in_source,
            :source_run_id,
            :source_run_id
        )
        ON CONFLICT (source_system_id, source_entity_type, source_record_id)
        DO UPDATE SET
            source_run_id = EXCLUDED.source_run_id,
            raw_asset_id = EXCLUDED.raw_asset_id,
            source_name_raw = EXCLUDED.source_name_raw,
            source_address_raw = EXCLUDED.source_address_raw,
            source_geom_point = EXCLUDED.source_geom_point,
            source_latitude = EXCLUDED.source_latitude,
            source_longitude = EXCLUDED.source_longitude,
            source_rating = EXCLUDED.source_rating,
            source_review_count = EXCLUDED.source_review_count,
            source_primary_category_raw = EXCLUDED.source_primary_category_raw,
            source_categories_raw = EXCLUDED.source_categories_raw,
            source_status_raw = EXCLUDED.source_status_raw,
            source_payload_hash = EXCLUDED.source_payload_hash,
            match_method = EXCLUDED.match_method,
            match_confidence = EXCLUDED.match_confidence,
            is_current = TRUE,
            is_deleted_in_source = EXCLUDED.is_deleted_in_source,
            last_seen_run_id = EXCLUDED.last_seen_run_id
        RETURNING place_source_ref_id;
    """
    place_source_ref_id = str(
        conn.execute(
            text(sql),
            {
                "place_id": place_id,
                "source_system_id": source_system_id,
                "source_run_id": source_run_id,
                "raw_asset_id": raw_asset_id,
                "source_entity_type": DEFAULT_BUSINESS_ENTITY_TYPE,
                "source_record_id": business_id,
                "source_name_raw": name,
                "source_address_raw": truncate(address, 500),
                "source_latitude": lat,
                "source_longitude": lon,
                "source_rating": clamp(safe_float(business.get("stars")), 0, 5),
                "source_review_count": safe_int(business.get("review_count"), default=None),
                "source_primary_category_raw": get_primary_category(business),
                "source_categories_raw": json_dumps(categories_list),
                "source_status_raw": source_status_from_is_open(business.get("is_open")),
                "source_payload_hash": sha256_text(source_payload),
                "match_confidence": clamp(safe_float(business.get("food_confidence"), 0.95), 0, 1),
                "is_deleted_in_source": safe_int(business.get("is_open"), 1) == 0,
            },
        ).scalar_one()
    )
    return place_source_ref_id, not existed


def upsert_review(
    conn: Connection,
    schema: str,
    *,
    place_id: str,
    place_source_ref_id: str,
    source_system_id: str,
    source_run_id: str,
    raw_asset_id: str | None,
    review: dict[str, Any],
) -> str:
    review_text = normalize_space(review.get("review_text_raw"))
    review_text_normalized = normalize_space(review.get("review_text_normalized")) or review_text
    source_review_id = normalize_space(review.get("source_review_id"))
    source_business_id = normalize_space(review.get("source_business_id"))

    source_payload = {
        "source_system_code": review.get("source_system_code"),
        "source_dataset": review.get("source_dataset"),
        "source_entity_type": review.get("source_entity_type"),
        "source_review_id": source_review_id,
        "source_business_id": source_business_id,
        "source_user_id": review.get("source_user_id"),
        "rating_value": review.get("rating_value"),
        "review_date": review.get("review_date"),
        "useful_count": review.get("useful_count"),
        "funny_count": review.get("funny_count"),
        "cool_count": review.get("cool_count"),
        "is_food_review_candidate": review.get("is_food_review_candidate"),
        "is_training_eligible": review.get("is_training_eligible"),
    }

    sql = f"""
        INSERT INTO {qname(schema, 'review')} (
            place_id,
            place_source_ref_id,
            source_system_id,
            source_run_id,
            source_review_id,
            author_name_raw,
            rating_value,
            review_text_raw,
            review_text_normalized,
            review_language,
            review_created_at,
            helpful_count,
            text_length_chars,
            raw_asset_id,
            source_place_record_id,
            source_payload_hash,
            is_operational_review,
            is_training_eligible,
            is_active,
            is_deleted_in_source
        ) VALUES (
            :place_id,
            :place_source_ref_id,
            :source_system_id,
            :source_run_id,
            :source_review_id,
            :author_name_raw,
            :rating_value,
            :review_text_raw,
            :review_text_normalized,
            :review_language,
            :review_created_at,
            :helpful_count,
            :text_length_chars,
            :raw_asset_id,
            :source_place_record_id,
            :source_payload_hash,
            TRUE,
            :is_training_eligible,
            TRUE,
            FALSE
        )
        ON CONFLICT (source_system_id, source_place_record_id, source_review_id)
        WHERE source_place_record_id IS NOT NULL
          AND source_review_id IS NOT NULL
        DO UPDATE SET
            place_id = EXCLUDED.place_id,
            place_source_ref_id = EXCLUDED.place_source_ref_id,
            source_run_id = EXCLUDED.source_run_id,
            author_name_raw = EXCLUDED.author_name_raw,
            rating_value = EXCLUDED.rating_value,
            review_text_raw = EXCLUDED.review_text_raw,
            review_text_normalized = EXCLUDED.review_text_normalized,
            review_language = EXCLUDED.review_language,
            review_created_at = EXCLUDED.review_created_at,
            helpful_count = EXCLUDED.helpful_count,
            text_length_chars = EXCLUDED.text_length_chars,
            raw_asset_id = EXCLUDED.raw_asset_id,
            source_payload_hash = EXCLUDED.source_payload_hash,
            is_operational_review = TRUE,
            is_training_eligible = EXCLUDED.is_training_eligible,
            is_active = TRUE,
            is_deleted_in_source = FALSE
        RETURNING review_id;
    """

    return str(
        conn.execute(
            text(sql),
            {
                "place_id": place_id,
                "place_source_ref_id": place_source_ref_id,
                "source_system_id": source_system_id,
                "source_run_id": source_run_id,
                "source_review_id": source_review_id,
                # Yelp source_user_id is not a display name; keep it out of author_name_raw.
                "author_name_raw": None,
                "rating_value": clamp(safe_float(review.get("rating_value")), 0, 5),
                "review_text_raw": review_text,
                "review_text_normalized": review_text_normalized,
                "review_language": truncate(review.get("language") or "en", 10),
                "review_created_at": review.get("review_date"),
                "helpful_count": safe_int(review.get("useful_count"), default=None),
                "text_length_chars": safe_int(review.get("text_length_chars"), default=len(review_text)),
                "raw_asset_id": raw_asset_id,
                "source_place_record_id": source_business_id,
                "source_payload_hash": sha256_text(source_payload),
                "is_training_eligible": bool(review.get("is_training_eligible", True)),
            },
        ).scalar_one()
    )


def finalize_source_run(
    conn: Connection,
    schema: str,
    source_run_id: str,
    stats: LoadStats,
    started_at: datetime,
) -> None:
    finished_at = utc_now()
    duration_seconds = int((finished_at - started_at).total_seconds())
    warning_count = (
        stats.businesses_missing_from_business_file
        + stats.businesses_skipped_missing_coordinates
        + stats.reviews_skipped_missing_required_fields
        + stats.reviews_skipped_missing_place_mapping
    )
    status = "completed_with_warnings" if warning_count > 0 else "completed"

    sql = f"""
        UPDATE {qname(schema, 'source_run')}
        SET
            status = :status,
            finished_at = :finished_at,
            duration_seconds = :duration_seconds,
            records_extracted_count = :records_extracted_count,
            records_staged_count = :records_staged_count,
            records_rejected_count = :records_rejected_count,
            raw_asset_count = 2,
            error_count = 0,
            warning_count = :warning_count,
            request_summary = CAST(:request_summary AS jsonb)
        WHERE source_run_id = :source_run_id;
    """
    conn.execute(
        text(sql),
        {
            "source_run_id": source_run_id,
            "status": status,
            "finished_at": finished_at,
            "duration_seconds": duration_seconds,
            "records_extracted_count": stats.reviews_seen,
            "records_staged_count": stats.reviews_upserted,
            "records_rejected_count": stats.reviews_skipped_missing_required_fields + stats.reviews_skipped_missing_place_mapping,
            "warning_count": warning_count,
            "request_summary": json_dumps(asdict(stats)),
        },
    )


# -----------------------------------------------------------------------------
# Input scanning and validation
# -----------------------------------------------------------------------------


def collect_review_business_ids(reviews_path: Path, max_reviews: int | None = None) -> tuple[set[str], int, int]:
    business_ids: set[str] = set()
    reviews_seen = 0
    reviews_missing_required = 0

    for review in iter_jsonl(reviews_path, desc="Scanning review business IDs"):
        if max_reviews is not None and reviews_seen >= max_reviews:
            break

        reviews_seen += 1
        source_review_id = normalize_space(review.get("source_review_id"))
        source_business_id = normalize_space(review.get("source_business_id"))
        review_text = normalize_space(review.get("review_text_raw"))

        if not source_review_id or not source_business_id or not review_text:
            reviews_missing_required += 1
            continue

        business_ids.add(source_business_id)

    return business_ids, reviews_seen, reviews_missing_required


def load_businesses_map(
    businesses_path: Path,
    referenced_business_ids: set[str] | None,
    load_all_businesses: bool = False,
    max_businesses: int | None = None,
) -> tuple[dict[str, dict[str, Any]], int]:
    businesses: dict[str, dict[str, Any]] = {}
    rows_seen = 0

    for business in iter_jsonl(businesses_path, desc="Loading businesses"):
        if max_businesses is not None and rows_seen >= max_businesses:
            break

        rows_seen += 1
        business_id = normalize_space(business.get("business_id"))
        if not business_id:
            continue

        if load_all_businesses or referenced_business_ids is None or business_id in referenced_business_ids:
            businesses[business_id] = business

    return businesses, rows_seen


# -----------------------------------------------------------------------------
# Main load flow
# -----------------------------------------------------------------------------


def load_yelp_core(args: argparse.Namespace) -> LoadStats:
    schema = validate_schema_name(args.schema)
    businesses_path = Path(args.businesses_path)
    reviews_path = Path(args.reviews_path)

    if not businesses_path.exists():
        raise FileNotFoundError(f"Businesses file not found: {businesses_path}")
    if not reviews_path.exists():
        raise FileNotFoundError(f"Reviews file not found: {reviews_path}")

    print("Preparing file statistics...")
    business_file_stats = file_stats(
        businesses_path,
        calculate_checksum=not args.skip_checksum,
        calculate_lines=not args.skip_line_count,
    )
    review_file_stats = file_stats(
        reviews_path,
        calculate_checksum=not args.skip_checksum,
        calculate_lines=not args.skip_line_count,
    )

    referenced_business_ids, reviews_seen, reviews_missing_required_scan = collect_review_business_ids(
        reviews_path,
        max_reviews=args.max_reviews,
    )

    businesses_map, business_rows_seen = load_businesses_map(
        businesses_path,
        referenced_business_ids=referenced_business_ids,
        load_all_businesses=args.load_all_businesses,
        max_businesses=args.max_businesses,
    )

    missing_business_ids = referenced_business_ids - set(businesses_map)

    missing_coordinates = {
        business_id
        for business_id, business in businesses_map.items()
        if safe_float(business.get("latitude")) is None or safe_float(business.get("longitude")) is None
    }

    print("\nInput summary")
    print("-------------")
    print(f"Reviews seen: {reviews_seen:,}")
    print(f"Referenced businesses in reviews: {len(referenced_business_ids):,}")
    print(f"Businesses loaded from file: {len(businesses_map):,}")
    print(f"Businesses missing from business file: {len(missing_business_ids):,}")
    print(f"Businesses missing coordinates: {len(missing_coordinates):,}")

    if args.strict and (missing_business_ids or missing_coordinates or reviews_missing_required_scan):
        raise ValueError(
            "Strict mode failed: missing businesses, missing coordinates or invalid reviews were found. "
            "Run without --strict to skip invalid rows."
        )

    if args.dry_run:
        stats = LoadStats(
            source_system_code=args.source_code,
            run_code=args.run_code,
            businesses_seen_in_reviews=len(referenced_business_ids),
            businesses_loaded_from_file=len(businesses_map),
            businesses_missing_from_business_file=len(missing_business_ids),
            businesses_skipped_missing_coordinates=len(missing_coordinates),
            places_created=0,
            place_source_refs_created=0,
            place_source_refs_updated_or_reused=0,
            reviews_seen=reviews_seen,
            reviews_skipped_missing_required_fields=reviews_missing_required_scan,
            reviews_skipped_missing_place_mapping=0,
            reviews_upserted=0,
            dry_run=True,
        )
        print("\nDRY RUN. No database writes were performed.")
        print(json.dumps(asdict(stats), indent=2, ensure_ascii=False))
        return stats

    started_at = utc_now()

    with engine.begin() as conn:
        source_system_id = ensure_source_system(conn, schema, args.source_code)

        request_summary = {
            "loader": "load_yelp_ai_core_reviews.py",
            "businesses_path": str(businesses_path),
            "reviews_path": str(reviews_path),
            "business_file_stats": asdict(business_file_stats),
            "review_file_stats": asdict(review_file_stats),
            "load_all_businesses": args.load_all_businesses,
            "max_businesses": args.max_businesses,
            "max_reviews": args.max_reviews,
            "purpose": "AI prototype core import for Yelp-derived Hidden Gems experiments.",
        }

        source_run_id = ensure_source_run(
            conn,
            schema,
            args.run_code,
            source_system_id,
            request_summary,
            notes="Yelp Open Dataset imported as AI prototype corpus. Not Sevilla production data.",
            dry_run=False,
        )

        business_raw_asset_id = upsert_raw_asset(
            conn,
            schema,
            asset_code=f"{args.run_code}_businesses_jsonl",
            source_system_id=source_system_id,
            source_run_id=source_run_id,
            asset_name="Yelp AI food businesses JSONL",
            storage_path=str(businesses_path),
            file_format="jsonl",
            file_size_bytes=business_file_stats.size_bytes,
            record_count_estimated=business_file_stats.line_count,
            checksum_sha256=business_file_stats.checksum_sha256,
            notes="Business-level Yelp food corpus used to seed prototype places and place_source_ref rows.",
            dry_run=False,
        )

        review_raw_asset_id = upsert_raw_asset(
            conn,
            schema,
            asset_code=f"{args.run_code}_reviews_jsonl",
            source_system_id=source_system_id,
            source_run_id=source_run_id,
            asset_name="Yelp AI food reviews JSONL",
            storage_path=str(reviews_path),
            file_format="jsonl",
            file_size_bytes=review_file_stats.size_bytes,
            record_count_estimated=review_file_stats.line_count,
            checksum_sha256=review_file_stats.checksum_sha256,
            notes="Review-level Yelp food corpus used as operational/training text for the AI prototype.",
            dry_run=False,
        )

        business_to_place: dict[str, tuple[str, str]] = {}
        places_created = 0
        source_refs_created = 0
        source_refs_updated_or_reused = 0

        print("\nUpserting places and place_source_ref rows...")
        for business_id, business in tqdm(businesses_map.items(), desc="Upserting Yelp businesses"):
            if business_id in missing_coordinates:
                continue

            existing_ref = get_existing_place_ref(conn, schema, source_system_id, business_id)
            if existing_ref:
                place_id = str(existing_ref["place_id"])
            else:
                place_id = insert_place(conn, schema, business)
                places_created += 1

            place_source_ref_id, created_ref = upsert_place_source_ref(
                conn,
                schema,
                place_id=place_id,
                source_system_id=source_system_id,
                source_run_id=source_run_id,
                raw_asset_id=business_raw_asset_id,
                business=business,
            )

            if created_ref:
                source_refs_created += 1
            else:
                source_refs_updated_or_reused += 1

            business_to_place[business_id] = (place_id, place_source_ref_id)

        reviews_upserted = 0
        reviews_skipped_required = 0
        reviews_skipped_mapping = 0
        reviews_seen_second_pass = 0

        print("\nUpserting reviews...")
        for review in iter_jsonl(reviews_path, desc="Upserting Yelp reviews"):
            if args.max_reviews is not None and reviews_seen_second_pass >= args.max_reviews:
                break

            reviews_seen_second_pass += 1
            source_review_id = normalize_space(review.get("source_review_id"))
            source_business_id = normalize_space(review.get("source_business_id"))
            review_text = normalize_space(review.get("review_text_raw"))

            if not source_review_id or not source_business_id or not review_text:
                reviews_skipped_required += 1
                continue

            mapping = business_to_place.get(source_business_id)
            if mapping is None:
                reviews_skipped_mapping += 1
                continue

            place_id, place_source_ref_id = mapping

            upsert_review(
                conn,
                schema,
                place_id=place_id,
                place_source_ref_id=place_source_ref_id,
                source_system_id=source_system_id,
                source_run_id=source_run_id,
                raw_asset_id=review_raw_asset_id,
                review=review,
            )
            reviews_upserted += 1

        stats = LoadStats(
            source_system_code=args.source_code,
            run_code=args.run_code,
            businesses_seen_in_reviews=len(referenced_business_ids),
            businesses_loaded_from_file=len(businesses_map),
            businesses_missing_from_business_file=len(missing_business_ids),
            businesses_skipped_missing_coordinates=len(missing_coordinates),
            places_created=places_created,
            place_source_refs_created=source_refs_created,
            place_source_refs_updated_or_reused=source_refs_updated_or_reused,
            reviews_seen=reviews_seen_second_pass,
            reviews_skipped_missing_required_fields=reviews_skipped_required,
            reviews_skipped_missing_place_mapping=reviews_skipped_mapping,
            reviews_upserted=reviews_upserted,
            dry_run=False,
        )

        finalize_source_run(conn, schema, source_run_id, stats, started_at)

    print("\nLoad completed")
    print("--------------")
    print(json.dumps(asdict(stats), indent=2, ensure_ascii=False))
    return stats


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Load Yelp AI prototype businesses and reviews into Hidden Gems core tables."
    )

    parser.add_argument(
        "--businesses-path",
        required=True,
        help="Path to food_businesses.jsonl with business metadata and coordinates.",
    )
    parser.add_argument(
        "--reviews-path",
        required=True,
        help="Path to food_reviews.jsonl with one row per review.",
    )
    parser.add_argument(
        "--schema",
        default=DEFAULT_SCHEMA,
        help="PostgreSQL schema. Default: hidden_gems.",
    )
    parser.add_argument(
        "--source-code",
        default=DEFAULT_SOURCE_CODE,
        help="Source system code. Default: yelp_open_dataset.",
    )
    parser.add_argument(
        "--run-code",
        default=DEFAULT_RUN_CODE,
        help="source_run.run_code to create/update for this import.",
    )
    parser.add_argument(
        "--load-all-businesses",
        action="store_true",
        help="Load all businesses from businesses file. By default only businesses referenced by reviews are loaded.",
    )
    parser.add_argument(
        "--max-businesses",
        type=int,
        default=None,
        help="Optional limit for business rows read from businesses file, useful for tests.",
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=None,
        help="Optional limit for review rows read/upserted, useful for tests.",
    )
    parser.add_argument(
        "--skip-checksum",
        action="store_true",
        help="Skip SHA-256 file checksum calculation for faster execution.",
    )
    parser.add_argument(
        "--skip-line-count",
        action="store_true",
        help="Skip line counting for faster execution.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if missing businesses, missing coordinates or invalid reviews are detected.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print summary without writing to the database.",
    )

    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        load_yelp_core(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
