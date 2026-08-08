import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation
import random
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import numpy as np

# ==========================================
# 1. PAGE SETUP & SESSION STATE INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👣 Bigfoot Field Analysis Platform")
st.caption("Site-Specific Spatial Map & Predictive Multi-Criteria Infrasound Analysis Engine")

if "user_lat" not in st.session_state:
    st.session_state.user_lat = 41.7000
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -70.3000
if "location_name" not in st.session_state:
    st.session_state.location_name = "Massachusetts Target Zone"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)

# ==========================================
# 2. SUPABASE CLOUD CONNECTION & UTILITIES
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        if not url or not key:
            st.warning("⚠️ Supabase credentials missing in Streamlit Cloud Secrets.")
            return None
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Supabase Init Failed: {e}")
        return None

supabase: Client = init_supabase()

def apply_jitter(lat_val, lon_val, offset_seed=0):
    random.seed(int(lat_val * 1000) + int(lon_val * 1000) + offset_seed)
    lat_jitter = lat_val + random.uniform(-0.003, 0.003)
    lon_jitter = lon_val + random.uniform(-0.003, 0.003)
    return lat_jitter, lon_jitter

def get_season(date_str):
    if not date_str or date_str == 'N/A':
        return 'Unknown'
    try:
        month = int(str(date_str).split('-')[1])
        if month in [12, 1, 2]:
            return '❄️ Winter'
        elif month in [3, 4, 5]:
            return '🌸 Spring'
        elif month in [6, 7, 8]:
            return '☀️ Summer'
        elif month in [9, 10, 11]:
            return '🍂 Autumn'
    except Exception:
        return 'Unknown'

def filter_urban(check_lat, check_lon):
    urban_bounds = [
        {"min_lat": 35.5, "max_lat": 35.7, "min_lon": -82.65, "max_lon": -82.45},
        {"min_lat": 27.8, "max_lat": 28.1, "min_lon": -82.55, "max_lon": -82.30},
        {"min_lat": 28.4, "max_lat": 28.65, "min_lon": -81.50, "max_lon": -81.20},
        {"min_lat": 38.0, "max_lat": 38.2, "min_lon": -84.6, "max_lon": -84.4},
    ]
    for b in urban_bounds:
        if b["min_lat"] <= check_lat <= b["max_lat"] and b["min_lon"] <= check_lon <= b["max_lon"]:
            return True
    return False

def generate_gpx(target_lat, target_lon, loc_title, sightings, camps, audio, community_logs):
    gpx = ET.Element("gpx", version="1.1", creator="BigfootFieldPlatform", xmlns="http://www.topografix.com/GPX/1/1")
    wpt_target = ET.SubElement(gpx, "wpt", lat=str(target_lat), lon=str(target_lon))
    ET.SubElement(wpt_target, "name").text = f"TARGET: {loc_title}"
    ET.SubElement(wpt_target, "sym").text = "Cross-Hair"
    
    for s in sightings:
        wpt = ET.SubElement(gpx, "wpt", lat=str(s.get("latitude")), lon=str(s.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Sighting: {s.get('title', 'BFRO Report')}"
        ET.SubElement(wpt, "desc").text = f"Date: {s.get('event_date', 'N/A')} | Summary: {s.get('summary', '')}"
        ET.SubElement(wpt, "sym").text = "Footprint"

    for a in audio:
        wpt = ET.SubElement(gpx, "wpt", lat=str(a.get("latitude")), lon=str(a.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Audio: {a.get('event_type', 'Infrasound Log')}"
        ET.SubElement(wpt, "desc").text = a.get('notes', '')
        ET.SubElement(wpt, "sym").text = "Sound"

    return ET.tostring(gpx, encoding="utf-8", method="xml")

# ==========================================
# 3. HISTORIC TRIBAL TERRITORY POLYGONS
# ==========================================
TRIBAL_BOUNDARIES = {
    "Eastern Band of Cherokee": Polygon([(-85.5, 33.5), (-85.5, 37.0), (-80.5, 37.0), (-80.5, 33.5), (-85.5, 33.5)]),
    "Coast Salish / Halkomelem": Polygon([(-125.0, 46.5), (-125.0, 50.0), (-121.0, 50.0), (-121.0, 46.5), (-125.0, 46.5)]),
    "Choctaw Nation": Polygon([(-90.5, 30.5), (-90.5, 35.0), (-87.0, 35.0), (-87.0, 30.5), (-90.5, 30.5)]),
    "Klamath / Modoc / Yurok": Polygon([(-124.5, 40.0), (-124.5, 44.0), (-120.0, 44.0), (-120.0, 40.0), (-124.5, 40.0)]),
    "Ojibwe / Anishinaabe": Polygon([(-95.0, 44.0), (-95.0, 50.0), (-80.0, 50.0), (-80.0, 44.0), (-95.0, 44.0)]),
    "Cree Nation": Polygon([(-120.0, 51.0), (-120.0, 60.0), (-70.0, 60.0), (-70.0, 51.0), (-120.0, 51.0)]),
    "Haudenosaunee / Iroquois": Polygon([(-79.0, 41.0), (-79.0, 46.0), (-71.0, 46.0), (-71.0, 41.0), (-79.0, 41.0)]),
    "Tlingit / Athabascan": Polygon([(-155.0, 58.0), (-155.0, 68.0), (-130.0, 68.0), (-130.0, 58.0), (-155.0, 58.0)])
}

# ==========================================
# 4. SIDEBAR CONTROLS & GEOCODING
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN", "")
    if not token:
        st.error("Mapbox token missing in Streamlit Secrets.")
        return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
    params = {"access_token": token, "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("features"):
                feature = data["features"][0]
                lon_val, lat_val = feature["center"]
                place_name = feature.get("place_name", query)
                return lat_val, lon_val, place_name
    except Exception:
        pass
    return None

with st.sidebar:
    st.header("⚙️ Field Controls")
    
    loc_search = st.text_input("📍 Target Search Area", value=loc_name)
    radius_miles = st.selectbox("Field Radius (Miles)", [25, 50, 100, 250], index=1)
    deg_delta = radius_miles / 69.0
    regional_deg_delta = 100.0 / 69.0

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        search_btn = st.button("🔎 Search Area", use_container_width=True)
    with col_s2:
        gps_btn = st.button("📲 Use Device GPS", use_container_width=True)

    if search_btn and loc_search:
        res = geocode_mapbox(loc_search)
        if res:
            st.session_state.user_lat = res[0]
            st.session_state.user_lon = res[1]
            st.session_state.location_name = res[2]
            st.success("Target updated!")
            st.rerun()

    if gps_btn:
        loc_data = get_geolocation()
        if loc_data and "coords" in loc_data:
            st.session_state.user_lat = loc_data["coords"]["latitude"]
            st.session_state.user_lon = loc_data["coords"]["longitude"]
            st.session_state.location_name = f"Current GPS ({st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f})"
            st.rerun()

    st.markdown("---")
    st.subheader("🗺️ Active Map Layers")
    
    show_bfro = st.checkbox("👣 Sightings (Blue/Purple)", value=True)
    show_lore = st.checkbox("🪶 Regional Lore Net", value=True)
    show_news = st.checkbox("📰 Regional Press Net", value=True)
    show_user_logs = st.checkbox("⚠️ Community Logs (Green/Amber)", value=True)
    show_hotspots = st.checkbox("🚨 Ground-Truth Hot Zones (Red Rings)", value=True)
    show_refuges = st.checkbox("🪹 Predictive Refuge Zones (Amber Rings)", value=True)
    show_larson = st.checkbox("🌲 The Larson Hypothesis (Amorphous Corridors)", value=True)
    show_audio = st.checkbox("🔊 Infrasound / Acoustic Masking (Purple Rings)", value=True)
    show_camps = st.checkbox("🏕️ Camping & Access (Green)", value=True)

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)

# ==========================================
# 5. DATA RETRIEVAL
# ==========================================
sightings_data = []
seasonal_breakdown = {}
if supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = resp.data or []
        for s in sightings_data:
            season = get_season(s.get('event_date', 'N/A'))
            seasonal_breakdown[season] = seasonal_breakdown.get(season, 0) + 1
    except Exception:
        pass

audio_data = []
if show_audio and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("acoustic_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        audio_data = resp.data or []
    except Exception:
        pass

# ==========================================
# 6. TOPOGRAPHIC MAP ENGINE
# ==========================================
m = folium.Map(
    location=[lat, lon], 
    zoom_start=9, 
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap"
)

# Search Radius Boundary & Center Target Beacon Pin
folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_color="#e74c3c", fill_opacity=0.03).add_to(m)
folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER BEACON</b><br>{loc_name}", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"), z_index_offset=3000).add_to(m)

# LAYER: INFRASOUND / ACOUSTIC MASKING (PURPLE WAVE & PROPAGATION BUBBLES)
if show_audio and audio_data:
    for audio in audio_data:
        event_type = audio.get('event_type', 'Acoustic Observation')
        freq = audio.get('frequency_hz', 'Low Hz')
        notes = audio.get('notes', 'Acoustic pressure logged.')
        
        # Calculate Acoustic Masking Bubble Radius (~10-15 miles in meters)
        acoustic_radius = 16000 if "Aeolian" in event_type or "Hydro" in event_type else 9000
        
        audio_popup = f"""
        <div style="font-family: sans-serif; width: 230px;">
            <span style="background-color:#8e44ad; color:white; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:bold;">🔊 INFRASOUND / ACOUSTIC ANCHOR</span><br>
            <b style="color:#8e44ad; font-size:13px; display:inline-block; margin-top:4px;">{event_type}</b><br>
            <small><b>Frequency Spectrum:</b> {freq}</small><br>
            <p style="font-size: 11px; margin-top: 4px;">{notes}</p>
        </div>
        """
        
        # Acoustic Pin
        folium.Marker(
            [audio["latitude"], audio["longitude"]], 
            popup=folium.Popup(audio_popup, max_width=250), 
            icon=folium.Icon(color="purple", icon="volume-up", prefix="fa"), 
            z_index_offset=800
        ).add_to(m)
        
        # Acoustic Propagation Shield (Purple Translucent Ring)
        folium.Circle(
            radius=acoustic_radius,
            location=[audio["latitude"], audio["longitude"]],
            color="#8e44ad",
            weight=1.5,
            dash_array="3, 6",
            fill=True,
            fill_color="#8e44ad",
            fill_opacity=0.12,
            popup="🔊 Atmospheric Infrasound Acoustic Masking Bubble"
        ).add_to(m)

st.caption(f"Loaded **{len(sightings_data)} sightings** and **{len(audio_data)} acoustic masking anchors** in ~{radius_miles} miles.")
map_render_key = f"map_{lat:.4f}_{lon:.4f}_{radius_miles}"
st_folium(m, width="100%", height=520, returned_objects=[], key=map_render_key)

# ==========================================
# 7. INFRASOUND & ACOUSTIC MASKING DRAWER (BELOW BIOACOUSTICS)
# ==========================================
st.markdown("---")
with st.expander("🔊 Regional Infrasound & Acoustic Masking Engine (Frequency & Audio Simulator)", expanded=True):
    st.caption("Cross-reference low-frequency environmental infrasound generators (waterfalls, wind-notches, dams) and simulated biotic rumbles.")
    
    col_inf1, col_inf2 = st.columns([1, 1])
    
    with col_inf1:
        st.markdown("### 📊 Infrasound Physics & Propagation Drivers")
        st.markdown("""
        * **Sub-Audible Spectrum (< 20 Hz):** Infrasound waves travel over vast distances with minimal atmospheric attenuation compared to high frequencies.
        * **Natural Acoustic Masking:** Waterfalls and high-wind mountain notches flood local sectors with continuous low-Hz rumble, providing a natural auditory shield for concealed movement.
        * **Human Perceptual Effects:** High-amplitude infrasound ($5\text{–}15\text{ Hz}$) cannot be heard directly by human ears, but causes inner-ear pressure changes, localized chest vibrations, and feelings of unexplained disorientation or dread.
        """)
        
    with col_inf2:
        st.markdown("### 🎧 Human Hearing Pitch-Shift Simulator")
        st.caption("Infrasound is sub-audible. To hear what a $10\text{ Hz}$ wave looks and sounds like, we shift the frequency up into human hearing ($120\text{--}240\text{ Hz}$).")
        
        # Pitch Shift Interactive Slider
        base_hz = st.slider("Select Infrasound Base Frequency (Hz):", min_value=1.0, max_value=19.0, value=8.5, step=0.5)
        multiplier = st.select_slider("Pitch Shift Multiplier:", options=["4x (Sub-Audible Hum)", "8x (Low Audible Bass)", "16x (Audible Pitch)"], value="8x (Low Audible Bass)")
        
        mult_val = 4 if "4x" in multiplier else (8 if "8x" in multiplier else 16)
        audible_hz = base_hz * mult_val
        
        st.info(f"**Target Infrasound Wave:** `{base_hz} Hz`  ➜  **Pitch-Shifted Human Audible Tone:** `{audible_hz:.1f} Hz`")
        
        # Audio Tone Generator in Python
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        # Generate pitch-shifted audible sine wave
        tone = 0.5 * np.sin(2 * np.pi * audible_hz * t)
        
        # Convert to 16-bit PCM WAV audio bytes
        audio_bytes = (tone * 32767).astype(np.int16).tobytes()
        import io, wave
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_bytes)
            
        st.audio(wav_buffer.getvalue(), format="audio/wav")
        
