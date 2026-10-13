"""
Schema migration, safe to run any number of times.

Creates every missing table (including administrators and the v3 tables) and
adds missing columns with ADD COLUMN IF NOT EXISTS; it never drops or rewrites
data. Running it twice leaves the schema unchanged.

Usage (from backend/): python -m src.migrate
"""

from src.db import DB_NAME, create_all_tables, create_database_if_missing


def migrate():
    created = create_database_if_missing(DB_NAME)
    create_all_tables()
    return created


if __name__ == "__main__":
    print(f"Database {DB_NAME}: {'created' if migrate() else 'already existed'}; schema up to date.")
