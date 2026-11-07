from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from handler.road_segments import RoadSegmentHandler
from handler.vehicle import VehicleHandler

app = FastAPI(
    title="Car Tracking API",
    version="2.0.0",
    description="Phase II REST API (handler/dao) for CIIC 4060 / ICOM 5016",
)

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "phase": 2}


# ---- Vehicles ---------------------------------------------------------------


@app.post("/api/v1/vehicles", status_code=201)
async def create_vehicle(body: dict[str, Any]):
    return VehicleHandler().create_vehicle(body)


@app.get("/api/v1/vehicles")
async def get_vehicles(
    limit: int | None = None,
    offset: int | None = None,
    status: str | None = None,
    plate_number: str | None = None,
):
    return VehicleHandler().get_all_vehicles(limit, offset, status, plate_number)


@app.get("/api/v1/vehicles/{vehicle_id}/current-location")
async def get_current_location(vehicle_id: int):
    result = VehicleHandler().get_current_location(vehicle_id)
    if result is None:
        return Response(status_code=204)
    return result


@app.get("/api/v1/vehicles/{vehicle_id}/pings")
async def get_vehicle_pings(
    vehicle_id: int,
    limit: int | None = None,
    offset: int | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
):
    return VehicleHandler().get_vehicle_pings(vehicle_id, limit, offset, from_ts, to_ts)


@app.get("/api/v1/vehicles/{vehicle_id}/trips")
async def get_vehicle_trips(
    vehicle_id: int,
    limit: int | None = None,
    offset: int | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
):
    return VehicleHandler().get_vehicle_trips(vehicle_id, limit, offset, from_ts, to_ts)


@app.get("/api/v1/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: int):
    return VehicleHandler().get_vehicle_by_id(vehicle_id)


@app.put("/api/v1/vehicles/{vehicle_id}")
async def update_vehicle(vehicle_id: int, body: dict[str, Any]):
    return VehicleHandler().update_vehicle(vehicle_id, body)


@app.delete("/api/v1/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: int):
    return VehicleHandler().delete_vehicle(vehicle_id)


# ---- Road segments ----------------------------------------------------------


@app.post("/api/v1/road-segments", status_code=201)
async def create_road_segment(body: dict[str, Any]):
    return RoadSegmentHandler().create_road_segment(body)


@app.get("/api/v1/road-segments/geojson")
async def get_road_segments_geojson(
    limit: int | None = None,
    offset: int | None = None,
    name: str | None = None,
    min_speed_kph: int | None = None,
    max_speed_kph: int | None = None,
    bbox: str | None = None,
):
    payload = RoadSegmentHandler().get_road_segments_geojson(
        limit, offset, name, min_speed_kph, max_speed_kph, bbox
    )
    return JSONResponse(content=payload, media_type="application/geo+json")


@app.get("/api/v1/road-segments")
async def get_road_segments(
    limit: int | None = None,
    offset: int | None = None,
    name: str | None = None,
    min_speed_kph: int | None = None,
    max_speed_kph: int | None = None,
    bbox: str | None = None,
):
    return RoadSegmentHandler().get_all_road_segments(
        limit, offset, name, min_speed_kph, max_speed_kph, bbox
    )


@app.get("/api/v1/road-segments/{road_id}")
async def get_road_segment(road_id: int):
    return RoadSegmentHandler().get_road_segment_by_id(road_id)


@app.put("/api/v1/road-segments/{road_id}")
async def update_road_segment(road_id: int, body: dict[str, Any]):
    return RoadSegmentHandler().update_road_segment(road_id, body)


@app.delete("/api/v1/road-segments/{road_id}/remove")
async def delete_road_segment(road_id: int):
    return RoadSegmentHandler().delete_road_segment(road_id)
