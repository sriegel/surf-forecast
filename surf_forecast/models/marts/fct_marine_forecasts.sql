select
    latitude,
    longitude,
    forecast_issued_at,
    valid_time,
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
    {{ degrees_to_compass('swell_wave_direction') }} as swell_direction_compass

from {{ ref('stg_marine_forecasts') }}