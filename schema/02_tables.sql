-- Car Tracking schema — matches Moodle table diagram (Phase I).
-- Drop in reverse dependency order so reloads are idempotent.

DROP TABLE IF EXISTS vehicle_assignment CASCADE;
DROP TABLE IF EXISTS location_ping CASCADE;
DROP TABLE IF EXISTS trip CASCADE;
DROP TABLE IF EXISTS vehicle CASCADE;
DROP TABLE IF EXISTS vehicle_type CASCADE;
DROP TABLE IF EXISTS vehicle_kind CASCADE;
DROP TABLE IF EXISTS fuel_type CASCADE;
DROP TABLE IF EXISTS vehicle_status CASCADE;
DROP TABLE IF EXISTS driver CASCADE;
DROP TABLE IF EXISTS parking_area CASCADE;
DROP TABLE IF EXISTS road_segment CASCADE;

CREATE TABLE vehicle_kind (
    vehicle_kind_id bigint PRIMARY KEY,
    name            text NOT NULL
);

CREATE TABLE fuel_type (
    fuel_type_id bigint PRIMARY KEY,
    name         text NOT NULL
);

CREATE TABLE vehicle_status (
    vehicle_status_id bigint PRIMARY KEY,
    name              text NOT NULL
);

CREATE TABLE vehicle_type (
    vehicle_type_id   bigint PRIMARY KEY,
    vehicle_kind_id   bigint NOT NULL REFERENCES vehicle_kind (vehicle_kind_id),
    fuel_type_id      bigint NOT NULL REFERENCES fuel_type (fuel_type_id),
    emissions_rating  double precision,
    created_at        timestamp
);

CREATE TABLE vehicle (
    vehicle_id        bigint PRIMARY KEY,
    vehicle_type_id   bigint NOT NULL REFERENCES vehicle_type (vehicle_type_id),
    vehicle_status_id bigint NOT NULL REFERENCES vehicle_status (vehicle_status_id),
    plate_number      text,
    make              text,
    model             text,
    year              bigint,
    created_at        timestamp
);

CREATE TABLE driver (
    driver_id      bigint PRIMARY KEY,
    first_name     text,
    last_name      text,
    license_number text,
    hired_at       timestamp
);

CREATE TABLE vehicle_assignment (
    assignment_id  bigint PRIMARY KEY,
    vehicle_id     bigint NOT NULL REFERENCES vehicle (vehicle_id),
    driver_id      bigint NOT NULL REFERENCES driver (driver_id),
    assigned_from  timestamp,
    assigned_to    timestamp
);

CREATE TABLE location_ping (
    ping_id     bigint PRIMARY KEY,
    vehicle_id  bigint NOT NULL REFERENCES vehicle (vehicle_id),
    ts          timestamp,
    geom        geometry(point, 4326),
    speed_kph   double precision,
    heading_deg double precision
);

CREATE TABLE trip (
    trip_id     bigint PRIMARY KEY,
    vehicle_id  bigint NOT NULL REFERENCES vehicle (vehicle_id),
    start_ts    timestamp,
    end_ts      timestamp,
    start_geom  geometry(point, 4326),
    end_geom    geometry(point, 4326),
    distance_km double precision
);

CREATE TABLE parking_area (
    parking_area_id bigint PRIMARY KEY,
    name            text,
    capacity        bigint,
    geom            geometry(polygon, 4326),
    created_at      timestamp
);

CREATE TABLE road_segment (
    road_id          bigint PRIMARY KEY,
    name             text,
    speed_limit_kph  bigint,
    geom             geometry(linestring, 4326),
    created_at       timestamp,
    is_oneway        boolean,
    direction        text
);

-- Spatial indexes for later map / analytics queries.
CREATE INDEX location_ping_geom_idx ON location_ping USING GIST (geom);
CREATE INDEX trip_start_geom_idx ON trip USING GIST (start_geom);
CREATE INDEX trip_end_geom_idx ON trip USING GIST (end_geom);
CREATE INDEX parking_area_geom_idx ON parking_area USING GIST (geom);
CREATE INDEX road_segment_geom_idx ON road_segment USING GIST (geom);
