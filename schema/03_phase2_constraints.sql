DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'vehicle_plate_number_key'
    ) THEN
        ALTER TABLE vehicle ADD CONSTRAINT vehicle_plate_number_key UNIQUE (plate_number);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'driver_license_number_key'
    ) THEN
        ALTER TABLE driver ADD CONSTRAINT driver_license_number_key UNIQUE (license_number);
    END IF;
END $$;

CREATE SEQUENCE IF NOT EXISTS vehicle_vehicle_id_seq;
CREATE SEQUENCE IF NOT EXISTS road_segment_road_id_seq;
CREATE SEQUENCE IF NOT EXISTS parking_area_parking_area_id_seq;
CREATE SEQUENCE IF NOT EXISTS location_ping_ping_id_seq;
CREATE SEQUENCE IF NOT EXISTS trip_trip_id_seq;
CREATE SEQUENCE IF NOT EXISTS driver_driver_id_seq;
CREATE SEQUENCE IF NOT EXISTS vehicle_assignment_assignment_id_seq;

SELECT setval(
    'vehicle_vehicle_id_seq',
    GREATEST(COALESCE((SELECT MAX(vehicle_id) FROM vehicle), 0), 1),
    COALESCE((SELECT MAX(vehicle_id) FROM vehicle), 0) > 0
);
SELECT setval(
    'road_segment_road_id_seq',
    GREATEST(COALESCE((SELECT MAX(road_id) FROM road_segment), 0), 1),
    COALESCE((SELECT MAX(road_id) FROM road_segment), 0) > 0
);
SELECT setval(
    'parking_area_parking_area_id_seq',
    GREATEST(COALESCE((SELECT MAX(parking_area_id) FROM parking_area), 0), 1),
    COALESCE((SELECT MAX(parking_area_id) FROM parking_area), 0) > 0
);
SELECT setval(
    'location_ping_ping_id_seq',
    GREATEST(COALESCE((SELECT MAX(ping_id) FROM location_ping), 0), 1),
    COALESCE((SELECT MAX(ping_id) FROM location_ping), 0) > 0
);
SELECT setval(
    'trip_trip_id_seq',
    GREATEST(COALESCE((SELECT MAX(trip_id) FROM trip), 0), 1),
    COALESCE((SELECT MAX(trip_id) FROM trip), 0) > 0
);
SELECT setval(
    'driver_driver_id_seq',
    GREATEST(COALESCE((SELECT MAX(driver_id) FROM driver), 0), 1),
    COALESCE((SELECT MAX(driver_id) FROM driver), 0) > 0
);
SELECT setval(
    'vehicle_assignment_assignment_id_seq',
    GREATEST(COALESCE((SELECT MAX(assignment_id) FROM vehicle_assignment), 0), 1),
    COALESCE((SELECT MAX(assignment_id) FROM vehicle_assignment), 0) > 0
);

ALTER TABLE vehicle ALTER COLUMN vehicle_id SET DEFAULT nextval('vehicle_vehicle_id_seq');
ALTER TABLE road_segment ALTER COLUMN road_id SET DEFAULT nextval('road_segment_road_id_seq');
ALTER TABLE parking_area ALTER COLUMN parking_area_id SET DEFAULT nextval('parking_area_parking_area_id_seq');
ALTER TABLE location_ping ALTER COLUMN ping_id SET DEFAULT nextval('location_ping_ping_id_seq');
ALTER TABLE trip ALTER COLUMN trip_id SET DEFAULT nextval('trip_trip_id_seq');
ALTER TABLE driver ALTER COLUMN driver_id SET DEFAULT nextval('driver_driver_id_seq');
ALTER TABLE vehicle_assignment ALTER COLUMN assignment_id SET DEFAULT nextval('vehicle_assignment_assignment_id_seq');

ALTER SEQUENCE vehicle_vehicle_id_seq OWNED BY vehicle.vehicle_id;
ALTER SEQUENCE road_segment_road_id_seq OWNED BY road_segment.road_id;
ALTER SEQUENCE parking_area_parking_area_id_seq OWNED BY parking_area.parking_area_id;
ALTER SEQUENCE location_ping_ping_id_seq OWNED BY location_ping.ping_id;
ALTER SEQUENCE trip_trip_id_seq OWNED BY trip.trip_id;
ALTER SEQUENCE driver_driver_id_seq OWNED BY driver.driver_id;
ALTER SEQUENCE vehicle_assignment_assignment_id_seq OWNED BY vehicle_assignment.assignment_id;
