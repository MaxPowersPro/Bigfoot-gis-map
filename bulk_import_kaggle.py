import pandas as pd
import streamlit as st
from supabase import create_client

# Direct web source for the geocoded BFRO dataset
DATA_URL = "bfro_reports_geocoded.csv"
def run_import():
    st.write("🚀 Starting bulk import from web source...")
    
    # 1. Connect using Streamlit Secrets
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        supabase = create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        return

    # 2. Download and parse CSV directly from the web
    try:
        try:
    df = pd.read_csv(DATA_URL, sep=None, engine='python', on_bad_lines='skip')
except Exception:
    df = pd.read_csv(DATA_URL, sep='\t', engine='python', on_bad_lines='skip')
        st.write(f"📊 Downloaded {len(df)} raw rows from web dataset.")
    except Exception as e:
        st.error(f"Failed to fetch CSV dataset: {e}")
        return

    # 3. Clean and map columns
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

    # 4. Batch upsert into Supabase
    batch_size = 250
    total_inserted = 0
    progress_bar = st.progress(0)

    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        try:
            supabase.table("sighting_reports").upsert(batch, on_conflict="report_id").execute()
            total_inserted += len(batch)
            progress_bar.progress(min(total_inserted / len(records), 1.0))
        except Exception as e:
            st.warning(f"Batch insert warning: {e}")

    st.success(f"🔥 SUCCESS! Inserted {total_inserted} geocoded reports into Supabase!")

if __name__ == "__main__":
    run_import()
