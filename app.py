import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from shapely.geometry import Point, Polygon
from supabase import create_client, Client

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
    st.session_state.user_lat = 35.944444
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -82.772333
if "location_name" not in st.session_state:
    st.session_state.location_name = "Madison County, NC"

geolocator = Nominatim(user_agent="bigfoot_field_platform_v4")

# ==========================================
# 3. HISTORIC TRIBAL TERRITORY POLYGONS
# ==========================================
TRIBAL_BOUNDARIES = {
    "Eastern Band of Cherokee": Polygon([
        (-85.5, 33.5), (-85.5, 37.0), (-80.5, 37.0), (-80.5, 33.5), (-85.5, 33.5)
    ]),
    "Coast Salish / Halkomelem": Polygon([
        (-125.0, 46.5), (-125.0, 50.0), (-121.0, 50.0), (-121.0, 46.5), (-125.0, 46.5)
    ])
}

# ==========================================
# 4. SEARCH CONTROLS & LAYER TOGGLES
# ==========================================
col_input, col_radius, col_btn = st.columns([3, 1, 1])

with col_input:
    loc_search = st.text_input("📍 Target Search Area", value=st.session_state.location_name)

with col_radius:
    radius_miles = st.selectbox("Search Radius", [25, 50, 100, 250], index=1)
    deg_delta = radius_miles / 69.0

with col_btn:
    st.write("")
    if st.button("🔎 Update Map"):
        if loc_search:
            try:
                location = geolocator.geocode(loc_search)
                if location:
                    st.session_state.user_lat = location.latitude
                    st.session_state.user_lon = location.longitude
                    st.session_state.location_name = location.address
            except Exception:
                st.error("Geocoding service busy. Please try again.")

lat = st.session_state.user_lat
lon = st.session_state.user_lon
loc_name = st.session_state.location_name

# Layer Controls
st.markdown("**Active Layers:**")
c1, c2 = st.columns(2)
show_bfro = c1.checkbox("👣 BFRO Verified Sightings (Blue)", value=True)
show_lore = c2.checkbox("🪶 Regional Indigenous Lore (Orange)", value=True)

# ==========================================
# 5. MAP ENGINE & LAYER PRIORITY
# ==========================================
m = folium.Map(location=[lat, lon], zoom_start=9, tiles="OpenStreetMap")

# Red Pin: Center Target
folium.Marker(
    [lat, lon],
    popup=f"<b>Target Location</b><br>{loc_name}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
).add_to(m)

# ------------------------------------------
# LAYER 1 (DRAWN FIRST): BFRO SIGHTINGS (BLUE PINS)
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
            ).add_to(m)

    except Exception as e:
        st.warning(f"Database query error: {e}")

# ------------------------------------------
# LAYER 2 (DRAWN LAST = TOP PRIORITY): SPATIAL LORE
# ------------------------------------------
if show_lore and supabase:
    search_point = Point(lon, lat)
    detected_tribe = None

    for tribe_name, polygon in TRIBAL_BOUNDARIES.items():
        if polygon.contains(search_point):
            detected_tribe = tribe_name
            break

    if detected_tribe:
        try:
            lore_response = (
                supabase.table("tribal_lore")
                .select("*")
                .eq("tribe_name", detected_tribe)
                .execute()
            )
            lore_records = lore_response.data

            for lore in lore_records:
                # Self-contained card with full narrative text
                lore_popup = f"""
                <div style="font-family: sans-serif; width: 260px; max-height: 300px; overflow-y: auto;">
                    <b style="color:#d35400; font-size: 14px;">🪶 {lore['tribe_name']} Oral History</b><br>
                    <small style="color:#666;"><b>Entity / Tradition:</b> {lore['entity_name']}</small>
                    <hr style="margin: 6px 0; border: 0; border-top: 1px solid #eee;">
                    <p style="font-size: 11px; line-height: 1.4; color: #2c3e50; margin: 0;">
                        {lore['full_narrative']}
                    </p>
                </div>
                """
                
                # Placed last so it layers on top of all blue pins
                folium.Marker(
                    [lat + 0.015, lon + 0.015],
                    popup=folium.Popup(lore_popup, max_width=280),
                    icon=folium.Icon(color="orange", icon="feather", prefix="fa"),
                    z_index_offset=1000  # Forces icon to float over other markers
                ).add_to(m)

        except Exception as e:
            st.warning(f"Lore query error: {e}")

# Render Status & Map
st.caption(f"Loaded **{sightings_count} verified sightings** within ~{radius_miles} miles of target area.")
st_folium(m, width="100%", height=550, returned_objects=[])
