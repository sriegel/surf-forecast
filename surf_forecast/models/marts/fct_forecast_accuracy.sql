with forecasts as (
    select * from {{ ref('fct_marine_forecasts') }}
),

observed as (
    select * from {{ ref('fct_surf_conditions') }}
)

select
    f.valid_time,
    f.forecast_issued_at,
    f.lead_time_hours,

    f.wave_height_m  as forecast_wave_height_m,
    o.wave_height_m  as observed_wave_height_m,
    o.wave_height_m - f.wave_height_m as wave_height_error_m,
    abs(o.wave_height_m - f.wave_height_m) as wave_height_abs_error_m,

    f.swell_height_m as forecast_swell_height_m,
    o.swell_height_m as observed_swell_height_m,
    o.swell_height_m - f.swell_height_m as swell_height_error_m

from forecasts f
inner join observed o
     on f.valid_time = date_trunc('hour', o.timestamp)