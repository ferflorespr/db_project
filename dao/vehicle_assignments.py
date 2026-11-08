from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class VehicleAssignment(BaseModel):
    assignment_id: Optional[int] = None
    vehicle_id: int
    driver_id: int
    assigned_from: Optional[datetime] = None
    assigned_to: Optional[datetime] = None


class VehicleAssignmentDao:
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

    def driver_exists(self, driver_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM driver WHERE driver_id = %s",
                        (driver_id,),
                    )
                    return cursor.fetchone() is not None
        finally:
            self.pool.putconn(conn)

    def get_all_vehicle_assignments(self) -> list[VehicleAssignment]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM vehicle_assignment ORDER BY assignment_id"
                    )
                    return [
                        VehicleAssignment(**dict(row)) for row in cursor.fetchall()
                    ]
        finally:
            self.pool.putconn(conn)

    def get_vehicle_assignments(
        self,
        *,
        limit: int,
        offset: int,
        vehicle_id: Optional[int] = None,
        driver_id: Optional[int] = None,
        active: Optional[bool] = None,
    ) -> tuple[list[VehicleAssignment], int]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    where: list[str] = []
                    params: list[Any] = []
                    if vehicle_id is not None:
                        where.append("vehicle_id = %s")
                        params.append(vehicle_id)
                    if driver_id is not None:
                        where.append("driver_id = %s")
                        params.append(driver_id)
                    if active is True:
                        where.append("assigned_to IS NULL")
                    elif active is False:
                        where.append("assigned_to IS NOT NULL")
                    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
                    cursor.execute(
                        f"SELECT COUNT(*) AS n FROM vehicle_assignment{where_sql}",
                        params,
                    )
                    count = cursor.fetchone()["n"]
                    cursor.execute(
                        f"""
                        SELECT * FROM vehicle_assignment
                        {where_sql}
                        ORDER BY assignment_id
                        LIMIT %s OFFSET %s
                        """,
                        [*params, limit, offset],
                    )
                    items = [
                        VehicleAssignment(**dict(row)) for row in cursor.fetchall()
                    ]
                    return items, count
        finally:
            self.pool.putconn(conn)

    def get_vehicle_assignment_by_id(
        self, assignment_id: int
    ) -> Optional[VehicleAssignment]:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute(
                        "SELECT * FROM vehicle_assignment WHERE assignment_id = %s",
                        (assignment_id,),
                    )
                    row = cursor.fetchone()
                    return (
                        VehicleAssignment(**dict(row)) if row is not None else None
                    )
        finally:
            self.pool.putconn(conn)

    def create_vehicle_assignment(self, assignment: VehicleAssignment) -> int:
        data = assignment.model_dump(exclude_none=True)
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"%({k})s" for k in data.keys())
        query = f"""
            INSERT INTO vehicle_assignment ({columns})
            VALUES ({placeholders})
            RETURNING assignment_id
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, data)
                    return cursor.fetchone()[0]
        finally:
            self.pool.putconn(conn)

    def update_vehicle_assignment(self, assignment: VehicleAssignment) -> bool:
        query = """
            UPDATE vehicle_assignment
            SET vehicle_id = %(vehicle_id)s,
                driver_id = %(driver_id)s,
                assigned_from = %(assigned_from)s,
                assigned_to = %(assigned_to)s
            WHERE assignment_id = %(assignment_id)s
        """
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, assignment.model_dump())
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def delete_vehicle_assignment(self, assignment_id: int) -> bool:
        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM vehicle_assignment WHERE assignment_id = %s",
                        (assignment_id,),
                    )
                    return cursor.rowcount == 1
        finally:
            self.pool.putconn(conn)

    def close(self) -> None:
        self.pool.closeall()
