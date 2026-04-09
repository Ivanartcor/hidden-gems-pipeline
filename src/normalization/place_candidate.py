from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        clean_value = value.strip()
        if clean_value and clean_value not in seen:
            seen.add(clean_value)
            result.append(clean_value)

    return result


class CandidateProvenance(BaseModel):
    """
    Identidad y trazabilidad del candidato respecto a la fuente.
    """

    model_config = ConfigDict(extra="allow")

    source_system_code: str
    source_entity_type: str
    source_record_id: str

    source_run_id: str | None = None
    raw_asset_id: str | None = None

    source_url: str | None = None
    source_status_raw: str | None = None
    source_payload_hash: str | None = None

    source_created_at_raw: str | None = None
    source_updated_at_raw: str | None = None


class CandidateNameInfo(BaseModel):
    """
    Nombres y variantes textuales del local.
    """

    model_config = ConfigDict(extra="allow")

    source_name_raw: str | None = None
    source_official_name_raw: str | None = None
    source_display_name_raw: str | None = None
    source_alt_names_raw: list[str] = Field(default_factory=list)

    normalized_name: str | None = None
    display_name: str | None = None

    brand_raw: str | None = None
    operator_raw: str | None = None
    short_name_raw: str | None = None
    old_names_raw: list[str] = Field(default_factory=list)

    @field_validator("source_alt_names_raw", "old_names_raw", mode="before")
    @classmethod
    def _normalize_name_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return _dedupe_preserve_order([str(item) for item in value])
        return [str(value).strip()]


class CandidateAddressInfo(BaseModel):
    """
    Dirección estructurada y representaciones raw.
    """

    model_config = ConfigDict(extra="allow")

    source_address_raw: str | None = None
    source_address_normalized: str | None = None

    addr_full_raw: str | None = None
    street: str | None = None
    house_number: str | None = None
    postcode: str | None = None
    city: str | None = None
    country: str | None = None
    unit: str | None = None
    floor: str | None = None
    place: str | None = None
    house_name: str | None = None


class CandidateLocationInfo(BaseModel):
    """
    Localización fuente del candidato.
    """

    model_config = ConfigDict(extra="allow")

    latitude: float | None = None
    longitude: float | None = None
    geom_point_geojson: dict[str, Any] | None = None

    geo_precision: str | None = None
    geo_source_field: str | None = None

    @field_validator("latitude")
    @classmethod
    def _validate_latitude(cls, value: float | None) -> float | None:
        if value is not None and not (-90 <= value <= 90):
            raise ValueError("latitude fuera de rango.")
        return value

    @field_validator("longitude")
    @classmethod
    def _validate_longitude(cls, value: float | None) -> float | None:
        if value is not None and not (-180 <= value <= 180):
            raise ValueError("longitude fuera de rango.")
        return value

    @model_validator(mode="after")
    def _validate_coordinate_pair(self) -> "CandidateLocationInfo":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude y longitude deben venir ambas o ninguna.")
        return self


class CandidateClassificationInfo(BaseModel):
    """
    Clasificación del local según la fuente.
    """

    model_config = ConfigDict(extra="allow")

    source_primary_category_raw: str | None = None
    source_categories_raw: list[str] = Field(default_factory=list)

    amenity_raw: str | None = None
    cuisine_raw: list[str] = Field(default_factory=list)
    food_style_raw: list[str] = Field(default_factory=list)

    chain_or_brand_family: str | None = None

    @field_validator("source_categories_raw", "cuisine_raw", "food_style_raw", mode="before")
    @classmethod
    def _normalize_string_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return _dedupe_preserve_order([str(item) for item in value])
        return [str(value).strip()]


class CandidateBusinessInfo(BaseModel):
    """
    Información de negocio, contacto y señales útiles de explotación.
    """

    model_config = ConfigDict(extra="allow")

    phone_raw: str | None = None
    phone_normalized: str | None = None
    mobile_phone_raw: str | None = None
    email_raw: str | None = None

    website_url: str | None = None
    menu_url: str | None = None

    social_urls: dict[str, str] = Field(default_factory=dict)

    opening_hours_raw: str | None = None
    price_level_raw: str | None = None

    source_rating: float | None = None
    source_review_count: int | None = None

    wheelchair_raw: str | None = None
    takeaway_raw: str | None = None
    delivery_raw: str | None = None
    dine_in_raw: str | None = None
    drive_through_raw: str | None = None
    outdoor_seating_raw: str | None = None
    indoor_seating_raw: str | None = None
    reservation_raw: str | None = None
    smoking_raw: str | None = None
    internet_access_raw: str | None = None

    @field_validator("source_rating")
    @classmethod
    def _validate_rating(cls, value: float | None) -> float | None:
        if value is not None and not (0 <= value <= 5):
            raise ValueError("source_rating debe estar entre 0 y 5.")
        return value

    @field_validator("source_review_count")
    @classmethod
    def _validate_review_count(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("source_review_count no puede ser negativo.")
        return value


class CandidateQualitySignals(BaseModel):
    """
    Señales de calidad y decisión dentro del pipeline.
    """

    model_config = ConfigDict(extra="allow")

    has_name: bool = False
    has_coordinates: bool = False
    has_address: bool = False
    has_contact_info: bool = False
    has_category: bool = False
    has_opening_hours: bool = False

    completeness_score: float | None = None

    candidate_status: str = "pending"
    requires_manual_review: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    warning_messages: list[str] = Field(default_factory=list)

    @field_validator("completeness_score")
    @classmethod
    def _validate_completeness_score(cls, value: float | None) -> float | None:
        if value is not None and not (0 <= value <= 1):
            raise ValueError("completeness_score debe estar entre 0 y 1.")
        return value

    @field_validator("rejection_reasons", "warning_messages", mode="before")
    @classmethod
    def _normalize_message_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return _dedupe_preserve_order([str(item) for item in value])
        return [str(value).strip()]


class CandidateGeoEnrichment(BaseModel):
    """
    Resultado de enriquecimiento geográfico posterior.
    """

    model_config = ConfigDict(extra="allow")

    neighborhood_id: str | None = None
    neighborhood_name: str | None = None
    district_id: str | None = None
    district_name: str | None = None

    assignment_method: str | None = None
    assignment_confidence: float | None = None
    distance_to_centroid_m: float | None = None

    @field_validator("assignment_confidence")
    @classmethod
    def _validate_assignment_confidence(cls, value: float | None) -> float | None:
        if value is not None and not (0 <= value <= 1):
            raise ValueError("assignment_confidence debe estar entre 0 y 1.")
        return value

    @field_validator("distance_to_centroid_m")
    @classmethod
    def _validate_distance(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("distance_to_centroid_m no puede ser negativo.")
        return value


class CandidateMatchingInfo(BaseModel):
    """
    Información de matching contra place canónico.
    """

    model_config = ConfigDict(extra="allow")

    matched_place_id: str | None = None
    match_method: str | None = None
    match_confidence: float | None = None
    match_notes: str | None = None

    @field_validator("match_confidence")
    @classmethod
    def _validate_match_confidence(cls, value: float | None) -> float | None:
        if value is not None and not (0 <= value <= 1):
            raise ValueError("match_confidence debe estar entre 0 y 1.")
        return value


class NormalizedPlaceCandidate(BaseModel):
    """
    Contrato común intermedio para candidatos de local procedentes
    de distintas fuentes (OSM, Google Places, Yelp, etc.).

    No representa todavía la entidad canónica final `place`.
    Representa una versión normalizada, trazable y enriquecible
    del registro fuente.
    """

    model_config = ConfigDict(extra="allow")

    provenance: CandidateProvenance
    names: CandidateNameInfo = Field(default_factory=CandidateNameInfo)
    address: CandidateAddressInfo = Field(default_factory=CandidateAddressInfo)
    location: CandidateLocationInfo = Field(default_factory=CandidateLocationInfo)
    classification: CandidateClassificationInfo = Field(default_factory=CandidateClassificationInfo)
    business: CandidateBusinessInfo = Field(default_factory=CandidateBusinessInfo)
    quality: CandidateQualitySignals = Field(default_factory=CandidateQualitySignals)
    geo_enrichment: CandidateGeoEnrichment = Field(default_factory=CandidateGeoEnrichment)
    matching: CandidateMatchingInfo = Field(default_factory=CandidateMatchingInfo)

    source_attributes: dict[str, Any] = Field(default_factory=dict)
    source_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _derive_basic_quality_flags(self) -> "NormalizedPlaceCandidate":
        self.quality.has_name = any(
            bool(value and str(value).strip())
            for value in (
                self.names.source_name_raw,
                self.names.source_official_name_raw,
                self.names.brand_raw,
            )
        )

        self.quality.has_coordinates = (
            self.location.latitude is not None
            and self.location.longitude is not None
        )

        self.quality.has_address = any(
            bool(value and str(value).strip())
            for value in (
                self.address.source_address_raw,
                self.address.street,
                self.address.addr_full_raw,
            )
        )

        self.quality.has_contact_info = any(
            bool(value and str(value).strip())
            for value in (
                self.business.phone_raw,
                self.business.phone_normalized,
                self.business.email_raw,
                self.business.website_url,
            )
        )

        self.quality.has_category = any(
            bool(value and str(value).strip())
            for value in (
                self.classification.source_primary_category_raw,
                self.classification.amenity_raw,
            )
        ) or bool(self.classification.source_categories_raw)

        self.quality.has_opening_hours = bool(
            self.business.opening_hours_raw
            and self.business.opening_hours_raw.strip()
        )

        return self