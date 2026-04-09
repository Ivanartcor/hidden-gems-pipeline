from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from src.connectors.base import BaseConnector


class SevillaGeoConnector(BaseConnector):
    source_code = "sevilla_geo"

    @staticmethod
    def _normalize_file_format(file_format: str) -> str:
        normalized = file_format.lower().lstrip(".")
        if normalized not in {"geojson", "json"}:
            raise ValueError(
                "Este conector solo soporta por ahora ficheros GeoJSON/JSON."
            )
        return normalized

    @staticmethod
    def _infer_file_format_from_path(file_path: Path) -> str:
        suffix = file_path.suffix.lower().lstrip(".")
        return SevillaGeoConnector._normalize_file_format(suffix)

    @staticmethod
    def _infer_file_format_from_url(download_url: str) -> str:
        parsed = urlparse(download_url)
        suffix = Path(parsed.path).suffix.lower().lstrip(".")
        return SevillaGeoConnector._normalize_file_format(suffix or "geojson")

    @staticmethod
    def _decode_json_bytes(content: bytes) -> dict[str, Any]:
        try:
            return json.loads(content.decode("utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ValueError("El fichero no contiene un JSON/GeoJSON válido.") from exc

    @staticmethod
    def _validate_feature_collection(payload: dict[str, Any]) -> list[str]:
        warnings: list[str] = []

        if not isinstance(payload, dict):
            raise ValueError("El contenido del dataset no es un objeto JSON válido.")

        if payload.get("type") != "FeatureCollection":
            raise ValueError(
                "El GeoJSON recibido no tiene type='FeatureCollection'."
            )

        features = payload.get("features")
        if not isinstance(features, list):
            raise ValueError("El GeoJSON no contiene una lista válida en 'features'.")

        if len(features) == 0:
            raise ValueError("El GeoJSON no contiene features.")

        geometry_types: set[str] = set()

        for index, feature in enumerate(features, start=1):
            if not isinstance(feature, dict):
                warnings.append(f"Feature {index}: estructura no válida.")
                continue

            geometry = feature.get("geometry")
            if geometry is None:
                warnings.append(f"Feature {index}: geometry ausente.")
                continue

            if not isinstance(geometry, dict):
                warnings.append(f"Feature {index}: geometry no válida.")
                continue

            geometry_type = geometry.get("type")
            if geometry_type:
                geometry_types.add(geometry_type)

        unexpected_geometry_types = sorted(
            gtype for gtype in geometry_types if gtype not in {"Polygon", "MultiPolygon"}
        )

        if unexpected_geometry_types:
            warnings.append(
                "Se han encontrado geometrías no esperadas para capas territoriales: "
                + ", ".join(unexpected_geometry_types)
            )

        return warnings

    @staticmethod
    def _summarize_geojson(payload: dict[str, Any]) -> dict[str, Any]:
        features = payload.get("features", [])

        geometry_types = sorted(
            {
                feature.get("geometry", {}).get("type")
                for feature in features
                if isinstance(feature, dict)
                and isinstance(feature.get("geometry"), dict)
                and feature.get("geometry", {}).get("type")
            }
        )

        property_keys: set[str] = set()
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties")
            if isinstance(properties, dict):
                property_keys.update(properties.keys())

        return {
            "feature_count": len(features),
            "geometry_types": geometry_types,
            "property_keys_sample": sorted(property_keys)[:25],
        }

    @staticmethod
    def _build_asset_name(layer_name: str, source_version: str | None) -> str:
        if source_version:
            return f"sevilla_geo_{layer_name}_{source_version}"
        return f"sevilla_geo_{layer_name}"

    @staticmethod
    def _read_local_file(file_path: Path) -> bytes:
        if not file_path.exists():
            raise FileNotFoundError(f"No existe el fichero: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"La ruta no apunta a un fichero válido: {file_path}")

        return file_path.read_bytes()

    def _download_file(self, download_url: str) -> bytes:
        response = self.request(
            method="GET",
            url=download_url,
            headers={"Accept": "application/geo+json, application/json, */*"},
        )
        return response.content

    def run(
        self,
        *,
        layer_name: str,
        local_file_path: str | Path | None = None,
        download_url: str | None = None,
        source_version: str | None = None,
        trigger_type: str = "cli",
    ) -> dict[str, Any]:
        if bool(local_file_path) == bool(download_url):
            raise ValueError(
                "Debes indicar exactamente uno de estos parámetros: "
                "'local_file_path' o 'download_url'."
            )

        normalized_layer_name = layer_name.strip().lower()
        if normalized_layer_name not in {"district", "neighborhood"}:
            raise ValueError(
                "layer_name debe ser 'district' o 'neighborhood'."
            )

        request_summary = self.build_request_summary(
            layer_name=normalized_layer_name,
            local_file_path=str(local_file_path) if local_file_path else None,
            download_url=download_url,
            source_version=source_version,
        )
        request_signature_hash = self.build_request_signature(request_summary)

        run_context = self.start_run(
            run_type="manual_import",
            trigger_type=trigger_type,
            request_summary=request_summary,
            notes=(
                "Ingesta raw de dataset geográfico de Sevilla "
                f"para la capa {normalized_layer_name}."
            ),
        )

        try:
            if local_file_path is not None:
                file_path = Path(local_file_path)
                file_format = self._infer_file_format_from_path(file_path)
                raw_content = self._read_local_file(file_path)
                origin_note = f"origen=local:{file_path}"
            else:
                assert download_url is not None
                file_format = self._infer_file_format_from_url(download_url)
                raw_content = self._download_file(download_url)
                origin_note = f"origen=url:{download_url}"

            payload = self._decode_json_bytes(raw_content)
            warnings = self._validate_feature_collection(payload)
            summary = self._summarize_geojson(payload)

            raw_asset = self.save_raw_bytes(
                run_context=run_context,
                asset_name=self._build_asset_name(
                    normalized_layer_name,
                    source_version,
                ),
                content=raw_content,
                file_format=file_format,
                asset_type="geo_file",
                mime_type="application/geo+json",
                query_name=normalized_layer_name,
                request_signature_hash=request_signature_hash,
                notes=(
                    f"Dataset geográfico de Sevilla | "
                    f"layer={normalized_layer_name} | "
                    f"{origin_note}"
                ),
            )

            self.complete_run(
                run_context,
                records_extracted_count=summary["feature_count"],
                records_staged_count=0,
                records_rejected_count=0,
                warning_count=len(warnings),
                notes=(
                    "Dataset geográfico de Sevilla ingestado correctamente en raw. "
                    f"layer={normalized_layer_name}"
                ),
            )

            self.logger.info(
                "Sevilla geo ingestado | layer=%s | feature_count=%s",
                normalized_layer_name,
                summary["feature_count"],
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
                    f"Error en ingesta de Sevilla Geo "
                    f"(layer={normalized_layer_name}): {exc}"
                ),
            )
            raise