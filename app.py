import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

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

# Custom CSS for Solid Lower-Left Map UI Buttons & Popups
st.markdown("""
<style>
.map-container {
    position: relative;
}
.floating-ui-container {
    position: absolute;
    bottom: 30px;
    left: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.solid-map-btn {
    background-color: #1e293b;
    color: #ffffff !important;
    border: 2px solid #38bdf8;
    padding: 10px 16px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);
    cursor: pointer;
    text-align: left;
}
</style>
""", unsafe_allow_html=True)

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

# Initialize Location State (Fallback to MA region)
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 41.7000
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -70.3000
if "location_name" not in st.session_state:
    st.session_state.location_name = "Massachusetts Target Zone"

geolocator = Nominatim(user_agent="bigfoot_field_platform_v7")

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
show_bfro = c1.checkbox("👣 BFRO Sightings (Blue)", value=True)
show_lore = c2.checkbox("🪶 Indigenous Lore (Orange)", value=True)
show_news = c3.checkbox("📰 Physical Press Locations (Black)", value=True)

# ==========================================
# 5. TOPOGRAPHIC MAP ENGINE & CLUSTERING
# ==========================================
m = folium.Map(
    location=[lat, lon], 
    zoom_start=9, 
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr="OpenTopoMap"
)

# Enable MarkerCluster with Spiderfy so overlapping pins fan out cleanly
marker_cluster = MarkerCluster(spiderfyOnMaxZoom=True, showCoverageOnHover=False).add_to(m)

# Target Center Marker
folium.Marker(
    [lat, lon],
    popup=f"<b>Target Location</b><br>{loc_name}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
).add_to(marker_cluster)

# ------------------------------------------
# LAYER 1: SIGHTINGS (BLUE PINS)
# ------------------------------------------
sightings_count = 0
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

            if source == 'BFRO' and raw_id.isdigit() and len(raw_id) >= 3:
                full_report_url = f"https://www.bfro.net/GDB/show_report.asp?id={raw_id}"
                link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:6px; padding:4px 8px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Direct BFRO Report #{raw_id}</a>'
            else:
                link_html = ''

            popup_content = f"""
            <div style="font-family: sans-serif; width: 220px;">
                <b style="color:#2c3e50;">👣 {report.get('title', 'Sighting Report')}</b><br>
                <small><b>Date:</b> {report.get('event_date', 'N/A')} | <b>Class:</b> {report.get('class_rating', 'A/B')}</small><br>
                <p style="font-size: 11px; margin-top: 4px; margin-bottom: 4px;">{report.get('summary', 'No summary details.')}</p>
                {link_html}
            </div>
            """

            folium.Marker(
                [report["latitude"], report["longitude"]],
                popup=folium.Popup(popup_content, max_width=250),
                icon=folium.Icon(color="blue", icon="tree", prefix="fa")
            ).add_to(marker_cluster)

    except Exception as e:
        st.warning(f"Sighting query error: {e}")

# ------------------------------------------
# LAYER 2: SPATIAL LORE & AMBIENT MEDIA DATA
# ------------------------------------------
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
                    folium.Marker(
                        [lat + 0.01, lon + 0.01],
                        popup=folium.Popup(lore_popup, max_width=280),
                        icon=folium.Icon(color="orange", icon="feather", prefix="fa"),
                        z_index_offset=1000
                    ).add_to(marker_cluster)

# ------------------------------------------
# LAYER 3: HISTORICAL NEWSPAPERS (BLACK HIGH-CONTRAST PINS)
# ------------------------------------------
local_media_records = []
if supabase:
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

        if show_news:
            for article in local_media_records:
                art_lat = article.get("latitude")
                art_lon = article.get("longitude")

                if art_lat and art_lon:
                    media_popup = f"""
                    <div style="font-family: sans-serif; width: 250px;">
                        <b style="color:#000000;">📰 {article['title']}</b><br>
                        <small><b>Source:</b> {article['publication_name']} ({article['pub_date']})</small>
                        <hr style="margin: 4px 0;">
                        <p style="font-size: 11px; line-height: 1.3;">{article['full_text_transcript']}</p>
                    </div>
                    """
                    folium.Marker(
                        [float(art_lat), float(art_lon)],
                        popup=folium.Popup(media_popup, max_width=270),
                        icon=folium.Icon(color="black", icon="newspaper", prefix="fa"),
                        z_index_offset=900
                    ).add_to(marker_cluster)

    except Exception as e:
        st.warning(f"Media query error: {e}")

# Render Map View
st.caption(f"Loaded **{sightings_count} verified sightings** within ~{radius_miles} miles of target area.")
st_folium(m, width="100%", height=550, returned_objects=[])

# ==========================================
# 6. LOWER-LEFT SOLID UI CONTROLS & OVERLAYS
# ==========================================
st.markdown("### 🗂️ Regional Field Context & Media Panel")

col_lore_btn, col_media_btn = st.columns(2)

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
        with st.expander(f"📰 Local Press & Print Media ({len(local_media_records)})", expanded=False):
            for media_item in local_media_records:
                st.markdown(f"**📰 {media_item['title']}**")
                st.caption(f"{media_item['publication_name']} | {media_item['pub_date']} | {media_item['county']}, {media_item['state_province']}")
                st.write(f"* **Synopsis / Transcript:** {media_item['full_text_transcript']}")
                st.markdown("---")
    else:
        st.info(f"No historical print accounts tagged within {radius_miles} miles.")
