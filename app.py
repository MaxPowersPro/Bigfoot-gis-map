import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

# ==========================================
# PAGE SETUP & STYLING
# ==========================================
st.set_page_config(
    page_title="Cryptid GIS Field Engine",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="collapsed" # Starts collapsed for maximum map space
)

st.title("🌲 Cryptid GIS Field Platform")

# Initialize Session State
if "center_lat" not in st.session_state:
    st.session_state.center_lat = 35.944444
if "center_lon" not in st.session_state:
    st.session_state.center_lon = -82.772333
if "community_notes" not in st.session_state:
    st.session_state.community_notes = []

# Initialize Search Engine
geolocator = Nominatim(user_agent="cryptid_gis_app")

# ==========================================
# HIGH-SPEED LOCATION SEARCH BAR
# ==========================================
st.markdown("### 🔍 Find Any Location, Route, or Town")
col_search, col_btn = st.columns([4, 1])

with col_search:
    search_query = st.text_input("Search Place, Town, Highway, or Park", placeholder="e.g. Hot Springs NC, Route 25, or Unaka Mountain")

with col_btn:
    st.write("") # Alignment spacer
    if st.button("🔎 Search Map"):
        if search_query:
            try:
                location = geolocator.geocode(search_query)
                if location:
                    st.session_state.center_lat = location.latitude
                    st.session_state.center_lon = location.longitude
                    st.success(f"Found: {location.address}")
                else:
                    st.error("Location not found. Try adding a state or county name.")
            except Exception as e:
                st.error("Search service busy. Try again in a moment.")

st.markdown("---")

# ==========================================
# MAIN INTERFACE TABS
# ==========================================
tab_map, tab_field, tab_archives, tab_parser, tab_export = st.tabs([
    "🗺️ Interactive High-Detail Map",
    "📌 Submit Field Report & Media",
    "📰 Newspaper Archives & Toponyms",
    "📄 Witness Report Data Filter",
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: INTERACTIVE HIGH-DETAIL MAP
# ------------------------------------------
with tab_map:
    # Sidebar Layer Toggles
    with st.expander("🗂️ Map Layer Controls (Click to expand/collapse)", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        show_bfro = c1.checkbox("BFRO Sightings", value=True)
        show_bfm = c2.checkbox("Bigfoot Mapping Project", value=True)
        show_lore = c3.checkbox("🪶 Native American Lore", value=True)
        show_toponyms = c4.checkbox("USGS Ominous Toponyms", value=True)

    # Initialize Folium Map centered on searched location
    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=11, # Clear detail zoom level for town names & routes
        tiles=None # Custom tile handling below
    )

    # High-Detail Map Tile Options (Clear Routes & Towns)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Detailed Street & Route Map (Best for Road Numbers)",
        overlay=False,
        control=True
    ).add_to(m)

    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topographic & Terrain Map",
        overlay=False,
        control=True
    ).add_to(m)

    # Layer Control Button on Top-Right of Map
    folium.LayerControl(position="topright").add_to(m)

    # Target Crosshair Pin
    folium.Marker(
        [st.session_state.center_lat, st.session_state.center_lon],
        popup=f"Target Search Center: {st.session_state.center_lat:.4f}, {st.session_state.center_lon:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    # NATIVE AMERICAN LORE PINS (Directly on Map)
    if show_lore:
        lore_group = folium.FeatureGroup(name="Native American Lore").add_to(m)
        folium.Marker(
            [35.9500, -82.8000],
            popup="<b>🪶 Cherokee Tradition: Tsul 'Kalu (Judaculla)</b><br>Slant-eyed mountain giant associated with high bald peaks and petroglyphs.",
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(lore_group)
        folium.Marker(
            [35.8800, -82.7500],
            popup="<b>🪶 Cherokee Tradition: Nunne'hi</b><br>Invisible spirit race dwelling in subterranean caverns along river valleys.",
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(lore_group)

    # BFRO Sightings
    if show_bfro:
        bfro_group = folium.FeatureGroup(name="BFRO Sightings").add_to(m)
        folium.Marker(
            [35.9844, -82.8023],
            popup="<b>BFRO Class A</b><br>Wood knocks & rock throwing along creek.",
            icon=folium.Icon(color="blue", icon="tree", prefix="fa")
        ).add_to(bfro_group)

    # Bigfoot Mapping Project
    if show_bfm:
        bfm_group = folium.FeatureGroup(name="Bigfoot Mapping Project").add_to(m)
        folium.Marker(
            [35.9244, -82.7223],
            popup="<b>BFM Sightings Node</b><br>Visual encounter near ridge trail.",
            icon=folium.Icon(color="green", icon="eye", prefix="fa")
        ).add_to(bfm_group)

    # USGS Toponyms
    if show_toponyms:
        toponym_group = folium.FeatureGroup(name="USGS Toponyms").add_to(m)
        folium.Marker(
            [35.9100, -82.8300],
            popup="<b>USGS Feature: Wildman Branch</b><br>Historic 19th century creature reference.",
            icon=folium.Icon(color="purple", icon="map-pin", prefix="fa")
        ).add_to(toponym_group)

    # User Field Notes
    for note in st.session_state.community_notes:
        if note.get("privacy") == "Public":
            folium.Marker(
                [note["lat"], note["lon"]],
                popup=f"<b>{note['title']}</b><br>{note['notes']}",
                icon=folium.Icon(color="darkgreen", icon="flag", prefix="fa")
            ).add_to(m)

    # Render Map
    st_folium(m, width=1100, height=650)

# ------------------------------------------
# TAB 2: FIELD REPORT SUBMISSION
# ------------------------------------------
with tab_field:
    st.subheader("📌 Log Field Observation")
    col1, col2 = st.columns(2)
    with col1:
        e_title = st.text_input("Observation Title", "Creek Bed Log")
        e_lat = st.number_input("Latitude", value=st.session_state.center_lat, format="%.6f")
        e_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.6f")
        e_priv = st.radio("Privacy Setting", ["Public", "Private"])
    with col2:
        e_notes = st.text_area("Field Description & Environmental Notes", height=120)
        st.file_uploader("Attach Photo / Cast Picture", type=["jpg", "png"])
        st.file_uploader("Attach Audio Recording", type=["mp3", "wav"])

    if st.button("💾 Save Observation Pin"):
        st.session_state.community_notes.append({
            "title": e_title, "lat": e_lat, "lon": e_lon, 
            "privacy": e_priv, "notes": e_notes
        })
        st.success("Field report saved to map!")

# ------------------------------------------
# TAB 3: NEWSPAPER ARCHIVES & TOPONYMS
# ------------------------------------------
with tab_archives:
    st.subheader("📰 Local Historical News Archives & Toponyms")
    st.markdown("**Search Keywords Included:** `wild man`, `wildman`, `hairy giant`, `ape man`")
    news_records = [
        {"Date": "1888-04-12", "Publication": "WNC Democrat", "Headline": "'Hairy Giant' Terrorizes Local Ridge Farmers", "Matched Keyword": "hairy giant"},
        {"Date": "1923-11-14", "Publication": "Asheville Citizen-Times", "Headline": "'Wild Man' Reported in Unaka Mountains", "Matched Keyword": "wild man"},
    ]
    st.dataframe(pd.DataFrame(news_records), use_container_width=True)

# ------------------------------------------
# TAB 4: WITNESS REPORT DATA FILTER
# ------------------------------------------
with tab_parser:
    st.subheader("Witness Report Objective Data Extractor")
    raw = st.text_area("Paste Raw Witness Statement", height=120)
    if st.button("Parse Report"):
        lines = raw.split('\n')
        concrete = [l for l in lines if not any(w in l.lower() for w in ["felt", "thought", "believed", "telepathic", "afraid"])]
        conjecture = [l for l in lines if any(w in l.lower() for w in ["felt", "thought", "believed", "telepathic", "afraid"])]
        c1, c2 = st.columns(2)
        with c1:
            st.success("🟢 Concrete Observations")
            for c in concrete: st.markdown(f"- {c}")
        with c2:
            st.warning("🟡 Witness Conjecture")
            for c in *conjecture: st.markdown(f"- {c}")

# ------------------------------------------
# TAB 5: ONX / GPX EXPORTER
# ------------------------------------------
with tab_export:
    st.subheader("Export Center Point to onX Maps / Field GPS")
    gpx = f"""<?xml version="1.0"?><gpx version="1.1"><wpt lat="{st.session_state.center_lat}" lon="{st.session_state.center_lon}"><name>Target Center</name></wpt></gpx>"""
    st.code(gpx, language="xml")
    st.download_button("📥 Download .GPX File for onX", data=gpx, file_name="target_location.gpx")
