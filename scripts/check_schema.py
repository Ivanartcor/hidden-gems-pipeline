from sqlalchemy import text
from src.db.database import engine

EXPECTED_TABLES = {
    "source_system",
    "source_run",
    "raw_asset",
    "district",
    "neighborhood",
    "place",
    "place_source_ref",
    "review",
    "category",
    "place_category",
    "place_neighborhood_assignment",
    "validation_issue",
}

def main():
    query = text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'hidden_gems'
    """)

    with engine.connect() as conn:
        result = conn.execute(query)
        existing_tables = {row[0] for row in result}

    missing_tables = EXPECTED_TABLES - existing_tables

    print("Tablas encontradas:")
    for table in sorted(existing_tables):
        print(f" - {table}")

    if missing_tables:
        print("\nFaltan tablas:")
        for table in sorted(missing_tables):
            print(f" - {table}")
        raise SystemExit(1)

    print("\nSchema OK: todas las tablas esperadas existen.")

if __name__ == "__main__":
    main()