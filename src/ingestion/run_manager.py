from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


@dataclass(slots=True)
class RunContext:
    source_run_id: str
    source_system_id: str
    source_code: str
    run_code: str


class RunManager:
    def __init__(self) -> None:
        self.logger = logger

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _build_run_code(source_code: str) -> str:
        timestamp = RunManager._utc_now().strftime("%Y%m%dT%H%M%SZ")
        token = uuid.uuid4().hex[:8]
        return f"{source_code}_{timestamp}_{token}"

    def _get_source_system(self, source_code: str) -> dict[str, Any]:
        query = text(
            """
            SELECT source_system_id, source_code, source_name
            FROM hidden_gems.source_system
            WHERE source_code = :source_code
              AND is_active = TRUE
            LIMIT 1
            """
        )

        with engine.connect() as connection:
            result = connection.execute(query, {"source_code": source_code})
            row = result.mappings().first()

        if row is None:
            raise ValueError(
                f"No existe una fuente activa en hidden_gems.source_system "
                f"con source_code='{source_code}'."
            )

        return dict(row)

    def start_run(
        self,
        *,
        source_code: str,
        run_type: str = "incremental",
        trigger_type: str = "cli",
        request_summary: dict[str, Any] | None = None,
        notes: str | None = None,
        parent_run_id: str | None = None,
        config_snapshot_hash: str | None = None,
    ) -> RunContext:
        source_system = self._get_source_system(source_code)
        run_code = self._build_run_code(source_code)

        insert_sql = text(
            """
            INSERT INTO hidden_gems.source_run (
                run_code,
                source_system_id,
                run_type,
                trigger_type,
                status,
                started_at,
                config_snapshot_hash,
                request_summary,
                notes,
                parent_run_id
            )
            VALUES (
                :run_code,
                :source_system_id,
                :run_type,
                :trigger_type,
                'running',
                NOW(),
                :config_snapshot_hash,
                CAST(:request_summary AS jsonb),
                :notes,
                :parent_run_id
            )
            RETURNING source_run_id
            """
        )

        params = {
            "run_code": run_code,
            "source_system_id": source_system["source_system_id"],
            "run_type": run_type,
            "trigger_type": trigger_type,
            "config_snapshot_hash": config_snapshot_hash,
            "request_summary": (
                json.dumps(request_summary, ensure_ascii=False)
                if request_summary is not None
                else None
            ),
            "notes": notes,
            "parent_run_id": parent_run_id,
        }

        with engine.begin() as connection:
            result = connection.execute(insert_sql, params)
            source_run_id = str(result.scalar_one())

        self.logger.info(
            "Run iniciado | source_code=%s | run_code=%s | source_run_id=%s",
            source_code,
            run_code,
            source_run_id,
        )

        return RunContext(
            source_run_id=source_run_id,
            source_system_id=str(source_system["source_system_id"]),
            source_code=source_system["source_code"],
            run_code=run_code,
        )

    def complete_run(
        self,
        run_context: RunContext,
        *,
        records_extracted_count: int = 0,
        records_staged_count: int = 0,
        records_rejected_count: int = 0,
        error_count: int = 0,
        warning_count: int = 0,
        notes: str | None = None,
    ) -> None:
        final_status = (
            "completed_with_warnings" if warning_count > 0 else "completed"
        )

        update_sql = text(
            """
            UPDATE hidden_gems.source_run
            SET
                status = :status,
                finished_at = NOW(),
                duration_seconds = CASE
                    WHEN started_at IS NULL THEN NULL
                    ELSE GREATEST(
                        0,
                        FLOOR(EXTRACT(EPOCH FROM (NOW() - started_at)))::INTEGER
                    )
                END,
                records_extracted_count = :records_extracted_count,
                records_staged_count = :records_staged_count,
                records_rejected_count = :records_rejected_count,
                error_count = :error_count,
                warning_count = :warning_count,
                notes = COALESCE(:notes, notes)
            WHERE source_run_id = :source_run_id
            """
        )

        params = {
            "status": final_status,
            "records_extracted_count": max(0, records_extracted_count),
            "records_staged_count": max(0, records_staged_count),
            "records_rejected_count": max(0, records_rejected_count),
            "error_count": max(0, error_count),
            "warning_count": max(0, warning_count),
            "notes": notes,
            "source_run_id": run_context.source_run_id,
        }

        with engine.begin() as connection:
            connection.execute(update_sql, params)

        self.logger.info(
            "Run completado | run_code=%s | status=%s",
            run_context.run_code,
            final_status,
        )

    def fail_run(
        self,
        run_context: RunContext,
        *,
        error_message: str,
        warning_count: int = 0,
    ) -> None:
        update_sql = text(
            """
            UPDATE hidden_gems.source_run
            SET
                status = 'failed',
                finished_at = NOW(),
                duration_seconds = CASE
                    WHEN started_at IS NULL THEN NULL
                    ELSE GREATEST(
                        0,
                        FLOOR(EXTRACT(EPOCH FROM (NOW() - started_at)))::INTEGER
                    )
                END,
                error_count = GREATEST(error_count, 1),
                warning_count = :warning_count,
                notes = :notes
            WHERE source_run_id = :source_run_id
            """
        )

        params = {
            "warning_count": max(0, warning_count),
            "notes": error_message,
            "source_run_id": run_context.source_run_id,
        }

        with engine.begin() as connection:
            connection.execute(update_sql, params)

        self.logger.error(
            "Run fallido | run_code=%s | error=%s",
            run_context.run_code,
            error_message,
        )

    def increment_raw_asset_count(self, run_context: RunContext, increment: int = 1) -> None:
        update_sql = text(
            """
            UPDATE hidden_gems.source_run
            SET raw_asset_count = raw_asset_count + :increment
            WHERE source_run_id = :source_run_id
            """
        )

        with engine.begin() as connection:
            connection.execute(
                update_sql,
                {
                    "increment": max(1, increment),
                    "source_run_id": run_context.source_run_id,
                },
            )