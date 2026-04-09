from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text

from src.config.settings import settings
from src.db.database import engine
from src.ingestion.run_manager import RunContext, RunManager
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


class RawStorage:
    def __init__(self, base_path: Path | None = None) -> None:
        settings.ensure_directories()
        self.base_path = base_path or settings.data_raw_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.run_manager = RunManager()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _slugify(value: str) -> str:
        value = value.strip().lower()
        value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
        value = re.sub(r"[-\s]+", "_", value)
        return value[:80] or "asset"

    @staticmethod
    def _build_asset_code(source_code: str) -> str:
        timestamp = RawStorage._utc_now().strftime("%Y%m%dT%H%M%SZ")
        token = uuid.uuid4().hex[:8]
        return f"{source_code}_asset_{timestamp}_{token}"

    def _build_relative_path(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        file_format: str,
    ) -> Path:
        safe_name = self._slugify(asset_name)
        safe_ext = file_format.lower().lstrip(".")
        timestamp = self._utc_now().strftime("%Y%m%dT%H%M%SZ")
        token = uuid.uuid4().hex[:8]

        dated_folder = self._utc_now().strftime("%Y/%m/%d")
        filename = f"{timestamp}_{safe_name}_{token}.{safe_ext}"

        return Path(run_context.source_code) / dated_folder / run_context.run_code / filename

    @staticmethod
    def _checksum_sha256(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _guess_mime_type(file_name: str) -> str | None:
        mime_type, _ = mimetypes.guess_type(file_name)
        return mime_type

    def save_bytes(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        content: bytes,
        file_format: str,
        asset_type: str = "api_response",
        compression_type: str | None = None,
        mime_type: str | None = None,
        query_name: str | None = None,
        request_signature_hash: str | None = None,
        content_created_at: datetime | None = None,
        retention_class: str = "long_term",
        record_count_estimated: int | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        relative_path = self._build_relative_path(
            run_context=run_context,
            asset_name=asset_name,
            file_format=file_format,
        )
        full_path = self.base_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(content)

        checksum_sha256 = self._checksum_sha256(content)
        file_size_bytes = len(content)
        asset_code = self._build_asset_code(run_context.source_code)

        final_mime_type = mime_type or self._guess_mime_type(full_path.name)

        insert_sql = text(
            """
            INSERT INTO hidden_gems.raw_asset (
                asset_code,
                source_system_id,
                source_run_id,
                asset_name,
                asset_type,
                storage_path,
                file_format,
                compression_type,
                mime_type,
                file_size_bytes,
                record_count_estimated,
                checksum_sha256,
                query_name,
                request_signature_hash,
                content_created_at,
                retention_class,
                notes
            )
            VALUES (
                :asset_code,
                :source_system_id,
                :source_run_id,
                :asset_name,
                :asset_type,
                :storage_path,
                :file_format,
                :compression_type,
                :mime_type,
                :file_size_bytes,
                :record_count_estimated,
                :checksum_sha256,
                :query_name,
                :request_signature_hash,
                :content_created_at,
                :retention_class,
                :notes
            )
            RETURNING raw_asset_id
            """
        )

        params = {
            "asset_code": asset_code,
            "source_system_id": run_context.source_system_id,
            "source_run_id": run_context.source_run_id,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "storage_path": relative_path.as_posix(),
            "file_format": file_format.lower().lstrip("."),
            "compression_type": compression_type,
            "mime_type": final_mime_type,
            "file_size_bytes": file_size_bytes,
            "record_count_estimated": record_count_estimated,
            "checksum_sha256": checksum_sha256,
            "query_name": query_name,
            "request_signature_hash": request_signature_hash,
            "content_created_at": content_created_at,
            "retention_class": retention_class,
            "notes": notes,
        }

        with engine.begin() as connection:
            result = connection.execute(insert_sql, params)
            raw_asset_id = str(result.scalar_one())

        self.run_manager.increment_raw_asset_count(run_context)

        self.logger.info(
            "Raw asset guardado | run_code=%s | raw_asset_id=%s | path=%s",
            run_context.run_code,
            raw_asset_id,
            relative_path.as_posix(),
        )

        return {
            "raw_asset_id": raw_asset_id,
            "asset_code": asset_code,
            "storage_path": relative_path.as_posix(),
            "checksum_sha256": checksum_sha256,
            "file_size_bytes": file_size_bytes,
        }

    def save_text(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        content: str,
        file_format: str = "txt",
        asset_type: str = "raw_export",
        compression_type: str | None = None,
        mime_type: str | None = "text/plain",
        query_name: str | None = None,
        request_signature_hash: str | None = None,
        content_created_at: datetime | None = None,
        retention_class: str = "long_term",
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.save_bytes(
            run_context=run_context,
            asset_name=asset_name,
            content=content.encode("utf-8"),
            file_format=file_format,
            asset_type=asset_type,
            compression_type=compression_type,
            mime_type=mime_type,
            query_name=query_name,
            request_signature_hash=request_signature_hash,
            content_created_at=content_created_at,
            retention_class=retention_class,
            record_count_estimated=None,
            notes=notes,
        )

    def save_json(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        payload: Any,
        asset_type: str = "api_response",
        query_name: str | None = None,
        request_signature_hash: str | None = None,
        content_created_at: datetime | None = None,
        retention_class: str = "long_term",
        notes: str | None = None,
    ) -> dict[str, Any]:
        json_text = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

        record_count_estimated = len(payload) if isinstance(payload, list) else None

        return self.save_bytes(
            run_context=run_context,
            asset_name=asset_name,
            content=json_text.encode("utf-8"),
            file_format="json",
            asset_type=asset_type,
            compression_type=None,
            mime_type="application/json",
            query_name=query_name,
            request_signature_hash=request_signature_hash,
            content_created_at=content_created_at,
            retention_class=retention_class,
            record_count_estimated=record_count_estimated,
            notes=notes,
        )