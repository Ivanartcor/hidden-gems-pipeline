from __future__ import annotations

from src.normalization.osm_overpass_importer import (
    OSMOverpassImporter,
    OSMOverpassImportResult,
)


class GooglePlacesImporter(OSMOverpassImporter):
    """
    Importador inicial de candidatos deduplicados de Google Places.

    Reutiliza la lógica canónica ya validada en OSMOverpassImporter:

    - búsqueda de source_system
    - detección de place_source_ref existente
    - matching básico contra place por nombre + distancia
    - creación/actualización de place
    - creación/actualización de place_source_ref
    - upsert de category/place_category
    - asignación geográfica por barrio
    - registro de validation_issue

    La diferencia principal está en SOURCE_CODE, que hace que el importador
    opere contra source_system = google_places.

    Sí, esto es pequeño a propósito. Para esta primera fase es lo más seguro
    porque reutiliza la lógica ya funcional. Más adelante, cuando refinemos 
    Google Places, podremos extraer un BasePlaceImporter genérico y dejar 
    Overpass/Google como especializaciones limpias.
    """

    SOURCE_CODE = "google_places"