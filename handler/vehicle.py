from dao.vehicle import VehicleDao, Vehicle


class VehicleHandler:
    def __init__(self):
        self.dao = VehicleDao()

    def get_all_vehicles(self) :
        return self.dao.get_all_vehicles()

    def create_vehicle(self, vehicle: Vehicle):
        return self.dao.create_vehicle(vehicle)

    def update_vehicle(self, vehicle: Vehicle):
        return self.dao.update_vehicle(vehicle)

    def get_vehicle_by_id(self, vehicle_id: int) -> Vehicle:
        return self.dao.get_vehicle_by_id(vehicle_id)

    def delete_vehicle(self, vehicle_id: int):
        return self.dao.delete_vehicle(vehicle_id)
