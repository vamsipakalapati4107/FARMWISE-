"""Phase 0.5: safe, additive schema migration for the SQLite app database.

There is no migration framework (Alembic) in this project -- adding one for
a handful of nullable-column additions on a single-file SQLite dev database
would be disproportionate. Instead this script is a small, idempotent,
additive-only migrator:

  - Never drops or recreates a table.
  - Never deletes data/app.db.
  - Only ADD COLUMNs that don't already exist (checked via PRAGMA table_info,
    so re-running this is always safe -- it's a no-op once applied).
  - New tables (e.g. `plots`) are created via Base.metadata.create_all(),
    which also never touches existing tables.

Run standalone to migrate without starting the API:
    python src/migrate_db.py
It also runs automatically from db.init_db() at API startup.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

import db_models  # noqa: F401  -- registers all models (incl. Plot) on Base.metadata
from db import Base, engine

# table -> [(column_name, SQL column type), ...] to add if missing.
# Column types are plain SQLite types (SQLite is dynamically typed, so this
# matches what SQLAlchemy would have created these columns as).
ADDITIVE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "users": [
        ("selected_state", "VARCHAR"),
        ("selected_district", "VARCHAR"),
        ("selected_block", "VARCHAR"),
        ("sms_notifications_enabled", "BOOLEAN DEFAULT 1"),
        ("sms_alert_categories", "VARCHAR"),
    ],
    "farms": [
        ("latitude", "FLOAT"),
        ("longitude", "FLOAT"),
        ("boundary_geojson", "VARCHAR"),
        ("location_name", "VARCHAR"),
    ],
    "crops": [
        ("plot_id", "VARCHAR"),
    ],
}


def run_migrations() -> list[str]:
    """Returns a list of human-readable actions taken (empty if already
    up to date), so callers can log/report what happened."""
    actions: list[str] = []
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table, columns in ADDITIVE_COLUMNS.items():
            if table not in existing_tables:
                # Table doesn't exist yet at all -- create_all() below will
                # create it fresh (with these columns included), nothing to
                # ALTER here.
                continue

            existing_columns = {col["name"] for col in inspector.get_columns(table)}
            for column_name, column_type in columns:
                if column_name in existing_columns:
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}"))
                actions.append(f"ALTER TABLE {table} ADD COLUMN {column_name} {column_type}")

    # Creates any brand-new tables (e.g. `plots`) that don't exist yet.
    # This never touches tables that already exist.
    tables_before = set(inspect(engine).get_table_names())
    Base.metadata.create_all(bind=engine)
    tables_after = set(inspect(engine).get_table_names())
    for new_table in sorted(tables_after - tables_before):
        actions.append(f"CREATE TABLE {new_table}")

    return actions


if __name__ == "__main__":
    applied = run_migrations()
    if applied:
        print("Applied migrations:")
        for action in applied:
            print(f"  - {action}")
    else:
        print("Database already up to date -- no changes made.")
