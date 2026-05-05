from __future__ import annotations

from src.normalization.base_place_candidate_importer import (
    BasePlaceCandidateImporter,
    PlaceCandidateImportResult,
)


GooglePlacesImportResult = PlaceCandidateImportResult


class GooglePlacesImporter(BasePlaceCandidateImporter):
    """
    Importador de candidatos deduplicados de Google Places hacia:
    - place
    - place_source_ref
    - place_category
    - place_neighborhood_assignment

    La lógica común vive en BasePlaceCandidateImporter.
    Esta clase solo define la configuración específica de Google Places.
    """

    SOURCE_CODE = "google_places"
    SOURCE_LABEL = "Google Places"
    SOURCE_ENTITY_TYPE_LABEL = "place_source_ref"

    CATEGORY_ASSIGNMENT_NOTE = "Asignación primaria derivada desde Google Places."
    NEIGHBORHOOD_ASSIGNMENT_NOTE = "Asignación automática derivada desde Google Places."