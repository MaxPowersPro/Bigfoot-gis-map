import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
import urllib.parse
from supabase import create_client, Client

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

# ==========================================
# SUPABASE DATABASE CONNECTION
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.warning("⚠️ Database connection offline. Running in local session mode.")
        return None

supabase: Client = init_supabase()

# Initialize Session State
if "center_lat" not in st.session_state:
    st.session_state.center_lat = 35.944444
if "center_lon" not in st.session_state:
    st.session_state.center_lon = -82.772333
if "location_name" not in st.session_state:
    st.session_state.location_name = "Madison County, NC"

# Initialize Geocoder
geolocator = Nominatim(user_agent="max_powers_bigfoot_analysis")

# Helper URLs
def get_macaulay_url(query):
    encoded = urllib.parse.quote(query)
    return f"https://search.macaulaylibrary.org/catalog?q={encoded}&mediaType=audio"

def get_loc_archive_url(query, state=""):
    full_query = f"{query} {state}".strip()
    encoded = urllib.parse.quote(full_query)
    return f"https://chroniclingamerica.loc.gov/search/pages/results/?searchType=basic&terms={encoded}"

# ==========================================
# TARGET LOCATION SEARCH ENGINE
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
# DYNAMIC REGIONAL WILDLIFE DATABASE
# ==========================================
WILDLIFE_DATABASE = [
    {
        "Species": "White-tailed Deer",
        "Acoustic/Visual Profile": "Chimp-like snort-wheezes, aggressive blows & heavy nocturnal stomping in brush",
        "Regions Present": ["NC", "OH", "ME", "VA", "PA", "WV", "TN", "GA", "FL", "NY", "TX", "ALL_EAST"],
        "Macaulay Link": get_macaulay_url("White-tailed Deer snort wheeze")
    },
    {
        "Species": "Barred Owl",
        "Acoustic/Visual Profile": "Monkey-like 'Who cooks for you' duets & maniacal nocturnal laughter/screams",
        "Regions Present": ["NC", "OH", "ME", "VA", "PA", "WV", "TN", "GA", "FL", "NY", "ALL_EAST"],
        "Macaulay Link": get_macaulay_url("Barred Owl duet call")
    },
    {
        "Species": "Fisher (Pekan)",
        "Acoustic/Visual Profile": "Blood-curdling screech / scream in dark timber, often confused for human distress",
        "Regions Present": ["ME", "NY", "PA", "WV", "NH", "VT", "MA", "NORTH"],
        "Macaulay Link": get_macaulay_url("Pekania pennanti scream")
    },
    {
        "Species": "Red Fox (Vixen)",
        "Acoustic/Visual Profile": "High-pitched human-like distress scream echoing across ravines",
        "Regions Present": ["ALL"],
        "Macaulay Link": get_macaulay_url("Vulpes vulpes vixen scream")
    },
    {
        "Species": "Bobcat",
        "Acoustic/Visual Profile": "Eerie screaming, guttural growls, and raspy squalls during mating season",
        "Regions Present": ["ALL"],
        "Macaulay Link": get_macaulay_url("Lynx rufus vocalization")
    },
    {
        "Species": "Coyote (Pack)",
        "Acoustic/Visual Profile": "Group yip-howls creating acoustic Doppler illusion of multiple unseen vocalists",
        "Regions Present": ["ALL"],
        "Macaulay Link": get_macaulay_url("Canis latrans howl")
    },
    {
        "Species": "Black Bear",
        "Acoustic/Visual Profile": "Bipedal posture when foraging; heavy huffs, jaw pops, aggressive tree shaking, and stomps",
        "Regions Present": ["NC", "ME", "VA", "WV", "TN", "PA", "NY", "OR", "WA", "CA"],
        "Macaulay Link": get_macaulay_url("Ursus americanus huff")
    },
    {
        "Species": "Elk (Wapiti)",
        "Acoustic/Visual Profile": "Eerie high-pitched bugle echoing across high elevation mountain valleys",
        "Regions Present": ["NC", "PA", "TN", "OR", "WA", "MT", "WY", "CO"],
        "Macaulay Link": get_macaulay_url("Cervus canadensis bugle")
    }
]

def get_local_wildlife(location_string):
    loc_upper = location_string.upper()
    local_list = []
    for animal in WILDLIFE_DATABASE:
        if "ALL" in animal["Regions Present"]:
            local_list.append(animal)
        elif any(region in loc_upper for region in animal["Regions Present"]):
            local_list.append(animal)
    return local_list if local_list else WILDLIFE_DATABASE[:4]

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
        show_bfro = c1.checkbox("Documented Sighting Nodes (Supabase)", value=True)
        show_lore = c2.checkbox("🪶 Primary Ethno-Historical Lore", value=True)
        show_camping = c3.checkbox("⛺ Public Land Access", value=True)
        show_infrasound = c4.checkbox("🔊 Acoustic / Infrasound Hazards", value=True)
        show_wildlife = c1.checkbox("🐻 Local Fauna (Null Hypothesis)", value=True)

    m = folium.Map(
        location=[st.session_state.center_lat, st.session_state.center_lon],
        zoom_start=10,
        tiles="OpenStreetMap"
    )

    # Analysis Center Marker
    folium.Marker(
        [st.session_state.center_lat, st.session_state.center_lon],
        popup=f"<b>Analysis Center</b><br>{st.session_state.location_name}<br>Lat: {st.session_state.center_lat:.4f}, Lon: {st.session_state.center_lon:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)

    # Wildlife Pins
    if show_wildlife:
        for idx, species in enumerate(active_wildlife[:3]):
            offset_lat = st.session_state.center_lat + (0.015 * (idx + 1))
            offset_lon = st.session_state.center_lon - (0.02 * (idx + 1))
            wildlife_html = f"""
            <b>🐾 Candidate Species: {species['Species']}</b><br>
            <p><b>Acoustic Profile:</b> {species['Acoustic/Visual Profile']}</p>
            <a href="{species['Macaulay Link']}" target="_blank">🔊 Listen to Verified {species['Species']} Audio</a>
            """
            folium.Marker(
                [offset_lat, offset_lon],
                popup=folium.Popup(wildlife_html, max_width=280),
                icon=folium.Icon(color="cadetblue", icon="paw", prefix="fa")
            ).add_to(m)

    # Lore Pins
    if show_lore:
        lore_html = """
        <b>🪶 Primary Record: Ethno-Historical Lore Node</b><br>
        <p>Cherokee & regional settler oral histories record large wild beings controlling game across high bald peaks and timberlines.</p>
        <a href="https://www.ncpedia.org/judaculla-rock" target="_blank">📄 Read Historical Archive Record</a>
        """
        folium.Marker(
            [st.session_state.center_lat + 0.025, st.session_state.center_lon + 0.025],
            popup=folium.Popup(lore_html, max_width=280),
            icon=folium.Icon(color="orange", icon="feather", prefix="fa")
        ).add_to(m)

    # FETCH ALL SIGHTING REPORTS FROM SUPABASE
    if show_bfro and supabase:
        try:
            response = supabase.table("sighting_reports").select("*").execute()
            sightings = response.data
            for report in sightings:
                s_html = f"""
                <b>👣 [{report.get('source', 'Sighting')}] {report.get('title', 'Historical Report')}</b><br>
                <i>Date: {report.get('event_date', 'N/A')} | Rating: {report.get('class_rating', 'Class A/B')}</i><br>
                <p>{report.get('summary', 'No summary details.')}</p>
                """
                folium.Marker(
                    [report["latitude"], report["longitude"]],
                    popup=folium.Popup(s_html, max_width=280),
                    icon=folium.Icon(color="blue", icon="tree", prefix="fa")
                ).add_to(m)
        except Exception as e:
            st.warning(f"Sighting query error: {e}")

    # FETCH USER FIELD LOGS FROM SUPABASE
    if supabase:
        try:
            response = supabase.table("user_field_logs").select("*").execute()
            field_logs = response.data
            for log in field_logs:
                if log.get("privacy_setting") == "Public":
                    log_html = f"<b>📌 {log['title']}</b><br><i>By {log['researcher_name']}</i><br><p>{log['notes']}</p>"
                    folium.Marker(
                        [log["latitude"], log["longitude"]],
                        popup=folium.Popup(log_html, max_width=250),
                        icon=folium.Icon(color="darkgreen", icon="flag", prefix="fa")
                    ).add_to(m)
        except Exception:
            pass

    st_folium(m, width=1000, height=550, returned_objects=[])

# ------------------------------------------
# TAB 2: LOCAL CANDIDATE SPECIES (RULE-OUTS)
# ------------------------------------------
with tab_wildlife:
    st.subheader(f"🔊 Null-Hypothesis Analysis: Local Candidate Fauna for `{st.session_state.location_name}`")
    st.write("Applying strict scientific controls: before attributing an acoustic or visual anomaly to an unclassified hominid, rule out these confirmed regional species:")

    df_local_wildlife = pd.DataFrame(active_wildlife)
    st.data_editor(
        df_local_wildlife[["Species", "Acoustic/Visual Profile", "Macaulay Link"]],
        column_config={
            "Macaulay Link": st.column_config.LinkColumn("Macaulay Library Audio Search", display_text="🔊 Play Verified Audio Clips")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 3: PRIMARY SOURCES & ETHNO-LORE
# ------------------------------------------
with tab_archives:
    st.subheader(f"📰 Digitized Primary Sources & Historical Archives for `{st.session_state.location_name}`")
    st.write("Direct queries sent to the Library of Congress (Chronicling America) and state historical archives for 19th and early 20th century records.")

    loc_name = st.session_state.location_name
    
    local_news_records = [
        {
            "Topic / Historical Term": "19th Century 'Hairy Giant' & 'Wild Man' Reports",
            "Archive Source": "Library of Congress (Chronicling America)",
            "Search Query Focus": f"Hairy Giant / Wild Man in {loc_name}",
            "Primary Source Link": get_loc_archive_url("Hairy Giant", loc_name)
        },
        {
            "Topic / Historical Term": "Unexplained Wilderness Vocalizations & Wood Knocks",
            "Archive Source": "Library of Congress (Chronicling America)",
            "Search Query Focus": f"Strange screams / sounds in timberland near {loc_name}",
            "Primary Source Link": get_loc_archive_url("Wild Man Mountain", loc_name)
        },
        {
            "Topic / Historical Term": "Native Indigenous Oral History & Ethno-Lore",
            "Archive Source": "Regional Native Historical Archives & NCpedia",
            "Search Query Focus": "Indigenous accounts of mountain giants & wilderness guardians",
            "Primary Source Link": "https://www.ncpedia.org/judaculla-rock"
        }
    ]

    df_news = pd.DataFrame(local_news_records)
    st.data_editor(
        df_news,
        column_config={
            "Primary Source Link": st.column_config.LinkColumn("Historical Archive Query", display_text="📄 Search Library of Congress Scans")
        },
        disabled=True,
        use_container_width=True
    )

# ------------------------------------------
# TAB 4: SCIENTIFIC DATA LOGGER (WRITES TO SUPABASE)
# ------------------------------------------
with tab_field:
    st.subheader("📌 Scientific Field Observation Logger")
    st.write("Standardized data collection saved directly to your Supabase cloud database.")
    
    col1, col2 = st.columns(2)
    with col1:
        e_title = st.text_input("Observation Title / Log ID", "Creek Bed Trackway Log")
        e_researcher = st.text_input("Lead Researcher Name", "Max Powers")
        e_lat = st.number_input("Latitude", value=st.session_state.center_lat, format="%.6f")
        e_lon = st.number_input("Longitude", value=st.session_state.center_lon, format="%.6f")
    with col2:
        e_substrate = st.selectbox("Substrate / Soil Type", ["Silt / Mud", "Sand", "Pine Needles / Duft", "Hardpacked Dirt", "Rock / Riverbed"])
        e_priv = st.radio("Data Privacy", ["Public", "Private"])
        e_notes = st.text_area("Objective Metrics (Stride Length, Depth, Weather, Decibels)", height=100)

    if st.button("💾 Save Observation Pin to Database"):
        if supabase:
            try:
                new_log = {
                    "title": e_title,
                    "researcher_name": e_researcher,
                    "latitude": e_lat,
                    "longitude": e_lon,
                    "privacy_setting": e_priv,
                    "substrate": e_substrate,
                    "notes": e_notes
                }
                supabase.table("user_field_logs").insert(new_log).execute()
                st.success("✅ Log saved directly to Supabase cloud database! Refresh map to view pin.")
            except Exception as e:
                st.error(f"Error saving to database: {e}")
        else:
            st.error("Supabase database connection not active.")

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
    st.download_button("📥 Download .GPX File for Field Mapping", data=gpx, file_name="max_powers_target.gpx")
