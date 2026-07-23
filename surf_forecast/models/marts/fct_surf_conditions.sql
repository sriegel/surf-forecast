select
    station_id,
    timestamp,
    (timestamp at time zone 'UTC') at time zone 'America/Los_Angeles' as timestamp_local,

    -- wave/swell heights: meters and feet (1 m = 3.28084 ft)
    wvht                       as wave_height_m,
    round(wvht * 3.28084, 1)   as wave_height_ft,
    swh                        as swell_height_m,
    round(swh * 3.28084, 1)    as swell_height_ft,

    swp   as swell_period_s,
    swd   as swell_direction_compass,
    apd   as avg_period_s,

    -- wind waves: locally-generated seas, distinct from groundswell
    wwh                        as wind_wave_height_m,
    round(wwh * 3.28084, 1)    as wind_wave_height_ft,
    wwp                        as wind_wave_period_s,
    wwd                        as wind_wave_direction_compass,

    steepness,

    -- direction: degrees and 16-point compass
    mwd as wave_direction_deg,
    {{ degrees_to_compass('mwd') }} as wave_direction_compass,

    wspd  as wind_speed_ms,
    wdir  as wind_direction_deg,
    {{ degrees_to_compass('wdir') }} as wind_direction_compass,

    wtmp                      as water_temp_c,
    round(wtmp * 9/5 + 32, 1) as water_temp_f

from {{ ref('stg_buoy_observations') }}