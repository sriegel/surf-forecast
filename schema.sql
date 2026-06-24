-- DuckDB schema for the surf forecast pipeline.
-- Run with: duckdb surf.duckdb < schema.sql
-- Or interactively: duckdb surf.duckdb, then .read schema.sql

-- ============================================================
-- BRONZE: raw, append-only, minimally transformed
-- ============================================================

-- Loaded directly from data/raw/*.parquet via Python/dbt seed.
-- One row per observation per buoy station. Never updated, never
-- deduplicated here -- that happens in silver.
CREATE TABLE IF NOT EXISTS raw_buoy_observations (
    station_id      VARCHAR,
    timestamp       TIMESTAMP,
    wdir            DOUBLE,
    wspd            DOUBLE,
    gst             DOUBLE,
    pres            DOUBLE,
    atmp            DOUBLE,
    wtmp            DOUBLE,
    dewp            DOUBLE,
    vis             DOUBLE,
    ptdy            DOUBLE,
    tide            DOUBLE,
    wvht            DOUBLE,
    swh             DOUBLE,
    swp             DOUBLE,
    wwh             DOUBLE,
    wwp             DOUBLE,
    swd             VARCHAR,
    wwd             VARCHAR,
    steepness       VARCHAR,
    apd             DOUBLE,
    mwd             DOUBLE,
    _loaded_at      TIMESTAMP DEFAULT current_timestamp
);

-- Loaded from each Open-Meteo checkpoint parquet. Importantly,
-- forecast_issued_at captures *when this forecast was made* --
-- the same future hour will appear multiple times across different
-- pulls, each time with a (likely slightly different) prediction.
CREATE TABLE IF NOT EXISTS raw_marine_forecasts (
    latitude              DOUBLE,
    longitude             DOUBLE,
    forecast_issued_at    TIMESTAMP,   -- when the pipeline pulled this
    valid_time            TIMESTAMP,   -- the hour this prediction is for
    wave_height           DOUBLE,
    wave_direction        DOUBLE,
    wave_period           DOUBLE,
    swell_wave_height     DOUBLE,
    swell_wave_period     DOUBLE,
    swell_wave_direction  DOUBLE,
    _loaded_at            TIMESTAMP DEFAULT current_timestamp
);


-- ============================================================
-- SILVER: cleaned, typed, deduplicated
-- ============================================================

-- One row per (station, timestamp). If the same hour was pulled
-- more than once (re-running the script), keep only the latest load.
CREATE OR REPLACE VIEW stg_buoy_observations AS
SELECT
    station_id,
    timestamp,
    wdir, wspd, gst,
    pres, atmp, wtmp, dewp, vis, ptdy, tide,
    wvht, swh, swp, wwh, wwp, swd, wwd, steepness, apd, mwd
FROM (
    SELECT *,
        row_number() OVER (
            PARTITION BY station_id, timestamp
            ORDER BY _loaded_at DESC
        ) AS rn
    FROM raw_buoy_observations
)
WHERE rn = 1;

-- One row per (lat, lon, forecast_issued_at, valid_time). Forecast
-- snapshots are kept distinct on purpose -- do not dedupe across
-- forecast_issued_at, since that's exactly what lets us compare
-- forecasts made at different lead times later.
CREATE OR REPLACE VIEW stg_marine_forecasts AS
SELECT
    latitude, longitude,
    forecast_issued_at,
    valid_time,
    wave_height, wave_direction, wave_period,
    swell_wave_height, swell_wave_period, swell_wave_direction
FROM (
    SELECT *,
        row_number() OVER (
            PARTITION BY latitude, longitude, forecast_issued_at, valid_time
            ORDER BY _loaded_at DESC
        ) AS rn
    FROM raw_marine_forecasts
)
WHERE rn = 1;


-- ============================================================
-- GOLD: analysis-ready
-- ============================================================

-- The "what actually happened" table -- one row per observed hour.
CREATE OR REPLACE VIEW fct_surf_conditions AS
SELECT
    station_id,
    timestamp,
    wvht  AS wave_height_m,
    swh   AS swell_height_m,
    swp   AS swell_period_s,
    apd   AS avg_period_s,
    mwd   AS wave_direction_deg,
    wspd  AS wind_speed_ms,
    wdir  AS wind_direction_deg,
    wtmp  AS water_temp_c
FROM stg_buoy_observations;

-- fct_forecast_accuracy comes later, once we've accumulated multiple
-- forecast_issued_at snapshots to compare against observed reality.
-- Sketch (not yet runnable -- needs lead_time_hours logic):
--
-- SELECT
--     f.valid_time,
--     f.forecast_issued_at,
--     date_diff('hour', f.forecast_issued_at, f.valid_time) AS lead_time_hours,
--     f.wave_height AS forecast_wave_height_m,
--     o.wave_height_m AS observed_wave_height_m,
--     o.wave_height_m - f.wave_height AS error_m
-- FROM stg_marine_forecasts f
-- JOIN fct_surf_conditions o ON o.timestamp = f.valid_time