import os
from pathlib import Path
from dotenv import load_dotenv

# Render environment variables take precedence over a local .env file.
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

POOL_CONFIG = {
    "minconn": int(os.getenv("DB_POOL_MIN", "1")),
    "maxconn": int(os.getenv("DB_POOL_MAX", "5")),
}
if not 1 <= POOL_CONFIG["minconn"] <= POOL_CONFIG["maxconn"]:
    raise ValueError("Require 1 <= DB_POOL_MIN <= DB_POOL_MAX")

database_url = os.getenv("DATABASE_URL", "").strip()
if database_url:
    PG_DB_CONFIG = {"dsn": database_url, "connect_timeout": 10}
else:
    if os.getenv("RENDER"):
        raise RuntimeError("Set DATABASE_URL in the Render web service environment")
    # Preserve the project's existing local Docker defaults.
    PG_DB_CONFIG = {
        "dbname": os.getenv("PGDATABASE", "dbspring26"),
        "user": os.getenv("PGUSER", "dbuser"),
        "password": os.getenv("PGPASSWORD", "dbspring26"),
        "host": os.getenv("PGHOST", "localhost"),
        "port": int(os.getenv("PGPORT", "8981")),
        "connect_timeout": 10,
    }
