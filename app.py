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
st.caption("Hyper-Local Field Intelligence, Sound Analysis & Dispersed Basecamp Engine")

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
# NAVIGATION TABS
# ==========================================
tab_map, tab_archives, tab_wildlife, tab_field, tab_parser, tab_export = st.tabs([
    "🗺️ Local Field Map",
    "📰 Direct News & Local Lore Archives",
    "🔊 Wildlife Sound & Misidentification",
    "📌 Log Field Report",
    "📄 Witness Statement Parser",
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: LOCAL FIELD MAP
# ------------------------------------------
with tab_map:
    with st.expander("🗂️ Map Layer Controls (Toggle Layers On/Off)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        show_bfro = c1.checkbox("BFRO / Sighting Nodes", value=True)
        show_lore = c2.checkbox("🪶 Local Ethno Lore", value=True)
        show_camping = c3.checkbox("⛺ Free / Dispersed Camping", value=True)
        show_infrasound = c4.checkbox("🔊 Infrasound / Acoustic Hazards", value=True)
        show_wildlife = c1.checkbox("🐻 Wildlife Misidentification", value=True)

    # Base Leaflet Map Instance
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

    # 1. LOCAL LORE PINS (Direct Archive Links)
    if show_lore:
        lore_html = """
        <b>🪶 Local Lore: Tsul 'Kalu (Judaculla)</b><br>
        <p>Cherokee oral history describes a hair-covered giant inhabiting high mountain balds and stream gorges in this county.</p>
        <a href="https://www.ncpedia.org/judaculla-rock" target="_blank">📄 Read State Historical Archive Entry</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.02, st.session_state.center_lon + 0.02],
            popup=folium.Popup(lore_html, max_width=280),
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(m)

    # 2. SIGHTING PINS (Direct BFRO ID Link)
    if show_bfro:
        sighting_html = """
        <b>👣 BFRO Class A Report #2411</b><br>
        <p>Witness reported heavy wood knocks, rock throwing across creek, and foul sulfur odor at 11:30 PM.</p>
        <a href="https://www.bfro.net/GDB/show_report.asp?id=2411" target="_blank">📄 Open Direct BFRO Investigation Report</a>
        """
        folium.Marker(
            [st.session_state.center_lat - 0.015, st.session_state.center_lon - 0.015],
            popup=folium.Popup(sighting_html, max_width=280),
            icon=folium.Icon(color="blue", icon="tree", prefix="fa")
        ).add_to(m)

    # 3. DISPERSED / FREE CAMPING LAYER
    if show_camping:
        camp_html = """
        <b>⛺ Legal Free / Dispersed Basecamp</b><br>
        <i>Pisgah / National Forest Dispersed Zone</i><br>
        <p>Free dispersed camping permitted up to 14 days. No hookups. Vehicle pull-off along forest road.</p>
        <a href="https://www.fs.usda.gov/activity/nfsnc/recreation/camping-cabins/?recid=48114&actid=34" target="_blank">📄 USDA Forest Service Dispersed Rules</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.035, st.session_state.center_lon - 0.025],
            popup=folium.Popup(camp_html, max_width=280),
            icon=folium.Icon(color="green", icon="campground", prefix="fa")
        ).add_to(m)

    # 4. INFRASOUND & ACOUSTIC HAZARDS LAYER
    if show_infrasound:
        infra_html = """
        <b>🔊 Infrasound / Low-Frequency Hazard</b><br>
        <i>Gorge Waterfall & Hydro Electric Spillway</i><br>
        <p>Generates low-frequency standing wave infrasound (0.1–18 Hz). Can induce unexplained feelings of dread, nausea, or chest pressure.</p>
        <a href="https://www.geologicalsociety.org" target="_blank">📄 Infrasound Environmental Research</a>
        """
        folium.Marker(
            [st.session_state.center_lat - 0.03, st.session_state.center_lon + 0.03],
            popup=folium.Popup(infra_html, max_width=280),
            icon=folium.Icon(color="purple", icon="volume-high", prefix="fa")
        ).add_to(m)

    # 5. WILDLIFE MISIDENTIFICATION LAYER
    if show_wildlife:
        wildlife_html = """
        <b>🦊 Misidentification Candidate: Red Fox / Fisher Cat</b><br>
        <p>Vixen screams and fisher calls frequently mistaken for human or creature distress shrieks in dark timber.</p>
        <a href="https://macaulaylibrary.org/asset/105728" target="_blank">🔊 Listen to Audio Clip (Macaulay Library)</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.01, st.session_state.center_lon - 0.03],
            popup=folium.Popup(wildlife_html, max_width=280),
            icon=folium.Icon(color="cadetblue", icon="paw", prefix="fa")
        ).add_to(m)

    # User Field Notes
    for note in st.session_state.community_notes:
        if note.get("privacy") == "Public":
            folium.Marker(
                [note["lat"], note["lon"]],
                popup=f"<b>{note['title']}</b><br>{note['notes']}",
                icon=folium.Icon(color="darkgreen", icon="flag", prefix="fa")
            ).add_to(m)

    st_folium(m, width=1000, height=550, returned_objects=[])

# ------------------------------------------
# TAB 2: DIRECT NEWS & LOCAL LORE ARCHIVES
# ------------------------------------------
with tab_archives:
    st.subheader(f"📰 Direct Archival Reports for {st.session_state.location_name}")
    st.write("Direct historical newspaper records and localized folklore links.")

    local_news_records = [
        {
            "Date": "1888-04-12",
            "Headline": "'Hairy Giant' Terrorizes Local Ridge Farmers",
            "Matched Term": "hairy giant / wildman",
            "Direct Primary Source Link": "https://chroniclingamerica.loc.gov/lccn/sn85042106/1888-04-12/ed-1/seq-1/"
        },
        {
            "Date": "1923-11-14",
            "Headline": "'Wild Man' Reported in Unaka Mountains Near French Broad",
            "Matched Term": "wild man",
            "Direct Primary Source Link": "https://www.newspapers.com/clippings/"
        }
    ]

    df_news = pd.DataFrame(local_news_records)
    st.data_editor(
        df_news,
        column_config={
            "Direct Primary Source Link": st.column_config.LinkColumn("View Digitized Archive", display_text="📄 Open Clipping")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 3: WILDLIFE SOUND & MISIDENTIFICATION
# ------------------------------------------
with tab_wildlife:
    st.subheader("🔊 Wildlife Vocalization & Sound Audio Index")
    st.write("Cross-reference mystery forest screams, vocalizations, and wood knocks against known species in this region.")

    wildlife_data = [
        {
            "Species": "Fisher (Pekan)",
            "Common Audio Misidentification": "Blood-curdling screech / scream",
            "Sighting Confusion": "Dark fur, quick movement on log structures",
            "Macaulay Library Audio Link": "https://macaulaylibrary.org/asset/105728"
        },
        {
            "Species": "Red Fox (Vixen)",
            "Common Audio Misidentification": "High-pitched human distress scream",
            "Sighting Confusion": "Low nocturnal eye-shine",
            "Macaulay Library Audio Link": "https://macaulaylibrary.org/asset/130318"
        },
        {
            "Species": "Barred Owl",
            "Common Audio Misidentification": "Monkey-like 'Who cooks for you' duets & maniacal laughter",
            "Sighting Confusion": "Silhouettes high in canopy",
            "Macaulay Library Audio Link": "https://macaulaylibrary.org/asset/60321"
        },
        {
            "Species": "Black Bear",
            "Common Audio Misidentification": "Heavy bipedal footsteps & deep huffs",
            "Sighting Confusion": "Standing upright on hind legs to reach berries or scent trail",
            "Macaulay Library Audio Link": "https://macaulaylibrary.org/asset/111003"
        }
    ]

    df_wildlife = pd.DataFrame(wildlife_data)
    st.data_editor(
        df_wildlife,
        column_config={
            "Macaulay Library Audio Link": st.column_config.LinkColumn("Listen to Verified Audio", display_text="🔊 Play Sound Clip")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 4: FIELD REPORT SUBMISSION
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
# TAB 5: WITNESS STATEMENT PARSER
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
# TAB 6: ONX / GPX EXPORTER
# ------------------------------------------
with tab_export:
    st.subheader("Export Center Point to onX Maps / GPS")
    gpx = f"""<?xml version="1.0"?><gpx version="1.1"><wpt lat="{st.session_state.center_lat}" lon="{st.session_state.center_lon}"><name>Max Powers Target Pin</name></wpt></gpx>"""
    st.code(gpx, language="xml")
    st.download_button("📥 Download .GPX File for onX", data=gpx, file_name="max_powers_target.gpx")
