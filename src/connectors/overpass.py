from __future__ import annotations

import time
from typing import Any, Iterable

import httpx

from src.connectors.base import BaseConnector


class OverpassConnector(BaseConnector):
    source_code = "osm_overpass"

    RETRYABLE_STATUS_CODES = {429, 502, 503, 504}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = self.settings.overpass_base_url

    @staticmethod
    def _build_tag_filter(tags: dict[str, str | None] | None) -> str:
        if not tags:
            return ""

        parts: list[str] = []
        for key, value in tags.items():
            if value is None:
                parts.append(f'["{key}"]')
            else:
                parts.append(f'["{key}"="{value}"]')

        return "".join(parts)

    def build_bbox_query(
        self,
        *,
        south: float,
        west: float,
        north: float,
        east: float,
        tags: dict[str, str | None] | None = None,
        element_types: Iterable[str] = ("node", "way", "relation"),
        timeout_seconds: int = 90,
        out_mode: str = "center tags",
    ) -> str:
        tag_filter = self._build_tag_filter(tags)

        query_lines = [f"[out:json][timeout:{timeout_seconds}];", "("]
        for element_type in element_types:
            query_lines.append(
                f"  {element_type}{tag_filter}({south},{west},{north},{east});"
            )
        query_lines.append(");")
        query_lines.append(f"out {out_mode};")

        return "\n".join(query_lines)

    @staticmethod
    def _validate_payload(payload: Any) -> list[str]:
        warnings: list[str] = []

        if not isinstance(payload, dict):
            raise ValueError("La respuesta de Overpass no es un objeto JSON válido.")

        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise ValueError("La respuesta de Overpass no contiene una lista válida en 'elements'.")

        remark = payload.get("remark")
        if remark:
            warnings.append(f"Overpass remark: {remark}")

        return warnings

    @staticmethod
    def _summarize_payload(payload: dict[str, Any]) -> dict[str, Any]:
        elements = payload.get("elements", [])

        element_type_counts = {
            "node": 0,
            "way": 0,
            "relation": 0,
        }

        sample_tag_keys: set[str] = set()

        for element in elements:
            if not isinstance(element, dict):
                continue

            element_type = element.get("type")
            if element_type in element_type_counts:
                element_type_counts[element_type] += 1

            tags = element.get("tags")
            if isinstance(tags, dict):
                sample_tag_keys.update(tags.keys())

        return {
            "element_count": len(elements),
            "element_type_counts": element_type_counts,
            "sample_tag_keys": sorted(sample_tag_keys)[:30],
        }

    def _request_with_retry(
        self,
        *,
        overpass_query: str,
        clean_query_name: str,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                payload = self.request_json(
                    method="POST",
                    url=self.base_url,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"data": overpass_query},
                )
                return payload

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status_code = exc.response.status_code

                if status_code not in self.RETRYABLE_STATUS_CODES or attempt == max_attempts:
                    raise

                wait_seconds = 2 ** attempt
                self.logger.warning(
                    "Overpass devolvió status=%s | query_name=%s | intento=%s/%s | reintentando en %ss",
                    status_code,
                    clean_query_name,
                    attempt,
                    max_attempts,
                    wait_seconds,
                )
                time.sleep(wait_seconds)

            except httpx.RequestError as exc:
                last_exception = exc

                if attempt == max_attempts:
                    raise

                wait_seconds = 2 ** attempt
                self.logger.warning(
                    "Error de red en Overpass | query_name=%s | intento=%s/%s | reintentando en %ss | error=%s",
                    clean_query_name,
                    attempt,
                    max_attempts,
                    wait_seconds,
                    exc,
                )
                time.sleep(wait_seconds)

        if last_exception is not None:
            raise last_exception

        raise RuntimeError("Fallo inesperado en _request_with_retry.")

    def run(
        self,
        *,
        overpass_query: str,
        query_name: str,
        trigger_type: str = "cli",
        run_type: str = "full_refresh",
    ) -> dict[str, Any]:
        clean_query_name = query_name.strip().lower().replace(" ", "_")
        request_summary = self.build_request_summary(
            query_name=clean_query_name,
            endpoint=self.base_url,
            overpass_query=overpass_query,
        )
        request_signature_hash = self.build_request_signature(request_summary)

        run_context = self.start_run(
            run_type=run_type,
            trigger_type=trigger_type,
            request_summary=request_summary,
            notes=f"Consulta Overpass iniciada para query_name={clean_query_name}.",
        )

        try:
            payload = self._request_with_retry(
                overpass_query=overpass_query,
                clean_query_name=clean_query_name,
            )

            warnings = self._validate_payload(payload)
            summary = self._summarize_payload(payload)

            raw_asset = self.save_raw_json(
                run_context=run_context,
                asset_name=f"osm_overpass_{clean_query_name}",
                payload=payload,
                query_name=clean_query_name,
                request_signature_hash=request_signature_hash,
                notes=f"Respuesta raw de Overpass para query_name={clean_query_name}.",
            )

            self.complete_run(
                run_context,
                records_extracted_count=summary["element_count"],
                records_staged_count=0,
                records_rejected_count=0,
                warning_count=len(warnings),
                notes=f"Consulta Overpass completada para query_name={clean_query_name}.",
            )

            self.logger.info(
                "Overpass ejecutado | query_name=%s | element_count=%s",
                clean_query_name,
                summary["element_count"],
            )

            return {
                "source_code": self.source_code,
                "run_context": run_context,
                "raw_asset": raw_asset,
                "summary": summary,
                "warnings": warnings,
                "payload": payload,
            }

        except Exception as exc:
            self.fail_run(
                run_context,
                error_message=(
                    f"Error en consulta Overpass para query_name={clean_query_name}: {exc}"
                ),
            )
            raise