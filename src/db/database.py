from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import settings


DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=settings.pguser,
    password=settings.pgpassword,
    host=settings.pghost,
    port=settings.pgport,
    database=settings.pgdatabase,
)

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    echo=settings.db_echo,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_engine() -> Engine:
    return engine


def get_session() -> Session:
    return SessionLocal()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_db_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))