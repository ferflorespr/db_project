from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from dao.geo import dumps_geojson, format_ts, loads_geojson, nonneg, parse_bbox, parse_ts
from dao.location_pings import LocationPing, LocationPingDao


def _detail(ping: LocationPing) -> dict:
    return {
        "ping_id": ping.ping_id,
        "vehicle_id": ping.vehicle_id,
        "ts": format_ts(ping.ts),
        "geom": loads_geojson(ping.geom_json),
        "speed_kph": ping.speed_kph,
        "heading_deg": ping.heading_deg,
    }


class LocationPingHandler:
    def create_location_ping(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")
        try:
            vehicle_id = int(body["vehicle_id"])
            if vehicle_id <= 0:
                raise ValueError()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON") from exc
        dao = LocationPingDao()
        try:
            if not dao.vehicle_exists(vehicle_id):
                raise HTTPException(status_code=404, detail="vehicle_id does not exist")
            ts = parse_ts(body.get("ts"), "ts")
            if ts is None:
                raise HTTPException(status_code=400, detail="ts is required")
            geom_json = dumps_geojson(body.get("geom"), expected_type="Point")
            speed = body.get("speed_kph")
            if speed is not None:
                speed = float(speed)
                if speed < 0:
                    raise HTTPException(status_code=400, detail="speed_kph must be >= 0")
            heading = body.get("heading_deg")
            if heading is not None:
                heading = float(heading)
                if heading < 0 or heading >= 360:
                    raise HTTPException(
                        status_code=400, detail="heading_deg must be >= 0 and < 360"
                    )
            ping_id = dao.create_location_ping(
                LocationPing(
                    vehicle_id=vehicle_id,
                    ts=ts,
                    speed_kph=speed,
                    heading_deg=heading,
                ),
                geom_json,
            )
            return _detail(dao.get_location_ping_by_id(ping_id))
        finally:
            dao.close()

    def get_all_location_pings(
        self, limit=None, offset=None, vehicle_id=None, from_ts=None, to_ts=None, bbox=None
    ):
        limit_n = nonneg(limit, "limit", 100)
        offset_n = nonneg(offset, "offset", 0)
        vid = None
        if vehicle_id is not None and str(vehicle_id) != "":
            vid = int(vehicle_id)
            if vid <= 0:
                raise HTTPException(status_code=400, detail="vehicle_id must be a positive integer")
        start = parse_ts(from_ts, "from_ts")
        end = parse_ts(to_ts, "to_ts")
        if start and end and end < start:
            raise HTTPException(
                status_code=400, detail="from_ts and to_ts must be logically ordered"
            )
        dao = LocationPingDao()
        try:
            rows, count = dao.get_location_pings(
                limit=limit_n,
                offset=offset_n,
                vehicle_id=vid,
                from_ts=start,
                to_ts=end,
                bbox=parse_bbox(bbox),
            )
            return {
                "items": [_detail(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_location_ping_by_id(self, ping_id: int):
        if ping_id <= 0:
            raise HTTPException(status_code=400, detail="ping_id must be a positive integer")
        dao = LocationPingDao()
        try:
            row = dao.get_location_ping_by_id(ping_id)
            if row is None:
                raise HTTPException(status_code=404, detail="ping_id does not exist")
            return _detail(row)
        finally:
            dao.close()

    def update_location_ping(self, ping_id: int, body: dict[str, Any]):
        if ping_id <= 0:
            raise HTTPException(status_code=400, detail="ping_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload")
        dao = LocationPingDao()
        try:
            existing = dao.get_location_ping_by_id(ping_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="ping_id does not exist")
            data = existing.model_dump()
            geom_json = None
            touched = False
            if "vehicle_id" in body:
                vid = int(body["vehicle_id"])
                if not dao.vehicle_exists(vid):
                    raise HTTPException(
                        status_code=404, detail="referenced vehicle_id does not exist"
                    )
                data["vehicle_id"] = vid
                touched = True
            if "ts" in body:
                data["ts"] = parse_ts(body["ts"], "ts")
                touched = True
            if "speed_kph" in body:
                speed = body["speed_kph"]
                if speed is not None:
                    speed = float(speed)
                    if speed < 0:
                        raise HTTPException(status_code=400, detail="speed_kph must be >= 0")
                data["speed_kph"] = speed
                touched = True
            if "heading_deg" in body:
                heading = body["heading_deg"]
                if heading is not None:
                    heading = float(heading)
                    if heading < 0 or heading >= 360:
                        raise HTTPException(
                            status_code=400, detail="heading_deg must stay within [0, 360)"
                        )
                data["heading_deg"] = heading
                touched = True
            if "geom" in body:
                geom_json = dumps_geojson(body["geom"], expected_type="Point")
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be present"
                )
            dao.update_location_ping(LocationPing(**data), geom_json=geom_json)
            return _detail(dao.get_location_ping_by_id(ping_id))
        finally:
            dao.close()

    def delete_location_ping(self, ping_id: int):
        if ping_id <= 0:
            raise HTTPException(status_code=400, detail="ping_id must be a positive integer")
        dao = LocationPingDao()
        try:
            if not dao.delete_location_ping(ping_id):
                raise HTTPException(status_code=404, detail="ping_id does not exist")
            return {"message": "Location ping deleted successfully.", "ping_id": ping_id}
        finally:
            dao.close()
