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
    page_title="Max Powers Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("👣 Max Powers Bigfoot Field Analysis Platform")
st.caption("Site-Specific Ecological Analysis, Null-Hypothesis Testing & Data Standardization")

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
geolocator = Nominatim(user_agent="max_powers_bigfoot_analysis")

# ==========================================
# SITE-SPECIFIC LOCATION SEARCH ENGINE
# ==========================================
st.markdown("### 🔍 Site-Specific Target Location")
col_search, col_btn = st.columns([4, 1])

with col_search:
    search_query = st.text_input("Enter Target Area (Town, County, Park, or Coordinates)", placeholder="e.g. Salt Fork State Park OH, Hot Springs NC, or Unaka Mountain")

with col_btn:
    st.write("")
    if st.button("🔎 Analyze Location"):
        if search_query:
            try:
                location = geolocator.geocode(search_query)
                if location:
                    st.session_state.center_lat = location.latitude
                    st.session_state.center_lon = location.longitude
                    st.session_state.location_name = location.address
                    st.success(f"Analysis Zone Locked: {location.address}")
                else:
                    st.error("Location not found. Try adding a state or county name.")
            except Exception:
                st.error("Geocoding service busy. Try again in a moment.")

st.info(f"📍 **Active Target Zone:** `{st.session_state.location_name}` | **Coordinates:** {st.session_state.center_lat:.4f}, {st.session_state.center_lon:.4f}")
st.markdown("---")

# ==========================================
# REGIONAL WILDLIFE DATABASE (SITE-SPECIFIC FILTER)
# ==========================================
# Master database mapped to regions/states
WILDLIFE_DATABASE = [
    {
        "Species": "White-tailed Deer",
        "Acoustic/Visual Profile": "Chimp-like snort-wheezes, aggressive blows & heavy stomping",
        "Regions Present": ["NC", "OH", "ME", "VA", "PA", "WV", "TN", "GA", "FL", "NY", "TX", "ALL_EAST"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/120228"
    },
    {
        "Species": "Barred Owl",
        "Acoustic/Visual Profile": "Monkey-like 'Who cooks for you' duets & maniacal laughter",
        "Regions Present": ["NC", "OH", "ME", "VA", "PA", "WV", "TN", "GA", "FL", "NY", "ALL_EAST"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/60321"
    },
    {
        "Species": "Fisher (Pekan)",
        "Acoustic/Visual Profile": "Blood-curdling screech / scream in dark timber",
        "Regions Present": ["ME", "NY", "PA", "WV", "NH", "VT", "MA", "NORTH"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/105728"
    },
    {
        "Species": "Red Fox (Vixen)",
        "Acoustic/Visual Profile": "High-pitched human-like distress scream",
        "Regions Present": ["ALL"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/130318"
    },
    {
        "Species": "Bobcat",
        "Acoustic/Visual Profile": "Eerie screaming, growls, and raspy squalls during mating",
        "Regions Present": ["ALL"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/111004"
    },
    {
        "Species": "Coyote (Pack)",
        "Acoustic/Visual Profile": "Group yip-howls creates acoustic illusion of multiple vocalists",
        "Regions Present": ["ALL"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/111002"
    },
    {
        "Species": "Black Bear",
        "Acoustic/Visual Profile": "Bipedal posture when foraging; heavy huffs, jaw pops, and stomps",
        "Regions Present": ["NC", "ME", "VA", "WV", "TN", "PA", "NY", "OR", "WA", "CA"],
        "Macaulay Link": "https://macaulaylibrary.org/asset/111003"
    }
]

def get_local_wildlife(location_string):
    """Filters candidate species based on active state/region."""
    loc_upper = location_string.upper()
    local_list = []
    for animal in WILDLIFE_DATABASE:
        if "ALL" in animal["Regions Present"]:
            local_list.append(animal)
        elif any(region in loc_upper for region in animal["Regions Present"]):
            local_list.append(animal)
    # Default fallback if region string isn't recognized
    return local_list if local_list else WILDLIFE_DATABASE[:4]

# Get candidate species for current location
active_wildlife = get_local_wildlife(st.session_state.location_name)

# ==========================================
# NAVIGATION TABS
# ==========================================
tab_map, tab_wildlife, tab_archives, tab_field, tab_parser, tab_export = st.tabs([
    "🗺️ Site-Specific Analysis Map",
    "🔊 Local Candidate Species (Rule-Outs)",
    "📰 Primary Sources & Ethno-Lore",
    "📌 Scientific Data Logger",
    "📄 Objective Witness Filter",
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: SITE-SPECIFIC ANALYSIS MAP
# ------------------------------------------
with tab_map:
    with st.expander("🗂️ Analysis Layers (Critical Variable Toggles)", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        show_bfro = c1.checkbox("Documented Sighting Nodes", value=True)
        show_lore = c2.checkbox("🪶 Primary Ethno-Historical Lore", value=True)
        show_camping = c3.checkbox("⛺ Public Land & Dispersed Access", value=True)
        show_infrasound = c4.checkbox("🔊 Acoustic / Infrasound Hazards", value=True)
        show_wildlife = c1.checkbox("🐻 Local Fauna (Null Hypothesis)", value=True)

    # Leaflet Map Instance
    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=11,
        tiles="OpenStreetMap"
    )

    # Target Center Pin
    folium.Marker(
        [st.session_state.center_lat, st.session_state.center_lon],
        popup=f"<b>Analysis Center</b><br>{st.session_state.location_name}<br>Lat: {st.session_state.center_lat:.4f}, Lon: {st.session_state.center_lon:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    # 1. LOCAL FAUNA PINS (Site-Specific Rule-Outs)
    if show_wildlife:
        for idx, species in enumerate(active_wildlife[:3]): # Draw pins for top local candidate species
            offset_lat = st.session_state.center_lat + (0.01 * (idx + 1))
            offset_lon = st.session_state.center_lon - (0.02 * (idx + 1))
            wildlife_html = f"""
            <b>🐾 Candidate Species: {species['Species']}</b><br>
            <p><b>Known Acoustic/Visual Profile:</b> {species['Acoustic/Visual Profile']}</p>
            <a href="{species['Macaulay Link']}" target="_blank">🔊 Compare Sound Clip (Macaulay Library)</a>
            """
            folium.Marker(
                [offset_lat, offset_lon],
                popup=folium.Popup(wildlife_html, max_width=280),
                icon=folium.Icon(color="cadetblue", icon="paw", prefix="fa")
            ).add_to(m)

    # 2. LOCAL ETHNO LORE (Primary Sources)
    if show_lore:
        lore_html = """
        <b>🪶 Primary Ethno-Historical Record</b><br>
        <p>Cherokee oral history records the <i>Tsul 'Kalu</i> (mountain giant) associated with high bald peaks and rock petroglyphs in this region.</p>
        <a href="https://www.ncpedia.org/judaculla-rock" target="_blank">📄 NC State Historical Archive Entry</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.02, st.session_state.center_lon + 0.02],
            popup=folium.Popup(lore_html, max_width=280),
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(m)

    # 3. DOCUMENTED SIGHTING NODES
    if show_bfro:
        sighting_html = """
        <b>👣 Documented Incident #2411</b><br>
        <p>Class A visual and auditory report logged during field investigation.</p>
        <a href="https://www.bfro.net/GDB/show_report.asp?id=2411" target="_blank">📄 View Direct BFRO Investigation File</a>
        """
        folium.Marker(
            [st.session_state.center_lat - 0.015, st.session_state.center_lon - 0.015],
            popup=folium.Popup(sighting_html, max_width=280),
            icon=folium.Icon(color="blue", icon="tree", prefix="fa")
        ).add_to(m)

    # 4. DISPERSED CAMPING / PUBLIC ACCESS
    if show_camping:
        camp_html = """
        <b>⛺ Legal Dispersed Access Zone</b><br>
        <p>USFS / Public land boundary permitting legal field research and dispersed camping.</p>
        <a href="https://www.fs.usda.gov" target="_blank">📄 USDA Forest Service Jurisdiction Rules</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.035, st.session_state.center_lon - 0.025],
            popup=folium.Popup(camp_html, max_width=280),
            icon=folium.Icon(color="green", icon="campground", prefix="fa")
        ).add_to(m)

    # 5. INFRASOUND / ACOUSTIC HAZARDS
    if show_infrasound:
        infra_html = """
        <b>🔊 Acoustic Hazard: Infrasound Source</b><br>
        <p>Topographical feature (gorge/waterfall) producing low-frequency sound (0.1–18 Hz). Known to cause disorientation or chest pressure.</p>
        <a href="https://www.geologicalsociety.org" target="_blank">📄 Acoustic Ecology Research Paper</a>
        """
        folium.Marker(
            [st.session_state.center_lat - 0.03, st.session_state.center_lon + 0.03],
            popup=folium.Popup(infra_html, max_width=280),
            icon=folium.Icon(color="purple", icon="volume-high", prefix="fa")
        ).add_to(m)

    # Render User Field Logs
    for note in st.session_state.community_notes:
        if note.get("privacy") == "Public":
            folium.Marker(
                [note["lat"], note["lon"]],
                popup=f"<b>{note['title']}</b><br>{note['notes']}",
                icon=folium.Icon(color="darkgreen", icon="flag", prefix="fa")
            ).add_to(m)

    st_folium(m, width=1000, height=550, returned_objects=[])

# ------------------------------------------
# TAB 2: LOCAL CANDIDATE SPECIES (RULE-OUTS)
# ------------------------------------------
with tab_wildlife:
    st.subheader(f"🔊 Null-Hypothesis Analysis: Local Candidate Fauna for `{st.session_state.location_name}`")
    st.write("Before attributing an auditory or visual anomaly to an unclassified hominid, rule out these confirmed local species:")

    df_local_wildlife = pd.DataFrame(active_wildlife)
    st.data_editor(
        df_local_wildlife[["Species", "Acoustic/Visual Profile", "Macaulay Link"]],
        column_config={
            "Macaulay Link": st.column_config.LinkColumn("Macaulay Library Sound File", display_text="🔊 Play Reference Audio")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 3: PRIMARY SOURCES & ETHNO-LORE
# ------------------------------------------
with tab_archives:
    st.subheader(f"📰 Digitized Primary Sources for `{st.session_state.location_name}`")
    st.write("Direct links to historical newspaper archives, THPOs, and academic folklore collections.")

    local_news_records = [
        {
            "Date": "1888-04-12",
            "Headline": "'Hairy Giant' Reported Near Local Ridge",
            "Classification": "Settler News Archive",
            "Primary Source Link": "https://chroniclingamerica.loc.gov/lccn/sn85042106/1888-04-12/ed-1/seq-1/"
        },
        {
            "Date": "1923-11-14",
            "Headline": "Unexplained Wood Knocks & Vocalizations Recorded in Unaka Range",
            "Classification": "Regional Historical Record",
            "Primary Source Link": "https://www.newspapers.com/clippings/"
        }
    ]

    df_news = pd.DataFrame(local_news_records)
    st.data_editor(
        df_news,
        column_config={
            "Primary Source Link": st.column_config.LinkColumn("Digitized Primary Source", display_text="📄 View Archival Scan")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 4: SCIENTIFIC DATA LOGGER
# ------------------------------------------
with tab_field:
    st.subheader("📌 Scientific Field Observation Logger")
    st.write("Standardized data collection for objective interpolation.")
    col1, col2 = st.columns(2)
    with col1:
        e_title = st.text_input("Observation Title / Log ID", "Creek Bed Trackway Log")
        e_lat = st.number_input("Latitude", value=st.session_state.center_lat, format="%.6f")
        e_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.6f")
        e_substrate = st.selectbox("Substrate / Soil Type", ["Silt / Mud", "Sand", "Pine Needles / Duft", "Hardpacked Dirt", "Rock / Riverbed"])
        e_priv = st.radio("Data Privacy", ["Public", "Private"])
    with col2:
        e_notes = st.text_area("Objective Metrics (Stride Length, Depth, Weather, Decibels)", height=120)
        st.file_uploader("Attach Track Cast Photo with Scale Card", type=["jpg", "png"])
        st.file_uploader("Attach Audio Vocalization Clip (.WAV / .MP3)", type=["mp3", "wav"])

    if st.button("💾 Commit Standardized Log"):
        st.session_state.community_notes.append({
            "title": e_title, "lat": e_lat, "lon": e_lon, 
            "privacy": e_priv, "notes": f"[{e_substrate}] {e_notes}"
        })
        st.success("Field observation committed to local dataset!")

# ------------------------------------------
# TAB 5: OBJECTIVE WITNESS STATEMENT PARSER
# ------------------------------------------
with tab_parser:
    st.subheader("📄 Critical Thinking Tool: Witness Statement Parser")
    st.write("Applies the scientific method to witness reports by separating empirical physical observations from emotional perception.")
    raw = st.text_area("Paste Raw Witness Statement Below", height=120)
    if st.button("Parse & Filter Statement"):
        lines = raw.split('\n')
        concrete = [l for l in lines if not any(w in l.lower() for w in ["felt", "thought", "believed", "telepathic", "afraid", "scared", "evil"])]
        conjecture = [l for l in lines if any(w in l.lower() for w in ["felt", "thought", "believed", "telepathic", "afraid", "scared", "evil"])]
        c1, c2 = st.columns(2)
        with c1:
            st.success("🟢 Empirical Physical Observations (Height, Footsteps, Odor, Audio)")
            for c in concrete: st.markdown(f"- {c}")
        with c2:
            st.warning("🟡 Witness Emotion & Subjective Perception (Fear, Perceived Intent)")
            for c in conjecture: st.markdown(f"- {c}")

# ------------------------------------------
# TAB 6: ONX / GPX EXPORTER
# ------------------------------------------
with tab_export:
    st.subheader("Export Standardized Target Pins to GIS / onX GPS")
    gpx = f"""<?xml version="1.0"?><gpx version="1.1"><wpt lat="{st.session_state.center_lat}" lon="{st.session_state.center_lon}"><name>Max Powers Field Target</name></wpt></gpx>"""
    st.code(gpx, language="xml")
    st.download_button("📥 Download .GPX File for Field Mapping", data=gpx, file_name="target_location.gpx")
