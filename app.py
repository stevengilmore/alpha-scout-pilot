import os
import sys
import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from fear_and_greed import FearGreedIndex #
from google import genai
from google.genai import types

# --- 1. SETUP ---
def get_secret(key):
    val = os.environ.get(key)
    if val: return val
    try:
        if key in st.secrets: return st.secrets[key]
    except: pass
    return None

GEMINI_KEY = get_secret("GEMINI_KEY")
client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

WATCHLIST = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "PYPL", "DIS", "F", "INTC", "BABA", "PLTR", "SQ"]

# --- 2. SENTIMENT & MARKET DATA ---
@st.cache_data(ttl=3600)
def get_market_sentiment():
    """Fetches CNN Fear & Greed Index"""
    try:
        # Returns (value, description, last_update)
        data = FearGreedIndex().get() 
        return {
            "value": int(data.value),
            "feeling": data.description.upper(),
            "update": data.last_update.strftime("%Y-%m-%d")
        }
    except:
        return {"value": 50, "feeling": "NEUTRAL", "update": "N/A"}

@st.cache_data(ttl=3600)
def get_top_12_analysts(tickers):
    data_list = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            info = stock.info
            curr = info.get('currentPrice', 0)
            target = info.get('targetMeanPrice', 0)
            upside = ((target - curr) / curr) * 100 if curr > 0 and target > 0 else 0
            
            data_list.append({
                "Ticker": t,
                "Name": info.get('longName', t),
                "Price": curr,
                "Target": target,
                "Upside %": round(upside, 2),
                "Rating": info.get('recommendationMean', 5.0) # 1=Strong Buy, 5=Sell
            })
        except: continue
    return pd.DataFrame(data_list).sort_values("Rating").head(12)

# --- 3. UI LAYOUT ---
st.set_page_config(page_title="Alpha Scout Pro", layout="wide")

# HEADER: MARKET SENTIMENT
sentiment = get_market_sentiment()
col_title, col_fng = st.columns([2, 1])

with col_title:
    st.title("🛰️ Alpha Scout: Command Center")
    st.caption(f"Last Market Intel Refresh: {sentiment['update']}")

with col_fng:
    # Color mapping for sentiment
    color = "red" if sentiment['value'] < 40 else "orange" if sentiment['value'] < 60 else "green"
    st.metric(label=f"FEAR & GREED: {sentiment['feeling']}", value=sentiment['value'], delta_color="normal")
    st.progress(sentiment['value'] / 100) # Visual bar

st.divider()

# SECTION 1: TOP 12 ANALYST RANKINGS
st.header("📊 Wall Street Consensus: Top 12")
with st.spinner("Ranking analysts' top picks..."):
    df = get_top_12_analysts(WATCHLIST)
    def style_upside(v):
        return f"color: {'green' if v > 0 else 'red'}; font-weight: bold"
    
    st.dataframe(
        df.style.map(style_upside, subset=['Upside %']).format({"Price":"${:.2f}", "Target":"${:.2f}", "Upside %":"{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

st.divider()

# SECTION 2: AI AUDIT
st.header("🤖 Multi-Agent Committee Audit")
if st.button("🚀 RUN LIVE AGENT DEBATE"):
    with st.status("Agents are debating..."):
        # Audit top picks from the analyst list
        results = []
        for t in df['Ticker'].head(6): 
            try:
                res = client.models.generate_content(model="gemini-2.0-flash", contents=f"Audit {t}")
                vote = "BUY" if "BUY" in res.text.upper() else "HOLD/NO"
                results.append({"Ticker": t, "Committee Vote": vote})
            except: continue
        st.table(results)
