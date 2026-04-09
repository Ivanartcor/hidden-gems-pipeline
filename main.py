from src.config.settings import settings
from src.db.database import check_db_connection
from src.utils.logging_config import setup_logger


def main() -> int:
    settings.ensure_directories()
    logger = setup_logger()

    logger.info(
        "Iniciando %s | env=%s | schema=%s",
        settings.app_name,
        settings.app_env,
        settings.pgschema,
    )

    try:
        check_db_connection()
        logger.info("Conexión a PostgreSQL verificada correctamente.")
    except Exception:
        logger.exception("No se pudo verificar la conexión con la base de datos.")
        return 1

    logger.info("Pipeline base listo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())