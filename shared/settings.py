"""Shared configuration for the THCA Community Platform.

This module exists to keep backend + scrapers pointed at the same database file.
Override with the DATABASE_URL environment variable if desired.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Default to the scraper-populated SQLite DB so the API/Frontend can see data immediately.
DEFAULT_DB_PATH = PROJECT_ROOT / "scrapers" / "thca_platform.db"

def get_database_url() -> str:
    """Return SQLAlchemy-compatible database URL."""
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    # sqlite absolute path -> sqlite:////abs/path/to/db
    return f"sqlite:///{DEFAULT_DB_PATH.as_posix()}"
