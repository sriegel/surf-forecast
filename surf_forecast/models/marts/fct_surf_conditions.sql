select
    station_id,
    timestamp,
    wvht  as wave_height_m,
    swh   as swell_height_m,
    swp   as swell_period_s,
    apd   as avg_period_s,
    mwd   as wave_direction_deg,
    wspd  as wind_speed_ms,
    wdir  as wind_direction_deg,
    wtmp  as water_temp_c
from {{ ref('stg_buoy_observations') }}