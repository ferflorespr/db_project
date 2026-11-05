"""
Phase I ETL: Parquet → PostgreSQL + PostGIS.

Reads the official dataset as-is (no business transforms). Geometry columns
arrive as EWKB hex and are inserted with ST_GeomFromEWKB (SRID 4326).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd
import psycopg
from psycopg.rows import dict_row

from ETL.config import DATA_DIR, SCHEMA_DIR, get_database_url

# FK-safe load order. Each entry: (parquet stem, table, insert SQL, column list)
# Geometry columns use ST_GeomFromEWKB(decode(%s, 'hex')).
LOAD_PLAN: list[tuple[str, str, str, list[str]]] = [
    (
        "vehicle_kind",
        "vehicle_kind",
        "INSERT INTO vehicle_kind (vehicle_kind_id, name) VALUES (%s, %s)",
        ["vehicle_kind_id", "name"],
    ),
    (
        "fuel_type",
        "fuel_type",
        "INSERT INTO fuel_type (fuel_type_id, name) VALUES (%s, %s)",
        ["fuel_type_id", "name"],
    ),
    (
        "vehicle_status",
        "vehicle_status",
        "INSERT INTO vehicle_status (vehicle_status_id, name) VALUES (%s, %s)",
        ["vehicle_status_id", "name"],
    ),
    (
        "vehicle_type",
        "vehicle_type",
        """
        INSERT INTO vehicle_type (
            vehicle_type_id, vehicle_kind_id, fuel_type_id,
            emissions_rating, created_at
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        [
            "vehicle_type_id",
            "vehicle_kind_id",
            "fuel_type_id",
            "emissions_rating",
            "created_at",
        ],
    ),
    (
        "vehicle",
        "vehicle",
        """
        INSERT INTO vehicle (
            vehicle_id, vehicle_type_id, vehicle_status_id,
            plate_number, make, model, year, created_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            "vehicle_id",
            "vehicle_type_id",
            "vehicle_status_id",
            "plate_number",
            "make",
            "model",
            "year",
            "created_at",
        ],
    ),
    (
        "driver",
        "driver",
        """
        INSERT INTO driver (
            driver_id, first_name, last_name, license_number, hired_at
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        ["driver_id", "first_name", "last_name", "license_number", "hired_at"],
    ),
    (
        "vehicle_assignment",
        "vehicle_assignment",
        """
        INSERT INTO vehicle_assignment (
            assignment_id, vehicle_id, driver_id, assigned_from, assigned_to
        ) VALUES (%s, %s, %s, %s, %s)
        """,
        [
            "assignment_id",
            "vehicle_id",
            "driver_id",
            "assigned_from",
            "assigned_to",
        ],
    ),
    (
        "location_ping",
        "location_ping",
        """
        INSERT INTO location_ping (
            ping_id, vehicle_id, ts, geom, speed_kph, heading_deg
        ) VALUES (
            %s, %s, %s,
            ST_GeomFromEWKB(decode(%s, 'hex')),
            %s, %s
        )
        """,
        ["ping_id", "vehicle_id", "ts", "geom", "speed_kph", "heading_deg"],
    ),
    (
        "trip",
        "trip",
        """
        INSERT INTO trip (
            trip_id, vehicle_id, start_ts, end_ts,
            start_geom, end_geom, distance_km
        ) VALUES (
            %s, %s, %s, %s,
            ST_GeomFromEWKB(decode(%s, 'hex')),
            ST_GeomFromEWKB(decode(%s, 'hex')),
            %s
        )
        """,
        [
            "trip_id",
            "vehicle_id",
            "start_ts",
            "end_ts",
            "start_geom",
            "end_geom",
            "distance_km",
        ],
    ),
    (
        "parking_area",
        "parking_area",
        """
        INSERT INTO parking_area (
            parking_area_id, name, capacity, geom, created_at
        ) VALUES (
            %s, %s, %s,
            ST_GeomFromEWKB(decode(%s, 'hex')),
            %s
        )
        """,
        ["parking_area_id", "name", "capacity", "geom", "created_at"],
    ),
    (
        "road_segment",
        "road_segment",
        """
        INSERT INTO road_segment (
            road_id, name, speed_limit_kph, geom,
            created_at, is_oneway, direction
        ) VALUES (
            %s, %s, %s,
            ST_GeomFromEWKB(decode(%s, 'hex')),
            %s, %s, %s
        )
        """,
        [
            "road_id",
            "name",
            "speed_limit_kph",
            "geom",
            "created_at",
            "is_oneway",
            "direction",
        ],
    ),
]

EXPECTED_COUNTS = {
    "vehicle_kind": 5,
    "fuel_type": 2,
    "vehicle_status": 2,
    "vehicle_type": 8,
    "vehicle": 30,
    "driver": 12,
    "vehicle_assignment": 42,
    "location_ping": 28041,
    "trip": 300,
    "parking_area": 224,
    "road_segment": 4086,
}


def _clean_value(value: Any) -> Any:
    """Normalize pandas nulls so psycopg writes SQL NULL."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _rows_from_parquet(path: Path, columns: Sequence[str]) -> list[tuple[Any, ...]]:
    frame = pd.read_parquet(path)
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"{path.name} missing columns: {missing}")
    rows: list[tuple[Any, ...]] = []
    for record in frame[list(columns)].itertuples(index=False, name=None):
        rows.append(tuple(_clean_value(v) for v in record))
    return rows


def apply_schema(conn: psycopg.Connection) -> None:
    for name in ("01_extensions.sql", "02_tables.sql"):
        sql_path = SCHEMA_DIR / name
        sql = sql_path.read_text(encoding="utf-8")
        print(f"  applying {sql_path.name}")
        conn.execute(sql)
    conn.commit()


def load_all(conn: psycopg.Connection, data_dir: Path, batch_size: int = 1000) -> None:
    for stem, table, insert_sql, columns in LOAD_PLAN:
        path = data_dir / f"{stem}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Missing Parquet file: {path}")
        rows = _rows_from_parquet(path, columns)
        print(f"  loading {table}: {len(rows)} rows from {path.name}")
        with conn.cursor() as cur:
            for start in range(0, len(rows), batch_size):
                chunk = rows[start : start + batch_size]
                cur.executemany(insert_sql, chunk)
        conn.commit()


def verify_counts(conn: psycopg.Connection) -> bool:
    ok = True
    with conn.cursor(row_factory=dict_row) as cur:
        for table, expected in EXPECTED_COUNTS.items():
            cur.execute(f"SELECT COUNT(*) AS n FROM {table}")
            actual = cur.fetchone()["n"]
            mark = "OK" if actual == expected else "MISMATCH"
            if actual != expected:
                ok = False
            print(f"  {table:22} expected={expected:6} actual={actual:6} [{mark}]")

        # Spot-check geometry SRIDs
        cur.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM location_ping WHERE ST_SRID(geom) <> 4326) AS bad_pings,
              (SELECT COUNT(*) FROM parking_area WHERE ST_SRID(geom) <> 4326) AS bad_parking,
              (SELECT COUNT(*) FROM road_segment WHERE ST_SRID(geom) <> 4326) AS bad_roads,
              (SELECT GeometryType(geom) FROM location_ping LIMIT 1) AS ping_type,
              (SELECT GeometryType(geom) FROM parking_area LIMIT 1) AS parking_type,
              (SELECT GeometryType(geom) FROM road_segment LIMIT 1) AS road_type
            """
        )
        geo = cur.fetchone()
        print(
            "  geometry check:",
            f"ping={geo['ping_type']}",
            f"parking={geo['parking_type']}",
            f"road={geo['road_type']}",
            f"bad_srid_rows={geo['bad_pings'] + geo['bad_parking'] + geo['bad_roads']}",
        )
        if geo["bad_pings"] or geo["bad_parking"] or geo["bad_roads"]:
            ok = False
    return ok


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Car Tracking Phase I ETL")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing the official *.parquet files",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip DROP/CREATE (only insert — usually leave this off)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only print row counts against the expected official totals",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    database_url = get_database_url()
    print(f"Connecting…")
    # sslmode is often required for Render external connections.
    with psycopg.connect(database_url, connect_timeout=30) as conn:
        if args.verify_only:
            print("Verifying row counts…")
            return 0 if verify_counts(conn) else 1

        if not args.skip_schema:
            print("Applying schema…")
            apply_schema(conn)

        print(f"Loading Parquet from {args.data_dir}…")
        load_all(conn, args.data_dir.resolve())

        print("Verifying…")
        if not verify_counts(conn):
            print("ERROR: row counts do not match the official dataset.", file=sys.stderr)
            return 1

    print("ETL finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())