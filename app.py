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
    initial_sidebar_state="collapsed"
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

geolocator = Nominatim(user_agent="bigfoot_field_platform_v11")

# Helper Function: Micro-Offsetting Jitter for overlapping sighting pins
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
# 4. SEARCH CONTROLS & GEOLOCATION
# ==========================================
col_input, col_radius, col_btn = st.columns([3, 1, 1])

with col_input:
    loc_search = st.text_input("📍 Target Search Area", value=st.session_state.location_name)

with col_radius:
    radius_miles = st.selectbox("Search Radius", [25, 50, 100, 250], index=1)
    deg_delta = radius_miles / 69.0

with col_btn:
    st.write("")
    if st.button("🔎 Search Area"):
        if loc_search:
            try:
                location = geolocator.geocode(loc_search)
                if location:
                    st.session_state.user_lat = location.latitude
                    st.session_state.user_lon = location.longitude
                    st.session_state.location_name = location.address
            except Exception:
                st.error("Geocoding service busy. Please try again.")

# Mobile GPS Auto-Location Button
if st.button("📲 Use My Current Device GPS"):
    loc = get_geolocation()
    if loc and "coords" in loc:
        st.session_state.user_lat = loc["coords"]["latitude"]
        st.session_state.user_lon = loc["coords"]["longitude"]
        st.session_state.location_name = f"Current GPS ({st.session_state.user_lat:.4f}, {st.session_state.user_lon:.4f})"
        st.rerun()

lat = st.session_state.user_lat
lon = st.session_state.user_lon
loc_name = st.session_state.location_name

# Layer Toggles
st.markdown("**Active Map Layers:**")
c1, c2, c3 = st.columns(3)
show_bfro = c1.checkbox("👣 Sightings (Solid Blue Pin)", value=True)
show_lore = c2.checkbox("🪶 Indigenous Lore (Orange Feather)", value=True)
show_news = c3.checkbox("📰 Historic Press (Black Newspaper)", value=True)

# ==========================================
# 5. TOPOGRAPHIC MAP ENGINE
# ==========================================
m = folium.Map(
    location=[lat, lon], 
    zoom_start=9, 
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap"
)

# Target Center Marker (Red Crosshairs)
folium.Marker(
    [lat, lon],
    popup=f"<b>Target Location</b><br>{loc_name}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
).add_to(m)

# ------------------------------------------
# LAYER 1: SIGHTINGS (SOLID BLUE PINS ON TERRAIN)
# ------------------------------------------
sightings_count = 0
seasonal_breakdown = {}

if show_bfro and supabase:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta

        response = (
            supabase.table("sighting_reports")
            .select("*")
            .gte("latitude", lat_min)
            .lte("latitude", lat_max)
            .gte("longitude", lon_min)
            .lte("longitude", lon_max)
            .execute()
        )
        
        sightings = response.data
        sightings_count = len(sightings)

        for report in sightings:
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

            # Solid Blue Marker (No icons inside)
            folium.Marker(
                [j_lat, j_lon],
                popup=folium.Popup(popup_content, max_width=250),
                icon=folium.Icon(color="blue"),
                z_index_offset=500
            ).add_to(m)

    except Exception as e:
        st.warning(f"Sighting query error: {e}")

# ------------------------------------------
# LAYERS 2 & 3: REGIONAL DOCKING ENGINE (RIGHT-EDGE VERTICAL LINE)
# ------------------------------------------
# Right boundary line longitude
right_dock_lon = lon + (deg_delta * 0.48)
# Starting latitude (top of the map)
current_dock_lat = lat + (deg_delta * 0.42)
# Spacing interval between docked pins
dock_spacing = deg_delta * 0.12

# 1. Dock Regional Press (Black Pins)
local_media_records = []
if supabase and show_news:
    try:
        lat_min, lat_max = lat - deg_delta, lat + deg_delta
        lon_min, lon_max = lon - deg_delta, lon + deg_delta

        media_response = (
            supabase.table("historical_media")
            .select("*")
            .gte("latitude", lat_min)
            .lte("latitude", lat_max)
            .gte("longitude", lon_min)
            .lte("longitude", lon_max)
            .execute()
        )
        local_media_records = media_response.data

        for article in local_media_records:
            img_link = article.get("image_url")
            if img_link:
                link_btn = f'<br><a href="{img_link}" target="_blank" style="display:inline-block; margin-top:4px; font-size:11px; color:#27ae60; font-weight:bold;">🔗 View Original Article Image / Record</a>'
            else:
                link_btn = ''

            media_popup = f"""
            <div style="font-family: sans-serif; width: 250px;">
                <b style="color:#000000;">📰 {article['title']}</b><br>
                <small><b>Source:</b> {article['publication_name']} ({article['pub_date']})</small>
                <hr style="margin: 4px 0;">
                <p style="font-size: 11px; line-height: 1.3;">{article['full_text_transcript']}</p>
                {link_btn}
            </div>
            """
            
            # Drop pin in the clean right-side vertical column
            folium.Marker(
                [current_dock_lat, right_dock_lon],
                popup=folium.Popup(media_popup, max_width=270),
                icon=folium.Icon(color="black", icon="newspaper", prefix="fa"),
                z_index_offset=900
            ).add_to(m)

            # Move next dock position down
            current_dock_lat -= dock_spacing

    except Exception as e:
        st.warning(f"Media query error: {e}")

# 2. Dock Regional Indigenous Lore (Orange Pins)
detected_lore = []
search_point = Point(lon, lat)

if supabase:
    for tribe_name, polygon in TRIBAL_BOUNDARIES.items():
        if polygon.contains(search_point):
            lore_resp = supabase.table("tribal_lore").select("*").eq("tribe_name", tribe_name).execute()
            if lore_resp.data:
                detected_lore.extend(lore_resp.data)

            if show_lore:
                for lore in lore_resp.data:
                    lore_popup = f"""
                    <div style="font-family: sans-serif; width: 260px;">
                        <b style="color:#d35400;">🪶 {lore['tribe_name']} Oral History</b><br>
                        <small><b>Entity:</b> {lore['entity_name']}</small>
                        <p style="font-size: 11px; line-height: 1.4;">{lore['full_narrative']}</p>
                    </div>
                    """
                    # Drop pin directly below press pins in the right-side vertical column
                    folium.Marker(
                        [current_dock_lat, right_dock_lon],
                        popup=folium.Popup(lore_popup, max_width=280),
                        icon=folium.Icon(color="orange", icon="feather", prefix="fa"),
                        z_index_offset=1000
                    ).add_to(m)

                    current_dock_lat -= dock_spacing

# Render Map View
st.caption(f"Loaded **{sightings_count} verified sightings** within ~{radius_miles} miles of target area.")
st_folium(m, width="100%", height=550, returned_objects=[])

# ==========================================
# 6. REGIONAL FIELD CONTEXT BELOW MAP
# ==========================================
st.markdown("---")
st.markdown("### 🗂️ Regional Field Context & Intelligence Panel")

col_lore_btn, col_media_btn, col_season_btn = st.columns(3)

with col_lore_btn:
    if detected_lore:
        with st.expander(f"🪶 Regional Oral Histories ({len(detected_lore)})", expanded=False):
            for lore_item in detected_lore:
                st.markdown(f"**{lore_item['tribe_name']} — {lore_item['entity_name']}**")
                st.write(f"> {lore_item['full_narrative']}")
    else:
        st.info("No recorded regional indigenous narratives within active target boundary.")

with col_media_btn:
    if local_media_records:
        with st.expander(f"📰 Local Press & Archives ({len(local_media_records)})", expanded=False):
            for media_item in local_media_records:
                st.markdown(f"**📰 {media_item['title']}**")
                st.caption(f"{media_item['publication_name']} | {media_item['pub_date']} | {media_item['county']}, {media_item['state_province']}")
                st.write(f"* **Transcript:** {media_item['full_text_transcript']}")
                if media_item.get('image_url'):
                    st.markdown(f"[🔗 View Original Article Image / Record]({media_item['image_url']})")
                st.markdown("---")
    else:
        st.info(f"No historical press accounts tagged within {radius_miles} miles.")

with col_season_btn:
    with st.expander("🍂 Seasonal Activity Breakdown", expanded=False):
        if seasonal_breakdown:
            for season_name, count in seasonal_breakdown.items():
                st.markdown(f"**{season_name}:** {count} reports")
        else:
            st.info("No dated sighting activity in this active search area.")
