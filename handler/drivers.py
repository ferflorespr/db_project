from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from psycopg2 import errors as pg_errors

from dao.drivers import Driver, DriverDao
from dao.geo import format_ts, nonneg, parse_ts


def _row(driver: Driver) -> dict:
    return {
        "driver_id": driver.driver_id,
        "first_name": driver.first_name,
        "last_name": driver.last_name,
        "license_number": driver.license_number,
        "hired_at": format_ts(driver.hired_at),
    }


class DriverHandler:
    def create_driver(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape")
        try:
            first_name = str(body["first_name"]).strip()
            last_name = str(body["last_name"]).strip()
            license_number = str(body["license_number"]).strip()
            hired_at = parse_ts(body.get("hired_at"), "hired_at")
            if not first_name or not last_name or not license_number or hired_at is None:
                raise ValueError("required")
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail="A required field is null or invalid"
            ) from exc

        dao = DriverDao()
        try:
            driver = Driver(
                first_name=first_name,
                last_name=last_name,
                license_number=license_number,
                hired_at=hired_at,
            )
            try:
                driver_id = dao.create_driver(driver)
            except pg_errors.UniqueViolation as exc:
                raise HTTPException(status_code=409, detail="license_number already exists") from exc
            return _row(dao.get_driver_by_id(driver_id))
        finally:
            dao.close()

    def get_all_drivers(self, limit=None, offset=None, name=None, license_number=None):
        limit_n = nonneg(limit, "limit", 20)
        offset_n = nonneg(offset, "offset", 0)
        dao = DriverDao()
        try:
            rows, count = dao.get_drivers(
                limit=limit_n,
                offset=offset_n,
                name=name.strip() if name else None,
                license_number=license_number.strip() if license_number else None,
            )
            return {
                "items": [_row(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_driver_by_id(self, driver_id: int):
        if driver_id <= 0:
            raise HTTPException(status_code=400, detail="driver_id must be a positive integer")
        dao = DriverDao()
        try:
            row = dao.get_driver_by_id(driver_id)
            if row is None:
                raise HTTPException(status_code=404, detail="driver_id does not exist")
            return _row(row)
        finally:
            dao.close()

    def update_driver(self, driver_id: int, body: dict[str, Any]):
        if driver_id <= 0:
            raise HTTPException(status_code=400, detail="driver_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload")
        dao = DriverDao()
        try:
            existing = dao.get_driver_by_id(driver_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="driver_id does not exist")
            data = existing.model_dump()
            touched = False
            for field in ("first_name", "last_name", "license_number"):
                if field in body:
                    if body[field] is None or not str(body[field]).strip():
                        raise HTTPException(status_code=422, detail=f"{field} cannot be null")
                    data[field] = str(body[field]).strip()
                    touched = True
            if "hired_at" in body:
                hired_at = parse_ts(body["hired_at"], "hired_at")
                if hired_at is None:
                    raise HTTPException(status_code=422, detail="hired_at is invalid")
                data["hired_at"] = hired_at
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be supplied"
                )
            try:
                ok = dao.update_driver(Driver(**data))
            except pg_errors.UniqueViolation as exc:
                raise HTTPException(
                    status_code=409,
                    detail="Updated license_number conflicts with another driver",
                ) from exc
            if not ok:
                raise HTTPException(status_code=404, detail="driver_id does not exist")
            return _row(dao.get_driver_by_id(driver_id))
        finally:
            dao.close()

    def delete_driver(self, driver_id: int):
        if driver_id <= 0:
            raise HTTPException(status_code=400, detail="driver_id must be a positive integer")
        dao = DriverDao()
        try:
            if dao.get_driver_by_id(driver_id) is None:
                raise HTTPException(status_code=404, detail="driver_id does not exist")
            if dao.has_assignments(driver_id):
                raise HTTPException(
                    status_code=409, detail="The driver is referenced by a vehicle assignment"
                )
            dao.delete_driver(driver_id)
            return {"message": "Driver deleted successfully.", "driver_id": driver_id}
        finally:
            dao.close()
