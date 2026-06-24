import os
from datetime import datetime, timezone

import requests
import pandas as pd
from io import StringIO

STATION_ID = "46225"
BASE_URL = "https://www.ndbc.noaa.gov/data/realtime2/{station_id}.{ext}"
DATA_DIR = "data/raw"


def fetch_raw_text(station_id: str, ext: str = "txt") -> str:
    url = BASE_URL.format(station_id=station_id, ext=ext)
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.text


def parse_buoy_text(raw_text: str) -> pd.DataFrame:
    lines = raw_text.strip().split("\n")
    header = lines[0].lstrip("#").split()
    data_lines = lines[2:]
    df = pd.read_csv(
        StringIO("\n".join(data_lines)),
        sep=r"\s+",
        names=header,
        na_values=["MM"],
    )
    return df


def add_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Combine YY/MM/DD/hh/mm columns into a single UTC timestamp column."""
    df = df.copy()
    df["timestamp"] = pd.to_datetime(
        dict(year=df["YY"], month=df["MM"], day=df["DD"],
             hour=df["hh"], minute=df["mm"]),
        utc=True,
    )
    df = df.drop(columns=["YY", "MM", "DD", "hh", "mm"])
    # Reorder so timestamp leads
    cols = ["timestamp"] + [c for c in df.columns if c != "timestamp"]
    return df[cols]


def merge_met_and_wave(met_df: pd.DataFrame, wave_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge meteorological and wave-summary observations on timestamp.

    Wave fields (WVHT, APD, MWD) exist in both feeds; the .spec feed
    is the authoritative source for wave data on this station, so we
    drop those columns from the met side before merging to avoid
    duplicate/conflicting columns.
    """
    met_only = met_df.drop(columns=["WVHT", "APD", "MWD"], errors="ignore")
    merged = pd.merge(
        met_only, wave_df,
        on="timestamp",
        how="inner",          # keep only timestamps present in both feeds
        suffixes=("", "_dup"),
    )
    return merged


def save_checkpoint(df: pd.DataFrame, station_id: str) -> str:
    """
    Save the merged DataFrame to a timestamped Parquet file under
    data/raw/. Returns the path written.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    pulled_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = f"buoy_{station_id}_{pulled_at}.parquet"
    path = os.path.join(DATA_DIR, filename)
    df.to_parquet(path, index=False)
    return path


def main():
    met_raw = fetch_raw_text(STATION_ID, ext="txt")
    met_df = add_timestamp(parse_buoy_text(met_raw))

    wave_raw = fetch_raw_text(STATION_ID, ext="spec")
    wave_df = add_timestamp(parse_buoy_text(wave_raw))

    print(f"Met rows: {len(met_df)} | Wave rows: {len(wave_df)}")

    merged = merge_met_and_wave(met_df, wave_df)

    print(f"Merged rows: {len(merged)}")
    print(f"Merged columns: {list(merged.columns)}\n")
    print(merged.head())

    path = save_checkpoint(merged, STATION_ID)
    print(f"\nSaved checkpoint to: {path}")


if __name__ == "__main__":
    main()