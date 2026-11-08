from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from dao.geo import format_ts, nonneg, parse_ts
from dao.vehicle_assignments import VehicleAssignment, VehicleAssignmentDao


def _row(assignment: VehicleAssignment) -> dict:
    return {
        "assignment_id": assignment.assignment_id,
        "vehicle_id": assignment.vehicle_id,
        "driver_id": assignment.driver_id,
        "assigned_from": format_ts(assignment.assigned_from),
        "assigned_to": format_ts(assignment.assigned_to),
    }


class VehicleAssignmentHandler:
    def create_vehicle_assignment(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed JSON or invalid payload shape")
        try:
            vehicle_id = int(body["vehicle_id"])
            driver_id = int(body["driver_id"])
            assigned_from = parse_ts(body.get("assigned_from"), "assigned_from")
            if vehicle_id <= 0 or driver_id <= 0 or assigned_from is None:
                raise ValueError()
        except Exception as exc:
            raise HTTPException(
                status_code=400, detail="Malformed JSON or invalid payload shape"
            ) from exc
        assigned_to = parse_ts(body.get("assigned_to"), "assigned_to")
        if assigned_to is not None and assigned_to <= assigned_from:
            raise HTTPException(status_code=422, detail="The assignment time interval is invalid")

        dao = VehicleAssignmentDao()
        try:
            if not dao.vehicle_exists(vehicle_id) or not dao.driver_exists(driver_id):
                raise HTTPException(
                    status_code=404,
                    detail="Referenced vehicle_id or driver_id does not exist",
                )
            assignment_id = dao.create_vehicle_assignment(
                VehicleAssignment(
                    vehicle_id=vehicle_id,
                    driver_id=driver_id,
                    assigned_from=assigned_from,
                    assigned_to=assigned_to,
                )
            )
            return _row(dao.get_vehicle_assignment_by_id(assignment_id))
        finally:
            dao.close()

    def get_all_vehicle_assignments(
        self, limit=None, offset=None, vehicle_id=None, driver_id=None, active=None
    ):
        limit_n = nonneg(limit, "limit", 20)
        offset_n = nonneg(offset, "offset", 0)
        vid = int(vehicle_id) if vehicle_id is not None and str(vehicle_id) != "" else None
        did = int(driver_id) if driver_id is not None and str(driver_id) != "" else None
        active_flag = None
        if active is not None and str(active) != "":
            if isinstance(active, bool):
                active_flag = active
            else:
                text = str(active).strip().lower()
                if text in {"true", "1", "yes"}:
                    active_flag = True
                elif text in {"false", "0", "no"}:
                    active_flag = False
                else:
                    raise HTTPException(status_code=400, detail="Invalid query parameter values")
        dao = VehicleAssignmentDao()
        try:
            rows, count = dao.get_vehicle_assignments(
                limit=limit_n,
                offset=offset_n,
                vehicle_id=vid,
                driver_id=did,
                active=active_flag,
            )
            return {
                "items": [_row(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_vehicle_assignment_by_id(self, assignment_id: int):
        if assignment_id <= 0:
            raise HTTPException(status_code=400, detail="assignment_id must be a positive integer")
        dao = VehicleAssignmentDao()
        try:
            row = dao.get_vehicle_assignment_by_id(assignment_id)
            if row is None:
                raise HTTPException(status_code=404, detail="assignment_id does not exist")
            return _row(row)
        finally:
            dao.close()

    def update_vehicle_assignment(self, assignment_id: int, body: dict[str, Any]):
        if assignment_id <= 0:
            raise HTTPException(status_code=400, detail="assignment_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty update payload")
        dao = VehicleAssignmentDao()
        try:
            existing = dao.get_vehicle_assignment_by_id(assignment_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="assignment_id does not exist")
            data = existing.model_dump()
            touched = False
            if "vehicle_id" in body:
                if body["vehicle_id"] is None:
                    raise HTTPException(status_code=422, detail="vehicle_id cannot be null")
                vehicle_id = int(body["vehicle_id"])
                if not dao.vehicle_exists(vehicle_id):
                    raise HTTPException(
                        status_code=404,
                        detail="assignment_id or a referenced foreign key does not exist",
                    )
                data["vehicle_id"] = vehicle_id
                touched = True
            if "driver_id" in body:
                if body["driver_id"] is None:
                    raise HTTPException(status_code=422, detail="driver_id cannot be null")
                driver_id = int(body["driver_id"])
                if not dao.driver_exists(driver_id):
                    raise HTTPException(
                        status_code=404,
                        detail="assignment_id or a referenced foreign key does not exist",
                    )
                data["driver_id"] = driver_id
                touched = True
            if "assigned_from" in body:
                if body["assigned_from"] is None:
                    raise HTTPException(status_code=422, detail="assigned_from cannot be null")
                data["assigned_from"] = parse_ts(body["assigned_from"], "assigned_from")
                touched = True
            if "assigned_to" in body:
                data["assigned_to"] = parse_ts(body["assigned_to"], "assigned_to")
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be supplied"
                )
            if (
                data["assigned_to"] is not None
                and data["assigned_to"] <= data["assigned_from"]
            ):
                raise HTTPException(
                    status_code=422, detail="The resulting assignment interval is invalid"
                )
            dao.update_vehicle_assignment(VehicleAssignment(**data))
            return _row(dao.get_vehicle_assignment_by_id(assignment_id))
        finally:
            dao.close()

    def delete_vehicle_assignment(self, assignment_id: int):
        if assignment_id <= 0:
            raise HTTPException(status_code=400, detail="assignment_id must be a positive integer")
        dao = VehicleAssignmentDao()
        try:
            if not dao.delete_vehicle_assignment(assignment_id):
                raise HTTPException(status_code=404, detail="assignment_id does not exist")
            return {
                "message": "Vehicle assignment deleted successfully.",
                "assignment_id": assignment_id,
            }
        finally:
            dao.close()
