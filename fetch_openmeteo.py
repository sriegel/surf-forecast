"""
Fetch marine weather forecast data from the Open-Meteo Marine API.

No API key required. Returns hourly wave/swell forecast data for a
given lat/lon, as JSON with parallel time-series arrays.

Docs: https://open-meteo.com/en/docs/marine-weather-api
"""

import os
from datetime import datetime, timezone

import requests
import pandas as pd

# Coordinates near the Torrey Pines Outer buoy (32.933 N, 117.391 W)
# Using the same location as our NOAA buoy keeps the two sources comparable.
LATITUDE = 32.933
LONGITUDE = -117.391

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
DATA_DIR = "data/raw"

# Hourly variables that map onto the buoy's wave fields:
#   wave_height          ~ WVHT  (combined/significant wave height)
#   wave_direction        ~ MWD   (mean wave direction)
#   wave_period           ~ APD   (average period)
#   swell_wave_height     ~ SwH   (swell height)
#   swell_wave_period     ~ SwP   (swell period)
#   swell_wave_direction  (no direct buoy equivalent, but useful)
HOURLY_VARS = [
    "wave_height",
    "wave_direction",
    "wave_period",
    "swell_wave_height",
    "swell_wave_period",
    "swell_wave_direction",
]


def fetch_marine_forecast(latitude: float, longitude: float) -> dict:
    """Call the Open-Meteo Marine API and return the parsed JSON response."""
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": "UTC",
    }
    response = requests.get(MARINE_URL, params=params, timeout=15)
    response.raise_for_status()
    return response.json()


def parse_marine_response(data: dict) -> pd.DataFrame:
    """
    Convert the Open-Meteo JSON response (parallel arrays under
    data['hourly']) into a tidy DataFrame with one row per hour.
    """
    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.rename(columns={"time": "timestamp"})
    return df


def save_checkpoint(df: pd.DataFrame) -> str:
    """
    Save the forecast DataFrame to a timestamped Parquet file under
    data/raw/. Returns the path written.

    Note: unlike the buoy checkpoint (observed history), this captures
    a forecast *as of* the pull time — re-running later will produce
    a different forecast for overlapping hours, which is expected and
    useful for forecast-accuracy comparisons down the line.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    pulled_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"openmeteo_marine_{pulled_at}.parquet"
    path = os.path.join(DATA_DIR, filename)
    df.to_parquet(path, index=False)
    return path


def main():
    print(f"Fetching Open-Meteo marine forecast for ({LATITUDE}, {LONGITUDE})...")
    data = fetch_marine_forecast(LATITUDE, LONGITUDE)

    df = parse_marine_response(data)

    print(f"\nParsed {len(df)} rows, {len(df.columns)} columns")
    print(f"Columns: {list(df.columns)}\n")

    print("First 5 forecast hours:")
    print(df.head())

    path = save_checkpoint(df)
    print(f"\nSaved checkpoint to: {path}")


if __name__ == "__main__":
    main()