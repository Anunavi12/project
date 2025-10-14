import streamlit as st
import requests, json, os, re, time
import random
import hashlib
from datetime import datetime, timedelta
from io import BytesIO
import unicodedata
import pandas as pd
from streamlit_javascript import st_javascript
import html

# ========================
# 📂 Feedback Configuration
# ========================
# Use an absolute path for the feedback file to avoid working-dir issues
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FEEDBACK_FILE = os.path.join(BASE_DIR, "feedback.csv")

# Initialize feedback file if not present
if not os.path.exists(FEEDBACK_FILE):
    # ADDED 'ProblemStatement' COLUMN
    df = pd.DataFrame(columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])
    df.to_csv(FEEDBACK_FILE, index=False)

# Safe rerun helper: some Streamlit versions remove experimental_rerun
def safe_rerun():
    try:
        # preferred (Streamlit >= 1.28.0)
        rerun = getattr(st, 'rerun', None)
        if callable(rerun):
            rerun()
            return
    except Exception:
        pass
    try:
        # fallback (Streamlit < 1.28.0, uses older API)
        rerun_old = getattr(st, 'experimental_rerun', None)
        if callable(rerun_old):
            rerun_old()
            return
    except Exception:
        pass
    # Ultimate fallback: client-side reload
    try:
        import streamlit.components.v1 as components
        components.html('<script>window.location.reload()</script>', height=0)
    except Exception:
        pass

# --- Theme toggle state ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- Theme toggle (capsule-style single-click selector) ---
st.markdown('''
<style>
.st-theme-toggle-container { position: fixed; left: 18px; top: 18px; z-index: 10001; }
/* Make the radio look capsule-like where possible */
.st-theme-toggle-container .stRadio { width: 180px; }
.st-theme-toggle-container .stRadio .css-1wy0on6 { display: flex; gap: 0; }
.st-theme-toggle-container .stRadio label[data-baseweb="radio"] { flex: 1; }
.st-theme-toggle-container .stRadio .stRadio > div > label { border-radius: 999px; padding: 6px 12px; border: 1px solid rgba(0,0,0,0.06); }
</style>
''', unsafe_allow_html=True)

with st.container():
    col1, col2 = st.columns([1, 6])
    with col1:
        # Single-click capsule radio for Light / Dark
        try:
            theme_choice = st.radio('', options=['Light', 'Dark'], index=(1 if st.session_state.dark_mode else 0), key='theme_radio', horizontal=True)
        except TypeError:
            # older Streamlit versions may not support horizontal=True
            theme_choice = st.radio('', options=['Light', 'Dark'], index=(1 if st.session_state.dark_mode else 0), key='theme_radio')

        st.session_state.dark_mode = (theme_choice == 'Dark')

    with col2:
        st.markdown('')
if st.session_state.dark_mode:
    st.markdown('''
    <style>
    :root {
        --text-primary: #f3f4f6; /* light text */
        --bg-card: #23272f;      /* dark card bg */
        --text-light: #ffffff;  /* white text for colored badges */
        --border-color: rgba(255,255,255,0.06);
        --accent-orange: #ff6b35;
        --musigma-red: #8b1e1e;
        --accent-teal: #0ea5a4;
    }
    /* Dark overall background */
    body, .stApp, .main {
        background: linear-gradient(135deg, #0b0f14 0%, #18181b 50%, #23272f 100%) !important;
        color: var(--text-primary) !important;
    }
    /* Make all main boxes use Mu-Sigma red gradient and white text for contrast */
    .info-card, .qa-box, .problem-display, .vocab-display, .section-title-box, .score-badge, .dimension-box, .dimension-display-box {
        background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%) !important;
        color: var(--text-light) !important;
        border-color: rgba(255,255,255,0.06) !important;
        box-shadow: 0 6px 30px rgba(0,0,0,0.45) !important;
    }
    /* Business problem text should be white in dark mode */
    .problem-display, .problem-display p { color: var(--text-light) !important; }
    /* Inputs use dark backgrounds with light text to match dark theme */
    .stTextArea textarea, .stTextInput input, .stSelectbox > div > div, .stSelectbox [data-baseweb="select"] {
        background: #1f2933 !important;
        color: var(--text-light) !important;
        border-color: rgba(255,255,255,0.06) !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%) !important;
        color: var(--text-light) !important;
    }
    /* Ensure headings and labels are readable */
    h1, h2, h3, h4, h5, h6, .dimension-label, .qa-question, .score-badge *, .hardness-badge-hard, .hardness-badge-moderate, .hardness-badge-easy {
        color: var(--text-light) !important;
        text-shadow: 0 1px 4px rgba(0,0,0,0.6);
    }
    .theme-toggle-btn {
        background: transparent !important;
        color: var(--text-light) !important;
        border-color: var(--text-light) !important;
    }
    .theme-toggle-btn:hover {
        background: rgba(255,255,255,0.04) !important;
    }
    </style>
    ''', unsafe_allow_html=True)
else:
    st.markdown('''
    <style>
    :root {
        --text-primary: #1e293b;
        --bg-card: #ffffff;
        --text-light: #ffffff;
        --border-color: rgba(139, 30, 30, 0.15);
        --accent-orange: #ff6b35;
        --musigma-red: #8b1e1e;
    }
    body, .stApp, .main {
        background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 50%, #eeeeee 100%) !important;
        color: #1e293b !important;
    }
    /* Regular content cards: white background, dark text */
    .info-card, .qa-box, .vocab-display, .section-title-box {
        background: #fff !important;
        color: var(--text-primary) !important;
        border-color: #e5e7eb !important;
        box-shadow: 0 2px 16px rgba(0,0,0,0.08) !important;
    }
    /* Business problem area stays white for readability */
    .problem-display { background: #fff !important; color: var(--text-primary) !important; border-color: #e5e7eb !important; }

    /* Branded boxes (scores & dimensions) use Mu-Sigma red gradient and white text in light mode too */
    .score-badge, .dimension-box, .dimension-display-box {
        background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%) !important;
        color: var(--text-light) !important;
        border: 3px solid rgba(255,255,255,0.18) !important;
        box-shadow: var(--shadow-xl) !important;
    }
    .score-badge *, .dimension-box *, .dimension-display-box * { color: var(--text-light) !important; }
    .stTextArea textarea, .stTextInput input, .stSelectbox > div > div, .stSelectbox [data-baseweb="select"] {
        background: #fff !important;
        color: #1e293b !important;
        border-color: #e5e7eb !important;
    }
    .stButton > button {
        background: linear-gradient(135deg, #8b1e1e 0%, #ff6b35 100%) !important;
        color: #fff !important;
    }
    h1, h2, h3, h4, h5, h6, .dimension-label, .qa-question, .score-badge *, .hardness-badge-hard, .hardness-badge-moderate, .hardness-badge-easy {
        color: #1e293b !important;
        text-shadow: none;
    }
    .theme-toggle-btn {
        background: #fff !important;
        color: #8b1e1e !important;
        border-color: #8b1e1e !important;
    }
    .theme-toggle-btn:hover {
        background: #ffe5e5 !important;
        border-color: #ff6b35 !important;
    }
    </style>
    ''', unsafe_allow_html=True)


# -----------------------------
# Config - Page Setup
# -----------------------------
st.set_page_config(
    page_title="Business Problem Vocabulary Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
/* --- GOOGLE FONTS --- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700;900&family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

/* --- HIDE DEFAULT STREAMLIT ELEMENTS --- */
#MainMenu, footer, header { visibility: hidden; }
.element-container:empty { display: none !important; }
div[data-testid="stVerticalBlock"] > div:empty { display: none !important; }

/* --- COLOR VARIABLES (MU-SIGMA BRAND) --- */
:root {
    --musigma-red: #8b1e1e;
    --musigma-red-dark: #6b1515;
    --musigma-red-light: #a52828;
    --accent-orange: #ff6b35;
    --accent-teal: #940d0d;
    --accent-teal-light: #b81414;
    --bg-gradient: linear-gradient(135deg, #8b1e1e 0%, #00000 100%);
    --bg-card: #ffffff;
    --text-primary: #1e293b;
    --text-secondary: #64748b;
    --text-light: #ffffff;
    --border-color: rgba(139, 30, 30, 0.15);
    --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.08);
    --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.12);
    --shadow-lg: 0 8px 32px rgba(139, 30, 30, 0.25);
    --shadow-xl: 0 16px 48px rgba(139, 30, 30, 0.35);
    --shadow-glow: 0 0 30px rgba(255, 107, 53, 0.3);
}

/* --- SMOOTH ANIMATIONS --- */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(40px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}

@keyframes gradientFlow {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes slideInRight {
    from { opacity: 0; transform: translateX(30px); }
    to { opacity: 1; transform: translateX(0); }
}

@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-30px); }
    to { opacity: 1; transform: translateX(0); }
}

@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

@keyframes borderGlow {
    0%, 100% { box-shadow: 0 0 10px rgba(255, 107, 53, 0.3); }
    50% { box-shadow: 0 0 25px rgba(255, 107, 53, 0.6); }
}

/* --- APP BACKGROUND --- */
.main { 
    font-family: 'Inter', sans-serif; 
    background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 50%, #eeeeee 100%);
    background-attachment: fixed; 
    min-height: 100vh; 
    padding: 2rem 1rem;
}
.stApp { background: transparent; }

/* --- MAIN PAGE TITLE --- */
.page-title { 
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
    background-size: 200% 200%;
    animation: gradientFlow 6s ease infinite;
    padding: 3.5rem 3rem; 
    border-radius: 28px; 
    text-align: center; 
    margin-bottom: 3rem; 
    box-shadow: var(--shadow-xl);
    border: 3px solid rgba(255, 255, 255, 0.2);
    position: relative;
    overflow: hidden;
}

.page-title::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    animation: rotate 30s linear infinite;
}

.page-title h1 { 
    margin: 0; 
    font-weight: 900; 
    color: #ffffff !important;
    font-size: 3.5rem;
    letter-spacing: -1.5px;
    text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
    position: relative;
    z-index: 1;
    font-family: 'Poppins', sans-serif;
}

.page-subtitle {
    color: rgba(255,255,255,0.95) !important;
    font-size: 1.25rem;
    margin-top: 0.75rem;
    font-weight: 400;
    position: relative;
    z-index: 1;
    letter-spacing: 0.5px;
}

/* Decorative elements - STATIC */
.title-decoration {
    position: absolute;
    font-size: 3rem;
    opacity: 0.12;
}

.deco-1 { top: 25px; left: 40px; }
.deco-2 { top: 35px; right: 50px; }
.deco-3 { bottom: 30px; left: 60px; }
.deco-4 { bottom: 25px; right: 70px; }

/* Mu-Sigma Logo - FIXED POSITION */
.musigma-logo {
    position: fixed;
    top: 20px;
    right: 20px;
    width: 95px;
    height: 95px;
    border-radius: 50%;
    border: 3px solid var(--musigma-red);
    box-shadow: 0 10px 40px rgba(139, 30, 30, 0.4);
    z-index: 9999;
    background: white;
    opacity: 1;
    overflow: hidden;
    animation: fadeIn 1s ease-out;
}

.musigma-logo:hover { 
    box-shadow: 0 15px 50px rgba(139, 30, 30, 0.6);
    animation: borderGlow 2s ease-in-out infinite;
}

.musigma-logo img {
    width: 100% !important;
    height: 100% !important;
    object-fit: contain !important;
    padding: 12px;
}

/* --- SECTION HEADINGS (CENTERED) --- */
h2, h3, h4, h5, h6,
.stMarkdown h2, .stMarkdown h3, .stMarkdown h4, .stMarkdown h5, .stMarkdown h6,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3,
[data-testid="stMarkdownContainer"] h4,
[data-testid="stMarkdownContainer"] h5,
[data-testid="stMarkdownContainer"] h6 {
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    margin-top: 1.5rem !important;
    margin-bottom: 1rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
    text-align: center !important;
}

/* --- SECTION TITLE BOXES (CENTERED WITH GRADIENT) --- */

.section-title-box {
    /* Match the main title look: Mu-Sigma red -> accent orange gradient in all modes */
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%) !important;
    border-radius: 20px;
    padding: 2.5rem 3rem;
    margin: 0.5rem 0 1rem 0 !important; /* Reduced top margin from 2.5rem to 0.5rem */
    box-shadow: var(--shadow-lg) !important;
    /* Explicitly disable decorative animations for section title boxes */
    position: relative;
    overflow: hidden;
    text-align: center;
}

/* Remove shimmer overlay/animation for these boxes so headings remain fully visible */
.section-title-box::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 0;
    height: 0;
    background: transparent !important;
    animation: none !important;
}

.section-title-box h2,
.section-title-box h3,
.section-title-box h4 {
    color: var(--text-light) !important; /* ensure white text in all themes */
    margin: 0 !important;
    font-weight: 900 !important;
    font-size: 1.9rem !important;
    font-family: 'Poppins', sans-serif !important;
    position: relative;
    z-index: 2;
    text-align: center !important;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
}

.section-icon {
    font-size: 2rem;
    display: inline-block;
}

/* --- INFO CARDS --- */
.info-card { 
    background: var(--bg-card);
    border: 2px solid var(--border-color);
    border-radius: 24px; 
    padding: 2.5rem; 
    margin-bottom: 2rem; 
    box-shadow: var(--shadow-md);
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    animation: fadeInUp 0.7s ease-out;
    position: relative;
}

.info-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 5px;
    height: 0;
    background: linear-gradient(180deg, var(--musigma-red), var(--accent-orange), var(--accent-teal));
    transition: height 0.6s cubic-bezier(0.4, 0, 0.2, 1);
    border-radius: 24px 0 0 24px;
}

.info-card:hover::before {
    height: 100%;
}

.info-card:hover { 
    transform: translateY(-8px) scale(1.01); 
    box-shadow: var(--shadow-xl);
    border-color: var(--accent-orange);
}

.info-card p, .info-card li, .info-card span {
    color: var(--text-primary) !important; 
    line-height: 1.9;
    font-size: 1.05rem;
}

.info-card h3, .info-card h4 {
    color: var(--musigma-red) !important;
    font-weight: 700 !important;
    margin-bottom: 1.5rem !important;
}

/* --- PROBLEM DISPLAY --- */
.problem-display { 
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border: 2px solid var(--border-color);
    border-radius: 24px !important; 
    padding: 2.5rem !important; 
    margin-bottom: 2.5rem; 
    box-shadow: var(--shadow-md);
    animation: scaleIn 0.7s ease-out;
    position: relative;
    transition: all 0.4s ease;
}

.problem-display:hover {
    box-shadow: var(--shadow-lg);
    border-color: var(--accent-teal);
}

.problem-display::after {
    content: '📋';
    position: absolute;
    top: 25px;
    right: 25px;
    font-size: 2.5rem;
    opacity: 0.08;
}

.problem-display h4 { 
    color: var(--musigma-red) !important; 
    margin-top: 0; 
    font-weight: 700; 
    font-size: 1.5rem; 
    margin-bottom: 1.5rem;
    text-align: center !important;
}

.problem-display p { 
    color: var(--text-primary) !important; 
    line-height: 1.9;
    font-size: 1.05rem;
    margin: 0;
}

/* --- Q&A BOXES --- */
.qa-box { 
    background: var(--bg-card);
    border: 2px solid var(--border-color);
    border-radius: 20px; 
    padding: 2.25rem; 
    margin-bottom: 2rem; 
    box-shadow: var(--shadow-md);
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    animation: slideInRight 0.7s ease-out;
    position: relative;
    overflow: hidden;
}

.qa-box::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    width: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--musigma-red), var(--accent-orange), var(--accent-teal));
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.qa-box:hover::after {
    width: 100%;
}

.qa-box:hover { 
    transform: translateX(8px) translateY(-6px); 
    box-shadow: var(--shadow-lg);
    border-color: var(--accent-orange);
}

.qa-question { 
    font-weight: 700; 
    font-size: 1.2rem; 
    color: inherit !important; 
    margin-bottom: 1.5rem; 
    line-height: 1.7; 
    font-family: 'Space Grotesk', sans-serif;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.qa-question::before {
    content: '▸';
    color: var(--accent-orange);
    font-size: 1.5rem;
    flex-shrink: 0;
}

.qa-answer { 
    font-size: 1.05rem; 
    line-height: 1.9; 
    color: inherit !important; 
    white-space: pre-wrap; 
}

/* --- SCORE BADGES --- */
.score-badge { 
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
    padding: 3.5rem; 
    border-radius: 28px; 
    text-align: center; 
    color: var(--text-light); 
    box-shadow: var(--shadow-xl);
    animation: scaleIn 0.8s ease-out; 
    min-height: 220px; 
    display: flex; 
    flex-direction: column; 
    align-items: center; 
    justify-content: center; 
    border: 3px solid rgba(255, 255, 255, 0.2);
    position: relative;
    overflow: hidden;
    transition: all 0.4s ease;
}

.score-badge:hover {
    transform: scale(1.03);
    box-shadow: var(--shadow-glow);
}

.score-badge::before {
    content: '';
    position: absolute;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    animation: pulse 4s ease-in-out infinite;
}

.score-badge * { 
    color: var(--text-light) !important;
    position: relative;
    z-index: 1;
}

/* --- HARDNESS BADGES --- */
.hardness-badge-hard, 
.hardness-badge-moderate, 
.hardness-badge-easy { 
    color: var(--text-light) !important; 
    padding: 3.5rem; 
    border-radius: 28px; 
    font-size: 2.2rem; 
    font-weight: 900; 
    text-align: center; 
    min-height: 220px; 
    display: flex; 
    flex-direction: column;
    align-items: center; 
    justify-content: center; 
    animation: scaleIn 0.8s ease-out; 
    border: 3px solid rgba(255, 255, 255, 0.2);
    box-shadow: var(--shadow-xl);
    position: relative;
    overflow: hidden;
    transition: all 0.4s ease;
}

.hardness-badge-hard:hover,
.hardness-badge-moderate:hover,
.hardness-badge-easy:hover {
    transform: scale(1.03);
}

.hardness-badge-hard { 
    background: linear-gradient(135deg, #c62828 0%, #8b0000 100%);
}

.hardness-badge-moderate { 
    background: linear-gradient(135deg, #f57c00 0%, #e65100 100%);
}

.hardness-badge-easy { 
    background: linear-gradient(135deg,#53c853 0%, #1d911d 100%);
}

/* --- DIMENSION BOXES --- */
.dimension-box, 
.dimension-display-box { 
    color: var(--text-light) !important; 
    padding: 3rem; 
    border-radius: 24px; 
    text-align: center; 
    box-shadow: var(--shadow-md);
    min-height: 200px; 
    margin-bottom: 2rem; 
    transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1);
    animation: fadeInUp 0.8s ease-out; 
    border: 3px solid rgba(255, 255, 255, 0.2);
    position: relative;
    overflow: hidden;
}

.dimension-box::before,
.dimension-display-box::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 100%;
    background: radial-gradient(circle at top right, rgba(255,255,255,0.15) 0%, transparent 60%);
    top: 0;
    right: 0;
}

.dimension-box { 
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
    cursor: pointer;
}

.dimension-box:hover { 
    transform: translateY(-12px) scale(1.04); 
    box-shadow: 0 20px 60px rgba(139, 30, 30, 0.4);
    animation: borderGlow 2s ease-in-out infinite;
}

.dimension-display-box { 
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
}

.dimension-display-box:hover { 
    transform: translateY(-8px) scale(1.02); 
    box-shadow: var(--shadow-xl);
}

.dimension-score { 
    font-size: 4rem; 
    font-weight: 900; 
    margin: 1.25rem 0; 
    color: inherit !important; 
    font-family: 'Poppins', sans-serif;
    text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
    position: relative;
    z-index: 1;
}

.dimension-label { 
    font-size: 1.35rem; 
    font-weight: 700; 
    color: inherit !important; 
    text-transform: uppercase; 
    letter-spacing: 2px; 
    font-family: 'Space Grotesk', sans-serif;
    position: relative;
    z-index: 1;
}

/* --- VOCABULARY DISPLAY --- */
.vocab-display { 
    background: var(--bg-card) !important; 
    border: 2px solid var(--border-color);
    border-radius: 24px; 
    padding: 2.5rem; 
    line-height: 1.7 !important; 
    margin-top: 2rem;
    color: var(--text-primary) !important;
    font-size: 1.05rem;
    max-height: 650px;
    overflow-y: auto;
    box-shadow: var(--shadow-md);
    animation: slideInLeft 0.6s ease-out;
}

.vocab-display h4 {
    color: var(--musigma-red) !important;
    font-weight: 800 !important;
    font-size: 1.8rem !important;
    margin-bottom: 2rem !important;
    text-align: center !important;
}

.vocab-display strong {
    color: var(--accent-black) !important;
    font-weight: 700 !important;
}

/* --- SCORE GRID & DIMENSION ITEM STYLES (theme-aware) --- */
.scores-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
}
.score-item {
    padding: 0.75rem;
    border-radius: 8px;
    text-align: center;
    background: rgba(255, 107, 53, 0.05);
    color: var(--accent-orange);
}
.score-item strong { display:block; }
.score-item .score-value { font-size: 1.2rem; font-weight: 700; color: var(--accent-orange); }

.dim-item { 
    padding: 1rem; 
    margin-bottom: 0.75rem; 
    background: rgba(255, 107, 53, 0.05); 
    border-radius: 8px; 
    border-left: 3px solid var(--accent-orange);
}
.dim-item strong { color: var(--accent-orange); font-size: 1.1rem; }
.dim-item .dim-score { font-size: 1.5rem; font-weight: 700; color: var(--accent-orange); }

.vocab-item {
    margin-bottom: 1.25rem !important;
    padding-bottom: 1.25rem !important;
    border-bottom: 1px solid rgba(139, 30, 30, 0.1);
    transition: all 0.3s ease;
}

.vocab-item:hover {
    padding-left: 15px;
    background: linear-gradient(90deg, rgba(139, 30, 30, 0.03) 0%, transparent 100%);
    border-radius: 10px;
}

/* --- DIMENSION CLICK TEXT --- */
.dimension-click-text {
    color: var(--text-secondary) !important;
    font-size: 1.1rem !important;
    font-weight: 600 !important;
    text-align: center;
    margin-bottom: 3rem !important;
    padding: 1.5rem;
    background: linear-gradient(135deg, rgba(139, 30, 30, 0.05) 0%, rgba(255, 107, 53, 0.05) 100%);
    border-radius: 16px;
    border: 2px dashed var(--accent-orange);
    animation: pulse 4s ease-in-out infinite;
}

/* --- STREAMLIT SELECT BOXES (FIXED) --- */
.stSelectbox {
    margin-bottom: 1rem;
}

.stSelectbox > label {
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.5rem !important;
}

.stSelectbox > div > div { 
    background-color: var(--bg-card) !important; 
    border: 2px solid var(--border-color) !important; 
    border-radius: 16px !important; 
    padding: 0.5rem 1rem !important; 
    min-height: 48px !important; 
    max-height: 48px !important;
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease; 
}

.stSelectbox > div > div:hover { 
    border-color: var(--accent-purple) !important; 
    box-shadow: 0 4px 12px rgba(124, 58, 237, 0.2);
    transform: translateY(-2px); 
}

.stSelectbox [data-baseweb="select"] { 
    background-color: transparent !important; 
    min-height: 40px !important;
    max-height: 40px !important;
}

.stSelectbox [data-baseweb="select"] > div {
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    padding: 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
}

/* Fix for selected text visibility */
div[data-baseweb="select"] > div:first-child {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 100% !important;
    padding-right: 20px !important;
}

[data-baseweb="popover"] { 
    background-color: var(--bg-card) !important; 
    border-radius: 16px !important;
    box-shadow: var(--shadow-lg) !important;
    max-height: 300px !important;
    overflow-y: auto !important;
}

ul[role="listbox"] { 
    background-color: var(--bg-card) !important; 
    border: 2px solid var(--border-color) !important; 
    border-radius: 16px !important; 
    max-height: 280px !important; 
    overflow-y: auto !important; 
    box-shadow: var(--shadow-lg);
    padding: 0.5rem !important;
}

li[role="option"] { 
    color: var(--text-primary) !important; 
    background-color: transparent !important; 
    padding: 10px 14px !important; 
    font-size: 0.95rem !important; 
    line-height: 1.5 !important; 
    transition: all 0.2s ease;
    border-radius: 10px !important;
    margin: 2px 0 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

li[role="option"]:hover { 
    background-color: rgba(124, 58, 237, 0.1) !important; 
    color: var(--accent-purple) !important; 
    transform: translateX(5px); 
}

li[role="option"][aria-selected="true"] { 
    background-color: rgba(139, 30, 30, 0.15) !important; 
    color: var(--musigma-red) !important; 
    font-weight: 600 !important; 
}

/* --- TEXT AREAS & INPUTS --- */
.stTextArea textarea, 
.stTextInput input { 
    background: var(--bg-card) !important; 
    border: 2px solid var(--border-color) !important; 
    border-radius: 16px !important; 
    color: var(--text-primary) !important; 
    font-size: 1.05rem !important; 
    box-shadow: var(--shadow-sm);
    transition: all 0.3s ease; 
    padding: 1.25rem !important;
    line-height: 1.7 !important;
}

.stTextArea textarea {
    min-height: 180px !important;
}

.stTextArea textarea::placeholder,
.stTextInput input::placeholder {
    color: var(--text-secondary) !important;
    opacity: 0.7 !important;
}

.stTextArea textarea:focus, 
.stTextInput input:focus { 
    border-color: var(--accent-orange) !important; 
    box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.1) !important;
    outline: none !important;
}

/* --- BUTTONS --- */
.stButton > button { 
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
    color: #ffffff !important; 
    border: none; 
    border-radius: 16px; 
    padding: 1.1rem 2.75rem; 
    font-weight: 700; 
    font-size: 1.1rem; 
    box-shadow: var(--shadow-md);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.stButton > button::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
}

.stButton > button:hover::before {
    width: 400px;
    height: 400px;
}

.stButton > button:hover { 
    transform: translateY(-4px) scale(1.02); 
    box-shadow: 0 10px 30px rgba(139, 30, 30, 0.4);
}

.stButton > button:active { 
    transform: translateY(-2px); 
}

/* Reduce gap between button and vocabulary section */
.stButton {
    margin-bottom: 0.5rem !important;
}

/* Reduce spacing in main block container */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
}

/* --- PROGRESS BAR --- */
.stProgress > div > div { 
    background: linear-gradient(90deg, var(--musigma-red), var(--accent-orange), var(--accent-teal)) !important; 
    border-radius: 12px; 
    height: 12px !important;
}

/* --- FUN FACT STYLING --- */
.fun-fact {
    background: linear-gradient(135deg, rgba(139, 30, 30, 0.05) 0%, rgba(255, 107, 53, 0.05) 100%);
    padding: 1.5rem 2rem;
    border-radius: 16px;
    border-left: 4px solid var(--accent-orange);
    margin-top: 1rem;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
    animation: slideInRight 0.5s ease-out;
}

.fun-fact-title {
    font-weight: 700;
    color: var(--musigma-red);
    font-size: 1.1rem;
    margin-bottom: 0.5rem;
}

.fun-fact-text {
    color: var(--text-secondary);
    font-size: 1rem;
    line-height: 1.6;
}

/* --- SCROLLBAR --- */
::-webkit-scrollbar {
    width: 12px;
    height: 12px;
}

::-webkit-scrollbar-track {
    background: rgba(139, 30, 30, 0.05);
    border-radius: 12px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--musigma-red), var(--accent-orange));
    border-radius: 12px;
    transition: background 0.3s ease;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--musigma-red-dark), var(--accent-orange));
}

/* --- RESPONSIVE --- */
@media (max-width: 768px) {
    .page-title h1 {
        font-size: 2.2rem;
    }
    
    .section-title-box h2,
    .section-title-box h3 {
        font-size: 1.4rem !important;
    }
    
    .dimension-score {
        font-size: 3rem;
    }
    
    .musigma-logo {
        width: 75px;
        height: 75px;
    }
}
            /* Smaller, tighter titles/headings + box sizing */
:root {
    --heading-weight: 650;
    --title-padding-y: 0.5rem;
    --title-padding-x: 0.75rem;
    --title-radius: 8px;

    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
}

/* Headings: reduce size, tighten line-height and margins */
h1, h2, h3, .title, .heading, .card-title {
    letter-spacing: -0.01em;
    font-weight: var(--heading-weight);
}

h1 {
    font-size: clamp(1.6rem, 1.2rem + 1.8vw, 2.2rem);
    line-height: 1.15;
    margin: 0 0 var(--space-2);
}

h2 {
    font-size: clamp(1.3rem, 1.0rem + 1.2vw, 1.8rem);
    line-height: 1.2;
    margin: 0 0 var(--space-2);
}

h3 {
    font-size: clamp(1.1rem, 0.95rem + 0.8vw, 1.4rem);
    line-height: 1.25;
    margin: 0 0 var(--space-1);
}

/* Title/heading "boxes": smaller padding and radius */
.title-box,
.heading-box,
.card-header,
.section-header {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--title-padding-y) var(--title-padding-x);
    border-radius: var(--title-radius);
}

.card-title {
    font-size: clamp(1rem, 0.9rem + 0.5vw, 1.2rem);
    margin: 0;
}

/* Hero and sections: reduce vertical space */
.hero h1,
.page-title {
    font-size: clamp(1.7rem, 1.2rem + 2vw, 2.3rem);
}

.hero {
    padding-block: clamp(1.25rem, 0.8rem + 2vw, 2rem);
}

.section {
    padding-block: clamp(0.75rem, 0.5rem + 1.5vw, 1.5rem);
}

/* Layout gaps slightly tighter */
.grid,
.stack {
    gap: var(--space-2);
}

/* Container narrower for cleaner look on wide screens */
.container {
    max-width: min(1100px, 92vw);
    padding-inline: var(--space-3);
}

/* Navigation breadcrumb */
.nav-breadcrumb {
    background: rgba(139, 30, 30, 0.05);
    padding: 1rem 1.5rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    color: var(--text-secondary);
    animation: fadeIn 0.5s ease-out;
}

.nav-breadcrumb a {
    color: var(--musigma-red);
    text-decoration: none;
    font-weight: 600;
    transition: color 0.3s ease;
}

.nav-breadcrumb a:hover {
    color: var(--accent-orange);
}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Smaller, tighter titles/headings + box sizing */
:root {
    --heading-weight: 650;
    --title-padding-y: 0.5rem;
    --title-padding-x: 0.75rem;
    --title-radius: 8px;
    --space-1: 0.25rem;
    --space-2: 0.5rem;
    --space-3: 0.75rem;
}

/* Compact Section Heading Boxes */
.section-title-box {
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%) !important;
    border-radius: 12px !important;
    padding: 0.9rem 1.2rem !important;
    margin: 0.5rem 0 0.5rem 0 !important; /* Reduced margins from 1.5rem to 0.5rem */
    box-shadow: var(--shadow-md) !important;
    text-align: center !important;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease-in-out;
}

.section-title-box h2,
.section-title-box h3,
.section-title-box h4 {
    color: var(--text-light) !important;
    margin: 0 !important;
    font-weight: 800 !important;
    font-size: 1.25rem !important;
    font-family: 'Poppins', sans-serif !important;
    letter-spacing: 0.3px;
    text-align: center !important;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}

.section-title-box:hover {
    box-shadow: 0 0 18px rgba(255, 107, 53, 0.3) !important;
    transform: translateY(-2px);
}
  /* Compact Main Page Title (Hero Box) */
.page-title {
    background: linear-gradient(135deg, var(--musigma-red) 0%, var(--accent-orange) 100%);
    background-size: 200% 200%;
    animation: gradientFlow 6s ease infinite;
    padding: 1.4rem 1.8rem !important;   /* ↓ Reduced height */
    border-radius: 18px !important;
    text-align: center;
    margin-bottom: 2rem !important;       /* ↓ Less vertical gap */
    box-shadow: var(--shadow-lg);
    border: 2px solid rgba(255, 255, 255, 0.15);
    position: relative;
    overflow: hidden;
}

/* Title text inside hero */
.page-title h1 {
    margin: 0;
    font-weight: 800;
    color: #ffffff !important;
    font-size: 2.2rem !important;        /* ↓ Reduced font size */
    letter-spacing: -0.5px;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.25);
    font-family: 'Poppins', sans-serif;
}

.page-subtitle {
    color: rgba(255,255,255,0.9) !important;
    font-size: 1rem !important;          /* ↓ Slightly smaller subtitle */
    margin-top: 0.3rem;
    font-weight: 400;
    letter-spacing: 0.3px;
}

/* Optional subtle hover lift for the main title box */
.page-title:hover {
    transform: translateY(-3px);
    box-shadow: 0 0 22px rgba(255, 107, 53, 0.4);
}
            
</style>
""", unsafe_allow_html=True)
# ========================
# 🔗 CLICKABLE MU SIGMA LOGO TO TOGGLE ADMIN PANEL
# ========================

# ✅ Use a valid transparent Mu Sigma logo (corrected URL)
# The old URL was missing or had permission issues — this one works.
LOGO_URL = "https://yt3.googleusercontent.com/ytc/AIdro_k-7HkbByPWjKpVPO3LCF8XYlKuQuwROO0vf3zo1cqgoaE=s900-c-k-c0x00ffffff-no-rj" 

# ✅ Inject JavaScript directly to handle sessionStorage and toggle
# (Removed duplicate logo injection that relied on window.parent.document)

st.markdown(("""
    <a href="?adminPanelToggled=true#admin-section" style="text-decoration:none;">
        <div class="musigma-logo" id="musigma-logo" style="cursor: pointer;" title="Open Admin View">
            <img src="LOGO_URL_HERE" alt="Mu Sigma Logo">
        </div>
    </a>
    <div id="admin-section" style="display:none;"></div>
""").replace("LOGO_URL_HERE", LOGO_URL), unsafe_allow_html=True)

# ========================
# 🧠 JavaScript toggle bridge (connects sessionStorage to Streamlit)
# ========================
# Try to use streamlit_javascript if available; otherwise fall back to a tiny component
try:
    toggle_signal = st_javascript("""
        let toggled = window.sessionStorage.getItem('adminPanelToggled');
        if (toggled === 'true') {
            return 'show';
        } else {
            return 'hide';
        }
    """)
except Exception:
    # Fallback: use st.components.v1 to run a small JS snippet that returns the value
    import streamlit.components.v1 as components
    try:
        toggle_signal = components.html(
            """
            <script>
            (function() {
                const t = window.sessionStorage.getItem('adminPanelToggled');
                const out = (t === 'true') ? 'show' : 'hide';
                const el = document.createElement('div');
                el.id = 'admin-toggle-signal';
                el.textContent = out;
                document.body.appendChild(el);
            })();
            </script>
            <div id="admin-toggle-signal"></div>
            """,
            height=0
        )
        # components.html doesn't return the value to Python; we'll instead try reading via query params fallback
        toggle_signal = None
    except Exception:
        toggle_signal = None

# Ensure admin panel state exists
if 'show_admin_panel' not in st.session_state:
    st.session_state.show_admin_panel = False
# intermediate selection flag: user clicked logo and wants to see admin selection
if 'admin_view_selected' not in st.session_state:
    st.session_state.admin_view_selected = False

# First, check for a URL query param (set by the logo onclick) - highest priority
qparams = st.query_params
if 'adminPanelToggled' in qparams:
    v = qparams.get('adminPanelToggled')[0].lower()
    
    # FIX APPLIED: Added 't' for robustness in case of partial URL input
    if v in ('1', 't', 'true', 'show', 'yes'): 
        st.session_state.current_page = 'admin'
        st.session_state.show_admin_panel = True
        st.session_state.admin_view_selected = True
    else:
        st.session_state.show_admin_panel = False
    # Remove the query param to keep the URL clean
    try:
        import streamlit.components.v1 as components
        components.html("""
            <script>
            (function(){
                const url = new URL(window.location.href);
                url.searchParams.delete('adminPanelToggled');
                history.replaceState(null, '', url.pathname + url.search + url.hash);
            })();
            </script>
        """, height=0)
    except Exception:
        pass
    # Don't rerun here - let Streamlit handle the state change naturally
        pass
elif 'openFeedback' in qparams:
    v = qparams.get('openFeedback')[0].lower()
    if v in ('1', 'true', 'show', 'yes'):
        # Stay on the main page but show the vocabulary/feedback section
        st.session_state.current_page = 'page1'
        st.session_state.show_vocabulary = True
        st.session_state.open_feedback_from_logo = True
    # Remove the query param to keep the URL clean
    try:
        import streamlit.components.v1 as components
        components.html("""
            <script>
            (function(){
                const url = new URL(window.location.href);
                url.searchParams.delete('openFeedback');
                history.replaceState(null, '', url.pathname + url.search + url.hash);
            })();
            </script>
        """, height=0)
    except Exception:
        pass
# If no query param, fall back to the toggle_signal (if available)
elif toggle_signal == "show":
    st.session_state.show_admin_panel = True
elif toggle_signal == "hide":
    st.session_state.show_admin_panel = False

if 'show_admin_panel' not in st.session_state:
    st.session_state.show_admin_panel = False

if toggle_signal == "show":
    st.session_state.show_admin_panel = True
elif toggle_signal == "hide":
    st.session_state.show_admin_panel = False

# If admin panel is requested but admin view not yet selected, show a Streamlit-native intermediate selection UI
if st.session_state.show_admin_panel and not st.session_state.admin_view_selected:
    # Use columns to center the panel and buttons
    st.markdown("""
    <div style='display:flex; justify-content:center; margin-top:12px;'>
        <div style='max-width:680px; width:92%; background:var(--bg-card); border-radius:12px; padding:16px; box-shadow:0 8px 32px rgba(0,0,0,0.08); border:1px solid rgba(139,30,30,0.04);'>
            <h4 style='margin:0 0 6px 0; color:#8b1e1e; text-align:center;'>Admin view requested</h4>
            <p style='margin:0 0 12px 0; text-align:center; color:var(--text-secondary);'>Do you want to open the Admin View? This will allow access to admin-only controls like feedback download.</p>
            <div style='display:flex; justify-content:center; gap:12px;'>
                </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        open_admin = st.button("Open Admin View", key="open_admin_view_btn")
        cancel_admin = st.button("Cancel", key="cancel_admin_view_btn")
        if open_admin:
            st.session_state.admin_view_selected = True
            # keep show_admin_panel True so admin block renders
            safe_rerun()
        if cancel_admin:
            st.session_state.show_admin_panel = False
            st.session_state.admin_view_selected = False
            safe_rerun()


# -----------------------------
# Config - Data & Auth
# -----------------------------
TENANT_ID = "talos"
AUTH_TOKEN = None
HEADERS_BASE = {"Content-Type": "application/json"}

# ================================
# 🏢 Account & Industry Mapping (Expanded + Stable Auto-Mapping)
# ================================

# --- Safe defaults ---
if "account" not in st.session_state:
    st.session_state.account = "Select Account"
if "industry" not in st.session_state:
    st.session_state.industry = "Select Industry"

# -----------------------------
# EXPANDED ACCOUNTS with Industry Mapping (CORRECTED VERSION)
# -----------------------------
ACCOUNT_INDUSTRY_MAP = {
    "Select Account": "Select Industry",

    # --- Priority Accounts (shown first) ---
    "Abbvie": "Pharma", "BMS": "Pharma", "BLR Airport": "Other",
    "Chevron": "Energy", "Coles": "Retail", "DELL": "Technology",
    "Microsoft": "Technology", "Mu Labs": "Technology", "Nike": "Consumer Goods",
    "Skill Development": "Education", "Southwest Airlines": "Airlines",
    "Sabic": "Energy", "Johnson & Johnson": "Pharma", "THD": "Retail",
    "Tmobile": "Telecom", "Walmart": "Retail",

    # --- Rest of the Accounts ---
    # Pharmaceutical
    "Pfizer": "Pharma", "Novartis": "Pharma", "Merck": "Pharma", "Roche": "Pharma",

    # Technology
    "IBM": "Technology", "Oracle": "Technology", "SAP": "Technology",
    "Salesforce": "Technology", "Adobe": "Technology",

    # Retail
    "Target": "Retail", "Costco": "Retail", "Kroger": "Retail", "Tesco": "Retail",
    "Carrefour": "Retail",

    # Airlines
    "Delta Airlines": "Airlines", "United Airlines": "Airlines", "American Airlines": "Airlines",
    "Emirates": "Airlines", "Lufthansa": "Airlines",

    # Consumer Goods
    "Adidas": "Consumer Goods", "Unilever": "Consumer Goods",
    "Procter & Gamble": "Consumer Goods", "Coca-Cola": "Consumer Goods",
    "PepsiCo": "Consumer Goods", "Mars": "Consumer Goods",

    # Energy
    "ExxonMobil": "Energy", "Shell": "Energy", "BP": "Energy", "TotalEnergies": "Energy",

    # Finance
    "JPMorgan Chase": "Finance", "Bank of America": "Finance", "Wells Fargo": "Finance",
    "Goldman Sachs": "Finance", "Morgan Stanley": "Finance", "Citigroup": "Finance",

    # Healthcare
    "UnitedHealth": "Healthcare", "CVS Health": "Healthcare", "Anthem": "Healthcare",
    "Humana": "Healthcare", "Kaiser Permanente": "Healthcare",

    # Logistics
    "FedEx": "Logistics", "UPS": "Logistics", "DHL": "Logistics",
    "Maersk": "Logistics", "Amazon Logistics": "Logistics",

    # E-commerce
    "Amazon": "E-commerce", "Alibaba": "E-commerce", "eBay": "E-commerce",
    "Shopify": "E-commerce", "Flipkart": "E-commerce",

    # Automotive
    "Tesla": "Automotive", "Ford": "Automotive", "General Motors": "Automotive",
    "Toyota": "Automotive", "Volkswagen": "Automotive",

    # Hospitality
    "Marriott": "Hospitality", "Hilton": "Hospitality",
    "Hyatt": "Hospitality", "Airbnb": "Hospitality",

    # Education
    "Coursera": "Education", "Udemy": "Education", "Khan Academy": "Education"
}

# --- Priority Accounts ---
PRIORITY_ACCOUNTS = [
    "Abbvie", "BMS", "BLR Airport", "Chevron", "Coles", "DELL",
    "Microsoft", "Mars", "Mu Labs", "Nike", "Skill Development",
    "Southwest Airlines", "Sabic", "Johnson & Johnson", "THD",
    "Tmobile", "Walmart"
]

# --- Add remaining accounts (alphabetically) ---
OTHER_ACCOUNTS = [
    acc for acc in ACCOUNT_INDUSTRY_MAP.keys()
    if acc not in PRIORITY_ACCOUNTS and acc != "Select Account"
]
OTHER_ACCOUNTS.sort()
OTHER_ACCOUNTS.append("Others")

# --- Add 'Others' mapping ---
ACCOUNT_INDUSTRY_MAP["Others"] = "Other"

# --- Final ordered account list ---
ACCOUNTS = ["Select Account"] + PRIORITY_ACCOUNTS + OTHER_ACCOUNTS

# --- Unique Industries ---
all_industries = list(set(ACCOUNT_INDUSTRY_MAP.values()))
INDUSTRIES = sorted([i for i in all_industries if i != "Select Industry"])
if "Other" not in INDUSTRIES:
    INDUSTRIES.append("Other")
INDUSTRIES = ["Select Industry"] + INDUSTRIES

# --- Debug Info ---
print(f"Total Accounts: {len(ACCOUNTS)}")
print(f"Total Industries: {len(INDUSTRIES)}")
print(f"Industries: {INDUSTRIES}")

# === API CONFIGURATION ===
API_CONFIGS = [
    {
        "name": "vocabulary",
        "url": "https://eoc.mu-sigma.com/talos-engine/agency/reasoning_api?society_id=1757657318406&agency_id=1758548233201&level=1",
        "multiround_convo":3,
        "description": "vocabulary",
        "prompt": lambda problem, outputs: (
            f"{problem}\n\nExtract the vocabulary from this problem statement."
        )
    }
]
# -----------------------------
# Utility Functions
# -----------------------------
def json_to_text(data):
    if data is None: 
        return ""
    if isinstance(data, str): 
        return data
    if isinstance(data, dict):
        for key in ("result", "output", "content", "text"):
            if key in data and data[key]: 
                return json_to_text(data[key])
        if "data" in data: 
            return json_to_text(data["data"])
        return "\n".join(f"{k}: {json_to_text(v)}" for k, v in data.items() if v)
    if isinstance(data, list): 
        return "\n".join(json_to_text(x) for x in data if x)
    return str(data)

def sanitize_text(text):
    """Remove markdown artifacts and clean up text"""
    if not text:
        return ""
    
    # Fix the "s" character issue - remove stray 's' characters at the beginning
    text = re.sub(r'^\s*s\s+', '', text.strip())
    text = re.sub(r'\n\s*s\s+', '\n', text)
    
    text = re.sub(r'Q\d+\s*Answer\s*Explanation\s*:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'^\s*[-*]\s+', '• ', text, flags=re.MULTILINE)
    text = re.sub(r'<\/?[^>]+>', '', text)
    text = re.sub(r'&', '&', text)
    text = re.sub(r'& Key Takeaway:', 'Key Takeaway:', text)
    
    return text.strip()


def format_vocabulary_with_bold(text, extra_phrases=None):
    """
    Updated formatter rules (high-level):
      - Replace ' - ' with ' :'
      - Normalize bullets(-, *) -> •
      - If a numbered heading has a colon (e.g. '10. Heading:'), bold ONLY the numbered heading (left-of-colon).
      - If a numbered heading has NO colon (e.g. '2. Heading'), bold the whole numbered heading line and its immediate continuation lines.
      - 'Step N:' bolds the whole block (line + continuation lines).
      - extra_phrases: optional list of strings/regex to bold wherever they appear.
    """
    if not text:
        return "No vocabulary data available"

    # If you have sanitize_text, keep it; otherwise fall back to identity.
    try:
        clean_text = sanitize_text(text)
    except NameError:
        clean_text = text

    # basic normalization
    clean_text = clean_text.replace(" - ", " : ")
    clean_text = re.sub(r'(?m)^\s*[-*]\s+', '• ', clean_text)

    # prepare extra phrase patterns
    extra_patterns = []
    if extra_phrases:
        for p in extra_phrases:
            if any(ch in p for ch in r".^$*+?{}[]\|()"):
                extra_patterns.append(p)
            else:
                extra_patterns.append(re.escape(p))

    lines = clean_text.splitlines()
    n = len(lines)
    i = 0
    paragraph_html = []

    def collect_continuation(start_idx):
        """Collect continuation lines for block-style headings (indented or starting lowercase)."""
        block_lines = [lines[start_idx].rstrip()]
        j = start_idx + 1
        while j < n:
            next_line = lines[j]
            if not next_line.strip():  # paragraph boundary
                break
            if re.match(r'^\s+', next_line) or re.match(r'^\s*[a-z]', next_line):
                block_lines.append(next_line.rstrip())
                j += 1
                continue
            if re.match(r'^\s*(?:•|-|\d+\.)\s+', next_line):
                break
            break
        return block_lines, j

    while i < n:
        ln = lines[i].rstrip()
        if not ln.strip():
            paragraph_html.append('')  # paragraph break marker
            i += 1
            continue

        # 1) extra phrases (inline replacements)
        if extra_patterns:
            new_ln = ln
            for pat in extra_patterns:
                try:
                    new_ln = re.sub(pat, lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
                except re.error:
                    new_ln = re.sub(re.escape(pat), lambda m: f"<strong>{m.group(0)}</strong>", new_ln, flags=re.IGNORECASE)
            if new_ln != ln:
                paragraph_html.append(new_ln)
                i += 1
                continue

        # 2) Step N: anywhere -> bold entire block (line + continuation)
        if re.search(r'(Step\s*\d+\s*:)', ln, flags=re.IGNORECASE):
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong>{block_text}</strong>")
            i = j
            continue

        # 3) Numbered heading WITH colon: bold only left-of-colon (the numbered heading)
        m_num_colon = re.match(r'^\s*(\d+\.\s+[^:]+):\s*(.*)$', ln)
        if m_num_colon:
            heading = m_num_colon.group(1).strip()
            remainder = m_num_colon.group(2).strip()
            if remainder:
                paragraph_html.append(f"<strong>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"<strong>{heading}:</strong>")
            i += 1
            continue

        # 4) Numbered heading WITHOUT colon: bold whole block (line + continuation) — previous behavior
        m_num_no_colon = re.match(r'^\s*(\d+\.\s+.+)$', ln)
        if m_num_no_colon:
            block, j = collect_continuation(i)
            block_text = "<br>".join([b.strip() for b in block])
            paragraph_html.append(f"<strong>{block_text}</strong>")
            i = j
            continue

        # 5) Bullet/heading with colon (non-numbered): bold left-of-colon
        m_bullet_heading = re.match(r'^\s*(?:•|\d+\.)\s*([^:]+):\s*(.*)$', ln)
        if m_bullet_heading:
            heading = m_bullet_heading.group(1).strip()
            remainder = m_bullet_heading.group(2).strip()
            if remainder:
                paragraph_html.append(f"• <strong>{heading}:</strong> {remainder}")
            else:
                paragraph_html.append(f"• <strong>{heading}:</strong>")
            i += 1
            continue

        # 6) Generic inline heading "LeftOfColon: rest" -> bold left-of-colon if short
        m_side = re.match(r'^\s*([^:]+):\s*(.*)$', ln)
        if m_side and len(m_side.group(1).split()) <= 8:
            left = m_side.group(1).strip()
            right = m_side.group(2).strip()
            paragraph_html.append(f"<strong>{left}:</strong> {right}" if right else f"<strong>{left}:</strong>")
            i += 1
            continue

        # 7) Full-line special-case "Revenue Growth Rate"
        if re.fullmatch(r'\s*Revenue\s+Growth\s+Rate\s*', ln, flags=re.IGNORECASE):
            paragraph_html.append(f"<strong>{ln.strip()}</strong>")
            i += 1
            continue

        # default
        paragraph_html.append(ln)
        i += 1

    # group into paragraphs
    final_paragraphs = []
    temp_lines = []
    for entry in paragraph_html:
        if entry == '':
            if temp_lines:
                final_paragraphs.append("<br>".join(temp_lines))
                temp_lines = []
        else:
            temp_lines.append(entry)
    if temp_lines:
        final_paragraphs.append("<br>".join(temp_lines))

    para_wrapped = [f"<p style='margin:6px 0; line-height:1.45; font-size:0.98rem;'>{p}</p>" for p in final_paragraphs]
    final_html = "\n".join(para_wrapped)

    formatted_output = f"""
    <div style="
        background: var(--bg-card);
        border: 1px solid rgba(139,30,30,0.06);
        border-radius: 10px;
        padding: 12px 14px;
        font-family: Inter, sans-serif;
        color: var(--text-primary);
        max-height: 650px;
        overflow-y: auto;
        white-space: normal;
        word-break: break-word;
    ">
        {final_html}
    </div>
    """

    formatted_output = re.sub(r'(<br>\s*){3,}', '<br><br>', formatted_output)
    return formatted_output

def init_session_state():
    defaults = {
        "current_page": "page1",
        "problem_text": "",
        "industry": "Select Industry",
        "account": "Select Account",
        "account_input": "",
        "outputs": {},
        "analysis_complete": False,
        "dimension_scores": {
            "Volatility": 0.0,
            "Ambiguity": 0.0, 
            "Interconnectedness": 0.0,
            "Uncertainty": 0.0
        },
        "question_scores": {},
        "hardness_level": None,
        "overall_score": 0.0,
        "summary": "",
        "current_system_full": "",
        "input_text": "",
        "output_text": "",
        "pain_points_text": "",
        "hardness_summary_text": "",
        "show_vocabulary": False,
        "industry_updated": False,
        "feedback_submitted": False,  # NEW: Track if feedback has been submitted
        "user_info_collected": False,  # NEW: Track if user info was collected during analysis
        "analysis_account": "",  # NEW: Store account at analysis time
        "analysis_industry": "",  # NEW: Store industry at analysis time
        "validation_attempted": False  # NEW: Track if user attempted to extract without valid inputs
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def reset_app_state():
    """Completely reset session state to initial values"""
    # Clear all session state
    keys_to_preserve = ['dark_mode']  # Preserve theme setting
    preserved_state = {key: st.session_state[key] for key in keys_to_preserve if key in st.session_state}
    
    st.session_state.clear()
    
    # Restore preserved state
    for key, value in preserved_state.items():
        st.session_state[key] = value
    
    # Re-initialize with defaults
    init_session_state()
    
    st.success("✅ Application reset successfully! You can start a new analysis.")

def submit_feedback(feedback_type, name="", email="", off_definitions="", additional_feedback="", suggestions=""):
    """Submit feedback to CSV file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get context data
    account = st.session_state.get("analysis_account", "")
    industry = st.session_state.get("analysis_industry", "")
    # NEW: Get the problem statement
    problem_statement = st.session_state.get("problem_text", "")
    
    new_entry = pd.DataFrame([[
        timestamp, name, email, additional_feedback, feedback_type, off_definitions, suggestions, account, industry, problem_statement
    ]], columns=["Timestamp", "Name", "Email", "Feedback", "FeedbackType", "OffDefinitions", "Suggestions", "Account", "Industry", "ProblemStatement"])
    
    try:
        if os.path.exists(FEEDBACK_FILE):
            existing = pd.read_csv(FEEDBACK_FILE)
            
            # Handle schema mismatch (e.g. if 'ProblemStatement' is missing in existing file)
            missing_cols = set(new_entry.columns) - set(existing.columns)
            for col in missing_cols:
                existing[col] = '' # Add missing columns to existing with default value
            
            # Reorder existing columns to match the new entry's order
            existing = existing[new_entry.columns]

            updated = pd.concat([existing, new_entry], ignore_index=True)
        else:
            updated = new_entry
        
        updated.to_csv(FEEDBACK_FILE, index=False)
        st.session_state.feedback_submitted = True
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {str(e)}")
        return False

init_session_state()

# -----------------------------
# PAGE 1: Business Problem Input & Analysis (Structural Fix Applied here)
# -----------------------------

# If admin_view_selected is true, we ONLY show the admin sections
# Otherwise, we show the main page logic.

if not st.session_state.get('admin_view_selected', False) or st.session_state.get('current_page', 'page1') == 'page1':
    # This block renders the main UI and processing (Page 1 content)
    
    if st.session_state.current_page == "page1":
    # ---- Page Title ----
        st.markdown("""
        <div class="page-title" style="text-align:center; margin-bottom:1.2rem;">
            <h1 style="font-weight:800; color:#ffffff;">Business Problem Vocabulary Assistant</h1>
            <p class="page-subtitle">
            Identify key terms and context of your business problem instantly.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # ---- Account & Industry ----
        st.markdown('<div class="section-title-box"><h3>Account & Industry</h3></div>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        
        with col1:
            # Safely fetch current account
            current_account = st.session_state.get('account', 'Select Account')
            try:
                current_account_index = ACCOUNTS.index(current_account)
            except (ValueError, AttributeError):
                current_account_index = 0

            # Account dropdown - UNIQUE KEY
            selected_account = st.selectbox(
                "Select Account:",
                options=ACCOUNTS,
                index=current_account_index,
                key="account_selector_main"
            )

            # Auto-map logic with rerun
            if selected_account != st.session_state.get('account'):
                st.session_state.account = selected_account
                if selected_account in ACCOUNT_INDUSTRY_MAP:
                    st.session_state.industry = ACCOUNT_INDUSTRY_MAP[selected_account]
                    st.session_state.industry_updated = True
                st.rerun()

        with col2:
            # Safely fetch current industry
            current_industry = st.session_state.get('industry', 'Select Industry')
            try:
                current_industry_index = INDUSTRIES.index(current_industry)
            except (ValueError, AttributeError):
                current_industry_index = 0

            # Dynamic key ensures dropdown refreshes when mapping changes
            industry_key = f"industry_selector_main_{current_industry}"

            selected_industry = st.selectbox(
                "Industry:",
                options=INDUSTRIES,
                index=current_industry_index,
                key=industry_key,
                disabled=(st.session_state.get('account', 'Select Account') == "Select Account")
            )

            if selected_industry != st.session_state.get('industry'):
                st.session_state.industry = selected_industry
                st.rerun()

        # ---- Business Problem ----
        st.markdown('<div class="section-title-box"><h3>Business Problem Description</h3></div>', unsafe_allow_html=True)
        st.session_state.problem_text = st.text_area(
            "Describe your business problem in detail:",
            value=st.session_state.get("problem_text", ""),
            height=180,
            placeholder="Feel free to just type down your problem statement, or copy-paste if you have it handy somewhere...",
            label_visibility="collapsed",
            key="problem_text_area"
        )

        # ---- Validation Helper Function ----
        def is_valid_problem_text(text):
            """Check if problem text is meaningful (not just random characters)"""
            if not text or len(text.strip()) < 20:
                return False
            # Check if text has at least 3 words
            words = text.strip().split()
            if len(words) < 3:
                return False
            # Check if text contains mostly random characters (no vowels pattern)
            vowels = set('aeiouAEIOU')
            has_vowels = any(c in vowels for c in text)
            if not has_vowels:
                return False
            return True

        # ---- Validation checks ----
        is_account_selected = st.session_state.account != "Select Account"
        is_industry_selected = st.session_state.industry != "Select Industry"
        has_problem_text = bool(st.session_state.problem_text.strip())
        is_valid_problem = is_valid_problem_text(st.session_state.problem_text)
        
        # Display validation warnings only after user attempts to extract
        if not st.session_state.analysis_complete and st.session_state.validation_attempted:
            warning_messages = []
            if not is_account_selected:
                warning_messages.append("⚠️ Please select an account")
            if not is_industry_selected:
                warning_messages.append("⚠️ Please select an industry")
            if has_problem_text and not is_valid_problem:
                warning_messages.append("⚠️ Please enter a valid business problem description (minimum 20 characters with meaningful content)")
            elif not has_problem_text:
                warning_messages.append("⚠️ Please enter a business problem description")
            
            if warning_messages:
                for msg in warning_messages:
                    st.warning(msg)

        # ---- Buttons ----
        if not st.session_state.analysis_complete:
            # Full width Extract vocabulary button
            analyze_btn = st.button(
                "Extract vocabulary",
                type="primary",
                use_container_width=True,
                disabled=not (
                    st.session_state.problem_text.strip()
                    and st.session_state.account != "Select Account"
                    and st.session_state.industry != "Select Industry"
                ),
                key="analyze_btn"
            )

        # ---- Analysis Action ----
        if not st.session_state.analysis_complete and 'analyze_btn' in locals() and analyze_btn:
            # Set validation attempted flag
            st.session_state.validation_attempted = True
            
            # Final validation before processing
            if not is_account_selected:
                st.error("❌ Please select an account before proceeding.")
                st.stop()
            
            if not is_industry_selected:
                st.error("❌ Please select an industry before proceeding.")
                st.stop()
            
            if not has_problem_text:
                st.error("❌ Please enter a business problem description.")
                st.stop()
            
            if not is_valid_problem:
                st.error("❌ Please enter a valid business problem description with meaningful content (minimum 20 characters).")
                st.stop()

            # ✅ COLLECT USER INFORMATION AT ANALYSIS TIME
            st.session_state.analysis_account = st.session_state.account
            st.session_state.analysis_industry = st.session_state.industry
            st.session_state.user_info_collected = True

            full_context = f"""
            Business Problem:
            {st.session_state.problem_text.strip()}

            Context:
            Account: {st.session_state.account}
            Industry: {st.session_state.industry}
            """

            # Prepare headers
            HEADERS = HEADERS_BASE.copy()
            HEADERS.update({"Tenant-ID": TENANT_ID, "X-Tenant-ID": TENANT_ID})
            if AUTH_TOKEN:
                HEADERS["Authorization"] = f"Bearer {AUTH_TOKEN}"

            with st.spinner("🔍 Extracting vocabulary and analyzing context..."):
                progress = st.progress(0)
                st.session_state.outputs = {}
                session = requests.Session()
                total = len(API_CONFIGS)

                for i, api_cfg in enumerate(API_CONFIGS):
                    progress.progress(i / total)
                    if api_cfg["name"] != "vocabulary":
                        continue  # run only vocabulary in this mode
                    try:
                        goal = api_cfg["prompt"](full_context, {})
                        resp = session.post(api_cfg["url"], headers=HEADERS, json={"agency_goal": goal})
                        if resp.status_code == 200:
                            text = sanitize_text(json_to_text(resp.json()))
                        else:
                            text = f"API Error {resp.status_code}"
                        st.session_state.outputs["vocabulary"] = text
                    except Exception as e:
                        st.session_state.outputs["vocabulary"] = f"Error: {str(e)}"

                progress.progress(1.0)
                session.close()
                st.session_state.analysis_complete = True
                st.session_state.show_vocabulary = True
                
                # Store vocabulary in a temporary file as backup for admin access
                try:
                    import tempfile
                    vocab_backup_file = os.path.join(tempfile.gettempdir(), "streamlit_vocab_backup.txt")
                    with open(vocab_backup_file, 'w', encoding='utf-8') as f:
                        f.write(st.session_state.outputs.get("vocabulary", ""))
                except Exception:
                    pass  # Silently fail if file write doesn't work
                
                st.success("✅ Vocabulary extraction complete!")
                st.rerun()

    # ---- Show Vocabulary Directly After Analysis ----
    if st.session_state.analysis_complete:
        # Anchor for feedback/vocabulary section so ?openFeedback=true#feedback-section works
        st.markdown('<div id="feedback-section"></div>', unsafe_allow_html=True)

        # Client-side scroll helper: ensure hash targets scroll into view after Streamlit reruns
        try:
            scroll_script = """
            <script>
            (function(){
                // small delay to let Streamlit finish rendering
                function scrollToHash(){
                    try{
                        var h = window.location.hash;
                        if(!h) return;
                        // support both admin-section and feedback-section
                        var id = h.replace('#','');
                        var el = document.getElementById(id);
                        if(el){
                            // use scrollIntoView with smooth behavior when possible
                            setTimeout(function(){ el.scrollIntoView({behavior: 'smooth', block: 'start'}); }, 120);
                        }
                    }catch(e){console.log('scrollToHash error', e)}
                }

                // run once on load
                if (document.readyState === 'complete') {
                    scrollToHash();
                } else {
                    window.addEventListener('load', scrollToHash, {once:true});
                }

                // also observe mutations and try again (handles Streamlit dynamic DOM updates)
                var obs = new MutationObserver(function(m){
                    if(window.location.hash){
                        scrollToHash();
                    }
                });
                obs.observe(document.body, {childList:true, subtree:true});
            })();
            </script>
            """
            import streamlit.components.v1 as components
            components.html(scroll_script, height=0)
        except Exception:
            pass
        vocab_text = st.session_state.outputs.get("vocabulary", "")
        
        # ✅ Step 1: Get the pre-formatted HTML from your function
        formatted_vocab = format_vocabulary_with_bold(vocab_text)

        # ✅ Step 2: Clean HTML entities (important!)
        formatted_vocab = html.unescape(formatted_vocab)
        formatted_vocab = formatted_vocab.replace("<", "<").replace(">", ">") # Re-escape HTML tags

        # ✅ Step 3: Dynamically get account & industry for substitutions
        account_name = st.session_state.get("analysis_account", "").strip()
        industry_name = st.session_state.get("analysis_industry", "").strip()

        # ✅ Step 4: Replace generic mentions in the ALREADY FORMATTED HTML
        if account_name:
            # Use a more careful replacement that preserves HTML tags
            formatted_vocab = re.sub(
                r'\bthe company\b', 
                account_name, 
                formatted_vocab, 
                flags=re.IGNORECASE
            )
        if industry_name:
            formatted_vocab = re.sub(
                r'\bthe industry\b', 
                industry_name, 
                formatted_vocab, 
                flags=re.IGNORECASE
            )

        # ✅ Step 5: Fallback display names for header
        display_account = account_name if account_name else "the company"
        display_industry = industry_name if industry_name else "the industry"

        # ---- Section Title & Subheading ----
        st.markdown(f"""
            <div class="section-title-box" style="text-align:center; margin-top:0.5rem !important;">
                <div style="display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    <h3 style="
                        margin-bottom:8px;
                        color:white;
                        font-weight:800;
                        font-size:1.4rem;
                        line-height:1.2;
                    ">
                        Vocabulary
                    </h3>
                    <p style="
                        font-size:0.95rem;  
                        color:white;  
                        margin:0;
                        line-height:1.5;
                        text-align:center;
                        max-width: 800px;
                    ">
                        Please note that it is an <strong>AI-generated Vocabulary</strong>, derived from  
                        the <em>company</em> <strong>{display_account}</strong> and  
                        the <em>industry</em> <strong>{display_industry}</strong> based on the  
                        <em>problem statement</em> you shared.<br>
                        In case you find something off, there's a provision to share feedback at the bottom  
                        we encourage you to use it.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # ✅ Step 6: DIRECTLY render the formatted HTML (no extra wrapping)
        st.markdown(formatted_vocab, unsafe_allow_html=True)

        # ========================
        # 💬 ENHANCED FEEDBACK FORM (SHOW ONLY AFTER ANALYSIS)
        # ========================
        
        # Show feedback section if not submitted OR if user wants to submit again
        show_feedback = not st.session_state.get('feedback_submitted', False)
        
        if show_feedback:
            st.markdown("---")
            st.markdown("""
                <div class="section-title-box" style="text-align:center;">
                    <h3>💬 User Feedback</h3>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("Please share your thoughts or suggestions after reviewing the vocabulary results.")

            # ✅ INITIALIZE FEEDBACK STATE - NO OPTION SELECTED INITIALLY
            if 'feedback_option' not in st.session_state:
                st.session_state.feedback_option = None

            # Radio buttons for feedback type - NO DEFAULT SELECTION
            feedback_option = st.radio(
                "Select your feedback type:",
                options=[
                    "I have read it, found it useful, thanks.",
                    "I have read it, found some definitions to be off.",
                    "The widget seems interesting, but I have some suggestions on the features."
                ],
                key="feedback_radio",
                index=None  # ✅ NO DEFAULT SELECTION
            )

            # Update session state when user selects an option
            if feedback_option != st.session_state.feedback_option:
                st.session_state.feedback_option = feedback_option
            
            # Form 1: Positive Feedback (Now collects Name/Email)
            if feedback_option == "I have read it, found it useful, thanks.":
                with st.form("feedback_form_1_positive", clear_on_submit=True):
                    st.info("Thank you for your positive feedback! Optional: Share your name and email.")
                    
                    # Show account and industry from analysis
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Account", value=st.session_state.get("analysis_account", ""), disabled=True, key="account_pos")
                    with col2:
                        st.text_input("Industry", value=st.session_state.get("analysis_industry", ""), disabled=True, key="industry_pos")
                    
                    name = st.text_input("Your Name (optional)", key="name_pos")
                    email = st.text_input("Your Email (optional)", key="email_pos")
                    
                    submitted = st.form_submit_button("📨 Submit Positive Feedback")
                    
                    if submitted:
                        if submit_feedback(feedback_type=feedback_option, name=name, email=email):
                            st.success("✅ Thank you! Your positive feedback has been recorded.")
            
            # Form 2: Definitions Off
            elif feedback_option == "I have read it, found some definitions to be off.":
                with st.form("feedback_form_2", clear_on_submit=True):
                    st.markdown("**Please select which sections have definitions that seem off:**")
                
                    # Show account and industry from analysis
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Account", value=st.session_state.get("analysis_account", ""), disabled=True, key="account_def")
                    with col2:
                        st.text_input("Industry", value=st.session_state.get("analysis_industry", ""), disabled=True, key="industry_def")
                    
                    name = st.text_input("Your Name")
                    email = st.text_input("Your Email (optional)")
                
                    # Extract vocabulary sections dynamically
                    vocab_text = st.session_state.outputs.get("vocabulary", "")
                    
                    # Parse vocabulary to extract Step headings
                    step_sections = {}
                    if vocab_text:
                        # Extract Step N: headings with their content
                        step_pattern = r'(Step\s*(\d+)\s*:\s*([^\n]+))'
                        matches = re.finditer(step_pattern, vocab_text, re.IGNORECASE)
                        
                        for match in matches:
                            step_num = match.group(2)
                            step_title = match.group(3).strip()
                            step_key = f"Step {step_num}"
                            step_sections[step_key] = step_title
                    
                    # If no steps found or less than 5, create generic options
                    if len(step_sections) == 0:
                        step_sections = {
                            "Step 1": "Key Performance Indicators (KPIs)",
                            "Step 2": "Technical Definitions",
                            "Step 3": "Industry Context",
                            "Step 4": "Business Metrics",
                            "Step 5": "Strategic Implications"
                        }
                    
                    # Create 5 multiselect dropdowns for each step
                    st.markdown("### Select problematic sections:")
                    
                    selected_issues = {}
                    for i in range(1, 6):
                        step_key = f"Step {i}"
                        step_title = step_sections.get(step_key, f"Section {i}")
                        
                        # Extract sub-headings (numbered items under each step)
                        sub_items = []
                        if vocab_text:
                            # Look for numbered items (1. Item, 2. Item, etc.) in the vocabulary
                            # This will find items like "1. Revenue Growth Rate:", "2. Market Share:", etc.
                            step_section_match = re.search(
                                rf'Step\s*{i}\s*:.*?(?=Step\s*\d+\s*:|$)',
                                vocab_text,
                                re.IGNORECASE | re.DOTALL
                            )
                            
                            if step_section_match:
                                step_content = step_section_match.group(0)
                                # Extract numbered sub-items
                                sub_item_pattern = r'^\s*(\d+)\.\s+([^:\n]+)'
                                sub_matches = re.finditer(sub_item_pattern, step_content, re.MULTILINE)
                                
                                for sub_match in sub_matches:
                                    item_text = sub_match.group(2).strip()
                                    # Clean up any extra formatting
                                    item_text = re.sub(r'<[^>]+>', '', item_text)  # Remove HTML tags
                                    item_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', item_text)  # Remove bold markers
                                    sub_items.append(item_text)
                        
                        # If no sub-items found, add just the step heading as an option
                        if not sub_items:
                            sub_items = [f"{step_title} - General"]
                        
                        # Special handling for Step 5 (usually a paragraph)
                        if i == 5 and not sub_items:
                            sub_items = [f"{step_key}: {step_title}"]
                        
                        # Create multiselect for this step
                        selected = st.multiselect(
                            f"**{step_key}: {step_title}**",
                            options=sub_items,
                            key=f"step_{i}_issues",
                            help=f"Select items from {step_key} that have definition issues"
                        )
                        
                        if selected:
                            selected_issues[step_key] = selected
                
                    additional_feedback = st.text_area(
                        "Additional comments:", 
                        placeholder="Please provide more details about the definition issues you found..."
                    )
                
                    submitted = st.form_submit_button("📨 Submit Feedback")
                
                    if submitted:
                        if not selected_issues:
                            st.warning("⚠️ Please select at least one section/item that has definition issues.")
                        else:
                            # Format the selected issues for CSV storage
                            issues_list = []
                            for step, items in selected_issues.items():
                                for item in items:
                                    issues_list.append(f"{step} - {item}")
                            
                            off_defs_text = " | ".join(issues_list)
                        
                            if submit_feedback(
                                feedback_type=feedback_option,
                                name=name,
                                email=email,
                                off_definitions=off_defs_text,
                                additional_feedback=additional_feedback
                            ):
                                st.success("✅ Thank you! Your feedback has been submitted.")

            # Form 3: Suggestions
            elif feedback_option == "The widget seems interesting, but I have some suggestions on the features.":
                with st.form("feedback_form_3", clear_on_submit=True):
                    st.markdown("**Please share your suggestions for improvement:**")
                
                    # Show account and industry from analysis
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Account", value=st.session_state.get("analysis_account", ""), disabled=True, key="account_sug")
                    with col2:
                        st.text_input("Industry", value=st.session_state.get("analysis_industry", ""), disabled=True, key="industry_sug")
                    
                    name = st.text_input("Your Name")
                    email = st.text_input("Your Email (optional)")
                
                    suggestions = st.text_area(
                        "Your suggestions:",
                        placeholder="What features would you like to see improved or added?",
                        key="suggestions_textarea" 
                    )
                
                    submitted = st.form_submit_button("📨 Submit Feedback")
                
                    if submitted:
                        if not suggestions.strip():
                            st.warning("⚠️ Please provide your suggestions.")
                        else:
                            if submit_feedback(
                                feedback_type=feedback_option,
                                name=name,
                                email=email,
                                suggestions=suggestions
                            ):
                                st.success("✅ Thank you! Your feedback has been submitted.")
                                # Hide feedback form after submission
                                st.rerun()

        else:
            # Feedback already submitted - show thank you message and option to submit again
            st.markdown("---")
            st.success("✅ Thank you! Your feedback has been recorded.")
            st.info("💡 If you'd like to provide additional feedback after reviewing the vocabulary again, click below.")
            
            if st.button("📝 Submit Additional Feedback", key="reopen_feedback_btn"):
                st.session_state.feedback_submitted = False
                st.rerun()

        # ========================
        # 📥 VOCABULARY DOWNLOAD SECTION
        # ========================
        st.markdown("---")
        st.markdown("""
            <div class="section-title-box" style="text-align:center;">
                <h3>📥 Download Vocabulary</h3>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("**Would you like to download this vocabulary?**")

        # Get the vocabulary text for download
        vocab_text = st.session_state.outputs.get("vocabulary", "") if st.session_state.get("analysis_complete", False) else ""

        if vocab_text:
            # Create downloadable content
            account_name = st.session_state.get("analysis_account", "Unknown Company")
            industry_name = st.session_state.get("analysis_industry", "Unknown Industry")
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"vocabulary_{account_name.replace(' ', '_')}_{timestamp}.txt"
            
            # Format the content for download
            download_content = f"""Vocabulary Export
    Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    Company: {account_name}
    Industry: {industry_name}

    {vocab_text}

    ---
    Generated by Vocabulary Analysis Tool
    """
            
            st.download_button(
                label="⬇️ Download Vocabulary as Text File",
                data=download_content,
                file_name=filename,
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.info("No vocabulary available for download. Please complete the analysis first.")
        
        # ========================
        # 🔄 NEW ANALYSIS BUTTON (Below Download) - Full Width
        # ========================
        st.markdown("---")
        if st.button("🔄 New Analysis", type="primary", key="new_analysis_btn", use_container_width=True):
            reset_app_state()
            st.rerun()


# ========================
# 🧩 ADMIN SECTION (DOWNLOAD REPORTS)
# ========================
# Renders the admin panel directly if current_page is set to 'admin'
if st.session_state.get('current_page', '') == 'admin':
    st.markdown("---")
    # anchor for hash navigation
    st.markdown('<div id="admin-section"></div>', unsafe_allow_html=True)
    st.subheader("📊 Admin Section (Download Reports)")

    # Small back button to return to main app
    if st.button("← Back to app", key="admin_back_btn"):
        st.session_state.current_page = 'page1'
        st.session_state.show_admin_panel = False
        st.session_state.admin_view_selected = False
        st.session_state.admin_authenticated = False
        # Clear query params to ensure clean navigation
        st.query_params.clear()
        st.rerun() 

    # Show password input only inside admin section
    password = st.text_input("Enter admin password:", type="password", key="admin_password")

    # Load admin password from Streamlit secrets or environment variable for security
    try:
        secret_admin_pw = st.secrets.get("admin_password") if hasattr(st, 'secrets') else None
    except Exception:
        secret_admin_pw = None

    env_admin_pw = os.environ.get("ADMIN_PASSWORD")
    ADMIN_PASSWORD = secret_admin_pw or env_admin_pw or "admin123"

    # Authenticate
    if password and password == ADMIN_PASSWORD:
        st.session_state.admin_authenticated = True
        st.success("Access granted ✅")
    
        # Admin download options - Full width for feedback report only
        st.markdown("**📋 Feedback Report**")
        
        if os.path.exists(FEEDBACK_FILE):
            try:
                # Read the file with the expected schema, allowing missing columns to be inferred
                df = pd.read_csv(FEEDBACK_FILE) 
            except Exception as e:
                st.error(f"Error reading feedback file: {e}")
                df = None

            if df is not None and not df.empty:
                # Add filter dropdown
                filter_option = st.selectbox(
                    "Filter by feedback type:",
                    options=[
                        "All",
                        "I have read it, found it useful, thanks.",
                        "I have read it, found some definitions to be off.",
                        "The widget seems interesting, but I have some suggestions on the features."
                    ],
                    key="admin_feedback_filter"
                )
                
                # Apply filter
                if filter_option == "All":
                    filtered_df = df.copy()
                else:
                    filtered_df = df[df['FeedbackType'] == filter_option]
                
                # Show count
                st.info(f"Showing {len(filtered_df)} of {len(df)} feedback entries")
                
                # Display filtered feedback data table - fit to full page width
                st.markdown("### 📋 User Feedback")
                st.dataframe(filtered_df, use_container_width=True, height=500)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Download filtered feedback
                feedback_csv = filtered_df.to_csv(index=False).encode("utf-8")
                download_filename = f"feedback_report_{filter_option.replace(' ', '_').replace('.', '').replace(',', '')}.csv"
                
                st.download_button(
                    "⬇️ Download Filtered Feedback Report",
                    feedback_csv,
                    download_filename,
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.info("No feedback data available (file is empty or unreadable).")
        else:
            st.info("Feedback file not found. No feedback has been submitted yet.")

    elif password and password != "":
        st.session_state.admin_authenticated = False
        st.error("❌ Invalid password. Access denied.")
