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

    DEFAULT_DETAILS_FIELD_MASK = [
        "id",
        "displayName",
        "reviews",
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
    

    @staticmethod
    def _validate_place_details_payload(payload: Any) -> list[str]:
        warnings: list[str] = []

        if not isinstance(payload, dict):
            raise ValueError("La respuesta de Google Places Details no es un objeto JSON válido.")

        if not payload.get("id"):
            warnings.append("La respuesta no contiene 'id'.")

        reviews = payload.get("reviews")
        if reviews is not None and not isinstance(reviews, list):
            raise ValueError("La clave 'reviews' no contiene una lista válida.")

        return warnings

    @staticmethod
    def _summarize_place_details_payload(payload: dict[str, Any]) -> dict[str, Any]:
        reviews = payload.get("reviews", [])

        if not isinstance(reviews, list):
            reviews = []

        reviews_with_text = 0
        reviews_with_rating = 0
        rating_counts: dict[str, int] = {}
        language_counts: dict[str, int] = {}

        for review in reviews:
            if not isinstance(review, dict):
                continue

            rating = review.get("rating")
            if rating is not None:
                reviews_with_rating += 1
                rating_key = str(rating)
                rating_counts[rating_key] = rating_counts.get(rating_key, 0) + 1

            text_obj = review.get("text")
            if isinstance(text_obj, dict) and str(text_obj.get("text") or "").strip():
                reviews_with_text += 1
                language_code = text_obj.get("languageCode")
                if isinstance(language_code, str):
                    language_counts[language_code] = language_counts.get(language_code, 0) + 1

        return {
            "google_place_id": payload.get("id"),
            "display_name": (
                payload.get("displayName", {}).get("text")
                if isinstance(payload.get("displayName"), dict)
                else None
            ),
            "review_count": len(reviews),
            "reviews_with_text": reviews_with_text,
            "reviews_with_rating": reviews_with_rating,
            "rating_counts": rating_counts,
            "language_counts": language_counts,
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

    def _request_get_with_retry(
        self,
        *,
        endpoint: str,
        headers: dict[str, str],
        params: dict[str, Any] | None,
        clean_query_name: str,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        last_exception: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                payload = self.request_json(
                    method="GET",
                    url=endpoint,
                    headers=headers,
                    params=params,
                )
                return payload

            except httpx.HTTPStatusError as exc:
                last_exception = exc
                status_code = exc.response.status_code

                if status_code not in self.RETRYABLE_STATUS_CODES or attempt == max_attempts:
                    raise

                self.logger.warning(
                    "Google Places Details devolvió status=%s | query_name=%s | intento=%s/%s",
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
                    "Error de red en Google Places Details | query_name=%s | intento=%s/%s | error=%s",
                    clean_query_name,
                    attempt,
                    max_attempts,
                    exc,
                )

        if last_exception is not None:
            raise last_exception

        raise RuntimeError("Fallo inesperado en _request_get_with_retry.")



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

    def run_place_details(
        self,
        *,
        google_place_id: str,
        query_name: str,
        language_code: str = "es",
        region_code: str = "ES",
        field_mask: list[str] | None = None,
        trigger_type: str = "cli",
        run_type: str = "incremental",
        place_id: str | None = None,
        place_source_ref_id: str | None = None,
    ) -> dict[str, Any]:
        clean_query_name = self._clean_query_name(query_name)
        clean_google_place_id = google_place_id.strip()

        if clean_google_place_id.startswith("places/"):
            clean_google_place_id = clean_google_place_id.removeprefix("places/")

        if not clean_google_place_id:
            raise ValueError("google_place_id no puede estar vacío.")

        endpoint = f"{self.base_url}/places/{clean_google_place_id}"
        final_field_mask = self.build_field_mask(field_mask or self.DEFAULT_DETAILS_FIELD_MASK)

        request_params = {
            "languageCode": language_code,
            "regionCode": region_code,
        }

        request_summary = self.build_request_summary(
            query_name=clean_query_name,
            endpoint=endpoint,
            method="GET",
            google_place_id=clean_google_place_id,
            place_id=place_id,
            place_source_ref_id=place_source_ref_id,
            language_code=language_code,
            region_code=region_code,
            field_mask=final_field_mask,
            purpose="place_details_reviews",
        )
        request_signature_hash = self.build_request_signature(request_summary)

        run_context = self.start_run(
            run_type=run_type,
            trigger_type=trigger_type,
            request_summary=request_summary,
            notes=(
                "Consulta Google Places Place Details iniciada "
                f"para query_name={clean_query_name}, google_place_id={clean_google_place_id}."
            ),
        )

        try:
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.settings.google_maps_api_key,
                "X-Goog-FieldMask": final_field_mask,
            }

            payload = self._request_get_with_retry(
                endpoint=endpoint,
                headers=headers,
                params=request_params,
                clean_query_name=clean_query_name,
            )

            warnings = self._validate_place_details_payload(payload)
            summary = self._summarize_place_details_payload(payload)

            raw_asset = self.save_raw_json(
                run_context=run_context,
                asset_name=f"google_places_details_{clean_query_name}",
                payload=payload,
                query_name=clean_query_name,
                request_signature_hash=request_signature_hash,
                notes=(
                    "Respuesta raw de Google Places Place Details "
                    f"para query_name={clean_query_name}, google_place_id={clean_google_place_id}."
                ),
            )

            self.complete_run(
                run_context,
                records_extracted_count=summary["review_count"],
                records_staged_count=0,
                records_rejected_count=0,
                warning_count=len(warnings),
                notes=(
                    "Consulta Google Places Place Details completada "
                    f"para query_name={clean_query_name}."
                ),
            )

            self.logger.info(
                "Google Places Place Details ejecutado | query_name=%s | google_place_id=%s | review_count=%s",
                clean_query_name,
                clean_google_place_id,
                summary["review_count"],
            )

            return {
                "source_code": self.source_code,
                "run_context": run_context,
                "raw_asset": raw_asset,
                "summary": summary,
                "warnings": warnings,
                "payload": payload,
                "place_id": place_id,
                "place_source_ref_id": place_source_ref_id,
                "google_place_id": clean_google_place_id,
            }

        except Exception as exc:
            self.fail_run(
                run_context,
                error_message=(
                    "Error en Google Places Place Details "
                    f"para query_name={clean_query_name}, google_place_id={clean_google_place_id}: {exc}"
                ),
            )
            raise

    def run(self, **kwargs: Any) -> dict[str, Any]:
        return self.run_text_search(**kwargs)