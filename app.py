import streamlit as st
import pandas as pd
import time
import os
import io
import csv
from datetime import datetime

# Must be the first Streamlit command
st.set_page_config(
    page_title="Prospect Finder",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🕵️ Prospect Finder")
    st.markdown("Enter the team password to continue.")

    password = st.text_input("Password", type="password", label_visibility="collapsed")
    expected = st.secrets.get("password", os.environ.get("PROSPECT_PASSWORD", ""))

    if password:
        if password == expected:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False


if not check_password():
    st.stop()

# ─── APP STATE ─────────────────────────────────────────────────────────────────
if "scan_running" not in st.session_state:
    st.session_state.scan_running = False
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "scan_stats" not in st.session_state:
    st.session_state.scan_stats = None
if "scan_history" not in st.session_state:
    st.session_state.scan_history = []
if "stop_flag" not in st.session_state:
    st.session_state.stop_flag = False
if "scan_stopped" not in st.session_state:
    st.session_state.scan_stopped = False
if "partial_count" not in st.session_state:
    st.session_state.partial_count = 0
if "scan_message" not in st.session_state:
    st.session_state.scan_message = ""


def stop_scan():
    st.session_state.stop_flag = True
    st.session_state.scan_stopped = True


def reset_scan():
    st.session_state.scan_running = False
    st.session_state.scan_results = None
    st.session_state.scan_stats = None
    st.session_state.stop_flag = False
    st.session_state.scan_stopped = False
    st.session_state.partial_count = 0
    st.session_state.scan_message = ""
    st.session_state.scan_state = None


# ─── GET API KEYS ────────────────────────────────────────────────────────────────
def get_api_key():
    return st.secrets.get("google_api_key", os.environ.get("GOOGLE_API_KEY", ""))

def get_geoapify_key():
    return st.secrets.get("geoapify_key", os.environ.get("GEOAPIFY_KEY", ""))

def get_google_cx():
    return st.secrets.get("google_cx", os.environ.get("GOOGLE_CX", ""))

def get_serpapi_key():
    return st.secrets.get("serpapi_key", os.environ.get("SERPAPI_KEY", ""))


# ─── DEMO DATA ─────────────────────────────────────────────────────────────────
def load_demo_data():
    sample = [
        {"name": "Glow Aesthetics Studio", "category": "med spa", "city": "Frisco", "state": "TX", "country": "US",
         "phone": "(469) 555-0123", "website": "", "rating": 4.7, "review_count": 43,
         "emails": ["hello@glowaesthetics.com"], "linkedin": "https://linkedin.com/company/glow-aesthetics",
         "instagram": "https://instagram.com/glowaesthetics", "facebook": "https://facebook.com/glowaesthetics",
         "has_website": False, "lead_priority": "Hot", "email_source": "DuckDuckGo",
         "enrichment_notes": "Email found, no website"},
        {"name": "Radiant Skin Med Spa", "category": "med spa", "city": "Frisco", "state": "TX", "country": "US",
         "phone": "(972) 555-0456", "website": "https://radiantskinmedspa.com", "rating": 4.5, "review_count": 28,
         "emails": ["info@radiantskinmedspa.com"], "linkedin": "", "instagram": "https://instagram.com/radiantskinmedspa",
         "facebook": "https://facebook.com/radiantskinmedspa", "has_website": True, "lead_priority": "Hot",
         "email_source": "Website", "enrichment_notes": "Email found"},
        {"name": "Fresh Face Aesthetics", "category": "med spa", "city": "Scottsdale", "state": "AZ", "country": "US",
         "phone": "(480) 555-0789", "website": "", "rating": 4.9, "review_count": 112,
         "emails": [], "linkedin": "https://linkedin.com/in/jessica-freshface",
         "instagram": "https://instagram.com/freshfaceaz", "facebook": "",
         "has_website": False, "lead_priority": "Hot", "email_source": "",
         "enrichment_notes": "LinkedIn found, no website"},
        {"name": "Luxe Dermatology & Laser", "category": "med spa", "city": "Scottsdale", "state": "AZ", "country": "US",
         "phone": "(480) 555-0345", "website": "https://luxedermscottsdale.com", "rating": 4.8, "review_count": 87,
         "emails": ["contact@luxedermscottsdale.com"], "linkedin": "https://linkedin.com/company/luxe-dermatology",
         "instagram": "https://instagram.com/luxederm", "facebook": "https://facebook.com/luxederm",
         "has_website": True, "lead_priority": "Hot", "email_source": "Facebook",
         "enrichment_notes": "Email found"},
        {"name": "Chandler Beauty Lounge", "category": "med spa", "city": "Chandler", "state": "AZ", "country": "US",
         "phone": "(480) 555-0678", "website": "", "rating": 4.6, "review_count": 35,
         "emails": ["beautylounge.chandler@gmail.com"], "linkedin": "",
         "instagram": "https://instagram.com/chandlerbeautylounge", "facebook": "https://facebook.com/ChandlerBeautyLounge",
         "has_website": False, "lead_priority": "Hot", "email_source": "Instagram",
         "enrichment_notes": "Email found, no website"},
        {"name": "Elite Skin Studio", "category": "med spa", "city": "Chandler", "state": "AZ", "country": "US",
         "phone": "", "website": "", "rating": 4.4, "review_count": 18,
         "emails": [], "linkedin": "https://linkedin.com/in/elite-skin-studio",
         "instagram": "", "facebook": "https://facebook.com/EliteSkinStudio",
         "has_website": False, "lead_priority": "Hot", "email_source": "",
         "enrichment_notes": "LinkedIn + Facebook found, no website"},
        {"name": "Alpharetta Aesthetics Lab", "category": "med spa", "city": "Alpharetta", "state": "GA", "country": "US",
         "phone": "(678) 555-0901", "website": "https://alpharettaaesthetics.com", "rating": 4.3, "review_count": 22,
         "emails": ["hello@alpharettaaesthetics.com"], "linkedin": "", "instagram": "https://instagram.com/alphareaesthetics",
         "facebook": "", "has_website": True, "lead_priority": "Hot", "email_source": "Website",
         "enrichment_notes": "Email found"},
        {"name": "Peach State Medical Spa", "category": "med spa", "city": "Alpharetta", "state": "GA", "country": "US",
         "phone": "(770) 555-0234", "website": "", "rating": 4.1, "review_count": 9,
         "emails": ["peachstatemedspa@yahoo.com"], "linkedin": "", "instagram": "",
         "facebook": "https://facebook.com/PeachStateMedSpa", "has_website": False, "lead_priority": "Hot",
         "email_source": "DuckDuckGo", "enrichment_notes": "Email found, no website"},
        {"name": "Franklin Rejuvenation Center", "category": "med spa", "city": "Franklin", "state": "TN", "country": "US",
         "phone": "(615) 555-0567", "website": "", "rating": 4.8, "review_count": 56,
         "emails": [], "linkedin": "https://linkedin.com/company/franklin-rejuvenation",
         "instagram": "https://instagram.com/franklinrejuvenation", "facebook": "",
         "has_website": False, "lead_priority": "Hot", "email_source": "",
         "enrichment_notes": "LinkedIn + Instagram found, no website"},
        {"name": "Cool Springs Cosmetic Dentist", "category": "cosmetic dentistry", "city": "Franklin", "state": "TN", "country": "US",
         "phone": "(615) 555-0890", "website": "https://coolspringsdentist.com", "rating": 4.9, "review_count": 134,
         "emails": ["appointments@coolspringsdentist.com"], "linkedin": "",
         "instagram": "https://instagram.com/coolspringsdentist", "facebook": "https://facebook.com/CoolSpringsDentist",
         "has_website": True, "lead_priority": "Warm", "email_source": "DuckDuckGo",
         "enrichment_notes": "Email found"},
        {"name": "The London Facialist", "category": "med spa", "city": "London", "state": "UK", "country": "UK",
         "phone": "+44 20 5555 0123", "website": "", "rating": 4.6, "review_count": 41,
         "emails": ["info@thelondonfacialist.co.uk"], "linkedin": "", "instagram": "https://instagram.com/londonfacialist",
         "facebook": "https://facebook.com/TheLondonFacialist", "has_website": False, "lead_priority": "Hot",
         "email_source": "DuckDuckGo", "enrichment_notes": "Email found, no website"},
        {"name": "Sydney Skin Co.", "category": "med spa", "city": "Sydney", "state": "AU", "country": "AU",
         "phone": "+61 2 5555 6789", "website": "", "rating": 4.5, "review_count": 33,
         "emails": ["hello@sydneyskinco.com.au"], "linkedin": "https://linkedin.com/company/sydney-skin-co",
         "instagram": "https://instagram.com/sydneyskinco", "facebook": "",
         "has_website": False, "lead_priority": "Hot", "email_source": "Instagram",
         "enrichment_notes": "Email found, no website"},
        {"name": "Elara Medical Spa", "category": "med spa", "city": "Singapore", "state": "SG", "country": "SG",
         "phone": "+65 6789 0123", "website": "https://elaramedspa.sg", "rating": 4.7, "review_count": 62,
         "emails": ["contact@elaramedspa.sg"], "linkedin": "https://linkedin.com/company/elara-medical-spa",
         "instagram": "https://instagram.com/elaramedspa", "facebook": "https://facebook.com/ElaraMedicalSpa",
         "has_website": True, "lead_priority": "Warm", "email_source": "Website",
         "enrichment_notes": "Email found"},
        {"name": "Mumbai Aesthetic Clinic", "category": "med spa", "city": "Mumbai", "state": "IN", "country": "IN",
         "phone": "+91 22 5555 9876", "website": "", "rating": 4.3, "review_count": 27,
         "emails": ["care@mumbaiaesthetics.in"], "linkedin": "",
         "instagram": "https://instagram.com/mumbaiaesthetics", "facebook": "https://facebook.com/MumbaiAestheticClinic",
         "has_website": False, "lead_priority": "Hot", "email_source": "DuckDuckGo",
         "enrichment_notes": "Email found, no website"},
    ]

    stats = {
        "total_found": len(sample),
        "with_email": sum(1 for r in sample if r["emails"]),
        "with_phone": sum(1 for r in sample if r["phone"]),
        "no_website": sum(1 for r in sample if not r["has_website"]),
        "with_linkedin": sum(1 for r in sample if r["linkedin"]),
        "hot": sum(1 for r in sample if r["lead_priority"] == "Hot"),
        "deduped": 0,
        "skipped_no_contact": 0,
    }

    return sample, stats


# ─── UI ────────────────────────────────────────────────────────────────────────
st.title("🕵️ Prospect Finder")
st.caption("Discover businesses worldwide with enriched contact data. Finds email, LinkedIn, Instagram, Facebook, and phone.")

# Check API keys
api_key = get_api_key()
geoapify_key = get_geoapify_key()
serpapi_key = get_serpapi_key()
has_api_key = bool(api_key)
has_geoapify = bool(geoapify_key)
has_serpapi = bool(serpapi_key)
if not has_api_key and not has_geoapify:
    st.warning("⚠️ **No API keys found.** DuckDuckGo-only mode is limited. Set Google Places or Geoapify key in secrets for better results. Use **Load Demo Data** to test the UI.")

with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("Business Types")
    type_input = st.text_area(
        "One per line or comma-separated",
        height=80,
        label_visibility="collapsed",
        placeholder="e.g. dentist, home decor store, block print"
    )
    business_types = [t.strip() for t in type_input.replace("\n", ",").split(",") if t.strip()]

    st.subheader("Locations")
    st.caption("Format: City, State/Country (e.g. London, UK or Mumbai, IN)")
    loc_input = st.text_area(
        "One per line",
        height=130,
        label_visibility="collapsed",
        placeholder="London, UK\nNew York, NY, US\nMumbai, MH, IN"
    )
    locations = []
    for line in loc_input.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        city = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
        # Infer country from state
        us_states = {"TX", "AZ", "GA", "TN", "NC", "CA", "NY", "FL", "IL", "CO", "WA", "OR", "NV"}
        uk_cities = {"london", "manchester", "birmingham", "edinburgh", "glasgow", "bristol", "liverpool"}
        au_cities = {"sydney", "melbourne", "brisbane", "perth", "adelaide", "gold coast"}
        sg_cities = {"singapore"}
        in_cities = {"mumbai", "delhi", "bangalore", "pune", "hyderabad", "chennai", "kolkata", "ahmedabad"}

        if rest.upper() in us_states:
            country = "US"
            state = rest.upper()
        elif rest.upper() in ("UK", "GB", "UNITED KINGDOM") or city.lower() in uk_cities:
            country = "UK"
            state = rest.upper() if rest.upper() not in ("GB", "UNITED KINGDOM") else "UK"
        elif rest.upper() in ("AU", "AUS", "AUSTRALIA") or city.lower() in au_cities:
            country = "AU"
            state = rest.upper() if rest.upper() not in ("AUS", "AUSTRALIA") else "AU"
        elif rest.upper() in ("SG", "SINGAPORE") or city.lower() in sg_cities:
            country = "SG"
            state = rest.upper() if rest.upper() != "SINGAPORE" else "SG"
        elif rest.upper() in ("IN", "INDIA") or city.lower() in in_cities:
            country = "IN"
            state = rest.upper() if rest.upper() != "INDIA" else "IN"
        elif rest:
            country = rest.upper()
            state = rest.upper()
        else:
            country = "US"
            state = ""

        locations.append({"city": city, "state": state, "country": country})

    # Country indicators for each location
    country_emojis = {"US": "🇺🇸", "UK": "🇬🇧", "AU": "🇦🇺", "SG": "🇸🇬", "IN": "🇮🇳"}
    for loc in locations:
        emoji = country_emojis.get(loc["country"], "🌍")
        st.caption(f"  {emoji} {loc['city']}, {loc['state']} ({loc['country']})")

    st.divider()

    st.subheader("Dedup (optional)")
    uploaded_file = st.file_uploader(
        "Upload existing CSV to avoid duplicates",
        type=["csv"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        st.session_state.uploaded_csv = uploaded_file
        st.success(f"✅ Loaded: {uploaded_file.name}")
    else:
        st.session_state.uploaded_csv = None

    st.divider()

    if has_geoapify:
        st.caption("✅ Geoapify key detected — fast discovery enabled")
    st.session_state.geoapify_key = geoapify_key

    if has_serpapi:
        st.caption("✅ SerpAPI key detected — extra discovery & enrichment")
    st.session_state.serpapi_key = serpapi_key

    st.divider()

    google_cx = get_google_cx()
    has_cx = bool(google_cx)
    st.subheader("🔍 Custom Web Search")
    custom_query = st.text_area(
        "Google Custom Search query (100/day free)",
        height=60,
        label_visibility="collapsed",
        placeholder='e.g. site:etsy.com "block print" bedcovers',
        help="Uses Google Custom Search API. CX key must be set in secrets."
    )
    if not has_cx:
        st.caption("⚠️ Set `google_cx` in secrets to enable")
    elif custom_query.strip():
        st.caption(f"Will search: {custom_query[:60]}")
    st.session_state.custom_query = custom_query.strip() if has_cx else ""
    st.session_state.google_cx = google_cx

    with st.expander("💡 Search ideas", expanded=False):
        st.markdown("""
**For block printing:**  
`"home decor" "block print" UK`  
`"textile shop" "block print" Instagram`  
`site:etsy.com "block print" bedcovers`  
`"boutique" "hand block print" Clothing`  

**For SaaS prospects:**  
`"Shopify store" email contact`  
`"ecommerce" founder LinkedIn UK`  
`"digital agency" "no CRM"`  
`"WordPress site" "email marketing"`  

**For content writing / blog outreach:**  
`"home decor" blog "write for us"`  
`"textile" magazine "guest post"`  
`"interior design" blog "contributor"`  

**For any business + email:**  
`"home decor store" London email`  
`site:facebook.com "textile shop" UK`  
""")

    st.divider()

    st.subheader("⛔ Blacklist Domains")
    blacklist_input = st.text_input(
        "Exclude these domains (comma-separated)",
        placeholder="competitor.com, etsy.com",
        label_visibility="collapsed",
    )
    st.session_state.blacklist_domains = [d.strip().lower() for d in blacklist_input.split(",") if d.strip()]

    st.divider()

    st.subheader("Max Leads")
    max_leads = st.number_input(
        "Max prospects per location (0 = unlimited)",
        min_value=0, max_value=100, value=10, step=5,
        label_visibility="collapsed",
        help="Limits how many prospects to enrich per city. Keeps scans fast.",
    )
    if max_leads:
        st.caption(f"⏱ Will process up to **{max_leads}** prospects per location")

    keep_no_contact = st.checkbox(
        "Keep businesses with no contact info",
        value=False,
        help="When checked, businesses without email/phone/website are kept in results.",
    )
    if keep_no_contact:
        st.caption("📋 Will include businesses missing email, phone, and website")

    st.divider()

    st.session_state.max_leads = max_leads

    col1, col2 = st.columns(2)
    with col1:
        enabled = not st.session_state.scan_running
        sources = []
        if has_api_key: sources.append("Google")
        if has_geoapify: sources.append("Geoapify")
        if has_serpapi: sources.append("SerpAPI")
        sources.append("DuckDuckGo")
        btn_label = f"🔍 Scan ({'+'.join(sources)})"
        start_btn = st.button(
            btn_label,
            type="primary",
            width="stretch",
            disabled=not enabled,
        )
    with col2:
        st.button(
            "⏹ Stop",
            on_click=stop_scan,
            width="stretch",
            disabled=not st.session_state.scan_running,
        )

    demo_btn = st.button(
        "🎲 Load Demo Data",
        width="stretch",
        disabled=st.session_state.scan_running,
    )

    if st.session_state.scan_running:
        st.button("🔄 Reset", on_click=reset_scan, width="stretch")

# ─── MAIN PANEL ────────────────────────────────────────────────────────────────

# Progress + live results area
scan_container = st.container()
live_container = st.container()
results_container = st.container()

# Demo button handler
if demo_btn:
    demo_results, demo_stats = load_demo_data()
    st.session_state.scan_running = False
    st.session_state.scan_results = demo_results
    st.session_state.scan_stats = demo_stats
    st.session_state.stop_flag = False
    st.session_state.partial_count = 0

    scan_record = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "types": "demo data",
        "locations": "US, UK, AU, SG, IN",
        "found": len(demo_results),
        "email": demo_stats["with_email"],
        "hot": demo_stats["hot"],
        "deduped": 0,
    }
    st.session_state.scan_history.append(scan_record)
    st.rerun()

# Scan logic
if start_btn:
    st.session_state.scan_running = True
    st.session_state.stop_flag = False
    st.session_state.scan_stopped = False
    st.session_state.scan_results = None
    st.session_state.scan_stats = None
    st.session_state.partial_count = 0
    st.session_state.scan_message = ""
    st.session_state.scan_state = None
    st.rerun()

if st.session_state.scan_running:
    api_key = get_api_key()

    tmp_csv = ""
    if st.session_state.uploaded_csv:
        tmp_path = f"/tmp/uploaded_prospects_{int(time.time())}.csv"
        with open(tmp_path, "wb") as f:
            f.write(st.session_state.uploaded_csv.getbuffer())
        tmp_csv = tmp_path

    from scraper import init_scan_state, run_scan_step, _scan_stop_event

    max_leads = st.session_state.get("max_leads", 10)

    with scan_container:
        progress_bar = st.progress(0, text="⏳ Initializing scan...")
        status_text = st.info("Preparing to discover businesses...")
        phase_text = st.empty()
        live_table = st.empty()

    # Initialize scan state on first run, resume on subsequent reruns
    if "scan_state" not in st.session_state or st.session_state.scan_state is None:
        st.session_state.scan_state = init_scan_state(
            api_key=api_key,
            business_types=business_types,
            locations=locations,
            existing_csv_path=tmp_csv,
            max_leads=max_leads or 0,
            geoapify_key=geoapify_key,
            serpapi_key=serpapi_key,
            keep_no_contact=keep_no_contact,
            google_cx=st.session_state.get("google_cx", ""),
            custom_query=st.session_state.get("custom_query", ""),
            blacklist_domains=st.session_state.get("blacklist_domains", []),
        )

    state = st.session_state.scan_state

    # Check stop before each step
    if st.session_state.stop_flag:
        _scan_stop_event.set()
        state.step = "stopped"
        from scraper import _complete
        update = _complete(state)
    else:
        update = run_scan_step(state, stop_flag=lambda: st.session_state.stop_flag)

    t = update["type"]

    if t == "status":
        status_text.info(update["message"])
        st.session_state.scan_message = update["message"]
        st.rerun()

    elif t == "phase":
        progress_bar.progress(min(update.get("progress", 0), 1.0), text=update["message"])
        phase = update.get("phase", 1)
        label = "📡 Phase 1: Discovering..." if phase == 1 else "🔎 Phase 2: Enriching..."
        phase_text.info(label)
        status_text.info(update["message"])
        st.rerun()

    elif t == "enrichment_progress":
        result = update.get("result")
        if result:
            st.session_state.partial_count = len(state.all_results)

        waiting = " ⏹ Stopping..." if st.session_state.stop_flag else ""
        meta = f"Found {len(state.all_results)} enriched prospects so far{waiting}"

        if state.all_results:
            preview = state.all_results[-15:]
            rows = []
            for r in preview:
                rows.append({
                    "🔥": "🔥" if r["lead_priority"] == "Hot" else "👍",
                    "Business": r["name"][:35],
                    "Email": r["emails"][0] if r["emails"] else "—",
                    "Phone": r["phone"] or "—",
                    "LI": "✅" if r["linkedin"] else "",
                    "FB/IG": "✅" if r["facebook"] or r["instagram"] else "",
                })
            live_table.dataframe(
                rows,
                width="stretch",
                height=min(420, 28 * len(rows) + 28),
                column_config={
                    "🔥": st.column_config.TextColumn(width="small"),
                    "Business": st.column_config.TextColumn(width="medium"),
                    "Email": st.column_config.TextColumn(width="medium"),
                },
            )
        else:
            live_table.caption(meta)

        if tmp_csv and os.path.exists(tmp_csv):
            os.remove(tmp_csv)
        st.rerun()

    elif t == "error":
        status_text.error(update["message"])
        st.rerun()

    elif t == "complete":
        results = update["results"]
        stats = update["stats"]
        st.session_state.scan_results = results
        st.session_state.scan_stats = stats
        st.session_state.scan_running = False
        st.session_state.partial_count = len(results)
        st.session_state.scan_state = None
        # scan_stopped persists for "stopped" banner; clear only on normal completion
        if not st.session_state.stop_flag:
            st.session_state.scan_stopped = False

        scan_record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "types": ", ".join(business_types),
            "locations": ", ".join([f"{l['city']}, {l['state']}" for l in locations]),
            "found": stats["total_found"],
            "email": stats["with_email"],
            "hot": stats["hot"],
            "deduped": stats["deduped"],
        }
        st.session_state.scan_history.append(scan_record)

        if tmp_csv and os.path.exists(tmp_csv):
            os.remove(tmp_csv)
        st.rerun()


# ─── RESULTS DISPLAY ───────────────────────────────────────────────────────────
if st.session_state.scan_results is not None:
    results = st.session_state.scan_results
    stats = st.session_state.scan_stats

    with results_container:
        st.divider()

        if not results:
            if st.session_state.scan_stopped:
                st.info("⏹ Scan stopped before any prospects were found. Try again with different settings or wait longer.")
            else:
                st.warning("No prospects found. Try different locations or business types.")
        else:
            if st.session_state.scan_stopped:
                st.info(f"⏹ Scan stopped — showing {len(results)} partial results.")
            st.subheader("📊 Results")

        if results:
            # Summary cards
            kpi_cols = st.columns(6)
            with kpi_cols[0]:
                st.metric("Total Prospects", stats["total_found"])
            with kpi_cols[1]:
                pct = f"{stats['with_email'] / stats['total_found'] * 100:.0f}%" if stats["total_found"] else "0%"
                st.metric("📧 With Email", stats["with_email"], pct)
            with kpi_cols[2]:
                st.metric("🔥 Hot Leads", stats["hot"])
            with kpi_cols[3]:
                st.metric("🌐 No Website", stats["no_website"])
            with kpi_cols[4]:
                st.metric("🔗 With LinkedIn", stats["with_linkedin"])
            with kpi_cols[5]:
                st.metric("📞 With Phone", stats["with_phone"])

            if stats["deduped"]:
                st.caption(f"⏭ {stats['deduped']} duplicates skipped")
            if stats["skipped_no_contact"]:
                st.caption(f"⏭ {stats['skipped_no_contact']} excluded (no contact info)")

            # Build DataFrame
            df_rows = []
            for r in results:
                df_rows.append({
                    "🔥 Priority": "🔥" if r["lead_priority"] == "Hot" else "👍",
                    "Business Name": r["name"],
                    "Contact": f"{r.get('contact_person', '')}" + (f" ({r.get('contact_title', '')})" if r.get('contact_title') else ""),
                    "Category": r["category"].title(),
                    "City": r["city"],
                    "State": r["state"],
                    "Country": r["country"],
                    "📧 Email": r["emails"][0] if r["emails"] else "",
                    "🔗 LinkedIn": r["linkedin"],
                    "📸 Instagram": r["instagram"],
                    "📘 Facebook": r["facebook"],
                    "📞 Phone": r["phone"],
                    "🌐 Website": r["website"] if r["has_website"] else "❌ No website",
                    "⭐ Rating": r["rating"] if r["rating"] else "",
                    "📝 Reviews": r["review_count"],
                    "Email Source": r["email_source"],
                    "Notes": r["enrichment_notes"],
                })

            df = pd.DataFrame(df_rows)

            st.dataframe(
                df,
                width="stretch",
                height=min(400, 40 * len(df_rows) + 40),
                column_config={
                    "🔥 Priority": st.column_config.TextColumn(width="small"),
                    "Business Name": st.column_config.TextColumn(width="medium"),
                    "📧 Email": st.column_config.TextColumn(width="medium"),
                    "🌐 Website": st.column_config.TextColumn(width="medium"),
                    "📞 Phone": st.column_config.TextColumn(width="medium"),
                },
            )

            # Export
            st.divider()
            st.subheader("📥 Export")

            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()

            export_col1, export_col2 = st.columns(2)
            with export_col1:
                st.download_button(
                    label="📥 Download Full CSV",
                    data=csv_data,
                    file_name=f"prospects_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    width="stretch",
                )

            import_rows = []
            for i, r in enumerate(results, 1):
                emails = "; ".join(r["emails"]) if r["emails"] else ""
                import_rows.append({
                    "#": i,
                    "CATEGORY": r["category"].title(),
                    "CITY": r["city"],
                    "STATE": r["state"],
                    "TIER": 1,
                    "CLINIC NAME": r["name"],
                    "CONTACT PERSON": r.get("contact_person", ""),
                    "TITLE": r.get("contact_title", ""),
                    "EMAIL": emails,
                    "PHONE": r["phone"],
                    "WEBSITE": r["website"],
                    "LINKEDIN (Person)": r.get("linkedin_person", ""),
                    "LINKEDIN (Company)": r.get("linkedin_company", "") or r.get("linkedin", ""),
                    "INSTAGRAM": r["instagram"],
                    "FACEBOOK": r["facebook"],
                    "LEAD PRIORITY": r["lead_priority"],
                    "NOTES": r["enrichment_notes"],
                })

            import_df = pd.DataFrame(import_rows)
            import_csv = import_df.to_csv(index=False)

            with export_col2:
                st.download_button(
                    label="📥 Download Import-Ready CSV",
                    data=import_csv,
                    file_name=f"prospects_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    width="stretch",
                )

            # Hot leads quick view
            hot_df = df[df["🔥 Priority"] == "🔥"].copy()
            if not hot_df.empty:
                st.divider()
                st.subheader("🔥 Hot Leads")
                st.dataframe(hot_df, width="stretch", height=min(300, 40 * len(hot_df) + 40))

elif not st.session_state.scan_running:
    with results_container:
        st.divider()
        if has_api_key:
            st.info("👈 Configure your search in the sidebar and click **Start Scan**.")
        else:
            st.info("👈 Click **🎲 Load Demo Data** to test the full UI with sample prospects. Add your Google API key to run real scans.")

# ─── HISTORY ────────────────────────────────────────────────────────────────────
with st.sidebar:
    if st.session_state.scan_history:
        st.divider()
        st.subheader("📋 Scan History")
        for h in reversed(st.session_state.scan_history[-10:]):
            st.caption(
                f"{h['timestamp']} — {h['locations'][:40]}...\n"
                f"  → {h['found']} found, {h['email']} emails, {h['hot']} hot"
            )
