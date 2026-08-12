import os
import pandas as pd
import streamlit as st

def load_and_standardize_dataset(file_path):
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔍 Loader Diagnostics")
    
    if not os.path.exists(file_path):
        st.sidebar.error(f"❌ File path does not exist: `{file_path}`")
        return []

    try:
        df = pd.read_csv(file_path, engine='python', on_bad_lines='skip')
        st.sidebar.write(f"📁 Opened file. Total rows: `{len(df)}`")
    except Exception as e:
        st.sidebar.error(f"❌ Read failure: {e}")
        return []

    df.columns = [str(col).strip().lower() for col in df.columns]
    st.sidebar.write(f"🏷️ Columns detected: `{list(df.columns)[:5]}...`")

    # Check coordinate presence
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        st.sidebar.error("❌ 'latitude' or 'longitude' column missing from header.")
        return []

    # Count valid coordinates
    valid_coords = df[df['latitude'].notna() & df['longitude'].notna()]
    st.sidebar.write(f"📍 Rows with non-null lat/lon: `{len(valid_coords)}`")

    records = []
    for idx, row in valid_coords.iterrows():
        try:
            records.append({
                "id": str(row.get('number', idx)),
                "title": str(row.get('title', f"Report #{idx}")),
                "latitude": float(row['latitude']),
                "longitude": float(row['longitude']),
                "summary": str(row.get('observed', row.get('summary', ''))),
                "metadata": row.to_dict()
            })
        except Exception:
            continue

    st.sidebar.success(f"✅ Successfully converted `{len(records)}` records!")
    return records
