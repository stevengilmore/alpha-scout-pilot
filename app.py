import os
import requests
import pandas as pd
import yfinance as yf
import streamlit as st
import concurrent.futures
from google import genai
from google.genai import types
from streamlit_confetti import confetti
from datetime import datetime

# --- 1. SELF-HEALING CONFIG & KEYS ---
session = requests.Session()
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"}

# Multi-stage Fallback for 2026 Model IDs
MODELS_TO_TRY = ["gemini-2.0-flash", "gemini-2.0-flash-001", "gemini-1.5-flash"]

# Key Detection: Checks Render Env and Streamlit Secrets
GEMINI_KEY = (
    os.environ.get("GEMINI_KEY") or 
    os.environ.get("GOOGLE_API_KEY") or 
    st.secrets.get("GEMINI_KEY")
)

if not GEMINI_KEY:
    st.error("🚨 API Key Missing: Please add 'GEMINI_KEY' to your Render Environment Variables.")
    st.stop()

client = genai.Client(api_key=GEMINI_KEY)

AGENT_ROLES = {
    "🐂 Opportunistic Scout": "Analyze catalysts & upside. Explain logic. End with VOTE: BUY/NO.",
    "📈 Growth Specialist": "Analyze revenue & momentum. Explain logic. End with VOTE: BUY/NO.",
    "🐻 Risk Auditor": "Identify red flags (debt, volatility). List rejection reasons. End with VOTE: BUY/NO."
}

# --- 2. GLOBAL DATA ENGINES ---
@st.cache_data(ttl=86400)
def get_tickers(index_name):
    if index_name == "Top Crypto":
        return ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "AVAX-USD", "LINK-USD"]
    urls = {
        "S&P 500": "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
        "Nasdaq-100": "https://en.wikipedia.org/wiki/Nasdaq-100",
        "DAX": "https://en.wikipedia.org/wiki/DAX"
    }
    try:
        res = session.get(urls[index_name], headers=HEADERS, timeout=10)
        tables = pd.read_html(res.text)
        if index_name == "S&P 500": return tables[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        if index_name == "Nasdaq-100": return tables[4]['Ticker'].tolist()
        if index_name == "DAX": return tables[4]['Ticker'].tolist()
    except: return []

@st.cache_data(ttl=3600)
def get_intel(tickers, is_crypto=False):
    data = []
    for t in tickers[:15]: 
        try:
            info = yf.Ticker(t).info
            score = info.get('recommendationMean', 2.0 if is_crypto else 5.0)
            curr = info.get('regularMarketPrice') or info.get('currentPrice')
            target = info.get('targetMeanPrice', curr * 1.15 if is_crypto else 0)
            if curr:
                upside = ((target - curr) / curr * 100) if target else 0
                rank = 3 if upside > 15 and score < 2.2 else 2 if upside > 5 else 1
                data.append({
                    "Ticker": t, "Company": info.get('shortName') or info.get('longName', t),
                    "Price": curr, "Upside %": round(upside, 1),
                    "Score": score, "AI Favor": "HIGH 🔥" if rank == 3 else "MED ⚖️" if rank == 2 else "LOW",
                    "rank": rank
                })
        except: continue
    if not data: return pd.DataFrame()
    # SORTING: AI Favor first, then Institutional Score [cite: 3.4
