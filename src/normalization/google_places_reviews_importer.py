from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


@dataclass(slots=True)
class GooglePlacesReviewImportResult:
    input_count: int
    imported_count: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    validation_issue_count: int


class GooglePlacesReviewsImporter:
    """
    Importa candidatos de review de Google Places desde staging hacia hidden_gems.review.

    La review queda asociada a:
    - place
    - place_source_ref
    - source_system
    - source_run
    - raw_asset

    La deduplicación se realiza por:
    - source_system_id
    - source_place_record_id
    - source_review_id
    """

    SOURCE_CODE = "google_places"

    @staticmethod
    def _get_nested(data: dict[str, Any], path: tuple[str, ...]) -> Any:
        current: Any = data

        for key in path:
            if not isinstance(current, dict):
                return None
            current = current.get(key)

        return current

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None

        text_value = str(value).strip()
        return text_value or None

    def _get_source_system_id(self, connection: Connection) -> str:
        query = text(
            """
            SELECT source_system_id::text
            FROM hidden_gems.source_system
            WHERE source_code = :source_code
              AND is_active = TRUE
            LIMIT 1
            """
        )

        result = connection.execute(
            query,
            {"source_code": self.SOURCE_CODE},
        ).scalar_one_or_none()

        if result is None:
            raise ValueError(
                f"No existe source_system activo para source_code='{self.SOURCE_CODE}'."
            )

        return str(result)

    def _validate_place_source_ref(
        self,
        connection: Connection,
        *,
        place_id: str,
        place_source_ref_id: str,
        source_place_record_id: str,
    ) -> bool:
        query = text(
            """
            SELECT 1
            FROM hidden_gems.place_source_ref psr
            JOIN hidden_gems.source_system ss
                ON ss.source_system_id = psr.source_system_id
            WHERE psr.place_source_ref_id = :place_source_ref_id
              AND psr.place_id = :place_id
              AND psr.source_record_id = :source_place_record_id
              AND ss.source_code = :source_code
              AND psr.is_current = TRUE
              AND psr.is_deleted_in_source = FALSE
            LIMIT 1
            """
        )

        result = connection.execute(
            query,
            {
                "place_id": place_id,
                "place_source_ref_id": place_source_ref_id,
                "source_place_record_id": source_place_record_id,
                "source_code": self.SOURCE_CODE,
            },
        ).scalar_one_or_none()

        return result is not None

    def _find_existing_review(
        self,
        connection: Connection,
        *,
        source_system_id: str,
        source_place_record_id: str,
        source_review_id: str,
    ) -> str | None:
        query = text(
            """
            SELECT review_id::text
            FROM hidden_gems.review
            WHERE source_system_id = :source_system_id
              AND source_place_record_id = :source_place_record_id
              AND source_review_id = :source_review_id
            LIMIT 1
            """
        )

        result = connection.execute(
            query,
            {
                "source_system_id": source_system_id,
                "source_place_record_id": source_place_record_id,
                "source_review_id": source_review_id,
            },
        ).scalar_one_or_none()

        if result is not None:
            return str(result)

        fallback_query = text(
            """
            SELECT review_id::text
            FROM hidden_gems.review
            WHERE source_system_id = :source_system_id
              AND source_review_id = :source_review_id
            LIMIT 1
            """
        )

        fallback = connection.execute(
            fallback_query,
            {
                "source_system_id": source_system_id,
                "source_review_id": source_review_id,
            },
        ).scalar_one_or_none()

        return str(fallback) if fallback is not None else None

    def _build_review_params(
        self,
        *,
        candidate: dict[str, Any],
        source_system_id: str,
        source_run_id: str,
        raw_asset_id: str,
    ) -> dict[str, Any]:
        provenance = candidate.get("provenance") or {}
        author = candidate.get("author") or {}
        text_info = candidate.get("text") or {}
        rating_info = candidate.get("rating") or {}
        time_info = candidate.get("time") or {}

        return {
            "place_id": self._clean_text(provenance.get("place_id")),
            "place_source_ref_id": self._clean_text(
                provenance.get("place_source_ref_id")
            ),
            "source_system_id": source_system_id,
            "source_run_id": source_run_id,
            "raw_asset_id": raw_asset_id,
            "source_review_id": self._clean_text(provenance.get("source_record_id")),
            "source_place_record_id": self._clean_text(
                provenance.get("source_place_record_id")
            ),
            "author_name_raw": self._clean_text(author.get("author_name_raw")),
            "author_uri": self._clean_text(author.get("author_uri")),
            "rating_value": rating_info.get("rating_value"),
            "review_title": None,
            "review_text_raw": self._clean_text(text_info.get("review_text_raw")),
            "review_text_normalized": self._clean_text(
                text_info.get("review_text_normalized")
            ),
            "review_language": self._clean_text(text_info.get("review_language")),
            "review_created_at": self._clean_text(time_info.get("review_created_at")),
            "review_updated_at": self._clean_text(time_info.get("review_updated_at")),
            "relative_publish_time_description": self._clean_text(
                time_info.get("relative_publish_time_description")
            ),
            "source_review_url": self._clean_text(provenance.get("source_url")),
            "helpful_count": None,
            "translated_text": self._clean_text(text_info.get("translated_text")),
            "source_payload_hash": self._clean_text(
                provenance.get("source_payload_hash")
            ),
            "is_operational_review": bool(
                candidate.get("is_operational_review", True)
            ),
            "is_training_eligible": bool(
                candidate.get("is_training_eligible", True)
            ),
        }

    def _insert_validation_issue(
        self,
        connection: Connection,
        *,
        source_run_id: str,
        raw_asset_id: str | None,
        entity_type: str,
        entity_id: str | None,
        issue_code: str,
        issue_type: str,
        severity: str,
        message: str,
        field_name: str | None = None,
        received_value: str | None = None,
        expected_rule: str | None = None,
    ) -> None:
        connection.execute(
            text(
                """
                INSERT INTO hidden_gems.validation_issue (
                    source_run_id,
                    raw_asset_id,
                    entity_type,
                    entity_id,
                    issue_code,
                    issue_type,
                    severity,
                    message,
                    field_name,
                    received_value,
                    expected_rule
                )
                VALUES (
                    :source_run_id,
                    :raw_asset_id,
                    :entity_type,
                    :entity_id,
                    :issue_code,
                    CAST(:issue_type AS hidden_gems.validation_issue_type_enum),
                    CAST(:severity AS hidden_gems.validation_severity_enum),
                    :message,
                    :field_name,
                    :received_value,
                    :expected_rule
                )
                """
            ),
            {
                "source_run_id": source_run_id,
                "raw_asset_id": raw_asset_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "issue_code": issue_code,
                "issue_type": issue_type,
                "severity": severity,
                "message": message,
                "field_name": field_name,
                "received_value": received_value,
                "expected_rule": expected_rule,
            },
        )

    def _insert_review(
        self,
        connection: Connection,
        *,
        params: dict[str, Any],
    ) -> str:
        query = text(
            """
            INSERT INTO hidden_gems.review (
                place_id,
                place_source_ref_id,
                source_system_id,
                source_run_id,
                raw_asset_id,
                source_review_id,
                source_place_record_id,
                author_name_raw,
                author_uri,
                rating_value,
                review_title,
                review_text_raw,
                review_text_normalized,
                review_language,
                review_created_at,
                review_updated_at,
                relative_publish_time_description,
                source_review_url,
                helpful_count,
                translated_text,
                source_payload_hash,
                is_operational_review,
                is_training_eligible,
                is_active,
                is_deleted_in_source
            )
            VALUES (
                :place_id,
                :place_source_ref_id,
                :source_system_id,
                :source_run_id,
                :raw_asset_id,
                :source_review_id,
                :source_place_record_id,
                :author_name_raw,
                :author_uri,
                :rating_value,
                :review_title,
                :review_text_raw,
                :review_text_normalized,
                :review_language,
                :review_created_at,
                :review_updated_at,
                :relative_publish_time_description,
                :source_review_url,
                :helpful_count,
                :translated_text,
                :source_payload_hash,
                :is_operational_review,
                :is_training_eligible,
                TRUE,
                FALSE
            )
            RETURNING review_id::text
            """
        )

        result = connection.execute(query, params).scalar_one()
        return str(result)

    def _update_review(
        self,
        connection: Connection,
        *,
        review_id: str,
        params: dict[str, Any],
    ) -> None:
        query = text(
            """
            UPDATE hidden_gems.review
            SET
                place_id = :place_id,
                place_source_ref_id = :place_source_ref_id,
                source_run_id = :source_run_id,
                raw_asset_id = :raw_asset_id,
                source_place_record_id = :source_place_record_id,
                author_name_raw = :author_name_raw,
                author_uri = :author_uri,
                rating_value = :rating_value,
                review_title = :review_title,
                review_text_raw = :review_text_raw,
                review_text_normalized = :review_text_normalized,
                review_language = :review_language,
                review_created_at = :review_created_at,
                review_updated_at = :review_updated_at,
                relative_publish_time_description = :relative_publish_time_description,
                source_review_url = :source_review_url,
                helpful_count = :helpful_count,
                translated_text = :translated_text,
                source_payload_hash = :source_payload_hash,
                is_operational_review = :is_operational_review,
                is_training_eligible = :is_training_eligible,
                is_active = TRUE,
                is_deleted_in_source = FALSE
            WHERE review_id = :review_id
            """
        )

        connection.execute(
            query,
            {
                **params,
                "review_id": review_id,
            },
        )

    def import_reviews(
        self,
        *,
        reviews: list[dict[str, Any]],
        source_run_id: str,
        raw_asset_id: str,
    ) -> GooglePlacesReviewImportResult:
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        validation_issue_count = 0

        with engine.begin() as connection:
            source_system_id = self._get_source_system_id(connection)

            for candidate in reviews:
                params = self._build_review_params(
                    candidate=candidate,
                    source_system_id=source_system_id,
                    source_run_id=source_run_id,
                    raw_asset_id=raw_asset_id,
                )

                required_fields = {
                    "place_id": params["place_id"],
                    "place_source_ref_id": params["place_source_ref_id"],
                    "source_review_id": params["source_review_id"],
                    "source_place_record_id": params["source_place_record_id"],
                    "review_text_raw": params["review_text_raw"],
                }

                missing_fields = [
                    field_name
                    for field_name, value in required_fields.items()
                    if value is None or str(value).strip() == ""
                ]

                if missing_fields:
                    skipped_count += 1
                    validation_issue_count += 1
                    self._insert_validation_issue(
                        connection,
                        source_run_id=source_run_id,
                        raw_asset_id=raw_asset_id,
                        entity_type="review",
                        entity_id=None,
                        issue_code="review_missing_required_import_fields",
                        issue_type="validation",
                        severity="warning",
                        message=(
                            "La review accepted no tiene campos mínimos para importar: "
                            + ", ".join(missing_fields)
                        ),
                        expected_rule=(
                            "accepted reviews must have place_id, place_source_ref_id, "
                            "source_review_id, source_place_record_id and review_text_raw"
                        ),
                    )
                    continue

                valid_ref = self._validate_place_source_ref(
                    connection,
                    place_id=params["place_id"],
                    place_source_ref_id=params["place_source_ref_id"],
                    source_place_record_id=params["source_place_record_id"],
                )

                if not valid_ref:
                    skipped_count += 1
                    validation_issue_count += 1
                    self._insert_validation_issue(
                        connection,
                        source_run_id=source_run_id,
                        raw_asset_id=raw_asset_id,
                        entity_type="review",
                        entity_id=None,
                        issue_code="review_place_source_ref_not_valid",
                        issue_type="validation",
                        severity="warning",
                        message=(
                            "La review apunta a una combinación place/place_source_ref/"
                            "source_place_record_id no válida para Google Places."
                        ),
                        expected_rule=(
                            "place_source_ref must belong to source google_places, "
                            "same place_id and same Google Place ID"
                        ),
                    )
                    continue

                existing_review_id = self._find_existing_review(
                    connection,
                    source_system_id=source_system_id,
                    source_place_record_id=params["source_place_record_id"],
                    source_review_id=params["source_review_id"],
                )

                if existing_review_id is None:
                    self._insert_review(connection, params=params)
                    inserted_count += 1
                else:
                    self._update_review(
                        connection,
                        review_id=existing_review_id,
                        params=params,
                    )
                    updated_count += 1

            imported_count = inserted_count + updated_count

            connection.execute(
                text(
                    """
                    UPDATE hidden_gems.source_run
                    SET
                        records_staged_count = GREATEST(records_staged_count, :records_staged_count),
                        records_rejected_count = records_rejected_count + :records_rejected_count,
                        warning_count = warning_count + :warning_count
                    WHERE source_run_id = :source_run_id
                    """
                ),
                {
                    "source_run_id": source_run_id,
                    "records_staged_count": imported_count,
                    "records_rejected_count": skipped_count,
                    "warning_count": validation_issue_count,
                },
            )

        result = GooglePlacesReviewImportResult(
            input_count=len(reviews),
            imported_count=inserted_count + updated_count,
            inserted_count=inserted_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            validation_issue_count=validation_issue_count,
        )

        logger.info(
            "Importador Google Places Reviews completado | input=%s | imported=%s | inserted=%s | updated=%s | skipped=%s | issues=%s",
            result.input_count,
            result.imported_count,
            result.inserted_count,
            result.updated_count,
            result.skipped_count,
            result.validation_issue_count,
        )

        return result