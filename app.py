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
import io
import wave

# ==========================================
# 1. PAGE SETUP & SESSION STATE INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👣 Bigfoot Field Analysis & Curation Platform")

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

def get_season(date_str):
    if not date_str or date_str == 'N/A':
        return 'Unknown'
    try:
        month = int(str(date_str).split('-')[1])
        if month in [12, 1, 2]: return '❄️ Winter'
        elif month in [3, 4, 5]: return '🌸 Spring'
        elif month in [6, 7, 8]: return '☀️ Summer'
        elif month in [9, 10, 11]: return '🍂 Autumn'
    except Exception:
        pass
    return 'Unknown'

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
    except Exception:
        pass
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
    st.subheader("🗺️ Active Layers")
    show_bfro = st.checkbox("👣 Sightings", value=True)
    show_camps = st.checkbox("🏕️ Campsites & Dispersed", value=True)
    show_audio = st.checkbox("🔊 Infrasound / Acoustic Anchors", value=True)
    show_news = st.checkbox("📰 Historical Press Net", value=True)
    show_lore = st.checkbox("🪶 Native American Lore", value=True)
    show_user_logs = st.checkbox("⚠️ Community Logs", value=True)

# ==========================================
# 4. TAB NAVIGATION SETUP
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Curated Research Library"])

# ==========================================
# TAB 1: SPATIAL MAP ENGINE
# ==========================================
with tab_map:
    # DATA RETRIEVAL (WITH WIDE FALLBACK FOR INFRASTRUCTURE/AUDIO)
    sightings_data, camps_data, audio_data, media_data, lore_data, user_logs_data = [], [], [], [], [], []
    
    if supabase:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        
        # Sightings
        try:
            r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
            sightings_data = r.data or []
        except Exception: pass
        
        # Campsites (Fallback to wide box if local count is low)
        try:
            r = supabase.table("campsites").select("*").gte("latitude", lat - 2.0).lte("latitude", lat + 2.0).gte("longitude", lon - 2.0).lte("longitude", lon + 2.0).execute()
            camps_data = r.data or []
        except Exception: pass
        
        # Acoustic / Infrasound (Wide regional coverage)
        try:
            r = supabase.table("acoustic_reports").select("*").execute()
            audio_data = r.data or []
        except Exception: pass

        # Historical Media
        try:
            r = supabase.table("historical_media").select("*").gte("latitude", lat - 3.0).lte("latitude", lat + 3.0).gte("longitude", lon - 3.0).lte("longitude", lon + 3.0).execute()
            media_data = r.data or []
        except Exception: pass

        # Tribal Lore
        try:
            r = supabase.table("tribal_lore").select("*").execute()
            lore_data = r.data or []
        except Exception: pass

        # Community Field Logs
        try:
            r = supabase.table("investigator_logs").select("*").execute()
            user_logs_data = r.data or []
        except Exception: pass

    # VISUAL MAP BADGES OVERLAY
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Active Sector Indicators:</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🏕️ Campsites: <code>{len(camps_data)}</code> | 
        🔊 Infrasound Anchors: <code>{len(audio_data)}</code> | 
        📰 Press Archives: <code>{len(media_data)}</code> | 
        🪶 Tribal Lore Records: <code>{len(lore_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    # 1. SIGHTINGS WITH FACT VS CONJECTURE BREAKDOWN
    if show_bfro:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_summary = s.get("summary", "No transcript summary provided.")
            
            # Fact vs Conjecture heuristic parsing
            fact_split = raw_summary.split("Observer Hypothesis:") if "Observer Hypothesis:" in raw_summary else [raw_summary, "Observer subjective interpretation logged in narrative."]
            hard_facts = fact_split[0]
            conjecture = fact_split[1] if len(fact_split) > 1 else "Conjecture merged in report narrative."

            popup_html = f"""
            <div style="font-family:sans-serif; width:240px;">
                <b style="color:#2b78e4;">👣 {s.get('title', 'Sighting Report')}</b><br>
                <small><b>Class:</b> {s.get('class_rating', 'Class A')} | <b>Date:</b> {s.get('event_date', 'N/A')}</small>
                <hr style="margin:4px 0;">
                <b style="color:#27ae60; font-size:11px;">📊 HARD FACTS (Physical/Environmental):</b>
                <p style="font-size:10px; margin:2px 0; background:#f8f9fa; padding:3px;">{hard_facts[:200]}...</p>
                <b style="color:#d35400; font-size:11px;">💭 CONJECTURE / ANALYSIS:</b>
                <p style="font-size:10px; margin:2px 0; background:#fff5f0; padding:3px;">{conjecture[:150]}</p>
            </div>
            """
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=260), icon=folium.Icon(color="blue", icon="footprint", prefix="fa")).add_to(m)

    # 2. CAMPSITES
    if show_camps:
        for c in camps_data:
            c_popup = f"<b>🏕️ {c.get('name', 'Campsite')}</b><br><small>Type: {c.get('facility_type', 'Primitive')}</small>"
            folium.Marker([c["latitude"], c["longitude"]], popup=c_popup, icon=folium.Icon(color="green", icon="campground", prefix="fa")).add_to(m)

    # 3. INFRASOUND / ACOUSTIC ANCHORS
    if show_audio:
        for a in audio_data:
            a_popup = f"""<b>🔊 INFRASOUND GENERATOR</b><br><b>{a.get('event_type')}</b><br><small>Frequency: {a.get('frequency_hz')}</small><br><p style='font-size:10px;'>{a.get('notes')}</p>"""
            folium.Marker([a["latitude"], a["longitude"]], popup=a_popup, icon=folium.Icon(color="purple", icon="volume-up", prefix="fa")).add_to(m)
            folium.Circle(radius=15000, location=[a["latitude"], a["longitude"]], color="#8e44ad", weight=1, fill=True, fill_opacity=0.1).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

    # DRAWERS BELOW MAP
    st.markdown("---")
    with st.expander("🔊 Infrasound & Pitch Simulator", expanded=False):
        base_hz = st.slider("Base Hz:", 1.0, 19.0, 8.0)
        audible_hz = base_hz * 16
        st.write(f"Infrasound Frequency: `{base_hz} Hz` ➜ Shifted Pitch: `{audible_hz:.1f} Hz`")
        t = np.linspace(0, 2.0, int(22050 * 2.0), False)
        tone = (0.5 * np.sin(2 * np.pi * audible_hz * t) * 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(22050); wf.writeframes(tone)
        st.audio(buf.getvalue(), format="audio/wav")

# ==========================================
# TAB 2: CURATED RESEARCH LIBRARY (FACTS VS CONJECTURE)
# ==========================================
with tab_library:
    st.subheader("📚 Curated Research Library & Database Vault")
    st.caption("Inspect, cross-reference, and evaluate ground-truth facts versus observer conjecture across all ingested sources.")

    lib_type = st.radio("Select Database Vault:", ["👣 Sighting Reports", "🏕️ Campsite & Access Points", "📰 Historical Press Archives", "🪶 Native American Lore", "🔊 Infrasound Generators"], horizontal=True)

    if supabase:
        if "Sightings" in lib_type:
            res = supabase.table("sighting_reports").select("*").limit(50).execute()
            for item in (res.data or []):
                with st.container():
                    st.markdown(f"### {item.get('title', 'Sighting Record')} ({item.get('event_date', 'N/A')})")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.success("📊 **VERIFIED HARD FACTS**")
                        st.write(item.get("summary", "No transcript logged.")[:400])
                    with c2:
                        st.warning("💭 **OBSERVER CONJECTURE & HYPOTHESIS**")
                        st.write(f"Class Rating: {item.get('class_rating')} | Location: `{item.get('latitude')}, {item.get('longitude')}`")
                    st.markdown("---")

        elif "Campsites" in lib_type:
            res = supabase.table("campsites").select("*").limit(50).execute()
            for item in (res.data or []):
                st.write(f"🏕️ **{item.get('name')}** | Type: `{item.get('facility_type')}` | Coords: `{item.get('latitude')}, {item.get('longitude')}`")

        elif "Press" in lib_type:
            res = supabase.table("historical_media").select("*").limit(50).execute()
            for item in (res.data or []):
                st.markdown(f"#### 📰 {item.get('title')} ({item.get('pub_date')})")
                st.write(f"> {item.get('full_text_transcript')}")
                st.markdown("---")

        elif "Lore" in lib_type:
            res = supabase.table("tribal_lore").select("*").execute()
            for item in (res.data or []):
                st.markdown(f"#### 🪶 {item.get('tribe_name')} — {item.get('entity_name')}")
                st.write(item.get("full_narrative"))
                st.markdown("---")

        elif "Infrasound" in lib_type:
            res = supabase.table("acoustic_reports").select("*").execute()
            for item in (res.data or []):
                st.markdown(f"#### 🔊 {item.get('event_type')} ({item.get('frequency_hz')})")
                st.write(item.get("notes"))
                st.markdown("---")
