import pandas as pd
import streamlit as st
from supabase import create_client

# Direct working URL to the geocoded dataset repository
DATA_URL = "https://raw.githubusercontent.com/datasets/bigfoot-locations/main/data/bfro_reports_geocoded.csv"

def run_import():
    st.info("🚀 Starting dataset import directly from the web source...")
    
    # 1. Connect to Supabase
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        return

    # 2. Fetch directly from the web URL
    try:
        df = pd.read_csv(DATA_URL)
        st.write(f"📊 Successfully fetched dataset with {len(df)} rows.")
    except Exception as e:
        st.error(f"Failed to load dataset from web: {e}")
        return

    # 3. Clean and structure records
    records = []
    for idx, row in df.iterrows():
        lat = row.get("latitude")
        lon = row.get("longitude")
        
        if pd.isna(lat) or pd.isna(lon):
            continue

        report_id = str(row.get("number", idx)).split(".")[0]
        title_str = str(row.get("title", f"BFRO Report #{report_id}"))
        if title_str == "nan":
            title_str = f"BFRO Report #{report_id}"

        summary_text = str(row.get("observed", row.get("summary", "No transcript body recorded.")))
        if summary_text == "nan":
            summary_text = "No transcript body recorded."

        records.append({
            "report_id": report_id,
            "title": title_str,
            "class_rating": str(row.get("classification", "Class A")),
            "event_date": str(row.get("date", "N/A")),
            "summary": summary_text,
            "latitude": float(lat),
            "longitude": float(lon),
            "dist_to_road_miles": 0.5,
            "pop_density_sq_mi": 30.0,
            "has_tracks": "track" in summary_text.lower() or "footprint" in summary_text.lower(),
            "has_hair": "hair" in summary_text.lower(),
            "has_physical_evidence": "cast" in summary_text.lower() or "dna" in summary_text.lower()
        })

    st.write(f"⚙️ Formatted {len(records)} geocoded records. Upserting to Supabase...")

    # 4. Batch upsert into Supabase
    batch_size = 200
    total_inserted = 0
    progress_bar = st.progress(0)

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        try:
            supabase.table("sighting_reports").upsert(batch, on_conflict="report_id").execute()
            total_inserted += len(batch)
            progress_bar.progress(min(total_inserted / len(records), 1.0))
        except Exception as e:
            st.warning(f"Batch insert error on row {i}: {e}")

    st.success(f"🔥 SUCCESS! Inserted {total_inserted} geocoded reports into Supabase!")

run_import()
