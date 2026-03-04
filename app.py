import streamlit as st
import os
import requests
import yfinance as yf
import pandas as pd
from google import genai
from datetime import datetime, timedelta

# --- 1. CONFIG & ULTRA-READABLE STYLING ---
st.set_page_config(page_title="Momentum Master Terminal", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .main { background-color: #0d1117; color: #ffffff !important; }
    [data-testid="stSidebar"] { background-color: #161b22 !important; border-right: 1px solid #30363d; }
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #ffffff !important; font-weight: 700 !important; font-size: 1.1rem !important;
    }
    .stAlert { background-color: #1c2128 !important; color: #ffffff !important; border: 2px solid #58a6ff !important; }
    .stAlert p, .stAlert li, .stAlert span, .stAlert div { color: #ffffff !important; font-weight: 500 !important; }
    .stMetric { background-color: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

# UPDATED 2026 MODEL POOL (Removing retired 2.0 models)
MODEL_POOL = ["gemini-3-flash", "gemini-2.5-flash", "gemini-3.1-flash-lite-preview"]

GEMINI_KEY = os.environ.get("GEMINI_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# --- 2. THE TOOLS ---
def send_telegram(message):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": f"🛰️ *MOMENTUM MASTER BRIEFING*\n---\n{message}", "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
        return True
    except: return False

@st.cache_data(ttl=300)
def get_clean_data(tickers):
    data = []
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            price = tk.fast_info['last_price']
            name = tk.info.get('longName') or t
            hist = tk.history(period="3mo")
            mom = ((hist['Close
