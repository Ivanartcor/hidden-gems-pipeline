from sqlalchemy import create_engine
from src.config.settings import settings


DATABASE_URL = (
    f"postgresql+psycopg2://{settings.pguser}:{settings.pgpassword}"
    f"@{settings.pghost}:{settings.pgport}/{settings.pgdatabase}"
)

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)