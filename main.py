from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from handler.trips import TripHandler
from handler.road_segments import RoadSegmentHandler
from handler.vehicle import VehicleHandler
from handler.location_pings import LocationPingHandler
from handler.parking_areas import ParkingAreaHandler


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
# ---- Parking areas ----------------------------------------------------------


@app.post("/api/v1/parking-areas", status_code=201)
async def create_parking_area(body: dict[str, Any]):
    return ParkingAreaHandler().create_parking_area(body)


@app.get("/api/v1/parking-areas")
async def get_parking_areas(
    limit: int | None = None,
    offset: int | None = None,
    name: str | None = None,
    bbox: str | None = None,
):
    return ParkingAreaHandler().get_all_parking_areas(limit, offset, name, bbox)


@app.get("/api/v1/parking-areas/{parking_area_id}")
async def get_parking_area(parking_area_id: int):
    return ParkingAreaHandler().get_parking_area_by_id(parking_area_id)


@app.put("/api/v1/parking-areas/{parking_area_id}")
async def update_parking_area(parking_area_id: int, body: dict[str, Any]):
    return ParkingAreaHandler().update_parking_area(parking_area_id, body)


@app.delete("/api/v1/parking-areas/{parking_area_id}")
async def delete_parking_area(parking_area_id: int):
    return ParkingAreaHandler().delete_parking_area(parking_area_id)

# ---- Location pings ---------------------------------------------------------


@app.post("/api/v1/location-pings", status_code=201)
async def create_location_ping(body: dict[str, Any]):
    return LocationPingHandler().create_location_ping(body)


@app.get("/api/v1/location-pings")
async def get_location_pings(
    limit: int | None = None,
    offset: int | None = None,
    vehicle_id: int | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
    bbox: str | None = None,
):
    return LocationPingHandler().get_all_location_pings(
        limit, offset, vehicle_id, from_ts, to_ts, bbox
    )


@app.get("/api/v1/location-pings/{ping_id}")
async def get_location_ping(ping_id: int):
    return LocationPingHandler().get_location_ping_by_id(ping_id)


@app.put("/api/v1/location-pings/{ping_id}")
async def update_location_ping(ping_id: int, body: dict[str, Any]):
    return LocationPingHandler().update_location_ping(ping_id, body)


@app.delete("/api/v1/location-pings/{ping_id}")
async def delete_location_ping(ping_id: int):
    return LocationPingHandler().delete_location_ping(ping_id)
# ---- Trips ------------------------------------------------------------------


@app.post("/api/v1/trips", status_code=201)
async def create_trip(body: dict[str, Any]):
    return TripHandler().create_trip(body)


@app.get("/api/v1/trips")
async def get_trips(
    limit: int | None = None,
    offset: int | None = None,
    vehicle_id: int | None = None,
    from_ts: str | None = None,
    to_ts: str | None = None,
):
    return TripHandler().get_all_trips(limit, offset, vehicle_id, from_ts, to_ts)


@app.get("/api/v1/trips/{trip_id}")
async def get_trip(trip_id: int):
    return TripHandler().get_trip_by_id(trip_id)


@app.put("/api/v1/trips/{trip_id}")
async def update_trip(trip_id: int, body: dict[str, Any]):
    return TripHandler().update_trip(trip_id, body)


@app.delete("/api/v1/trips/{trip_id}")
async def delete_trip(trip_id: int):
    return TripHandler().delete_trip(trip_id)

