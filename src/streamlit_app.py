import os
import streamlit as st
import requests
import pandas as pd
import json

# --- Configuration ---
API = os.getenv("API_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("DEV_TOKEN", "")

def auth_headers():
    if TOKEN:
        return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}

def fetch_json(path, method="GET", body=None):
    url = f"{API}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=auth_headers(), timeout=15)
        else:
            r = requests.post(url, headers=auth_headers(), json=body or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e), "items": []}

st.set_page_config(
    page_title="SentientShield • Cyber Intelligence Platform",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CSS Injection ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@400;600&display=swap');

    :root {
        --bg-color: #0B0F1A;
        --card-bg: #111827;
        --primary-glow: #00F5FF;
        --secondary-glow: #7C3AED;
        --danger-color: #EF4444;
        --text-color: #E5E7EB;
        --border-color: rgba(255, 255, 255, 0.08);
    }

    /* Global Reset & Typography */
    .stApp {
        background-color: var(--bg-color);
        font-family: 'Inter', sans-serif;
        color: var(--text-color);
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Space Grotesk', sans-serif;
        color: white !important;
    }

    /* Navbar */
    .navbar {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 60px;
        background: rgba(17, 24, 39, 0.7);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 2rem;
        z-index: 999;
    }
    
    .navbar-brand {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.2rem;
        color: white;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .navbar-brand span {
        color: var(--primary-glow);
    }

    .navbar-menu {
        display: flex;
        gap: 1.5rem;
        font-size: 0.9rem;
    }
    
    .navbar-menu a {
        color: #9CA3AF;
        text-decoration: none;
        transition: color 0.3s;
    }
    
    .navbar-menu a:hover {
        color: var(--primary-glow);
    }

    /* Hero Section */
    .hero-section {
        margin-top: 60px;
        padding: 4rem 2rem;
        text-align: center;
        position: relative;
    }
    
    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        background: linear-gradient(90deg, #fff, #9CA3AF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .hero-subtitle {
        color: #9CA3AF;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .glowing-line {
        width: 100px;
        height: 4px;
        background: var(--primary-glow);
        margin: 0 auto;
        box-shadow: 0 0 20px var(--primary-glow);
        border-radius: 2px;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 0.6; width: 100px; }
        50% { opacity: 1; width: 150px; }
        100% { opacity: 0.6; width: 100px; }
    }

    /* Cards */
    div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
        /* This targets nested vertical blocks which often wrap columns */
        /* It's hard to target specific custom cards in Streamlit without custom components */
    }

    .css-card {
        background: var(--card-bg);
        border-radius: 20px;
        border: 1px solid var(--border-color);
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
        transition: transform 0.3s, box-shadow 0.3s;
        margin-bottom: 1.5rem;
        height: 100%;
    }
    
    .css-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 50px rgba(0, 245, 255, 0.1);
        border-color: rgba(0, 245, 255, 0.3);
    }
    
    .card-title {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    /* Buttons */
    .stButton > button {
        background: rgba(0, 245, 255, 0.1);
        color: var(--primary-glow);
        border: 1px solid rgba(0, 245, 255, 0.3);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background: var(--primary-glow);
        color: #000;
        box-shadow: 0 0 20px var(--primary-glow);
        border-color: var(--primary-glow);
    }

    /* Inputs */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea, .stSelectbox > div > div > div {
        background-color: #1F2937;
        color: white;
        border: 1px solid var(--border-color);
        border-radius: 8px;
    }

    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-glow);
        box-shadow: 0 0 10px rgba(0, 245, 255, 0.2);
    }

    /* Charts */
    /* Try to force dark theme for charts if possible, mostly handled by Streamlit theme config */

    /* Custom Event Console */
    .console-box {
        background: #000;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Courier New', monospace;
        color: #0f0;
        margin-bottom: 1rem;
        border-left: 4px solid var(--primary-glow);
    }

</style>

<div class="navbar">
    <div class="navbar-brand">
        <span>🛡️</span> SentientShield
    </div>
    <div class="navbar-menu">
        <a href="http://localhost:8000/static/neuralfort_dashboard.html" target="_blank">Dashboard</a>
        <a href="#" class="active">Threat Intel</a>
        <a href="http://localhost:8000/static/premium.html" target="_blank">Overview</a>
        <a href="#">Reports</a>
        <a href="#">Settings</a>
    </div>
</div>

<div class="hero-section">
    <h1 class="hero-title">Threat Intelligence Dashboard</h1>
    <div class="hero-subtitle">Real-time AI-driven cyber risk monitoring</div>
    <div class="glowing-line"></div>
</div>
""", unsafe_allow_html=True)

# --- Main Layout ---

# Create a container for the grid
st.markdown('<div style="max-width: 1400px; margin: auto;">', unsafe_allow_html=True)

# Row 1
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🔥 Top Attack Types</div>', unsafe_allow_html=True)
    
    # Logic for Top Attacks
    if "top_attacks_data" not in st.session_state:
        # Fetch initial data
        try:
            data = fetch_json("/api/logs/trends/top-attack-types")
            st.session_state.top_attacks_data = data.get("items", [])
        except:
            st.session_state.top_attacks_data = []

    if st.button("Refresh", key="btn_top"):
        try:
            data = fetch_json("/api/logs/trends/top-attack-types")
            st.session_state.top_attacks_data = data.get("items", [])
        except Exception as e:
            st.error(str(e))
    
    items = st.session_state.top_attacks_data
    if items:
        df = pd.DataFrame(items)
        st.bar_chart(df.set_index("threat_type")["count"], color="#00F5FF")
    else:
        st.info("No data available")
        
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📈 Attack Frequency</div>', unsafe_allow_html=True)
    
    bucket = st.selectbox("Time Bucket", ["hour", "day"], index=0, key="freq_bucket")
    
    if st.button("Refresh", key="btn_freq"):
        try:
            data = fetch_json(f"/api/logs/trends/attack-frequency?bucket={bucket}&limit=24")
            st.session_state.freq_data = data.get("items", [])
        except:
            st.session_state.freq_data = []
            
    if "freq_data" not in st.session_state:
        # Initial load
        try:
             data = fetch_json(f"/api/logs/trends/attack-frequency?bucket={bucket}&limit=24")
             st.session_state.freq_data = data.get("items", [])
        except:
             st.session_state.freq_data = []

    items = st.session_state.freq_data
    if items:
        df = pd.DataFrame(items)
        st.line_chart(df.set_index("time")["count"], color="#7C3AED")
    else:
        st.info("No data available")

    st.markdown('</div>', unsafe_allow_html=True)

# Row 2
col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🛡️ MITRE Distribution</div>', unsafe_allow_html=True)
    
    if st.button("Refresh", key="btn_mitre"):
        try:
            data = fetch_json("/api/logs/trends/mitre-distribution")
            st.session_state.mitre_data = data.get("items", [])
        except:
            st.session_state.mitre_data = []

    if "mitre_data" not in st.session_state:
        try:
            data = fetch_json("/api/logs/trends/mitre-distribution")
            st.session_state.mitre_data = data.get("items", [])
        except:
             st.session_state.mitre_data = []
             
    items = st.session_state.mitre_data
    if items:
        df = pd.DataFrame(items)
        # Using bar chart as simple donut is not native in basic Streamlit without altair/plotly code
        # But bar chart works well for distribution
        st.bar_chart(df.set_index("technique_id")["count"], color="#10B981")
    else:
        st.info("No MITRE data")
        
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="css-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📉 Risk Score Trends</div>', unsafe_allow_html=True)
    
    risk_bucket = st.selectbox("Risk Bucket", ["day", "hour"], index=0, key="risk_bucket_sel")
    
    if st.button("Refresh", key="btn_risk"):
        try:
            data = fetch_json(f"/api/logs/trends/risk-trends?bucket={risk_bucket}&limit=14")
            st.session_state.risk_data = data.get("items", [])
        except:
            st.session_state.risk_data = []

    if "risk_data" not in st.session_state:
        try:
            data = fetch_json(f"/api/logs/trends/risk-trends?bucket={risk_bucket}&limit=14")
            st.session_state.risk_data = data.get("items", [])
        except:
            st.session_state.risk_data = []
            
    items = st.session_state.risk_data
    if items:
        df = pd.DataFrame(items)
        st.area_chart(df.set_index("time")["avg_risk"], color="#EF4444")
    else:
        st.info("No risk data")

    st.markdown('</div>', unsafe_allow_html=True)

# Row 3 - Event Injection
st.markdown('<div class="css-card" style="margin-top: 2rem;">', unsafe_allow_html=True)
st.markdown('<div class="card-title">⚡ Event Injection Console</div>', unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
with c1:
    sample_msg = st.text_area("Log Message Payload", 
        "Failed login attempt from 203.0.113.7, user admin; possible brute_force; CVE-2021-44228 referenced",
        height=100
    )
with c2:
    st.write("")
    st.write("")
    if st.button("🚀 Record Event", use_container_width=True):
        try:
            resp = fetch_json("/api/logs/record-event", method="POST", body={"message": sample_msg})
            st.toast("Event Recorded Successfully!", icon="✅")
            st.code(json.dumps(resp, indent=2), language="json")
        except Exception as e:
            st.error(str(e))

st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True) # Close max-width container

# Sidebar for extra navigation
with st.sidebar:
    st.markdown("### Navigation")
    st.page_link("http://127.0.0.1:8000/static/neuralfort_dashboard.html", label="Live Dashboard", icon=":material/dashboard:")
    st.page_link("http://127.0.0.1:8000/static/premium.html", label="Intro UI", icon=":material/home:")
    st.markdown("---")
