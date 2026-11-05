from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Repo root: .../ETL/config.py → parent.parent
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data")).resolve()
SCHEMA_DIR = Path(os.getenv("SCHEMA_DIR", ROOT_DIR / "schema")).resolve()

# Prefer .env in the repo root; override with real env if already set.
load_dotenv(ROOT_DIR / ".env")


def get_database_url() -> str:
    """Return the Postgres connection string or raise a clear error."""
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill in "
            "your Render (or Docker) connection string."
        )
    # Render external URLs often use postgres://; psycopg accepts postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url