from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class GeoValidationIssue:
    issue_code: str
    severity: str
    message: str
    feature_index: int | None = None
    field_name: str | None = None
    received_value: Any | None = None


@dataclass(slots=True)
class TransformedNeighborhoodRecord:
    source_feature_index: int
    source_feature_id: str | None
    official_code: str | None
    official_name: str
    normalized_name: str
    display_name: str
    district_official_code: str | None
    district_official_name: str
    district_normalized_name: str
    district_display_name: str
    geometry_geojson: dict[str, Any]
    source_properties: dict[str, Any]
    source_version: str | None = None


@dataclass(slots=True)
class TransformedDistrictGroup:
    official_code: str | None
    official_name: str
    normalized_name: str
    display_name: str
    source_geometries_geojson: list[dict[str, Any]] = field(default_factory=list)
    source_feature_indexes: list[int] = field(default_factory=list)
    source_version: str | None = None


@dataclass(slots=True)
class GeoTransformationResult:
    districts: list[TransformedDistrictGroup]
    neighborhoods: list[TransformedNeighborhoodRecord]
    issues: list[GeoValidationIssue]
    total_features: int
    accepted_features: int
    rejected_features: int


class SevillaGeoTransformer:
    """
    Transforma el raw GeoJSON de Sevilla Geo en estructuras canónicas intermedias,
    listas para una fase posterior de import a tablas district y neighborhood.

    Esta clase NO escribe en base de datos.
    """

    REQUIRED_FIELDS = ("Barrio", "DISTRITO", "DISTRITO_N")

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        text = re.sub(r"\s+", " ", text)

        return text or None

    @staticmethod
    def _normalize_name(value: str) -> str:
        text = value.strip()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        text = text.replace("_", " ")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    @staticmethod
    def _build_display_name(value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value.strip())
        return cleaned.title()

    @staticmethod
    def _clean_official_code(value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, float) and value.is_integer():
            return str(int(value))

        text = str(value).strip()
        return text or None

    @staticmethod
    def _normalize_geometry(
        geometry: dict[str, Any],
    ) -> dict[str, Any] | None:
        """
        Convierte Polygon -> MultiPolygon.
        Mantiene MultiPolygon tal cual.
        """
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")

        if geometry_type == "Polygon":
            if not isinstance(coordinates, list) or len(coordinates) == 0:
                return None

            return {
                "type": "MultiPolygon",
                "coordinates": [coordinates],
            }

        if geometry_type == "MultiPolygon":
            if not isinstance(coordinates, list) or len(coordinates) == 0:
                return None

            return geometry

        return None

    def _build_issue(
        self,
        *,
        issue_code: str,
        severity: str,
        message: str,
        feature_index: int | None = None,
        field_name: str | None = None,
        received_value: Any | None = None,
    ) -> GeoValidationIssue:
        return GeoValidationIssue(
            issue_code=issue_code,
            severity=severity,
            message=message,
            feature_index=feature_index,
            field_name=field_name,
            received_value=received_value,
        )

    def transform_feature_collection(
        self,
        payload: dict[str, Any],
        *,
        source_version: str | None = None,
    ) -> GeoTransformationResult:
        if not isinstance(payload, dict):
            raise ValueError("El payload debe ser un dict.")

        if payload.get("type") != "FeatureCollection":
            raise ValueError("El payload no es un FeatureCollection válido.")

        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("El payload no contiene una lista válida en 'features'.")

        issues: list[GeoValidationIssue] = []
        neighborhoods: list[TransformedNeighborhoodRecord] = []
        district_map: dict[str, TransformedDistrictGroup] = {}
        seen_neighborhood_keys: set[tuple[str, str]] = set()

        for feature_index, feature in enumerate(features, start=1):
            if not isinstance(feature, dict):
                issues.append(
                    self._build_issue(
                        issue_code="invalid_feature_structure",
                        severity="error",
                        message="La feature no tiene una estructura válida.",
                        feature_index=feature_index,
                    )
                )
                continue

            properties = feature.get("properties")
            geometry = feature.get("geometry")

            if not isinstance(properties, dict):
                issues.append(
                    self._build_issue(
                        issue_code="missing_properties",
                        severity="error",
                        message="La feature no contiene properties válidas.",
                        feature_index=feature_index,
                        field_name="properties",
                    )
                )
                continue

            if not isinstance(geometry, dict):
                issues.append(
                    self._build_issue(
                        issue_code="missing_geometry",
                        severity="error",
                        message="La feature no contiene geometry válida.",
                        feature_index=feature_index,
                        field_name="geometry",
                    )
                )
                continue

            missing_fields = [
                field_name
                for field_name in self.REQUIRED_FIELDS
                if self._clean_text(properties.get(field_name)) is None
            ]
            if missing_fields:
                issues.append(
                    self._build_issue(
                        issue_code="missing_required_fields",
                        severity="error",
                        message=(
                            "Faltan campos obligatorios en properties: "
                            + ", ".join(missing_fields)
                        ),
                        feature_index=feature_index,
                        field_name="properties",
                        received_value=properties,
                    )
                )
                continue

            neighborhood_name = self._clean_text(properties.get("Barrio"))
            district_code = self._clean_official_code(properties.get("DISTRITO"))
            district_name = self._clean_text(properties.get("DISTRITO_N"))
            source_feature_id = self._clean_official_code(properties.get("FID"))

            assert neighborhood_name is not None
            assert district_name is not None

            normalized_geometry = self._normalize_geometry(geometry)
            if normalized_geometry is None:
                issues.append(
                    self._build_issue(
                        issue_code="unsupported_or_invalid_geometry",
                        severity="error",
                        message=(
                            "La geometría no es válida o no está soportada. "
                            "Solo se admiten Polygon y MultiPolygon."
                        ),
                        feature_index=feature_index,
                        field_name="geometry.type",
                        received_value=geometry.get("type"),
                    )
                )
                continue

            neighborhood_normalized_name = self._normalize_name(neighborhood_name)
            district_normalized_name = self._normalize_name(district_name)

            if district_code is None:
                issues.append(
                    self._build_issue(
                        issue_code="missing_district_code",
                        severity="error",
                        message="No se ha podido derivar el código oficial del distrito.",
                        feature_index=feature_index,
                        field_name="DISTRITO",
                        received_value=properties.get("DISTRITO"),
                    )
                )
                continue

            neighborhood_unique_key = (district_code, neighborhood_normalized_name)
            if neighborhood_unique_key in seen_neighborhood_keys:
                issues.append(
                    self._build_issue(
                        issue_code="duplicate_neighborhood_within_district",
                        severity="error",
                        message=(
                            "Se ha detectado un barrio duplicado dentro del mismo distrito "
                            "tras la normalización."
                        ),
                        feature_index=feature_index,
                        field_name="Barrio",
                        received_value=neighborhood_name,
                    )
                )
                continue

            seen_neighborhood_keys.add(neighborhood_unique_key)

            neighborhood_record = TransformedNeighborhoodRecord(
                source_feature_index=feature_index,
                source_feature_id=source_feature_id,
                official_code=None,
                official_name=neighborhood_name,
                normalized_name=neighborhood_normalized_name,
                display_name=self._build_display_name(neighborhood_name),
                district_official_code=district_code,
                district_official_name=district_name,
                district_normalized_name=district_normalized_name,
                district_display_name=self._build_display_name(district_name),
                geometry_geojson=normalized_geometry,
                source_properties=properties,
                source_version=source_version,
            )
            neighborhoods.append(neighborhood_record)

            district_key = district_code
            existing_district = district_map.get(district_key)

            if existing_district is None:
                district_map[district_key] = TransformedDistrictGroup(
                    official_code=district_code,
                    official_name=district_name,
                    normalized_name=district_normalized_name,
                    display_name=self._build_display_name(district_name),
                    source_geometries_geojson=[normalized_geometry],
                    source_feature_indexes=[feature_index],
                    source_version=source_version,
                )
            else:
                if existing_district.normalized_name != district_normalized_name:
                    issues.append(
                        self._build_issue(
                            issue_code="district_name_inconsistency",
                            severity="warning",
                            message=(
                                "Se ha detectado inconsistencia de nombre de distrito "
                                "para el mismo código oficial."
                            ),
                            feature_index=feature_index,
                            field_name="DISTRITO_N",
                            received_value=district_name,
                        )
                    )

                existing_district.source_geometries_geojson.append(normalized_geometry)
                existing_district.source_feature_indexes.append(feature_index)

        districts = list(district_map.values())

        return GeoTransformationResult(
            districts=districts,
            neighborhoods=neighborhoods,
            issues=issues,
            total_features=len(features),
            accepted_features=len(neighborhoods),
            rejected_features=len(features) - len(neighborhoods),
        )