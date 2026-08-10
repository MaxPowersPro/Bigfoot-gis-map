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
# 1. PAGE SETUP & AUTO-LOCATION INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Auto-detect visitor's location on startup
if "user_lat" not in st.session_state or "user_lon" not in st.session_state:
    device_loc = get_geolocation()
    if device_loc and "coords" in device_loc:
        st.session_state.user_lat = device_loc["coords"]["latitude"]
        st.session_state.user_lon = device_loc["coords"]["longitude"]
        st.session_state.location_name = "Detected Local Sector"
    else:
        st.session_state.user_lat = 41.7000
        st.session_state.user_lon = -70.3000
        st.session_state.location_name = "Default Target Zone"

if "user_state" not in st.session_state:
    st.session_state.user_state = "Massachusetts"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)
active_state = str(st.session_state.user_state)

# ==========================================
# CUSTOM BRANDING HEADER BANNER
# ==========================================
try:
    st.image("image.png", use_container_width=True)
except Exception:
    try:
        st.image("header_banner.png", use_container_width=True)
    except Exception:
        st.title("Maxquest")

st.caption("Site-Specific Spatial Map & Predictive Multi-Criteria Analysis Engine")
st.markdown("---")

# ==========================================
# 2. SUPABASE CONNECTION & UTILITIES
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "https://knyusghtnszqbburygor.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "sb_publishable_ydyOYDYfYTKhGHlZv0AqIg_kzs_SKjM")
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Supabase Init Failed: {e}")
        return None

supabase: Client = init_supabase()

def apply_jitter(lat_val, lon_val, offset_seed=0):
    random.seed(int(lat_val * 1000) + int(lon_val * 1000) + offset_seed)
    return lat_val + random.uniform(-0.003, 0.003), lon_val + random.uniform(-0.003, 0.003)

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# ==========================================
# 3. SIDEBAR CONTROLS & GEOCODING
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN", "")
    if not token: return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
    try:
        resp = requests.get(url, params={"access_token": token, "limit": 1}, timeout=5)
        if resp.status_code == 200 and resp.json().get("features"):
            feature = resp.json()["features"][0]
            center = feature["center"]
            place_name = feature.get("place_name", query)
            state = "Massachusetts"
            for ctx in feature.get("context", []):
                if "region" in ctx.get("id", ""):
                    state = ctx.get("text", state)
            return center[1], center[0], place_name, state
    except Exception: pass
    return None

with st.sidebar:
    st.header("⚙️ Field Controls")
    loc_search = st.text_input("📍 Target Search Area", value=loc_name)
    radius_miles = st.selectbox("Field Radius (Miles)", [25, 50, 100, 250, 500], index=2)
    deg_delta = radius_miles / 69.0

    if st.button("🔎 Search Area", use_container_width=True) and loc_search:
        res = geocode_mapbox(loc_search)
        if res:
            st.session_state.user_lat, st.session_state.user_lon, st.session_state.location_name, st.session_state.user_state = res
            st.rerun()

    st.markdown("---")
    show_bfro = st.checkbox("1. 👣 Sightings", value=True)
    show_lore = st.checkbox("2. 🪶 Tribal Lore", value=True)
    show_news = st.checkbox("3. 📰 Press Archives", value=True)

# ==========================================
# 4. DATA RETRIEVAL WITH RESILIENT FALLBACKS
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Curated Research Library"])

sightings_data, media_data, lore_data = [], [], []

if supabase:
    lat_min, lat_max = lat - deg_delta, lat + deg_delta
    lon_min, lon_max = lon - deg_delta, lon + deg_delta

    # BFRO Sightings
    try:
        r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = r.data or []
    except Exception: pass

    # Historical Media (State Match with Global Fallback)
    try:
        r = supabase.table("historical_media").select("*").ilike("state", f"%{active_state}%").execute()
        media_data = r.data or []
        if not media_data:
            r_all = supabase.table("historical_media").select("*").execute()
            media_data = r_all.data or []
    except Exception: pass

    # Tribal Lore (State Match with Global Fallback)
    try:
        r = supabase.table("tribal_lore").select("*").ilike("state", f"%{active_state}%").execute()
        lore_data = r.data or []
        if not lore_data:
            r_all = supabase.table("tribal_lore").select("*").execute()
            lore_data = r_all.data or []
    except Exception: pass

# ==========================================
# TAB 1: SPATIAL MAP ENGINE
# ==========================================
with tab_map:
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Active Sector ({loc_name}):</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🪶 Lore Entries: <code>{len(lore_data)}</code> | 
        📰 Historical News Scans: <code>{len(media_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    if show_bfro and sightings_data:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_id = str(s.get('report_id', '')).strip()
            link_html = f'<br><a href="https://www.bfro.net/GDB/show_report.asp?id={raw_id}" target="_blank">📄 View BFRO Report #{raw_id}</a>' if raw_id.isdigit() else ''
            popup_html = f"<b>👣 {s.get('title', 'Sighting')}</b><br><small>{s.get('summary', '')[:150]}...</small>{link_html}"
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=250), icon=folium.Icon(color="blue", icon="paw", prefix="fa")).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

    # REGIONAL INTEL PANEL
    st.markdown("---")
    with st.expander("📊 Integrated Regional Intelligence Panel", expanded=True):
        c_lore, c_media = st.columns(2)
        with c_lore:
            st.markdown(f"#### 🪶 Regional Tribal Lore")
            for item in lore_data:
                st.markdown(f"**{item.get('tribe_name')} — {item.get('entity_name')}**")
                st.info(item.get('full_narrative'))

        with c_media:
            st.markdown(f"#### 📰 Historical Press Archives")
            for item in media_data:
                st.markdown(f"**{item.get('title')} ({item.get('pub_date')})**")
                st.caption(f"Publication: `{item.get('publication_name')}` | Location: `{item.get('county')}, {item.get('state')}`")
                st.write(item.get('full_text_transcript'))
                if item.get("article_url"):
                    st.markdown(f"[🔗 **View Direct Library Archive Source**]({item.get('article_url')})")
                st.markdown("---")

# ==========================================
# TAB 2: RESEARCH LIBRARY
# ==========================================
with tab_library:
    st.header("📚 Curated Research Library & Source Vault")
    lib_choice = st.radio("Select Vault Section:", ["📰 Historical Press Archives", "🪶 Indigenous Lore", "👣 BFRO Sightings"], horizontal=True)

    if "Press Archives" in lib_choice:
        st.subheader("📰 Historical Press Archives & Pre-Internet Media Scans")
        for item in media_data:
            st.markdown(f"### {item.get('title')} ({item.get('pub_date')})")
            st.markdown(f"**Publication:** `{item.get('publication_name')}` | **Location:** {item.get('county')}, {item.get('state')}")
            st.info(item.get('full_text_transcript'))
            if item.get("article_url"):
                st.markdown(f"[🔗 **Open Direct Historical Archive Link**]({item.get('article_url')})")
            st.markdown("---")

    elif "Lore" in lib_choice:
        st.subheader("🪶 Indigenous Ethnographic Lore & Land Anchors")
        for item in lore_data:
            st.markdown(f"### {item.get('tribe_name')} — *{item.get('entity_name')}*")
            st.markdown(f"**Region:** `{item.get('state')}` | **Evidence Weight:** `{item.get('evidence_weight', 1.5)}x`")
            st.write(item.get("full_narrative"))
            st.markdown("---")

    elif "Sightings" in lib_choice:
        st.subheader("👣 BFRO Field Reports")
        for item in sightings_data[:20]:
            raw_id = str(item.get('report_id', '')).strip()
            st.markdown(f"#### 👣 {item.get('title')}")
            st.write(item.get('summary'))
            if raw_id.isdigit():
                st.markdown(f"[📄 View BFRO Report #{raw_id}](https://www.bfro.net/GDB/show_report.asp?id={raw_id})")
            st.markdown("---")
