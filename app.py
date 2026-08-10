import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point, Polygon
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation
import random
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import numpy as np

# ==========================================
# 1. PAGE SETUP & SESSION STATE INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "user_lat" not in st.session_state:
    st.session_state.user_lat = 41.7000
if "user_lon" not in st.session_state:
    st.session_state.user_lon = -70.3000
if "location_name" not in st.session_state:
    st.session_state.location_name = "Massachusetts Target Zone"

lat = float(st.session_state.user_lat)
lon = float(st.session_state.user_lon)
loc_name = str(st.session_state.location_name)

# ==========================================
# CUSTOM BRANDING HEADER (SINGLE BANNER)
# ==========================================
try:
    st.image("image.png", use_container_width=True)
except Exception:
    try:
        st.image("header_banner.png", use_container_width=True)
    except Exception:
        st.title("Maxquest")

st.caption("Site-Specific Spatial Map & Predictive Multi-Criteria Analysis Engine")
st.markdown("---")

# ==========================================
# 2. SUPABASE CONNECTION & UTILITIES
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets.get("SUPABASE_URL", "https://knyusghtnszqbburygor.supabase.co")
        key = st.secrets.get("SUPABASE_KEY", "sb_publishable_ydyOYDYfYTKhGHlZv0AqIg_kzs_SKjM")
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Supabase Init Failed: {e}")
        return None

supabase: Client = init_supabase()

def apply_jitter(lat_val, lon_val, offset_seed=0):
    random.seed(int(lat_val * 1000) + int(lon_val * 1000) + offset_seed)
    return lat_val + random.uniform(-0.003, 0.003), lon_val + random.uniform(-0.003, 0.003)

def haversine_miles(lat1, lon1, lat2, lon2):
    R = 3958.8
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
def geocode_mapbox(query):
    token = st.secrets.get("MAPBOX_TOKEN", "")
    if not token: return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(query)}.json"
    try:
        resp = requests.get(url, params={"access_token": token, "limit": 1}, timeout=5)
        if resp.status_code == 200 and resp.json().get("features"):
            feature = resp.json()["features"][0]
            return feature["center"][1], feature["center"][0], feature.get("place_name", query)
    except Exception: pass
    return None

with st.sidebar:
    st.header("⚙️ Field Controls")
    loc_search = st.text_input("📍 Target Search Area", value=loc_name)
    radius_miles = st.selectbox("Field Radius (Miles)", [25, 50, 100, 250, 500], index=2)
    deg_delta = radius_miles / 69.0

    col_s1, col_s2 = st.columns(2)
    if col_s1.button("🔎 Search Area", use_container_width=True) and loc_search:
        res = geocode_mapbox(loc_search)
        if res:
            st.session_state.user_lat, st.session_state.user_lon, st.session_state.location_name = res
            st.rerun()

    if col_s2.button("📲 Device GPS", use_container_width=True):
        loc_data = get_geolocation()
        if loc_data and "coords" in loc_data:
            st.session_state.user_lat = loc_data["coords"]["latitude"]
            st.session_state.user_lon = loc_data["coords"]["longitude"]
            st.session_state.location_name = "Device GPS"
            st.rerun()

    st.markdown("---")
    st.subheader("🗺️ Active Map Layers")
    show_bfro = st.checkbox("1. 👣 Sightings", value=True)
    show_lore = st.checkbox("2. 🪶 Indigenous Lore", value=True)
    show_news = st.checkbox("3. 📰 Press Archives", value=True)
    show_hotspots = st.checkbox("4. 🚨 Hot Zones & Larson Corridors", value=True)
    show_audio = st.checkbox("5. 🔊 Infrasound Masking", value=True)

# ==========================================
# 4. TAB NAVIGATION & DATA RETRIEVAL
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Research Library"])

sightings_data, camps_data, audio_data, media_data, lore_data = [], [], [], [], []

if supabase:
    lat_min, lat_max = lat - deg_delta, lat + deg_delta
    lon_min, lon_max = lon - deg_delta, lon + deg_delta

    try:
        r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("historical_media").select("*").execute()
        media_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("tribal_lore").select("*").execute()
        lore_data = r.data or []
    except Exception: pass

# ==========================================
# TAB 1: SPATIAL MAP ENGINE
# ==========================================
with tab_map:
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Sector Records (Within {radius_miles} miles):</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🪶 Tribal Lore: <code>{len(lore_data)}</code> | 
        📰 Press Archives: <code>{len(media_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    if show_bfro and sightings_data:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_summary = s.get("summary", "No transcript provided.")
            raw_id = str(s.get('report_id', '')).strip()
            
            link_html = f'<br><a href="https://www.bfro.net/GDB/show_report.asp?id={raw_id}" target="_blank" style="color:#007bff;">📄 View BFRO Report #{raw_id}</a>' if raw_id.isdigit() else ''

            popup_html = f"<b>👣 {s.get('title', 'Sighting')}</b><br><small>{raw_summary[:150]}...</small>{link_html}"
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=250), icon=folium.Icon(color="blue", icon="paw", prefix="fa")).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

# ==========================================
# TAB 2: RESEARCH LIBRARY
# ==========================================
with tab_library:
    st.header("📚 Research Library & Analytical Vault")
    
    lib_choice = st.radio(
        "Select Vault Section:", 
        ["🔊 Infrasound & Acoustic Physics", "👣 BFRO Sightings Vault", "🪶 Indigenous Ethnographic Lore", "📰 Historical Press Archives", "🦉 Bioacoustics Guide"], 
        horizontal=True
    )

    st.markdown("---")

    # 1. INFRASOUND
    if "Infrasound" in lib_choice:
        st.subheader("🔊 Crash Course: Infrasound Physics, Propagation, & Physiological Impact")
        
        st.markdown("### 1. What is Infrasound?")
        st.write(
            "Infrasound refers to acoustic waves that oscillate at frequencies below the human lower limit of audibility—typically "
            "between 0.1 Hz and 20 Hz. Because these waves possess extremely long wavelengths (ranging from 50 feet up to several miles), "
            "they interact with the environment in unique ways. High-frequency sounds like bird calls are easily blocked by foliage and terrain, "
            "whereas infrasonic waves pass through dense forest canopy, timber, and granite with minimal loss of energy."
        )

        st.markdown("### 2. Atmospheric Propagation & Acoustic Ducting")
        st.write(
            "Infrasound travels dozens or even hundreds of miles without losing significant power. At standard audible frequencies (1,000 Hz), "
            "atmospheric friction dampens sound over short distances. At sub-audible frequencies (below 10 Hz), atmospheric absorption drops to "
            "nearly zero. Under thermal inversions or mountain valley pressure ceilings, infrasonic waves bounce between the ground and the air "
            "layers in a channel called acoustic ducting, allowing low-frequency signals to saturate entire river systems."
        )

        st.markdown("### 3. Natural vs. Biological Generators")
        st.write(
            "Wilderness infrasound comes from two distinct sources. Abiotic generators include wind-notch mountain passes (where high winds "
            "funnel through narrow granite gaps like a giant whistle at 0.5 to 5 Hz) and hydro-electric dams or waterfalls (producing deep hydraulic "
            "impact rumbles at 3 to 15 Hz). Biological generators include large terrestrial mammals like elephants, tigers, and cassowaries. "
            "Hypothesized relict hominids with large chest cavities could utilize 8 to 18 Hz vocal emissions for long-range communication across "
            "valleys or as an acoustic deterrent against competitors."
        )

        st.markdown("### 4. Human Physiological & Neurological Effects")
        st.write(
            "When humans enter an active infrasound envelope without realization, the body reacts physically even though the ears hear nothing. "
            "Frequencies between 1 and 7 Hz match the internal resonance of human inner ear fluid, causing sudden dizziness, micro-barometric "
            "headaches, and disorientation. Frequencies between 7 and 12 Hz overlap with human brain alpha waves, inducing acute hyper-vigilance, "
            "irrational fear, and a strong sense of being watched. Frequencies around 19 Hz match the resonant frequency of the human eyeball, "
            "causing subtle ocular vibrations that create peripheral optical smears or shadow-like visual distortions."
        )

    # 2. BFRO SIGHTINGS WITH DIRECT LINKS
    elif "BFRO Sightings" in lib_choice:
        st.subheader("👣 BFRO Field Report Archives")
        for item in sightings_data[:25]:
            raw_id = str(item.get('report_id', '')).strip()
            title = item.get('title', 'Sighting Report')
            event_date = item.get('event_date', 'N/A')
            class_rating = item.get('class_rating', 'Class A')
            summary = item.get('summary', 'No summary transcript recorded.')

            st.markdown(f"#### {title} ({event_date})")
            st.write(f"**Class:** `{class_rating}` | **Location:** {item.get('county', 'N/A')}, {item.get('state', 'N/A')}")
            st.info(summary)
            if raw_id.isdigit():
                st.markdown(f"[📄 View Official BFRO Report #{raw_id}](https://www.bfro.net/GDB/show_report.asp?id={raw_id})")
            st.markdown("---")

    # 3. INDIGENOUS LORE
    elif "Lore" in lib_choice:
        st.subheader("🪶 Indigenous Ethnographic Lore & Land Anchors")
        st.write("Regional tribal records documenting wilderness hominid entities:")
        for item in lore_data:
            st.markdown(f"#### {item.get('tribe_name')} — *{item.get('entity_name')}*")
            st.write(f"**Region:** `{item.get('region_label')}` | **Evidence Weight:** `{item.get('evidence_weight', 1.5)}x`")
            st.write(item.get("full_narrative"))
            st.markdown("---")

    # 4. HISTORICAL PRESS ARCHIVES
    elif "Press Archives" in lib_choice:
        st.subheader("📰 Historical Press Archives")
        for item in media_data:
            pub_name = item.get('publication_name', item.get('source', 'Historical Archive'))
            st.markdown(f"#### {item.get('title')} ({item.get('pub_date')})")
            st.write(f"**Source:** `{pub_name}` | **Location:** {item.get('county', 'N/A')}, {item.get('state', 'N/A')}")
            st.write(f"> {item.get('full_text_transcript')}")
            st.markdown("---")

    # 5. BIOACOUSTICS
    elif "Bioacoustics" in lib_choice:
        st.subheader("🦉 Bioacoustics & Fauna Repertoires")
        st.markdown(
            "* **Barred Owl (*Strix varia*):** Produces caterwauls, screams, and multi-tone hoots.\n"
            "* **Eastern Coyote (*Canis latrans*):** High-pitched yips and howl-harmonics across valley floors.\n"
            "* **Red Fox (*Vulpes vulpes*):** Unsettling night alarm screams in the 1.5 kHz to 3.5 kHz range.\n"
            "* **White-Tailed Deer (*Odocoileus virginianus*):** Loud, explosive blowing snorts used as perimeter warnings."
        )
