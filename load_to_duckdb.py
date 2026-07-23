"""
Load Parquet checkpoints from data/raw/ into the surf.duckdb database,
applying the bronze/silver/gold schema defined in schema.sql.

Usage:
    uv run load_to_duckdb.py

Note on idempotency: bronze tables are append-only (re-running re-inserts
the same rows if you re-load the same checkpoint files), and silver
views dedupe on key columns, keeping the most recently loaded row.
If you run this multiple times against the *same* checkpoint files,
bronze will accumulate duplicate rows -- that's expected and harmless,
since silver/gold dedupe on top. If that bothers you, see the note
at the bottom about moving to an incremental load later.
"""

import glob
import os

import duckdb
import pandas as pd

DB_PATH = f"md:surf_forecast?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}"
SCHEMA_PATH = "schema.sql"
DATA_DIR = "data/raw"

# Buoy column names map directly to lowercase DuckDB column names.
BUOY_COLUMN_MAP = {
    "WDIR": "wdir", "WSPD": "wspd", "GST": "gst",
    "PRES": "pres", "ATMP": "atmp", "WTMP": "wtmp", "DEWP": "dewp",
    "VIS": "vis", "PTDY": "ptdy", "TIDE": "tide",
    "WVHT": "wvht", "SwH": "swh", "SwP": "swp",
    "WWH": "wwh", "WWP": "wwp", "SwD": "swd", "WWD": "wwd",
    "STEEPNESS": "steepness", "APD": "apd", "MWD": "mwd",
}


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    """
    Run schema.sql to create bronze tables and silver/gold views.

    schema.sql contains multiple statements (CREATE TABLE, CREATE VIEW,
    separated by semicolons). con.execute() only runs a single
    statement, so we split on ';' and run each one individually,
    skipping blank/comment-only fragments.
    """
    with open(SCHEMA_PATH, "r") as f:
        script = f.read()

    statements = [s.strip() for s in script.split(";")]
    for stmt in statements:
        if not stmt:
            continue
        # Skip fragments that are only comments (e.g. the trailing
        # commented-out fct_forecast_accuracy sketch at the bottom).
        non_comment_lines = [
            line for line in stmt.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        if not non_comment_lines:
            continue
        con.execute(stmt)


def load_buoy_checkpoints(con: duckdb.DuckDBPyConnection) -> int:
    """Load all buoy_*.parquet files into raw_buoy_observations."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "buoy_*.parquet")))
    total_rows = 0

    for path in files:
        df = pd.read_parquet(path)

        # Extract station_id from filename: buoy_46225_<timestamp>.parquet
        basename = os.path.basename(path)
        station_id = basename.split("_")[1]

        df = df.rename(columns=BUOY_COLUMN_MAP)
        df["station_id"] = station_id

        # Keep only columns that exist in the target table; missing
        # ones (e.g. a sensor column absent from a given pull) get
        # filled with NaN -> NULL on insert.
        expected_cols = [
            "station_id", "timestamp", "wdir", "wspd", "gst", "pres",
            "atmp", "wtmp", "dewp", "vis", "ptdy", "tide", "wvht",
            "swh", "swp", "wwh", "wwp", "swd", "wwd", "steepness",
            "apd", "mwd",
        ]
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        df = df[expected_cols]

        con.register("df_tmp", df)
        con.execute(f"""
            INSERT INTO raw_buoy_observations
                ({", ".join(expected_cols)})
            SELECT {", ".join(expected_cols)} FROM df_tmp
        """)
        con.unregister("df_tmp")

        total_rows += len(df)
        print(f"  Loaded {len(df):>5} rows from {basename}")

    return total_rows


def load_openmeteo_checkpoints(con: duckdb.DuckDBPyConnection) -> int:
    """Load all openmeteo_marine_*.parquet files into raw_marine_forecasts."""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "openmeteo_marine_*.parquet")))
    total_rows = 0

    for path in files:
        df = pd.read_parquet(path)

        # forecast_issued_at = when this file was pulled (from filename).
        basename = os.path.basename(path)
        issued_str = basename.replace("openmeteo_marine_", "").replace(".parquet", "")
        forecast_issued_at = pd.to_datetime(issued_str, format="%Y%m%dT%H%M%SZ", utc=True)

        df = df.rename(columns={"timestamp": "valid_time"})
        df["forecast_issued_at"] = forecast_issued_at
        df["latitude"] = 32.933
        df["longitude"] = -117.391

        expected_cols = [
            "latitude", "longitude", "forecast_issued_at", "valid_time",
            "wave_height", "wave_direction", "wave_period",
            "swell_wave_height", "swell_wave_period", "swell_wave_direction",
            "wind_wave_height", "wind_wave_period", "wind_wave_direction",
        ]
        # Older checkpoint files pulled before wind-wave fields were added
        # to HOURLY_VARS won't have those columns -- fill with NULL.
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        df = df[expected_cols]

        con.register("df_tmp", df)
        con.execute(f"""
            INSERT INTO raw_marine_forecasts
                ({", ".join(expected_cols)})
            SELECT {", ".join(expected_cols)} FROM df_tmp
        """)
        con.unregister("df_tmp")

        total_rows += len(df)
        print(f"  Loaded {len(df):>5} rows from {basename}")

    return total_rows


def main():
    con = duckdb.connect(DB_PATH)
    # Pin the session timezone so tz-aware pandas columns convert to the
    # naive TIMESTAMP columns consistently regardless of which machine
    # runs this script (local dev vs. the UTC GitHub Actions runner).
    # Without this, DuckDB converts using the client's local system
    # timezone, silently shifting every timestamp loaded from a non-UTC
    # machine.
    con.execute("SET TimeZone='UTC'")
    init_schema(con)

    print("Loading buoy checkpoints into raw_buoy_observations...")
    buoy_rows = load_buoy_checkpoints(con)

    print("\nLoading Open-Meteo checkpoints into raw_marine_forecasts...")
    forecast_rows = load_openmeteo_checkpoints(con)

    print(f"\nTotal: {buoy_rows} buoy rows, {forecast_rows} forecast rows loaded.")

    # Quick sanity check via the gold view.
    result = con.execute("""
        SELECT count(*) AS n, min(timestamp) AS earliest, max(timestamp) AS latest
        FROM fct_surf_conditions
    """).fetchone()
    print(f"\nfct_surf_conditions: {result[0]} rows, {result[1]} to {result[2]}")

    con.close()
    print("\nDatabase saved to: md:surf_forecast")


if __name__ == "__main__":
    main()