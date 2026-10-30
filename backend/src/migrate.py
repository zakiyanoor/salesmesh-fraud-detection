"""
Schema migration, safe to run any number of times.

Creates every missing table (including administrators and the v3 tables) and
adds missing columns with ADD COLUMN IF NOT EXISTS; it never drops or rewrites
data. Running it twice leaves the schema unchanged. With DB_CREATE_DATABASE=false
(a managed database that already exists) it does not try to create the database.

Usage (from backend/): python -m src.migrate
"""

from src.db import DB_CREATE_DATABASE, DB_NAME, create_all_tables, create_database_if_missing


def migrate(create_database=DB_CREATE_DATABASE):
    created = create_database_if_missing(DB_NAME) if create_database else False
    create_all_tables()
    return created


if __name__ == "__main__":
    created = migrate()
    state = "created" if created else "already existed" if DB_CREATE_DATABASE else "used as it is (DB_CREATE_DATABASE=false)"
    print(f"Database {DB_NAME}: {state}; schema up to date.")
