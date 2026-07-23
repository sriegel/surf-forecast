with source as (
    select * from {{ source('bronze', 'raw_marine_forecasts') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by latitude, longitude, forecast_issued_at, valid_time
            order by _loaded_at desc
        ) as rn
    from source
)

select
    latitude,
    longitude,
    forecast_issued_at,
    valid_time,
    wave_height,
    wave_direction,
    wave_period,
    swell_wave_height,
    swell_wave_period,
    swell_wave_direction,
    wind_wave_height,
    wind_wave_period,
    wind_wave_direction
from deduplicated
where rn = 1