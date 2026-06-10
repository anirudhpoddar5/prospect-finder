import streamlit as st
import pandas as pd
import time
import os
import io
import csv
from datetime import datetime

st.set_page_config(
    page_title="Prospect Finder",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CUSTOM CSS - MATRIX HACKER THEME ────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&display=swap');

    * { font-family: 'JetBrains Mono', monospace; }

    /* ─── MATRIX RAIN ────────────────────────────────────────────────────── */
    .matrix-rain {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        overflow: hidden; z-index: 0; pointer-events: none;
        background: #0A0D14;
    }
    .rain-column {
        position: absolute; top: -120%;
        writing-mode: vertical-lr;
        text-orientation: upright;
        font-family: 'JetBrains Mono', monospace;
        font-size: 14px;
        line-height: 1;
        color: rgba(0, 255, 136, 0.45);
        white-space: nowrap;
        animation: matrixRain linear infinite;
        user-select: none;
        letter-spacing: 2px;
    }
    @keyframes matrixRain {
        0% { transform: translateY(-100%); opacity: 0; }
        8% { opacity: 0.6; }
        85% { opacity: 0.6; }
        100% { transform: translateY(110vh); opacity: 0; }
    }
    @keyframes blink {
        50% { opacity: 0; }
    }
    /* ─── LOGIN CARD (style Streamlit container as glowing terminal card) ── */
    div[data-testid="stVerticalBlock"]:has(.login-dots) {
        background: linear-gradient(135deg, #131720 0%, #1A2030 100%);
        border: 1px solid #00FF88;
        border-radius: 12px;
        padding: 32px 36px 24px;
        box-shadow: 0 0 40px rgba(0,255,136,0.15), 0 0 80px rgba(0,255,136,0.05);
        width: 100%;
        max-width: 460px;
        margin: 15vh auto 0;
    }
    .login-dots {
        display: flex; align-items: center; gap: 8px; margin-bottom: 20px;
    }
    .login-dots span {
        width: 12px; height: 12px; border-radius: 50%;
    }
    .login-dots .r { background: #FF3355; }
    .login-dots .y { background: #FFD700; }
    .login-dots .g { background: #00FF88; }
    .login-dots .title {
        color: #808080; font-size: 11px; margin-left: 4px; flex: 1;
    }
    div[data-testid="stVerticalBlock"]:has(.login-dots) input {
        background: #0A0D14 !important;
        border: 1px solid #00FF88 !important;
        border-radius: 6px !important;
        color: #00FF88 !important;
        font-size: 20px !important;
        padding: 12px !important;
        text-align: center !important;
        letter-spacing: 8px !important;
        caret-color: #00FF88 !important;
        box-shadow: 0 0 10px rgba(0,255,136,0.1) !important;
    }
    div[data-testid="stVerticalBlock"]:has(.login-dots) input:focus {
        box-shadow: 0 0 25px rgba(0,255,136,0.4) !important;
        border-color: #00FF88 !important;
    }

    /* Glass card */
    .glass-card {
        background: #131720;
        border: 1px solid #2A3040;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 16px;
        transition: border-color 0.3s;
    }
    .glass-card:hover { border-color: #00FF88; }

    /* Terminal window card */
    .terminal-card {
        background: #0D1117;
        border: 1px solid #1E2330;
        border-radius: 8px;
        overflow: hidden;
        margin-bottom: 16px;
    }
    .terminal-card .term-header {
        background: #1E2330;
        padding: 8px 16px;
        display: flex; align-items: center; gap: 8px;
        border-bottom: 1px solid #2A3040;
    }
    .terminal-card .term-header .dot {
        width: 10px; height: 10px; border-radius: 50%;
    }
    .terminal-card .term-body {
        padding: 16px;
        font-size: 13px;
    }
    .terminal-card .term-body .line {
        color: #C0C0C0; margin: 4px 0;
    }
    .terminal-card .term-body .line-green { color: #00FF88; }
    .terminal-card .term-body .line-cyan { color: #00D4FF; }
    .terminal-card .term-body .line-red { color: #FF3355; }
    .terminal-card .term-body .prompt { color: #00FF88; }

    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #131720 0%, #1A2030 100%);
        border: 1px solid #2A3040;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        transition: border-color 0.3s;
    }
    .kpi-card:hover { border-color: #00FF88; }
    .kpi-card .kpi-value {
        font-size: 28px; font-weight: 700; color: #00FF88;
        text-shadow: 0 0 10px rgba(0,255,136,0.3);
    }
    .kpi-card .kpi-label {
        font-size: 11px; color: #808080; margin-top: 4px;
        text-transform: uppercase; letter-spacing: 1px;
    }
    .kpi-card .kpi-delta {
        font-size: 12px; margin-top: 4px;
    }

    /* Status dots */
    .status-dot {
        display: inline-block; width: 8px; height: 8px; border-radius: 50%;
        margin-right: 6px; vertical-align: middle;
    }
    .status-dot.green { background: #00FF88; box-shadow: 0 0 6px #00FF88; }
    .status-dot.red { background: #FF3355; box-shadow: 0 0 6px #FF3355; }
    .status-dot.gray { background: #404040; }

    /* Hot badge */
    .hot-badge {
        display: inline-block;
        background: rgba(255,51,85,0.15);
        color: #FF3355;
        border: 1px solid rgba(255,51,85,0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }
    .warm-badge {
        display: inline-block;
        background: rgba(255,215,0,0.15);
        color: #FFD700;
        border: 1px solid rgba(255,215,0,0.3);
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    /* Scan button */
    .stButton button {
        font-family: 'JetBrains Mono', monospace !important;
        font-weight: 700 !important;
        letter-spacing: 2px !important;
    }
    div[data-testid="column"] .stButton button {
        width: 100%;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #808080 !important;
        border-bottom: 1px solid #2A3040;
        padding-bottom: 6px;
        margin-top: 16px;
    }

    /* Override Streamlit defaults */
    .stApp { background: #0A0D14; }
    section[data-testid="stSidebar"] { background: #0D1117; border-right: 1px solid #1E2330; }
    section[data-testid="stSidebar"] .stTextInput input,
    section[data-testid="stSidebar"] .stTextArea textarea,
    section[data-testid="stSidebar"] .stNumberInput input {
        background: #0A0D14 !important;
        border-color: #2A3040 !important;
        color: #C0C0C0 !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .stProgress > div > div > div > div {
        background: #00FF88 !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 28px !important;
        color: #00FF88 !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 12px !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stTabs [aria-selected="true"] {
        color: #00FF88 !important;
    }

    /* Table */
    [data-testid="StyledDataFrameDataTable"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Dividers */
    hr { border-color: #2A3040 !important; }

    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: #0A0D14; }
    ::-webkit-scrollbar-thumb { background: #2A3040; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #00FF88; }
</style>
""", unsafe_allow_html=True)

# ─── AUTH ─────────────────────────────────────────────────────────────────────
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    # ── Matrix rain background (generated once per session) ──
    if "matrix_rain" not in st.session_state:
        cols_html = []
        chars = []
        for c in range(0xFF66, 0xFF9F):
            chars.append(chr(c))
        for c in range(0x30A0, 0x30FF):
            chars.append(chr(c))
        chars.extend("0123456789:-*+#$%&@")
        n = len(chars)
        for i in range(40):
            col_chars = "".join(chars[(i * 7 + j * 13) % n] for j in range(30))
            dur = round(7 + (i % 5) * 0.8, 1)
            delay = round((i % 12) * 0.7, 1)
            left = round((i / 40) * 98 + 0.5, 1)
            cols_html.append(
                f'<div class="rain-column" style="left:{left}%;'
                f'animation-duration:{dur}s;animation-delay:{delay}s;">{col_chars}</div>'
            )
        st.session_state.matrix_rain = (
            '<div class="matrix-rain">' + "".join(cols_html) + "</div>"
        )

    st.markdown(st.session_state.matrix_rain, unsafe_allow_html=True)

    # ── Login card (Streamlit container styled via CSS :has(.login-dots)) ──
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div class="login-dots">
            <span class="r"></span><span class="y"></span><span class="g"></span>
            <span class="title">prospect_finder.exe</span>
        </div>
        <h1 style="text-align:center;color:#00FF88;font-size:24px;font-weight:700;margin-bottom:4px;margin-top:0;text-shadow:0 0 15px rgba(0,255,136,0.4);">🕵️ PROSPECT FINDER</h1>
        <p style="text-align:center;color:#00FF88;font-size:12px;opacity:0.6;margin-bottom:0;">$ SECURE TERMINAL v1.0 — AUTHORIZATION REQUIRED</p>
        <p style="text-align:center;color:#808080;font-size:11px;margin-top:24px;margin-bottom:6px;">$ enter password:</p>
        """, unsafe_allow_html=True)

        password = st.text_input("Password", type="password", label_visibility="collapsed", placeholder="")

        expected = st.secrets.get("password", os.environ.get("PROSPECT_PASSWORD", ""))
        if password:
            if password == expected:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.markdown("""
                <div style="text-align:center;padding:8px;border:1px solid rgba(255,51,85,0.3);border-radius:6px;background:rgba(255,51,85,0.08);margin-top:10px;">
                    <span style="color:#FF3355;font-size:13px;">✗ ACCESS DENIED — INCORRECT PASSWORD</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
        <p style="text-align:center;color:#00FF88;font-size:12px;opacity:0.5;margin-top:16px;">
            $ access --grant <span style="display:inline-block;width:8px;height:15px;background:#00FF88;animation:blink 1s step-end infinite;vertical-align:middle;margin-left:4px;"></span>
        </p>
        """, unsafe_allow_html=True)

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


# ─── CHECK API KEYS ──────────────────────────────────────────────────────────────
api_key = get_api_key()
geoapify_key = get_geoapify_key()
serpapi_key = get_serpapi_key()
google_cx = get_google_cx()
has_api_key = bool(api_key)
has_geoapify = bool(geoapify_key)
has_serpapi = bool(serpapi_key)
has_cx = bool(google_cx)

# ─── MAIN HEADER ─────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
    <span style="font-size:28px;">🕵️</span>
    <span style="font-size:22px;font-weight:700;color:#00FF88;text-shadow:0 0 10px rgba(0,255,136,0.3);">PROSPECT FINDER</span>
    <span style="font-size:11px;color:#404040;margin-left:auto;">v1.0</span>
</div>
""", unsafe_allow_html=True)


# ─── SIDEBAR ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <h3 style="margin-top:0;">🔑 STATUS</h3>
    """, unsafe_allow_html=True)

    api_status = []
    api_status.append(f'<span class="status-dot {"green" if has_api_key else "red"}"></span> Google Places {"✅" if has_api_key else "❌"}')
    api_status.append(f'<span class="status-dot {"green" if has_geoapify else "gray"}"></span> Geoapify {"✅" if has_geoapify else "—"}')
    api_status.append(f'<span class="status-dot {"green" if has_serpapi else "gray"}"></span> SerpAPI {"✅" if has_serpapi else "—"}')
    api_status.append(f'<span class="status-dot {"green" if has_cx else "gray"}"></span> Custom Search {"✅" if has_cx else "—"}')

    st.markdown(
        '<div style="font-size:12px;line-height:2;">' + "<br>".join(api_status) + "</div>",
        unsafe_allow_html=True
    )

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── TARGET ──────────────────────────────────────────────────────────────────
    st.markdown("<h3>🎯 TARGET</h3>", unsafe_allow_html=True)

    type_input = st.text_area(
        "Business Types",
        height=80,
        label_visibility="collapsed",
        placeholder="dentist, med spa, chiropractor"
    )
    business_types = [t.strip() for t in type_input.replace("\n", ",").split(",") if t.strip()]

    loc_input = st.text_area(
        "Locations (City, State)",
        height=100,
        label_visibility="collapsed",
        placeholder="Austin, TX\nScottsdale, AZ\nLondon, UK"
    )
    locations = []
    for line in loc_input.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in line.split(",")]
        city = parts[0]
        rest = parts[1].strip() if len(parts) > 1 else ""
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

    if locations:
        country_emojis = {"US": "🇺🇸", "UK": "🇬🇧", "AU": "🇦🇺", "SG": "🇸🇬", "IN": "🇮🇳"}
        loc_preview = " &nbsp;| ".join(
            f"{country_emojis.get(l['country'], '🌍')} {l['city']}" for l in locations[:5]
        )
        st.markdown(f'<div style="font-size:11px;color:#808080;">{loc_preview}</div>', unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── CUSTOM SEARCH ────────────────────────────────────────────────────────────
    st.markdown("<h3>🌐 CUSTOM SEARCH</h3>", unsafe_allow_html=True)
    custom_query = st.text_area(
        "Google Custom Search query",
        height=60,
        label_visibility="collapsed",
        placeholder='site:etsy.com "block print" bedcovers',
        help="Requires google_cx in secrets"
    )
    if not has_cx:
        st.markdown('<div style="font-size:11px;color:#FF3355;">⚠️ CX key not set in secrets</div>', unsafe_allow_html=True)
    elif custom_query.strip():
        st.markdown(f'<div style="font-size:11px;color:#00D4FF;">$ will search: {custom_query[:60]}</div>', unsafe_allow_html=True)
    st.session_state.custom_query = custom_query.strip() if has_cx else ""
    st.session_state.google_cx = google_cx

    with st.expander("💡 Search ideas"):
        st.markdown("""
`"home decor" "block print" UK`  
`site:etsy.com "block print" bedcovers`  
`"Shopify store" email contact`  
`"ecommerce" founder LinkedIn UK`
""")

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── FILTERS ───────────────────────────────────────────────────────────────────
    st.markdown("<h3>⛔ FILTERS</h3>", unsafe_allow_html=True)

    blacklist_input = st.text_input(
        "Exclude domains",
        placeholder="competitor.com, etsy.com",
        label_visibility="collapsed",
    )
    st.session_state.blacklist_domains = [d.strip().lower() for d in blacklist_input.split(",") if d.strip()]

    max_leads = st.number_input(
        "Max per location",
        min_value=0, max_value=100, value=10, step=5,
        label_visibility="collapsed",
    )
    if max_leads:
        st.markdown(f'<div style="font-size:11px;color:#808080;">⏱ {max_leads} prospects per city</div>', unsafe_allow_html=True)

    st.checkbox(
        "Keep no-contact entries",
        value=False,
        key="keep_no_contact",
    )

    st.session_state.max_leads = max_leads

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── DEDUP ─────────────────────────────────────────────────────────────────────
    st.markdown("<h3>📂 DEDUP</h3>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "Upload existing CSV to skip duplicates",
        type=["csv"],
        label_visibility="collapsed",
    )
    if uploaded_file:
        st.session_state.uploaded_csv = uploaded_file
        st.markdown(f'<div style="font-size:11px;color:#00FF88;">$ Loaded: {uploaded_file.name}</div>', unsafe_allow_html=True)
    else:
        st.session_state.uploaded_csv = None

    st.markdown("<hr>", unsafe_allow_html=True)

    # ── SCAN / STOP BUTTONS ──────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        enabled = not st.session_state.scan_running
        start_btn = st.button(
            "🖥 SCAN",
            type="primary",
            use_container_width=True,
            disabled=not enabled,
        )
    with col2:
        st.button(
            "⏹ STOP",
            use_container_width=True,
            disabled=not st.session_state.scan_running,
            on_click=stop_scan,
        )

    if st.session_state.scan_running:
        st.button("🔄 RESET", use_container_width=True, on_click=reset_scan)

    # ── HISTORY ──────────────────────────────────────────────────────────────────
    if st.session_state.scan_history:
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3>📋 HISTORY</h3>", unsafe_allow_html=True)
        for h in reversed(st.session_state.scan_history[-5:]):
            st.markdown(
                f'<div style="font-size:11px;color:#808080;border-left:2px solid #00FF88;padding-left:8px;margin:6px 0;">'
                f'<span style="color:#00FF88;">$</span> {h["timestamp"]}<br>'
                f'  → {h["found"]} leads · {h["email"]} 📧 · {h["hot"]} 🔥'
                f'</div>',
                unsafe_allow_html=True
            )

# ─── MAIN PANEL ────────────────────────────────────────────────────────────────
scan_container = st.container()
live_container = st.container()
results_container = st.container()

# ─── SCAN LOGIC ─────────────────────────────────────────────────────────────────
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
    keep_no_contact = st.session_state.get("keep_no_contact", False)

    with scan_container:
        status_box = st.container()
        progress_bar = st.progress(0, text="⏳ Initializing...")
        phase_text = st.empty()
        live_table = st.empty()

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

    if st.session_state.stop_flag:
        _scan_stop_event.set()
        state.step = "stopped"
        from scraper import _complete
        update = _complete(state)
    else:
        update = run_scan_step(state, stop_flag=lambda: st.session_state.stop_flag)

    t = update["type"]

    if t == "status":
        with status_box:
            st.markdown(f'<div style="font-size:13px;"><span style="color:#00FF88;">$</span> {update["message"]}</div>', unsafe_allow_html=True)
        st.session_state.scan_message = update["message"]
        st.rerun()

    elif t == "phase":
        progress_bar.progress(min(update.get("progress", 0), 1.0), text=update["message"])
        phase = update.get("phase", 1)
        label = "📡 SCANNING..." if phase == 1 else "🔎 ENRICHING..."
        phase_text.markdown(f'<div style="color:#00FF88;font-weight:600;font-size:14px;">$ {label}</div>', unsafe_allow_html=True)
        st.rerun()

    elif t == "enrichment_progress":
        result = update.get("result")
        if result:
            st.session_state.partial_count = len(state.all_results)

        waiting = " ⏹ ABORTING..." if st.session_state.stop_flag else ""
        meta = f"$ {len(state.all_results)} prospects enriched{waiting}"

        if state.all_results:
            preview = state.all_results[-15:]
            rows = []
            for r in preview:
                priority_badge = "🔥" if r["lead_priority"] == "Hot" else "👍"
                rows.append({
                    "": priority_badge,
                    "BUSINESS": r["name"][:35],
                    "EMAIL": r["emails"][0] if r["emails"] else "—",
                    "PHONE": r["phone"] or "—",
                    "LI": "✅" if r["linkedin"] else "",
                    "SOCIAL": "✅" if r["facebook"] or r["instagram"] else "",
                })
            live_table.dataframe(
                rows,
                use_container_width=True,
                height=min(420, 28 * len(rows) + 28),
                column_config={
                    "": st.column_config.TextColumn(width="small"),
                    "BUSINESS": st.column_config.TextColumn(width="medium"),
                    "EMAIL": st.column_config.TextColumn(width="medium"),
                },
            )
        else:
            live_table.caption(meta)

        if tmp_csv and os.path.exists(tmp_csv):
            os.remove(tmp_csv)
        st.rerun()

    elif t == "error":
        st.markdown(f'<div style="color:#FF3355;font-size:13px;">$ ERROR: {update["message"]}</div>', unsafe_allow_html=True)
        st.rerun()

    elif t == "complete":
        results = update["results"]
        stats = update["stats"]
        st.session_state.scan_results = results
        st.session_state.scan_stats = stats
        st.session_state.scan_running = False
        st.session_state.partial_count = len(results)
        st.session_state.scan_state = None
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
        if not results:
            if st.session_state.scan_stopped:
                st.markdown('<div style="color:#FFD700;font-size:13px;">$ SCAN ABORTED — no results</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#FF3355;font-size:13px;">$ NO RESULTS — try different settings</div>', unsafe_allow_html=True)
        else:
            if st.session_state.scan_stopped:
                st.markdown(f'<div style="color:#FFD700;font-size:13px;">$ PARTIAL RESULTS — {len(results)} leads</div>', unsafe_allow_html=True)
            st.markdown("<hr>", unsafe_allow_html=True)

        if results:
            # ── KPI CARDS ────────────────────────────────────────────────────────
            st.markdown("<h3>📊 SUMMARY</h3>", unsafe_allow_html=True)
            kpi_cols = st.columns(6)
            kpis = [
                ("TOTAL", stats["total_found"]),
                ("📧 EMAIL", stats["with_email"]),
                ("🔥 HOT", stats["hot"]),
                ("🌐 NO SITE", stats["no_website"]),
                ("🔗 LINKEDIN", stats["with_linkedin"]),
                ("📞 PHONE", stats["with_phone"]),
            ]
            for i, (label, val) in enumerate(kpis):
                with kpi_cols[i]:
                    st.markdown(
                        f'<div class="kpi-card">'
                        f'<div class="kpi-value">{val}</div>'
                        f'<div class="kpi-label">{label}</div>'
                        f'</div>',
                        unsafe_allow_html=True
                    )

            if stats["deduped"]:
                st.markdown(f'<div style="font-size:12px;color:#808080;">$ {stats["deduped"]} duplicates skipped</div>', unsafe_allow_html=True)
            if stats["skipped_no_contact"]:
                st.markdown(f'<div style="font-size:12px;color:#808080;">$ {stats["skipped_no_contact"]} excluded (no contact)</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # ── TABS ──────────────────────────────────────────────────────────────
            tab_all, tab_hot, tab_stats = st.tabs(["📋 ALL RESULTS", "🔥 HOT LEADS", "📊 STATS"])

            df_rows = []
            for r in results:
                priority = "🔥" if r["lead_priority"] == "Hot" else "👍"
                df_rows.append({
                    "": priority,
                    "BUSINESS": r["name"],
                    "CONTACT": f"{r.get('contact_person', '')}" + (f" ({r.get('contact_title', '')})" if r.get('contact_title') else ""),
                    "CATEGORY": r["category"].title(),
                    "CITY": r["city"],
                    "STATE": r["state"],
                    "EMAIL": r["emails"][0] if r["emails"] else "",
                    "LINKEDIN": r["linkedin"],
                    "INSTAGRAM": r["instagram"],
                    "FACEBOOK": r["facebook"],
                    "PHONE": r["phone"],
                    "WEBSITE": r["website"] if r["has_website"] else "❌ No site",
                    "RATING": r["rating"] if r["rating"] else "",
                    "REVIEWS": r["review_count"],
                    "SOURCE": r["email_source"],
                    "NOTES": r["enrichment_notes"],
                })

            df = pd.DataFrame(df_rows)

            with tab_all:
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=min(500, 40 * len(df_rows) + 40),
                    column_config={
                        "": st.column_config.TextColumn(width="small"),
                        "BUSINESS": st.column_config.TextColumn(width="medium"),
                        "EMAIL": st.column_config.TextColumn(width="medium"),
                        "WEBSITE": st.column_config.TextColumn(width="medium"),
                        "PHONE": st.column_config.TextColumn(width="medium"),
                    },
                )

                # Export
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("<h4>📥 EXPORT</h4>", unsafe_allow_html=True)
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                export_col1, export_col2 = st.columns(2)
                with export_col1:
                    st.download_button(
                        label="📥 Download CSV",
                        data=csv_data,
                        file_name=f"prospects_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
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
                        label="📥 Import-Ready CSV",
                        data=import_csv,
                        file_name=f"prospects_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )

            with tab_hot:
                hot_df = df[df[""] == "🔥"].copy()
                if not hot_df.empty:
                    st.dataframe(
                        hot_df,
                        use_container_width=True,
                        height=min(400, 40 * len(hot_df) + 40),
                        column_config={
                            "": st.column_config.TextColumn(width="small"),
                            "BUSINESS": st.column_config.TextColumn(width="medium"),
                            "EMAIL": st.column_config.TextColumn(width="medium"),
                        },
                    )
                else:
                    st.markdown('<div style="font-size:13px;color:#808080;">$ No hot leads found</div>', unsafe_allow_html=True)

            with tab_stats:
                st.markdown(
                    f"""
                    <div class="glass-card">
                        <div style="font-size:13px;line-height:2;">
                            <span style="color:#00FF88;">$</span> Total discovered: <strong>{stats['total_found']}</strong><br>
                            <span style="color:#00FF88;">$</span> With email: <strong>{stats['with_email']}</strong> ({stats['with_email']/stats['total_found']*100:.0f}%)<br>
                            <span style="color:#00FF88;">$</span> With phone: <strong>{stats['with_phone']}</strong><br>
                            <span style="color:#00FF88;">$</span> With LinkedIn: <strong>{stats['with_linkedin']}</strong><br>
                            <span style="color:#00FF88;">$</span> No website: <strong>{stats['no_website']}</strong><br>
                            <span style="color:#00FF88;">$</span> Hot leads: <strong>{stats['hot']}</strong><br>
                            <span style="color:#00FF88;">$</span> Duplicates skipped: <strong>{stats['deduped']}</strong><br>
                            <span style="color:#00FF88;">$</span> Excluded (no contact): <strong>{stats['skipped_no_contact']}</strong>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

elif not st.session_state.scan_running:
    with results_container:
        st.markdown(
            f"""
            <div style="display:flex;gap:16px;margin-top:16px;flex-wrap:wrap;">
                <div class="terminal-card" style="flex:1;min-width:200px;">
                    <div class="term-header">
                        <span class="dot" style="background:#FF3355;"></span>
                        <span class="dot" style="background:#FFD700;"></span>
                        <span class="dot" style="background:#00FF88;"></span>
                        <span style="margin-left:8px;font-size:11px;color:#808080;">discover.exe</span>
                    </div>
                    <div class="term-body">
                        <div class="line-green">$ scan --discover</div>
                        <div class="line">Search across Google Places, Geoapify,</div>
                        <div class="line">SerpAPI, DuckDuckGo, and Etsy</div>
                        <div class="line">Finds businesses by type + location</div>
                    </div>
                </div>
                <div class="terminal-card" style="flex:1;min-width:200px;">
                    <div class="term-header">
                        <span class="dot" style="background:#FF3355;"></span>
                        <span class="dot" style="background:#FFD700;"></span>
                        <span class="dot" style="background:#00FF88;"></span>
                        <span style="margin-left:8px;font-size:11px;color:#808080;">enrich.exe</span>
                    </div>
                    <div class="term-body">
                        <div class="line-green">$ scan --enrich</div>
                        <div class="line">Extracts emails, phones, LinkedIn,</div>
                        <div class="line">Instagram, and Facebook from web</div>
                        <div class="line">Scrapes websites and social profiles</div>
                    </div>
                </div>
                <div class="terminal-card" style="flex:1;min-width:200px;">
                    <div class="term-header">
                        <span class="dot" style="background:#FF3355;"></span>
                        <span class="dot" style="background:#FFD700;"></span>
                        <span class="dot" style="background:#00FF88;"></span>
                        <span style="margin-left:8px;font-size:11px;color:#808080;">export.exe</span>
                    </div>
                    <div class="term-body">
                        <div class="line-green">$ scan --export</div>
                        <div class="line">Download results as CSV</div>
                        <div class="line">Import-ready format for your CRM</div>
                        <div class="line">Auto-dedup against existing lists</div>
                    </div>
                </div>
            </div>
            <div style="text-align:center;margin-top:24px;font-size:13px;color:#404040;">
                $ Configure targets in the sidebar and run <span style="color:#00FF88;">SCAN</span>
            </div>
            """,
            unsafe_allow_html=True
        )
