from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from src.normalization.review_candidate import (
    NormalizedReviewCandidate,
    ReviewAuthorInfo,
    ReviewProvenance,
    ReviewQualitySignals,
    ReviewRatingInfo,
    ReviewTextInfo,
    ReviewTimeInfo,
)


@dataclass(slots=True)
class GooglePlacesReviewTransformationIssue:
    issue_code: str
    severity: str
    message: str
    review_index: int | None = None
    source_entity_type: str | None = None
    source_record_id: str | None = None
    field_name: str | None = None
    received_value: Any | None = None


@dataclass(slots=True)
class GooglePlacesReviewTransformationResult:
    payload_metadata: dict[str, Any]
    candidates: list[NormalizedReviewCandidate]
    issues: list[GooglePlacesReviewTransformationIssue]
    total_reviews: int
    accepted_count: int
    rejected_count: int
    skipped_count: int


class GooglePlacesReviewsTransformer:
    """
    Transforma una respuesta raw de Google Places Place Details en
    candidatos normalizados de reseña.

    Entrada esperada:
    {
      "id": "ChIJ...",
      "displayName": {...},
      "reviews": [...]
    }
    """

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)
        return text or None

    @staticmethod
    def _normalize_review_text(value: str | None) -> str | None:
        if not value:
            return None

        text = value.strip()
        text = re.sub(r"\s+", " ", text)
        return text or None

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
    def _hash_review_identity(
        *,
        google_place_id: str,
        review_name: str | None,
        author_name: str | None,
        publish_time: str | None,
        rating: Any | None,
        review_text: str | None,
    ) -> str:
        """
        Genera un ID estable de review.

        Si Google devuelve reviews[].name, se usa como señal principal.
        Si en el futuro alguna respuesta no lo trae, el hash sigue siendo estable
        usando place_id + autor + fecha + rating + texto.
        """
        identity_payload = {
            "google_place_id": google_place_id,
            "review_name": review_name,
            "author_name": author_name,
            "publish_time": publish_time,
            "rating": rating,
            "review_text": review_text,
        }

        serialized = json.dumps(
            identity_payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        ).encode("utf-8")

        return hashlib.sha256(serialized).hexdigest()

    def _build_issue(
        self,
        *,
        issue_code: str,
        severity: str,
        message: str,
        review_index: int | None = None,
        source_entity_type: str | None = None,
        source_record_id: str | None = None,
        field_name: str | None = None,
        received_value: Any | None = None,
    ) -> GooglePlacesReviewTransformationIssue:
        return GooglePlacesReviewTransformationIssue(
            issue_code=issue_code,
            severity=severity,
            message=message,
            review_index=review_index,
            source_entity_type=source_entity_type,
            source_record_id=source_record_id,
            field_name=field_name,
            received_value=received_value,
        )

    @staticmethod
    def _extract_display_name(payload: dict[str, Any]) -> str | None:
        display_name = payload.get("displayName")

        if isinstance(display_name, dict):
            text = display_name.get("text")
            return str(text).strip() if text else None

        return None

    @staticmethod
    def _extract_localized_text(
        review: dict[str, Any],
        field_name: str,
    ) -> tuple[str | None, str | None]:
        value = review.get(field_name)

        if not isinstance(value, dict):
            return None, None

        text = value.get("text")
        language_code = value.get("languageCode")

        clean_text = str(text).strip() if text else None
        clean_language = str(language_code).strip() if language_code else None

        return clean_text, clean_language

    @staticmethod
    def _extract_author(review: dict[str, Any]) -> dict[str, Any]:
        author = review.get("authorAttribution")

        if not isinstance(author, dict):
            return {}

        return author

    def _assign_candidate_status(
        self,
        candidate: NormalizedReviewCandidate,
    ) -> NormalizedReviewCandidate:
        rejection_reasons: list[str] = []
        warning_messages: list[str] = []

        if not candidate.quality.has_source_review_id:
            rejection_reasons.append("missing_source_review_id")

        if not candidate.quality.has_place_link:
            rejection_reasons.append("missing_place_link")

        if not candidate.quality.has_text:
            rejection_reasons.append("missing_review_text")

        if not candidate.quality.has_rating:
            warning_messages.append("missing_rating")

        if not candidate.quality.has_author:
            warning_messages.append("missing_author")

        if not candidate.quality.has_publish_time:
            warning_messages.append("missing_publish_time")

        candidate.quality.rejection_reasons = rejection_reasons
        candidate.quality.warning_messages = warning_messages

        if rejection_reasons:
            candidate.quality.candidate_status = "rejected"
            candidate.quality.requires_manual_review = False
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
        place_id: str | None = None,
        place_source_ref_id: str | None = None,
    ) -> GooglePlacesReviewTransformationResult:
        if not isinstance(payload, dict):
            raise ValueError("El payload debe ser un dict.")

        google_place_id = self._clean_text(payload.get("id"))
        display_name = self._extract_display_name(payload)

        reviews = payload.get("reviews")
        if reviews is None:
            reviews = []

        if not isinstance(reviews, list):
            raise ValueError("El payload no contiene una lista válida en 'reviews'.")

        issues: list[GooglePlacesReviewTransformationIssue] = []
        candidates: list[NormalizedReviewCandidate] = []

        accepted_count = 0
        rejected_count = 0
        skipped_count = 0

        payload_metadata = {
            "source": "google_places",
            "response_type": "place_details_reviews",
            "google_place_id": google_place_id,
            "display_name": display_name,
            "review_count": len(reviews),
            "place_id": place_id,
            "place_source_ref_id": place_source_ref_id,
        }

        if not google_place_id:
            issues.append(
                self._build_issue(
                    issue_code="missing_google_place_id",
                    severity="error",
                    message="El payload de Place Details no contiene id.",
                    field_name="id",
                    received_value=payload.get("id"),
                )
            )

        for review_index, review in enumerate(reviews, start=1):
            if not isinstance(review, dict):
                issues.append(
                    self._build_issue(
                        issue_code="invalid_review_structure",
                        severity="error",
                        message="El elemento de reviews no tiene una estructura válida.",
                        review_index=review_index,
                        received_value=review,
                    )
                )
                skipped_count += 1
                continue

            source_entity_type = "google_place_review"

            review_name = self._clean_text(review.get("name"))
            rating_value = review.get("rating")
            review_text_raw, review_language = self._extract_localized_text(review, "text")
            original_text_raw, original_language = self._extract_localized_text(review, "originalText")
            author = self._extract_author(review)

            author_name = self._clean_text(author.get("displayName"))
            author_uri = self._clean_text(author.get("uri"))
            author_photo_uri = self._clean_text(author.get("photoUri"))

            publish_time = self._clean_text(review.get("publishTime"))
            relative_publish_time_description = self._clean_text(
                review.get("relativePublishTimeDescription")
            )
            google_maps_uri = self._clean_text(review.get("googleMapsUri"))
            flag_content_uri = self._clean_text(review.get("flagContentUri"))

            preferred_text = review_text_raw or original_text_raw

            source_payload_hash = self._hash_payload(review)
            source_review_id = self._hash_review_identity(
                google_place_id=google_place_id or "missing_google_place_id",
                review_name=review_name,
                author_name=author_name,
                publish_time=publish_time,
                rating=rating_value,
                review_text=preferred_text,
            )

            if not preferred_text:
                issues.append(
                    self._build_issue(
                        issue_code="missing_review_text",
                        severity="warning",
                        message="La review de Google no contiene texto utilizable.",
                        review_index=review_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_review_id,
                        field_name="text",
                        received_value=review.get("text"),
                    )
                )

            if not review_name:
                issues.append(
                    self._build_issue(
                        issue_code="missing_review_name",
                        severity="warning",
                        message="La review de Google no contiene name; se usará hash sintético.",
                        review_index=review_index,
                        source_entity_type=source_entity_type,
                        source_record_id=source_review_id,
                        field_name="name",
                        received_value=review.get("name"),
                    )
                )

            provenance = ReviewProvenance(
                source_system_code="google_places",
                source_entity_type=source_entity_type,
                source_record_id=source_review_id,
                source_run_id=str(source_run_id) if source_run_id is not None else None,
                raw_asset_id=str(raw_asset_id) if raw_asset_id is not None else None,
                place_id=str(place_id) if place_id is not None else None,
                place_source_ref_id=(
                    str(place_source_ref_id)
                    if place_source_ref_id is not None
                    else None
                ),
                source_place_record_id=google_place_id,
                source_url=google_maps_uri,
                source_payload_hash=source_payload_hash,
            )

            text_info = ReviewTextInfo(
                review_text_raw=preferred_text,
                review_text_normalized=self._normalize_review_text(preferred_text),
                original_text_raw=original_text_raw,
                translated_text=(
                    review_text_raw
                    if original_text_raw
                    and review_text_raw
                    and review_text_raw != original_text_raw
                    else None
                ),
                review_language=review_language or original_language,
                original_language=original_language,
                text_length_chars=len(preferred_text) if preferred_text else None,
            )

            rating_info = ReviewRatingInfo(
                rating_value=float(rating_value) if rating_value is not None else None,
                rating_scale_min=1.0,
                rating_scale_max=5.0,
            )

            author_info = ReviewAuthorInfo(
                author_name_raw=author_name,
                author_uri=author_uri,
                author_photo_uri=author_photo_uri,
            )

            time_info = ReviewTimeInfo(
                review_created_at=publish_time,
                review_updated_at=publish_time,
                relative_publish_time_description=relative_publish_time_description,
            )

            quality = ReviewQualitySignals()

            candidate = NormalizedReviewCandidate(
                provenance=provenance,
                author=author_info,
                text=text_info,
                rating=rating_info,
                time=time_info,
                quality=quality,
                is_operational_review=True,
                is_training_eligible=True,
                source_attributes={
                    "google_review_name": review_name,
                    "flag_content_uri": flag_content_uri,
                    "author_photo_uri": author_photo_uri,
                    "place_display_name": display_name,
                },
                source_payload=review,
            )

            candidate = self._assign_candidate_status(candidate)

            if candidate.quality.candidate_status == "accepted":
                accepted_count += 1
            elif candidate.quality.candidate_status == "rejected":
                rejected_count += 1
                for rejection_reason in candidate.quality.rejection_reasons:
                    issues.append(
                        self._build_issue(
                            issue_code=rejection_reason,
                            severity="warning",
                            message=(
                                "La review ha sido marcada como rejected "
                                f"por: {rejection_reason}"
                            ),
                            review_index=review_index,
                            source_entity_type=source_entity_type,
                            source_record_id=source_review_id,
                        )
                    )

            candidates.append(candidate)

        return GooglePlacesReviewTransformationResult(
            payload_metadata=payload_metadata,
            candidates=candidates,
            issues=issues,
            total_reviews=len(reviews),
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            skipped_count=skipped_count,
        )