import streamlit as st
import pydeck as pdk
import pandas as pd
import numpy as np
from supabase import create_client, Client

# Page setup for large displays
st.set_page_config(
    page_title="Bigfoot Field Map & Research Engine",
    page_icon="🌲",
    layout="wide"
)
st.title("🌲 Bigfoot Field Map & Research Engine")

# 1. MAPBOX & SUPABASE CREDENTIALS
MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"⚠️ Supabase Init Failed: {e}")
        return None

supabase = init_supabase()

# 2. FETCH DATA FROM SUPABASE
@st.cache_data(ttl=600)
def load_data():
    if not supabase:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
    sightings = supabase.table("sighting_reports").select("title, class_rating, latitude, longitude, summary").execute()
    media = supabase.table("historical_media").select("title, publication_name, latitude, longitude, full_text_transcript").execute()
    campsites = supabase.table("campsites").select("name, type, latitude, longitude").execute()
    
    df_sightings = pd.DataFrame(sightings.data) if sightings.data else pd.DataFrame()
    df_media = pd.DataFrame(media.data) if media.data else pd.DataFrame()
    df_campsites = pd.DataFrame(campsites.data) if campsites.data else pd.DataFrame()
    
    return df_sightings, df_media, df_campsites

df_sightings, df_media, df_campsites = load_data()

# 3. SIDEBAR CONTROLS
st.sidebar.header("🗺️ Map Layer Toggles")
show_hotspots = st.sidebar.checkbox("🔴 Probability Hot Zones (Red Boundaries)", value=True)
show_larson = st.sidebar.checkbox("🌲 The Larson Hypothesis (Amorphous Corridors)", value=True)
show_campsites = st.sidebar.checkbox("🏕️ Campsites & Dispersed Areas", value=True)

# 4. ALGORITHM: URBAN MASK & HOTZONE CLUSTERING
def filter_urban(lat, lon):
    # Rule out high-density urban polygons (e.g., Asheville NC region, city centers)
    urban_bounds = [
        {"min_lat": 35.5, "max_lat": 35.7, "min_lon": -82.65, "max_lon": -82.45}, # Asheville
    ]
    for b in urban_bounds:
        if b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]:
            return True
    return False

# Combine research reports into coordinate matrix
all_coords = []
for df in [df_sightings, df_media]:
    if not df.empty and "latitude" in df and "longitude" in df:
        valid_df = df.dropna(subset=["latitude", "longitude"])
        all_coords.extend(valid_df[["latitude", "longitude"]].values.tolist())

hotspot_polygons = []
corridor_polygons = []

if len(all_coords) > 0:
    coords_arr = np.array(all_coords)
    
    # Pure NumPy Euclidean distance matrix calculation
    dist_matrix = np.sqrt(((coords_arr[:, np.newaxis, :] - coords_arr[np.newaxis, :, :]) ** 2).sum(axis=-1))
    
    clusters = []
    visited = set()
    MIN_POINTS = 3
    RADIUS_DEG = 0.25
    
    for i, pt in enumerate(coords_arr):
        if i in visited:
            continue
        neighbors = np.where(dist_matrix[i] < RADIUS_DEG)[0]
        if len(neighbors) >= MIN_POINTS:
            center_lat = np.mean(coords_arr[neighbors, 0])
            center_lon = np.mean(coords_arr[neighbors, 1])
            if not filter_urban(center_lat, center_lon):
                clusters.append({"lat": center_lat, "lon": center_lon, "count": len(neighbors)})
                visited.update(neighbors)

    # Generate Red Hot Zone Boundaries (No raw individual pins)
    for c in clusters:
        angles = np.linspace(0, 2 * np.pi, 16)
        r = 0.15 + (c["count"] * 0.02)
        polygon = [[c["lon"] + r * np.cos(a), c["lat"] + r * np.sin(a)] for a in angles]
        hotspot_polygons.append({"polygon": polygon, "score": f"Probability Score: {c['count']} linked indicators"})

    # Generate "The Larson Hypothesis" Amorphous Flow Corridors
    if len(clusters) > 1:
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                c1, c2 = clusters[i], clusters[j]
                d = np.sqrt((c1["lat"] - c2["lat"])**2 + (c1["lon"] - c2["lon"])**2)
                if d < 1.5:
                    vec = np.array([c2["lon"] - c1["lon"], c2["lat"] - c1["lat"]])
                    perp = np.array([-vec[1], vec[0]])
                    perp = perp / (np.linalg.norm(perp) + 1e-6) * 0.08
                    
                    p1 = [c1["lon"] + perp[0], c1["lat"] + perp[1]]
                    p2 = [c2["lon"] + perp[0], c2["lat"] + perp[1]]
                    p3 = [c2["lon"] - perp[0], c2["lat"] - perp[1]]
                    p4 = [c1["lon"] - perp[0], c1["lat"] - perp[1]]
                    
                    corridor_polygons.append({"polygon": [p1, p2, p3, p4]})

# 5. CONSTRUCT PYDECK LAYERS
layers = []

# HOT ZONES LAYER
if show_hotspots and hotspot_polygons:
    hotzone_layer = pdk.Layer(
        "PolygonLayer",
        data=hotspot_polygons,
        get_polygon="polygon",
        get_fill_color=[239, 68, 68, 120],
        get_line_color=[220, 38, 38, 255],
        get_line_width=3,
        stroked=True,
        filled=True,
        pickable=True,
    )
    layers.append(hotzone_layer)

# THE LARSON HYPOTHESIS LAYER
if show_larson and corridor_polygons:
    larson_layer = pdk.Layer(
        "PolygonLayer",
        data=corridor_polygons,
        get_polygon="polygon",
        get_fill_color=[34, 197, 94, 90],
        get_line_color=[22, 163, 74, 180],
        get_line_width=2,
        stroked=True,
        filled=True,
        pickable=True,
    )
    layers.append(larson_layer)

# CAMPSITES LAYER
if show_campsites and not df_campsites.empty:
    tent_icon_data = {
        "url": "https://img.icons8.com/color/48/tent.png",
        "width": 128,
        "height": 128,
        "anchorY": 128
    }
    
    campsite_layer = pdk.Layer(
        "IconLayer",
        data=df_campsites,
        get_icon=lambda d: tent_icon_data,
        get_size=5,
        size_scale=8,
        get_position=["longitude", "latitude"],
        pickable=True,
    )
    layers.append(campsite_layer)

# 6. INITIAL MAP VIEW
view_state = pdk.ViewState(
    latitude=39.8283,
    longitude=-98.5795,
    zoom=4,
    pitch=0
)

# 7. RENDER MAP
r = pdk.Deck(
    layers=layers,
    initial_view_state=view_state,
    api_keys={"mapbox": MAPBOX_TOKEN},
    map_style="mapbox://styles/mapbox/outdoors-v12",
    tooltip={"text": "{name}\n{score}"}
)

st.pydeck_chart(r, use_container_width=True)
