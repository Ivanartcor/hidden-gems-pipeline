from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.db.database import engine
from src.normalization.place_candidate import NormalizedPlaceCandidate
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


@dataclass(slots=True)
class OSMOverpassImportResult:
    input_count: int
    imported_count: int
    skipped_count: int
    place_created_count: int
    place_updated_count: int
    place_source_ref_created_count: int
    place_source_ref_updated_count: int
    place_category_upserted_count: int
    place_neighborhood_assignment_upserted_count: int
    validation_issue_count: int


class OSMOverpassImporter:
    """
    Importador de candidatos deduplicados de OSM Overpass hacia:
    - place
    - place_source_ref
    - place_category
    - place_neighborhood_assignment
    """

    SOURCE_CODE = "osm_overpass"
    SOURCE_ENTITY_TYPE_LABEL = "place_source_ref"

    def __init__(self) -> None:
        self.logger = logger

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if not value:
            return None
        return re.sub(r"\s+", " ", value.strip().lower()) or None

    @staticmethod
    def _slugify_category_code(value: str) -> str:
        text = value.strip().lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", "_", text).strip("_")
        return text

    @staticmethod
    def _display_name_from_raw(value: str | None) -> str | None:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value.strip())
        return cleaned.title() if cleaned else None

    @staticmethod
    def _candidate_source_name(candidate: NormalizedPlaceCandidate) -> str | None:
        return (
            candidate.names.source_name_raw
            or candidate.names.source_official_name_raw
            or candidate.names.brand_raw
            or candidate.names.display_name
        )

    @staticmethod
    def _candidate_point_geojson(candidate: NormalizedPlaceCandidate) -> str:
        if candidate.location.geom_point_geojson is None:
            raise ValueError("El candidato no tiene geom_point_geojson.")
        return json.dumps(candidate.location.geom_point_geojson, ensure_ascii=False)

    @staticmethod
    def _candidate_categories_json(candidate: NormalizedPlaceCandidate) -> str:
        return json.dumps(
            candidate.classification.source_categories_raw,
            ensure_ascii=False,
        )

    def _get_source_system_id(self, connection: Connection) -> str:
        query = text(
            """
            SELECT source_system_id
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
                "No existe source_system activo para source_code='osm_overpass'."
            )

        return str(result)

    def _find_existing_source_ref(
        self,
        connection: Connection,
        *,
        source_system_id: str,
        candidate: NormalizedPlaceCandidate,
    ) -> dict[str, Any] | None:
        query = text(
            """
            SELECT place_source_ref_id, place_id
            FROM hidden_gems.place_source_ref
            WHERE source_system_id = :source_system_id
              AND source_entity_type = :source_entity_type
              AND source_record_id = :source_record_id
            LIMIT 1
            """
        )

        row = connection.execute(
            query,
            {
                "source_system_id": source_system_id,
                "source_entity_type": candidate.provenance.source_entity_type,
                "source_record_id": candidate.provenance.source_record_id,
            },
        ).mappings().first()

        return dict(row) if row else None

    def _match_existing_place(
        self,
        connection: Connection,
        *,
        candidate: NormalizedPlaceCandidate,
    ) -> tuple[str | None, float | None, str | None]:
        if (
            candidate.names.normalized_name is None
            or candidate.location.latitude is None
            or candidate.location.longitude is None
        ):
            return None, None, None

        query = text(
            """
            WITH candidate_point AS (
                SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS geom
            )
            SELECT
                p.place_id,
                CASE
                    WHEN :address_normalized IS NOT NULL
                         AND p.address_normalized = :address_normalized
                    THEN 1 ELSE 0
                END AS address_match,
                ST_DistanceSphere(
                    p.geom_point,
                    (SELECT geom FROM candidate_point)
                ) AS distance_m
            FROM hidden_gems.place p
            WHERE p.normalized_name = :normalized_name
              AND ST_DWithin(
                    p.geom_point::geography,
                    (SELECT geom FROM candidate_point)::geography,
                    20
              )
            ORDER BY address_match DESC, distance_m ASC
            LIMIT 1
            """
        )

        row = connection.execute(
            query,
            {
                "normalized_name": candidate.names.normalized_name,
                "address_normalized": candidate.address.source_address_normalized,
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
            },
        ).mappings().first()

        if row is None:
            return None, None, None

        address_match = int(row["address_match"]) == 1
        confidence = 0.95 if address_match else 0.85
        match_method = "rule_based"

        return str(row["place_id"]), confidence, match_method

    def _insert_place(
        self,
        connection: Connection,
        *,
        candidate: NormalizedPlaceCandidate,
    ) -> str:
        query = text(
            """
            INSERT INTO hidden_gems.place (
                canonical_name,
                normalized_name,
                display_name,
                address_text,
                address_normalized,
                geom_point,
                latitude,
                longitude,
                website_url,
                phone_number,
                is_active,
                place_confidence
            )
            VALUES (
                :canonical_name,
                :normalized_name,
                :display_name,
                :address_text,
                :address_normalized,
                ST_SetSRID(ST_GeomFromGeoJSON(:geom_point_geojson), 4326),
                :latitude,
                :longitude,
                :website_url,
                :phone_number,
                TRUE,
                :place_confidence
            )
            RETURNING place_id
            """
        )

        result = connection.execute(
            query,
            {
                "canonical_name": self._candidate_source_name(candidate),
                "normalized_name": candidate.names.normalized_name,
                "display_name": candidate.names.display_name,
                "address_text": candidate.address.source_address_raw,
                "address_normalized": candidate.address.source_address_normalized,
                "geom_point_geojson": self._candidate_point_geojson(candidate),
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
                "website_url": candidate.business.website_url,
                "phone_number": candidate.business.phone_normalized or candidate.business.phone_raw,
                "place_confidence": candidate.quality.completeness_score,
            },
        ).scalar_one()

        return str(result)

    def _update_place_minimally(
        self,
        connection: Connection,
        *,
        place_id: str,
        candidate: NormalizedPlaceCandidate,
    ) -> None:
        query = text(
            """
            UPDATE hidden_gems.place
            SET
                address_text = COALESCE(address_text, :address_text),
                address_normalized = COALESCE(address_normalized, :address_normalized),
                website_url = COALESCE(website_url, :website_url),
                phone_number = COALESCE(phone_number, :phone_number),
                place_confidence = GREATEST(COALESCE(place_confidence, 0), COALESCE(:place_confidence, 0)),
                is_active = TRUE
            WHERE place_id = :place_id
            """
        )

        connection.execute(
            query,
            {
                "place_id": place_id,
                "address_text": candidate.address.source_address_raw,
                "address_normalized": candidate.address.source_address_normalized,
                "website_url": candidate.business.website_url,
                "phone_number": candidate.business.phone_normalized or candidate.business.phone_raw,
                "place_confidence": candidate.quality.completeness_score,
            },
        )

    def _insert_place_source_ref(
        self,
        connection: Connection,
        *,
        place_id: str,
        source_system_id: str,
        source_run_id: str,
        raw_asset_id: str | None,
        candidate: NormalizedPlaceCandidate,
        match_method: str,
        match_confidence: float,
    ) -> str:
        query = text(
            """
            INSERT INTO hidden_gems.place_source_ref (
                place_id,
                source_system_id,
                source_run_id,
                raw_asset_id,
                source_entity_type,
                source_record_id,
                source_name_raw,
                source_address_raw,
                source_geom_point,
                source_latitude,
                source_longitude,
                source_url,
                source_rating,
                source_review_count,
                source_primary_category_raw,
                source_categories_raw,
                source_status_raw,
                source_payload_hash,
                match_method,
                match_confidence,
                is_current,
                is_deleted_in_source,
                first_seen_run_id,
                last_seen_run_id
            )
            VALUES (
                :place_id,
                :source_system_id,
                :source_run_id,
                :raw_asset_id,
                :source_entity_type,
                :source_record_id,
                :source_name_raw,
                :source_address_raw,
                ST_SetSRID(ST_GeomFromGeoJSON(:source_geom_point), 4326),
                :source_latitude,
                :source_longitude,
                :source_url,
                :source_rating,
                :source_review_count,
                :source_primary_category_raw,
                CAST(:source_categories_raw AS jsonb),
                :source_status_raw,
                :source_payload_hash,
                :match_method,
                :match_confidence,
                TRUE,
                FALSE,
                :first_seen_run_id,
                :last_seen_run_id
            )
            RETURNING place_source_ref_id
            """
        )

        result = connection.execute(
            query,
            {
                "place_id": place_id,
                "source_system_id": source_system_id,
                "source_run_id": source_run_id,
                "raw_asset_id": raw_asset_id,
                "source_entity_type": candidate.provenance.source_entity_type,
                "source_record_id": candidate.provenance.source_record_id,
                "source_name_raw": self._candidate_source_name(candidate),
                "source_address_raw": candidate.address.source_address_raw,
                "source_geom_point": self._candidate_point_geojson(candidate),
                "source_latitude": candidate.location.latitude,
                "source_longitude": candidate.location.longitude,
                "source_url": candidate.provenance.source_url,
                "source_rating": candidate.business.source_rating,
                "source_review_count": candidate.business.source_review_count,
                "source_primary_category_raw": candidate.classification.source_primary_category_raw,
                "source_categories_raw": self._candidate_categories_json(candidate),
                "source_status_raw": candidate.provenance.source_status_raw,
                "source_payload_hash": candidate.provenance.source_payload_hash,
                "match_method": match_method,
                "match_confidence": match_confidence,
                "first_seen_run_id": source_run_id,
                "last_seen_run_id": source_run_id,
            },
        ).scalar_one()

        return str(result)

    def _update_place_source_ref(
        self,
        connection: Connection,
        *,
        place_source_ref_id: str,
        source_run_id: str,
        raw_asset_id: str | None,
        candidate: NormalizedPlaceCandidate,
    ) -> None:
        query = text(
            """
            UPDATE hidden_gems.place_source_ref
            SET
                source_run_id = :source_run_id,
                raw_asset_id = :raw_asset_id,
                source_name_raw = :source_name_raw,
                source_address_raw = :source_address_raw,
                source_geom_point = ST_SetSRID(ST_GeomFromGeoJSON(:source_geom_point), 4326),
                source_latitude = :source_latitude,
                source_longitude = :source_longitude,
                source_url = :source_url,
                source_rating = :source_rating,
                source_review_count = :source_review_count,
                source_primary_category_raw = :source_primary_category_raw,
                source_categories_raw = CAST(:source_categories_raw AS jsonb),
                source_status_raw = :source_status_raw,
                source_payload_hash = :source_payload_hash,
                match_method = 'source_raw',
                match_confidence = 1.0,
                is_current = TRUE,
                is_deleted_in_source = FALSE,
                last_seen_run_id = :last_seen_run_id
            WHERE place_source_ref_id = :place_source_ref_id
            """
        )

        connection.execute(
            query,
            {
                "place_source_ref_id": place_source_ref_id,
                "source_run_id": source_run_id,
                "raw_asset_id": raw_asset_id,
                "source_name_raw": self._candidate_source_name(candidate),
                "source_address_raw": candidate.address.source_address_raw,
                "source_geom_point": self._candidate_point_geojson(candidate),
                "source_latitude": candidate.location.latitude,
                "source_longitude": candidate.location.longitude,
                "source_url": candidate.provenance.source_url,
                "source_rating": candidate.business.source_rating,
                "source_review_count": candidate.business.source_review_count,
                "source_primary_category_raw": candidate.classification.source_primary_category_raw,
                "source_categories_raw": self._candidate_categories_json(candidate),
                "source_status_raw": candidate.provenance.source_status_raw,
                "source_payload_hash": candidate.provenance.source_payload_hash,
                "last_seen_run_id": source_run_id,
            },
        )

    def _get_or_create_category(
        self,
        connection: Connection,
        *,
        raw_category: str,
    ) -> str:
        normalized_name = self._normalize_text(raw_category)
        if normalized_name is None:
            raise ValueError("No se puede crear categoría a partir de valor vacío.")

        category_code = self._slugify_category_code(normalized_name)
        category_name = raw_category.strip()
        display_name = self._display_name_from_raw(raw_category)

        select_query = text(
            """
            SELECT category_id
            FROM hidden_gems.category
            WHERE normalized_name = :normalized_name
            LIMIT 1
            """
        )
        row = connection.execute(
            select_query,
            {"normalized_name": normalized_name},
        ).scalar_one_or_none()

        if row is not None:
            return str(row)

        insert_query = text(
            """
            INSERT INTO hidden_gems.category (
                category_code,
                category_name,
                normalized_name,
                display_name,
                description,
                parent_category_id,
                category_level,
                is_food_related,
                is_active,
                sort_order
            )
            VALUES (
                :category_code,
                :category_name,
                :normalized_name,
                :display_name,
                NULL,
                NULL,
                1,
                TRUE,
                TRUE,
                NULL
            )
            RETURNING category_id
            """
        )

        result = connection.execute(
            insert_query,
            {
                "category_code": category_code,
                "category_name": category_name,
                "normalized_name": normalized_name,
                "display_name": display_name,
            },
        ).scalar_one()

        return str(result)

    def _upsert_primary_place_category(
        self,
        connection: Connection,
        *,
        place_id: str,
        category_id: str,
        source_system_id: str,
    ) -> None:
        connection.execute(
            text(
                """
                UPDATE hidden_gems.place_category
                SET is_primary = FALSE
                WHERE place_id = :place_id
                  AND is_active = TRUE
                  AND is_primary = TRUE
                """
            ),
            {"place_id": place_id},
        )

        existing = connection.execute(
            text(
                """
                SELECT place_category_id
                FROM hidden_gems.place_category
                WHERE place_id = :place_id
                  AND category_id = :category_id
                  AND assignment_method = 'normalized'
                LIMIT 1
                """
            ),
            {
                "place_id": place_id,
                "category_id": category_id,
            },
        ).scalar_one_or_none()

        if existing is None:
            connection.execute(
                text(
                    """
                    INSERT INTO hidden_gems.place_category (
                        place_id,
                        category_id,
                        source_system_id,
                        assignment_method,
                        is_primary,
                        assignment_confidence,
                        is_active,
                        notes
                    )
                    VALUES (
                        :place_id,
                        :category_id,
                        :source_system_id,
                        'normalized',
                        TRUE,
                        0.95,
                        TRUE,
                        'Asignación primaria derivada desde OSM Overpass.'
                    )
                    """
                ),
                {
                    "place_id": place_id,
                    "category_id": category_id,
                    "source_system_id": source_system_id,
                },
            )
        else:
            connection.execute(
                text(
                    """
                    UPDATE hidden_gems.place_category
                    SET
                        source_system_id = :source_system_id,
                        is_primary = TRUE,
                        assignment_confidence = 0.95,
                        is_active = TRUE,
                        notes = 'Asignación primaria derivada desde OSM Overpass.'
                    WHERE place_category_id = :place_category_id
                    """
                ),
                {
                    "place_category_id": existing,
                    "source_system_id": source_system_id,
                },
            )

    def _resolve_neighborhood_assignment(
        self,
        connection: Connection,
        *,
        candidate: NormalizedPlaceCandidate,
    ) -> dict[str, Any] | None:
        if (
            candidate.location.latitude is None
            or candidate.location.longitude is None
        ):
            return None

        point_in_polygon_query = text(
            """
            WITH candidate_point AS (
                SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS geom
            )
            SELECT
                n.neighborhood_id,
                n.district_id,
                ST_DistanceSphere(
                    (SELECT geom FROM candidate_point),
                    n.centroid_point
                ) AS distance_to_centroid_m
            FROM hidden_gems.neighborhood n
            WHERE ST_Covers(n.geometry, (SELECT geom FROM candidate_point))
            ORDER BY distance_to_centroid_m ASC
            LIMIT 1
            """
        )

        row = connection.execute(
            point_in_polygon_query,
            {
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
            },
        ).mappings().first()

        if row:
            return {
                "neighborhood_id": str(row["neighborhood_id"]),
                "district_id": str(row["district_id"]) if row["district_id"] else None,
                "assignment_method": "point_in_polygon",
                "assignment_confidence": 1.0,
                "distance_to_centroid_m": float(row["distance_to_centroid_m"])
                if row["distance_to_centroid_m"] is not None
                else None,
            }

        nearest_query = text(
            """
            WITH candidate_point AS (
                SELECT ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) AS geom
            )
            SELECT
                n.neighborhood_id,
                n.district_id,
                ST_DistanceSphere(
                    (SELECT geom FROM candidate_point),
                    n.centroid_point
                ) AS distance_to_centroid_m
            FROM hidden_gems.neighborhood n
            ORDER BY n.geometry <-> (SELECT geom FROM candidate_point)
            LIMIT 1
            """
        )

        row = connection.execute(
            nearest_query,
            {
                "latitude": candidate.location.latitude,
                "longitude": candidate.location.longitude,
            },
        ).mappings().first()

        if row:
            return {
                "neighborhood_id": str(row["neighborhood_id"]),
                "district_id": str(row["district_id"]) if row["district_id"] else None,
                "assignment_method": "nearest_polygon",
                "assignment_confidence": 0.70,
                "distance_to_centroid_m": float(row["distance_to_centroid_m"])
                if row["distance_to_centroid_m"] is not None
                else None,
            }

        return None

    def _upsert_place_neighborhood_assignment(
        self,
        connection: Connection,
        *,
        place_id: str,
        assignment: dict[str, Any],
    ) -> None:
        existing = connection.execute(
            text(
                """
                SELECT place_neighborhood_assignment_id, neighborhood_id, district_id
                FROM hidden_gems.place_neighborhood_assignment
                WHERE place_id = :place_id
                  AND is_current = TRUE
                LIMIT 1
                """
            ),
            {"place_id": place_id},
        ).mappings().first()

        if existing is None:
            connection.execute(
                text(
                    """
                    INSERT INTO hidden_gems.place_neighborhood_assignment (
                        place_id,
                        neighborhood_id,
                        district_id,
                        assignment_method,
                        assignment_confidence,
                        source_geometry_used,
                        distance_to_centroid_m,
                        is_current,
                        is_manually_verified,
                        valid_from,
                        valid_to,
                        notes
                    )
                    VALUES (
                        :place_id,
                        :neighborhood_id,
                        :district_id,
                        CAST(:assignment_method AS hidden_gems.assignment_method_enum),
                        :assignment_confidence,
                        'source_geom_point',
                        :distance_to_centroid_m,
                        TRUE,
                        FALSE,
                        NOW(),
                        NULL,
                        'Asignación automática derivada desde OSM Overpass.'
                    )
                    """
                ),
                {
                    "place_id": place_id,
                    "neighborhood_id": assignment["neighborhood_id"],
                    "district_id": assignment["district_id"],
                    "assignment_method": assignment["assignment_method"],
                    "assignment_confidence": assignment["assignment_confidence"],
                    "distance_to_centroid_m": assignment["distance_to_centroid_m"],
                },
            )
            return

        same_neighborhood = str(existing["neighborhood_id"]) == assignment["neighborhood_id"]
        same_district = (
            str(existing["district_id"]) == assignment["district_id"]
            if existing["district_id"] is not None and assignment["district_id"] is not None
            else existing["district_id"] == assignment["district_id"]
        )

        if same_neighborhood and same_district:
            connection.execute(
                text(
                    """
                    UPDATE hidden_gems.place_neighborhood_assignment
                    SET
                        assignment_method = CAST(:assignment_method AS hidden_gems.assignment_method_enum),
                        assignment_confidence = :assignment_confidence,
                        source_geometry_used = 'source_geom_point',
                        distance_to_centroid_m = :distance_to_centroid_m,
                        is_current = TRUE,
                        notes = 'Asignación automática derivada desde OSM Overpass.'
                    WHERE place_neighborhood_assignment_id = :assignment_id
                    """
                ),
                {
                    "assignment_id": existing["place_neighborhood_assignment_id"],
                    "assignment_method": assignment["assignment_method"],
                    "assignment_confidence": assignment["assignment_confidence"],
                    "distance_to_centroid_m": assignment["distance_to_centroid_m"],
                },
            )
            return

        connection.execute(
            text(
                """
                UPDATE hidden_gems.place_neighborhood_assignment
                SET
                    is_current = FALSE,
                    valid_to = NOW()
                WHERE place_neighborhood_assignment_id = :assignment_id
                """
            ),
            {"assignment_id": existing["place_neighborhood_assignment_id"]},
        )

        connection.execute(
            text(
                """
                INSERT INTO hidden_gems.place_neighborhood_assignment (
                    place_id,
                    neighborhood_id,
                    district_id,
                    assignment_method,
                    assignment_confidence,
                    source_geometry_used,
                    distance_to_centroid_m,
                    is_current,
                    is_manually_verified,
                    valid_from,
                    valid_to,
                    notes
                )
                VALUES (
                    :place_id,
                    :neighborhood_id,
                    :district_id,
                    CAST(:assignment_method AS hidden_gems.assignment_method_enum),
                    :assignment_confidence,
                    'source_geom_point',
                    :distance_to_centroid_m,
                    TRUE,
                    FALSE,
                    NOW(),
                    NULL,
                    'Asignación automática derivada desde OSM Overpass.'
                )
                """
            ),
            {
                "place_id": place_id,
                "neighborhood_id": assignment["neighborhood_id"],
                "district_id": assignment["district_id"],
                "assignment_method": assignment["assignment_method"],
                "assignment_confidence": assignment["assignment_confidence"],
                "distance_to_centroid_m": assignment["distance_to_centroid_m"],
            },
        )

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

    def import_candidates(
        self,
        *,
        candidates: list[NormalizedPlaceCandidate],
        source_run_id: str,
        raw_asset_id: str | None = None,
    ) -> OSMOverpassImportResult:
        place_created_count = 0
        place_updated_count = 0
        place_source_ref_created_count = 0
        place_source_ref_updated_count = 0
        place_category_upserted_count = 0
        place_neighborhood_assignment_upserted_count = 0
        validation_issue_count = 0
        imported_count = 0
        skipped_count = 0

        accepted_candidates = [
            candidate
            for candidate in candidates
            if candidate.quality.candidate_status == "accepted"
        ]

        with engine.begin() as connection:
            source_system_id = self._get_source_system_id(connection)

            for candidate in accepted_candidates:
                source_name = self._candidate_source_name(candidate)

                if (
                    source_name is None
                    or candidate.names.normalized_name is None
                    or candidate.location.geom_point_geojson is None
                ):
                    skipped_count += 1
                    validation_issue_count += 1
                    self._insert_validation_issue(
                        connection,
                        source_run_id=source_run_id,
                        raw_asset_id=raw_asset_id,
                        entity_type="place_source_ref",
                        entity_id=None,
                        issue_code="candidate_missing_required_import_fields",
                        issue_type="validation",
                        severity="warning",
                        message="El candidato accepted no tiene campos mínimos para importar.",
                        expected_rule="accepted candidates must have source_name, normalized_name and geom_point",
                    )
                    continue

                existing_source_ref = self._find_existing_source_ref(
                    connection,
                    source_system_id=source_system_id,
                    candidate=candidate,
                )

                if existing_source_ref is not None:
                    place_id = str(existing_source_ref["place_id"])

                    self._update_place_minimally(
                        connection,
                        place_id=place_id,
                        candidate=candidate,
                    )
                    place_updated_count += 1

                    self._update_place_source_ref(
                        connection,
                        place_source_ref_id=str(existing_source_ref["place_source_ref_id"]),
                        source_run_id=source_run_id,
                        raw_asset_id=raw_asset_id,
                        candidate=candidate,
                    )
                    place_source_ref_updated_count += 1
                else:
                    matched_place_id, match_confidence, match_method = self._match_existing_place(
                        connection,
                        candidate=candidate,
                    )

                    if matched_place_id is None:
                        place_id = self._insert_place(
                            connection,
                            candidate=candidate,
                        )
                        place_created_count += 1

                        place_source_ref_id = self._insert_place_source_ref(
                            connection,
                            place_id=place_id,
                            source_system_id=source_system_id,
                            source_run_id=source_run_id,
                            raw_asset_id=raw_asset_id,
                            candidate=candidate,
                            match_method="source_raw",
                            match_confidence=1.0,
                        )
                        place_source_ref_created_count += 1
                    else:
                        place_id = matched_place_id

                        self._update_place_minimally(
                            connection,
                            place_id=place_id,
                            candidate=candidate,
                        )
                        place_updated_count += 1

                        place_source_ref_id = self._insert_place_source_ref(
                            connection,
                            place_id=place_id,
                            source_system_id=source_system_id,
                            source_run_id=source_run_id,
                            raw_asset_id=raw_asset_id,
                            candidate=candidate,
                            match_method=match_method or "rule_based",
                            match_confidence=match_confidence or 0.85,
                        )
                        place_source_ref_created_count += 1

                primary_category_raw = candidate.classification.source_primary_category_raw
                if primary_category_raw:
                    category_id = self._get_or_create_category(
                        connection,
                        raw_category=primary_category_raw,
                    )
                    self._upsert_primary_place_category(
                        connection,
                        place_id=place_id,
                        category_id=category_id,
                        source_system_id=source_system_id,
                    )
                    place_category_upserted_count += 1

                neighborhood_assignment = self._resolve_neighborhood_assignment(
                    connection,
                    candidate=candidate,
                )

                if neighborhood_assignment is not None:
                    self._upsert_place_neighborhood_assignment(
                        connection,
                        place_id=place_id,
                        assignment=neighborhood_assignment,
                    )
                    place_neighborhood_assignment_upserted_count += 1
                else:
                    validation_issue_count += 1
                    self._insert_validation_issue(
                        connection,
                        source_run_id=source_run_id,
                        raw_asset_id=raw_asset_id,
                        entity_type="place",
                        entity_id=place_id,
                        issue_code="neighborhood_assignment_not_resolved",
                        issue_type="geospatial",
                        severity="warning",
                        message="No se pudo resolver una asignación geográfica para el local.",
                        expected_rule="accepted place candidates should resolve to a neighborhood",
                    )

                imported_count += 1

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

        result = OSMOverpassImportResult(
            input_count=len(candidates),
            imported_count=imported_count,
            skipped_count=skipped_count,
            place_created_count=place_created_count,
            place_updated_count=place_updated_count,
            place_source_ref_created_count=place_source_ref_created_count,
            place_source_ref_updated_count=place_source_ref_updated_count,
            place_category_upserted_count=place_category_upserted_count,
            place_neighborhood_assignment_upserted_count=place_neighborhood_assignment_upserted_count,
            validation_issue_count=validation_issue_count,
        )

        self.logger.info(
            "Importador OSM Overpass completado | imported=%s | skipped=%s | "
            "place_created=%s | place_updated=%s | "
            "source_ref_created=%s | source_ref_updated=%s",
            result.imported_count,
            result.skipped_count,
            result.place_created_count,
            result.place_updated_count,
            result.place_source_ref_created_count,
            result.place_source_ref_updated_count,
        )

        return result