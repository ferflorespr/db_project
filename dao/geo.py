from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException


def format_ts(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def loads_geojson(raw: str | None) -> dict | None:
    if raw is None:
        return None
    return json.loads(raw)


def dumps_geojson(value: Any, expected_type: str | None = None) -> str:
    if value is None:
        raise HTTPException(status_code=400, detail="geom is required")
    if not isinstance(value, dict):
        raise HTTPException(status_code=400, detail="geom must be a GeoJSON object")
    geom_type = value.get("type")
    coords = value.get("coordinates")
    if not geom_type or coords is None:
        raise HTTPException(status_code=400, detail="Malformed geometry JSON")
    if expected_type and geom_type != expected_type:
        raise HTTPException(status_code=400, detail=f"geom must be a {expected_type}")
    return json.dumps({"type": geom_type, "coordinates": coords})


def parse_bbox(bbox: str | None) -> tuple[float, float, float, float] | None:
    if bbox is None or str(bbox).strip() == "":
        return None
    parts = [p.strip() for p in str(bbox).split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must be minLon,minLat,maxLon,maxLat")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox values must be numeric") from exc
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise HTTPException(status_code=400, detail="bbox longitude out of WGS84 range")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise HTTPException(status_code=400, detail="bbox latitude out of WGS84 range")
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=400, detail="bbox min values must be less than max values")
    return min_lon, min_lat, max_lon, max_lat


def nonneg(value: Any, name: str, default: int) -> int:
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400, detail=f"{name} must be a non-negative integer"
        ) from exc
    if n < 0:
        raise HTTPException(status_code=400, detail=f"{name} must be a non-negative integer")
    return n


def parse_ts(value: Any, name: str) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    text = str(value).strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} must be a valid timestamp") from exc
    return dt.replace(tzinfo=None) if dt.tzinfo else dt
