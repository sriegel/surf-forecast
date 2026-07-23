select
    latitude,
    longitude,
    forecast_issued_at,
    (forecast_issued_at at time zone 'UTC') at time zone 'America/Los_Angeles' as forecast_issued_at_local,
    valid_time,
    (valid_time at time zone 'UTC') at time zone 'America/Los_Angeles' as valid_time_local,
    date_diff('hour', forecast_issued_at, valid_time) as lead_time_hours,

    wave_height                     as wave_height_m,
    round(wave_height * 3.28084, 1) as wave_height_ft,

    swell_wave_height                     as swell_height_m,
    round(swell_wave_height * 3.28084, 1) as swell_height_ft,

    swell_wave_period as swell_period_s,
    wave_period       as avg_period_s,

    wave_direction as wave_direction_deg,
    {{ degrees_to_compass('wave_direction') }} as wave_direction_compass,

    swell_wave_direction as swell_direction_deg,
    {{ degrees_to_compass('swell_wave_direction') }} as swell_direction_compass,

    wind_wave_height                     as wind_wave_height_m,
    round(wind_wave_height * 3.28084, 1) as wind_wave_height_ft,

    wind_wave_period as wind_wave_period_s,

    wind_wave_direction as wind_wave_direction_deg,
    {{ degrees_to_compass('wind_wave_direction') }} as wind_wave_direction_compass

from {{ ref('stg_marine_forecasts') }}