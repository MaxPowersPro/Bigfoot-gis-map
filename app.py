import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import urllib.parse
from supabase import create_client, Client

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="Bigfoot & Historical Archive Map",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("👣 Bigfoot Sightings, Native Lore & Historical Newspapers")

# ==========================================
# 2. SUPABASE DATABASE CONNECTION
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

# Default Location State (Madison County, NC)
if "user_lat" not in st.session_state:
    st.session_state.user_lat = 35.944444
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -82.772333
if "location_name" not in st.session_state:
    st.session_state.location_name = "Madison County, NC"

geolocator = Nominatim(user_agent="bigfoot_multi_layer_locator")

# Helper for Library of Congress search URLs
def get_loc_archive_url(query, location=""):
    full_query = f"{query} {location}".strip()
    encoded = urllib.parse.quote(full_query)
    return f"https://chroniclingamerica.loc.gov/search/pages/results/?searchType=basic&terms={encoded}"

# ==========================================
# 3. SEARCH CONTROLS & LAYER TOGGLES
# ==========================================
col_input, col_radius, col_btn = st.columns([3, 1, 1])

with col_input:
    loc_search = st.text_input("📍 Enter Target Location", value=st.session_state.location_name)

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
                st.error("Geocoding service timed out.")

lat = st.session_state.user_lat
lon = st.session_state.user_lon
loc_name = st.session_state.location_name

# Layer Checkboxes
st.markdown("**Map Layers:**")
c1, c2, c3 = st.columns(3)
show_bfro = c1.checkbox("👣 BFRO Sightings (Blue)", value=True)
show_lore = c2.checkbox("🪶 Native American Lore (Orange)", value=True)
show_news = c3.checkbox("📰 Historical Newspaper Articles (Green)", value=True)

# ==========================================
# 4. MAP ENGINE WITH MULTI-ICON LAYERS
# ==========================================
m = folium.Map(location=[lat, lon], zoom_start=9, tiles="OpenStreetMap")

# Red Pin: Active Search Center
folium.Marker(
    [lat, lon],
    popup=f"<b>Target Center</b><br>{loc_name}",
    icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
).add_to(m)

# ------------------------------------------
# LAYER 1: BFRO SIGHTINGS (Blue Tree Pins)
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
                link_html = f'<a href="{full_report_url}" target="_blank" style="display:inline-block; margin-top:6px; padding:4px 8px; background-color:#007bff; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📄 Read Full Report #{raw_id}</a>'
            else:
                link_html = ''

            popup_content = f"""
            <div style="font-family: sans-serif; width: 220px;">
                <b style="color:#2c3e50;">👣 {report.get('title', 'Sighting Report')}</b><br>
                <small><b>Date:</b> {report.get('event_date', 'N/A')}</small><br>
                <p style="font-size: 11px; margin-top: 4px;">{report.get('summary', 'No summary details.')}</p>
                {link_html}
            </div>
            """

            folium.Marker(
                [report["latitude"], report["longitude"]],
                popup=folium.Popup(popup_content, max_width=250),
                icon=folium.Icon(color="blue", icon="tree", prefix="fa")
            ).add_to(m)
    except Exception as e:
        st.warning(f"Sighting query issue: {e}")

# ------------------------------------------
# LAYER 2: NATIVE AMERICAN LORE (Orange Feather Pins)
# ------------------------------------------
if show_lore:
    lore_lat = lat + 0.02
    lore_lon = lon + 0.02
    lore_popup = f"""
    <div style="font-family: sans-serif; width: 230px;">
        <b style="color:#d35400;">🪶 Native American Oral History</b><br>
        <small><b>Region:</b> {loc_name}</small>
        <p style="font-size: 11px; margin-top: 6px;">
        Indigenous accounts (such as Cherokees' <i>Tsul 'Kalu / Judaculla</i>) describe hair-covered mountain spirits and guardians of high ridges.
        </p>
        <a href="https://www.ncpedia.org/judaculla-rock" target="_blank" style="display:inline-block; padding:4px 8px; background-color:#e67e22; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">🪶 Explore Historical Record</a>
    </div>
    """
    folium.Marker(
        [lore_lat, lore_lon],
        popup=folium.Popup(lore_popup, max_width=260),
        icon=folium.Icon(color="orange", icon="feather", prefix="fa")
    ).add_to(m)

# ------------------------------------------
# LAYER 3: NEWSPAPER / MEDIA ARCHIVES (Green Newspaper Pins)
# ------------------------------------------
if show_news:
    news_lat = lat - 0.02
    news_lon = lon - 0.02
    news_url = get_loc_archive_url("Hairy Giant Wild Man", loc_name)
    news_popup = f"""
    <div style="font-family: sans-serif; width: 230px;">
        <b style="color:#27ae60;">📰 19th-Century Newspaper Archive</b><br>
        <small><b>Archive:</b> Library of Congress (Chronicling America)</small>
        <p style="font-size: 11px; margin-top: 6px;">
        Searches digitized newspapers (1800s–1950s) for "Wild Man" or "Hairy Giant" reports near <b>{loc_name}</b>.
        </p>
        <a href="{news_url}" target="_blank" style="display:inline-block; padding:4px 8px; background-color:#27ae60; color:white; border-radius:4px; text-decoration:none; font-size:11px; font-weight:bold;">📰 View Newspaper Scans</a>
    </div>
    """
    folium.Marker(
        [news_lat, news_lon],
        popup=folium.Popup(news_popup, max_width=260),
        icon=folium.Icon(color="green", icon="newspaper", prefix="fa")
    ).add_to(m)

# Status & Map Render
st.caption(f"Loaded **{sightings_count} BFRO sightings** within ~{radius_miles} miles of target.")
st_folium(m, width="100%", height=550, returned_objects=[])
