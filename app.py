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

# Custom Header Branding
st.title("👣 Max Powers Bigfoot Hunter GIS Platform")
st.caption("Field Intelligence, Ethno-Historical Lore, & Archival Sighting Engine")

# Initialize Session State
if "center_lat" not in st.session_state:
    st.session_state.center_lat = 35.944444
if "center_lon" not in st.session_state:
    st.session_state.center_lon = -82.772333
if "community_notes" not in st.session_state:
    st.session_state.community_notes = []

# Initialize Geocoder
geolocator = Nominatim(user_agent="max_powers_bigfoot_hunter")

# ==========================================
# LOCATION SEARCH ENGINE
# ==========================================
st.markdown("### 🔍 Search Location, Route, or Mountain Peak")
col_search, col_btn = st.columns([4, 1])

with col_search:
    search_query = st.text_input("Location Search", placeholder="e.g. Hot Springs NC, Route 25, Unaka Mountain, or Presque Isle ME")

with col_btn:
    st.write("")
    if st.button("🔎 Center Map"):
        if search_query:
            try:
                location = geolocator.geocode(search_query)
                if location:
                    st.session_state.center_lat = location.latitude
                    st.session_state.center_lon = location.longitude
                    st.success(f"Centered: {location.address}")
                else:
                    st.error("Location not found. Try including state or county.")
            except Exception:
                st.error("Search temporarily busy. Try again in a moment.")

st.markdown("---")

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_map, tab_archives, tab_field, tab_parser, tab_export = st.tabs([
    "🗺️ Interactive Field Map",
    "📰 Historical Archives & Cultural Lore",
    "📌 Submit Field Log & Media",
    "📄 Witness Statement Parser",
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: INTERACTIVE FIELD MAP
# ------------------------------------------
with tab_map:
    with st.expander("🗂️ Map Layer Controls", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        show_bfro = c1.checkbox("BFRO Sightings", value=True)
        show_bfm = c2.checkbox("Bigfoot Mapping Project", value=True)
        show_lore = c3.checkbox("🪶 Native & European Lore", value=True)
        show_toponyms = c4.checkbox("USGS Historic Toponyms", value=True)

    # Reliable High-Detail Map Instance
    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=10,
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
    )

    # Layer Control Button
    folium.LayerControl(position="topright").add_to(m)

    # Target Pin
    folium.Marker(
        [st.session_state.center_lat, st.session_state.center_lon],
        popup=f"<b>Target Center</b><br>Lat: {st.session_state.center_lat:.4f}<br>Lon: {st.session_state.center_lon:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    # CULTURAL & INDIGENOUS LORE PINS (HTML Popups with Links)
    if show_lore:
        lore_group = folium.FeatureGroup(name="Indigenous & Regional Lore").add_to(m)
        
        # Cherokee Tsul 'Kalu
        cherokee_html = """
        <b>🪶 Cherokee Tradition: Tsul 'Kalu (Judaculla)</b><br>
        <i>Mountain Slant-Eyed Giant</i><br>
        <p>A massive hair-covered entity associated with high bald peaks and rock petroglyphs in WNC.</p>
        <a href="https://www.ncpedia.org/judaculla-rock" target="_blank">📖 Read Full Historical Record</a>
        """
        folium.Marker(
            [35.9500, -82.8000],
            popup=folium.Popup(cherokee_html, max_width=300),
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(lore_group)

        # French-Canadian / Algonquin Rugaru & Chenoo
        french_html = """
        <b>⚜️ French-Canadian & Algonquin Lore: Rugaru / Chenoo</b><br>
        <i>Northwoods Giant & Cannibal Beast</i><br>
        <p>Documented by 17th-century French fur trappers in Maine, Quebec, and upstate NY as hairy forest giants.</p>
        <a href="https://www.native-languages.org/chenoo.htm" target="_blank">📖 Read Full Trapper Lore</a>
        """
        folium.Marker(
            [45.1000, -69.2000],
            popup=folium.Popup(french_html, max_width=300),
            icon=folium.Icon(color="purple", icon="book", prefix="fa")
        ).add_to(lore_group)

    # BFRO Sightings
    if show_bfro:
        bfro_group = folium.FeatureGroup(name="BFRO Sightings").add_to(m)
        folium.Marker(
            [35.9844, -82.8023],
            popup="<b>BFRO Class A Encounter</b><br>Heavy vocalizations & wood knocks along ridge.",
            icon=folium.Icon(color="blue", icon="tree", prefix="fa")
        ).add_to(bfro_group)

    # Bigfoot Mapping Project
    if show_bfm:
        bfm_group = folium.FeatureGroup(name="Bigfoot Mapping Project").add_to(m)
        folium.Marker(
            [35.9244, -82.7223],
            popup="<b>BFM Sighting Node</b><br>Bipedal visual encounter near forest trail.",
            icon=folium.Icon(color="green", icon="eye", prefix="fa")
        ).add_to(bfm_group)

    # USGS Toponyms
    if show_toponyms:
        toponym_group = folium.FeatureGroup(name="USGS Toponyms").add_to(m)
        folium.Marker(
            [35.9100, -82.8300],
            popup="<b>USGS Feature: Wildman Branch</b><br>Named during 19th-century settler survey.",
            icon=folium.Icon(color="darkpurple", icon="map-pin", prefix="fa")
        ).add_to(toponym_group)

    # Render User Notes
    for note in st.session_state.community_notes:
        if note.get("privacy") == "Public":
            folium.Marker(
                [note["lat"], note["lon"]],
                popup=f"<b>{note['title']}</b><br>{note['notes']}",
                icon=folium.Icon(color="darkgreen", icon="flag", prefix="fa")
            ).add_to(m)

    # Render Map to Screen
    st_folium(m, width=1100, height=600)

# ------------------------------------------
# TAB 2: HISTORICAL ARCHIVES & MULTI-CULTURAL LORE
# ------------------------------------------
with tab_archives:
    st.subheader("📰 Historical News Archives & Multi-Cultural Creature Index")
    st.write("Cross-referenced historical news archives and multi-language regional creature terms.")

    st.markdown("#### 🔍 Active Cultural & Multi-Language Search Keywords:")
    st.info("""
    * **English & Settler:** `wild man`, `wildman`, `hairy giant`, `booger`, `booger bear`, `wood devil`, `skunk ape`, `dogman`, `beast of bray road`
    * **French-Canadian & Algonquin:** `loup-garou`, `rugaru`, `chenoo`, `wendigo`, `matshishkapeu`
    * **Spanish & Southwest:** `el cuero`, `chupacabra`, `la llorona`
    * **German & Dutch:** `dwayyo`, `snallygaster`, `waldschrat`, `boschduivel`
    * **Native American Traditions:** `tsul 'kalu`, `nunne'hi`, `sasquatch`, `saskets`, `skookum`
    """)

    news_data = [
        {
            "Date": "1888-04-12",
            "Publication": "Western WNC Democrat",
            "Headline": "'Hairy Giant' Terrorizes Local Ridge Farmers",
            "Region": "Appalachia",
            "Article Link": "https://chroniclingamerica.loc.gov/"
        },
        {
            "Date": "1904-09-22",
            "Publication": "The Bangor Daily Gazette (ME)",
            "Headline": "French Trappers Report 'Chenoo' Wildman in Deep Timber",
            "Region": "Northeast / Quebec Border",
            "Article Link": "https://chroniclingamerica.loc.gov/"
        },
        {
            "Date": "1923-11-14",
            "Publication": "Asheville Citizen-Times",
            "Headline": "'Wild Man' Reported in Unaka Mountains",
            "Region": "Appalachia",
            "Article Link": "https://chroniclingamerica.loc.gov/"
        }
    ]

    df_news = pd.DataFrame(news_data)
    # Render table with active clickable links
    st.data_editor(
        df_news,
        column_config={
            "Article Link": st.column_config.LinkColumn("Read Full Newspaper Archive", display_text="🔗 View Archive")
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
        e_title = st.text_input("Observation Title", "Creek Bed Footprint Log")
        e_lat = st.number_input("Latitude", value=st.session_state.center_lat, format="%.6f")
        e_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.6f")
        e_priv = st.radio("Privacy Setting", ["Public", "Private"])
    with col2:
        e_notes = st.text_area("Field Description & Environmental Notes", height=120)
        st.file_uploader("Attach Photo / Track Cast Picture", type=["jpg", "png"])
        st.file_uploader("Attach Audio Vocalization Clip", type=["mp3", "wav"])

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
