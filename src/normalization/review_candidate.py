from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ReviewProvenance(BaseModel):
    """
    Identidad y trazabilidad de una reseña respecto a la fuente.
    """

    model_config = ConfigDict(extra="allow")

    source_system_code: str
    source_entity_type: str
    source_record_id: str

    source_run_id: str | None = None
    raw_asset_id: str | None = None

    place_id: str | None = None
    place_source_ref_id: str | None = None
    source_place_record_id: str | None = None

    source_url: str | None = None
    source_payload_hash: str | None = None


class ReviewAuthorInfo(BaseModel):
    """
    Información pública del autor tal y como llega de la fuente.
    """

    model_config = ConfigDict(extra="allow")

    author_name_raw: str | None = None
    author_uri: str | None = None
    author_photo_uri: str | None = None


class ReviewTextInfo(BaseModel):
    """
    Texto de la reseña y variantes.
    """

    model_config = ConfigDict(extra="allow")

    review_text_raw: str | None = None
    review_text_normalized: str | None = None
    original_text_raw: str | None = None
    translated_text: str | None = None
    review_language: str | None = None
    original_language: str | None = None
    text_length_chars: int | None = None

    @field_validator("text_length_chars")
    @classmethod
    def _validate_text_length(cls, value: int | None) -> int | None:
        if value is not None and value < 0:
            raise ValueError("text_length_chars no puede ser negativo.")
        return value


class ReviewRatingInfo(BaseModel):
    """
    Rating y escala.
    """

    model_config = ConfigDict(extra="allow")

    rating_value: float | None = None
    rating_scale_min: float = 1.0
    rating_scale_max: float = 5.0

    @field_validator("rating_value")
    @classmethod
    def _validate_rating_value(cls, value: float | None) -> float | None:
        if value is not None and not (0 <= value <= 5):
            raise ValueError("rating_value debe estar entre 0 y 5.")
        return value


class ReviewTimeInfo(BaseModel):
    """
    Fechas de publicación/actualización fuente.
    """

    model_config = ConfigDict(extra="allow")

    review_created_at: str | None = None
    review_updated_at: str | None = None
    relative_publish_time_description: str | None = None


class ReviewQualitySignals(BaseModel):
    """
    Señales de calidad del candidato de reseña.
    """

    model_config = ConfigDict(extra="allow")

    has_source_review_id: bool = False
    has_place_link: bool = False
    has_text: bool = False
    has_rating: bool = False
    has_author: bool = False
    has_publish_time: bool = False

    candidate_status: str = "pending"
    requires_manual_review: bool = False
    rejection_reasons: list[str] = Field(default_factory=list)
    warning_messages: list[str] = Field(default_factory=list)


class NormalizedReviewCandidate(BaseModel):
    """
    Contrato intermedio para reseñas procedentes de fuentes externas.

    No representa todavía una fila insertada en hidden_gems.review.
    Sirve para staging, validación, deduplicación e importación posterior.
    """

    model_config = ConfigDict(extra="allow")

    provenance: ReviewProvenance
    author: ReviewAuthorInfo = Field(default_factory=ReviewAuthorInfo)
    text: ReviewTextInfo = Field(default_factory=ReviewTextInfo)
    rating: ReviewRatingInfo = Field(default_factory=ReviewRatingInfo)
    time: ReviewTimeInfo = Field(default_factory=ReviewTimeInfo)
    quality: ReviewQualitySignals = Field(default_factory=ReviewQualitySignals)

    is_operational_review: bool = True
    is_training_eligible: bool = True

    source_attributes: dict[str, Any] = Field(default_factory=dict)
    source_payload: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _derive_quality_flags(self) -> "NormalizedReviewCandidate":
        self.quality.has_source_review_id = bool(
            self.provenance.source_record_id
            and str(self.provenance.source_record_id).strip()
        )
        self.quality.has_place_link = bool(
            self.provenance.place_id
            and self.provenance.place_source_ref_id
            and self.provenance.source_place_record_id
        )
        self.quality.has_text = bool(
            self.text.review_text_raw
            and self.text.review_text_raw.strip()
        )
        self.quality.has_rating = self.rating.rating_value is not None
        self.quality.has_author = bool(
            self.author.author_name_raw
            and self.author.author_name_raw.strip()
        )
        self.quality.has_publish_time = bool(
            self.time.review_created_at
            and str(self.time.review_created_at).strip()
        )
        return self