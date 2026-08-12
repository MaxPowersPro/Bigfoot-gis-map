import os
import pandas as pd
import streamlit as st

@st.cache_data
def load_and_standardize_dataset(file_path):
    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path, sep=None, engine='python', on_bad_lines='skip')
    except Exception:
        try:
            df = pd.read_csv(file_path, sep='\t', engine='python', on_bad_lines='skip')
        except Exception:
            return []

    if df.empty:
        return []

    # Clean headers
    df.columns = [str(col).strip().lower() for col in df.columns]

    standardized_records = []

    for idx, row in df.iterrows():
        # Safely convert coordinates
        raw_lat = row.get('latitude')
        raw_lon = row.get('longitude')

        if pd.isna(raw_lat) or pd.isna(raw_lon):
            continue

        try:
            lat = float(raw_lat)
            lon = float(raw_lon)
        except (ValueError, TypeError):
            continue

        record_id = str(row.get('number', idx)).split('.')[0]
        title = str(row.get('title', f"Report #{record_id}"))
        if title == "nan":
            title = f"Report #{record_id}"

        summary = str(row.get('observed', row.get('summary', "No narrative recorded.")))
        if summary == "nan":
            summary = "No narrative recorded."

        event_date = str(row.get('date', "Unknown Date"))

        # Pack weather, season, classification, county, etc. into flexible metadata
        extra_metadata = {}
        for col in df.columns:
            if col not in ['latitude', 'longitude', 'title', 'observed', 'summary', 'date']:
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
            "metadata": extra_metadata
        })

    return standardized_records
