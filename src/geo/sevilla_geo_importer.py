from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from src.db.database import engine
from src.geo.sevilla_geo_transformer import (
    GeoTransformationResult,
    GeoValidationIssue,
    SevillaGeoTransformer,
    TransformedDistrictGroup,
    TransformedNeighborhoodRecord,
)
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


@dataclass(slots=True)
class GeoImportResult:
    district_inserted_count: int
    district_updated_count: int
    neighborhood_inserted_count: int
    neighborhood_updated_count: int
    validation_issue_count: int
    staged_count: int
    rejected_count: int


class SevillaGeoImporter:
    """
    Importa a district y neighborhood a partir del payload GeoJSON ya validado
    y transformado por SevillaGeoTransformer.

    Esta clase:
    - transforma el payload
    - inserta/actualiza district
    - inserta/actualiza neighborhood
    - registra validation_issue
    - actualiza métricas básicas de source_run
    """

    def __init__(self) -> None:
        self.transformer = SevillaGeoTransformer()
        self.logger = logger

    @staticmethod
    def _build_district_union_geometry_sql(
        geometries: list[dict[str, Any]],
    ) -> tuple[str, dict[str, str]]:
        if not geometries:
            raise ValueError("No hay geometrías para construir el distrito.")

        values_sql_parts: list[str] = []
        params: dict[str, str] = {}

        for idx, geometry in enumerate(geometries):
            param_name = f"geom_{idx}"
            values_sql_parts.append(
                f"(ST_SetSRID(ST_GeomFromGeoJSON(:{param_name}), 4326))"
            )
            params[param_name] = json.dumps(geometry, ensure_ascii=False)

        values_sql = ", ".join(values_sql_parts)

        geometry_sql = f"""
        (
            WITH input_geoms(geom) AS (
                VALUES {values_sql}
            )
            SELECT ST_Multi(ST_UnaryUnion(ST_Collect(geom)))
            FROM input_geoms
        )
        """

        return geometry_sql, params

    @staticmethod
    def _find_existing_district_id(
        connection: Connection,
        district_group: TransformedDistrictGroup,
    ) -> str | None:
        if district_group.official_code is not None:
            query = text(
                """
                SELECT district_id
                FROM hidden_gems.district
                WHERE official_code = :official_code
                LIMIT 1
                """
            )
            result = connection.execute(
                query,
                {"official_code": district_group.official_code},
            ).scalar_one_or_none()

            if result is not None:
                return str(result)

        fallback_query = text(
            """
            SELECT district_id
            FROM hidden_gems.district
            WHERE normalized_name = :normalized_name
            LIMIT 1
            """
        )
        result = connection.execute(
            fallback_query,
            {"normalized_name": district_group.normalized_name},
        ).scalar_one_or_none()

        return str(result) if result is not None else None

    def _insert_district(
        self,
        connection: Connection,
        district_group: TransformedDistrictGroup,
    ) -> str:
        geometry_sql, geometry_params = self._build_district_union_geometry_sql(
            district_group.source_geometries_geojson
        )

        sql = text(
            f"""
            INSERT INTO hidden_gems.district (
                official_code,
                official_name,
                normalized_name,
                display_name,
                geometry,
                alias_names,
                source_version,
                is_active
            )
            VALUES (
                :official_code,
                :official_name,
                :normalized_name,
                :display_name,
                {geometry_sql},
                NULL,
                :source_version,
                TRUE
            )
            RETURNING district_id
            """
        )

        params = {
            "official_code": district_group.official_code,
            "official_name": district_group.official_name,
            "normalized_name": district_group.normalized_name,
            "display_name": district_group.display_name,
            "source_version": district_group.source_version,
            **geometry_params,
        }

        district_id = connection.execute(sql, params).scalar_one()
        return str(district_id)

    def _update_district(
        self,
        connection: Connection,
        *,
        district_id: str,
        district_group: TransformedDistrictGroup,
    ) -> None:
        geometry_sql, geometry_params = self._build_district_union_geometry_sql(
            district_group.source_geometries_geojson
        )

        sql = text(
            f"""
            UPDATE hidden_gems.district
            SET
                official_code = :official_code,
                official_name = :official_name,
                normalized_name = :normalized_name,
                display_name = :display_name,
                geometry = {geometry_sql},
                source_version = COALESCE(:source_version, source_version),
                is_active = TRUE
            WHERE district_id = :district_id
            """
        )

        params = {
            "district_id": district_id,
            "official_code": district_group.official_code,
            "official_name": district_group.official_name,
            "normalized_name": district_group.normalized_name,
            "display_name": district_group.display_name,
            "source_version": district_group.source_version,
            **geometry_params,
        }

        connection.execute(sql, params)

    @staticmethod
    def _find_existing_neighborhood_id(
        connection: Connection,
        *,
        district_id: str,
        normalized_name: str,
    ) -> str | None:
        query = text(
            """
            SELECT neighborhood_id
            FROM hidden_gems.neighborhood
            WHERE district_id = :district_id
              AND normalized_name = :normalized_name
            LIMIT 1
            """
        )

        result = connection.execute(
            query,
            {
                "district_id": district_id,
                "normalized_name": normalized_name,
            },
        ).scalar_one_or_none()

        return str(result) if result is not None else None

    @staticmethod
    def _insert_neighborhood(
        connection: Connection,
        *,
        district_id: str,
        neighborhood: TransformedNeighborhoodRecord,
    ) -> str:
        sql = text(
            """
            INSERT INTO hidden_gems.neighborhood (
                district_id,
                official_code,
                official_name,
                normalized_name,
                display_name,
                geometry,
                alias_names,
                source_version,
                is_active
            )
            VALUES (
                :district_id,
                :official_code,
                :official_name,
                :normalized_name,
                :display_name,
                ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry_geojson), 4326)),
                NULL,
                :source_version,
                TRUE
            )
            RETURNING neighborhood_id
            """
        )

        params = {
            "district_id": district_id,
            "official_code": neighborhood.official_code,
            "official_name": neighborhood.official_name,
            "normalized_name": neighborhood.normalized_name,
            "display_name": neighborhood.display_name,
            "geometry_geojson": json.dumps(
                neighborhood.geometry_geojson,
                ensure_ascii=False,
            ),
            "source_version": neighborhood.source_version,
        }

        neighborhood_id = connection.execute(sql, params).scalar_one()
        return str(neighborhood_id)

    @staticmethod
    def _update_neighborhood(
        connection: Connection,
        *,
        neighborhood_id: str,
        district_id: str,
        neighborhood: TransformedNeighborhoodRecord,
    ) -> None:
        sql = text(
            """
            UPDATE hidden_gems.neighborhood
            SET
                district_id = :district_id,
                official_code = :official_code,
                official_name = :official_name,
                normalized_name = :normalized_name,
                display_name = :display_name,
                geometry = ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(:geometry_geojson), 4326)),
                source_version = COALESCE(:source_version, source_version),
                is_active = TRUE
            WHERE neighborhood_id = :neighborhood_id
            """
        )

        params = {
            "neighborhood_id": neighborhood_id,
            "district_id": district_id,
            "official_code": neighborhood.official_code,
            "official_name": neighborhood.official_name,
            "normalized_name": neighborhood.normalized_name,
            "display_name": neighborhood.display_name,
            "geometry_geojson": json.dumps(
                neighborhood.geometry_geojson,
                ensure_ascii=False,
            ),
            "source_version": neighborhood.source_version,
        }

        connection.execute(sql, params)

    @staticmethod
    def _map_issue_type(issue: GeoValidationIssue) -> str:
        if issue.severity == "warning":
            return "quality"
        return "validation"

    def _insert_validation_issues(
        self,
        connection: Connection,
        *,
        source_run_id: str,
        raw_asset_id: str | None,
        issues: list[GeoValidationIssue],
    ) -> int:
        if not issues:
            return 0

        insert_sql = text(
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
                received_value
            )
            VALUES (
                :source_run_id,
                :raw_asset_id,
                'raw_asset',
                NULL,
                :issue_code,
                :issue_type,
                :severity,
                :message,
                :field_name,
                :received_value
            )
            """
        )

        inserted = 0

        for issue in issues:
            message = issue.message
            if issue.feature_index is not None:
                message = f"[feature_index={issue.feature_index}] {message}"

            connection.execute(
                insert_sql,
                {
                    "source_run_id": source_run_id,
                    "raw_asset_id": raw_asset_id,
                    "issue_code": issue.issue_code,
                    "issue_type": self._map_issue_type(issue),
                    "severity": issue.severity,
                    "message": message,
                    "field_name": issue.field_name,
                    "received_value": (
                        json.dumps(issue.received_value, ensure_ascii=False, default=str)
                        if issue.received_value is not None
                        else None
                    ),
                },
            )
            inserted += 1

        return inserted

    @staticmethod
    def _update_source_run_counts(
        connection: Connection,
        *,
        source_run_id: str,
        staged_count: int,
        rejected_count: int,
        issues: list[GeoValidationIssue],
    ) -> None:
        warning_count = sum(1 for issue in issues if issue.severity == "warning")
        error_count = sum(
            1 for issue in issues if issue.severity in {"error", "critical"}
        )

        sql = text(
            """
            UPDATE hidden_gems.source_run
            SET
                records_staged_count = :staged_count,
                records_rejected_count = :rejected_count,
                warning_count = warning_count + :warning_count,
                error_count = error_count + :error_count
            WHERE source_run_id = :source_run_id
            """
        )

        connection.execute(
            sql,
            {
                "source_run_id": source_run_id,
                "staged_count": staged_count,
                "rejected_count": rejected_count,
                "warning_count": warning_count,
                "error_count": error_count,
            },
        )

    def import_payload(
        self,
        *,
        payload: dict[str, Any],
        source_run_id: str,
        raw_asset_id: str | None = None,
        source_version: str | None = None,
    ) -> GeoImportResult:
        transformed = self.transformer.transform_feature_collection(
            payload,
            source_version=source_version,
        )

        district_inserted_count = 0
        district_updated_count = 0
        neighborhood_inserted_count = 0
        neighborhood_updated_count = 0

        with engine.begin() as connection:
            district_id_by_code: dict[str, str] = {}

            for district_group in transformed.districts:
                existing_district_id = self._find_existing_district_id(
                    connection,
                    district_group,
                )

                if existing_district_id is None:
                    district_id = self._insert_district(connection, district_group)
                    district_inserted_count += 1
                else:
                    self._update_district(
                        connection,
                        district_id=existing_district_id,
                        district_group=district_group,
                    )
                    district_id = existing_district_id
                    district_updated_count += 1

                if district_group.official_code is not None:
                    district_id_by_code[district_group.official_code] = district_id

            for neighborhood in transformed.neighborhoods:
                district_id = district_id_by_code.get(neighborhood.district_official_code)
                if district_id is None:
                    transformed.issues.append(
                        GeoValidationIssue(
                            issue_code="district_not_resolved_for_neighborhood",
                            severity="error",
                            message=(
                                "No se ha podido resolver district_id para el barrio "
                                "durante el import."
                            ),
                            feature_index=neighborhood.source_feature_index,
                            field_name="DISTRITO",
                            received_value=neighborhood.district_official_code,
                        )
                    )
                    continue

                existing_neighborhood_id = self._find_existing_neighborhood_id(
                    connection,
                    district_id=district_id,
                    normalized_name=neighborhood.normalized_name,
                )

                if existing_neighborhood_id is None:
                    self._insert_neighborhood(
                        connection,
                        district_id=district_id,
                        neighborhood=neighborhood,
                    )
                    neighborhood_inserted_count += 1
                else:
                    self._update_neighborhood(
                        connection,
                        neighborhood_id=existing_neighborhood_id,
                        district_id=district_id,
                        neighborhood=neighborhood,
                    )
                    neighborhood_updated_count += 1

            validation_issue_count = self._insert_validation_issues(
                connection,
                source_run_id=source_run_id,
                raw_asset_id=raw_asset_id,
                issues=transformed.issues,
            )

            self._update_source_run_counts(
                connection,
                source_run_id=source_run_id,
                staged_count=transformed.accepted_features,
                rejected_count=transformed.rejected_features,
                issues=transformed.issues,
            )

        result = GeoImportResult(
            district_inserted_count=district_inserted_count,
            district_updated_count=district_updated_count,
            neighborhood_inserted_count=neighborhood_inserted_count,
            neighborhood_updated_count=neighborhood_updated_count,
            validation_issue_count=validation_issue_count,
            staged_count=transformed.accepted_features,
            rejected_count=transformed.rejected_features,
        )

        self.logger.info(
            "Import Sevilla Geo completado | "
            "district_inserted=%s | district_updated=%s | "
            "neighborhood_inserted=%s | neighborhood_updated=%s | "
            "issues=%s",
            result.district_inserted_count,
            result.district_updated_count,
            result.neighborhood_inserted_count,
            result.neighborhood_updated_count,
            result.validation_issue_count,
        )

        return result