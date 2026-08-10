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
if "user_county" not in st.session_state:
    st.session_state.user_county = "Plymouth County"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)
active_state = str(st.session_state.user_state)
active_county = str(st.session_state.user_county)

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

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

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

    for c in camps:
        wpt = ET.SubElement(gpx, "wpt", lat=str(c.get("latitude")), lon=str(c.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Camp: {c.get('name', 'Campsite')}"
        ET.SubElement(wpt, "sym").text = "Campground"

    for a in audio:
        wpt = ET.SubElement(gpx, "wpt", lat=str(a.get("latitude")), lon=str(a.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Audio: {a.get('event_type', 'Infrasound Log')}"
        ET.SubElement(wpt, "desc").text = a.get('notes', '')
        ET.SubElement(wpt, "sym").text = "Sound"

    for log in community_logs:
        wpt = ET.SubElement(gpx, "wpt", lat=str(log.get("latitude")), lon=str(log.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Field Log: {log.get('observation_type', 'Unvetted Log')}"
        ET.SubElement(wpt, "desc").text = f"Facts: {log.get('physical_evidence_notes', '')} | Narrative: {log.get('field_narrative', '')}"
        ET.SubElement(wpt, "sym").text = "Pin"

    return ET.tostring(gpx, encoding="utf-8", method="xml")

# ==========================================
# 3. SIDEBAR CONTROLS & GEOCODING
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN", "")
    if not token: return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
    try:
        resp = requests.get(url, params={"access_token": token, "limit": 1, "types": "place,locality,address,district,region"}, timeout=5)
        if resp.status_code == 200 and resp.json().get("features"):
            feature = resp.json()["features"][0]
            center = feature["center"]
            place_name = feature.get("place_name", query)
            
            state = "Massachusetts"
            county = ""
            for ctx in feature.get("context", []):
                if "region" in ctx.get("id", ""):
                    state = ctx.get("text", state)
                elif "district" in ctx.get("id", ""):
                    county = ctx.get("text", county)

            return center[1], center[0], place_name, state, county
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
            st.session_state.user_lat, st.session_state.user_lon, st.session_state.location_name, st.session_state.user_state, st.session_state.user_county = res
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
    show_bfro = st.checkbox("1. 👣 Sightings (Dual Footprints)", value=True)
    show_lore = st.checkbox("2. 🪶 Native American Lore Net", value=True)
    show_news = st.checkbox("3. 📰 Press Archives Net", value=True)
    show_hotspots = st.checkbox("4. 🚨 Hot Zones & The Larson Hypothesis", value=True)
    show_audio = st.checkbox("5. 🔊 Infrasound / Acoustic Masking", value=True)
    show_user_logs = st.checkbox("6. ⚠️ Community Field Logs", value=True)
    show_camps = st.checkbox("7. 🏕️ Camping & Access Points", value=True)

# ==========================================
# 4. DATA RETRIEVAL
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Curated Research Library"])

sightings_data, camps_data, audio_data, media_data, lore_data, user_logs_data = [], [], [], [], [], []
seasonal_breakdown = {}

if supabase:
    lat_min, lat_max = lat - deg_delta, lat + deg_delta
    lon_min, lon_max = lon - deg_delta, lon + deg_delta

    # BFRO Sightings
    try:
        r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = r.data or []
        for s in sightings_data:
            s["evidence_weight"] = float(s.get("evidence_weight", 1.0))
            season = get_season(s.get('event_date', 'N/A'))
            seasonal_breakdown[season] = seasonal_breakdown.get(season, 0) + 1
    except Exception: pass

    # Campsites
    try:
        r = supabase.table("campsites").select("*").execute()
        raw_camps = r.data or []
        for c in raw_camps:
            if haversine_miles(lat, lon, float(c["latitude"]), float(c["longitude"])) <= radius_miles:
                camps_data.append(c)
    except Exception: pass

    # Infrasound / Audio
    try:
        r = supabase.table("acoustic_reports").select("*").execute()
        raw_audio = r.data or []
        for a in raw_audio:
            a_lat, a_lon = float(a["latitude"]), float(a["longitude"])
            e_type = a.get("event_type", "")
            prop_radius = 80 if "Niagara" in e_type else (60 if "Dam" in e_type or "Snoqualmie" in e_type else 45)
            a["prop_radius_miles"] = prop_radius
            dist_to_target = haversine_miles(lat, lon, a_lat, a_lon)
            a["dist_to_target"] = dist_to_target
            if dist_to_target <= (radius_miles + prop_radius):
                overlap_dist = (radius_miles + prop_radius) - dist_to_target
                coverage_pct = min(100, int((overlap_dist / (radius_miles * 2)) * 100))
                a["coverage_pct"] = max(10, coverage_pct)
                a["is_offscreen"] = dist_to_target > radius_miles
                audio_data.append(a)
    except Exception: pass

    # Historical Media
    try:
        r = supabase.table("historical_media").select("*").ilike("state", f"%{active_state}%").execute()
        media_data = r.data or []
        if not media_data:
            r_all = supabase.table("historical_media").select("*").limit(5).execute()
            media_data = r_all.data or []
        for m_item in media_data:
            m_item["evidence_weight"] = float(m_item.get("evidence_weight", 1.2))
    except Exception: pass

    # Tribal Lore
    try:
        r = supabase.table("tribal_lore").select("*").or_(f"state.ilike.%{active_state}%,region_label.ilike.%{active_state}%").execute()
        lore_data = r.data or []
        for l_item in lore_data:
            l_item["evidence_weight"] = float(l_item.get("evidence_weight", 1.5))
    except Exception: pass

    # Field Logs
    try:
        r = supabase.table("investigator_logs").select("*").execute()
        raw_logs = r.data or []
        for log in raw_logs:
            if haversine_miles(lat, lon, float(log["latitude"]), float(log["longitude"])) <= radius_miles:
                user_logs_data.append(log)
    except Exception: pass

# ==========================================
# TAB 1: SPATIAL MAP
# ==========================================
with tab_map:
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Active Sector ({loc_name} • {active_state}):</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🪶 Regional Lore: <code>{len(lore_data)}</code> | 
        📰 Press Archives: <code>{len(media_data)}</code> | 
        🔊 Infrasound: <code>{len(audio_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    if show_bfro and sightings_data:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_summary = s.get("summary", "No transcript summary provided.")
            raw_id = str(s.get('report_id', '')).strip()
            
            link_html = f'<br><a href="https://www.bfro.net/GDB/show_report.asp?id={raw_id}" target="_blank" style="display:inline-block; margin-top:4px; padding:3px 6px; background:#007bff; color:white; border-radius:3px; text-decoration:none; font-size:10px;">📄 Direct BFRO Report #{raw_id}</a>' if raw_id.isdigit() else ''

            popup_html = f"""
            <div style="font-family:sans-serif; width:250px;">
                <b style="color:#2b78e4;">👣 👣 {s.get('title', 'Sighting Report')}</b><br>
                <small><b>Class:</b> {s.get('class_rating', 'Class A')} | <b>Weight:</b> {s.get('evidence_weight', 1.0)}x</small>
                <hr style="margin:4px 0;">
                <b style="color:#27ae60; font-size:11px;">📊 HARD PHYSICAL FACTS:</b>
                <p style="font-size:10px; margin:2px 0; background:#f8f9fa; padding:4px; border-left:3px solid #27ae60;">{raw_summary[:180]}...</p>
                {link_html}
            </div>
            """
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=270), icon=folium.DivIcon(html="""<div style="font-size:16px;">👣</div>""", icon_size=(20, 20), icon_anchor=(10, 10))).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

    # REGIONAL INTEL PANEL WITH EXPANDED TRANSCRIPTS & LINKS
    st.markdown("---")
    with st.expander("📊 Integrated Regional Intelligence & Field Diagnostics Panel", expanded=True):
        panel_tab1, panel_tab2, panel_tab3, panel_tab4 = st.tabs([
            "🚨 Hot Zones & Larson Hypothesis", 
            "🔊 Infrasound Physics", 
            "🦉 Bioacoustics", 
            "🗂️ Regional Intel"
        ])

        with panel_tab4:
            c_lore, c_media = st.columns(2)
            with c_lore:
                st.markdown(f"#### 🪶 Regional Tribal Lore ({active_state})")
                if lore_data:
                    for item in lore_data:
                        st.markdown(f"**{item.get('tribe_name')} — {item.get('entity_name')}** (`{item.get('evidence_weight', 1.5)}x`)")
                        st.info(item.get('full_narrative'))
                else:
                    st.info(f"No tribal lore entries currently indexed for {active_state}.")

            with c_media:
                st.markdown(f"#### 📰 Historical Press Archives ({active_state})")
                if media_data:
                    for item in media_data:
                        pub_name = item.get('publication_name', 'Historical Newspaper')
                        st.markdown(f"**{item.get('title')} ({item.get('pub_date')})**")
                        st.caption(f"Source: `{pub_name}` | Location: `{item.get('county', 'N/A')}, {item.get('state', 'N/A')}`")
                        st.write(item.get('full_text_transcript'))
                        if item.get("article_url"):
                            st.markdown(f"[🔗 **View Direct Library Archive Source**]({item.get('article_url')})")
                        st.markdown("---")
                else:
                    st.info(f"No historical press accounts currently indexed for {active_state}.")

# ==========================================
# TAB 2: RESEARCH LIBRARY
# ==========================================
with tab_library:
    st.header("📚 Curated Research Library & Deep Science Vault")
    lib_choice = st.radio("Select Vault Section:", ["📰 Historical Press Archives", "🪶 Indigenous Lore", "👣 BFRO Sightings", "🔊 Infrasound Physics"], horizontal=True)

    if "Press Archives" in lib_choice:
        st.subheader("📰 Historical Press Archives & Pre-Internet Media Scans")
        for item in media_data:
            pub_name = item.get('publication_name', 'Historical Gazette')
            st.markdown(f"### {item.get('title')} ({item.get('pub_date')})")
            st.markdown(f"**Publication:** `{pub_name}` | **Location:** {item.get('county')}, {item.get('state')}")
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
