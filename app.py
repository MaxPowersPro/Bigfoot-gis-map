import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation
import random

# ==========================================
# 1. PAGE SETUP & WORKING TITLE
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👣 Bigfoot Field Analysis Platform")
st.caption("Site-Specific Spatial Map & Self-Contained Field Analysis Engine")

# ==========================================
# 2. SUPABASE CLOUD CONNECTION
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase: Client = init_supabase()

# Initialize Location State
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 41.7000
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -70.3000
if "location_name" not in st.session_state:
    st.session_state.location_name = "Massachusetts Target Zone"

geolocator = Nominatim(user_agent="bigfoot_field_platform_v13")

# Helper Function: Micro-Offsetting Jitter
def apply_jitter(lat_val, lon_val, offset_seed=0):
    random.seed(int(lat_val * 1000) + int(lon_val * 1000) + offset_seed)
    lat_jitter = lat_val + random.uniform(-0.003, 0.003)
    lon_jitter = lon_val + random.uniform(-0.003, 0.003)
    return lat_jitter, lon_jitter

# Helper Function: Parse Season
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

# ==========================================
# 3. HISTORIC TRIBAL TERRITORY POLYGONS
# ==========================================
TRIBAL_BOUNDARIES = {
    "Eastern Band of Cherokee": Polygon([
        (-85.5, 33.5), (-85.5, 37.0), (-80.5, 37.0), (-80.5, 33.5), (-85.5, 33.5)
    ]),
    "Coast Salish / Halkomelem": Polygon([
        (-125.0, 46.5), (-125.0, 50.0), (-121.0, 50.0), (-121.0, 46.5), (-125.0, 46.5)
    ]),
    "Choctaw Nation": Polygon([
        (-90.5, 30.5), (-90.5, 35.0), (-87.0, 35.0), (-87.0, 30.5), (-90.5, 30.5)
    ]),
    "Klamath / Modoc / Yurok": Polygon([
        (-124.5, 40.0), (-124.5, 44.0), (-120.0, 44.0), (-120.0, 40.0), (-124.5, 40.0)
    ]),
    "Ojibwe / Anishinaabe": Polygon([
        (-95.0, 44.0), (-95.0, 50.0), (-80.0, 50.0), (-80.0, 44.0), (-95.0, 44.0)
    ]),
    "Cree Nation": Polygon([
        (-120.0, 51.0), (-120.0, 60.0), (-70.0, 60.0), (-70.0, 51.0), (-120.0, 51.0)
    ]),
    "Haudenosaunee / Iroquois": Polygon([
        (-79.0, 41.0), (-79.0, 46.0), (-71.0, 46.0), (-71.0, 41.0), (-79.0, 41.0)
    ]),
    "Tlingit / Athabascan": Polygon([
        (-155.0, 58.0), (-155.0, 68.0), (-130.0, 68.0), (-130.0, 58.0), (-155.0, 58.0)
    ])
}

# ==========================================
# 4. SIDEBAR CONTROLS & GEOLOCATION
# ==========================================
with st.sidebar:
    st.header("⚙️ Field Controls")
    
    loc_search = st.text_input("📍 Target Search Area", value=st.session_state.location_name)
    radius_miles = st.selectbox("Field Radius (Miles)", [25, 50, 100, 250], index=1)
    deg_delta = radius_miles / 69.0
    
    # 100-Mile Delta for Regional Press Net
    regional_deg_delta = 100.0 / 69.0

    if st.button("🔎 Search Area", use_container_width=True):
        if loc_search:
            try:
                location = geolocator.geocode(loc_search)
                if location:
                    st.session_state.user_lat = location.latitude
                    st.session_state.user_lon = location.longitude
                    st.session_state.location_name = location.address
            except Exception:
                st.error("Geocoding service busy. Please try again.")

    if st.button("📲 Use Device GPS", use_container_width=True):
        loc = get_geolocation()
        if loc and "coords" in loc:
            st.session_state.user_lat = loc["coords"]["latitude"]
            st.session_state.user_lon = loc["coords"]["longitude"]
            st.session_state.location_name = f"Current GPS ({st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f})"
            st.rerun()

    st.markdown("---")
    st.subheader("🗺️ Active Map Layers")
    show_bfro = st.checkbox("👣 Sightings (Blue)", value=True)
    show_camps = st.checkbox("🏕️ Campsites (Green)", value=True)
    show_audio = st.checkbox("🔊 Infrasound (Purple)", value=True)
    show_lore = st.checkbox("🪶 Regional Lore Net", value=True)
    show_news = st.checkbox("📰 Regional Press Net", value=True)

lat = st.session_state.user_lat
lon = st.session_state.user_lon
loc_name = st.session_state.location_name

# ==========================================
# 5. DATA RETRIEVAL (REGIONAL & FIELD)
# ==========================================
# 1. Sightings
sightings_data = []
seasonal_breakdown = {}
if show_bfro and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = resp.data
    except Exception:
        pass

# 2. Campsites
camps_data = []
if show_camps and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("campsites").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        camps_data = resp.data
    except Exception:
        pass

# 3. Infrasound / Acoustic
audio_data = []
if show_audio and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("acoustic_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        audio_data = resp.data
    except Exception:
        pass

# 4. Regional Media (100-Mile Net)
local_media_records = []
if show_news and supabase:
    try:
        r_lat_min, r_lat_max = lat - regional_deg_delta, lat + regional_deg_delta
        r_lon_min, r_lon_max = lon - regional_deg_delta, lon + regional_deg_delta
        resp = supabase.table("historical_media").select("*").gte("latitude", r_lat_min).lte("latitude", r_lat_max).gte("longitude", r_lon_min).lte("longitude", r_lon_max).execute()
        local_media_records = resp.data
    except Exception:
        pass

# 5. Regional Lore
detected_lore = []
search_point = Point(lon, lat)
if supabase and show_lore:
    for tribe_name, polygon in TRIBAL_BOUNDARIES.items():
        if polygon.contains(search_point):
            lore_resp = supabase.table("tribal_lore").select("*").eq("tribe_name", tribe_name).execute()
            if lore_resp.data:
                detected_lore.extend(lore_resp.data)

# ==========================================
# 6. TOPOGRAPHIC MAP ENGINE
# ==========================================
m = folium.Map(
    location=[lat, lon], 
    zoom_start=9, 
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap"
)

# 50-Mile Field Search Boundary
folium.Circle(
    radius=radius_miles * 1609.34,
    location=[lat, lon],
    color="#e74c3c",
    weight=2,
    fill=True,
    fill_color="#e74c3c",
    fill_opacity=0.05,
    popup=f"Field Radius ({radius_miles} Miles)"
).add_to(m)

# 100-Mile Regional Intelligence Boundary (Dashed Ring)
folium.Circle(
    radius=100 * 1609.34,
    location=[lat, lon],
    color="#34495e",
    weight=1.5,
    dash_array="5, 8",
    fill=False,
    popup="100-Mile Regional Intelligence Boundary"
).add_to(m)

# Target Center Beacon
folium.CircleMarker(
    location=[lat, lon],
    radius=16,
    color="#ff0000",
    weight=3,
    fill=True,
    fill_color="#ff4d4d",
    fill_opacity=0.5,
    popup=f"<b>TARGET CENTER HALO</b><br>{loc_name}"
).add_to(m)

folium.Marker(
    [lat, lon],
    popup=f"<b>📍 TARGET CENTER BEACON</b><br>{loc_name}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa"),
    z_index_offset=3000
).add_to(m)

# ------------------------------------------
# MAP LAYER 1: SIGHTINGS (SOLID BLUE DOTS)
# ------------------------------------------
for report in sightings_data:
    raw_id = str(report.get('report_id', '')).strip()
    source = report.get('source', 'BFRO')
    event_date = report.get('event_date', 'N/A')

    season = get_season(event_date)
    seasonal_breakdown[season] = seasonal_breakdown.get(season, 0) + 1

    if source == 'BFRO' and raw_id.isdigit() and len(raw_id) >= 3:
        full_report_url = f"https://www.bfro.net/GDB/show_report.asp?id={raw_id}"
        link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:6px; padding:4px 8px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Direct BFRO Report #{raw_id}</a>'
    else:
        link_html = ''

    popup_content = f"""
    <div style="font-family: sans-serif; width: 220px;">
        <b style="color:#2c3e50;">👣 {report.get('title', 'Sighting Report')}</b><br>
        <small><b>Date:</b> {event_date} | <b>Class:</b> {report.get('class_rating', 'A/B')}</small><br>
        <p style="font-size: 11px; margin-top: 4px; margin-bottom: 4px;">{report.get('summary', 'No summary details.')}</p>
        {link_html}
    </div>
    """

    j_lat, j_lon = apply_jitter(report["latitude"], report["longitude"], offset_seed=1)

    blue_pin_html = """
    <div style="
        background-color: #2b78e4; 
        width: 14px; 
        height: 14px; 
        border-radius: 50%; 
        border: 2px solid white; 
        box-shadow: 0 0 4px rgba(0,0,0,0.5);">
    </div>
    """

    folium.Marker(
        [j_lat, j_lon],
        popup=folium.Popup(popup_content, max_width=250),
        icon=folium.DivIcon(html=blue_pin_html, icon_size=(14, 14), icon_anchor=(7, 7)),
        z_index_offset=500
    ).add_to(m)

# ------------------------------------------
# MAP LAYER 2: CAMPSITES (GREEN TENT PINS)
# ------------------------------------------
for camp in camps_data:
    camp_popup = f"""
    <div style="font-family: sans-serif; width: 210px;">
        <b style="color:#27ae60;">🏕️ {camp.get('name', 'Campground')}</b><br>
        <small><b>Type:</b> {camp.get('facility_type', 'Public Campsite')}</small><br>
        <p style="font-size: 11px; margin-top: 4px;">{camp.get('description', 'Public camping access point.')}</p>
    </div>
    """
    folium.Marker(
        [camp["latitude"], camp["longitude"]],
        popup=folium.Popup(camp_popup, max_width=230),
        icon=folium.Icon(color="green", icon="campground", prefix="fa"),
        z_index_offset=400
    ).add_to(m)

# ------------------------------------------
# MAP LAYER 3: INFRASOUND / ACOUSTIC (PURPLE MICROPHONE PINS)
# ------------------------------------------
for audio in audio_data:
    audio_popup = f"""
    <div style="font-family: sans-serif; width: 220px;">
        <b style="color:#8e44ad;">🔊 {audio.get('event_type', 'Acoustic Observation')}</b><br>
        <small><b>Frequency:</b> {audio.get('frequency_hz', 'Low Hz')} | <b>Date:</b> {audio.get('event_date', 'N/A')}</small><br>
        <p style="font-size: 11px; margin-top: 4px;">{audio.get('notes', 'Acoustic/Infrasound anomaly logged.')}</p>
    </div>
    """
    folium.Marker(
        [audio["latitude"], audio["longitude"]],
        popup=folium.Popup(audio_popup, max_width=240),
        icon=folium.Icon(color="purple", icon="microphone", prefix="fa"),
        z_index_offset=600
    ).add_to(m)

# ------------------------------------------
# ON-MAP REGIONAL ALERT BADGE
# ------------------------------------------
total_regional_records = len(local_media_records) + len(detected_lore)
if total_regional_records > 0:
    badge_html = f"""
    <div style="
        position: fixed; 
        bottom: 20px; 
        left: 20px; 
        z-index: 9999; 
        background-color: #2c3e50; 
        color: white; 
        padding: 10px 14px; 
        border-radius: 8px; 
        box-shadow: 0 2px 8px rgba(0,0,0,0.4); 
        font-family: sans-serif; 
        font-size: 13px; 
        font-weight: bold; 
        border: 1px solid #34495e;">
        📰 🪶 {total_regional_records} Regional Accounts Active (100-Mi. Net) — <a href="#regional-panel" style="color:#f39c12; text-decoration:underline;">Scroll Down to Read</a>
    </div>
    """
    m.get_root().html.add_child(folium.Element(badge_html))

# Render Topographic Map
st.caption(f"Loaded **{len(sightings_data)} sightings**, **{len(camps_data)} campsites**, and **{len(audio_data)} acoustic logs** in ~{radius_miles} miles.")
st_folium(m, width="100%", height=520, returned_objects=[])

# ==========================================
# 7. REGIONAL FIELD CONTEXT BELOW MAP
# ==========================================
st.markdown("<div id='regional-panel'></div>", unsafe_allow_html=True)
st.markdown("---")
st.markdown("### 🗂️ Regional Field Context & Intelligence Panel (100-Mile Radius)")

col_lore_btn, col_media_btn, col_season_btn = st.columns(3)

with col_lore_btn:
    if detected_lore:
        with st.expander(f"🪶 Regional Oral Histories ({len(detected_lore)})", expanded=True):
            for lore_item in detected_lore:
                st.markdown(f"#### {lore_item['tribe_name']} — {lore_item['entity_name']}")
                st.write(f"> {lore_item['full_narrative']}")
                st.markdown("---")
    else:
        st.info("No recorded regional indigenous narratives within active target boundary.")

with col_media_btn:
    if local_media_records:
        with st.expander(f"📰 Local Press & Archives ({len(local_media_records)})", expanded=True):
            for media_item in local_media_records:
                st.markdown(f"#### 📰 {media_item['title']}")
                st.caption(f"**Publication:** {media_item['publication_name']} | **Date:** {media_item['pub_date']} | **Location:** {media_item['county']}, {media_item['state_province']}")
                st.write(f"**Transcript:** {media_item['full_text_transcript']}")
                if media_item.get('image_url'):
                    st.markdown(f"[🔗 View Original Article Record / Source Image]({media_item['image_url']})")
                st.markdown("---")
    else:
        st.info("No historical press accounts tagged within 100 miles.")

with col_season_btn:
    with st.expander("🍂 Seasonal Activity Breakdown", expanded=True):
        if seasonal_breakdown:
            for season_name, count in seasonal_breakdown.items():
                st.markdown(f"**{season_name}:** {count} reports")
        else:
            st.info("No dated sighting activity in this active search area.")
