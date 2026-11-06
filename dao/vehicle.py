from email.mime import text

from config.dbconfig import PG_DB_CONFIG, POOL_CONFIG
import psycopg2
from pydantic import BaseModel
from typing import Optional
from psycopg2.extras import DictCursor
from psycopg2.pool import SimpleConnectionPool


class Vehicle(BaseModel):
    vehicle_id : bigint
    vehicle_type_id : bigint
    vehicle_status_id : bigint
    plate_nuber : text
    make : text
    model : text
    year : bigint
    created_at : timestamp


class VehicleDao(BaseModel):
    def __int__(self) :
        self.pool = SimpleConnectionPool(POOL_CONFIG["minconn"],
                                     POOL_CONFIG["maxconn"],
                                     **PG_DB_CONFIG)

    def get_all_vehicles(self) -> list[Vehicle]:
        conn = self.pool.getconn()
        cursor = conn.cursor()

        query = f"select * from vehicles "
        cursor.execute(query)
        result: list[Vehicle] = []
        for row in cursor:
            result.append(Vehicle(**row))
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result

    def get_vehicle_by_id(self, vehicle_id: bigint):
        # Get connection from pool
        conn = self.pool.getconn()
        # now get the cursor
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """select * from vehicles where vehicle_id = %s 
        """
        cursor.execute(query, (vehicle_id,))
        result: Optional[Vehicle] = None
        result = cursor.fetchone()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return result

    def create_vehicle(self, new_part: Vehicle) -> bigint:
        # Get connection from pool
        conn = self.pool.getconn()
        # now get the cursor
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """
        insert into 
        vehicle (vehicle_id, vehicle_type_id, plate_nuber, make, model, year, created_at)
        values (%(vehicle_id)s, %(vehicle_type_id)s, %(vehicle_status_id)s, %(plate_number)s, %(make)s, %(model)s, %(year)s, %(created_at)s)
        returning vehicle_id;
        """
        cursor.execute(query, new_part.model_dump(exclude_none=True))
        pid = cursor.fetchone()[0]
        # Commit change to DB
        conn.commit()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return pid


    def update_vehicle(self, vehicle):
        # Get connection from pool
        conn = self.pool.getconn()
        # now get the cursor
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """
        update vehicle 
        set vehicle_id = %(vehicle_id)s, vehicle_status_id = %(vehicle_status_id)s,  = %(plate_number)s, make = %(make)s, model = %(model)s, year = %(year)s, created_at = %(created_at)s
        where vehicle = %(vehicle)s
        """
        cursor.execute(query, vehicle.model_dump())
        conn.commit()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return part

    def delete_vehicle(self, vehicle):
        # Get connection from pool
        conn = self.pool.getconn()
        # now get the cursor
        cursor = conn.cursor(cursor_factory=DictCursor)
        query = """
                delete from vehicle 
                where vehicle_id = %s
                """
        cursor.execute(query, (part,))
        rows = cursor.rowcount
        conn.commit()
        # Always close cursor
        cursor.close()
        # Return the connection to the pool
        self.pool.putconn(conn)
        return rows == 1




