from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class ParkingArea(BaseModel):
    parking_area_id: Optional[int] = None
    name: Optional[str] = None
    capacity: Optional[int] = None
    created_at: Optional[datetime] = None
    geom_json: Optional[str] = None


class ParkingAreaDao:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            POOL_CONFIG["minconn"],
            POOL_CONFIG["maxconn"],
            **PG_DB_CONFIG,
        )

    def get_all_parking_areas(self) -> list[ParkingArea]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT parking_area_id, name, capacity, created_at,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM parking_area
                        ORDER BY parking_area_id
                        """
                    )
                    return [ParkingArea(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_parking_areas(
        self,
        *,
        limit: int,
        offset: int,
        name: Optional[str] = None,
        bbox: Optional[tuple[float, float, float, float]] = None,
        include_geom: bool = False,
    ) -> tuple[list[ParkingArea], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if name:
                        where.append("name ILIKE %s")
                        params.append(f"%{name}%")
                    if bbox:
                        where.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                        params.extend(bbox)
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM parking_area{where_sql}", params
                    )
                    count = cursor.fetchone()["n"]
                    geom_select = (
                        ", ST_AsGeoJSON(geom) AS geom_json" if include_geom else ""
                    )
                    cursor.execute(
                        f"""
                        SELECT parking_area_id, name, capacity, created_at{geom_select}
                        FROM parking_area
                        {where_sql}
                        ORDER BY parking_area_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [ParkingArea(**dict(row)) for row in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_parking_area_by_id(self, parking_area_id: int) -> Optional[ParkingArea]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT parking_area_id, name, capacity, created_at,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM parking_area
                        WHERE parking_area_id = %s
                        """,
                        (parking_area_id,),
                    )
                    row = cursor.fetchone()
                    return ParkingArea(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def create_parking_area(self, parking: ParkingArea, geom_json: str) -> int:
        query = """
            INSERT INTO parking_area (name, capacity, geom, created_at)
            VALUES (
                %(name)s, %(capacity)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326),
                %(created_at)s
            )
            RETURNING parking_area_id
        """
        data = parking.model_dump(exclude={"parking_area_id", "geom_json"})
        data["geom_json"] = geom_json
        if data.get("created_at") is None:
            data["created_at"] = datetime.utcnow()
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_parking_area(
        self, parking: ParkingArea, geom_json: Optional[str] = None
    ) -> bool:
        if geom_json is None:
            query = """
                UPDATE parking_area
                SET name = %(name)s,
                    capacity = %(capacity)s
                WHERE parking_area_id = %(parking_area_id)s
            """
            data = parking.model_dump()
        else:
            query = """
                UPDATE parking_area
                SET name = %(name)s,
                    capacity = %(capacity)s,
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326)
                WHERE parking_area_id = %(parking_area_id)s
            """
            data = parking.model_dump()
            data["geom_json"] = geom_json
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_parking_area(self, parking_area_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM parking_area WHERE parking_area_id = %s",
                        (parking_area_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
