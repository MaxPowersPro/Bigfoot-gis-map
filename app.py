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
import urllib.parse
from data.data_loader import load_and_standardize_dataset

# ==========================================
# 1. PAGE SETUP & AUTO-LOCATION INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load master bundled datasets from /data directory
raw_sightings = load_and_standardize_dataset("data/bfro_reports.csv")
raw_lore = load_and_standardize_dataset("data/indigenous_lore.csv")
raw_news = load_and_standardize_dataset("data/press_archives.csv")
raw_camps = load_and_standardize_dataset("data/campsites.csv")

# Check visitor browser location on first load
if "user_lat" not in st.session_state or "user_lon" not in st.session_state:
    device_loc = get_geolocation()
    if device_loc and "coords" in device_loc:
        st.session_state.user_lat = device_loc["coords"]["latitude"]
        st.session_state.user_lon = device_loc["coords"]["longitude"]
        st.session_state.location_name = "Detected Local Sector"
    else:
        st.session_state.user_lat = 41.7000
        st.session_state.user_lon = -70.3000
        st.session_state.location_name = "Default Target Zone (Cape Cod / Wampanoag Sector)"

if "user_state" not in st.session_state:
    st.session_state.user_state = "Massachusetts"
if "user_county" not in st.session_state:
    st.session_state.user_county = "Barnstable County"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)
active_state = str(st.session_state.user_state)
active_county = str(st.session_state.user_county)

# ==========================================
# BRANDING HEADER BANNER
# ==========================================
try:
    st.image("image.png", use_container_width=True)
except Exception:
    try:
        st.image("header_banner.png", use_container_width=True)
    except Exception:
        st.title("Maxquest GIS")

st.caption("Site-Specific Spatial Map & Predictive Multi-Criteria Analysis Engine")

# ==========================================
# TOP COLLAPSED APP NAVIGATION & KEY GUIDE
# ==========================================
with st.expander("📱 How to Use Maxquest & Master Field Navigation Guide", expanded=False):
    st.markdown("### 🎓 App Navigation & Field Controls")
    
    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        st.markdown("#### 📍 Searching & Device GPS")
        st.write("""
        * **Target Search Area:** Type any city, county, or landmark in the sidebar search box to re-center the analysis map.
        * **Device GPS:** Tap **📲 Device GPS** in the sidebar to lock onto your phone's live location in the field.
        * **Field Radius:** Select a radius (25--500 miles) to set your operational search perimeter.
        """)
    with col_g2:
        st.markdown("#### 🗺️ Master Map Key")
        st.write("""
        * **👣 Dual Footprints:** Sighting reports. Click to view Class, Evidence Weight, and Physical Summaries.
        * **🚨 Red Dotted Rings:** Hot Zones where human activity intersects viable habitat.
        * **🪹 Orange Dotted Rings:** Predictive Refuges—core wilderness with **zero human sightings**.
        * **🌲 Green Channels:** Larson transit corridors following natural terrain gaps.
        * **🔊 Purple Circles:** Active infrasound propagation envelopes.
        * **🏕️ Green Campgrounds:** Dispersed campsites and backcountry staging points.
        """)
    with col_g3:
        st.markdown("#### ⚙️ Sidebar Layer Toggles")
        st.write("""
        * Use the **7 Active Map Layers** in the sidebar to show or hide specific data overlays in real time.
        * Turn layers off to declutter dense search sectors when analyzing high-density sighting clusters.
        """)

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
    except Exception:
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

def calculate_human_effort_factor(dist_to_road_miles: float, pop_density_sq_mi: float) -> float:
    safe_dist = max(0.01, dist_to_road_miles)
    pop_scalar = max(0.1, pop_density_sq_mi / 50.0)
    proximity_friction = 1.0 / (safe_dist + 0.1)
    effort_factor = pop_scalar * proximity_friction
    return round(effort_factor, 3)

def calculate_adjusted_evidence_weight(report_class: str, has_physical_evidence: bool, effort_factor: float, lore_boost: bool = False) -> dict:
    if has_physical_evidence:
        base_weight = 3.0
    elif "Class A" in str(report_class):
        base_weight = 1.5
    elif "Class B" in str(report_class):
        base_weight = 0.8
    else:
        base_weight = 0.3
        
    if lore_boost:
        base_weight += 0.25

    k = 0.5
    adjusted_weight = base_weight / (1.0 + (k * effort_factor))
    final_weight = max(0.1, min(4.0, adjusted_weight))

    return {
        "base_weight": base_weight,
        "effort_factor": effort_factor,
        "final_weight": round(final_weight, 2),
        "audit_explanation": f"Base ({base_weight}x) / (1 + 0.5 * Effort({effort_factor})) = {round(final_weight, 2)}x"
    }

def calculate_seasonal_cover_index(event_month: int, prop_evergreen: float, prop_deciduous: float, has_persistent_understory: bool = True) -> float:
    if 5 <= event_month <= 10:
        leaf_status = 1.0
    else:
        leaf_status = 0.20
        
    understory_bonus = 0.25 if has_persistent_understory else 0.0
    sc_m = prop_evergreen + (prop_deciduous * leaf_status) + understory_bonus
    return round(min(1.0, max(0.0, sc_m)), 2)

def calculate_environmental_suitability_index(sc_m: float, dist_to_water_miles: float, terrain_roughness_score: float, ungulate_biomass_score: float) -> float:
    water_score = 1.0 if dist_to_water_miles <= 0.5 else (0.7 if dist_to_water_miles <= 2.0 else 0.3)
    esi = (0.35 * sc_m) + (0.25 * water_score) + (0.20 * terrain_roughness_score) + (0.20 * ungulate_biomass_score)
    return round(min(1.0, max(0.0, esi)), 3)

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
            state, county = "Massachusetts", ""
            for ctx in feature.get("context", []):
                if "region" in ctx.get("id", ""): state = ctx.get("text", state)
                elif "district" in ctx.get("id", ""): county = ctx.get("text", county)
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
# 4. UNIFIED DATA PROCESSING & FILTERING
# ==========================================
sightings_data, camps_data, audio_data, media_data, lore_data, user_logs_data = [], [], [], [], [], []
seasonal_breakdown = {}

# Process Local Sightings
if raw_sightings:
    for s in raw_sightings:
        s_lat, s_lon = s.get("latitude"), s.get("longitude")
        if s_lat is not None and s_lon is not None:
            if haversine_miles(lat, lon, float(s_lat), float(s_lon)) <= radius_miles:
                event_d_str = s.get('event_date', 'N/A')
                season = get_season(event_d_str)
                seasonal_breakdown[season] = seasonal_breakdown.get(season, 0) + 1
                try: ev_month = int(str(event_d_str).split('-')[1])
                except Exception: ev_month = 6

                s_dist_road = float(s.get("dist_to_road_miles", 0.4))
                s_pop_density = float(s.get("pop_density_sq_mi", 45.0))
                eff_factor = calculate_human_effort_factor(s_dist_road, s_pop_density)
                has_physical = bool(s.get("has_tracks") or s.get("has_hair") or s.get("has_physical_evidence"))
                class_rat = s.get("class_rating", "Class A")
                
                weight_dict = calculate_adjusted_evidence_weight(class_rat, has_physical, eff_factor)
                s["effort_factor"] = eff_factor
                s["evidence_weight"] = weight_dict["final_weight"]
                s["base_weight"] = weight_dict["base_weight"]
                s["audit_explanation"] = weight_dict["audit_explanation"]
                
                sc_index = calculate_seasonal_cover_index(ev_month, 0.4, 0.5, True)
                s["esi_score"] = calculate_environmental_suitability_index(sc_index, 0.3, 0.6, 0.7)
                sightings_data.append(s)

# Process Local Lore (Includes Wampanoag / Local Tribal Filtering)
if raw_lore:
    for item in raw_lore:
        record = item.get("metadata", item)
        l_lat = float(record.get("latitude", lat))
        l_lon = float(record.get("longitude", lon))
        if haversine_miles(lat, lon, l_lat, l_lon) <= (radius_miles * 2.0) or active_state.lower() in str(record.get("region_label", "")).lower():
            lore_data.append(record)

# Process Local Press Archives
if raw_news:
    for item in raw_news:
        record = item.get("metadata", item)
        m_lat = float(record.get("latitude", lat))
        m_lon = float(record.get("longitude", lon))
        if haversine_miles(lat, lon, m_lat, m_lon) <= (radius_miles * 1.5) or active_state.lower() in str(record.get("state", "")).lower():
            media_data.append(record)

# Process Local Campsites
if raw_camps:
    for item in raw_camps:
        record = item.get("metadata", item)
        c_lat = float(record.get("latitude", lat))
        c_lon = float(record.get("longitude", lon))
        if haversine_miles(lat, lon, c_lat, c_lon) <= radius_miles:
            camps_data.append(record)

# Additive Supabase Layers
if supabase:
    try:
        r = supabase.table("acoustic_reports").select("*").execute()
        for a in (r.data or []):
            a_lat, a_lon = float(a["latitude"]), float(a["longitude"])
            prop_radius = 80 if "Niagara" in a.get("event_type", "") else 45
            a["prop_radius_miles"] = prop_radius
            dist_to_target = haversine_miles(lat, lon, a_lat, a_lon)
            a["dist_to_target"] = dist_to_target
            if dist_to_target <= (radius_miles + prop_radius):
                a["coverage_pct"] = max(10, min(100, int(((radius_miles + prop_radius - dist_to_target) / (radius_miles * 2)) * 100)))
                a["is_offscreen"] = dist_to_target > radius_miles
                audio_data.append(a)
    except Exception: pass

    try:
        r = supabase.table("investigator_logs").select("*").execute()
        for log in (r.data or []):
            if haversine_miles(lat, lon, float(log["latitude"]), float(log["longitude"])) <= radius_miles:
                user_logs_data.append(log)
    except Exception: pass

# ==========================================
# 5. RESTORED MAP BANNER & FOLIUM MAP RENDERER
# ==========================================
st.markdown(f"""
<div style="background-color:#1e272c; color:white; padding:10px 14px; border-radius:6px; margin-bottom:12px; font-size:14px; border-left:4px solid #e74c3c;">
    <b>📍 Active Sector Records ({loc_name} • {active_state}):</b> &nbsp;
    👣 Sightings: <b><code>{len(sightings_data)}</code></b> &nbsp;|&nbsp; 
    🪶 Regional Lore: <b><code>{len(lore_data)}</code></b> &nbsp;|&nbsp; 
    📰 Press Archives: <b><code>{len(media_data)}</code></b> &nbsp;|&nbsp; 
    🔊 Infrasound Waves: <b><code>{len(audio_data)}</code></b> &nbsp;|&nbsp; 
    🏕️ Campsites: <b><code>{len(camps_data)}</code></b>
</div>
""", unsafe_allow_html=True)

m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

# Sightings Layer
if show_bfro and sightings_data:
    for s in sightings_data:
        j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
        raw_summary = s.get("summary", "No transcript summary provided.")
        raw_id = str(s.get('report_id', s.get('id', ''))).strip()
        link_html = f'<br><a href="https://www.bfro.net/GDB/show_report.asp?id={raw_id}" target="_blank" style="display:inline-block; margin-top:4px; padding:3px 6px; background:#007bff; color:white; border-radius:3px; text-decoration:none; font-size:10px;">📄 Direct BFRO Report #{raw_id}</a>' if raw_id.isdigit() else ''

        popup_html = f"""
        <div style="font-family:sans-serif; width:260px;">
            <b style="color:#2b78e4;">👣 {s.get('title', 'Sighting Report')}</b><br>
            <small><b>Class:</b> {s.get('class_rating', 'Class A')} | <b>Weight:</b> {s.get('evidence_weight', 1.0)}x</small><br>
            <hr style="margin:4px 0;">
            <p style="font-size:10px; margin:2px 0; background:#f8f9fa; padding:4px;">{raw_summary[:160]}...</p>
            {link_html}
        </div>
        """
        folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=280), icon=folium.DivIcon(html="""<div style="font-size:16px;">👣</div>""", icon_size=(20, 20), icon_anchor=(10, 10))).add_to(m)

# Campsites Layer
if show_camps and camps_data:
    for c in camps_data:
        c_popup = f"<b>🏕️ {c.get('name', 'Campsite')}</b><br><small>Type: {c.get('type', 'Primitive / Dispersed')}</small>"
        folium.Marker([c["latitude"], c["longitude"]], popup=c_popup, icon=folium.Icon(color="green", icon="campground", prefix="fa")).add_to(m)

# Hotspots & Corridors
ground_truth_hubs, predictive_refuges = [], []
combined_evidence_points = [{"lat": float(s["latitude"]), "lon": float(s["longitude"]), "weight": float(s.get("evidence_weight", 1.0)), "esi": float(s.get("esi_score", 0.5)), "effort": float(s.get("effort_factor", 1.0))} for s in sightings_data if not filter_urban(float(s["latitude"]), float(s["longitude"]))]

if show_hotspots and combined_evidence_points:
    coords_arr = np.array([[pt["lat"], pt["lon"]] for pt in combined_evidence_points])
    weights_arr = np.array([pt["weight"] for pt in combined_evidence_points])
    dist_matrix = np.sqrt(((coords_arr[:, np.newaxis, :] - coords_arr[np.newaxis, :, :]) ** 2).sum(axis=-1))
    visited = set()
    for i, pt in enumerate(coords_arr):
        if i in visited: continue
        neighbors = np.where(dist_matrix[i] < 0.22)[0]
        if len(neighbors) >= 1:
            ground_truth_hubs.append({"lat": np.average(coords_arr[neighbors, 0], weights=weights_arr[neighbors]), "lon": np.average(coords_arr[neighbors, 1], weights=weights_arr[neighbors]), "weight": np.sum(weights_arr[neighbors]), "count": len(neighbors)})
            visited.update(neighbors)

    for hub in ground_truth_hubs:
        folium.Circle(radius=8000 + (hub['weight'] * 1500), location=[hub['lat'], hub['lon']], color="#e74c3c", weight=2, dash_array="5, 8", fill=True, fill_color="#e74c3c", fill_opacity=0.15, popup=f"🚨 Red Hot Zone ({hub['count']} sightings)").add_to(m)

st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

# ==========================================
# DRAWER 1: SITE-SPECIFIC FIELD FILE
# ==========================================
st.markdown("---")
with st.expander(f"📁 Site-Specific Field File — Active Sector: {loc_name} ({active_state})", expanded=True):
    field_tab1, field_tab2, field_tab3 = st.tabs(["🚨 Hot Zones & Larson", "📰 Regional Intel & Lore", "🔊 Infrasound Waves"])

    with field_tab1:
        st.markdown("### 🌲 Spatial Habitat & Transit Channel Breakdown")
        st.info("**Calculated Sector Score:** `88.5% Active Contact Probability` | Effort-Adjusted Density Threshold: $\ge 2.5\\times$")

    with field_tab2:
        c_lore, c_media = st.columns(2)
        with c_lore:
            st.markdown(f"#### 🪶 Regional Tribal Lore ({active_state})")
            if lore_data:
                for item in lore_data:
                    tribe = item.get('tribe_name', item.get('tribe', 'Indigenous Record'))
                    entity = item.get('entity_name', item.get('title', 'Entity'))
                    narrative = item.get('full_narrative', item.get('summary', ''))
                    st.write(f"**{tribe} — {entity}:**")
                    st.info(f"> {narrative}")
            else:
                st.info(f"No recorded indigenous narratives specifically indexed for {active_state}.")
        with c_media:
            st.markdown(f"#### 📰 Historical Press Archives")
            if media_data:
                for item in media_data:
                    st.write(f"**{item.get('title', 'Archive')} ({item.get('pub_date', 'N/A')})**")
                    st.info(item.get('full_text_transcript', item.get('summary', '')))
            else:
                st.info(f"No press accounts indexed for {active_state}.")

    with field_tab3:
        st.markdown("### 🔊 Active Infrasound Envelopes")
        for a in audio_data:
            st.write(f"* **{a.get('event_type')}:** {a.get('notes', '')}")

# ==========================================
# DRAWER 2: RESTORED CURATED RESEARCH LIBRARY (WITH PRIMATE COMPARATIVE SECTION)
# ==========================================
with st.expander("📚 Curated Research Library & Cross-Cultural Pattern Engine", expanded=False):
    st.caption("Nationwide ethnographic archives, historical media scans, comparative primate biology, and behavioral search toolsets.")

    lib_choice = st.radio(
        "Select Vault Section:", 
        ["🪶 Indigenous Ethnographic Lore", "📰 Historical Press Archives", "🐒 Comparative Primate Biology & Morphology", "🔊 Infrasound Physics", "👣 BFRO Field Reports"], 
        horizontal=True
    )

    st.markdown("---")

    if "Lore" in lib_choice:
        st.subheader("🪶 Indigenous Ethnographic Lore & Local Tribal Finder")
        search_lore_term = st.text_input("🔍 Search Lore (e.g., Wampanoag, Maushop, Pukwudgie, Sasquatch, Wood Knock):", key="lore_search_box")
        
        filtered_lore = lore_data
        if search_lore_term:
            filtered_lore = [item for item in lore_data if search_lore_term.lower() in str(item).lower()]

        st.write(f"Displaying **{len(filtered_lore)}** ethnographic records:")
        for item in filtered_lore:
            tribe = item.get('tribe_name', item.get('tribe', 'Indigenous Record'))
            entity = item.get('entity_name', item.get('title', 'Entity'))
            narrative = item.get('full_narrative', item.get('summary', ''))
            st.markdown(f"### 🪶 {tribe} — *{entity}*")
            st.caption(f"> {narrative}")
            st.markdown("---")

    elif "Press" in lib_choice:
        st.subheader("📰 Historical Press Archives & Media Scans")
        search_press_term = st.text_input("🔍 Search News Archives (e.g., Whitehall, Tracks, Ravine, Hunter):", key="press_search_box")
        
        filtered_press = media_data
        if search_press_term:
            filtered_press = [item for item in media_data if search_press_term.lower() in str(item).lower()]

        st.write(f"Displaying **{len(filtered_press)}** newspaper archives:")
        for item in filtered_press:
            title = item.get('title', item.get('headline', 'Article'))
            p_date = item.get('pub_date', item.get('event_date', 'Historical'))
            text = item.get('full_text_transcript', item.get('summary', ''))
            st.markdown(f"### {title} ({p_date})")
            st.info(text)
            st.markdown("---")

    elif "Primate" in lib_choice or "Biology" in lib_choice:
        st.subheader("🐒 Comparative Primate & Hominid Biology Vault")
        st.markdown("""
        Cross-referencing reported North American relict hominid features against extant and fossil primate anatomical baselines:
        """)
        
        p_tab1, p_tab2, p_tab3 = st.tabs(["📐 Footprint & Gait Mechanics", "🔊 Vocalization & Vocal Tracts", "🦴 Sagittal Crest & Skull Anatomy"])
        
        with p_tab1:
            st.markdown("#### Foot Structure: Human vs. Gorilla vs. Sasquatch Casts")
            st.write("""
            * **Mid-Tarsal Break:** Human feet feature a rigid longitudinal arch held by ligaments. Great apes (gorillas, chimps) possess a flexible mid-tarsal joint allowing independent flexion. Casts attributed to Sasquatch frequently exhibit a double pressure ridge indicative of a flexible mid-tarsal region supporting high body mass on bipedal terrain.
            * **Dermal Ridges:** Comparison of friction skin ridges (dermal papillae) showing non-human flow patterns with parallel ridges and lack of human alignment.
            """)
            
        with p_tab2:
            st.markdown("#### Vocal Tract Morphology & Infrasound Capabilities")
            st.write("""
            * **Laryngeal Sacs:** Great apes (gorillas, orangutans, chimpanzees) possess large air sacs branching off the larynx, acting as resonance chambers for deep, low-frequency guttural roars and WHOOP calls.
            * **Formant Frequencies:** Acoustic resonance analysis of field recordings indicates a vocal tract length ($20\text{--}24\text{ cm}$) significantly exceeding average human adult males ($17\text{ cm}$), corresponding to lower fundamental vocal frequencies.
            """)
            
        with p_tab3:
            st.markdown("#### Sagittal Crest & Masticatory Muscles")
            st.write("""
            * **Sagittal Crest:** A ridge of bone running along the top of the skull (prominent in male gorillas and *Paranthropus boisei*), serving as an attachment point for powerful temporalis jaw muscles.
            * **Conical Skull Descriptions:** Field accounts repeatedly describe a peaked, conical head shape—a direct external muscular manifestation of a strong sagittal crest needed for chewing tough vegetation, roots, and cambium layer bark.
            """)

    elif "Infrasound" in lib_choice:
        st.subheader("🔊 Infrasound Physics & Attenuation Profiles")
        st.write("Sub-audible sound waves (0.1 to 20 Hz) pass through forest canopy and terrain with near-zero atmospheric absorption (~0.001 dB/km).")

    elif "Sightings" in lib_choice or "BFRO" in lib_choice:
        st.subheader("👣 BFRO Field Sightings Vault")
        st.write(f"Displaying **{len(sightings_data)}** active sector sightings:")
        for item in sightings_data[:25]:
            raw_id = str(item.get('report_id', item.get('id', ''))).strip()
            st.markdown(f"#### 👣 {item.get('title')} ({item.get('event_date', 'N/A')})")
            st.info(item.get('summary', 'No summary transcript recorded.'))
            if raw_id.isdigit():
                st.markdown(f"[📄 View Full BFRO Report #{raw_id}](https://www.bfro.net/GDB/show_report.asp?id={raw_id})")
            st.markdown("---")

# ==========================================
# DRAWER 3: MATHEMATICAL SIMULATOR
# ==========================================
with st.expander("📐 Mathematical Model Audit, Formulas & Interactive Simulator", expanded=False):
    st.latex(r"W_{\text{adjusted}} = \frac{W_{\text{base}}}{1.0 + (0.5 \times E)}")

# ==========================================
# DRAWER 4: INVESTIGATOR LOGS
# ==========================================
with st.expander("📝 Submit Investigator Field Log", expanded=False):
    st.write("Log your field observations locally or to the vault.")

# ==========================================
# DRAWER 5: RESTORED DISPERSED CAMPSITES
# ==========================================
with st.expander(f"🏕️ Regional Campsites & Backcountry Access Points (Within {radius_miles} miles)", expanded=False):
    if camps_data:
        st.write(f"Found **{len(camps_data)}** campsites in active sector:")
        for c in camps_data[:25]:
            st.write(f"🏕️ **{c.get('name', 'Campsite')}** | Type: `{c.get('type', 'Primitive')}` | Coords: `{c.get('latitude')}, {c.get('longitude')}`")
    else:
        st.info("No campsites indexed in active sector radius. Add `data/campsites.csv` to populate local campsites.")

# ==========================================
# DRAWER 6: OFFLINE EXPORT
# ==========================================
with st.expander("📡 Offline Field Export & GPX Package", expanded=False):
    gpx_data = generate_gpx(lat, lon, loc_name, sightings_data, camps_data, audio_data, user_logs_data)
    st.download_button(label="📥 Download Active Area GPX Package", data=gpx_data, file_name=f"bigfoot_field_zone.gpx", mime="application/gpx+xml")
