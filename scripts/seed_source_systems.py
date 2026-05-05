from sqlalchemy import text

from src.db.database import engine
from src.utils.logging_config import setup_logger


logger = setup_logger(__name__)


SEED_SOURCES = [
    {
        "source_code": "osm_overpass",
        "source_name": "OSM / Overpass",
        "source_type": "api",
        "description": "Fuente abierta para POIs y enriquecimiento espacial.",
        "base_url": "https://overpass-api.de/",
        "auth_type": "none",
        "data_format_default": "json",
        "refresh_mode_default": "full_refresh",
        "supports_incremental": True,
        "is_active": True,
        "notes": "Fuente libre para primeras pruebas del pipeline.",
    },
    {
        "source_code": "sevilla_geo",
        "source_name": "Sevilla Geo",
        "source_type": "geo_dataset",
        "description": "Capas geográficas oficiales de distritos y barrios de Sevilla.",
        "base_url": None,
        "auth_type": "none",
        "data_format_default": "geojson",
        "refresh_mode_default": "manual_snapshot",
        "supports_incremental": False,
        "is_active": True,
        "notes": "Dataset geográfico oficial de referencia.",
    },
    {
        "source_code": "yelp_open_dataset",
        "source_name": "Yelp Open Dataset",
        "source_type": "bulk_dataset",
        "description": "Snapshot de apoyo para NLP y pruebas de pipeline.",
        "base_url": None,
        "auth_type": "none",
        "data_format_default": "json",
        "refresh_mode_default": "manual_snapshot",
        "supports_incremental": False,
        "is_active": True,
        "notes": "Dataset libre de apoyo para pruebas y procesamiento textual.",
    },

    # De momento lo dejamos fuera para no mezclar aún fuentes con API key.
    # Cuando toque activarlo, basta con descomentar este bloque.
    
    {
        "source_code": "google_places",
        "source_name": "Google Places",
        "source_type": "api",
        "description": "Fuente dinámica para enriquecimiento y consolidación de locales gastronómicos.",
        "base_url": "https://places.googleapis.com/v1",
        "auth_type": "api_key",
        "data_format_default": "json",
        "refresh_mode_default": "incremental",
        "supports_incremental": True,
        "is_active": True,
        "notes": "Fuente activada para la vertical Google Places con Places API New.",
    },
]


UPSERT_SQL = text(
    """
    INSERT INTO hidden_gems.source_system (
        source_code,
        source_name,
        source_type,
        description,
        base_url,
        auth_type,
        data_format_default,
        refresh_mode_default,
        supports_incremental,
        is_active,
        notes
    )
    VALUES (
        :source_code,
        :source_name,
        :source_type,
        :description,
        :base_url,
        :auth_type,
        :data_format_default,
        :refresh_mode_default,
        :supports_incremental,
        :is_active,
        :notes
    )
    ON CONFLICT (source_code) DO UPDATE
    SET
        source_name = EXCLUDED.source_name,
        source_type = EXCLUDED.source_type,
        description = EXCLUDED.description,
        base_url = EXCLUDED.base_url,
        auth_type = EXCLUDED.auth_type,
        data_format_default = EXCLUDED.data_format_default,
        refresh_mode_default = EXCLUDED.refresh_mode_default,
        supports_incremental = EXCLUDED.supports_incremental,
        is_active = EXCLUDED.is_active,
        notes = EXCLUDED.notes,
        updated_at = NOW()
    """
)


def seed_source_systems() -> None:
    logger.info("Iniciando seed de source_system...")

    with engine.begin() as connection:
        for source in SEED_SOURCES:
            connection.execute(UPSERT_SQL, source)
            logger.info("Fuente registrada/actualizada: %s", source["source_code"])

    logger.info("Seed de source_system finalizado correctamente.")


if __name__ == "__main__":
    seed_source_systems()