from __future__ import annotations

from src.normalization.base_place_candidate_importer import (
    BasePlaceCandidateImporter,
    PlaceCandidateImportResult,
)


OSMOverpassImportResult = PlaceCandidateImportResult


class OSMOverpassImporter(BasePlaceCandidateImporter):
    """
    Importador de candidatos deduplicados de OSM Overpass hacia:
    - place
    - place_source_ref
    - place_category
    - place_neighborhood_assignment

    La lógica común vive en BasePlaceCandidateImporter.
    Esta clase solo define la configuración específica de la fuente OSM.
    """

    SOURCE_CODE = "osm_overpass"
    SOURCE_LABEL = "OSM Overpass"
    SOURCE_ENTITY_TYPE_LABEL = "place_source_ref"

    CATEGORY_ASSIGNMENT_NOTE = "Asignación primaria derivada desde OSM Overpass."
    NEIGHBORHOOD_ASSIGNMENT_NOTE = "Asignación automática derivada desde OSM Overpass."