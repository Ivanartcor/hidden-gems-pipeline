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
class OverpassTransformationIssue:
    issue_code: str
    severity: str
    message: str
    element_index: int | None = None
    source_entity_type: str | None = None
    source_record_id: str | None = None
    field_name: str | None = None
    received_value: Any | None = None


@dataclass(slots=True)
class OverpassTransformationResult:
    payload_metadata: dict[str, Any]
    candidates: list[NormalizedPlaceCandidate]
    issues: list[OverpassTransformationIssue]
    total_elements: int
    accepted_count: int
    needs_review_count: int
    rejected_count: int
    skipped_count: int


class OSMOverpassTransformer:
    """
    Transforma el raw JSON de OSM Overpass en una colección de
    NormalizedPlaceCandidate sin escribir todavía en base de datos.
    """

    VALID_ENTITY_TYPES = {"node", "way", "relation"}

    def _build_issue(
        self,
        *,
        issue_code: str,
        severity: str,
        message: str,
        element_index: int | None = None,
        source_entity_type: str | None = None,
        source_record_id: str | None = None,
        field_name: str | None = None,
        received_value: Any | None = None,
    ) -> OverpassTransformationIssue:
        return OverpassTransformationIssue(
            issue_code=issue_code,
            severity=severity,
            message=message,
            element_index=element_index,
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

        cleaned = re.sub(r"\s+", " ", value.strip())
        return cleaned.title() if cleaned else None

    @staticmethod
    def _split_multi_value(value: str | None) -> list[str]:
        if not value:
            return []

        parts = [part.strip() for part in value.split(";")]
        return [part for part in parts if part]

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

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        serialized = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def _extract_coordinates(
        self,
        element: dict[str, Any],
    ) -> tuple[float | None, float | None, str | None]:
        element_type = element.get("type")

        if element_type == "node":
            lat = element.get("lat")
            lon = element.get("lon")
            if lat is not None and lon is not None:
                return float(lat), float(lon), "lat_lon"

        if element_type in {"way", "relation"}:
            center = element.get("center")
            if isinstance(center, dict):
                lat = center.get("lat")
                lon = center.get("lon")
                if lat is not None and lon is not None:
                    return float(lat), float(lon), "center"

        return None, None, None

    def _build_point_geojson(
        self,
        latitude: float | None,
        longitude: float | None,
    ) -> dict[str, Any] | None:
        if latitude is None or longitude is None:
            return None

        return {
            "type": "Point",
            "coordinates": [longitude, latitude],
        }

    def _resolve_name_fields(
        self,
        tags: dict[str, Any],
    ) -> tuple[str | None, str | None, str | None]:
        source_name_raw = self._clean_text(tags.get("name"))
        source_official_name_raw = self._clean_text(tags.get("official_name"))
        brand_raw = self._clean_text(tags.get("brand"))

        preferred_name = (
            source_name_raw
            or source_official_name_raw
            or brand_raw
        )

        return source_name_raw, source_official_name_raw, preferred_name

    def _extract_alt_names(self, tags: dict[str, Any]) -> tuple[list[str], list[str], str | None]:
        alt_names: list[str] = []
        old_names: list[str] = []

        short_name = self._clean_text(tags.get("short_name"))
        alt_name = self._clean_text(tags.get("alt_name"))
        old_name = self._clean_text(tags.get("old_name"))

        if alt_name:
            alt_names.extend(self._split_multi_value(alt_name))

        for key, value in tags.items():
            if not isinstance(key, str):
                continue
            if key.startswith("name:"):
                clean_value = self._clean_text(value)
                if clean_value:
                    alt_names.append(clean_value)

        if old_name:
            old_names.extend(self._split_multi_value(old_name))

        return (
            self._dedupe_preserve_order(alt_names),
            self._dedupe_preserve_order(old_names),
            short_name,
        )

    def _build_address_info(self, tags: dict[str, Any]) -> CandidateAddressInfo:
        street = self._clean_text(tags.get("addr:street"))
        house_number = self._clean_text(tags.get("addr:housenumber"))
        postcode = self._clean_text(tags.get("addr:postcode"))
        city = self._clean_text(tags.get("addr:city"))
        country = self._clean_text(tags.get("addr:country"))
        unit = self._clean_text(tags.get("addr:unit"))
        floor = self._clean_text(tags.get("addr:floor"))
        place = self._clean_text(tags.get("addr:place"))
        house_name = self._clean_text(tags.get("addr:housename"))
        addr_full_raw = self._clean_text(tags.get("addr:full"))

        address_parts = [
            street,
            house_number,
            postcode,
            city,
            country,
        ]
        source_address_raw = ", ".join(part for part in address_parts if part) or addr_full_raw

        return CandidateAddressInfo(
            source_address_raw=source_address_raw,
            source_address_normalized=self._normalize_name(source_address_raw),
            addr_full_raw=addr_full_raw,
            street=street,
            house_number=house_number,
            postcode=postcode,
            city=city,
            country=country,
            unit=unit,
            floor=floor,
            place=place,
            house_name=house_name,
        )

    def _build_social_urls(self, tags: dict[str, Any]) -> dict[str, str]:
        mappings = {
            "facebook": ["contact:facebook", "facebook"],
            "instagram": ["contact:instagram", "instagram"],
            "twitter": ["contact:twitter", "twitter"],
            "tiktok": ["contact:tiktok"],
            "tripadvisor": ["contact:tripadvisor"],
        }

        social_urls: dict[str, str] = {}

        for social_name, candidate_keys in mappings.items():
            for key in candidate_keys:
                value = self._clean_text(tags.get(key))
                if value:
                    social_urls[social_name] = value
                    break

        return social_urls

    def _derive_source_status(self, tags: dict[str, Any]) -> str | None:
        if tags.get("disused") or tags.get("disused:amenity"):
            return "disused"

        if tags.get("amenity"):
            return "active"

        return None

    def _build_classification_info(
        self,
        tags: dict[str, Any],
    ) -> CandidateClassificationInfo:
        amenity_raw = self._clean_text(tags.get("amenity"))
        cuisine_raw = self._split_multi_value(self._clean_text(tags.get("cuisine")))

        source_categories_raw = self._dedupe_preserve_order(
            [value for value in [amenity_raw, *cuisine_raw] if value]
        )

        food_style_raw = []

        for style_key in (
            "breakfast",
            "bakery",
            "brewery",
            "bar",
            "cafe",
            "fast_food",
            "regional",
            "food",
        ):
            if style_key in tags:
                food_style_raw.append(style_key)

        return CandidateClassificationInfo(
            source_primary_category_raw=amenity_raw,
            source_categories_raw=source_categories_raw,
            amenity_raw=amenity_raw,
            cuisine_raw=cuisine_raw,
            food_style_raw=self._dedupe_preserve_order(food_style_raw),
            chain_or_brand_family=self._clean_text(tags.get("brand")),
        )

    def _build_business_info(
        self,
        tags: dict[str, Any],
    ) -> CandidateBusinessInfo:
        phone_raw = (
            self._clean_text(tags.get("phone"))
            or self._clean_text(tags.get("contact:phone"))
        )

        mobile_phone_raw = (
            self._clean_text(tags.get("phone:mobile"))
            or self._clean_text(tags.get("contact:mobile"))
        )

        website_url = (
            self._clean_text(tags.get("website"))
            or self._clean_text(tags.get("contact:website"))
        )

        return CandidateBusinessInfo(
            phone_raw=phone_raw,
            phone_normalized=phone_raw,
            mobile_phone_raw=mobile_phone_raw,
            email_raw=(
                self._clean_text(tags.get("email"))
                or self._clean_text(tags.get("contact:email"))
            ),
            website_url=website_url,
            menu_url=self._clean_text(tags.get("website:menu")),
            social_urls=self._build_social_urls(tags),
            opening_hours_raw=self._clean_text(tags.get("opening_hours")),
            price_level_raw=None,
            source_rating=None,
            source_review_count=None,
            wheelchair_raw=self._clean_text(tags.get("wheelchair")),
            takeaway_raw=self._clean_text(tags.get("takeaway")),
            delivery_raw=self._clean_text(tags.get("delivery")),
            dine_in_raw=self._clean_text(tags.get("dine_in")),
            drive_through_raw=self._clean_text(tags.get("drive_through")),
            outdoor_seating_raw=self._clean_text(tags.get("outdoor_seating")),
            indoor_seating_raw=self._clean_text(tags.get("indoor_seating")),
            reservation_raw=self._clean_text(tags.get("reservation")),
            smoking_raw=self._clean_text(tags.get("smoking")),
            internet_access_raw=self._clean_text(tags.get("internet_access")),
        )

    def _calculate_completeness_score(
        self,
        *,
        has_name: bool,
        has_coordinates: bool,
        has_category: bool,
        has_address: bool,
        has_contact_info: bool,
        has_opening_hours: bool,
    ) -> float:
        score = 0.0
        score += 0.35 if has_name else 0.0
        score += 0.25 if has_coordinates else 0.0
        score += 0.15 if has_category else 0.0
        score += 0.10 if has_address else 0.0
        score += 0.10 if has_contact_info else 0.0
        score += 0.05 if has_opening_hours else 0.0
        return round(score, 4)

    def _assign_candidate_status(
        self,
        candidate: NormalizedPlaceCandidate,
    ) -> NormalizedPlaceCandidate:
        rejection_reasons: list[str] = []
        warning_messages: list[str] = []

        if not candidate.quality.has_coordinates:
            rejection_reasons.append("missing_coordinates")

        if not candidate.quality.has_category:
            rejection_reasons.append("missing_category")

        if not candidate.quality.has_name:
            warning_messages.append("missing_name")

        source_status = candidate.provenance.source_status_raw
        if source_status == "disused":
            warning_messages.append("source_marked_as_disused")

        candidate.quality.completeness_score = self._calculate_completeness_score(
            has_name=candidate.quality.has_name,
            has_coordinates=candidate.quality.has_coordinates,
            has_category=candidate.quality.has_category,
            has_address=candidate.quality.has_address,
            has_contact_info=candidate.quality.has_contact_info,
            has_opening_hours=candidate.quality.has_opening_hours,
        )

        candidate.quality.rejection_reasons = rejection_reasons
        candidate.quality.warning_messages = warning_messages

        if rejection_reasons:
            candidate.quality.candidate_status = "rejected"
        elif not candidate.quality.has_name:
            candidate.quality.candidate_status = "needs_review"
            candidate.quality.requires_manual_review = True
        elif source_status == "disused":
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
    ) -> OverpassTransformationResult:
        if not isinstance(payload, dict):
            raise ValueError("El payload debe ser un dict.")

        elements = payload.get("elements")
        if not isinstance(elements, list):
            raise ValueError("El payload no contiene una lista válida en 'elements'.")

        issues: list[OverpassTransformationIssue] = []
        candidates: list[NormalizedPlaceCandidate] = []

        accepted_count = 0
        needs_review_count = 0
        rejected_count = 0
        skipped_count = 0

        payload_metadata = {
            "version": payload.get("version"),
            "generator": payload.get("generator"),
            "osm_base_timestamp": (
                payload.get("osm3s", {}).get("timestamp_osm_base")
                if isinstance(payload.get("osm3s"), dict)
                else None
            ),
        }

        for element_index, element in enumerate(elements, start=1):
            if not isinstance(element, dict):
                issues.append(
                    self._build_issue(
                        issue_code="invalid_element_structure",
                        severity="error",
                        message="El elemento no tiene una estructura válida.",
                        element_index=element_index,
                    )
                )
                skipped_count += 1
                continue

            source_entity_type = self._clean_text(element.get("type"))
            source_record_id = self._clean_text(element.get("id"))

            if source_entity_type not in self.VALID_ENTITY_TYPES:
                issues.append(
                    self._build_issue(
                        issue_code="invalid_entity_type",
                        severity="error",
                        message="El elemento tiene un type no soportado.",
                        element_index=element_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        field_name="type",
                        received_value=element.get("type"),
                    )
                )
                skipped_count += 1
                continue

            if source_record_id is None:
                issues.append(
                    self._build_issue(
                        issue_code="missing_source_record_id",
                        severity="error",
                        message="El elemento no contiene id utilizable.",
                        element_index=element_index,
                        source_entity_type=source_entity_type,
                        field_name="id",
                        received_value=element.get("id"),
                    )
                )
                skipped_count += 1
                continue

            tags = element.get("tags")
            if not isinstance(tags, dict):
                issues.append(
                    self._build_issue(
                        issue_code="missing_tags",
                        severity="error",
                        message="El elemento no contiene tags válidos.",
                        element_index=element_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                        field_name="tags",
                        received_value=tags,
                    )
                )
                skipped_count += 1
                continue

            latitude, longitude, geo_source_field = self._extract_coordinates(element)

            if latitude is None or longitude is None:
                issues.append(
                    self._build_issue(
                        issue_code="missing_coordinates",
                        severity="warning",
                        message="El elemento no tiene coordenadas utilizables.",
                        element_index=element_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_record_id,
                    )
                )

            source_name_raw, source_official_name_raw, preferred_name = self._resolve_name_fields(tags)
            alt_names, old_names, short_name = self._extract_alt_names(tags)

            address_info = self._build_address_info(tags)
            classification_info = self._build_classification_info(tags)
            business_info = self._build_business_info(tags)

            provenance = CandidateProvenance(
                source_system_code="osm_overpass",
                source_entity_type=source_entity_type,
                source_record_id=source_record_id,
                source_run_id=str(source_run_id) if source_run_id is not None else None,
                raw_asset_id=str(raw_asset_id) if raw_asset_id is not None else None,
                source_url=None,
                source_status_raw=self._derive_source_status(tags),
                source_payload_hash=self._hash_payload(element),
                source_created_at_raw=None,
                source_updated_at_raw=None,
            )

            names = CandidateNameInfo(
                source_name_raw=source_name_raw,
                source_official_name_raw=source_official_name_raw,
                source_display_name_raw=preferred_name,
                source_alt_names_raw=alt_names,
                normalized_name=self._normalize_name(preferred_name),
                display_name=self._build_display_name(preferred_name),
                brand_raw=self._clean_text(tags.get("brand")),
                operator_raw=self._clean_text(tags.get("operator")),
                short_name_raw=short_name,
                old_names_raw=old_names,
            )

            location = CandidateLocationInfo(
                latitude=latitude,
                longitude=longitude,
                geom_point_geojson=self._build_point_geojson(latitude, longitude),
                geo_precision="point" if geo_source_field == "lat_lon" else "center",
                geo_source_field=geo_source_field,
            )

            quality = CandidateQualitySignals()

            candidate = NormalizedPlaceCandidate(
                provenance=provenance,
                names=names,
                address=address_info,
                location=location,
                classification=classification_info,
                business=business_info,
                quality=quality,
                source_attributes=dict(tags),
                source_payload=element,
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
                        element_index=element_index,
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
                            element_index=element_index,
                            source_entity_type=source_entity_type,
                            source_record_id=source_record_id,
                        )
                    )

            candidates.append(candidate)

        return OverpassTransformationResult(
            payload_metadata=payload_metadata,
            candidates=candidates,
            issues=issues,
            total_elements=len(elements),
            accepted_count=accepted_count,
            needs_review_count=needs_review_count,
            rejected_count=rejected_count,
            skipped_count=skipped_count,
        )