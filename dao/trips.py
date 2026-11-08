from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class Trip(BaseModel):
    trip_id: Optional[int] = None
    vehicle_id: int
    start_ts: Optional[datetime] = None
    end_ts: Optional[datetime] = None
    distance_km: Optional[float] = None
    start_geom_json: Optional[str] = None
    end_geom_json: Optional[str] = None


class TripDao:
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

    def get_all_trips(self) -> list[Trip]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT trip_id, vehicle_id, start_ts, end_ts, distance_km,
                               ST_AsGeoJSON(start_geom) AS start_geom_json,
                               ST_AsGeoJSON(end_geom) AS end_geom_json
                        FROM trip
                        ORDER BY trip_id
                        """
                    )
                    return [Trip(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_trips(
        self,
        *,
        limit: int,
        offset: int,
        vehicle_id: Optional[int] = None,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> tuple[list[Trip], int]:
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
                        where.append("start_ts >= %s")
                        params.append(from_ts)
                    if to_ts:
                        where.append("end_ts <= %s")
                        params.append(to_ts)
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(f"SELECT COUNT(*) AS n FROM trip{where_sql}", params)
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT trip_id, vehicle_id, start_ts, end_ts, distance_km
                        FROM trip
                        {where_sql}
                        ORDER BY start_ts, trip_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [Trip(**dict(row)) for row in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_trip_by_id(self, trip_id: int) -> Optional[Trip]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT trip_id, vehicle_id, start_ts, end_ts, distance_km,
                               ST_AsGeoJSON(start_geom) AS start_geom_json,
                               ST_AsGeoJSON(end_geom) AS end_geom_json
                        FROM trip
                        WHERE trip_id = %s
                        """,
                        (trip_id,),
                    )
                    row = cursor.fetchone()
                    return Trip(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def create_trip(
        self,
        trip: Trip,
        start_geom_json: Optional[str] = None,
        end_geom_json: Optional[str] = None,
    ) -> int:
        query = """
            INSERT INTO trip (
                vehicle_id, start_ts, end_ts, start_geom, end_geom, distance_km
            )
            VALUES (
                %(vehicle_id)s, %(start_ts)s, %(end_ts)s,
                CASE WHEN %(start_geom_json)s IS NULL THEN NULL
                     ELSE ST_SetSRID(ST_GeomFromGeoJSON(%(start_geom_json)s), 4326) END,
                CASE WHEN %(end_geom_json)s IS NULL THEN NULL
                     ELSE ST_SetSRID(ST_GeomFromGeoJSON(%(end_geom_json)s), 4326) END,
                %(distance_km)s
            )
            RETURNING trip_id
        """
        data = trip.model_dump(exclude={"trip_id", "start_geom_json", "end_geom_json"})
        data["start_geom_json"] = start_geom_json
        data["end_geom_json"] = end_geom_json
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_trip(
        self,
        trip: Trip,
        start_geom_json: Optional[str] = None,
        end_geom_json: Optional[str] = None,
        update_start_geom: bool = False,
        update_end_geom: bool = False,
    ) -> bool:
        sets = [
            "vehicle_id = %(vehicle_id)s",
            "start_ts = %(start_ts)s",
            "end_ts = %(end_ts)s",
            "distance_km = %(distance_km)s",
        ]
        data = trip.model_dump()
        if update_start_geom:
            sets.append(
                "start_geom = CASE WHEN %(start_geom_json)s IS NULL THEN NULL "
                "ELSE ST_SetSRID(ST_GeomFromGeoJSON(%(start_geom_json)s), 4326) END"
            )
            data["start_geom_json"] = start_geom_json
        if update_end_geom:
            sets.append(
                "end_geom = CASE WHEN %(end_geom_json)s IS NULL THEN NULL "
                "ELSE ST_SetSRID(ST_GeomFromGeoJSON(%(end_geom_json)s), 4326) END"
            )
            data["end_geom_json"] = end_geom_json
        query = f"""
            UPDATE trip
            SET {", ".join(sets)}
            WHERE trip_id = %(trip_id)s
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_trip(self, trip_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM trip WHERE trip_id = %s",
                        (trip_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
