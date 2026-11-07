from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class Vehicle(BaseModel):
    vehicle_id: Optional[int] = None
    vehicle_type_id: int
    vehicle_status_id: int
    plate_number: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    created_at: Optional[datetime] = None


class VehicleDao:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            POOL_CONFIG["minconn"],
            POOL_CONFIG["maxconn"],
            **PG_DB_CONFIG,
        )

    def get_all_vehicles(self) -> list[Vehicle]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM vehicle ORDER BY vehicle_id"
                    )
                    return [Vehicle(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_vehicles(
        self,
        *,
        limit: int,
        offset: int,
        status: Optional[str] = None,
        plate_number: Optional[str] = None,
    ) -> tuple[list[Vehicle], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if status:
                        if status.isdigit():
                            where.append("v.vehicle_status_id = %s")
                            params.append(int(status))
                        else:
                            where.append(
                                "EXISTS (SELECT 1 FROM vehicle_status vs "
                                "WHERE vs.vehicle_status_id = v.vehicle_status_id "
                                "AND LOWER(vs.name) = LOWER(%s))"
                            )
                            params.append(status)
                    if plate_number:
                        where.append("v.plate_number ILIKE %s")
                        params.append(f"%{plate_number}%")
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM vehicle v{where_sql}", params
                    )
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT v.* FROM vehicle v
                        {where_sql}
                        ORDER BY v.vehicle_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    items = [Vehicle(**dict(row)) for row in cursor.fetchall()]
                    return items, count
        finally:
            self.pool.putconn(conn)

    def get_vehicle_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM vehicle WHERE vehicle_id = %s",
                        (vehicle_id,),
                    )
                    row = cursor.fetchone()
                    return Vehicle(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def exists_vehicle_type(self, vehicle_type_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM vehicle_type WHERE vehicle_type_id = %s",
                        (vehicle_type_id,),
                    )
                    return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

    def exists_vehicle_status(self, vehicle_status_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM vehicle_status WHERE vehicle_status_id = %s",
                        (vehicle_status_id,),
                    )
                    return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

    def create_vehicle(self, vehicle: Vehicle) -> int:
        data = vehicle.model_dump(exclude_none=True)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"%({k})s" for k in data.keys())
        query = f"""
            INSERT INTO vehicle ({columns})
            VALUES ({placeholders})
            RETURNING vehicle_id
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_vehicle(self, vehicle: Vehicle) -> bool:
        query = """
            UPDATE vehicle
            SET vehicle_type_id = %(vehicle_type_id)s,
                vehicle_status_id = %(vehicle_status_id)s,
                plate_number = %(plate_number)s,
                make = %(make)s,
                model = %(model)s,
                year = %(year)s,
                created_at = %(created_at)s
            WHERE vehicle_id = %(vehicle_id)s
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, vehicle.model_dump())
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_vehicle(self, vehicle_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM vehicle WHERE vehicle_id = %s",
                        (vehicle_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def get_current_location(self, vehicle_id: int) -> Optional[dict]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT ping_id, vehicle_id, ts, speed_kph, heading_deg,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM location_ping
                        WHERE vehicle_id = %s
                        ORDER BY ts DESC, ping_id DESC
                        LIMIT 1
                        """,
                        (vehicle_id,),
                    )
                    row = cursor.fetchone()
                    return dict(row) if row else None
        finally:
            self.pool.putconn(conn)

    def get_vehicle_pings(
        self,
        vehicle_id: int,
        *,
        limit: int,
        offset: int,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where = ["vehicle_id = %s"]
                    params: list[Any] = [vehicle_id]
                    if from_ts:
                        where.append("ts >= %s")
                        params.append(from_ts)
                    if to_ts:
                        where.append("ts <= %s")
                        params.append(to_ts)
                    where_sql = " AND ".join(where)
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM location_ping WHERE {where_sql}",
                        params,
                    )
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT ping_id, ts, speed_kph, heading_deg,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM location_ping
                        WHERE {where_sql}
                        ORDER BY ts, ping_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [dict(r) for r in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_vehicle_trips(
        self,
        vehicle_id: int,
        *,
        limit: int,
        offset: int,
        from_ts: Optional[datetime] = None,
        to_ts: Optional[datetime] = None,
    ) -> tuple[list[dict], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where = ["vehicle_id = %s"]
                    params: list[Any] = [vehicle_id]
                    if from_ts:
                        where.append("start_ts >= %s")
                        params.append(from_ts)
                    if to_ts:
                        where.append("end_ts <= %s")
                        params.append(to_ts)
                    where_sql = " AND ".join(where)
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM trip WHERE {where_sql}", params
                    )
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT trip_id, start_ts, end_ts, distance_km
                        FROM trip
                        WHERE {where_sql}
                        ORDER BY start_ts, trip_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [dict(r) for r in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
