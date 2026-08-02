import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from supabase import create_client, Client

# ==========================================
# 1. PAGE SETUP & MOBILE STYLING
# ==========================================
st.set_page_config(
    page_title="Bigfoot Sightings Nearby",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("👣 Bigfoot Sightings Near You")

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

# Initialize location state (Defaults to Madison County, NC)
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 35.944444
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -82.772333

geolocator = Nominatim(user_agent="bigfoot_mobile_locator_v2")

# ==========================================
# 3. SEARCH CONTROLS
# ==========================================
col_input, col_radius, col_btn = st.columns([3, 1, 1])

with col_input:
    loc_search = st.text_input("📍 Enter Location (City, County, or Zip)", placeholder="e.g. Asheville, NC or Madison County NC")

with col_radius:
    radius_miles = st.selectbox("Search Radius", [25, 50, 100, 250], index=1)
    # Convert miles to approximate latitude/longitude degrees (1 degree ~ 69 miles)
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
                    st.success(f"Locked to: {location.address}")
                else:
                    st.error("Location not found. Try adding a state abbreviation.")
            except Exception:
                st.error("Geocoding service timed out. Please try again.")

# Active coordinates
lat = st.session_state.user_lat
lon = st.session_state.user_lon

# ==========================================
# 4. MAP ENGINE & SIGHTINGS QUERY
# ==========================================
m = folium.Map(location=[lat, lon], zoom_start=9, tiles="OpenStreetMap")

# Red Pin: User's Search Location
folium.Marker(
    [lat, lon],
    popup="<b>Search Center Target</b>",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
).add_to(m)

sightings_count = 0

if supabase:
    try:
        # Bounding box around search target
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
            # Clean and validate the report_id
            raw_id = str(report.get('report_id', '')).strip()
            source = report.get('source', 'BFRO')
            state_abbr = str(report.get('state', '')).strip()

            # Smart link logic: Only link directly if we have a real numeric report ID
            if source == 'BFRO' and raw_id.isdigit() and len(raw_id) >= 3:
                full_report_url = f"https://www.bfro.net/GDB/show_report.asp?id={raw_id}"
                link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:8px; padding:5px 10px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Read Full Report #{raw_id}</a>'
            elif state_abbr:
                # Fallback to state database search page if specific ID isn't linked
                search_url = f"https://www.bfro.net/GDB/state_listing.asp?state={state_abbr}"
                link_html = f'<a href="{search_url}" target="_blank" style="display:inline-block; margin-top:8px; padding:5px 10px; background-color:#6c757d; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">🔍 Browse {state_abbr} BFRO Records</a>'
            else:
                link_html = ''

            # Build popup container
            popup_content = f"""
            <div style="font-family: sans-serif; width: 230px;">
                <b style="color:#2c3e50; font-size:14px;">👣 {report.get('title', 'Sighting Report')}</b><br>
                <small style="color:#666;"><b>Date:</b> {report.get('event_date', 'N/A')} | <b>Class:</b> {report.get('class_rating', 'A/B')}</small><br>
                <p style="font-size: 12px; margin-top: 6px; margin-bottom: 6px; color:#333; line-height: 1.3;">{report.get('summary', 'No summary details provided.')}</p>
                {link_html}
            </div>
            """

            folium.Marker(
                [report["latitude"], report["longitude"]],
                popup=folium.Popup(popup_content, max_width=260),
                icon=folium.Icon(color="blue", icon="tree", prefix="fa")
            ).add_to(m)

    except Exception as e:
        st.warning(f"Could not load sightings from database: {e}")

# Map status banner and display
st.caption(f"Showing **{sightings_count} sightings** within ~{radius_miles} miles of target area.")
st_folium(m, width="100%", height=550, returned_objects=[])
