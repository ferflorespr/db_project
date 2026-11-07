from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from psycopg2 import errors as pg_errors

from dao.geo import format_ts, loads_geojson, nonneg, parse_ts
from dao.vehicle import Vehicle, VehicleDao


def _vehicle_json(vehicle: Vehicle) -> dict:
    return {
        "vehicle_id": vehicle.vehicle_id,
        "vehicle_type_id": vehicle.vehicle_type_id,
        "vehicle_status_id": vehicle.vehicle_status_id,
        "plate_number": vehicle.plate_number,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "created_at": format_ts(vehicle.created_at),
    }


class VehicleHandler:
    def create_vehicle(self, body: dict[str, Any]):
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape")
        try:
            vehicle_type_id = int(body["vehicle_type_id"])
            vehicle_status_id = int(body["vehicle_status_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=400, detail="Malformed JSON or invalid payload shape"
            ) from exc

        plate = body.get("plate_number")
        if plate is None or not isinstance(plate, str) or not plate.strip():
            raise HTTPException(
                status_code=400, detail="plate_number is required and must be non-empty"
            )
        year = body.get("year")
        if year is not None:
            year = int(year)
            if year < 1950 or year > 2100:
                raise HTTPException(status_code=400, detail="year must be between 1950 and 2100")

        make = body.get("make")
        model = body.get("model")
        if isinstance(make, str):
            make = make.strip() or None
        if isinstance(model, str):
            model = model.strip() or None

        dao = VehicleDao()
        try:
            if not dao.exists_vehicle_type(vehicle_type_id) or not dao.exists_vehicle_status(
                vehicle_status_id
            ):
                raise HTTPException(
                    status_code=404,
                    detail="Referenced vehicle_type_id or vehicle_status_id does not exist",
                )
            vehicle = Vehicle(
                vehicle_type_id=vehicle_type_id,
                vehicle_status_id=vehicle_status_id,
                plate_number=plate.strip(),
                make=make,
                model=model,
                year=year,
                created_at=datetime.utcnow(),
            )
            try:
                vehicle_id = dao.create_vehicle(vehicle)
            except pg_errors.UniqueViolation as exc:
                raise HTTPException(status_code=409, detail="plate_number already exists") from exc
            created = dao.get_vehicle_by_id(vehicle_id)
            return _vehicle_json(created)
        finally:
            dao.close()

    def get_all_vehicles(
        self,
        limit: Any = None,
        offset: Any = None,
        status: str | None = None,
        plate_number: str | None = None,
    ):
        limit_n = nonneg(limit, "limit", 20)
        offset_n = nonneg(offset, "offset", 0)
        dao = VehicleDao()
        try:
            rows, count = dao.get_vehicles(
                limit=limit_n,
                offset=offset_n,
                status=status.strip() if status else None,
                plate_number=plate_number.strip() if plate_number else None,
            )
            return {
                "items": [_vehicle_json(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_vehicle_by_id(self, vehicle_id: int):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        dao = VehicleDao()
        try:
            row = dao.get_vehicle_by_id(vehicle_id)
            if row is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            return _vehicle_json(row)
        finally:
            dao.close()

    def update_vehicle(self, vehicle_id: int, body: dict[str, Any]):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty payload")

        allowed = {
            "vehicle_type_id",
            "vehicle_status_id",
            "plate_number",
            "make",
            "model",
            "year",
        }
        updates = {k: v for k, v in body.items() if k in allowed}
        if not updates:
            raise HTTPException(
                status_code=400, detail="At least one updatable field must be supplied"
            )

        dao = VehicleDao()
        try:
            existing = dao.get_vehicle_by_id(vehicle_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")

            data = existing.model_dump()
            if "vehicle_type_id" in updates:
                vt = int(updates["vehicle_type_id"])
                if not dao.exists_vehicle_type(vt):
                    raise HTTPException(
                        status_code=404, detail="referenced foreign key does not exist"
                    )
                data["vehicle_type_id"] = vt
            if "vehicle_status_id" in updates:
                vs = int(updates["vehicle_status_id"])
                if not dao.exists_vehicle_status(vs):
                    raise HTTPException(
                        status_code=404, detail="referenced foreign key does not exist"
                    )
                data["vehicle_status_id"] = vs
            if "plate_number" in updates:
                plate = updates["plate_number"]
                if plate is None or not isinstance(plate, str) or not plate.strip():
                    raise HTTPException(status_code=400, detail="plate_number must be non-empty")
                data["plate_number"] = plate.strip()
            if "year" in updates and updates["year"] is not None:
                year = int(updates["year"])
                if year < 1950 or year > 2100:
                    raise HTTPException(
                        status_code=400, detail="year must be between 1950 and 2100"
                    )
                data["year"] = year
            if "make" in updates:
                make = updates["make"]
                data["make"] = make.strip() if isinstance(make, str) else make
                if data["make"] == "":
                    data["make"] = None
            if "model" in updates:
                model = updates["model"]
                data["model"] = model.strip() if isinstance(model, str) else model
                if data["model"] == "":
                    data["model"] = None

            vehicle = Vehicle(**data)
            try:
                ok = dao.update_vehicle(vehicle)
            except pg_errors.UniqueViolation as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Updated plate_number conflicts with another vehicle",
                ) from exc
            if not ok:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            return _vehicle_json(dao.get_vehicle_by_id(vehicle_id))
        finally:
            dao.close()

    def delete_vehicle(self, vehicle_id: int):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        dao = VehicleDao()
        try:
            if dao.get_vehicle_by_id(vehicle_id) is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            try:
                dao.delete_vehicle(vehicle_id)
            except pg_errors.ForeignKeyViolation as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Deletion is blocked by business rules / foreign key constraints",
                ) from exc
            return {"message": "Vehicle deleted successfully.", "vehicle_id": vehicle_id}
        finally:
            dao.close()

    def get_current_location(self, vehicle_id: int):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        dao = VehicleDao()
        try:
            if dao.get_vehicle_by_id(vehicle_id) is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            row = dao.get_current_location(vehicle_id)
            if row is None:
                return None
            return {
                "vehicle_id": row["vehicle_id"],
                "ping_id": row["ping_id"],
                "ts": format_ts(row["ts"]),
                "last_geom": loads_geojson(row["geom_json"]),
                "speed_kph": row["speed_kph"],
                "heading_deg": row["heading_deg"],
            }
        finally:
            dao.close()

    def get_vehicle_pings(
        self,
        vehicle_id: int,
        limit: Any = None,
        offset: Any = None,
        from_ts: Any = None,
        to_ts: Any = None,
    ):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        dao = VehicleDao()
        try:
            if dao.get_vehicle_by_id(vehicle_id) is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            limit_n = nonneg(limit, "limit", 100)
            offset_n = nonneg(offset, "offset", 0)
            start = parse_ts(from_ts, "from_ts")
            end = parse_ts(to_ts, "to_ts")
            if start and end and end < start:
                raise HTTPException(
                    status_code=400, detail="from_ts and to_ts must be logically ordered"
                )
            rows, count = dao.get_vehicle_pings(
                vehicle_id, limit=limit_n, offset=offset_n, from_ts=start, to_ts=end
            )
            return {
                "vehicle_id": vehicle_id,
                "items": [
                    {
                        "ping_id": r["ping_id"],
                        "ts": format_ts(r["ts"]),
                        "geom": loads_geojson(r["geom_json"]),
                        "speed_kph": r["speed_kph"],
                        "heading_deg": r["heading_deg"],
                    }
                    for r in rows
                ],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_vehicle_trips(
        self,
        vehicle_id: int,
        limit: Any = None,
        offset: Any = None,
        from_ts: Any = None,
        to_ts: Any = None,
    ):
        if vehicle_id <= 0:
            raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        dao = VehicleDao()
        try:
            if dao.get_vehicle_by_id(vehicle_id) is None:
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            limit_n = nonneg(limit, "limit", 50)
            offset_n = nonneg(offset, "offset", 0)
            start = parse_ts(from_ts, "from_ts")
            end = parse_ts(to_ts, "to_ts")
            if start and end and end < start:
                raise HTTPException(
                    status_code=400, detail="from_ts and to_ts must be logically ordered"
                )
            rows, count = dao.get_vehicle_trips(
                vehicle_id, limit=limit_n, offset=offset_n, from_ts=start, to_ts=end
            )
            return {
                "vehicle_id": vehicle_id,
                "items": [
                    {
                        "trip_id": r["trip_id"],
                        "start_ts": format_ts(r["start_ts"]),
                        "end_ts": format_ts(r["end_ts"]),
                        "distance_km": r["distance_km"],
                    }
                    for r in rows
                ],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()
