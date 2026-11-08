from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class RoadSegment(BaseModel):
    road_id: Optional[int] = None
    name: Optional[str] = None
    speed_limit_kph: Optional[int] = None
    created_at: Optional[datetime] = None
    is_oneway: Optional[bool] = None
    direction: Optional[str] = None
    geom_json: Optional[str] = None


class RoadSegmentDao:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            POOL_CONFIG["minconn"],
            POOL_CONFIG["maxconn"],
            **PG_DB_CONFIG,
        )

    def get_all_road_segments(self) -> list[RoadSegment]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT road_id, name, speed_limit_kph, created_at,
                               is_oneway, direction,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM road_segment
                        ORDER BY road_id
                        """
                    )
                    return [RoadSegment(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_road_segments(
        self,
        *,
        limit: int,
        offset: int,
        name: Optional[str] = None,
        min_speed: Optional[int] = None,
        max_speed: Optional[int] = None,
        bbox: Optional[tuple[float, float, float, float]] = None,
        include_geom: bool = False,
    ) -> tuple[list[RoadSegment], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if name:
                        where.append("name ILIKE %s")
                        params.append(f"%{name}%")
                    if min_speed is not None:
                        where.append("speed_limit_kph >= %s")
                        params.append(min_speed)
                    if max_speed is not None:
                        where.append("speed_limit_kph <= %s")
                        params.append(max_speed)
                    if bbox:
                        where.append("geom && ST_MakeEnvelope(%s, %s, %s, %s, 4326)")
                        params.extend(bbox)
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM road_segment{where_sql}", params
                    )
                    count = cursor.fetchone()["n"]
                    geom_select = (
                        ", ST_AsGeoJSON(geom) AS geom_json" if include_geom else ""
                    )
                    cursor.execute(
                        f"""
                        SELECT road_id, name, speed_limit_kph, created_at,
                               is_oneway, direction{geom_select}
                        FROM road_segment
                        {where_sql}
                        ORDER BY road_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [RoadSegment(**dict(row)) for row in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_road_segment_by_id(self, road_id: int) -> Optional[RoadSegment]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        """
                        SELECT road_id, name, speed_limit_kph, created_at,
                               is_oneway, direction,
                               ST_AsGeoJSON(geom) AS geom_json
                        FROM road_segment
                        WHERE road_id = %s
                        """,
                        (road_id,),
                    )
                    row = cursor.fetchone()
                    return RoadSegment(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def create_road_segment(self, road: RoadSegment, geom_json: str) -> int:
        query = """
            INSERT INTO road_segment (
                name, speed_limit_kph, geom, created_at, is_oneway, direction
            )
            VALUES (
                %(name)s, %(speed_limit_kph)s,
                ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326),
                %(created_at)s, %(is_oneway)s, %(direction)s
            )
            RETURNING road_id
        """
        data = road.model_dump(exclude={"road_id", "geom_json"})
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

    def update_road_segment(
        self, road: RoadSegment, geom_json: Optional[str] = None
    ) -> bool:
        if geom_json is None:
            query = """
                UPDATE road_segment
                SET name = %(name)s,
                    speed_limit_kph = %(speed_limit_kph)s,
                    is_oneway = %(is_oneway)s,
                    direction = %(direction)s
                WHERE road_id = %(road_id)s
            """
            data = road.model_dump()
        else:
            query = """
                UPDATE road_segment
                SET name = %(name)s,
                    speed_limit_kph = %(speed_limit_kph)s,
                    is_oneway = %(is_oneway)s,
                    direction = %(direction)s,
                    geom = ST_SetSRID(ST_GeomFromGeoJSON(%(geom_json)s), 4326)
                WHERE road_id = %(road_id)s
            """
            data = road.model_dump()
            data["geom_json"] = geom_json
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_road_segment(self, road_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM road_segment WHERE road_id = %s",
                        (road_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
