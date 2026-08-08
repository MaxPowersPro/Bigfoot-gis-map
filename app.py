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
st.caption("Site-Specific Spatial Map & Self-Contained Multi-Criteria Analysis Engine")

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
    """Suppresses high-density human infrastructure nodes and suburban centroids."""
    urban_bounds = [
        {"min_lat": 35.5, "max_lat": 35.7, "min_lon": -82.65, "max_lon": -82.45}, # Asheville, NC
        {"min_lat": 27.8, "max_lat": 28.1, "min_lon": -82.55, "max_lon": -82.30}, # Tampa Suburbs, FL
        {"min_lat": 28.4, "max_lat": 28.65, "min_lon": -81.50, "max_lon": -81.20}, # Orlando Core, FL
        {"min_lat": 38.0, "max_lat": 38.2, "min_lon": -84.6, "max_lon": -84.4},   # Lexington urban fringe, KY
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

    for c in camps:
        wpt = ET.SubElement(gpx, "wpt", lat=str(c.get("latitude")), lon=str(c.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Camp: {c.get('name', 'Campsite')}"
        ET.SubElement(wpt, "desc").text = c.get('description', '')
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
        else:
            st.error("Location not found. Please check spelling or enter a ZIP code.")

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
    show_hotspots = st.checkbox("🚨 Hot Zones & The Larson Hypothesis", value=True)
    show_audio = st.checkbox("🔊 Infrasound / Acoustic (Purple)", value=True)
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
seen_narrative_texts = set()
search_point = Point(lon, lat)

if supabase and show_lore:
    for tribe_name, polygon in TRIBAL_BOUNDARIES.items():
        if polygon.contains(search_point):
            lore_resp = supabase.table("tribal_lore").select("*").eq("tribe_name", tribe_name).execute()
            if lore_resp.data:
                for lore_item in lore_resp.data:
                    narrative = lore_item.get("full_narrative", "").strip()
                    if narrative and narrative not in seen_narrative_texts:
                        seen_narrative_texts.add(narrative)
                        detected_lore.append(lore_item)

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

# LAYER 1: SIGHTINGS (BIOLOGICAL VS. ANOMALOUS PINS)
if show_bfro and sightings_data:
    for report in sightings_data:
        raw_id = str(report.get('report_id', '')).strip()
        source = report.get('source', 'BFRO')
        class_rating = str(report.get('class_rating', 'Class A')).upper()

        if source == 'BFRO' and raw_id.isdigit() and len(raw_id) >= 3:
            full_report_url = f"https://www.bfro.net/GDB/show_report.asp?id={raw_id}"
            link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:6px; padding:4px 8px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Direct BFRO Report #{raw_id}</a>'
        else:
            link_html = ''

        is_anomalous = "CLASS C" in class_rating or "ANOMALOUS" in class_rating
        pin_color = "#8e44ad" if is_anomalous else "#2b78e4"
        pin_label = "🔮 Anomalous Sighting" if is_anomalous else "👣 Biological Sighting"

        popup_content = f"""
        <div style="font-family: sans-serif; width: 220px;">
            <b style="color:{pin_color};">{pin_label}</b><br>
            <small><b>Title:</b> {report.get('title', 'Report')} | <b>Class:</b> {class_rating}</small><br>
            <p style="font-size: 11px; margin-top: 4px; margin-bottom: 4px;">{report.get('summary', 'No summary details.')}</p>
            {link_html}
        </div>
        """

        j_lat, j_lon = apply_jitter(report["latitude"], report["longitude"], offset_seed=1)
        pin_html = f"""<div style="background-color: {pin_color}; width: 14px; height: 14px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.5);"></div>"""

        folium.Marker(
            [j_lat, j_lon],
            popup=folium.Popup(popup_content, max_width=250),
            icon=folium.DivIcon(html=pin_html, icon_size=(14, 14), icon_anchor=(7, 7)),
            z_index_offset=500
        ).add_to(m)

# LAYER 2: CAMPSITES
for camp in camps_data:
    camp_popup = f"""<div style="font-family: sans-serif; width: 210px;"><b style="color:#27ae60;">🏕️ {camp.get('name', 'Campground')}</b><br><small><b>Type:</b> {camp.get('facility_type', 'Public Campsite')}</small><br><p style="font-size: 11px; margin-top: 4px;">{camp.get('description', 'Public camping access point.')}</p></div>"""
    folium.Marker([camp["latitude"], camp["longitude"]], popup=folium.Popup(camp_popup, max_width=230), icon=folium.Icon(color="green", icon="campground", prefix="fa"), z_index_offset=400).add_to(m)

# LAYER 3: INFRASOUND / ACOUSTIC
for audio in audio_data:
    audio_popup = f"""<div style="font-family: sans-serif; width: 220px;"><b style="color:#8e44ad;">🔊 {audio.get('event_type', 'Acoustic Observation')}</b><br><small><b>Frequency:</b> {audio.get('frequency_hz', 'Low Hz')} | <b>Date:</b> {audio.get('event_date', 'N/A')}</small><br><p style="font-size: 11px; margin-top: 4px;">{audio.get('notes', 'Acoustic/Infrasound anomaly logged.')}</p></div>"""
    folium.Marker([audio["latitude"], audio["longitude"]], popup=folium.Popup(audio_popup, max_width=240), icon=folium.Icon(color="purple", icon="microphone", prefix="fa"), z_index_offset=600).add_to(m)

# LAYER 4: COMMUNITY FIELD LOGS
for ulog in community_logs_data:
    has_physical_facts = bool(ulog.get('physical_evidence_notes') and len(ulog.get('physical_evidence_notes').strip()) > 5)
    icon_color = "green" if has_physical_facts else "orange"
    badge_label = "📊 VERIFIED PHYSICAL DATA" if has_physical_facts else "⚠️ OBSERVER CONJECTURE"
    badge_bg = "#27ae60" if has_physical_facts else "#d35400"

    log_popup = f"""
    <div style="font-family: sans-serif; width: 240px;">
        <span style="background-color:{badge_bg}; color:white; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:bold;">{badge_label}</span><br>
        <b style="color:#2c3e50; font-size:13px; display:inline-block; margin-top:4px;">📝 {ulog.get('observation_type', 'Field Log')}</b><br>
        <small><b>Date:</b> {ulog.get('event_date', 'N/A')}</small>
        <hr style="margin:4px 0;">
        <b>📊 Facts (Physical Measurements):</b>
        <p style="font-size:11px; margin:2px 0;">{ulog.get('physical_evidence_notes', 'None logged.')}</p>
        <b>💭 Observer Hypothesis:</b>
        <p style="font-size:11px; margin:2px 0;">{ulog.get('field_narrative', 'None logged.')}</p>
    </div>
    """
    folium.Marker([ulog["latitude"], ulog["longitude"]], popup=folium.Popup(log_popup, max_width=260), icon=folium.Icon(color=icon_color, icon="clipboard", prefix="fa"), z_index_offset=700).add_to(m)

# ==========================================
# 7. MULTI-CRITERIA EVALUATION (MCE) & LARSON HYPOTHESIS ENGINE
# ==========================================
if show_hotspots:
    grid_lat_steps = np.linspace(lat - deg_delta, lat + deg_delta, 12)
    grid_lon_steps = np.linspace(lon - deg_delta, lon + deg_delta, 12)

    high_prob_hubs = []

    for glat in grid_lat_steps:
        for glon in grid_lon_steps:
            if filter_urban(glat, glon):
                continue
                
            dist_to_center = np.sqrt((glat - lat)**2 + (glon - lon)**2)
            env_score = max(0, 40 - (dist_to_center * 30))
            
            sightings_near = 0
            for s in sightings_data:
                s_dist = np.sqrt((glat - float(s["latitude"]))**2 + (glon - float(s["longitude"]))**2)
                if s_dist < 0.18:
                    sightings_near += 1
                    
            presence_score = sightings_near * 15
            total_score = env_score + presence_score
            
            if total_score >= 45:
                high_prob_hubs.append({"lat": glat, "lon": glon, "score": total_score, "sightings": sightings_near})

    # Render Probability Hot Zones (Red Rings)
    for hub in high_prob_hubs:
        hotzone_popup = f"""
        <div style="font-family: sans-serif; width: 230px;">
            <span style="background-color:#e74c3c; color:white; padding:2px 6px; border-radius:3px; font-size:10px; font-weight:bold;">🚨 HIGH PROBABILITY TARGET ZONE</span><br>
            <b style="color:#c0392b; font-size:13px; display:inline-block; margin-top:4px;">Multi-Criteria Suitability Hub</b><br>
            <small><b>Calculated Suitability Score:</b> {int(hub['score'])}%</small><br>
            <small><b>Local Sighting Density:</b> {hub['sightings']} reports</small>
        </div>
        """
        folium.Circle(
            radius=3500 + (hub['sightings'] * 400),
            location=[hub['lat'], hub['lon']],
            color="#e74c3c",
            weight=2,
            dash_array="4, 6",
            fill=True,
            fill_color="#e74c3c",
            fill_opacity=0.18,
            popup=folium.Popup(hotzone_popup, max_width=250)
        ).add_to(m)

    # Render The Larson Hypothesis (Amorphous Green Flow Corridors)
    if len(high_prob_hubs) > 1:
        connected_pairs = set()
        for i in range(len(high_prob_hubs)):
            h1 = high_prob_hubs[i]
            distances = []
            for j in range(len(high_prob_hubs)):
                if i == j:
                    continue
                h2 = high_prob_hubs[j]
                d = np.sqrt((h1["lat"] - h2["lat"])**2 + (h1["lon"] - h2["lon"])**2)
                distances.append((d, j))
            
            distances.sort()
            if distances and distances[0][0] < 0.38:
                j_near = distances[0][1]
                pair_key = tuple(sorted([i, j_near]))
                if pair_key not in connected_pairs:
                    connected_pairs.add(pair_key)
                    h2 = high_prob_hubs[j_near]
                    
                    vec = np.array([h2["lon"] - h1["lon"], h2["lat"] - h1["lat"]])
                    perp = np.array([-vec[1], vec[0]])
                    perp = perp / (np.linalg.norm(perp) + 1e-6) * 0.025
                    
                    p1 = [h1["lat"] + perp[1], h1["lon"] + perp[0]]
                    p2 = [h2["lat"] + perp[1], h2["lon"] + perp[0]]
                    p3 = [h2["lat"] - perp[1], h2["lon"] - perp[0]]
                    p4 = [h1["lat"] - perp[1], h1["lon"] - perp[0]]
                    
                    folium.Polygon(
                        locations=[p1, p2, p3, p4],
                        color="#27ae60",
                        weight=1.5,
                        fill=True,
                        fill_color="#27ae60",
                        fill_opacity=0.15,
                        popup="🌲 The Larson Hypothesis: Amorphous Terrain Transit Channel"
                    ).add_to(m)

st.caption(f"Loaded **{len(sightings_data)} sightings**, **{len(camps_data)} campsites**, **{len(audio_data)} acoustic logs**, and **{len(community_logs_data)} community field logs** in ~{radius_miles} miles.")
map_render_key = f"map_{lat:.4f}_{lon:.4f}_{radius_miles}"
st_folium(m, width="100%", height=520, returned_objects=[], key=map_render_key)

# ==========================================
# 8. MAIN SCREEN SECTION 1: HABITAT & LARSON HYPOTHESIS BREAKDOWN
# ==========================================
st.markdown("---")
current_month = datetime.now().month
is_leaf_on = current_month in [5, 6, 7, 8, 9]
canopy_weight = 25 if is_leaf_on else 12
larson_index = min(50 + canopy_weight + (len(sightings_data) * 2), 98)

with st.expander("🚨 Hot Zones & The Larson Hypothesis: Landscape Connectivity & Flow Breakdown", expanded=True):
    col_hs1, col_hs2, col_hs3 = st.columns(3)
    
    with col_hs1:
        st.metric("Larson Hypothesis Index", f"{larson_index}%", delta="Continuous Cover Matrix")
        st.caption(f"**Seasonal Canopy Regime:** {'🍃 Leaf-On (High Deciduous Cover)' if is_leaf_on else '🌲 Leaf-Off (Evergreen & Laurel Dependence)'}")
        
    with col_hs2:
        st.markdown("#### Environmental Suitability Drivers")
        st.markdown("""
        * **Hydrology Continuity:** Primary river/creek drainage channel within transit vector.
        * **Topographic Relief:** Steep ridge lines offering natural thermal buffers & concealed saddles.
        * **Seasonal Foliage:** Evergreen / Rhododendron thickets provide year-round low-exposure transit.
        """)
        
    with col_hs3:
        st.markdown("#### Active Target Zone Coordinates")
        st.write(f"**Target Latitude:** `{lat:.4f}`")
        st.write(f"**Target Longitude:** `{lon:.4f}`")
        st.info("Prioritize game trail funnel bottlenecks, drainage intersections, and ridge saddles along amorphous green flow channels.")

# ==========================================
# 9. MAIN SCREEN SECTION 2: BIOACOUSTICS & FAUNA REFERENCE
# ==========================================
st.markdown("---")
with st.expander("🦉 Regional Bioacoustic & Fauna Reference Engine", expanded=False):
    st.caption("Cross-reference field audio against native regional wildlife vocal repertoires before logging anomalous acoustic events.")
    st.warning("**Field Science Note on Vocal Spectrum:** Native species possess extensive vocal ranges often mistaken for anomalous sounds (e.g. Barred Owl juvenile caterwauling or Coyote yip-harmonics).")
    
    col_bio1, col_bio2 = st.columns([1, 1])
    with col_bio1:
        st.subheader("📍 Target Bio-Profile")
        st.write(f"**Location:** {loc_name} (`{lat:.4f}, {lon:.4f}`)")
        st.markdown("""
        * **Owls & Raptors:** Barred Owl (caterwauls, whoops), Great Horned Owl (deep hoots, barks), Eastern Screech-Owl.
        * **Canids & Predators:** Eastern Coyote (yip-harmonics), Red/Gray Fox (screams, alarm barks), Bobcat / Fisher Cat.
        * **Mammals:** White-Tailed Deer (alarm snorts), Black Bear (guttural huffs, jaw-pops).
        """)

    with col_bio2:
        st.subheader("🔗 External Audio Databases")
        macaulay_url = f"https://www.macaulaylibrary.org/catalog?searchField=location&lat={lat}&long={lon}"
        xenocanto_url = f"https://xeno-canto.org/explore?query=lat:{lat}%20lon:{lon}"
        st.markdown(f"""
        * [🔊 **Macaulay Library (Cornell Lab)**]({macaulay_url})
        * [🌐 **Xeno-Canto Geographic Database**]({xenocanto_url})
        """)

# ==========================================
# 10. MAIN SCREEN SECTION 3: FIELD CONTEXT & INTEL (LORE & PRESS)
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
        with st.expander(f"📰 Local Press Archives ({len(local_media_records)})", expanded=True):
            for media_item in local_media_records:
                st.markdown(f"#### 📰 {media_item['title']}")
                st.caption(f"**Publication:** {media_item['publication_name']} | **Date:** {media_item['pub_date']}")
                st.write(f"**Transcript:** {media_item['full_text_transcript']}")
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

# ==========================================
# 11. MAIN SCREEN SECTION 4: INVESTIGATOR FIELD LOG
# ==========================================
st.markdown("---")
with st.expander("📝 Submit Investigator Field Log (Facts vs. Conjecture Mode)", expanded=False):
    st.caption("Log field observations directly to your private vault or contribute unvetted data to the public layer.")
    
    with st.form("investigator_log_form", clear_on_submit=True):
        visibility = st.radio("Log Storage Mode:", ["🔒 Private Vault (Only Me)", "🌐 Public Community Layer (Unvetted)"], horizontal=True)
        is_public = True if "Public" in visibility else False

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            obs_type = st.selectbox("Nature of Evidence", ["Suspect Impression", "Potential Nesting / Matting Site", "Vegetation Disturbance", "Acoustic Event", "Visual Observation", "Biological Trace", "Environmental Anomaly"])
        with col_f2:
            obs_date = st.date_input("Observation Date", value=datetime.now())
        with col_f3:
            log_lat = st.number_input("Latitude", value=float(lat), format="%.5f")
            log_lon = st.number_input("Longitude", value=float(lon), format="%.5f")

        physical_notes = st.text_area("Hard Physical Facts Only", placeholder="Measurements, trail surface, scale markers used...")
        field_narrative = st.text_area("Observer Conjecture & Narrative", placeholder="Subjective impressions, hypotheses...")
        ethics_agree = st.checkbox("I certify this is an honest field record and agree to the Field Code of Ethics.")

        submit_btn = st.form_submit_button("💾 Save Investigator Field Log", use_container_width=True)
        if submit_btn and ethics_agree and supabase:
            try:
                log_payload = {
                    "is_public": is_public, "observation_type": obs_type, "event_date": str(obs_date),
                    "latitude": log_lat, "longitude": log_lon, "physical_evidence_notes": physical_notes,
                    "field_narrative": field_narrative, "ethics_agreed": True
                }
                supabase.table("investigator_logs").insert(log_payload).execute()
                st.success("Field log successfully recorded!")
                st.rerun()
            except Exception as e:
                st.error(f"Error saving log: {e}")

# ==========================================
# 12. MAIN SCREEN SECTION 5: OFFLINE FIELD EXPORT
# ==========================================
st.markdown("---")
st.markdown("### 📡 Offline Field Export & Backcountry Tools")

col_exp_btn, col_disclaimer = st.columns([1, 2])

with col_exp_btn:
    gpx_data = generate_gpx(
        lat, lon, loc_name, 
        sightings_data if 'sightings_data' in locals() else [], 
        camps_data if 'camps_data' in locals() else [], 
        audio_data if 'audio_data' in locals() else [], 
        community_logs_data if 'community_logs_data' in locals() else []
    )
    st.download_button(
        label="📥 Download Active Area GPX Package",
        data=gpx_data,
        file_name=f"bigfoot_field_zone_{int(lat)}_{int(lon)}.gpx",
        mime="application/gpx+xml",
        use_container_width=True
    )
    st.caption("Compatible with Garmin BaseCamp, Gaia GPS, OnX Offroad, and handheld units.")

with col_disclaimer:
    st.warning("**Backcountry Safety Notice:** Always carry analog topographic maps, a compass, and primary navigation gear when venturing off-grid.")
