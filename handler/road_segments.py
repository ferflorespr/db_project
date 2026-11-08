from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from dao.geo import dumps_geojson, format_ts, loads_geojson, nonneg, parse_bbox
from dao.road_segments import RoadSegment, RoadSegmentDao


def _detail(road: RoadSegment) -> dict:
    out = {
        "road_id": road.road_id,
        "name": road.name,
        "speed_limit_kph": road.speed_limit_kph,
        "created_at": format_ts(road.created_at),
        "geom": loads_geojson(road.geom_json),
        "is_oneway": road.is_oneway,
        "direction": road.direction,
    }
    return out


def _summary(road: RoadSegment) -> dict:
    return {
        "road_id": road.road_id,
        "name": road.name,
        "speed_limit_kph": road.speed_limit_kph,
        "created_at": format_ts(road.created_at),
    }


class RoadSegmentHandler:
    def create_road_segment(self, body: dict[str, Any]):
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Malformed geometry or invalid JSON")
        name = body.get("name")
        if not isinstance(name, str) or not name.strip():
            raise HTTPException(status_code=400, detail="name is required and must be non-empty")
        speed = body.get("speed_limit_kph")
        if speed is not None:
            speed = int(speed)
            if speed < 0:
                raise HTTPException(status_code=400, detail="speed_limit_kph must be >= 0")
        geom_json = dumps_geojson(body.get("geom"), expected_type="LineString")
        direction = body.get("direction")
        if isinstance(direction, str):
            direction = direction.strip()
        dao = RoadSegmentDao()
        try:
            road_id = dao.create_road_segment(
                RoadSegment(
                    name=name.strip(),
                    speed_limit_kph=speed,
                    is_oneway=body.get("is_oneway"),
                    direction=direction,
                ),
                geom_json,
            )
            return _detail(dao.get_road_segment_by_id(road_id))
        finally:
            dao.close()

    def get_all_road_segments(
        self, limit=None, offset=None, name=None, min_speed_kph=None, max_speed_kph=None, bbox=None
    ):
        limit_n = nonneg(limit, "limit", 20)
        offset_n = nonneg(offset, "offset", 0)
        box = parse_bbox(bbox)
        min_s = int(min_speed_kph) if min_speed_kph is not None and str(min_speed_kph) != "" else None
        max_s = int(max_speed_kph) if max_speed_kph is not None and str(max_speed_kph) != "" else None
        if min_s is not None and max_s is not None and min_s > max_s:
            raise HTTPException(status_code=400, detail="min_speed_kph cannot exceed max_speed_kph")
        dao = RoadSegmentDao()
        try:
            rows, count = dao.get_road_segments(
                limit=limit_n,
                offset=offset_n,
                name=name.strip() if name else None,
                min_speed=min_s,
                max_speed=max_s,
                bbox=box,
            )
            return {
                "items": [_summary(r) for r in rows],
                "limit": limit_n,
                "offset": offset_n,
                "count": count,
            }
        finally:
            dao.close()

    def get_road_segment_by_id(self, road_id: int):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be a positive integer")
        dao = RoadSegmentDao()
        try:
            row = dao.get_road_segment_by_id(road_id)
            if row is None:
                raise HTTPException(status_code=404, detail="road_id does not exist")
            return _detail(row)
        finally:
            dao.close()

    def update_road_segment(self, road_id: int, body: dict[str, Any]):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be a positive integer")
        if not isinstance(body, dict) or not body:
            raise HTTPException(status_code=400, detail="Malformed JSON or empty patch payload")
        dao = RoadSegmentDao()
        try:
            existing = dao.get_road_segment_by_id(road_id)
            if existing is None:
                raise HTTPException(status_code=404, detail="road_id does not exist")
            data = existing.model_dump()
            geom_json = None
            touched = False
            if "name" in body:
                if not isinstance(body["name"], str) or not body["name"].strip():
                    raise HTTPException(status_code=400, detail="name must be non-empty")
                data["name"] = body["name"].strip()
                touched = True
            if "speed_limit_kph" in body:
                speed = body["speed_limit_kph"]
                if speed is not None:
                    speed = int(speed)
                    if speed < 0:
                        raise HTTPException(status_code=400, detail="speed_limit_kph must be >= 0")
                data["speed_limit_kph"] = speed
                touched = True
            if "is_oneway" in body:
                data["is_oneway"] = body["is_oneway"]
                touched = True
            if "direction" in body:
                data["direction"] = body["direction"]
                touched = True
            if "geom" in body:
                geom_json = dumps_geojson(body["geom"], expected_type="LineString")
                touched = True
            if not touched:
                raise HTTPException(
                    status_code=400, detail="At least one updatable field must be present"
                )
            dao.update_road_segment(RoadSegment(**data), geom_json=geom_json)
            return _detail(dao.get_road_segment_by_id(road_id))
        finally:
            dao.close()

    def delete_road_segment(self, road_id: int):
        if road_id <= 0:
            raise HTTPException(status_code=400, detail="road_id must be a positive integer")
        dao = RoadSegmentDao()
        try:
            if not dao.delete_road_segment(road_id):
                raise HTTPException(status_code=404, detail="road_id does not exist")
            return {"message": "Road segment deleted successfully.", "road_id": road_id}
        finally:
            dao.close()

    def get_road_segments_geojson(
        self, limit=None, offset=None, name=None, min_speed_kph=None, max_speed_kph=None, bbox=None
    ):
        if bbox is not None and str(bbox).strip() != "":
            raise HTTPException(
                status_code=400, detail="This endpoint does not accept a bbox parameter"
            )
        try:
            limit_n = nonneg(limit, "limit", 20)
            offset_n = nonneg(offset, "offset", 0)
        except HTTPException as exc:
            raise HTTPException(status_code=422, detail=exc.detail) from exc
        min_s = int(min_speed_kph) if min_speed_kph is not None and str(min_speed_kph) != "" else None
        max_s = int(max_speed_kph) if max_speed_kph is not None and str(max_speed_kph) != "" else None
        if min_s is not None and max_s is not None and min_s > max_s:
            raise HTTPException(status_code=400, detail="min_speed_kph cannot exceed max_speed_kph")
        dao = RoadSegmentDao()
        try:
            rows, count = dao.get_road_segments(
                limit=limit_n,
                offset=offset_n,
                name=name.strip() if name else None,
                min_speed=min_s,
                max_speed=max_s,
                include_geom=True,
            )
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": loads_geojson(r.geom_json),
                        "properties": {
                            "road_id": r.road_id,
                            "name": r.name,
                            "speed_limit_kph": r.speed_limit_kph,
                            "created_at": format_ts(r.created_at),
                        },
                    }
                    for r in rows
                ],
                "count": count,
                "limit": limit_n,
                "offset": offset_n,
            }
        finally:
            dao.close()
