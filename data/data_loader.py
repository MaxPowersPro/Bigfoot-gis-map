import os
import pandas as pd

def load_and_standardize_dataset(file_path):
    if not os.path.exists(file_path):
        return []

    try:
        df = pd.read_csv(file_path, engine='python', on_bad_lines='skip')
    except Exception:
        return []

    df.columns = [str(col).strip().lower() for col in df.columns]

    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        return []

    valid_coords = df[df['latitude'].notna() & df['longitude'].notna()]

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

    return records
