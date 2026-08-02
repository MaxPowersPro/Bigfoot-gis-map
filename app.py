import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from supabase import create_client, Client

# Page Setup
st.set_page_config(
    page_title="Bigfoot Sightings Nearby",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("👣 Bigfoot Sightings Near You")

# Database Connection
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception:
        return None

supabase: Client = init_supabase()

# Default Location (Madison County, NC if GPS inactive)
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 35.944444
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -82.772333
if "search_radius" not in st.session_state:
    st.session_state.search_radius = 50.0  # miles

geolocator = Nominatim(user_agent="bigfoot_mobile_locator")

# ==========================================
# LOCATION INPUT & CONTROLS
# ==========================================
col_input, col_radius, col_btn = st.columns([3, 1, 1])

with col_input:
    loc_search = st.text_input("📍 Search Town, County, or Zip", placeholder="e.g. Asheville, NC")

with col_radius:
    radius_miles = st.selectbox("Search Radius", [25, 50, 100, 250], index=1)
    # Convert miles to approximate lat/lon degrees (1 deg ~ 69 miles)
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
            except Exception:
                st.error("Location lookup failed. Try again.")

# Active Coordinates
lat = st.session_state.user_lat
lon = st.session_state.user_lon

# ==========================================
# MAP ENGINE
# ==========================================
m = folium.Map(location=[lat, lon], zoom_start=9, tiles="OpenStreetMap")

# Red Pin: User's Current Location
folium.Marker(
    [lat, lon],
    popup="<b>Your Location</b>",
    icon=folium.Icon(color="red", icon="user", prefix="fa")
).add_to(m)

# Blue Pins: Database Sightings within Search Radius
sightings_count = 0
if supabase:
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
            report_id = str(report.get('report_id', '')).strip()
            source = report.get('source', 'BFRO')

            # Generate direct link to official full report if it's a BFRO record
            if source == 'BFRO' and report_id.isdigit():
                full_report_url = f"https://www.bfro.net/GDB/show_report.asp?id={report_id}"
                link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:8px; padding:4px 8px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Read Full Report #{report_id}</a>'
            else:
                link_html = ''

            popup_content = f"""
            <div style="font-family: sans-serif; width: 230px;">
                <b style="color:#2c3e50;">👣 {report.get('title', 'Sighting Report')}</b><br>
                <small><b>Date:</b> {report.get('event_date', 'N/A')} | <b>Class:</b> {report.get('class_rating', 'A/B')}</small><br>
                <p style="font-size: 12px; margin-top: 6px; margin-bottom: 6px; color:#333;">{report.get('summary', 'No description available.')}</p>
                {link_html}
            </div>
            """
            
            folium.Marker(
                [report["latitude"], report["longitude"]],
                popup=folium.Popup(popup_content, max_width=260),
                icon=folium.Icon(color="blue", icon="tree", prefix="fa")
            ).add_to(m)

    except Exception as e:
        st.warning(f"Could not load sightings: {e}")

st.caption(f"Showing **{sightings_count} sightings** within ~{radius_miles} miles of your location.")
st_folium(m, width="100%", height=500, returned_objects=[])
