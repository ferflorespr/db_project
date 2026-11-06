from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG


class Vehicle(BaseModel):
    vehicle_id: int
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
                    return [
                        Vehicle(**dict(row))
                        for row in cursor.fetchall()
                    ]
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

    def create_vehicle(self, vehicle: Vehicle) -> int:
        query = """
            INSERT INTO vehicle (
                vehicle_id,
                vehicle_type_id,
                vehicle_status_id,
                plate_number,
                make,
                model,
                year,
                created_at
            )
            VALUES (
                %(vehicle_id)s,
                %(vehicle_type_id)s,
                %(vehicle_status_id)s,
                %(plate_number)s,
                %(make)s,
                %(model)s,
                %(year)s,
                %(created_at)s
            )
            RETURNING vehicle_id
        """

        conn = self.pool.getconn()
        try:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, vehicle.model_dump())
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

    def close(self) -> None:
        self.pool.closeall()