from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class LocationPing(BaseModel):
    ping_id: Optional[int] = None
    vehicle_id: int
    ts: Optional[datetime] = None
    speed_kph: Optional[float] = None
    heading_deg: Optional[float] = None
    geom_json: Optional[str] = None


class LocationPingDao:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            POOL_CONFIG["minconn"],
            POOL_CONFIG["maxconn"],
            **PG_DB_CONFIG,
        )

    def vehicle_exists(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM vehicle WHERE vehicle_id = %s",
                        (vehicle_id,),
                    )
                    return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

    def get_all_location_pings(self) -> list[LocationPing]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM location_ping
                        ORDER BY ping_id
                        """
                    )
                    return [LocationPing(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_location_pings(
        self,
        *,
        limit: int,
        offset: int,
        vehicle_id: Optional[int] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
        bbox: Optional[tuple[float, float, float, float]] = None,
    ) -> tuple[list[LocationPing], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if vehicle_id is not None:
                        where.append("vehicle_id = %s")
                        params.append(vehicle_id)
                    if from_ts:
                        where.append("ts >= %s")
                        params.append(from_ts)
                    if to_ts:
                        where.append("ts <= %s")
                        params.append(to_ts)
                    if bbox:
                        where.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                        params.extend(bbox)
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM location_ping{where_sql}", params
                    )
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM location_ping
                        {where_sql}
                        ORDER BY ts, ping_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [LocationPing(**dict(row)) for row in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_location_ping_by_id(self, ping_id: int) -> Optional[LocationPing]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM location_ping
                        WHERE ping_id = %s
                        """,
                        (ping_id,),
                    )
                    row = cursor.fetchone()
                    return LocationPing(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def create_location_ping(self, ping: LocationPing, geom_json: str) -> int:
        query = """
            INSERT INTO location_ping (vehicle_id, ts, geom, speed_kph, heading_deg)
            VALUES (
                %(vehicle_id)s, %(ts)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326),
                %(speed_kph)s, %(heading_deg)s
            )
            RETURNING ping_id
        """
        data = ping.model_dump(exclude={"ping_id", "geom_json"})
        data["geom_json"] = geom_json
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_location_ping(
        self, ping: LocationPing, geom_json: Optional[str] = None
    ) -> bool:
        if geom_json is None:
            query = """
                UPDATE location_ping
                SET vehicle_id = %(vehicle_id)s,
                    ts = %(ts)s,
                    speed_kph = %(speed_kph)s,
                    heading_deg = %(heading_deg)s
                WHERE ping_id = %(ping_id)s
            """
            data = ping.model_dump()
        else:
            query = """
                UPDATE location_ping
                SET vehicle_id = %(vehicle_id)s,
                    ts = %(ts)s,
                    speed_kph = %(speed_kph)s,
                    heading_deg = %(heading_deg)s,
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326)
                WHERE ping_id = %(ping_id)s
            """
            data = ping.model_dump()
            data["geom_json"] = geom_json
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_location_ping(self, ping_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM location_ping WHERE ping_id = %s",
                        (ping_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
