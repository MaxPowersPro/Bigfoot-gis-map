import streamlit as st
import folium
from streamlit_folium import st_folium
from shapely.geometry import Point
import pyproj
from functools import partial
from shapely.ops import transform
import urllib.parse
import json

# ==========================================
# PAGE CONFIGURATION (CEO UI SETUP)
# ==========================================
st.set_page_config(
    page_title="Cryptid GIS & Spatial Research Engine",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌲 Cryptid GIS & Spatial Research Engine")
st.caption("Phase 1 Prototype | Objective Spatial Analysis, Infrasound Auditing & Toponym Scanning")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def create_geodesic_buffer(lat, lon, miles):
    """
    Creates a mathematically accurate geodesic circle (buffer) in miles 
    around a specific latitude and longitude point.
    """
    meters = miles * 1609.34
    proj_wgs84 = pyproj.CRS('EPSG:4326')
    
    # Azimuthal Equidistant Projection centered on target coordinate
    proj_aeqd = pyproj.CRS(f"+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0 +datum=WGS84 +units=m")
    
    project_to_aeqd = pyproj.Transformer.from_crs(proj_wgs84, proj_aeqd, always_xy=True).transform
    project_to_wgs84 = pyproj.Transformer.from_crs(proj_aeqd, proj_wgs84, always_xy=True).transform
    
    point = Point(lon, lat)
    point_aeqd = transform(project_to_aeqd, point)
    buffer_aeqd = point_aeqd.buffer(meters)
    buffer_wgs84 = transform(project_to_wgs84, buffer_aeqd)
    
    coords = list(buffer_wgs84.exterior.coords)
    return [(y, x) for x, y in coords]

def parse_witness_report(raw_text):
    """
    Categorizes raw witness statements into Concrete Observations vs. Witness Conjecture.
    """
    if not raw_text.strip():
        return None, None
        
    lines = raw_text.split('\n')
    concrete = []
    conjecture = []
    
    # Rule-based classification keywords
    conjecture_keywords = ["felt", "thought", "believed", "seemed", "appeared", "telepathic", "mindspeak", "intent", "afraid", "scared", "angry", "protecting"]
    
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if any(word in line_str.lower() for word in conjecture_keywords):
            conjecture.append(line_str)
        else:
            concrete.append(line_str)
            
    return concrete, conjecture

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.header("📍 Target Coordinates")
lat_input = st.sidebar.number_input("Latitude", value=35.944444, format="%.6f")
lon_input = st.sidebar.number_input("Longitude", value=-82.772333, format="%.6f")

st.sidebar.markdown("---")
st.sidebar.header("🔍 Dynamic Map Scope")

# Google Maps Style Zoom Slider
zoom_level = st.sidebar.slider(
    "Zoom Scope",
    min_value=6,
    max_value=14,
    value=10,
    step=1,
    help="Zoom 13 (~10mi Micro-Terrain) | Zoom 11 (~25mi Local) | Zoom 9 (~50mi Regional) | Zoom 7 (~100mi Corridor)"
)

show_active_ring = st.sidebar.checkbox("Draw Active Scope Ring on Map", value=True)

st.sidebar.markdown("---")
st.sidebar.header("🎯 Feature Layers")
show_bfro = st.sidebar.checkbox("Show BFRO Sample Nodes", value=True)
show_bfm = st.sidebar.checkbox("Show Bigfoot Mapping Project Nodes", value=True)
show_infrasound = st.sidebar.checkbox("Show Infrasound / Industrial Producers", value=True)

# ==========================================
# MAIN INTERFACE TABS
# ==========================================
tab_map, tab_toponyms, tab_parser, tab_export = st.tabs([
    "🗺️ Interactive GIS Map", 
    "🏷️ USGS Ominous Toponyms", 
    "📄 Witness Report Filter", 
    "📱 onX / GPX Exporter"
])

# ------------------------------------------
# TAB 1: INTERACTIVE MAP (TOUCH & PINCH ENABLED)
# ------------------------------------------
with tab_map:
    st.subheader("Spatial Overlay & Dynamic Viewport")
    st.caption("Pinch with two fingers on mobile to zoom, or drag with one finger to pan.")
    
    # Initialize Folium Map with Native Mobile Touch Optimizations
    m = folium.Map(
        location=[lat_input, lon_input], 
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        control_scale=True,       # Google-style distance scale (miles/km)
        zoom_control=True,        # On-screen +/- buttons
        scroll_wheel_zoom=True,   # Desktop mouse wheel zoom
        touch_zoom=True,          # Native mobile pinch-to-zoom
        dragging=True             # One-finger touch panning
    )
    
    # Center Pin
    folium.Marker(
        [lat_input, lon_input],
        popup=f"Target: {lat_input:.4f}, {lon_input:.4f}",
        icon=folium.Icon(color="red", icon="crosshairs", prefix="fa")
    ).add_to(m)
    
    # Active Radius Ring based on Zoom Level
    if show_active_ring:
        zoom_to_miles = {6: 150, 7: 100, 8: 75, 9: 50, 10: 35, 11: 25, 12: 15, 13: 10, 14: 5}
        active_miles = zoom_to_miles.get(zoom_level, 25)
        
        poly_coords = create_geodesic_buffer(lat_input, lon_input, active_miles)
        folium.Polygon(
            locations=poly_coords,
            color="#3388ff",
            weight=2,
            fill=True,
            fill_opacity=0.06,
            popup=f"Active Scope: ~{active_miles} Miles"
        ).add_to(m)

    # Biological Sightings Layer (BFRO)
    if show_bfro:
        bfro_group = folium.FeatureGroup(name="BFRO Reports (Biological Focus)").add_to(m)
        folium.Marker(
            [lat_input + 0.04, lon_input - 0.03],
            popup="<b>BFRO Class A</b><br>Wood knocks, rock throwing along creek bed.",
            icon=folium.Icon(color="blue", icon="tree", prefix="fa")
        ).add_to(bfro_group)

    # Bigfoot Mapping Project Layer
    if show_bfm:
        bfm_group = folium.FeatureGroup(name="Bigfoot Mapping Project").add_to(m)
        folium.Marker(
            [lat_input - 0.02, lon_input + 0.05],
            popup="<b>BFM Sighting Node</b><br>Visual encounter near ridge trail.",
            icon=folium.Icon(color="green", icon="eye", prefix="fa")
        ).add_to(bfm_group)

    # Infrasound Layer
    if show_infrasound:
        infra_group = folium.FeatureGroup(name="Infrasound Producers").add_to(m)
        folium.Marker(
            [lat_input + 0.08, lon_input + 0.02],
            popup="<b>Infrasound Producer: Hydroelectric Dam</b><br>Continuous low-frequency vibration (0.5 - 12 Hz).",
            icon=folium.Icon(color="purple", icon="industry", prefix="fa")
        ).add_to(infra_group)

    # Render Map
    st_folium(m, width=1100, height=600)

# ------------------------------------------
# TAB 2: USGS TOPONYM SCANNER
# ------------------------------------------
with tab_toponyms:
    st.subheader("USGS GNIS Ominous & Folklore Feature Scanner")
    st.write("Identifies local physical features with ominous or historical folklore names within radius.")
    
    ominous_keywords = ["Devil", "Dead", "Ghost", "Hell", "Coffin", "Skeleton", "Blood", "Dark", "Spook", "Witch"]
    st.markdown("**Active Keyword Filter:** " + ", ".join([f"`{k}`" for k in ominous_keywords]))
    
    gnis_data = [
        {"Feature Name": "Devil's Fork", "Type": "Stream", "Distance (mi)": 4.2, "Keyword Match": "Devil"},
        {"Feature Name": "Deadman Branch", "Type": "Stream", "Distance (mi)": 8.7, "Keyword Match": "Dead"},
        {"Feature Name": "Hell Hole Gap", "Type": "Gap", "Distance (mi)": 14.1, "Keyword Match": "Hell"},
        {"Feature Name": "Coffin Ridge", "Type": "Ridge", "Distance (mi)": 22.5, "Keyword Match": "Coffin"},
    ]
    st.table(gnis_data)

# ------------------------------------------
# TAB 3: WITNESS REPORT PARSER
# ------------------------------------------
with tab_parser:
    st.subheader("Witness Report Objective Data Extractor")
    st.write("Paste a raw witness statement below to parse **Concrete Physical Observations** from **Witness Conjecture**.")
    
    sample_text = """We were fishing near the river late at night. Out of nowhere, all insect noises completely stopped.
Then something threw a heavy rock into the river about 20 yards away, followed by a foul rotten sulfur smell.
I heard a deep, low-frequency growl that shook my chest.
I felt in my gut that it was telepathic and was trying to warn us that it was going to attack us if we didn't leave."""

    user_report = st.text_area("Raw Witness Statement", value=sample_text, height=180)
    
    if st.button("Extract Data & Parse"):
        concrete, conjecture = parse_witness_report(user_report)
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("🟢 Concrete Observations (Raw Data)")
            if concrete:
                for line in concrete:
                    st.markdown(f"- {line}")
            else:
                st.write("No concrete observations identified.")
                
        with col2:
            st.warning("🟡 Witness Conjecture & Subjective Claims")
            if conjecture:
                for line in conjecture:
                    st.markdown(f"- {line}")
            else:
                st.write("No conjecture identified.")

# ------------------------------------------
# TAB 4: ONX / GPX EXPORTER
# ------------------------------------------
with tab_export:
    st.subheader("Export Targets to onX Maps / Field Navigation")
    st.write("Generate a standard `.GPX` file to import target coordinates straight into **onX Offroad** or **Gaia GPS**.")
    
    gpx_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="CryptidGIS">
  <wpt lat="{lat_input}" lon="{lon_input}">
    <name>Target Center Point</name>
    <desc>Cryptid GIS Target Center</desc>
  </wpt>
  <wpt lat="{lat_input + 0.04}" lon="{lon_input - 0.03}">
    <name>BFRO Sighting Node</name>
    <desc>Class A Sighting Spot</desc>
  </wpt>
</gpx>"""

    st.code(gpx_template, language="xml")
    
    st.download_button(
        label="📥 Download .GPX File for onX Maps",
        data=gpx_template,
        file_name=f"cryptid_target_{lat_input}_{lon_input}.gpx",
        mime="application/gpx+xml"
    )
