from __future__ import annotations

from typing import Any

import httpx

from src.connectors.base import BaseConnector


class GooglePlacesConnector(BaseConnector):
    source_code = "google_places"

    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    DEFAULT_FIELD_MASK = [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.location",
        "places.types",
        "places.businessStatus",
        "places.googleMapsUri",
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.base_url = self.settings.google_places_base_url.rstrip("/")

        if not self.settings.google_maps_api_key:
            raise ValueError(
                "No se ha definido GOOGLE_MAPS_API_KEY en el entorno."
            )

    @staticmethod
    def _clean_query_name(query_name: str) -> str:
        return query_name.strip().lower().replace(" ", "_")

    @classmethod
    def build_field_mask(cls, field_mask: list[str] | None = None) -> str:
        fields = field_mask or cls.DEFAULT_FIELD_MASK
        return ",".join(fields)

    @staticmethod
    def _validate_text_search_payload(payload: Any) -> list[str]:
        warnings: list[str] = []

        if not isinstance(payload, dict):
            raise ValueError("La respuesta de Google Places no es un objeto JSON válido.")

        places = payload.get("places")

        if places is None:
            warnings.append("La respuesta no contiene la clave 'places'.")
            return warnings

        if not isinstance(places, list):
            raise ValueError("La clave 'places' no contiene una lista válida.")

        return warnings

    @staticmethod
    def _summarize_text_search_payload(payload: dict[str, Any]) -> dict[str, Any]:
        places = payload.get("places", [])

        business_status_counts: dict[str, int] = {}
        type_counts: dict[str, int] = {}

        for place in places:
            if not isinstance(place, dict):
                continue

            status = place.get("businessStatus")
            if isinstance(status, str):
                business_status_counts[status] = business_status_counts.get(status, 0) + 1

            types = place.get("types")
            if isinstance(types, list):
                for place_type in types:
                    if isinstance(place_type, str):
                        type_counts[place_type] = type_counts.get(place_type, 0) + 1

        top_types = sorted(
            type_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:20]

        return {
            "place_count": len(places) if isinstance(places, list) else 0,
            "business_status_counts": business_status_counts,
            "top_types": dict(top_types),
        }

    def _request_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        json_body: dict[str, Any],
        clean_query_name: str,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                payload = self.request_json(
                    method="POST",
                    url=endpoint,
                    headers=headers,
                    json_body=json_body,
                )
                return payload

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status_code = exc.response.status_code

                if status_code not in self.RETRYABLE_STATUS_CODES or attempt == max_attempts:
                    raise

                self.logger.warning(
                    "Google Places devolvió status=%s | query_name=%s | intento=%s/%s",
                    status_code,
                    clean_query_name,
                    attempt,
                    max_attempts,
                )

            except httpx.RequestError as exc:
                last_exception = exc

                if attempt == max_attempts:
                    raise

                self.logger.warning(
                    "Error de red en Google Places | query_name=%s | intento=%s/%s | error=%s",
                    clean_query_name,
                    attempt,
                    max_attempts,
                    exc,
                )

        if last_exception is not None:
            raise last_exception

        raise RuntimeError("Fallo inesperado en _request_with_retry.")

    def run_text_search(
        self,
        *,
        text_query: str,
        query_name: str,
        max_result_count: int = 3,
        language_code: str = "es",
        region_code: str = "ES",
        field_mask: list[str] | None = None,
        trigger_type: str = "cli",
        run_type: str = "incremental",
    ) -> dict[str, Any]:
        clean_query_name = self._clean_query_name(query_name)
        endpoint = f"{self.base_url}/places:searchText"
        final_field_mask = self.build_field_mask(field_mask)

        if max_result_count < 1 or max_result_count > 20:
            raise ValueError("max_result_count debe estar entre 1 y 20 para esta fase inicial.")

        json_body = {
            "textQuery": text_query,
            "maxResultCount": max_result_count,
            "languageCode": language_code,
            "regionCode": region_code,
        }

        request_summary = self.build_request_summary(
            query_name=clean_query_name,
            endpoint=endpoint,
            method="POST",
            text_query=text_query,
            max_result_count=max_result_count,
            language_code=language_code,
            region_code=region_code,
            field_mask=final_field_mask,
        )
        request_signature_hash = self.build_request_signature(request_summary)

        run_context = self.start_run(
            run_type=run_type,
            trigger_type=trigger_type,
            request_summary=request_summary,
            notes=f"Consulta Google Places Text Search iniciada para query_name={clean_query_name}.",
        )

        try:
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.settings.google_maps_api_key,
                "X-Goog-FieldMask": final_field_mask,
            }

            payload = self._request_with_retry(
                endpoint=endpoint,
                headers=headers,
                json_body=json_body,
                clean_query_name=clean_query_name,
            )

            warnings = self._validate_text_search_payload(payload)
            summary = self._summarize_text_search_payload(payload)

            raw_asset = self.save_raw_json(
                run_context=run_context,
                asset_name=f"google_places_text_search_{clean_query_name}",
                payload=payload,
                query_name=clean_query_name,
                request_signature_hash=request_signature_hash,
                notes=f"Respuesta raw de Google Places Text Search para query_name={clean_query_name}.",
            )

            self.complete_run(
                run_context,
                records_extracted_count=summary["place_count"],
                records_staged_count=0,
                records_rejected_count=0,
                warning_count=len(warnings),
                notes=f"Consulta Google Places Text Search completada para query_name={clean_query_name}.",
            )

            self.logger.info(
                "Google Places Text Search ejecutado | query_name=%s | place_count=%s",
                clean_query_name,
                summary["place_count"],
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
                    f"Error en Google Places Text Search para query_name={clean_query_name}: {exc}"
                ),
            )
            raise

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.run_text_search(**kwargs)