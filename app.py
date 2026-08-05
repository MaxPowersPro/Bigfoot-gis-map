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

# ==========================================
# 1. PAGE SETUP & WORKING TITLE
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="auto"
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

# Helper Function: Generate GPX XML Package
def generate_gpx(target_lat, target_lon, loc_title, sightings, camps, audio, community_logs):
    gpx = ET.Element("gpx", version="1.1", creator="BigfootFieldPlatform", xmlns="http://www.topografix.com/GPX/1/1")
    
    # Target Center
    wpt_target = ET.SubElement(gpx, "wpt", lat=str(target_lat), lon=str(target_lon))
    ET.SubElement(wpt_target, "name").text = f"TARGET: {loc_title}"
    ET.SubElement(wpt_target, "sym").text = "Cross-Hair"
    
    # Sightings
    for s in sightings:
        wpt = ET.SubElement(gpx, "wpt", lat=str(s.get("latitude")), lon=str(s.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Sighting: {s.get('title', 'BFRO Report')}"
        ET.SubElement(wpt, "desc").text = f"Date: {s.get('event_date', 'N/A')} | Summary: {s.get('summary', '')}"
        ET.SubElement(wpt, "sym").text = "Footprint"

    # Campsites
    for c in camps:
        wpt = ET.SubElement(gpx, "wpt", lat=str(c.get("latitude")), lon=str(c.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Camp: {c.get('name', 'Campsite')}"
        ET.SubElement(wpt, "desc").text = c.get('description', '')
        ET.SubElement(wpt, "sym").text = "Campground"

    # Audio
    for a in audio:
        wpt = ET.SubElement(gpx, "wpt", lat=str(a.get("latitude")), lon=str(a.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Audio: {a.get('event_type', 'Infrasound Log')}"
        ET.SubElement(wpt, "desc").text = a.get('notes', '')
        ET.SubElement(wpt, "sym").text = "Sound"

    # Community Field Logs
    for log in community_logs:
        wpt = ET.SubElement(gpx, "wpt", lat=str(log.get("latitude")), lon=str(log.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Field Log: {log.get('observation_type', 'Unvetted Log')}"
        ET.SubElement(wpt, "desc").text = f"Facts: {log.get('physical_evidence_notes', '')} | Narrative: {log.get('field_narrative', '')}"
        ET.SubElement(wpt, "sym").text = "Pin"

    return ET.tostring(gpx, encoding="utf-8", method="xml")

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
# 4. SIDEBAR CONTROLS & MAPBOX GEOLOCATION
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN")
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
    
    loc_search = st.text_input("📍 Target Search Area", value=st.session_state.location_name)
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
        else:
            st.error("Location not found. Please check spelling or enter a ZIP code.")

    if gps_btn:
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
    show_user_logs = st.checkbox("⚠️ Community Logs (Amber)", value=True)
    show_lore = st.checkbox("🪶 Regional Lore Net", value=True)
    show_news = st.checkbox("📰 Regional Press Net", value=True)

lat = st.session_state.user_lat
lon = st.session_state.user_lon
loc_name = st.session_state.location_name

# ==========================================
# 5. DATA RETRIEVAL & DEDUPLICATION
# ==========================================
sightings_data = []
seasonal_breakdown = {}
if show_bfro and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = resp.data or []
    except Exception:
        pass

camps_data = []
if show_camps and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("campsites").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        camps_data = resp.data or []
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

community_logs_data = []
if show_user_logs and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta
        resp = supabase.table("investigator_logs").select("*").eq("is_public", True).gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        community_logs_data = resp.data or []
    except Exception:
        pass

local_media_records = []
if show_news and supabase:
    try:
        r_lat_min, r_lat_max = lat - regional_deg_delta, lat + regional_deg_delta
        r_lon_min, r_lon_max = lon - regional_deg_delta, lon + regional_deg_delta
        resp = supabase.table("historical_media").select("*").gte("latitude", r_lat_min).lte("latitude", r_lat_max).gte("longitude", r_lon_min).lte("longitude", r_lon_max).execute()
        local_media_records = resp.data or []
    except Exception:
        pass

detected_lore = []
seen_lore_ids = set()
search_point = Point(lon, lat)

if supabase and show_lore:
    for tribe_name, polygon in TRIBAL_BOUNDARIES.items():
        if polygon.contains(search_point):
            lore_resp = supabase.table("tribal_lore").select("*").eq("tribe_name", tribe_name).execute()
            if lore_resp.data:
                for lore_item in lore_resp.data:
                    lore_id = lore_item.get("id") or lore_item.get("entity_name")
                    if lore_id not in seen_lore_ids:
                        seen_lore_ids.add(lore_id)
                        detected_lore.append(lore_item)
# ==========================================
# DIAGNOSTIC DEBUG PANEL (TEMPORARY TROUBLESHOOTING)
# ==========================================
with st.expander("🔍 System Diagnostics & Query Inspector", expanded=True):
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        st.write(f"**Target Location:** {loc_name}")
        st.write(f"**Center Lat/Lon:** `{lat:.5f}, {lon:.5f}`")
        st.write(f"**Search Radius:** {radius_miles} miles (`deg_delta: {deg_delta:.4f}`)")
    with col_d2:
        st.write(f"**Latitude Range:** `{lat - deg_delta:.5f}` to `{lat + deg_delta:.5f}`")
        st.write(f"**Longitude Range:** `{lon - deg_delta:.5f}` to `{lon + deg_delta:.5f}`")
        st.write(f"**Supabase Client Active:** `{supabase is not None}`")
    with col_d3:
        st.write(f"**Sightings Fetched:** `{len(sightings_data)}`")
        st.write(f"**Campsites Fetched:** `{len(camps_data)}`")
        st.write(f"**Audio Logs Fetched:** `{len(audio_data)}`")
        st.write(f"**Community Logs Fetched:** `{len(community_logs_data)}`")

    # Raw Query Test Button
    if st.button("🧪 Test Unfiltered Supabase Fetch (First 5 Rows)"):
        if supabase:
            try:
                test_resp = supabase.table("sighting_reports").select("title, latitude, longitude, event_date").limit(5).execute()
                st.write("**Sample Supabase Sighting Records:**", test_resp.data)
            except Exception as err:
                st.error(f"Supabase Query Error: {err}")
# ==========================================
# 6. TOPOGRAPHIC MAP ENGINE
# ==========================================
m = folium.Map(
    location=[lat, lon], 
    zoom_start=9, 
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap"
)

# 50-Mile Field Boundary
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

# 100-Mile Regional Boundary
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

# LAYER 1: SIGHTINGS (SOLID BLUE DOTS)
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

# LAYER 2: CAMPSITES
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

# LAYER 3: INFRASOUND / ACOUSTIC
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

# LAYER 4: COMMUNITY FIELD LOGS (AMBER PINS)
for ulog in community_logs_data:
    log_popup = f"""
    <div style="font-family: sans-serif; width: 240px;">
        <span style="background-color:#d35400; color:white; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:bold;">⚠️ UNVETTED FIELD LOG</span><br>
        <b style="color:#2c3e50; font-size:13px;">📝 {ulog.get('observation_type', 'Field Log')}</b><br>
        <small><b>Date:</b> {ulog.get('event_date', 'N/A')}</small>
        <hr style="margin:4px 0;">
        <b>📊 Facts (Hard Data):</b>
        <p style="font-size:11px; margin:2px 0;">{ulog.get('physical_evidence_notes', 'None logged.')}</p>
        <b>💭 Field Conjecture:</b>
        <p style="font-size:11px; margin:2px 0;">{ulog.get('field_narrative', 'None logged.')}</p>
    </div>
    """
    folium.Marker(
        [ulog["latitude"], ulog["longitude"]],
        popup=folium.Popup(log_popup, max_width=260),
        icon=folium.Icon(color="orange", icon="clipboard", prefix="fa"),
        z_index_offset=700
    ).add_to(m)

# ON-MAP ALERT BADGE
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

# Render Map with Dynamic Key to Force Clean Redraw
st.caption(f"Loaded **{len(sightings_data)} sightings**, **{len(camps_data)} campsites**, **{len(audio_data)} acoustic logs**, and **{len(community_logs_data)} community field logs** in ~{radius_miles} miles.")

map_render_key = f"map_{lat:.4f}_{lon:.4f}_{radius_miles}"
st_folium(m, width="100%", height=520, returned_objects=[], key=map_render_key)

# ==========================================
# 7. INVESTIGATOR FIELD LOG FORM (UN-LED NEUTRAL ENGINE)
# ==========================================
st.markdown("---")
with st.expander("📝 Submit Investigator Field Log (Objective Data Engine)", expanded=False):
    st.caption("Log field observations directly to your private account or contribute unvetted data to the community layer.")
    
    with st.form("investigator_log_form", clear_on_submit=True):
        st.subheader("1. Privacy & Storage Settings")
        visibility = st.radio(
            "Log Storage Mode:", 
            ["🔒 Private Vault (Only Me)", "🌐 Public Community Layer (Unvetted)"], 
            horizontal=True
        )
        is_public = True if "Public" in visibility else False

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            obs_type = st.selectbox(
                "Nature of Physical Evidence", 
                [
                    "Suspect Impression",
                    "Potential Nesting / Matting Site",
                    "Vegetation Disturbance / Fractured Foliage",
                    "Acoustic Event / Audio Record",
                    "Visual Observation",
                    "Unidentified Biological Trace",
                    "Unusual Environmental Anomaly"
                ]
            )
        with col_f2:
            obs_date = st.date_input("Observation Date", value=datetime.now())
        with col_f3:
            st.write("Coordinates")
            log_lat = st.number_input("Latitude", value=float(lat), format="%.5f")
            log_lon = st.number_input("Longitude", value=float(lon), format="%.5f")

        st.markdown("---")
        st.subheader("2. Hard Field Data (Objective Facts)")
        col_facts1, col_facts2 = st.columns(2)
        with col_facts1:
            weather_temp = st.text_input(
                "Environmental Baseline & Elevation", 
                placeholder="e.g. 54°F, Clear, High Humidity, 1,200ft elevation"
            )
        with col_facts2:
            habitat_type = st.text_input(
                "Habitat & Terrain Type", 
                placeholder="e.g. Dense Pine Ridge near river drainage"
            )
        
        physical_notes = st.text_area(
            "Exactly what did you find? (Hard Physical Facts Only)", 
            placeholder="Describe physical reality without assumptions: exact measurements (length, depth, stride), scale markers used, lighting conditions, or trail surface."
        )

        st.markdown("---")
        st.subheader("3. Observer Conjecture & Hypothesis")
        col_conj1, col_conj2 = st.columns(2)
        with col_conj1:
            size_stride = st.text_input(
                "Estimated Dimensions / Stride / Gait", 
                placeholder="e.g. Estimated stride 44 inches, deep ground depression"
            )
        with col_conj2:
            st.caption("Keep subjective impressions and personal hypotheses strictly separate from hard measurements.")
        
        field_narrative = st.text_area(
            "Field Narrative & Personal Interpretation", 
            placeholder="What do you personally hypothesize caused or created this? Describe context, sequence of events, or subjective impressions."
        )

        st.markdown("---")
        st.subheader("4. Code of Ethics & Agreement")
        ethics_agree = st.checkbox(
            "I certify this is an honest field record and agree to abide by the Field Code of Ethics (zero trespassing, non-harassment of wildlife, and objective reporting)."
        )

        submit_btn = st.form_submit_button("💾 Save Investigator Field Log", use_container_width=True)

        if submit_btn:
            if not ethics_agree:
                st.error("You must agree to the Field Code of Ethics to submit a log.")
            elif not supabase:
                st.error("Database connection unavailable.")
            else:
                try:
                    log_payload = {
                        "is_public": is_public,
                        "observation_type": obs_type,
                        "event_date": str(obs_date),
                        "latitude": log_lat,
                        "longitude": log_lon,
                        "weather_temp": weather_temp,
                        "habitat_type": habitat_type,
                        "physical_evidence_notes": physical_notes,
                        "estimated_size_stride": size_stride,
                        "field_narrative": field_narrative,
                        "ethics_agreed": True
                    }
                    supabase.table("investigator_logs").insert(log_payload).execute()
                    st.success("Investigator Field Log successfully recorded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving log: {e}")

# ==========================================
# 8. REGIONAL FAUNA & BIOACOUSTIC REFERENCE ENGINE
# ==========================================
st.markdown("---")
with st.expander("🦉 Regional Bioacoustic & Fauna Reference Engine (Un-Led Acoustic Analysis)", expanded=False):
    st.caption("Cross-reference field audio against native regional wildlife vocal repertoires before logging anomalous acoustic events.")
    
    st.warning(
        "**Field Science Note on Vocal Spectrum:** Native species possess extensive vocal ranges often mistaken for anomalous sounds. "
        "For example, Barred Owls produce juvenile 'whoop' calls and group caterwauling that mimics primate troops, while Coyotes utilize complex yip-harmonic transitions."
    )
    
    col_bio1, col_bio2 = st.columns([1, 1])
    
    with col_bio1:
        st.subheader("📍 Active Target Location Bio-Profile")
        st.write(f"**Current Search Zone:** {loc_name}")
        st.write(f"**Coordinates:** `{lat:.4f}, {lon:.4f}`")
        
        st.markdown("#### Primary Regional Vocalizers to Cross-Reference")
        st.markdown("""
        * **Raptors & Owls:**
          * *Barred Owl:* Full range includes 8-accented calls, juvenile beggars, throat-whoops, and chaotic group duets/caterwauling.
          * *Great Horned Owl:* Deep territorial hoots, guttural barks, high-pitched squawks.
          * *Eastern Screech-Owl:* Tremolo whinnies and monotonic trills.
        * **Canids & Predators:**
          * *Eastern Coyote:* Solitary bark-howls, group yip-harmonics (often sounding like twice the pack size), challenge barks.
          * *Red Fox / Gray Fox:* High-pitched vixen screams, raspy alarm barks, chatter calls.
          * *Fisher Cat / Bobcat:* Screeching caterwauls, low grunts, raspy chittering.
        * **Ungulates & Large Mammals:**
          * *White-Tailed Deer:* High-pressure alarm snorts/blows, wheezes, juvenile grunts.
          * *Black Bear:* Guttural huffs, jaw-pops, woofs, and cub crying sounds.
        """)

    with col_bio2:
        st.subheader("🔗 External Bioacoustic Databases")
        st.caption("Query open-access sound archives filtered to native wildlife near your current coordinates:")
        
        macaulay_url = f"https://www.macaulaylibrary.org/catalog?searchField=location&lat={lat}&long={lon}"
        xenocanto_url = f"https://xeno-canto.org/explore?query=lat:{lat}%20lon:{lon}"
        
        st.markdown(f"""
        * [🔊 **Macaulay Library (Cornell Lab of Ornithology)**]({macaulay_url})
          *Access complete behavioral audio suites, variation recordings, and spectrograms for birds and mammals.*
        * [🌐 **Xeno-Canto Geographic Sound Database**]({xenocanto_url})
          *Search community-contributed wildlife sound recordings near active field coordinates.*
        """)
        
        st.markdown("---")
        st.subheader("📊 Neutral Acoustic Diagnostic Checklist")
        st.caption("Evaluate physical audio parameters prior to assigning species or origin hypothesis:")
        
        st.checkbox("Acoustic Cadence: Is the sound a single burst, or does it repeat at measured intervals?")
        st.checkbox("Harmonic Resonance: Does the sound exhibit low-frequency reverberation through terrain/canopy?")
        st.checkbox("Vocal Repertoire Check: Have you evaluated juvenile/duet calls for local owl or canid populations?")
        st.checkbox("Environmental Echo: Are reflections off ledges or water bodies altering pitch perception?")

# ==========================================
# 9. OFFLINE FIELD TOOLS & EXPORT ENGINE
# ==========================================
st.markdown("---")
st.markdown("### 📡 Offline Field Export & Backcountry Tools")

col_exp_btn, col_disclaimer = st.columns([1, 2])

with col_exp_btn:
    gpx_data = generate_gpx(lat, lon, loc_name, sightings_data, camps_data, audio_data, community_logs_data)
    st.download_button(
        label="📥 Download Active Area GPX Package",
        data=gpx_data,
        file_name=f"bigfoot_field_zone_{int(lat)}_{int(lon)}.gpx",
        mime="application/gpx+xml",
        use_container_width=True
    )
    st.caption("Compatible with Garmin BaseCamp, Gaia GPS, OnX Offroad, and handheld GPS units.")

with col_disclaimer:
    st.warning("**Backcountry Safety Notice:** This platform serves as a secondary spatial research engine. Always carry paper topographic maps, a compass, and dedicated navigation gear when heading off-grid.")

# ==========================================
# 10. REGIONAL FIELD CONTEXT BELOW MAP
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
                
                img_url = media_item.get('image_url')
                if img_url and str(img_url).startswith("http"):
                    st.markdown(f"[🔗 View Original Article Record / Source Image]({img_url})")
                
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
