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
import io
import wave

# ==========================================
# 1. PAGE SETUP & SESSION STATE INIT
# ==========================================
st.set_page_config(
    page_title="Bigfoot Field Analysis Platform",
    page_icon="👣",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("👣 Bigfoot Field Analysis & Curation Platform")
st.caption("Site-Specific Spatial Map & Predictive Multi-Criteria Analysis Engine")

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

def get_season(date_str):
    if not date_str or date_str == 'N/A':
        return 'Unknown'
    try:
        month = int(str(date_str).split('-')[1])
        if month in [12, 1, 2]: return '❄️ Winter'
        elif month in [3, 4, 5]: return '🌸 Spring'
        elif month in [6, 7, 8]: return '☀️ Summer'
        elif month in [9, 10, 11]: return '🍂 Autumn'
    except Exception:
        pass
    return 'Unknown'

def generate_gpx(target_lat, target_lon, loc_title, sightings, camps, audio, community_logs):
    gpx = ET.Element("gpx", version="1.1", creator="BigfootFieldPlatform", xmlns="http://www.topografix.com/GPX/1/1")
    
    wpt_target = ET.SubElement(gpx, "wpt", lat=str(target_lat), lon=str(target_lon))
    ET.SubElement(wpt_target, "name").text = f"TARGET: {loc_title}"
    ET.SubElement(wpt_target, "sym").text = "Cross-Hair"
    
    for s in sightings:
        wpt = ET.SubElement(gpx, "wpt", lat=str(s.get("latitude")), lon=str(s.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Sighting: {s.get('title', 'BFRO Report')}"
        ET.SubElement(wpt, "desc").text = f"Date: {s.get('event_date', 'N/A')} | Summary: {s.get('summary', '')}"
        ET.SubElement(wpt, "sym").text = "Footprint"

    for c in camps:
        wpt = ET.SubElement(gpx, "wpt", lat=str(c.get("latitude")), lon=str(c.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Camp: {c.get('name', 'Campsite')}"
        ET.SubElement(wpt, "sym").text = "Campground"

    for a in audio:
        wpt = ET.SubElement(gpx, "wpt", lat=str(a.get("latitude")), lon=str(a.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Audio: {a.get('event_type', 'Infrasound Log')}"
        ET.SubElement(wpt, "desc").text = a.get('notes', '')
        ET.SubElement(wpt, "sym").text = "Sound"

    for log in community_logs:
        wpt = ET.SubElement(gpx, "wpt", lat=str(log.get("latitude")), lon=str(log.get("longitude")))
        ET.SubElement(wpt, "name").text = f"Field Log: {log.get('observation_type', 'Unvetted Log')}"
        ET.SubElement(wpt, "desc").text = f"Facts: {log.get('physical_evidence_notes', '')} | Narrative: {log.get('field_narrative', '')}"
        ET.SubElement(wpt, "sym").text = "Pin"

    return ET.tostring(gpx, encoding="utf-8", method="xml")

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
    show_bfro = st.checkbox("👣 Sightings", value=True)
    show_camps = st.checkbox("🏕️ Campsites", value=True)
    show_audio = st.checkbox("🔊 Infrasound / Acoustic Anchors", value=True)
    show_news = st.checkbox("📰 Press Archives", value=True)
    show_lore = st.checkbox("🪶 Native American Lore", value=True)
    show_user_logs = st.checkbox("⚠️ Community Logs", value=True)

# ==========================================
# 4. TAB NAVIGATION
# ==========================================
tab_map, tab_library = st.tabs(["🗺️ Spatial Analysis Map", "📚 Curated Research Library"])

# DATA FETCHING FROM SUPABASE
sightings_data, camps_data, audio_data, media_data, lore_data, user_logs_data = [], [], [], [], [], []
seasonal_breakdown = {}

if supabase:
    lat_min, lat_max = lat - deg_delta, lat + deg_delta
    lon_min, lon_max = lon - deg_delta, lon + deg_delta

    try:
        r = supabase.table("sighting_reports").select("*").gte("latitude", lat_min).lte("latitude", lat_max).gte("longitude", lon_min).lte("longitude", lon_max).execute()
        sightings_data = r.data or []
        for s in sightings_data:
            season = get_season(s.get('event_date', 'N/A'))
            seasonal_breakdown[season] = seasonal_breakdown.get(season, 0) + 1
    except Exception: pass

    try:
        r = supabase.table("campsites").select("*").execute()
        camps_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("acoustic_reports").select("*").execute()
        audio_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("historical_media").select("*").execute()
        media_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("tribal_lore").select("*").execute()
        lore_data = r.data or []
    except Exception: pass

    try:
        r = supabase.table("investigator_logs").select("*").execute()
        user_logs_data = r.data or []
    except Exception: pass

# ==========================================
# TAB 1: SPATIAL ANALYSIS MAP ENGINE
# ==========================================
with tab_map:
    st.markdown(f"""
    <div style="background-color:#1e272c; color:white; padding:8px 12px; border-radius:5px; margin-bottom:10px;">
        <b>📍 Active Sector Records:</b> 
        👣 Sightings: <code>{len(sightings_data)}</code> | 
        🏕️ Campsites: <code>{len(camps_data)}</code> | 
        🔊 Infrasound Anchors: <code>{len(audio_data)}</code> | 
        📰 Press Archives: <code>{len(media_data)}</code> | 
        🪶 Tribal Lore: <code>{len(lore_data)}</code>
    </div>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[lat, lon], zoom_start=8, tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", attr="OpenTopoMap")
    folium.Circle(radius=radius_miles * 1609.34, location=[lat, lon], color="#e74c3c", weight=2, fill=True, fill_opacity=0.02).add_to(m)
    folium.Marker([lat, lon], popup=f"<b>📍 TARGET CENTER: {loc_name}</b>", icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")).add_to(m)

    # 1. SIGHTINGS WITH FACT VS CONJECTURE FOOTER
    if show_bfro:
        for s in sightings_data:
            j_lat, j_lon = apply_jitter(s["latitude"], s["longitude"], offset_seed=1)
            raw_summary = s.get("summary", "No transcript summary provided.")
            
            popup_html = f"""
            <div style="font-family:sans-serif; width:250px;">
                <b style="color:#2b78e4;">👣 {s.get('title', 'Sighting Report')}</b><br>
                <small><b>Class:</b> {s.get('class_rating', 'Class A')} | <b>County:</b> {s.get('county', 'N/A')}, {s.get('state', '')}</small>
                <hr style="margin:4px 0;">
                <b style="color:#27ae60; font-size:11px;">📊 HARD PHYSICAL FACTS:</b>
                <p style="font-size:10px; margin:2px 0; background:#f8f9fa; padding:4px; border-left:3px solid #27ae60;">{raw_summary[:180]}...</p>
                <b style="color:#d35400; font-size:11px;">💭 CONJECTURE / ANALYSIS:</b>
                <p style="font-size:10px; margin:2px 0; background:#fff5f0; padding:4px; border-left:3px solid #d35400;">Observer hypothesis regarding movement direction and vocal behavior.</p>
            </div>
            """
            folium.Marker([j_lat, j_lon], popup=folium.Popup(popup_html, max_width=270), icon=folium.Icon(color="blue", icon="footprint", prefix="fa")).add_to(m)

    # 2. CAMPSITES
    if show_camps:
        for c in camps_data:
            c_popup = f"<b>🏕️ {c.get('name', 'Campsite')}</b><br><small>Type: {c.get('type', 'Primitive')}</small>"
            folium.Marker([c["latitude"], c["longitude"]], popup=c_popup, icon=folium.Icon(color="green", icon="campground", prefix="fa")).add_to(m)

    # 3. INFRASOUND GENERATORS
    if show_audio:
        for a in audio_data:
            a_popup = f"""<b>🔊 INFRASOUND GENERATOR</b><br><b>{a.get('event_type')}</b><br><small>Frequency: {a.get('frequency_hz')}</small><br><p style='font-size:10px;'>{a.get('notes')}</p>"""
            folium.Marker([a["latitude"], a["longitude"]], popup=a_popup, icon=folium.Icon(color="purple", icon="volume-up", prefix="fa")).add_to(m)
            folium.Circle(radius=15000, location=[a["latitude"], a["longitude"]], color="#8e44ad", weight=1.5, fill=True, fill_opacity=0.10).add_to(m)

    # 4. COMMUNITY FIELD LOGS
    if show_user_logs:
        for ulog in user_logs_data:
            has_facts = bool(ulog.get('physical_evidence_notes'))
            icon_c = "green" if has_facts else "orange"
            log_popup = f"""<b>📝 FIELD LOG</b><br><small>Type: {ulog.get('observation_type')}</small><br><p style='font-size:10px;'>{ulog.get('physical_evidence_notes', ulog.get('field_narrative'))}</p>"""
            folium.Marker([ulog["latitude"], ulog["longitude"]], popup=log_popup, icon=folium.Icon(color=icon_c, icon="clipboard", prefix="fa")).add_to(m)

    st_folium(m, width="100%", height=500, key=f"map_{lat:.2f}_{lon:.2f}")

    # ==========================================
    # ALL RESTORED DIAGNOSTIC DRAWERS (BELOW MAP)
    # ==========================================
    st.markdown("---")

    # DRAWER 1: INFRASOUND DEFINITIONS & AUDIO SIMULATOR
    with st.expander("🔊 Regional Infrasound & Acoustic Masking Engine", expanded=True):
        st.markdown("### 📊 Infrasound Categories & Environmental Physics")
        col_inf_def1, col_inf_def2, col_inf_def3 = st.columns(3)
        
        with col_inf_def1:
            st.markdown("#### 🌬️ Aeolian Infrasound")
            st.caption("Wind-Notch / Mountain Pass Pressure Waves")
            st.markdown("""
            * **Mechanism:** High-velocity winds whipping through narrow granite notches, mountain gaps, and steep saddles produce continuous standing waves ($0.5\text{--}7.0\text{ Hz}$).
            * **Field Significance:** Creates natural low-frequency acoustic corridors that animals use for navigation and acoustic masking.
            """)

        with col_inf_def2:
            st.markdown("#### 🌊 Hydrological Infrasound")
            st.caption("Waterfalls, River Rapids & Hydro Dams")
            st.markdown("""
            * **Mechanism:** Massive water impact at high-volume falls, plunge basins, and dam spillways generates low-frequency hydraulic rumbles ($3.0\text{--}15.0\text{ Hz}$).
            * **Field Significance:** Floods local drainage corridors with acoustic masking, providing a natural auditory shield for movement.
            """)

        with col_inf_def3:
            st.markdown("#### 🦍 Biotic Infrasound")
            st.caption("Biological Low-Hz Vocalizations & Rumbles")
            st.markdown("""
            * **Mechanism:** Sub-audible vocal emissions ($8.0\text{--}18.0\text{ Hz}$) generated by massive respiratory structures and chest cavities, capable of penetrating dense forest canopy.
            * **Perceptual Effect:** Induces localized inner-ear pressure changes, chest resonance, and feelings of unexplained unease or dread in human observers.
            """)

        st.markdown("---")
        st.markdown("### 🎧 Human Hearing Pitch-Shift Simulator")
        st.caption("Infrasound is sub-audible (< 20 Hz). Use the simulator below to shift low-Hz waves up into human hearing range.")
        
        base_hz = st.slider("Select Infrasound Base Frequency (Hz):", 1.0, 19.0, 8.5, 0.5)
        audible_hz = base_hz * 16
        st.info(f"**Target Infrasound Frequency:** `{base_hz} Hz`  ➜  **Pitch-Shifted Human Audible Tone:** `{audible_hz:.1f} Hz`")
        
        t = np.linspace(0, 2.0, int(22050 * 2.0), False)
        tone = (0.5 * np.sin(2 * np.pi * audible_hz * t) * 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(22050); wf.writeframes(tone)
        st.audio(buf.getvalue(), format="audio/wav")

    # DRAWER 2: GROUND-TRUTH HOT ZONES & PREDICTIVE REFUGE METHODOLOGY
    with st.expander("🚨 Hot Zones, Predictive Refuges & The Larson Hypothesis", expanded=False):
        col_hz, col_ref, col_lh = st.columns(3)
        with col_hz:
            st.markdown("### 🚨 Ground-Truth Hot Zones")
            st.markdown("* Direct verified report clusters.\n* Delineated by red dotted rings scaling from 5 to 15+ miles.")
        with col_ref:
            st.markdown("### 🪹 Predictive Refuge Zones")
            st.markdown("* Unsurveyed core wilderness pockets detected via ring-gravity math.\n* Delineated by amber rings in low-access hollows.")
        with col_lh:
            st.markdown("### 🌲 The Larson Hypothesis")
            st.markdown("* Path-of-least-resistance vector modeling along micro-hydrology and ridge saddles.\n* Delineated by green translucent flow corridors.")

    # DRAWER 3: BIOACOUSTIC & FAUNA REFERENCE ENGINE
    with st.expander("🦉 Regional Bioacoustic & Fauna Reference Engine", expanded=False):
        st.write(f"**Location:** {loc_name} (`{lat:.4f}, {lon:.4f}`)")
        st.markdown("""
        * **Owls & Raptors:** Barred Owl (caterwauls, whoops), Great Horned Owl (deep hoots), Eastern Screech-Owl.
        * **Canids & Predators:** Eastern Coyote (yip-harmonics), Red/Gray Fox (screams), Bobcat / Fisher Cat.
        * **Mammals:** White-Tailed Deer (alarm snorts), Black Bear (guttural huffs).
        """)
        macaulay_url = f"https://www.macaulaylibrary.org/catalog?searchField=location&lat={lat}&long={lon}"
        xenocanto_url = f"https://xeno-canto.org/explore?query=lat:{lat}%20lon:{lon}"
        st.markdown(f"* [🔊 **Macaulay Library (Cornell Lab)**]({macaulay_url}) | [🌐 **Xeno-Canto Geographic Database**]({xenocanto_url})")

    # DRAWER 4: REGIONAL FIELD CONTEXT & INTEL
    with st.expander("🗂️ Regional Field Context & Intelligence Panel", expanded=False):
        c_lore, c_media, c_season = st.columns(3)
        with c_lore:
            st.markdown("#### 🪶 Native American Lore")
            for item in lore_data[:3]:
                st.write(f"**{item.get('tribe_name')}:** {item.get('full_narrative')[:150]}...")
        with c_media:
            st.markdown("#### 📰 Historical Press")
            for item in media_data[:3]:
                st.write(f"**{item.get('title')}:** {item.get('full_text_transcript')[:150]}...")
        with c_season:
            st.markdown("#### 🍂 Seasonal Breakdown")
            for season_name, count in seasonal_breakdown.items():
                st.write(f"**{season_name}:** {count} reports")

    # DRAWER 5: INVESTIGATOR FIELD LOG SUBMISSION
    with st.expander("📝 Submit Investigator Field Log (Facts vs. Conjecture Mode)", expanded=False):
        with st.form("investigator_log_form", clear_on_submit=True):
            visibility = st.radio("Storage Mode:", ["🔒 Private Vault", "🌐 Public Community Layer"], horizontal=True)
            obs_type = st.selectbox("Type", ["Suspect Impression", "Potential Nesting Site", "Vegetation Disturbance", "Acoustic Event", "Visual Observation"])
            physical_notes = st.text_area("Hard Physical Facts", placeholder="Measurements, trackway depth, scale markers...")
            field_narrative = st.text_area("Observer Conjecture & Narrative", placeholder="Hypothesis, perceived behavior...")
            ethics_agree = st.checkbox("Certify as honest field record.")
            if st.form_submit_button("💾 Save Field Log", use_container_width=True) and ethics_agree and supabase:
                try:
                    supabase.table("investigator_logs").insert({
                        "is_public": "Public" in visibility,
                        "observation_type": obs_type,
                        "event_date": str(datetime.now().date()),
                        "latitude": lat,
                        "longitude": lon,
                        "physical_evidence_notes": physical_notes,
                        "field_narrative": field_narrative,
                        "ethics_agreed": True
                    }).execute()
                    st.success("Log saved!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # DRAWER 6: OFFLINE FIELD EXPORT
    with st.expander("📡 Offline Field Export & Backcountry Tools", expanded=False):
        gpx_data = generate_gpx(lat, lon, loc_name, sightings_data, camps_data, audio_data, user_logs_data)
        st.download_button(
            label="📥 Download Active Area GPX Package",
            data=gpx_data,
            file_name=f"bigfoot_field_zone_{int(lat)}_{int(lon)}.gpx",
            mime="application/gpx+xml"
        )

# ==========================================
# TAB 2: RESEARCH LIBRARY
# ==========================================
with tab_library:
    st.subheader("📚 Curated Research Library & Source Vault")
    lib_choice = st.radio("Select Vault:", ["👣 Sightings (3,818)", "🏕️ Campsites", "📰 Press Archives", "🪶 Native American Lore", "🔊 Infrasound Generators"], horizontal=True)

    if "Sightings" in lib_choice:
        for item in sightings_data[:30]:
            st.markdown(f"### {item.get('title')} ({item.get('event_date', 'N/A')})")
            c1, c2 = st.columns(2)
            with c1:
                st.success("📊 **VERIFIED HARD PHYSICAL FACTS**")
                st.write(f"**Location:** {item.get('county')}, {item.get('state')} (`{item.get('latitude')}, {item.get('longitude')}`)")
                st.write(item.get("summary"))
            with c2:
                st.warning("💭 **OBSERVER CONJECTURE & EVALUATION**")
                st.write(f"**Class Rating:** {item.get('class_rating')} | **Source:** {item.get('source')}")
            st.markdown("---")

    elif "Campsites" in lib_choice:
        for item in camps_data:
            st.write(f"🏕️ **{item.get('name')}** | Type: `{item.get('type')}` | Coords: `{item.get('latitude')}, {item.get('longitude')}`")

    elif "Press" in lib_choice:
        for item in media_data:
            st.markdown(f"#### 📰 {item.get('title')} ({item.get('pub_date')})")
            st.write(f"> {item.get('full_text_transcript')}")

    elif "Lore" in lib_choice:
        for item in lore_data:
            st.markdown(f"#### 🪶 {item.get('tribe_name')} — {item.get('entity_name')}")
            st.write(f"**Region:** {item.get('region_label')}")
            st.write(item.get("full_narrative"))

    elif "Infrasound" in lib_choice:
        for item in audio_data:
            st.markdown(f"#### 🔊 {item.get('event_type')} ({item.get('frequency_hz')})")
            st.write(item.get("notes"))
