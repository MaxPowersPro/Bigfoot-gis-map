import streamlit as st
import folium
from streamlit_folium import st_folium
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation
import random
import requests
import numpy as np
import io
import wave

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="Bigfoot Field Platform", page_icon="👣", layout="wide")
st.title("👣 Bigfoot Field Analysis & Curation Platform")

if "user_lat" not in st.session_state: st.session_state.user_lat = 41.7000
if "user_lon" not in st.session_state: st.session_state.user_lon = -70.3000
if "location_name" not in st.session_state: st.session_state.location_name = "Massachusetts Target Zone"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)

# ==========================================
# 2. SUPABASE INITIALIZATION
# ==========================================
@st.cache_resource
def init_supabase():
    url = st.secrets.get("SUPABASE_URL", "https://knyusghtnszqbburygor.supabase.co")
    key = st.secrets.get("SUPABASE_KEY", "sb_publishable_ydyOYDYfYTKhGHlZv0AqIg_kzs_SKjM")
    return create_client(url, key)

supabase: Client = init_supabase()

def apply_jitter(lat_val, lon_val, offset_seed=0):
    random.seed(int(lat_val * 1000) + int(lon_val * 1000) + offset_seed)
    return lat_val + random.uniform(-0.003, 0.003), lon_val + random.uniform(-0.003, 0.003)

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN", "")
    if not token: return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
    try:
        resp = requests.get(url, params={"access_token": token, "limit": 1}, timeout=5)
        if resp.status_code == 200 and resp.json().get("features"):
            feature = resp.json()["features"][0]
            return feature["center"][1], feature["center"][0], feature.get("place_name", query)
    except Exception: pass
    return None

with st.sidebar:
    st.header("⚙️ Field Controls")
    loc_search = st.text_input("📍 Target Search Area", value=loc_name)
    radius_miles = st.selectbox("Field Radius (Miles)", [25, 50, 100, 250, 500], index=2)
    deg_delta = radius_miles / 69.0

    col_s1, col_s2 = st.columns(2)
    if col_s1.button("🔎 Search Area", use_container_width=True) and loc_search:
        res = geocode_mapbox(loc_search)
        if res:
            st.session_state.user_lat, st.session_state.user_lon, st.session_state.location_name = res
            st.rerun()

    if col_s2.button("📲 Device GPS", use_container_width=True):
        loc_data = get_geolocation()
        if loc_data and "coords" in loc_data:
            st.session_state.user_lat = loc_data["coords"]["latitude"]
            st.session_state.user_lon = loc_data["coords"]["longitude"]
            st.session_state.location_name = "Device GPS"
            st.rerun()

    st.markdown("---")
    st.subheader("🗺️ Active Map Layers")
    show_bfro = st.checkbox("👣 Sightings", value=True)
    show_camps = st.checkbox("🏕️ Campsites", value=True)
    show_audio = st.checkbox("🔊 Infrasound / Acoustic Anchors", value=True)
    show_news = st.checkbox("📰 Press Archives", value=True)
    show_lore = st.checkbox("🪶 Native American Lore", value=True)

# ==========================================
# 4. TAB NAVIGATION
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Curated Research Library"])

# DATA FETCHING
sightings_data, camps_data, audio_data, media_data, lore_data = [], [], [], [], []

if supabase:
    lat_min, lat_max = lat - deg_delta, lat + deg_delta
    lon_min, lon_max = lon - deg_delta, lon + deg_delta

    try:
        r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("campsites").select("*").execute()
        camps_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("acoustic_reports").select("*").execute()
        audio_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("historical_media").select("*").execute()
        media_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("tribal_lore").select("*").execute()
        lore_data = r.data or []
    except Exception: pass

with tab_map:
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Active Sector Records:</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🏕️ Campsites: <code>{len(camps_data)}</code> | 
        🔊 Infrasound Anchors: <code>{len(audio_data)}</code> | 
        📰 Press Archives: <code>{len(media_data)}</code> | 
        🪶 Tribal Lore: <code>{len(lore_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    # 1. SIGHTINGS WITH FACT VS CONJECTURE FOOTER
    if show_bfro:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_summary = s.get("summary", "No transcript summary provided.")
            
            popup_html = f"""
            <div style="font-family:sans-serif; width:250px;">
                <b style="color:#2b78e4;">👣 {s.get('title', 'Sighting Report')}</b><br>
                <small><b>Class:</b> {s.get('class_rating', 'Class A')} | <b>County:</b> {s.get('county', 'N/A')}, {s.get('state', '')}</small>
                <hr style="margin:4px 0;">
                <b style="color:#27ae60; font-size:11px;">📊 HARD PHYSICAL FACTS:</b>
                <p style="font-size:10px; margin:2px 0; background:#f8f9fa; padding:4px; border-left:3px solid #27ae60;">{raw_summary[:180]}...</p>
                <b style="color:#d35400; font-size:11px;">💭 CONJECTURE / ANALYSIS:</b>
                <p style="font-size:10px; margin:2px 0; background:#fff5f0; padding:4px; border-left:3px solid #d35400;">Observer hypothesis regarding movement direction and vocal behavior.</p>
            </div>
            """
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=270), icon=folium.Icon(color="blue", icon="footprint", prefix="fa")).add_to(m)

    # 2. CAMPSITES (Column: type)
    if show_camps:
        for c in camps_data:
            c_popup = f"<b>🏕️ {c.get('name', 'Campsite')}</b><br><small>Type: {c.get('type', 'Primitive')}</small>"
            folium.Marker([c["latitude"], c["longitude"]], popup=c_popup, icon=folium.Icon(color="green", icon="campground", prefix="fa")).add_to(m)

    # 3. INFRASOUND GENERATORS
    if show_audio:
        for a in audio_data:
            a_popup = f"""<b>🔊 INFRASOUND GENERATOR</b><br><b>{a.get('event_type')}</b><br><small>Frequency: {a.get('frequency_hz')}</small><br><p style='font-size:10px;'>{a.get('notes')}</p>"""
            folium.Marker([a["latitude"], a["longitude"]], popup=a_popup, icon=folium.Icon(color="purple", icon="volume-up", prefix="fa")).add_to(m)
            folium.Circle(radius=15000, location=[a["latitude"], a["longitude"]], color="#8e44ad", weight=1.5, fill=True, fill_opacity=0.10).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

    st.markdown("---")
    with st.expander("🔊 Infrasound & Pitch Simulator", expanded=False):
        base_hz = st.slider("Base Frequency (Hz):", 1.0, 19.0, 8.5, 0.5)
        audible_hz = base_hz * 16
        st.write(f"**Infrasound Frequency:** `{base_hz} Hz` ➜ **Shifted Pitch:** `{audible_hz:.1f} Hz`")
        t = np.linspace(0, 2.0, int(22050 * 2.0), False)
        tone = (0.5 * np.sin(2 * np.pi * audible_hz * t) * 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(22050); wf.writeframes(tone)
        st.audio(buf.getvalue(), format="audio/wav")

# ==========================================
# TAB 2: RESEARCH LIBRARY
# ==========================================
with tab_library:
    st.subheader("📚 Curated Research Library & Source Vault")
    lib_choice = st.radio("Select Vault:", ["👣 Sightings (3,818)", "🏕️ Campsites", "📰 Press Archives", "🪶 Native American Lore", "🔊 Infrasound Generators"], horizontal=True)

    if "Sightings" in lib_choice:
        for item in sightings_data[:30]:
            st.markdown(f"### {item.get('title')} ({item.get('event_date', 'N/A')})")
            c1, c2 = st.columns(2)
            with c1:
                st.success("📊 **VERIFIED HARD PHYSICAL FACTS**")
                st.write(f"**Location:** {item.get('county')}, {item.get('state')} (`{item.get('latitude')}, {item.get('longitude')}`)")
                st.write(item.get("summary"))
            with c2:
                st.warning("💭 **OBSERVER CONJECTURE & EVALUATION**")
                st.write(f"**Class Rating:** {item.get('class_rating')} | **Source:** {item.get('source')}")
            st.markdown("---")

    elif "Campsites" in lib_choice:
        for item in camps_data:
            st.write(f"🏕️ **{item.get('name')}** | Type: `{item.get('type')}` | Coords: `{item.get('latitude')}, {item.get('longitude')}`")

    elif "Press" in lib_choice:
        for item in media_data:
            st.markdown(f"#### 📰 {item.get('title')} ({item.get('pub_date')})")
            st.write(f"> {item.get('full_text_transcript')}")

    elif "Lore" in lib_choice:
        for item in lore_data:
            st.markdown(f"#### 🪶 {item.get('tribe_name')} — {item.get('entity_name')}")
            st.write(f"**Region:** {item.get('region_label')}")
            st.write(item.get("full_narrative"))

    elif "Infrasound" in lib_choice:
        for item in audio_data:
            st.markdown(f"#### 🔊 {item.get('event_type')} ({item.get('frequency_hz')})")
            st.write(item.get("notes"))
