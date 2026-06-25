with source as (
    select * from {{ source('bronze', 'raw_buoy_observations') }}
),

deduplicated as (
    select
        *,
        row_number() over (
            partition by station_id, timestamp
            order by _loaded_at desc
        ) as rn
    from source
)

select
    station_id,
    timestamp,
    wdir, wspd, gst,
    pres, atmp, wtmp, dewp, vis, ptdy, tide,
    wvht, swh, swp, wwh, wwp, swd, wwd, steepness, apd, mwd
from deduplicated
where rn = 1