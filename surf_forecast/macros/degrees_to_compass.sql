{% macro degrees_to_compass(degrees_column) %}
{#-
    Converts a numeric degrees column (0-360) into a 16-point compass
    direction label (N, NNE, NE, ENE, E, ESE, SE, SSE, S, SSW, SW,
    WSW, W, WNW, NW, NNW).

    Each direction covers a 22.5-degree wedge, centered on its
    compass heading (e.g. 'N' covers 348.75-360 and 0-11.25).
    NULL input passes through as NULL.

    Usage:
        {{ degrees_to_compass('mwd') }} as wave_direction_compass
-#}
case
    when {{ degrees_column }} is null then null
    when {{ degrees_column }} >= 348.75 or {{ degrees_column }} < 11.25  then 'N'
    when {{ degrees_column }} >= 11.25  and {{ degrees_column }} < 33.75  then 'NNE'
    when {{ degrees_column }} >= 33.75  and {{ degrees_column }} < 56.25  then 'NE'
    when {{ degrees_column }} >= 56.25  and {{ degrees_column }} < 78.75  then 'ENE'
    when {{ degrees_column }} >= 78.75  and {{ degrees_column }} < 101.25 then 'E'
    when {{ degrees_column }} >= 101.25 and {{ degrees_column }} < 123.75 then 'ESE'
    when {{ degrees_column }} >= 123.75 and {{ degrees_column }} < 146.25 then 'SE'
    when {{ degrees_column }} >= 146.25 and {{ degrees_column }} < 168.75 then 'SSE'
    when {{ degrees_column }} >= 168.75 and {{ degrees_column }} < 191.25 then 'S'
    when {{ degrees_column }} >= 191.25 and {{ degrees_column }} < 213.75 then 'SSW'
    when {{ degrees_column }} >= 213.75 and {{ degrees_column }} < 236.25 then 'SW'
    when {{ degrees_column }} >= 236.25 and {{ degrees_column }} < 258.75 then 'WSW'
    when {{ degrees_column }} >= 258.75 and {{ degrees_column }} < 281.25 then 'W'
    when {{ degrees_column }} >= 281.25 and {{ degrees_column }} < 303.75 then 'WNW'
    when {{ degrees_column }} >= 303.75 and {{ degrees_column }} < 326.25 then 'NW'
    when {{ degrees_column }} >= 326.25 and {{ degrees_column }} < 348.75 then 'NNW'
end
{% endmacro %}