from sqlalchemy import text
from src.db.database import engine


def main():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_schema(), version();"))
        row = result.fetchone()
        print("Conexión OK:", row)


if __name__ == "__main__":
    main()