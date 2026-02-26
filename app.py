import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
from google import genai
from google.genai import types

# --- 1. SETTINGS & SECRETS ---
st.set_page_config(page_title="Alpha Scout Pro", page_icon="🛡️", layout="wide")
GEMINI_KEY = st.secrets.get("GEMINI_KEY")
TG_TOKEN = st.secrets.get("TG_TOKEN")
CHAT_ID = st.secrets.get("CHAT_ID")

# --- 2. ASSET MAPPING (Full Names) ---
ASSET_MAP = {
    "QQQ": "Invesco QQQ Trust (Nasdaq 100)",
    "SPY": "SPDR S&P 500 ETF Trust",
    "BTC-USD": "Bitcoin (USD)",
    "NVDA": "NVIDIA Corporation",
    "AAPL": "Apple Inc.",
    "TSLA": "Tesla, Inc."
}

with st.sidebar:
    st.title("🛡️ Control Panel")
    ticker = st.selectbox("Select Asset", list(ASSET_MAP.keys()))
    asset_full_name = ASSET_MAP[ticker]
    capital = 2500  
    # LOWERED THRESHOLD: 70% allows more opportunities
    threshold = st.slider("Success Probability Threshold", 50, 90, 75)
    test_mode = st.toggle("Enable Test Mode")

# --- 3. DATA & DIRECTION ENGINE ---
@st.cache_data(ttl=60)
def get_market_data(symbol):
    df = yf.download(symbol, period="5d", interval="5m", auto_adjust=True)
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df['EMA_200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    return df

def get_signal_direction(df):
    curr = df.iloc[-1]
    # LONG if price > EMA (Bullish), SHORT if price < EMA (Bearish)
    direction = "LONG (🟢 Buy)" if curr['Close'] > curr['EMA_200'] else "SHORT (🔴 Sell)"
    
    # Calculate score based on trend and RSI momentum
    score = 60 # Base for trend alignment
    if direction == "LONG (🟢 Buy)" and curr['RSI'] < 45: score += 20
    if direction == "SHORT (🔴 Sell)" and curr['RSI'] > 55: score += 20
    return direction, score

# --- 4. DASHBOARD ---
data = get_market_data(ticker)
if not data.empty:
    curr = data.iloc[-1]
    trade_dir, prob_score = get_signal_direction(data)
    
    st.title(f"🛡️ {asset_full_name} ({ticker})")
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.line_chart(data[['Close', 'EMA_200']])
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Price", f"${round(curr['Close'], 2)}")
        m2.metric("Direction", trade_dir)
        m3.metric("AI Confidence", f"{prob_score}%")

    with col2:
        st.subheader("💰 Risk Manager")
        pos_size = min(capital, (25 / ((curr['ATR']*2) / curr['Close']))) if curr['ATR'] > 0 else 0
        st.write(f"Direction: **{trade_dir}**")
        st.success(f"Suggested Entry: **{round(pos_size, 2)} €**")

# --- 5. THE AGENT SWARM ---
st.divider()
if st.button("🚀 ACTIVATE AGENT SYSTEM", key="swarm_btn"):
    with st.status("Agent Swarm Active...", expanded=True) as status:
        if prob_score >= threshold or test_mode:
            st.write(f"🧠 Strategist: Auditing **{trade_dir}** on {asset_full_name}...")
            
            persona = f"""
            You are a Senior Risk Manager. We are looking at a {trade_dir} trade for {asset_full_name}.
            Search news for any events that would crash this specific asset today.
            VETO if risky, PROCEED if safe.
            """
            
            try:
                client = genai.Client(api_key=GEMINI_KEY)
                response = client.models.generate_content(
                    model='gemini-3-flash-preview', 
                    contents=persona,
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                )

                if "PROCEED" in response.text.upper():
                    st.write("✅ Risk Audit: **PASSED**")
                    msg = (f"🎯 **ALPHA SCOUT SIGNAL**\n"
                           f"Asset: {asset_full_name} ({ticker})\n"
                           f"Direction: {trade_dir}\n"
                           f"Entry: ${round(curr['Close'], 2)}\n"
                           f"Size: {round(pos_size, 2)}€")
                    
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                                  data={"chat_id": CHAT_ID, "text": msg})
                    status.update(label="🚀 SIGNAL SENT!", state="complete")
                    st.balloons()
                else:
                    st.error(f"❌ AI VETO: {response.text}")
                    status.update(label="⚠️ Vetoed", state="error")
            except Exception as e:
                st.error(f"AI Error: {e}")
        else:
            st.warning(f"⚖️ Analyst: Confidence ({prob_score}%) below {threshold}% threshold.")
