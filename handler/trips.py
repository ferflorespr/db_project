from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from dao.geo import dumps_geojson, format_ts, loads_geojson, nonneg, parse_ts
from dao.trips import Trip, TripDao


def _detail(trip: Trip) -> dict:
    return {
        "trip_id": trip.trip_id,
        "vehicle_id": trip.vehicle_id,
        "start_ts": format_ts(trip.start_ts),
        "end_ts": format_ts(trip.end_ts),
        "start_geom": loads_geojson(trip.start_geom_json),
        "end_geom": loads_geojson(trip.end_geom_json),
        "distance_km": trip.distance_km,
    }


def _summary(trip: Trip) -> dict:
    return {
        "trip_id": trip.trip_id,
        "vehicle_id": trip.vehicle_id,
        "start_ts": format_ts(trip.start_ts),
        "end_ts": format_ts(trip.end_ts),
        "distance_km": trip.distance_km,
    }


class TripHandler:
    def create_trip(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")
        try:
            vehicle_id = int(body["vehicle_id"])
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON") from exc
        dao = TripDao()
        try:
            if not dao.vehicle_exists(vehicle_id):
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            start_ts = parse_ts(body.get("start_ts"), "start_ts")
            end_ts = parse_ts(body.get("end_ts"), "end_ts")
            if start_ts is None or end_ts is None:
                raise HTTPException(status_code=400, detail="start_ts and end_ts are required")
            if end_ts <= start_ts:
                raise HTTPException(status_code=400, detail="end_ts must be later than start_ts")
            start_json = (
                dumps_geojson(body["start_geom"], expected_type="Point")
                if body.get("start_geom") is not None
                else None
            )
            end_json = (
                dumps_geojson(body["end_geom"], expected_type="Point")
                if body.get("end_geom") is not None
                else None
            )
            distance = body.get("distance_km")
            if distance is not None:
                distance = float(distance)
                if distance < 0:
                    raise HTTPException(status_code=400, detail="distance_km must be >= 0")
            trip_id = dao.create_trip(
                Trip(
                    vehicle_id=vehicle_id,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    distance_km=distance,
                ),
                start_geom_json=start_json,
                end_geom_json=end_json,
            )
            return _detail(dao.get_trip_by_id(trip_id))
        finally:
            dao.close()

    def get_all_trips(self, limit=None, offset=None, vehicle_id=None, from_ts=None, to_ts=None):
        limit_n = nonneg(limit, "limit", 50)
        offset_n = nonneg(offset, "offset", 0)
        vid = int(vehicle_id) if vehicle_id is not None and str(vehicle_id) != "" else None
        start = parse_ts(from_ts, "from_ts")
        end = parse_ts(to_ts, "to_ts")
        if start and end and end < start:
            raise HTTPException(
                status_code=400, detail="from_ts and to_ts must be logically ordered"
            )
        dao = TripDao()
        try:
            rows, count = dao.get_trips(
                limit=limit_n, offset=offset_n, vehicle_id=vid, from_ts=start, to_ts=end
            )
            return {
                "items": [_summary(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_trip_by_id(self, trip_id: int):
        if trip_id <= 0:
            raise HTTPException(status_code=400, detail="trip_id must be a positive integer")
        dao = TripDao()
        try:
            row = dao.get_trip_by_id(trip_id)
            if row is None:
                raise HTTPException(status_code=404, detail="trip_id does not exist")
            return _detail(row)
        finally:
            dao.close()

    def update_trip(self, trip_id: int, body: dict[str, Any]):
        if trip_id <= 0:
            raise HTTPException(status_code=400, detail="trip_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload")
        dao = TripDao()
        try:
            existing = dao.get_trip_by_id(trip_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="trip_id does not exist")
            data = existing.model_dump()
            start_json = None
            end_json = None
            update_start = update_end = False
            touched = False
            if "vehicle_id" in body:
                vid = int(body["vehicle_id"])
                if not dao.vehicle_exists(vid):
                    raise HTTPException(
                        status_code=404, detail="referenced vehicle_id does not exist"
                    )
                data["vehicle_id"] = vid
                touched = True
            if "start_ts" in body:
                data["start_ts"] = parse_ts(body["start_ts"], "start_ts")
                touched = True
            if "end_ts" in body:
                data["end_ts"] = parse_ts(body["end_ts"], "end_ts")
                touched = True
            if data["end_ts"] <= data["start_ts"]:
                raise HTTPException(
                    status_code=422, detail="end_ts must still be later than start_ts"
                )
            if "distance_km" in body:
                distance = body["distance_km"]
                if distance is not None:
                    distance = float(distance)
                    if distance < 0:
                        raise HTTPException(status_code=400, detail="distance_km must be >= 0")
                data["distance_km"] = distance
                touched = True
            if "start_geom" in body:
                update_start = True
                start_json = (
                    None
                    if body["start_geom"] is None
                    else dumps_geojson(body["start_geom"], expected_type="Point")
                )
                touched = True
            if "end_geom" in body:
                update_end = True
                end_json = (
                    None
                    if body["end_geom"] is None
                    else dumps_geojson(body["end_geom"], expected_type="Point")
                )
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be present"
                )
            dao.update_trip(
                Trip(**data),
                start_geom_json=start_json,
                end_geom_json=end_json,
                update_start_geom=update_start,
                update_end_geom=update_end,
            )
            return _detail(dao.get_trip_by_id(trip_id))
        finally:
            dao.close()

    def delete_trip(self, trip_id: int):
        if trip_id <= 0:
            raise HTTPException(status_code=400, detail="trip_id must be a positive integer")
        dao = TripDao()
        try:
            if not dao.delete_trip(trip_id):
                raise HTTPException(status_code=404, detail="trip_id does not exist")
            return {"message": "Trip deleted successfully.", "trip_id": trip_id}
        finally:
            dao.close()
