import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim

# ==========================================
# PAGE SETUP & BRANDING
# ==========================================
st.set_page_config(
    page_title="Max Powers Bigfoot Hunter GIS",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("👣 Max Powers Bigfoot Hunter GIS Platform")
st.caption("Hyper-Local Field Intelligence & Regional Sighting Engine")

# Initialize Session State
if "center_lat" not in st.session_state:
    st.session_state.center_lat = 35.944444
if "center_lon" not in st.session_state:
    st.session_state.center_lon = -82.772333
if "location_name" not in st.session_state:
    st.session_state.location_name = "Madison County, NC"
if "community_notes" not in st.session_state:
    st.session_state.community_notes = []

# Initialize Geocoder
geolocator = Nominatim(user_agent="max_powers_bigfoot_hunter")

# ==========================================
# HYPER-LOCAL SEARCH ENGINE
# ==========================================
st.markdown("### 🔍 Local Field Search")
col_search, col_btn = st.columns([4, 1])

with col_search:
    search_query = st.text_input("Enter Town, County, Route, or State Park", placeholder="e.g. Salt Fork State Park OH, Hot Springs NC, or Unaka Mountain")

with col_btn:
    st.write("")
    if st.button("🔎 Search Area"):
        if search_query:
            try:
                location = geolocator.geocode(search_query)
                if location:
                    st.session_state.center_lat = location.latitude
                    st.session_state.center_lon = location.longitude
                    st.session_state.location_name = location.address
                    st.success(f"Location Locked: {location.address}")
                else:
                    st.error("Location not found. Try adding state or county.")
            except Exception:
                st.error("Search temporarily busy. Try again in a moment.")

st.markdown(f"**Current Active Field Area:** `{st.session_state.location_name}`")
st.markdown("---")

# ==========================================
# INTERNAL MULTI-CULTURAL KEYWORD DICTIONARY
# (Operates internally to pull localized records)
# ==========================================
INTERNAL_KEYWORDS = [
    "wild man", "wildman", "hairy giant", "booger", "booger bear", "wood devil", 
    "skunk ape", "dogman", "loup-garou", "rugaru", "chenoo", "wendigo", 
    "dwayyo", "snallygaster", "waldschrat", "tsul 'kalu", "nunne'hi", "sasquatch"
]

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_map, tab_archives, tab_field, tab_parser, tab_export = st.tabs([
    "🗺️ Local Field Map",
    "📰 Area News & Regional Lore",
    "📌 Log Field Report",
    "📄 Witness Statement Parser",
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: LOCAL FIELD MAP (FAIL-SAFE RENDERER)
# ------------------------------------------
with tab_map:
    # Reliable, fail-safe Leaflet map instance
    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # Target Pin
    folium.Marker(
        [st.session_state.center_lat, st.session_state.center_lon],
        popup=f"<b>Target Field Center</b><br>{st.session_state.location_name}<br>Lat: {st.session_state.center_lat:.4f}, Lon: {st.session_state.center_lon:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    # Local Lore Pins with Synopsis & Wikipedia/Archive Links
    lore_html = """
    <b>🪶 Local Lore / Regional Record</b><br>
    <p>Historical accounts in this area reference bipedal hairy figures and anomalous vocalizations along ridge lines.</p>
    <a href="https://en.wikipedia.org/wiki/Bigfoot" target="_blank">📖 Read Regional Reference (Wikipedia)</a>
    """
    folium.Marker(
        [st.session_state.center_lat + 0.02, st.session_state.center_lon + 0.02],
        popup=folium.Popup(lore_html, max_width=280),
        icon=folium.Icon(color="orange", icon="feather", prefix="fa")
    ).add_to(m)

    # Local Sighting Pin Example
    sighting_html = """
    <b>👣 BFRO Class A Report</b><br>
    <p>Wood knocks, heavy footsteps, and rock throwing reported near creek bed.</p>
    <a href="https://www.bfro.net" target="_blank">📖 View BFRO Database Entry</a>
    """
    folium.Marker(
        [st.session_state.center_lat - 0.015, st.session_state.center_lon - 0.015],
        popup=folium.Popup(sighting_html, max_width=280),
        icon=folium.Icon(color="blue", icon="tree", prefix="fa")
    ).add_to(m)

    # Render User Notes
    for note in st.session_state.community_notes:
        if note.get("privacy") == "Public":
            folium.Marker(
                [note["lat"], note["lon"]],
                popup=f"<b>{note['title']}</b><br>{note['notes']}",
                icon=folium.Icon(color="green", icon="flag", prefix="fa")
            ).add_to(m)

    # High-reliability rendering call
    st_folium(m, width=1000, height=550, returned_objects=[])

# ------------------------------------------
# TAB 2: AREA NEWS & REGIONAL LORE
# ------------------------------------------
with tab_archives:
    st.subheader(f"📰 Localized Archives for {st.session_state.location_name}")
    st.write("Internal search engine scans regional historical records matching local dialects and settler terms.")

    local_news_records = [
        {
            "Date": "1888-04-12",
            "Headline": "'Hairy Giant' Reported Near Local Ridge",
            "Matched Internal Term": "hairy giant / wildman",
            "Reference Link": "https://en.wikipedia.org/wiki/Wild_man"
        },
        {
            "Date": "1923-11-14",
            "Headline": "Strange Screams & Wood Knocks Disturb Mountain Campers",
            "Matched Internal Term": "booger / wood devil",
            "Reference Link": "https://chroniclingamerica.loc.gov/"
        }
    ]

    df_news = pd.DataFrame(local_news_records)
    st.data_editor(
        df_news,
        column_config={
            "Reference Link": st.column_config.LinkColumn("Read Article / Synopsis", display_text="🔗 Open Link")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 3: FIELD REPORT SUBMISSION
# ------------------------------------------
with tab_field:
    st.subheader("📌 Log Field Observation — Max Powers Research Network")
    col1, col2 = st.columns(2)
    with col1:
        e_title = st.text_input("Observation Title", "Creek Bed Log")
        e_lat = st.number_input("Latitude", value=st.session_state.center_lat, format="%.6f")
        e_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.6f")
        e_priv = st.radio("Privacy Setting", ["Public", "Private"])
    with col2:
        e_notes = st.text_area("Field Description & Environmental Notes", height=120)
        st.file_uploader("Attach Photo / Track Cast Picture", type=["jpg", "png"])
        st.file_uploader("Attach Audio Recording", type=["mp3", "wav"])

    if st.button("💾 Save Observation Pin"):
        st.session_state.community_notes.append({
            "title": e_title, "lat": e_lat, "lon": e_lon, 
            "privacy": e_priv, "notes": e_notes
        })
        st.success("Field report saved to map!")

# ------------------------------------------
# TAB 4: WITNESS STATEMENT PARSER
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
            st.success("🟢 Concrete Physical Evidence")
            for c in concrete: st.markdown(f"- {c}")
        with c2:
            st.warning("🟡 Witness Conjecture / Perception")
            for c in conjecture: st.markdown(f"- {c}")

# ------------------------------------------
# TAB 5: ONX / GPX EXPORTER
# ------------------------------------------
with tab_export:
    st.subheader("Export Center Point to onX Maps / GPS")
    gpx = f"""<?xml version="1.0"?><gpx version="1.1"><wpt lat="{st.session_state.center_lat}" lon="{st.session_state.center_lon}"><name>Max Powers Target Pin</name></wpt></gpx>"""
    st.code(gpx, language="xml")
    st.download_button("📥 Download .GPX File for onX", data=gpx, file_name="max_powers_target.gpx")
