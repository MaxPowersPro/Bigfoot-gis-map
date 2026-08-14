"""
John Green Database — Coordinate Converter

Converts the old DDMM / DDMMSS coordinate encoding (e.g. lat=4518, lon=12747)
into standard decimal degrees (e.g. lat=45.3, lon=-127.783) that the map can
actually use.

FORMAT DETECTED (confirmed against known real coordinates for multiple towns):
  4 digits -> DD MM       (2-digit degrees + 2-digit minutes)
  5 digits -> DDD MM      (3-digit degrees + 2-digit minutes)
  6 digits -> DD MM SS    (2-digit degrees + 2-digit minutes + 2-digit seconds)
  7 digits -> DDD MM SS   (3-digit degrees + 2-digit minutes + 2-digit seconds)

Anything else (trailing dashes, wrong digit count, missing value) is DROPPED,
not guessed at -- an honest gap is better than a fabricated coordinate.

Longitude is assumed West (negative) since this is a North America-only
database (Canada & US Sasquatch sightings per John Green's own research scope).

USAGE:
    python3 convert_john_green_coords.py
"""

import requests
import pandas as pd
import io
import re

URL = "https://raw.githubusercontent.com/jameskbride/sasquatch-data-json/master/sasquatch_incident.csv"


def convert_coordinate(raw_value, is_longitude: bool):
    """Returns a decimal-degree float, or None if the value can't be trusted."""
    if pd.isna(raw_value):
        return None

    raw_str = str(raw_value).strip()

    # A trailing dash marks a truncated/incomplete original entry (e.g. "123414-").
    # Stripping it and using the remaining digits would silently fabricate a wrong
    # coordinate -- caught this exact bug testing against Weitchpec, CA before
    # handing this off. Honest move is to drop these, not guess at the missing digit.
    if raw_str.endswith("-"):
        return None

    digits_only = re.sub(r"[^0-9]", "", raw_str)
    if not digits_only:
        return None

    length = len(digits_only)

    try:
        if length == 4:
            degrees = int(digits_only[0:2])
            minutes = int(digits_only[2:4])
            seconds = 0
        elif length == 5:
            degrees = int(digits_only[0:3])
            minutes = int(digits_only[3:5])
            seconds = 0
        elif length == 6:
            degrees = int(digits_only[0:2])
            minutes = int(digits_only[2:4])
            seconds = int(digits_only[4:6])
        elif length == 7:
            degrees = int(digits_only[0:3])
            minutes = int(digits_only[3:5])
            seconds = int(digits_only[5:7])
        else:
            return None  # unrecognized format -- honest skip, not a guess
    except ValueError:
        return None

    if minutes >= 60 or seconds >= 60:
        return None  # not a valid minutes/seconds value -- likely a truncated/bad entry

    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)

    if is_longitude:
        decimal = -decimal  # North America -> West longitude

    return round(decimal, 5)


def main():
    print("Downloading sasquatch_incident.csv...")
    resp = requests.get(URL, timeout=20)
    resp.raise_for_status()
    try:
        df = pd.read_csv(io.StringIO(resp.text))
    except Exception:
        df = pd.read_csv(io.StringIO(resp.text), engine="python", on_bad_lines="skip")

    print(f"Loaded {len(df)} incidents. Converting coordinates...")

    df["latitude"] = df["i_latitude"].apply(lambda v: convert_coordinate(v, is_longitude=False))
    df["longitude"] = df["i_longitude"].apply(lambda v: convert_coordinate(v, is_longitude=True))

    # Sanity bounds check for North America -- catches any remaining bad conversions
    valid_mask = (
        df["latitude"].notna() & df["longitude"].notna() &
        df["latitude"].between(20, 75) & df["longitude"].between(-170, -50)
    )

    total = len(df)
    converted = valid_mask.sum()
    print(f"\nSuccessfully converted: {converted} / {total} ({converted / total * 100:.1f}%)")
    print(f"Dropped (missing, truncated, or out-of-bounds): {total - converted}")

    clean_df = df[valid_mask].copy()

    # Keep a useful, readable set of columns -- not all 83, just what's relevant
    keep_columns = [
        "i_incident_id", "latitude", "longitude", "i_observation_date", "i_year", "i_season",
        "i_state_prov", "i_county", "i_nearest_town", "i_elevation", "i_terrain",
        "i_nearby_water", "i_distance_to_water", "i_tree_cover", "i_undergrowth",
        "i_no_of_witnesses", "i_no_of_individuals", "i_tracks", "i_cast_made",
        "i_source_type", "i_source_reliability", "i_source_date", "i_account_of_incident", "i_name",
    ]
    keep_columns = [c for c in keep_columns if c in clean_df.columns]
    clean_df = clean_df[keep_columns]

    output_path = "john_green_incidents_clean.csv"
    clean_df.to_csv(output_path, index=False)

    print(f"\nSaved to: {output_path}")
    print("\nFirst 5 converted rows:")
    print(clean_df[["i_state_prov", "i_nearest_town", "latitude", "longitude"]].head(5).to_string(index=False))


if __name__ == "__main__":
    main()
