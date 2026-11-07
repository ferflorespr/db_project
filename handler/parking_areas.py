from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from dao.geo import dumps_geojson, format_ts, loads_geojson, nonneg, parse_bbox
from dao.parking_areas import ParkingArea, ParkingAreaDao


def _detail(row: ParkingArea) -> dict:
    return {
        "parking_area_id": row.parking_area_id,
        "name": row.name,
        "capacity": row.capacity,
        "created_at": format_ts(row.created_at),
        "geom": loads_geojson(row.geom_json),
    }


def _summary(row: ParkingArea) -> dict:
    return {
        "parking_area_id": row.parking_area_id,
        "name": row.name,
        "capacity": row.capacity,
        "created_at": format_ts(row.created_at),
    }


class ParkingAreaHandler:
    def create_parking_area(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="name is required and must be non-empty")
        capacity = body.get("capacity")
        if capacity is not None:
            capacity = int(capacity)
            if capacity < 0:
                raise HTTPException(status_code=400, detail="capacity must be >= 0")
        geom_json = dumps_geojson(body.get("geom"), expected_type="Polygon")
        dao = ParkingAreaDao()
        try:
            parking_area_id = dao.create_parking_area(
                ParkingArea(name=name.strip(), capacity=capacity), geom_json
            )
            return _detail(dao.get_parking_area_by_id(parking_area_id))
        finally:
            dao.close()

    def get_all_parking_areas(self, limit=None, offset=None, name=None, bbox=None):
        limit_n = nonneg(limit, "limit", 20)
        offset_n = nonneg(offset, "offset", 0)
        dao = ParkingAreaDao()
        try:
            rows, count = dao.get_parking_areas(
                limit=limit_n,
                offset=offset_n,
                name=name.strip() if name else None,
                bbox=parse_bbox(bbox),
            )
            return {
                "items": [_summary(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_parking_area_by_id(self, parking_area_id: int):
        if parking_area_id <= 0:
            raise HTTPException(
                status_code=400, detail="parking_area_id must be a positive integer"
            )
        dao = ParkingAreaDao()
        try:
            row = dao.get_parking_area_by_id(parking_area_id)
            if row is None:
                raise HTTPException(status_code=404, detail="parking_area_id does not exist")
            return _detail(row)
        finally:
            dao.close()

    def update_parking_area(self, parking_area_id: int, body: dict[str, Any]):
        if parking_area_id <= 0:
            raise HTTPException(
                status_code=400, detail="parking_area_id must be a positive integer"
            )
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload")
        dao = ParkingAreaDao()
        try:
            existing = dao.get_parking_area_by_id(parking_area_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="parking_area_id does not exist")
            data = existing.model_dump()
            geom_json = None
            touched = False
            if "name" in body:
                if not isinstance(body["name"], str) or not body["name"].strip():
                    raise HTTPException(status_code=400, detail="name must be non-empty")
                data["name"] = body["name"].strip()
                touched = True
            if "capacity" in body:
                capacity = body["capacity"]
                if capacity is not None:
                    capacity = int(capacity)
                    if capacity < 0:
                        raise HTTPException(status_code=400, detail="capacity must be >= 0")
                data["capacity"] = capacity
                touched = True
            if "geom" in body:
                geom_json = dumps_geojson(body["geom"], expected_type="Polygon")
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be present"
                )
            dao.update_parking_area(ParkingArea(**data), geom_json=geom_json)
            return _detail(dao.get_parking_area_by_id(parking_area_id))
        finally:
            dao.close()

    def delete_parking_area(self, parking_area_id: int):
        if parking_area_id <= 0:
            raise HTTPException(
                status_code=400, detail="parking_area_id must be a positive integer"
            )
        dao = ParkingAreaDao()
        try:
            if not dao.delete_parking_area(parking_area_id):
                raise HTTPException(status_code=404, detail="parking_area_id does not exist")
            return {
                "message": "Parking area deleted successfully.",
                "parking_area_id": parking_area_id,
            }
        finally:
            dao.close()
