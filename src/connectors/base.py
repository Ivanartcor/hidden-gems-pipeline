from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.config.settings import settings
from src.ingestion.raw_storage import RawStorage
from src.ingestion.run_manager import RunContext, RunManager
from src.utils.logging_config import setup_logger


class BaseConnector(ABC):
    source_code: str = ""

    def __init__(
        self,
        *,
        run_manager: RunManager | None = None,
        raw_storage: RawStorage | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        if not self.source_code:
            raise ValueError(
                "Cada conector debe definir un source_code de clase."
            )

        self.settings = settings
        self.run_manager = run_manager or RunManager()
        self.raw_storage = raw_storage or RawStorage()
        self.timeout_seconds = timeout_seconds or settings.request_timeout_seconds
        self.logger = setup_logger(f"connector.{self.source_code}")

    def build_default_headers(self) -> dict[str, str]:
        return {
            "User-Agent": f"{self.settings.app_name}/{self.settings.app_env}",
            "Accept": "application/json, text/plain, */*",
        }

    def build_request_summary(self, **kwargs: Any) -> dict[str, Any]:
        return {key: value for key, value in kwargs.items() if value is not None}

    def build_request_signature(self, payload: dict[str, Any] | None = None) -> str | None:
        if not payload:
            return None

        serialized = json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")

        return hashlib.sha256(serialized).hexdigest()

    def infer_record_count(self, payload: Any) -> int | None:
        if isinstance(payload, list):
            return len(payload)

        if isinstance(payload, dict):
            candidate_keys = ("elements", "results", "features", "items", "businesses")
            for key in candidate_keys:
                value = payload.get(key)
                if isinstance(value, list):
                    return len(value)

        return None

    def get_client(self) -> httpx.Client:
        return httpx.Client(
            timeout=self.timeout_seconds,
            headers=self.build_default_headers(),
            follow_redirects=True,
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: Any = None,
        json_body: Any = None,
    ) -> httpx.Response:
        merged_headers = self.build_default_headers()
        if headers:
            merged_headers.update(headers)

        self.logger.info(
            "HTTP request | source=%s | method=%s | url=%s",
            self.source_code,
            method.upper(),
            url,
        )

        with httpx.Client(
            timeout=self.timeout_seconds,
            headers=merged_headers,
            follow_redirects=True,
        ) as client:
            response = client.request(
                method=method,
                url=url,
                params=params,
                data=data,
                json=json_body,
            )
            response.raise_for_status()
            return response

    def request_json(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        data: Any = None,
        json_body: Any = None,
    ) -> Any:
        response = self.request(
            method=method,
            url=url,
            params=params,
            headers=headers,
            data=data,
            json_body=json_body,
        )
        return response.json()

    def start_run(
        self,
        *,
        run_type: str = "incremental",
        trigger_type: str = "cli",
        request_summary: dict[str, Any] | None = None,
        notes: str | None = None,
        parent_run_id: str | None = None,
        config_snapshot_hash: str | None = None,
    ) -> RunContext:
        return self.run_manager.start_run(
            source_code=self.source_code,
            run_type=run_type,
            trigger_type=trigger_type,
            request_summary=request_summary,
            notes=notes,
            parent_run_id=parent_run_id,
            config_snapshot_hash=config_snapshot_hash,
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
        self.run_manager.complete_run(
            run_context=run_context,
            records_extracted_count=records_extracted_count,
            records_staged_count=records_staged_count,
            records_rejected_count=records_rejected_count,
            error_count=error_count,
            warning_count=warning_count,
            notes=notes,
        )

    def fail_run(
        self,
        run_context: RunContext,
        *,
        error_message: str,
        warning_count: int = 0,
    ) -> None:
        self.run_manager.fail_run(
            run_context=run_context,
            error_message=error_message,
            warning_count=warning_count,
        )

    def save_raw_json(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        payload: Any,
        query_name: str | None = None,
        request_signature_hash: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.raw_storage.save_json(
            run_context=run_context,
            asset_name=asset_name,
            payload=payload,
            asset_type="api_response",
            query_name=query_name,
            request_signature_hash=request_signature_hash,
            notes=notes,
        )

    def save_raw_bytes(
        self,
        *,
        run_context: RunContext,
        asset_name: str,
        content: bytes,
        file_format: str,
        asset_type: str = "raw_export",
        mime_type: str | None = None,
        query_name: str | None = None,
        request_signature_hash: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        return self.raw_storage.save_bytes(
            run_context=run_context,
            asset_name=asset_name,
            content=content,
            file_format=file_format,
            asset_type=asset_type,
            mime_type=mime_type,
            query_name=query_name,
            request_signature_hash=request_signature_hash,
            notes=notes,
        )

    @abstractmethod
    def run(self, **kwargs: Any) -> dict[str, Any]:
        """
        Ejecuta la lógica completa del conector:
        iniciar run, obtener datos, guardar raw y cerrar ejecución.
        """
        raise NotImplementedError