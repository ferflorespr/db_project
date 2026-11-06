from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dao.vehicle import Vehicle
from handler.vehicle import VehicleHandler
app = FastAPI()


origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/vehicles")
async def get_vehicle():
    return VehicleHandler().get_all_vehicles()

@app.post("/api/v1/vehicles")
async def create_vehicle(new_vehicle: vehicle):
    return VehicleHandler().create_vehicle(new_vehicle)


@app.get("/api/v1/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: bigint):
    return VehicleHandler().get_vehicle_by_id(vehicle_id)

@app.put("/api/v1/vehicles/{vehicle_id}")
async def update_vehicle(Vehicle: int, Vehicle_data: Vehicle):
    return VehicleHandler().update_vehicle(vehicle, vehicle_data)

@app.delete("/api/v1/vehicles/{vehicle_id}")
async def delete_vehicle(vehicle_id: bigint):
    return VehicleHandler().delete_vehicle(vehicle_id)