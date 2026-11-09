from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class Driver(BaseModel):
    driver_id: Optional[int] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    license_number: Optional[str] = None
    hired_at: Optional[datetime] = None


class DriverDao:
    def __init__(self):
        self.pool = SimpleConnectionPool(
            POOL_CONFIG["minconn"],
            POOL_CONFIG["maxconn"],
            **PG_DB_CONFIG,
        )

    def get_all_drivers(self) -> list[Driver]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("SELECT * FROM driver ORDER BY driver_id")
                    return [Driver(**dict(row)) for row in cursor.fetchall()]
        finally:
            self.pool.putconn(conn)

    def get_drivers(
        self,
        *,
        limit: int,
        offset: int,
        name: Optional[str] = None,
        license_number: Optional[str] = None,
    ) -> tuple[list[Driver], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if name:
                        where.append("(first_name ILIKE %s OR last_name ILIKE %s)")
                        params.extend([f"%{name}%", f"%{name}%"])
                    if license_number:
                        where.append("license_number ILIKE %s")
                        params.append(f"%{license_number}%")
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(f"SELECT COUNT(*) AS n FROM driver{where_sql}", params)
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT * FROM driver
                        {where_sql}
                        ORDER BY driver_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    return [Driver(**dict(row)) for row in cursor.fetchall()], count
        finally:
            self.pool.putconn(conn)

    def get_driver_by_id(self, driver_id: int) -> Optional[Driver]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM driver WHERE driver_id = %s",
                        (driver_id,),
                    )
                    row = cursor.fetchone()
                    return Driver(**dict(row)) if row is not None else None
        finally:
            self.pool.putconn(conn)

    def create_driver(self, driver: Driver) -> int:
        data = driver.model_dump(exclude_none=True)
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COALESCE(MAX(driver_id), 0) + 1 FROM driver")
                    data["driver_id"] = cursor.fetchone()[0]

                    columns = ", ".join(data)
                    placeholders = ", ".join(f"%({key})s" for key in data)
                    query = f"""
                        INSERT INTO driver ({columns})
                        VALUES ({placeholders})
                        RETURNING driver_id
                    """
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_driver(self, driver: Driver) -> bool:
        query = """
            UPDATE driver
            SET first_name = %(first_name)s,
                last_name = %(last_name)s,
                license_number = %(license_number)s,
                hired_at = %(hired_at)s
            WHERE driver_id = %(driver_id)s
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, driver.model_dump())
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def has_assignments(self, driver_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM vehicle_assignment WHERE driver_id = %s LIMIT 1",
                        (driver_id,),
                    )
                    return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

    def delete_driver(self, driver_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM driver WHERE driver_id = %s",
                        (driver_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
