import os
import pandas as pd
import streamlit as st

@st.cache_data
def load_and_standardize_dataset(file_path):
    """
    Reads any CSV file, auto-detects coordinate and text columns,
    and returns a standardized list of dicts for Map & Library rendering.
    """
    if not os.path.exists(file_path):
        return []

    try:
        # Flexible loader handling tabs, bad lines, and comma errors
        df = pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip')
    except Exception:
        return []

    # Lowercase all column headers for easy matching
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Flexible column resolution lists
    lat_cols = ['latitude', 'lat', 'y', 'lat_deg']
    lon_cols = ['longitude', 'lon', 'lng', 'x', 'lon_deg']
    title_cols = ['title', 'headline', 'subject', 'report_id', 'number']
    text_cols = ['observed', 'summary', 'description', 'text', 'story', 'narrative']
    date_cols = ['date', 'event_date', 'year', 'timestamp']

    def find_best_col(options, default=None):
        for opt in options:
            if opt in df.columns:
                return opt
        return default

    col_lat = find_best_col(lat_cols)
    col_lon = find_best_col(lon_cols)
    col_title = find_best_col(title_cols)
    col_text = find_best_col(text_cols)
    col_date = find_best_col(date_cols)

    standardized_records = []

    for idx, row in df.iterrows():
        # Get coordinates
        try:
            lat = float(row[col_lat]) if col_lat and pd.notna(row[col_lat]) else None
            lon = float(row[col_lon]) if col_lon and pd.notna(row[col_lon]) else None
        except ValueError:
            continue

        if lat is None or lon is None:
            continue

        # Extract Core Standard Fields
        record_id = str(row.get('number', row.get('id', idx)))
        title = str(row[col_title]) if col_title and pd.notna(row[col_title]) else f"Report #{record_id}"
        summary = str(row[col_text]) if col_text and pd.notna(row[col_text]) else "No narrative recorded."
        event_date = str(row[col_date]) if col_date and pd.notna(row[col_date]) else "Unknown Date"

        # Pack ALL remaining unique/extra columns into a flexible metadata dict
        extra_metadata = {}
        for col in df.columns:
            if col not in [col_lat, col_lon, col_title, col_text, col_date]:
                val = row[col]
                if pd.notna(val):
                    extra_metadata[col] = str(val)

        standardized_records.append({
            "id": record_id,
            "title": title,
            "latitude": lat,
            "longitude": lon,
            "event_date": event_date,
            "summary": summary,
            "metadata": extra_metadata  # Preserves weather, classification, county, etc.
        })

    return standardized_records
