# ==========================================
# TAB 2: RESEARCH LIBRARY & SOURCE VAULT
# ==========================================
with tab_library:
    st.header("📚 Research Library & Analytical Vault")
    
    lib_choice = st.radio(
        "Select Vault Section:", 
        ["🔊 Infrasound & Acoustic Physics", "👣 BFRO Sightings Vault", "🪶 Indigenous Ethnographic Lore", "📰 Historical Press Archives", "🦉 Bioacoustics Guide"], 
        horizontal=True
    )

    st.markdown("---")

    # --------------------------------------------------
    # 1. INFRASOUND (CLEAN PARAGRAPH FORMATTING)
    # --------------------------------------------------
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
            "valleys or as a acoustic deterrent against competitors."
        )

        st.markdown("### 4. Human Physiological & Neurological Effects")
        st.write(
            "When humans enter an active infrasound envelope without realization, the body reacts physically even though the ears hear nothing. "
            "Frequencies between 1 and 7 Hz match the internal resonance of human inner ear fluid, causing sudden dizziness, micro-barometric "
            "headaches, and disorientation. Frequencies between 7 and 12 Hz overlap with human brain alpha waves, inducing acute hyper-vigilance, "
            "irrational fear, and a strong sense of being watched. Frequencies around 19 Hz match the resonant frequency of the human eyeball, "
            "causing subtle ocular vibrations that create peripheral optical smears or shadow-like visual distortions."
        )

    # --------------------------------------------------
    # 2. BFRO SIGHTINGS WITH DIRECT LINKS
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 3. INDIGENOUS LORE
    # --------------------------------------------------
    elif "Lore" in lib_choice:
        st.subheader("🪶 Indigenous Ethnographic Lore & Land Anchors")
        st.write("Regional tribal records documenting wilderness hominid entities:")
        for item in lore_data:
            st.markdown(f"#### {item.get('tribe_name')} — *{item.get('entity_name')}*")
            st.write(f"**Region:** `{item.get('region_label')}` | **Evidence Weight:** `{item.get('evidence_weight', 1.5)}x`")
            st.write(item.get("full_narrative"))
            st.markdown("---")

    # --------------------------------------------------
    # 4. HISTORICAL PRESS ARCHIVES
    # --------------------------------------------------
    elif "Press Archives" in lib_choice:
        st.subheader("📰 Historical Press Archives")
        for item in media_data:
            pub_name = item.get('publication_name', item.get('source', 'Historical Archive'))
            st.markdown(f"#### {item.get('title')} ({item.get('pub_date')})")
            st.write(f"**Source:** `{pub_name}` | **Location:** {item.get('county', 'N/A')}, {item.get('state', 'N/A')}")
            st.write(f"> {item.get('full_text_transcript')}")
            st.markdown("---")

    # --------------------------------------------------
    # 5. BIOACOUSTICS
    # --------------------------------------------------
    elif "Bioacoustics" in lib_choice:
        st.subheader("🦉 Bioacoustics & Fauna Repertoires")
        st.markdown(
            "* **Barred Owl (*Strix varia*):** Produces caterwauls, screams, and multi-tone hoots.\n"
            "* **Eastern Coyote (*Canis latrans*):** High-pitched yips and howl-harmonics across valley floors.\n"
            "* **Red Fox (*Vulpes vulpes*):** Unsettling night alarm screams in the 1.5 kHz to 3.5 kHz range.\n"
            "* **White-Tailed Deer (*Odocoileus virginianus*):** Loud, explosive blowing snorts used as perimeter warnings."
        )
