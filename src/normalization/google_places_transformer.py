from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from src.normalization.place_candidate import (
    CandidateAddressInfo,
    CandidateBusinessInfo,
    CandidateClassificationInfo,
    CandidateLocationInfo,
    CandidateNameInfo,
    CandidateProvenance,
    CandidateQualitySignals,
    NormalizedPlaceCandidate,
)


@dataclass(slots=True)
class GooglePlacesTransformationIssue:
    issue_code: str
    severity: str
    message: str
    place_index: int | None = None
    source_entity_type: str | None = None
    source_record_id: str | None = None
    field_name: str | None = None
    received_value: Any | None = None


@dataclass(slots=True)
class GooglePlacesTransformationResult:
    payload_metadata: dict[str, Any]
    candidates: list[NormalizedPlaceCandidate]
    issues: list[GooglePlacesTransformationIssue]
    total_places: int
    accepted_count: int
    needs_review_count: int
    rejected_count: int
    skipped_count: int


class GooglePlacesTransformer:
    """
    Transforma el raw JSON de Google Places Text Search en una colección
    de NormalizedPlaceCandidate sin escribir todavía en base de datos.
    """

    FOOD_TYPE_PRIORITY = [
        "restaurant",
        "spanish_restaurant",
        "tapas_restaurant",
        "mediterranean_restaurant",
        "fine_dining_restaurant",
        "bar",
        "wine_bar",
        "cocktail_bar",
        "cafe",
        "coffee_shop",
        "brunch_restaurant",
        "breakfast_restaurant",
        "fast_food_restaurant",
        "meal_takeaway",
        "food_delivery",
        "bakery",
        "ice_cream_shop",
        "dessert_shop",
    ]

    GENERIC_TYPES_TO_DEPRIORITIZE = {
        "food",
        "point_of_interest",
        "establishment",
        "service",
        "event_venue",
    }

    def _build_issue(
        self,
        *,
        issue_code: str,
        severity: str,
        message: str,
        place_index: int | None = None,
        source_entity_type: str | None = None,
        source_record_id: str | None = None,
        field_name: str | None = None,
        received_value: Any | None = None,
    ) -> GooglePlacesTransformationIssue:
        return GooglePlacesTransformationIssue(
            issue_code=issue_code,
            severity=severity,
            message=message,
            place_index=place_index,
            source_entity_type=source_entity_type,
            source_record_id=source_record_id,
            field_name=field_name,
            received_value=received_value,
        )

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        return text or None

    @staticmethod
    def _normalize_name(value: str | None) -> str | None:
        if not value:
            return None

        text = value.strip()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        text = text.replace("_", " ")
        text = re.sub(r"\s+", " ", text).strip()

        return text or None

    @staticmethod
    def _build_display_name(value: str | None) -> str | None:
        if not value:
            return None

        return re.sub(r"\s+", " ", value.strip()) or None

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    @staticmethod
    def _dedupe_preserve_order(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            clean_value = value.strip()
            if clean_value and clean_value not in seen:
                seen.add(clean_value)
                result.append(clean_value)

        return result

    def _extract_display_name(self, place: dict[str, Any]) -> str | None:
        display_name = place.get("displayName")

        if isinstance(display_name, dict):
            return self._clean_text(display_name.get("text"))

        return None

    def _extract_location(
        self,
        place: dict[str, Any],
    ) -> tuple[float | None, float | None]:
        location = place.get("location")

        if not isinstance(location, dict):
            return None, None

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        if latitude is None or longitude is None:
            return None, None

        return float(latitude), float(longitude)

    @staticmethod
    def _build_point_geojson(
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, Any] | None:
        if latitude is None or longitude is None:
            return None

        return {
            "type": "Point",
            "coordinates": [longitude, latitude],
        }

    def _extract_types(self, place: dict[str, Any]) -> list[str]:
        types = place.get("types")

        if not isinstance(types, list):
            return []

        return self._dedupe_preserve_order(
            [str(place_type).strip() for place_type in types if str(place_type).strip()]
        )

    def _resolve_primary_category(self, types: list[str]) -> str | None:
        if not types:
            return None

        for priority_type in self.FOOD_TYPE_PRIORITY:
            if priority_type in types:
                return priority_type

        for place_type in types:
            if place_type not in self.GENERIC_TYPES_TO_DEPRIORITIZE:
                return place_type

        return types[0]

    def _build_food_style_raw(self, types: list[str]) -> list[str]:
        food_styles: list[str] = []

        for place_type in types:
            if (
                place_type in self.FOOD_TYPE_PRIORITY
                or place_type.endswith("_restaurant")
                or place_type.endswith("_bar")
                or place_type in {"bar", "cafe", "bakery"}
            ):
                food_styles.append(place_type)

        return self._dedupe_preserve_order(food_styles)

    def _calculate_completeness_score(
        self,
        *,
        has_name: bool,
        has_coordinates: bool,
        has_category: bool,
        has_address: bool,
        has_contact_info: bool,
        has_google_maps_uri: bool,
        has_business_status: bool,
    ) -> float:
        score = 0.0
        score += 0.30 if has_name else 0.0
        score += 0.25 if has_coordinates else 0.0
        score += 0.15 if has_category else 0.0
        score += 0.10 if has_address else 0.0
        score += 0.05 if has_contact_info else 0.0
        score += 0.05 if has_google_maps_uri else 0.0
        score += 0.10 if has_business_status else 0.0
        return round(score, 4)

    def _assign_candidate_status(
        self,
        candidate: NormalizedPlaceCandidate,
    ) -> NormalizedPlaceCandidate:
        rejection_reasons: list[str] = []
        warning_messages: list[str] = []

        if not candidate.provenance.source_record_id:
            rejection_reasons.append("missing_source_record_id")

        if not candidate.quality.has_coordinates:
            rejection_reasons.append("missing_coordinates")

        if not candidate.quality.has_category:
            rejection_reasons.append("missing_category")

        if not candidate.quality.has_name:
            warning_messages.append("missing_name")

        if not candidate.quality.has_address:
            warning_messages.append("missing_address")

        source_status = candidate.provenance.source_status_raw

        if source_status and source_status != "OPERATIONAL":
            warning_messages.append(f"non_operational_status:{source_status}")

        candidate.quality.completeness_score = self._calculate_completeness_score(
            has_name=candidate.quality.has_name,
            has_coordinates=candidate.quality.has_coordinates,
            has_category=candidate.quality.has_category,
            has_address=candidate.quality.has_address,
            has_contact_info=candidate.quality.has_contact_info,
            has_google_maps_uri=bool(candidate.provenance.source_url),
            has_business_status=bool(candidate.provenance.source_status_raw),
        )

        candidate.quality.rejection_reasons = rejection_reasons
        candidate.quality.warning_messages = warning_messages

        if rejection_reasons:
            candidate.quality.candidate_status = "rejected"
            candidate.quality.requires_manual_review = False
        elif source_status and source_status != "OPERATIONAL":
            candidate.quality.candidate_status = "needs_review"
            candidate.quality.requires_manual_review = True
        elif not candidate.quality.has_name:
            candidate.quality.candidate_status = "needs_review"
            candidate.quality.requires_manual_review = True
        else:
            candidate.quality.candidate_status = "accepted"
            candidate.quality.requires_manual_review = False

        return candidate

    def transform_payload(
        self,
        payload: dict[str, Any],
        *,
        source_run_id: str | None = None,
        raw_asset_id: str | None = None,
    ) -> GooglePlacesTransformationResult:
        if not isinstance(payload, dict):
            raise ValueError("El payload debe ser un dict.")

        places = payload.get("places")

        if places is None:
            places = []

        if not isinstance(places, list):
            raise ValueError("El payload no contiene una lista válida en 'places'.")

        issues: list[GooglePlacesTransformationIssue] = []
        candidates: list[NormalizedPlaceCandidate] = []

        accepted_count = 0
        needs_review_count = 0
        rejected_count = 0
        skipped_count = 0

        payload_metadata = {
            "source": "google_places",
            "response_type": "text_search",
            "place_count": len(places),
            "has_next_page_token": bool(payload.get("nextPageToken")),
        }

        for place_index, place in enumerate(places, start=1):
            if not isinstance(place, dict):
                issues.append(
                    self._build_issue(
                        issue_code="invalid_place_structure",
                        severity="error",
                        message="El elemento de places no tiene una estructura válida.",
                        place_index=place_index,
                        received_value=place,
                    )
                )
                skipped_count += 1
                continue

            source_entity_type = "google_place"
            source_record_id = self._clean_text(place.get("id"))
            display_name_raw = self._extract_display_name(place)
            formatted_address = self._clean_text(place.get("formattedAddress"))
            latitude, longitude = self._extract_location(place)
            types = self._extract_types(place)
            primary_category = self._resolve_primary_category(types)
            business_status = self._clean_text(place.get("businessStatus"))
            google_maps_uri = self._clean_text(place.get("googleMapsUri"))

            if not source_record_id:
                issues.append(
                    self._build_issue(
                        issue_code="missing_source_record_id",
                        severity="error",
                        message="El place de Google no contiene id utilizable.",
                        place_index=place_index,
                        source_entity_type=source_entity_type,
                        field_name="id",
                        received_value=place.get("id"),
                    )
                )

            if latitude is None or longitude is None:
                issues.append(
                    self._build_issue(
                        issue_code="missing_coordinates",
                        severity="warning",
                        message="El place de Google no contiene coordenadas utilizables.",
                        place_index=place_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        field_name="location",
                        received_value=place.get("location"),
                    )
                )

            if not display_name_raw:
                issues.append(
                    self._build_issue(
                        issue_code="missing_name",
                        severity="warning",
                        message="El place de Google no contiene displayName.text.",
                        place_index=place_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        field_name="displayName",
                        received_value=place.get("displayName"),
                    )
                )

            if not types:
                issues.append(
                    self._build_issue(
                        issue_code="missing_types",
                        severity="warning",
                        message="El place de Google no contiene types.",
                        place_index=place_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        field_name="types",
                        received_value=place.get("types"),
                    )
                )

            provenance = CandidateProvenance(
                source_system_code="google_places",
                source_entity_type=source_entity_type,
                source_record_id=source_record_id or f"missing_google_id_{place_index}",
                source_run_id=str(source_run_id) if source_run_id is not None else None,
                raw_asset_id=str(raw_asset_id) if raw_asset_id is not None else None,
                source_url=google_maps_uri,
                source_status_raw=business_status,
                source_payload_hash=self._hash_payload(place),
                source_created_at_raw=None,
                source_updated_at_raw=None,
            )

            names = CandidateNameInfo(
                source_name_raw=display_name_raw,
                source_display_name_raw=display_name_raw,
                normalized_name=self._normalize_name(display_name_raw),
                display_name=self._build_display_name(display_name_raw),
            )

            address = CandidateAddressInfo(
                source_address_raw=formatted_address,
                source_address_normalized=self._normalize_name(formatted_address),
                addr_full_raw=formatted_address,
                country="ES",
            )

            location = CandidateLocationInfo(
                latitude=latitude,
                longitude=longitude,
                geom_point_geojson=self._build_point_geojson(latitude, longitude),
                geo_precision="point" if latitude is not None and longitude is not None else None,
                geo_source_field="location",
            )

            classification = CandidateClassificationInfo(
                source_primary_category_raw=primary_category,
                source_categories_raw=types,
                amenity_raw=primary_category,
                cuisine_raw=[],
                food_style_raw=self._build_food_style_raw(types),
            )

            business = CandidateBusinessInfo(
                phone_raw=None,
                phone_normalized=None,
                website_url=None,
                source_rating=None,
                source_review_count=None,
            )

            quality = CandidateQualitySignals()

            candidate = NormalizedPlaceCandidate(
                provenance=provenance,
                names=names,
                address=address,
                location=location,
                classification=classification,
                business=business,
                quality=quality,
                source_attributes={
                    "google_types": types,
                    "business_status": business_status,
                    "google_maps_uri": google_maps_uri,
                },
                source_payload=place,
            )

            candidate = self._assign_candidate_status(candidate)

            if candidate.quality.candidate_status == "accepted":
                accepted_count += 1
            elif candidate.quality.candidate_status == "needs_review":
                needs_review_count += 1
                issues.append(
                    self._build_issue(
                        issue_code="candidate_requires_review",
                        severity="warning",
                        message="El candidato requiere revisión manual antes de consolidar.",
                        place_index=place_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                    )
                )
            elif candidate.quality.candidate_status == "rejected":
                rejected_count += 1
                for rejection_reason in candidate.quality.rejection_reasons:
                    issues.append(
                        self._build_issue(
                            issue_code=rejection_reason,
                            severity="warning",
                            message=(
                                "El candidato ha sido marcado como rejected "
                                f"por: {rejection_reason}"
                            ),
                            place_index=place_index,
                            source_entity_type=source_entity_type,
                            source_record_id=source_record_id,
                        )
                    )

            candidates.append(candidate)

        return GooglePlacesTransformationResult(
            payload_metadata=payload_metadata,
            candidates=candidates,
            issues=issues,
            total_places=len(places),
            accepted_count=accepted_count,
            needs_review_count=needs_review_count,
            rejected_count=rejected_count,
            skipped_count=skipped_count,
        )